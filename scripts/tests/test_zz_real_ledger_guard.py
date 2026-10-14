"""Run the spawn-ledger real-ledger guard inside the scripts suite too (several tests here drive spawn writers).
The logic lives in mods/spawn-ledger/tests/test_zz_real_ledger_guard.py; loading it here snapshots the real
ledgers at discover time, before any scripts test runs, and the test below re-checks after them (test_zz sorts last).
Skipped when the mod tests are not next to this suite (a copy of scripts/ outside the repo)."""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "..", "mods", "spawn-ledger", "tests", "test_zz_real_ledger_guard.py")
_guard = None
if os.path.isfile(_SRC):
    _spec = importlib.util.spec_from_file_location("spawn_ledger_real_ledger_guard", _SRC)
    _guard = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_guard)


@unittest.skipIf(_guard is None, "mods/spawn-ledger/tests not present next to scripts/tests")
class RealLedgerGuard(unittest.TestCase):
    def test_no_test_wrote_a_real_ledger(self):
        problems = _guard.violations(_guard.SNAPSHOT)
        self.assertEqual(problems, [], "a test run wrote the REAL spawn ledger; isolate it with SPAWN_LOG_FILE=<tmp>:\n"
                         + "\n".join(problems))
