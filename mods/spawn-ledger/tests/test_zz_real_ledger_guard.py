"""Fails the run if any test touched a LIVE log (logs/**, memory/**/*.jsonl, spawns ledgers). test_zz sorts last.
Why: 2026-10-12 an un-isolated test wrote tu-1/tu-2 rows into the real global ledger (the reconcile sweep later closed them as
spawn_end rows dated the next day, so they looked like fresh leaks); 2026-10-13 a port run of test_win32.py leaked 4 rows into
logs/artifact-verify.jsonl (ledger.verify ignored a patched HOME). Isolation is opt-in per test, so the guard watches the files instead of trusting each test.
The logic, the classes (SESSION append-only + test fingerprints / STATIC any change / IGNORED) and the flake tradeoff are in the ONE
shared module hooks/lib/live_log_guard.py; the baseline was taken by test_00_isolation.py before any test ran (taken at import here
when this file is the only module loaded). Same loader in hooks/tests and scripts/tests. Self-tests of the guard: hooks/tests/test_live_log_guard.py.
Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../hooks/lib")))
import live_log_guard  # noqa: E402

BASELINE = live_log_guard.baseline()
REAL_HOME = live_log_guard.real_home()  # the passwd/recorded home, never the temp HOME a test patched


class LiveLogGuard(unittest.TestCase):
    def test_no_test_wrote_a_live_log(self):
        problems = live_log_guard.violations(BASELINE)
        self.assertEqual(problems, [], "a test run wrote a LIVE log; isolate the writer (see hooks/lib/test_home.py):\n" + "\n".join(problems))


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
        self.assertTrue(self.ledger.refuses_real_ledger(os.path.join(live_log_guard.real_root(), "logs", "spawns.jsonl")))
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
