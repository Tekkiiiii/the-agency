"""reconcile-stale-spawns.sh finds the spawn_end of a spawn in OTHER project logs through hooks/lib/spawn_project.all_logs,
including a project whose medium-term.md row is a Windows backslash path.

Why: the sweep's inline python split the table row on "/" only and expanded every "~". A Windows row
(`C:\\Users\\x\\proj\\memory\\`) became the garbage path `C:\\Users\\x\\proj\\memory\\/memory/spawns.jsonl`, so a spawn_end sitting in
that project's log was never seen and the spawn got a false ABANDONED row (the exact failure test_reconcile_cross_log.py guards
for the SPAWN_LOG_FILE/EXTRA_LOGS path, here for the medium-term.md path).
Table: Windows rows proj and proj2 (path-boundary siblings), a POSIX row whose directory holds a non-leading "~", a leading-"~" row.
Each of four spawns has its spawn_end in exactly one of those logs; a fifth has none and must be the ONLY ABANDONED.
macOS: project_rows folds C:\\x to C:/x, so the log is <dir of the primary log>/C:/Users/x/proj/memory/spawns.jsonl (the sweep cd's into the primary log's directory, so a
relative path resolves there);
on Windows the C:\\Users\\x tree would be real, so those tests are skipped there.
Run: python3 -m unittest discover -s hooks/tests -p 'test_reconcile_windows_rows*' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "lib")
sys.path.insert(0, LIB)
import find_bash  # noqa: E402  (never the Windows WSL launcher)
import spawn_project as sp  # noqa: E402
import test_home  # noqa: E402

SCRIPT = os.environ.get("RECONCILE_SCRIPT") or os.path.join(LIB, "reconcile-stale-spawns.sh")
BASH = find_bash.find_bash()
OLD = (datetime.now().astimezone() - timedelta(hours=10)).isoformat(timespec="seconds")


def rows(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def start(sid):
    return {"event": "spawn_start", "spawn_id": sid, "tool_use_id": "t" + sid, "subagent_type": "coord", "model": "inherit", "ts": OLD}


def end(sid):
    return {"event": "spawn_end", "spawn_id": sid, "outcome": "DONE", "ts": OLD}


@unittest.skipUnless(BASH, "no usable bash (on Windows: Git for Windows)")
@unittest.skipIf(os.name == "nt", "builds C:/Users/x/... under a temp cwd; the Windows spelling is covered by hooks/tests/test_win32_*")
class ReconcileMediumTermRows(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.cwd = os.path.join(self.tmp, "cwd")
        self.posix_root = os.path.join(self.tmp, "a~b", "posix")  # a "~" that is NOT leading
        self.root = os.path.join(self.home, "agency")  # the agency root, handed over as AGENCY_HOME
        os.makedirs(os.path.join(self.root, "memory"))
        os.makedirs(self.cwd)
        with open(os.path.join(self.root, "memory", "medium-term.md"), "w", encoding="utf-8") as f:
            f.write("\n".join([
                "| Project | Memory Path | PD | Flag |",
                "|---|---|---|---|",
                "| proj | `C:\\Users\\x\\proj\\memory\\` | proj-pd | active |",
                "| proj2 | `C:\\Users\\x\\proj2\\memory\\` | proj2-pd | active |",
                "| posix | `%s/memory/` | posix-pd | active |" % self.posix_root,
                "| tilde | `~/tproj/memory/` | tilde-pd | active |",
                "",
            ]))
        self.primary = os.path.join(self.tmp, "primary.jsonl")
        with open(self.primary, "w") as f:
            for sid in ("in-proj", "in-proj2", "in-posix", "in-tilde", "lone"):
                f.write(json.dumps(start(sid)) + "\n")
        # one spawn_end per project log, each in a DIFFERENT log: a proj log read for proj2 (or the reverse) would still miss one
        for root, sid in (("C:/Users/x/proj", "in-proj"), ("C:/Users/x/proj2", "in-proj2"),
                          (self.posix_root, "in-posix"), (self.home + "/tproj", "in-tilde")):
            log = os.path.join(os.path.dirname(self.primary), sp._native(root), "memory", "spawns.jsonl") if root.startswith("C:") \
                else sp._native(root) + "/memory/spawns.jsonl"
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "w") as f:
                f.write(json.dumps(end(sid)) + "\n")

    def sweep(self):
        env = test_home.shell_env(self.home, AGENCY_HOME=self.root)
        for k in ("SPAWN_LOG_FILE", "SPAWN_LEDGER_EXTRA_LOGS", "SPAWN_MEDIUM_TERM"):
            env.pop(k, None)
        r = subprocess.run([BASH, SCRIPT, self.primary], env=env, cwd=self.cwd, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_end_in_any_medium_term_project_log_is_not_abandoned(self):
        self.sweep()
        abandoned = sorted(r["spawn_id"] for r in rows(self.primary) if r.get("event") == "spawn_end")
        self.assertEqual(abandoned, ["lone"])  # false ABANDONED for in-proj / in-proj2 / in-posix = the Windows-row / "~" bug

    def test_sweep_is_idempotent(self):
        self.sweep()
        os.remove(self.primary + ".reconcile-marker")  # lift the throttle
        self.sweep()
        ends = [r["spawn_id"] for r in rows(self.primary) if r.get("event") == "spawn_end"]
        self.assertEqual(ends, ["lone"])


if __name__ == "__main__":
    unittest.main()
