"""Guard: a test run must not write the REAL spawn ledgers (global logs/spawns.jsonl, any {project}/memory/spawns.jsonl).

Why: 2026-10-12 an un-isolated test wrote tu-1/tu-2 rows into the real global ledger; the reconcile sweep closed them a
day later as spawn_end rows dated 2026-10-13, so they looked like fresh leaks. Isolation is opt-in per test, so the
guard watches the files instead of trusting each test.

How: this module is imported at discover time, BEFORE any test runs, and snapshots every real ledger (byte length +
sha256 of its content). The last test (test_zz sorts last) asserts for each ledger that
  1. the snapshotted bytes are unchanged (append-only invariant: no rewrite/truncate), and
  2. every row appended since carries an empty or real `toolu_...` tool_use_id.
It is NOT a size/mtime check: real sessions legitimately append to the live ledger while a suite runs, so that would
flake. Test fixtures use ids like tu-1, test-*, x, t1: any of them in a real ledger fails the run.
Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v
"""
import glob
import hashlib
import json
import os
try:
    import pwd
except ImportError:  # win32: no pwd; REAL_HOME falls back to expanduser below
    pwd = None
import unittest

# The real home from the passwd entry, not $HOME: tests patch HOME to a temp tree.
# SPAWN_LEDGER_GUARD_HOME points the guard at a stand-in tree (used only to demonstrate the guard failing).
REAL_HOME = os.environ.get("SPAWN_LEDGER_GUARD_HOME") or (pwd.getpwuid(os.getuid()).pw_dir if pwd else os.path.expanduser("~"))


# The agency root as ledger.py resolves it (AGENCY_HOME, else CLAUDE_CONFIG_DIR, else ~/.claude), read at import,
# before any test patches the environment. The default <home>/.claude is always watched too.
REAL_ROOT = os.environ.get("AGENCY_HOME") or os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(REAL_HOME, ".claude")


def real_ledgers():
    paths = []
    for root in {REAL_ROOT, os.path.join(REAL_HOME, ".claude")}:
        paths.append(os.path.join(root, "logs", "spawns.jsonl"))
        paths += glob.glob(os.path.join(root, "projects", "*", "memory", "spawns.jsonl"))
    paths += glob.glob(os.path.join(REAL_HOME, "projects", "*", "memory", "spawns.jsonl"))
    paths += glob.glob(os.path.join(REAL_HOME, "projects", "*", "*", "memory", "spawns.jsonl"))
    return sorted(set(paths))


def snapshot(path):
    """(length, sha256 of those bytes) or None when the file does not exist."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    return len(data), hashlib.sha256(data).hexdigest()


def violations(before):
    """Human-readable problems between the snapshot `before` ({path: snapshot|None}) and now; [] = clean."""
    problems = []
    for path in sorted(set(before) | set(real_ledgers())):
        was = before.get(path)
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            if was:
                problems.append("%s: real ledger disappeared" % path)
            continue
        base = was[0] if was else 0
        if was and hashlib.sha256(data[:base]).hexdigest() != was[1]:
            problems.append("%s: existing rows were rewritten or truncated during the test run" % path)
            continue
        for raw in data[base:].decode("utf-8", "replace").splitlines():
            try:
                tuid = json.loads(raw).get("tool_use_id")
            except Exception:
                problems.append("%s: non-JSON line appended: %.80r" % (path, raw))
                continue
            if tuid and not str(tuid).startswith("toolu_"):
                problems.append("%s: test row appended (tool_use_id=%r)" % (path, tuid))
    return problems


SNAPSHOT = {p: snapshot(p) for p in real_ledgers()}  # taken at import = before any test runs


class RealLedgerGuard(unittest.TestCase):
    def test_no_test_wrote_a_real_ledger(self):
        problems = violations(SNAPSHOT)
        self.assertEqual(problems, [], "a test run wrote the REAL spawn ledger; isolate it with SPAWN_LOG_FILE=<tmp>:\n"
                         + "\n".join(problems))


class GuardSelfTest(unittest.TestCase):
    """The guard itself, on temp files (never the real ledgers)."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp(prefix="ledger-guard-")
        self.path = os.path.join(self.dir, "spawns.jsonl")
        with open(self.path, "w") as f:
            f.write('{"event": "spawn_start", "tool_use_id": "toolu_01abc"}\n')
        self.before = {self.path: snapshot(self.path)}
        real = real_ledgers
        globals()["real_ledgers"] = lambda: [self.path]
        self.addCleanup(globals().__setitem__, "real_ledgers", real)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def append(self, line):
        with open(self.path, "a") as f:
            f.write(line + "\n")

    def test_clean_and_real_appends_pass(self):
        self.assertEqual(violations(self.before), [])
        self.append('{"event": "spawn_end", "tool_use_id": "toolu_02def"}')
        self.append('{"event": "spawn_end", "tool_use_id": ""}')
        self.assertEqual(violations(self.before), [])

    def test_test_row_fails(self):
        self.append('{"event": "spawn_end", "tool_use_id": "tu-1"}')
        self.assertEqual(len(violations(self.before)), 1)

    def test_rewrite_fails(self):
        with open(self.path, "w") as f:
            f.write('{"event": "spawn_start", "tool_use_id": "toolu_ZZZZZ"}\n')
        self.assertIn("rewritten", violations(self.before)[0])


class RefuseRealLedger(unittest.TestCase):
    """ledger.py's own backstop: under a test run it will not append to a spawns.jsonl outside the temp dir."""

    def setUp(self):
        import importlib.util
        here = os.path.dirname(os.path.realpath(__file__))
        spec = importlib.util.spec_from_file_location("ledger_refuse", os.path.join(here, "..", "bin", "ledger.py"))
        self.ledger = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ledger)
        self.probe_dir = os.path.join(here, "_refuse_probe")  # inside the repo, NOT under the temp dir
        self.addCleanup(__import__("shutil").rmtree, self.probe_dir, True)

    def test_non_tmp_ledger_is_refused(self):
        probe = os.path.join(self.probe_dir, "spawns.jsonl")
        self.ledger.append(probe, {"event": "spawn_start", "tool_use_id": "tu-1"})
        self.assertFalse(os.path.exists(probe))
        self.assertTrue(self.ledger.refuses_real_ledger(os.path.join(REAL_HOME, ".claude", "logs", "spawns.jsonl")))
        self.assertTrue(self.ledger.refuses_real_ledger("/x/projects/gamma/memory/spawns.jsonl"))

    def test_tmp_ledger_and_other_files_are_not_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ok = os.path.join(d, "sub", "spawns.jsonl")
            self.ledger.append(ok, {"event": "spawn_start", "tool_use_id": "tu-1"})
            self.assertTrue(os.path.exists(ok))
        self.assertFalse(self.ledger.refuses_real_ledger("/x/logs/artifact-verify.jsonl"))

    def test_production_subprocess_is_not_a_test_run(self):
        import subprocess
        import sys
        code = ("import importlib.util,sys;s=importlib.util.spec_from_file_location('l',sys.argv[1]);"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(m.under_test())")
        env = {k: v for k, v in os.environ.items() if k != "SPAWN_LEDGER_TEST"}
        out = subprocess.run([sys.executable, "-c", code, os.path.join(os.path.dirname(self.probe_dir), "..", "bin", "ledger.py")],
                             capture_output=True, text=True, env=env).stdout.strip()
        self.assertEqual(out, "False")


if __name__ == "__main__":
    unittest.main()
