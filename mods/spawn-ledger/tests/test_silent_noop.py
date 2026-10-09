"""Silent no-op spawn guard in ledger.end(): <5s and 0 work tool uses -> outcome UNKNOWN,
silent_noop true, one silent_noop_spawn metric, one-line warning on stdout.
Temp spawns log + temp metrics file via env overrides (SPAWN_LOG_FILE, SPAWN_LEDGER_METRICS_FILE);
nothing here touches the real logs.
Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # tests -> spawn-ledger -> mods -> repo root
spec = importlib.util.spec_from_file_location("ledger", os.path.join(HERE, "..", "bin", "ledger.py"))
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
ledger.ROOT = REPO  # not whatever AGENCY_HOME / ~/.claude the caller has
sys.path.insert(0, os.path.join(REPO, "hooks", "lib"))
import claude_pricing  # noqa: E402,F401


def usage(seconds, tool_uses, handback=""):
    return {"first_ts": "2026-10-08T10:00:00+00:00",
            "last_ts": "2026-10-08T10:00:%02d+00:00" % seconds if seconds < 60 else "2026-10-08T10:01:00+00:00",
            "tool_uses": tool_uses, "handback_text": handback, "last_text": "DONE all good",
            "totals": {"cost_usd": 0.0}, "by_model": {}}


class SilentNoop(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.log = os.path.join(tmp, "spawns.jsonl")
        self.metrics = os.path.join(tmp, "events.jsonl")
        self.transcript = os.path.join(tmp, "t.jsonl")
        open(self.transcript, "w").close()
        with open(self.log, "w") as f:
            f.write(json.dumps({"event": "spawn_start", "spawn_id": "sid-1", "tool_use_id": "tu-1"}) + "\n")
            f.write(json.dumps({"event": "spawn_launched", "spawn_id": "sid-1", "tool_use_id": "tu-1", "agent_id": "a1"}) + "\n")
        self.env = mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": self.log, "SPAWN_LEDGER_METRICS_FILE": self.metrics})
        self.env.start()
        self.rec = mock.patch.object(ledger, "reconcile", lambda lf: None)
        self.rec.start()

    def tearDown(self):
        self.env.stop(); self.rec.stop()

    def run_end(self, u):
        d = {"agent_id": "a1", "agent_type": "general-purpose", "agent_transcript_path": self.transcript,
             "last_assistant_message": "DONE"}
        out = io.StringIO()
        with mock.patch.object(claude_pricing, "usage_from_transcript", lambda p: u), contextlib.redirect_stdout(out):
            ledger.end(d)
        return self.end_entry(), self.events(), out.getvalue()

    def end_entry(self):
        with open(self.log) as f:
            rows = [json.loads(l) for l in f if '"spawn_end"' in l]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def events(self):
        if not os.path.exists(self.metrics):
            return []
        with open(self.metrics) as f:
            return [json.loads(l) for l in f]

    def test_a_3s_zero_tools_is_flagged(self):
        e, ev, out = self.run_end(usage(3, 0))
        self.assertEqual(e["outcome"], "UNKNOWN")
        self.assertIs(e["silent_noop"], True)
        self.assertEqual([x["event"] for x in ev], ["silent_noop_spawn"])
        self.assertEqual(ev[0]["agent_type"], "general-purpose")
        self.assertIn("silent no-op spawn: <5s/0 tools, treat as unverified", out)

    def test_a2_handback_only_is_still_silent(self):
        # SubagentHandback is itself a tool_use in the transcript; it is not work.
        e, ev, _ = self.run_end(usage(3, 1, handback="DONE nothing done"))
        self.assertEqual(e["outcome"], "UNKNOWN")
        self.assertIs(e["silent_noop"], True)
        self.assertEqual(len(ev), 1)

    def test_b_3s_two_tools_unchanged(self):
        e, ev, out = self.run_end(usage(3, 2))
        self.assertEqual(e["outcome"], "DONE")
        self.assertNotIn("silent_noop", e)
        self.assertEqual(ev, [])
        self.assertEqual(out, "")

    def test_b2_handback_plus_one_real_tool_unchanged(self):
        e, ev, _ = self.run_end(usage(3, 2, handback="DONE"))
        self.assertEqual(e["outcome"], "DONE")
        self.assertEqual(ev, [])

    def test_c_60s_zero_tools_unchanged(self):
        e, ev, out = self.run_end(usage(60, 0))
        self.assertEqual(e["outcome"], "DONE")
        self.assertNotIn("silent_noop", e)
        self.assertEqual(ev, [])

    def test_d_missing_usage_unchanged(self):
        e, ev, out = self.run_end(None)
        self.assertEqual(e["outcome"], "DONE")
        self.assertNotIn("silent_noop", e)
        self.assertEqual(ev, [])
        self.assertEqual(out, "")

    def test_d2_missing_timestamps_unchanged(self):
        u = usage(3, 0); u["first_ts"] = None
        e, ev, _ = self.run_end(u)
        self.assertEqual(e["outcome"], "DONE")
        self.assertEqual(ev, [])


if __name__ == "__main__":
    unittest.main()
