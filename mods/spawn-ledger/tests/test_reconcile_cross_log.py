"""reconcile-stale-spawns.sh must not write a false ABANDONED when the spawn_end sits in another log."""
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta

SCRIPT = os.environ.get("RECONCILE_SCRIPT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "hooks", "lib", "reconcile-stale-spawns.sh")
OLD = (datetime.now().astimezone() - timedelta(hours=10)).isoformat(timespec="seconds")


def rows(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


class CrossLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.a = os.path.join(self.tmp, "a.jsonl")
        self.b = os.path.join(self.tmp, "b.jsonl")
        with open(self.a, "w") as f:
            for sid in ("split-1", "lone-2"):
                f.write(json.dumps({"event": "spawn_start", "spawn_id": sid, "tool_use_id": "t" + sid,
                                    "subagent_type": "coord", "model": "inherit", "ts": OLD}) + "\n")
        with open(self.b, "w") as f:
            f.write(json.dumps({"event": "spawn_launched", "spawn_id": "lone-2", "resolved_model": "claude-opus-5-5[1m]"}) + "\n")
            f.write("not json spawn_end\n")
            f.write(json.dumps({"event": "spawn_end", "spawn_id": "split-1", "outcome": "DONE", "ts": OLD}) + "\n")

    def sweep(self, extra):
        env = dict(os.environ, SPAWN_LOG_FILE=self.a, SPAWN_LEDGER_EXTRA_LOGS=extra)
        r = subprocess.run(["bash", SCRIPT, self.a], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_end_in_other_log_is_not_abandoned(self):
        self.sweep(self.b)
        ab = [r for r in rows(self.a) if r.get("event") == "spawn_end"]
        self.assertEqual([r["spawn_id"] for r in ab], ["lone-2"])
        self.assertEqual(ab[0]["model"], "claude-opus-5-5")  # launched row in the other log is used

    def test_no_extra_logs_keeps_old_behaviour(self):
        self.sweep("")
        ab = sorted(r["spawn_id"] for r in rows(self.a) if r.get("event") == "spawn_end")
        self.assertEqual(ab, ["lone-2", "split-1"])


if __name__ == "__main__":
    unittest.main()
