"""Unit tests for scripts/os-cost-report.py (spawn cost by skill/agent/project/model, joined to Jev route ids).
Temp dirs only; SPAWN_LOG_FILE and SKILL_ROUTE_LOG point into them, so no real log is read or written.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_os_cost_report*' -v
"""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "os-cost-report.py")
NOW = datetime.datetime(2026, 10, 20, tzinfo=datetime.timezone.utc)


def load():
    spec = importlib.util.spec_from_file_location("os_cost_report", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def start(sid, route=None, skills=("backend",), project="demo", **kw):
    r = {"event": "spawn_start", "spawn_id": sid, "skills": list(skills), "project": project, "subagent_type": "general-purpose"}
    if route is not None:
        r["jev_route_id"] = route
    r.update(kw)
    return r


def end(sid, usd, tok, ts="2026-10-19T00:00:00Z", **kw):
    r = {"event": "spawn_end", "spawn_id": sid, "cost_usd": usd, "tokens": tok, "ts": ts, "model": "sonnet"}
    r.update(kw)
    return r


class CostReport(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="os-cost-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = os.path.join(self.tmp, "proj", "memory", "spawns.jsonl")
        self.route_log = os.path.join(self.tmp, "skill-route.jsonl")
        os.makedirs(os.path.dirname(self.log))
        patcher = mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": self.log, "SKILL_ROUTE_LOG": self.route_log})
        patcher.start()
        self.addCleanup(patcher.stop)
        for k in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR", "SPAWN_LEDGER_EXTRA_LOGS"):
            os.environ.pop(k, None)
        self.mod = load()

    def write(self, path, rows):
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def build(self, rows, routes=(), days=7):
        self.write(self.log, rows)
        self.write(self.route_log, routes)
        return self.mod.build([self.log], self.route_log, NOW, days)

    def test_exact_route_join_is_attributed(self):
        rep = self.build([start("s1", route="abc123"), end("s1", 2.0, 100)], [{"route_id": "abc123", "skills": ["backend"]}])
        self.assertEqual(rep["totals"]["attributed"]["usd"], 2.0)
        self.assertEqual(rep["attributed_pct"], 100.0)
        self.assertEqual(rep["totals"]["post_change_attributed"]["spawns"], 1)

    def test_start_without_route_key_is_pre_change_and_unattributed(self):
        rep = self.build([start("s1"), end("s1", 1.5, 50)], [{"route_id": "abc123"}])
        self.assertEqual(rep["totals"]["pre_change"]["usd"], 1.5)
        self.assertEqual(rep["totals"]["post_change"]["spawns"], 0)
        self.assertEqual(rep["totals"]["attributed"]["spawns"], 0)

    def test_empty_route_id_is_post_change_unattributed(self):
        rep = self.build([start("s1", route=""), end("s1", 1.0, 10)], [])
        self.assertEqual(rep["totals"]["post_change"]["spawns"], 1)
        self.assertEqual(rep["totals"]["attributed"]["spawns"], 0)

    def test_route_id_missing_from_route_log_is_unattributed(self):
        rep = self.build([start("s1", route="zzz999"), end("s1", 1.0, 10)], [{"route_id": "abc123"}])
        self.assertEqual(rep["totals"]["attributed"]["spawns"], 0)
        self.assertEqual(rep["totals"]["post_change"]["spawns"], 1)
        self.assertEqual(rep["attributed_pct_post_change"], 0.0)

    def test_end_without_start_row_counted(self):
        rep = self.build([end("ghost", 3.0, 30, agent_type="coord")])
        self.assertEqual(rep["totals"]["no_start_row"]["usd"], 3.0)
        self.assertIn("coord", rep["by_agent_type"])
        self.assertIn("(none)", rep["by_skill"])

    def test_window_cut_by_now_and_days(self):
        rows = [start("a"), end("a", 1.0, 10, ts="2026-10-19T00:00:00Z"),
                start("b"), end("b", 5.0, 50, ts="2026-10-01T00:00:00Z"),
                start("c"), end("c", 7.0, 70, ts="2026-10-21T00:00:00Z")]  # in the future of --now
        self.assertEqual(self.build(rows)["totals"]["all"]["usd"], 1.0)
        self.assertEqual(self.build(rows, days=30)["totals"]["all"]["usd"], 6.0)

    def test_skills_split_evenly(self):
        rep = self.build([start("s1", skills=("backend", "frontend")), end("s1", 2.0, 100)])
        self.assertEqual(rep["by_skill"]["backend"]["usd"], 1.0)
        self.assertEqual(rep["by_skill"]["frontend"]["usd"], 1.0)
        self.assertEqual(rep["by_skill"]["backend"]["tokens"], 50)
        self.assertEqual(rep["by_project"]["demo"]["usd"], 2.0)
        self.assertEqual(rep["by_model"]["sonnet"]["tokens"], 100)

    def test_continuation_rows_counted_and_summed(self):
        rep = self.build([start("s1"), end("s1", 1.0, 10), end("s1", 1.0, 10, continuation=True)])
        self.assertEqual(rep["continuation_rows"], 1)
        self.assertEqual(rep["totals"]["all"]["usd"], 2.0)

    def test_main_writes_report_and_exits_zero(self):
        self.write(self.log, [start("s1"), end("s1", 1.0, 10, ts=NOW.isoformat())])
        out = os.path.join(self.tmp, "o", "cost.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = self.mod.main(["--out", out, "--now", NOW.isoformat()])
        self.assertEqual(rc, 0)
        with open(out, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["totals"]["all"]["usd"], 1.0)

    def test_default_paths_resolve_under_agency_home(self):
        root = os.path.join(self.tmp, "custom-root")
        with mock.patch.dict(os.environ, {"AGENCY_HOME": root}):
            os.environ.pop("SKILL_ROUTE_LOG", None)
            mod = load()
            self.assertEqual(mod.default_out(), os.path.join(root, "state", "os", "cost-weekly.json"))
            self.assertEqual(mod.default_route_log(), os.path.join(root, "memory", "metrics", "skill-route.jsonl"))
            os.environ["SKILL_ROUTE_LOG"] = self.route_log
            self.assertEqual(mod.default_route_log(), self.route_log)


if __name__ == "__main__":
    unittest.main()
