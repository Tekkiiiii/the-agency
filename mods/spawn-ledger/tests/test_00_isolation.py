"""test_00_isolation.py: FIRST module `unittest discover` imports in this directory (it sorts first). Do not rename it.

It runs, before any other test module is imported:
  1. live_log_guard.baseline()  - snapshots every live log (hooks/lib/live_log_guard.py), so test_zz_real_ledger_guard.py can fail the
     run if any test touched one;
  2. test_home.isolate_process_home() - moves HOME/USERPROFILE/HOMEDRIVE/HOMEPATH of this whole process to a temp tree, so a test that
     forgets to isolate a writer (ledger.py verify, emit-metric.sh, jev_client, skill-route, ...) writes there, not into the real agency root.
Covers: `python3 -m unittest discover -s <this dir>` with any pattern that matches this file (the default test*.py does).
NOT covered: a single test file run on its own and `discover -p <one file>` (this module is not imported then), and the TS kit tests
(`claude plugin test`, a fake engine: no real fs). Those entry points stay safe only through each test's own isolation, the writers'
refusal backstops (ledger.py refuses_real_ledger) and a later full-suite guard run. Design and audit: hooks/lib/test_home.py,
hooks/lib/live_log_guard.py.
"""
import os
import sys
import unittest

LOADED_BEFORE = sorted(m for m in sys.modules if m.startswith("test_") and m != __name__)  # must be empty: we are first

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../hooks/lib')))
import live_log_guard  # noqa: E402
import test_home  # noqa: E402

live_log_guard.baseline()
ISOLATED = test_home.isolate_process_home()


class Isolation(unittest.TestCase):
    def test_this_module_was_imported_before_every_other_test_module(self):
        self.assertEqual(LOADED_BEFORE, [], "test_00_isolation must be the first test module imported")

    def test_process_home_is_the_temp_tree_not_the_real_home(self):
        self.assertEqual(os.path.expanduser("~"), ISOLATED.home)
        self.assertNotEqual(os.path.realpath(ISOLATED.home), os.path.realpath(live_log_guard.real_home()))
        self.assertEqual(os.environ.get("TEST_HOME_ISOLATED"), "1")

    def test_data_dirs_are_empty_temp_dirs_and_code_is_mirrored(self):
        for d in ("logs", "state", "memory", "projects"):  # real dirs inside the temp tree, never links to the real data
            self.assertTrue(os.path.isdir(os.path.join(ISOLATED.claude, d)))
            self.assertFalse(os.path.islink(os.path.join(ISOLATED.claude, d)))
        self.assertIn("hooks", ISOLATED.mirrored + ISOLATED.skipped)


if __name__ == "__main__":
    unittest.main()
