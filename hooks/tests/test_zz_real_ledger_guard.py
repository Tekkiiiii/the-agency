"""Fails the run if any test touched a LIVE log (logs/**, memory/**/*.jsonl, spawns ledgers). test_zz sorts last.
The logic, the classes (SESSION append-only + test fingerprints / STATIC any change / IGNORED) and the flake tradeoff are in
hooks/lib/live_log_guard.py; the baseline was taken by test_00_isolation.py before any test ran (or is taken at import here when
this file is the only module loaded, e.g. `discover -p test_zz*`)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib')))
import live_log_guard  # noqa: E402

BASELINE = live_log_guard.baseline()


class LiveLogGuard(unittest.TestCase):
    def test_no_test_wrote_a_live_log(self):
        problems = live_log_guard.violations(BASELINE)
        self.assertEqual(problems, [], "a test run wrote a LIVE log; isolate the writer (see hooks/lib/test_home.py):\n" + "\n".join(problems))

if __name__ == "__main__":
    unittest.main()
