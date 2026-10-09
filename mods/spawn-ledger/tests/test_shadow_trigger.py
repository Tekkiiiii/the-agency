"""Shadow-routing trigger in ledger.py: AGENCY_SKILL_ROUTER gate, kill switch, child guard, profile, payload. No real spawns.
Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v
(claude plugin test runs only *.test.ts; the TS fake engine replaces ledger.py, so this
 file is where ledger.py's own logic is covered.)"""
import importlib.util
import json
import os
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ledger", os.path.join(HERE, "..", "bin", "ledger.py"))
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)

D = {"description": "build ui", "parent_agent": "system-improvement-pd",
     "prompt": "Skills: /frontend\n" + "x" * 9000}


class FakePopen:
    calls = []

    def __init__(self, argv, **kw):
        self.argv, self.kw, self.written, self.closed = argv, kw, b"", False
        FakePopen.calls.append(self)
        outer = self

        class In:
            def write(s, b): outer.written += b
            def close(s): outer.closed = True
        self.stdin = In()


class ShadowTrigger(unittest.TestCase):
    def setUp(self):
        FakePopen.calls = []
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "scripts"))
        os.makedirs(os.path.join(self.root, "state", "skill-route"))
        with open(os.path.join(self.root, "scripts", "skill-route.py"), "w"):
            pass
        self.env = mock.patch.dict(os.environ, {"SKILL_ROUTE_CHILD": "", "SKILL_ROUTE_STATE_DIR": "",
                                                "AGENCY_SKILL_ROUTER": "1"})
        self.env.start()
        self.h = mock.patch.object(ledger, "ROOT", self.root)
        self.p = mock.patch.object(ledger.subprocess, "Popen", FakePopen)
        self.h.start(); self.p.start()

    def tearDown(self):
        self.env.stop(); self.h.stop(); self.p.stop()

    def fire(self):
        ledger.fire_shadow("sid-1", D, "general-purpose", D["prompt"])

    def test_fires_detached_with_payload(self):
        self.fire()
        self.assertEqual(len(FakePopen.calls), 1)
        c = FakePopen.calls[0]
        self.assertEqual(c.argv[1:], [os.path.join(self.root, "scripts", "skill-route.py"), "--shadow"])
        self.assertIs(c.kw["start_new_session"], True)
        self.assertEqual(c.kw["stdout"], ledger.subprocess.DEVNULL)
        self.assertEqual(c.kw["stderr"], ledger.subprocess.DEVNULL)
        self.assertTrue(c.closed)
        pl = json.loads(c.written)
        self.assertEqual(set(pl), {"spawn_id", "subagent_type", "parent_agent", "description", "prompt"})
        self.assertEqual(pl["spawn_id"], "sid-1")
        self.assertEqual(len(pl["prompt"]), 8000)

    def test_router_off_by_default(self):
        for value in ("", "0", "true"):
            os.environ["AGENCY_SKILL_ROUTER"] = value
            self.fire()
        del os.environ["AGENCY_SKILL_ROUTER"]
        self.fire()
        self.assertEqual(FakePopen.calls, [])

    def test_child_guard(self):
        os.environ["SKILL_ROUTE_CHILD"] = "1"
        self.fire()
        self.assertEqual(FakePopen.calls, [])

    def test_kill_switch(self):
        open(os.path.join(self.root, "state", "skill-route", "skill-route-shadow.off"), "w").close()
        self.fire()
        self.assertEqual(FakePopen.calls, [])

    def test_minimal_profile(self):
        open(os.path.join(self.root, ".hook-profile"), "w").write("minimal\n")
        self.fire()
        self.assertEqual(FakePopen.calls, [])

    def test_missing_script(self):
        os.remove(os.path.join(self.root, "scripts", "skill-route.py"))
        self.fire()
        self.assertEqual(FakePopen.calls, [])

    def test_never_raises(self):
        with mock.patch.object(ledger.subprocess, "Popen", side_effect=OSError("boom")):
            self.fire()


if __name__ == "__main__":
    unittest.main()
