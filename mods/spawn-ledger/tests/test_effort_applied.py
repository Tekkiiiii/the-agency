"""ledger.py effort_applied: the row the turn.step relay (hooks/register.ts) writes the first time it applies the effort
policy to a subagent. It lands NEXT TO the spawn_start row it belongs to (same lookup as `launched`: the resolved log,
then every other known log), carries what the request had (`seen`) and what was sent (`applied`), and flags `changed`.

Hermetic like the sibling tests: HOME + USERPROFILE (+ HOMEDRIVE/HOMEPATH) point at a temp tree (hooks/lib/test_home.py),
SPAWN_LOG_FILE / SPAWN_LEDGER_EXTRA_LOGS are temp files, the metrics file is a temp file. Nothing real is written.
Run: python3 -m unittest discover -s mods/spawn-ledger/tests -v"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "..", "bin", "ledger.py")
spec = importlib.util.spec_from_file_location("ledger_effort", LEDGER)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
import test_home  # noqa: E402  (ledger.py put hooks/lib on sys.path)


def start_row(sid="sid-1", tu="tu-1", typ="general-purpose"):
    return {"event": "spawn_start", "spawn_id": sid, "tool_use_id": tu, "subagent_type": typ, "child_agent": typ,
            "model": "inherit", "ts": "2026-10-15T09:00:00+07:00"}


def payload(**kw):
    return dict({"tool_use_id": "tu-1", "agent_id": "a1", "seen": "low", "applied": "high", "category": "coding_complex"}, **kw)


class EffortApplied(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="ledger-effort-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, ".claude", "memory"))
        self.log = os.path.join(self.tmp, "global", "spawns.jsonl")
        self.other = os.path.join(self.tmp, "proj", "memory", "spawns.jsonl")
        for p in (self.log, self.other):
            os.makedirs(os.path.dirname(p))
        env = {"SPAWN_LOG_FILE": self.log, "SPAWN_LEDGER_EXTRA_LOGS": self.other,
               "SPAWN_LEDGER_METRICS_FILE": os.path.join(self.tmp, "events.jsonl"), "SKILL_ROUTE_CHILD": "1"}
        env.update({k: test_home.home_env(self.home, base={})[k] for k in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")})
        patch_env = mock.patch.dict(os.environ, env)
        patch_env.start()
        self.addCleanup(patch_env.stop)
        patch_home = mock.patch.object(ledger, "HOME", self.home)  # ledger.HOME is read at import: never the real one
        patch_home.start()
        self.addCleanup(patch_home.stop)

    def put(self, path, *rs):
        with open(path, "a", encoding="utf-8") as f:
            for r in rs:
                f.write(json.dumps(r) + "\n")

    def rows(self, path):
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_row_lands_next_to_the_start_row_with_its_spawn_id(self):
        self.put(self.log, start_row())
        ledger.effort_applied(payload())
        start, row = self.rows(self.log)
        self.assertEqual(row["event"], "effort_applied")
        self.assertEqual(row["spawn_id"], start["spawn_id"])
        self.assertEqual((row["tool_use_id"], row["agent_id"]), ("tu-1", "a1"))
        self.assertEqual((row["seen"], row["applied"], row["category"]), ("low", "high", "coding_complex"))
        self.assertIs(row["changed"], True)
        self.assertTrue(row["ts"])

    def test_field_order(self):
        self.put(self.log, start_row())
        ledger.effort_applied(payload())
        self.assertEqual(list(self.rows(self.log)[1]), [
            "event", "spawn_id", "tool_use_id", "agent_id", "seen", "applied", "category", "changed", "ts"])

    def test_changed_is_false_when_seen_equals_applied(self):
        self.put(self.log, start_row())
        ledger.effort_applied(payload(seen="high"))
        self.assertIs(self.rows(self.log)[1]["changed"], False)

    def test_seen_null_counts_as_changed_and_stays_null(self):
        self.put(self.log, start_row())
        ledger.effort_applied(payload(seen=None))
        row = self.rows(self.log)[1]
        self.assertIsNone(row["seen"])
        self.assertIs(row["changed"], True)

    def test_start_in_another_known_log_the_row_follows_it(self):
        self.put(self.other, start_row(sid="sid-9", tu="tu-9"))
        ledger.effort_applied(payload(tool_use_id="tu-9"))
        self.assertEqual(self.rows(self.log), [])
        self.assertEqual([r["event"] for r in self.rows(self.other)], ["spawn_start", "effort_applied"])
        self.assertEqual(self.rows(self.other)[1]["spawn_id"], "sid-9")

    def test_two_spawns_do_not_cross(self):
        self.put(self.log, start_row("sid-1", "tu-1"), start_row("sid-2", "tu-2"))
        ledger.effort_applied(payload(tool_use_id="tu-2", agent_id="a2"))
        ledger.effort_applied(payload(tool_use_id="tu-1", agent_id="a1"))
        self.assertEqual([(r["agent_id"], r["spawn_id"]) for r in self.rows(self.log)[2:]], [("a2", "sid-2"), ("a1", "sid-1")])

    def test_unknown_tool_use_id_appends_to_the_resolved_log_with_an_empty_spawn_id(self):
        ledger.effort_applied(payload(tool_use_id="tu-nope"))
        rows = self.rows(self.log)
        self.assertEqual([r["event"] for r in rows], ["effort_applied"])
        self.assertEqual(rows[0]["spawn_id"], "")

    def test_a_test_run_never_writes_a_real_ledger(self):
        # outside the system temp dir and named spawns.jsonl = a "real" ledger as far as the guard can tell
        with mock.patch.object(ledger, "resolve_log_file", lambda d=None: "/effort-guard-probe/logs/spawns.jsonl"), \
                mock.patch.object(ledger, "other_logs", lambda p: []):
            ledger.effort_applied(payload())
        self.assertFalse(os.path.exists("/effort-guard-probe"))

    def test_cli_dispatch_exits_zero_and_writes_the_row(self):
        self.put(self.log, start_row())
        env = dict(os.environ, SPAWN_LEDGER_TEST="1")
        ran = subprocess.run([sys.executable, LEDGER, "effort_applied"], input=json.dumps(payload()), text=True,
                             capture_output=True, env=env, timeout=30)
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertEqual([r["event"] for r in self.rows(self.log)], ["spawn_start", "effort_applied"])

    def test_cli_garbage_payload_still_exits_zero(self):
        env = dict(os.environ, SPAWN_LEDGER_TEST="1")
        ran = subprocess.run([sys.executable, LEDGER, "effort_applied"], input="not json", text=True,
                             capture_output=True, env=env, timeout=30)
        self.assertEqual(ran.returncode, 0)
        self.assertEqual(self.rows(self.log), [])


if __name__ == "__main__":
    unittest.main()
