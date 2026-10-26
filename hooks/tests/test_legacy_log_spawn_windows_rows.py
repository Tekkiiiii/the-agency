"""log-spawn-from-agent.sh / log-spawn-end-from-agent.sh (legacy manual convention, no live caller) pick the project log through
hooks/lib/spawn_project, not their own `cwd.startswith(root)` copy of the matcher.

Why: that copy had no path boundary (project /x/proj captured a cwd in /x/proj2) and never matched a Windows backslash
CLAUDE_PROJECT_DIR (C:\\Users\\x\\proj\\sub vs row `C:\\Users\\x\\proj\\memory\\`), so such a spawn landed in the global log.
Without SPAWN_LOG_FILE both scripts must write start + end to the SAME resolved log. macOS: the Windows row folds to C:/Users/x/proj,
so the log is <cwd>/C:/Users/x/proj/memory/spawns.jsonl (script cwd = a temp dir); skipped on Windows (would build a real C:\\Users\\x tree).
Run: python3 -m unittest discover -s hooks/tests -p 'test_legacy_log_spawn_windows_rows*' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "lib")
sys.path.insert(0, LIB)
import find_bash  # noqa: E402
import test_home  # noqa: E402

BASH = find_bash.find_bash()


def rows(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


@unittest.skipUnless(BASH, "no usable bash (on Windows: Git for Windows)")
@unittest.skipIf(os.name == "nt", "builds C:/Users/x/... under a temp cwd")
class LegacyHooks(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.cwd = os.path.join(self.tmp, "cwd")
        self.root = os.path.join(self.home, "agency")  # the agency root, handed over as AGENCY_HOME
        os.makedirs(os.path.join(self.root, "memory"))
        os.makedirs(self.cwd)
        self.glob_log = os.path.join(self.root, "logs", "spawns.jsonl")

    def table(self, *lines):
        with open(os.path.join(self.root, "memory", "medium-term.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(["| Project | Memory Path | PD | Flag |", "|---|---|---|---|"] + list(lines) + [""]))

    def run_pair(self, project_dir):
        env = test_home.shell_env(self.home, AGENCY_HOME=self.root, CLAUDE_PROJECT_DIR=project_dir)
        env.pop("SPAWN_LOG_FILE", None)
        out = subprocess.run([BASH, os.path.join(LIB, "log-spawn-from-agent.sh"), "--parent-agent", "PD-x", "--child-subagent-type",
                              "nobody", "--description", "d", "--prompt-excerpt", "p"],
                             env=env, cwd=self.cwd, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        sid = out.stdout.strip()
        self.assertTrue(sid)
        e = subprocess.run([BASH, os.path.join(LIB, "log-spawn-end-from-agent.sh"), "--spawn-id", sid, "--outcome", "DONE"],
                           env=env, cwd=self.cwd, capture_output=True, text=True, timeout=60)
        self.assertEqual(e.returncode, 0, e.stderr)
        return sid

    def assert_pair_in(self, log, sid):
        self.assertTrue(os.path.isfile(log), "no log at %s" % log)
        self.assertEqual([(r["event"], r["spawn_id"]) for r in rows(log)], [("spawn_start", sid), ("spawn_end", sid)])

    def test_sibling_dir_is_not_inside_the_project(self):
        # only `proj` is in the table: a cwd in proj2 is NOT in it, so the rows go to the global log
        self.table("| proj | `%s/proj/memory/` | proj-pd | active |" % self.tmp)
        sid = self.run_pair(os.path.join(self.tmp, "proj2", "sub"))
        self.assert_pair_in(self.glob_log, sid)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "proj", "memory", "spawns.jsonl")))

    def test_dir_inside_the_project_uses_its_log(self):
        self.table("| proj | `%s/proj/memory/` | proj-pd | active |" % self.tmp)
        sid = self.run_pair(os.path.join(self.tmp, "proj", "sub"))
        self.assert_pair_in(os.path.join(self.tmp, "proj", "memory", "spawns.jsonl"), sid)

    def test_windows_backslash_project_dir_matches_windows_row(self):
        self.table("| proj | `C:\\Users\\x\\proj\\memory\\` | proj-pd | active |",
                   "| proj2 | `C:\\Users\\x\\proj2\\memory\\` | proj2-pd | active |")
        sid = self.run_pair("C:\\Users\\x\\proj2\\sub")
        self.assert_pair_in(os.path.join(self.cwd, "C:", "Users", "x", "proj2", "memory", "spawns.jsonl"), sid)
        self.assertFalse(os.path.exists(self.glob_log))


if __name__ == "__main__":
    unittest.main()
