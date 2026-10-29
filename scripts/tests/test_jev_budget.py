"""Tests for the Jev credit budget guard and the per-run cost approval in scripts/jev_client.py, plus the
paid-runner wiring (skill-route-eval.py, jev-drill.py). Offline: 127.0.0.1 stub only, hermetic state dir
(jev_stub.jev_test_env), no real `claude`, never a real credit file / usage log.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_budget*' -v
"""
import contextlib
import datetime
import io
import json
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import jev_stub  # noqa: E402
import jev_client  # noqa: E402

QUESTIONS = {"domain": {"type": "choice", "instructions": "Which domain?",
                        "criteria": {"frontend-ui": "web ui", "backend": "apis"}}}
OLD = "2026-10-01T00:00:00Z"
COST_ENV = ("JEV_APPROVED_USD", "JEV_RUN_ID", "JEV_RUN_OWNER_PID", "JEV_RUN_STARTED_PPID")


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class BudgetCase(unittest.TestCase):
    def setUp(self):
        self._cm = jev_stub.jev_test_env()
        self.env = self._cm.__enter__()
        self.stub = self.env.stub
        self._saved = {k: os.environ.get(k) for k in ("JEV_CREDIT_FILE", "JEV_BUDGET_RESERVE_USD", "JEV_PURPOSE") + COST_ENV}
        for k in self._saved:
            os.environ.pop(k, None)
        os.environ["JEV_APPROVED_USD"] = "1000"      # pre-approved by default; CostTests clear it
        jev_client._owner_warned[0] = False
        jev_client._budget_mem.clear()
        jev_client._budget_warned[0] = False

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        jev_client._budget_mem.clear()
        self._cm.__exit__(None, None, None)

    def credit(self, balance=5.0, as_of=OLD, expires=None, grant=5.0, day=20):
        exp = expires or _iso(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=20))
        with open(os.path.join(self.env.state_dir, "jev-credit.json"), "w") as fh:
            json.dump({"balance_usd": balance, "as_of": as_of, "monthly_grant_usd": grant,
                       "grant_day_utc": day, "current_grant_expires": exp}, fh)

    def row(self, usd, purpose="eval", router="jev", ok=True, ts=None, run_id=None):
        ts = ts or _iso(datetime.datetime.now(datetime.timezone.utc))
        rec = {"ts": ts, "purpose": purpose, "router": router, "model": "m",
               "input_tokens": 1, "output_tokens": 0, "usd": usd, "latency_ms": 1,
               "ok": ok, "shadow": False}
        if run_id:
            rec["run_id"] = run_id
        with open(self.env.usage_log, "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def ask(self, purpose="eval", **kw):
        return jev_client.ask("route this", QUESTIONS, purpose, **kw)

    def err(self, fn, *a, **kw):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            try:
                return fn(*a, **kw), buf.getvalue()
            except BaseException as e:  # noqa: BLE001
                return e, buf.getvalue()


class GuardTests(BudgetCase):
    def test_constants_and_class(self):
        self.assertEqual(jev_client.BUDGET_EXIT, 75)
        self.assertEqual(jev_client.RESERVE_USD, 1.00)
        self.assertEqual(jev_client.LIVE_PURPOSES, frozenset(["skill-route", "spawn-plan"]))
        self.assertFalse(issubclass(jev_client.BudgetExhausted, jev_client.RouterUnavailable))

    def test_refuses_non_live_below_reserve_no_call_no_haiku_no_usage(self):
        self.credit(balance=1.00)           # 1.00 - 0.0001 < 1.00 reserve
        r, _ = self.err(self.ask, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        self.assertEqual(self.stub.count, 0)
        self.assertEqual(jev_stub.fake_claude_records(self.env.fake_claude), [])
        self.assertEqual(self.env.usage_records(), [])

    def test_allows_non_live_above_reserve(self):
        self.credit(balance=5.0)
        self.assertEqual(self.ask("eval")["router"], "jev")

    def test_live_purposes_never_refused(self):
        self.credit(balance=0.0)
        for p in ("skill-route", "spawn-plan"):
            self.assertEqual(self.ask(p)["router"], "jev", p)

    def test_env_purpose_overrides_argument(self):
        self.credit(balance=0.5)
        os.environ["JEV_PURPOSE"] = "eval"
        r, _ = self.err(self.ask, "skill-route")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        os.environ["JEV_PURPOSE"] = "skill-route"
        self.assertEqual(self.ask("eval")["router"], "jev")

    def test_unknown_purpose_is_non_live(self):
        self.credit(balance=0.5)
        r, _ = self.err(self.ask, "something-new")
        self.assertIsInstance(r, jev_client.BudgetExhausted)

    def test_allow_jev_false_is_not_checked(self):
        self.credit(balance=0.0)
        self.assertEqual(self.ask("eval", allow_jev=False)["router"], "haiku")

    def test_spend_since_as_of_only_jev_rows(self):
        self.credit(balance=1.5, as_of="2026-10-10T00:00:00Z")
        self.row(0.9, ts="2026-10-09T00:00:00Z", ok=False)          # before as_of: ignored
        self.row(0.9, router="haiku", ok=False)                      # haiku: subscription, never counted
        self.assertEqual(self.ask("eval")["router"], "jev")
        self.row(0.6, ok=False)                                      # now 1.5 - 0.6 = 0.9 < reserve
        r, _ = self.err(self.ask, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)

    def test_est_per_call_is_mean_of_ok_jev_rows_for_purpose(self):
        self.credit(balance=1.30)
        self.row(0.2, "eval"); self.row(0.4, "eval"); self.row(9.0, "eval", ok=False); self.row(5.0, "replay")
        # spend 0.6 + 9.0(not ok still counted as spend) ... use fresh: only spend rows count toward balance
        b = jev_client._balance("eval")
        self.assertAlmostEqual(b[1], 0.3)                  # mean(0.2, 0.4); failed + other purpose excluded
        self.assertAlmostEqual(jev_client._balance("drill")[1], jev_client.FALLBACK_EST_USD)

    def test_reserve_env_override(self):
        self.credit(balance=1.5)
        os.environ["JEV_BUDGET_RESERVE_USD"] = "2.0"
        r, _ = self.err(self.ask, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        os.environ["JEV_BUDGET_RESERVE_USD"] = "0.1"
        self.assertEqual(self.ask("eval")["router"], "jev")

    def test_grant_rollover_resets_base(self):
        past = _iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2))
        self.credit(balance=0.2, expires=past, grant=5.0, day=20)
        self.row(0.3, ts=_iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)))
        self.assertEqual(self.ask("eval")["router"], "jev")    # base 5.0 as of expiry; old spend not counted
        self.assertAlmostEqual(jev_client._balance("eval")[0], 5.0, places=3)

    def test_missing_or_bad_credit_file_fails_open_with_one_warning(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            self.assertEqual(self.ask("eval")["router"], "jev")
            self.assertEqual(self.ask("eval")["router"], "jev")
        self.assertEqual(buf.getvalue().count("guard OPEN"), 1)
        with open(os.path.join(self.env.state_dir, "jev-credit.json"), "w") as fh:
            fh.write("{not json")
        jev_client._budget_warned[0] = False
        self.assertEqual(self.err(self.ask, "eval")[0]["router"], "jev")

    def test_credit_file_env_path(self):
        p = os.path.join(self.env.state_dir, "other.json")
        with open(p, "w") as fh:
            json.dump({"balance_usd": 0.1, "as_of": OLD}, fh)
        os.environ["JEV_CREDIT_FILE"] = p
        r, _ = self.err(self.ask, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)


class CacheTests(BudgetCase):
    def test_incremental_and_rebuild_on_shrink(self):
        self.credit(balance=5.0)
        self.row(0.5)
        self.assertAlmostEqual(jev_client._balance("eval")[0], 4.5)
        off = jev_client._budget_mem[(self.env.usage_log, self.env.state_dir)]["offset"]
        self.row(0.5)
        self.assertAlmostEqual(jev_client._balance("eval")[0], 4.0)
        self.assertGreater(jev_client._budget_mem[(self.env.usage_log, self.env.state_dir)]["offset"], off)
        open(self.env.usage_log, "w").close()               # truncate/rotate
        self.row(0.1)
        self.assertAlmostEqual(jev_client._balance("eval")[0], 4.9)

    def test_cache_file_written_and_reused_across_processes(self):
        self.credit(balance=5.0)
        for _ in range(50):
            self.row(0.01)
        jev_client._balance("eval")
        st = jev_client._budget_mem[(self.env.usage_log, self.env.state_dir)]
        jev_client._save_cache(st)
        self.assertTrue(os.path.exists(os.path.join(self.env.state_dir, "jev-spend-cache.json")))
        jev_client._budget_mem.clear()                       # new process: loads the cache, scans 0 new bytes
        self.assertAlmostEqual(jev_client._balance("eval")[0], 4.5)
        self.assertEqual(jev_client._budget_mem[(self.env.usage_log, self.env.state_dir)]["offset"],
                         os.path.getsize(self.env.usage_log))

    def test_base_change_rescans(self):
        self.credit(balance=5.0, as_of="2026-10-01T00:00:00Z")
        self.row(0.5, ts="2026-10-05T00:00:00Z")
        self.assertAlmostEqual(jev_client._balance("eval")[0], 4.5)
        self.credit(balance=5.0, as_of="2026-10-10T00:00:00Z")
        self.assertAlmostEqual(jev_client._balance("eval")[0], 5.0, places=3)

    def test_warm_path_overhead_under_5ms(self):
        self.credit(balance=50.0)
        with open(self.env.usage_log, "w") as fh:
            for i in range(30000):
                fh.write(json.dumps({"ts": "2026-10-05T00:00:00Z", "purpose": "eval", "router": "jev",
                                     "usd": 0.0001, "ok": True}) + "\n")
        jev_client._budget_guard("eval")                     # cold scan
        n = 200
        t = time.time()
        for i in range(n):
            if i % 20 == 0:
                self.row(0.0001)                             # appended lines are picked up incrementally
            jev_client._budget_guard("eval")
        per_ms = (time.time() - t) * 1000.0 / n
        self.assertLess(per_ms, 5.0, "guard overhead %.3f ms" % per_ms)


class PreflightTests(BudgetCase):
    def test_ok_line_and_dict(self):
        self.credit(balance=4.68)
        r, err = self.err(jev_client.budget_preflight, "eval", 100, "sweep")
        self.assertEqual(sorted(r), ["approved", "balance", "balance_after", "est_calls", "est_usd", "ok", "reserve"])
        self.assertTrue(r["ok"])
        self.assertEqual(err.strip(), "jev-budget: sweep purpose=eval est_calls=100 est_usd=$0.0100 "
                                      "balance=$4.68 balance_after=$4.67 reserve=$1.00 approved=$1000.0000 -> OK")

    def test_refused_raises_and_prints(self):
        self.credit(balance=4.68)
        r, err = self.err(jev_client.budget_preflight, "eval", 100000, "big")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        self.assertTrue(err.strip().endswith("-> REFUSED"))

    def test_dry_run_prints_never_refuses(self):
        self.credit(balance=0.5)
        r, err = self.err(jev_client.budget_preflight, "eval", 10, "dry", refuse=False)
        self.assertFalse(r["ok"])
        self.assertIn("-> REFUSED", err)

    def test_preflight_or_exit_75(self):
        self.credit(balance=0.5)
        r, _ = self.err(jev_client.preflight_or_exit, "eval", 10, "x")
        self.assertIsInstance(r, SystemExit)
        self.assertEqual(r.code, 75)
        r, _ = self.err(jev_client.preflight_or_exit, "eval", 10, "x", dry_run=True)
        self.assertTrue(r["balance"] == 0.5)

    def test_no_credit_file_prints_ok_unknown(self):
        r, err = self.err(jev_client.budget_preflight, "eval", 10, "x")
        self.assertTrue(r["ok"])
        self.assertIn("balance=unknown", err)


class GuardOrderTests(BudgetCase):
    def test_guard_runs_before_the_jev_attempt(self):
        calls = []
        real = jev_client._budget_guard
        jev_client._budget_guard = lambda p: calls.append(p)
        self.addCleanup(setattr, jev_client, "_budget_guard", real)
        self.ask("eval")
        self.assertEqual(calls, ["eval"])

    def test_budget_exhausted_stops_without_haiku_or_usage(self):
        def guard(p):
            raise jev_client.BudgetExhausted(1.0, 1.0, 0.1, p)
        real = jev_client._budget_guard
        jev_client._budget_guard = guard
        self.addCleanup(setattr, jev_client, "_budget_guard", real)
        with self.assertRaises(jev_client.BudgetExhausted):
            self.ask("eval")
        self.assertEqual(jev_stub.fake_claude_records(self.env.fake_claude), [])
        self.assertEqual(self.stub.count, 0)
        self.assertEqual(self.env.usage_records(), [])

    def test_disabled_router_never_reaches_the_guard(self):
        calls = []
        real = jev_client._budget_guard
        jev_client._budget_guard = lambda p: calls.append(p)
        self.addCleanup(setattr, jev_client, "_budget_guard", real)
        os.environ["AGENCY_SKILL_ROUTER"] = "0"
        with self.assertRaises(jev_client.RouterUnavailable) as cm:
            self.ask("eval")
        self.assertEqual(cm.exception.reason, "disabled")
        self.assertEqual(calls, [])


SCRIPTS = os.path.dirname(HERE)
FIX = os.path.join(HERE, "fixtures", "jev")


def _load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class WiringTests(unittest.TestCase):
    def test_eval_runner_stops_on_child_rc_75(self):
        ev = _load("ev_budget_t", os.path.join(SCRIPTS, "skill-route-eval.py"))
        os.environ["SKILL_ROUTE_CMD"] = "%s -c 'import sys; sys.exit(75)'" % sys.executable
        self.addCleanup(os.environ.pop, "SKILL_ROUTE_CMD", None)
        cases = [{"id": "c%d" % i, "source": "x", "split": "dev", "task": "t", "expected_skills": ["a"]}
                 for i in range(5)]
        rows = ev.run_cases(cases, "jev", "two-stage", 1)
        self.assertTrue(ev.BUDGET["stopped"])
        self.assertEqual(rows, [])       # the stopped call and everything after it are dropped


class ChildExitTests(BudgetCase):
    """REAL skill-route.py children (fixture skills, stub endpoint): a budget stop must surface as exit 75 and
    live purposes are never refused."""

    def setUp(self):
        BudgetCase.setUp(self)
        import shutil
        import tempfile
        self.fx = tempfile.mkdtemp(prefix="budget-child-")
        self.addCleanup(shutil.rmtree, self.fx, True)
        self.skills = os.path.join(self.fx, "skills")
        shutil.copytree(os.path.join(FIX, "router-skills"), self.skills)
        self.overlay = os.path.join(self.fx, "overlay.json")
        shutil.copy(os.path.join(FIX, "router-overlay.json"), self.overlay)
        open(os.path.join(self.fx, "medium-term.md"), "w").close()

    def child_env(self, purpose):
        env = dict(os.environ)
        env.update(SKILL_ROUTE_STATE_DIR=self.env.state_dir, JEV_USAGE_LOG=self.env.usage_log,
                   JEV_NOTIFY="0", JEV_EMIT="0", PYTHONDONTWRITEBYTECODE="1", AGENCY_SKILL_ROUTER="1",
                   SKILL_ROUTE_SKILLS_DIR=self.skills, SKILL_ROUTE_OVERLAY=self.overlay,
                   SKILL_ROUTE_MEDIUM_TERM=os.path.join(self.fx, "medium-term.md"),
                   CLAUDE_PROJECT_DIR=self.fx)
        env.pop("JEV_PURPOSE", None)
        if purpose:
            env["JEV_PURPOSE"] = purpose
        return env

    def run_child(self, purpose):
        import subprocess
        argv = [sys.executable, os.path.join(SCRIPTS, "skill-route.py"), "--router", "jev", "--no-log",
                "build a react landing page with tailwind"]
        return subprocess.run(argv, env=self.child_env(purpose), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL, timeout=120)

    def test_non_live_child_exits_75_with_stderr_line(self):
        self.credit(balance=0.5)
        p = self.run_child("eval")
        self.assertEqual(p.returncode, 75, p.stderr.decode()[-400:])
        self.assertIn("jev-budget:", p.stderr.decode())
        self.assertEqual(self.stub.count, 0)

    def test_live_child_not_refused(self):
        self.credit(balance=0.5)
        p = self.run_child(None)
        self.assertEqual(p.returncode, 0, p.stderr.decode()[-400:])
        self.assertNotIn("jev-budget: stopped", p.stderr.decode())
        self.assertGreaterEqual(self.stub.count, 1)


class CostTests(BudgetCase):
    """Per-run cost approval (--approved-usd), run cap, orphan self-stop. Offline only."""

    def setUp(self):
        BudgetCase.setUp(self)
        for k in COST_ENV:
            os.environ.pop(k, None)

    def test_refuse_without_flag_exit_75_no_call(self):
        self.credit(balance=5.0)
        r, err = self.err(jev_client.preflight_or_exit, "eval", 10, "x")
        self.assertIsInstance(r, SystemExit)
        self.assertEqual(r.code, 75)
        self.assertIn("--approved-usd", err)
        self.assertEqual(self.stub.count, 0)

    def test_refuse_when_estimate_above_approved(self):
        self.credit(balance=5.0)
        self.row(0.01)
        r, err = self.err(jev_client.preflight_or_exit, "eval", 10, "x", approved_usd=0.05)
        self.assertIsInstance(r, SystemExit)
        self.assertEqual(r.code, 75)
        self.assertIn("est_usd=$0.1000", err)
        self.assertNotIn("JEV_APPROVED_USD", os.environ)

    def test_approved_exports_env_and_prints_estimate(self):
        self.credit(balance=5.0)
        self.row(0.01)
        r, err = self.err(jev_client.preflight_or_exit, "eval", 10, "x", approved_usd=0.2, owner_pid=os.getpid())
        self.assertTrue(r["ok"])
        self.assertIn("est_calls=10", err)
        self.assertIn("balance_after=", err)
        self.assertEqual(float(os.environ["JEV_APPROVED_USD"]), 0.2)
        self.assertTrue(os.environ["JEV_RUN_ID"])
        self.assertEqual(os.environ["JEV_RUN_OWNER_PID"], str(os.getpid()))

    def test_new_run_id_per_run(self):
        a, _ = self.err(jev_client.preflight_or_exit, "eval", 1, "x", approved_usd=1.0)
        first = os.environ["JEV_RUN_ID"]
        os.environ.pop("JEV_APPROVED_USD")
        b, _ = self.err(jev_client.preflight_or_exit, "eval", 1, "x", approved_usd=1.0)
        self.assertNotEqual(first, os.environ["JEV_RUN_ID"])

    def test_dry_run_needs_no_flag_and_exports_nothing(self):
        self.credit(balance=5.0)
        r, err = self.err(jev_client.preflight_or_exit, "eval", 10, "x", dry_run=True)
        self.assertIsInstance(r, dict)
        self.assertIn("est_calls=10", err)
        self.assertIn("DRY-RUN", err)
        self.assertNotIn("REFUSED", err)
        self.assertNotIn("JEV_APPROVED_USD", os.environ)

    def test_live_purposes_exempt(self):
        self.credit(balance=5.0)
        for p in ("skill-route", "spawn-plan"):
            r, _ = self.err(jev_client.preflight_or_exit, p, 10, "x")
            self.assertIsInstance(r, dict, p)
            self.assertIsNone(self.err(jev_client.budget_check, p)[0], p)

    def test_non_live_without_env_is_budget_exhausted_no_call(self):
        r, _ = self.err(self.ask)
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        self.assertEqual(self.stub.count, 0)

    def test_mid_run_stop_at_cap(self):
        self.credit(balance=5.0)
        self.row(0.01)
        os.environ.update(JEV_APPROVED_USD="0.025", JEV_RUN_ID="r1")
        self.assertIsNone(self.err(jev_client.budget_check, "eval")[0])
        self.row(0.01, run_id="r1")
        self.row(0.01, run_id="r1")
        self.row(0.5, run_id="other")
        r, _ = self.err(jev_client.budget_check, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        n = self.stub.count
        r, _ = self.err(self.ask)
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        self.assertEqual(self.stub.count, n)

    def test_run_id_in_usage_row(self):
        os.environ.update(JEV_APPROVED_USD="5", JEV_RUN_ID="rid42")
        self.ask()
        with open(self.env.usage_log) as fh:
            rows = [json.loads(x) for x in fh if x.strip()]
        self.assertTrue(any(x.get("run_id") == "rid42" for x in rows))

    def test_orphan_owner_gone_stops_with_one_line(self):
        import subprocess
        p = subprocess.Popen([sys.executable, "-c", "pass"])
        p.wait()
        os.environ.update(JEV_APPROVED_USD="5", JEV_RUN_OWNER_PID=str(p.pid))
        r, err = self.err(jev_client.budget_check, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        self.assertEqual(err.strip(), "jev-budget: owner pid %d gone" % p.pid)
        r, err = self.err(jev_client.budget_check, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        self.assertEqual(err, "")       # one line per process
        self.assertEqual(self.err(self.ask)[0].__class__, jev_client.OwnerGone)
        self.assertEqual(self.stub.count, 0)

    def test_orphan_ppid_became_1(self):
        from unittest import mock
        os.environ.update(JEV_APPROVED_USD="5", JEV_RUN_OWNER_PID=str(os.getpid()))
        self.assertIsNone(self.err(jev_client.budget_check, "eval")[0])
        with mock.patch.object(os, "getppid", return_value=1):
            r, err = self.err(jev_client.budget_check, "eval")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        self.assertIn("owner pid", err)

    def test_live_purpose_ignores_orphan_and_cap(self):
        os.environ.update(JEV_RUN_OWNER_PID="999999999", JEV_APPROVED_USD="0")
        self.assertIsNone(self.err(jev_client.budget_check, "skill-route")[0])

    def test_find_owner_pid_and_override(self):
        self.assertGreater(jev_client.find_owner_pid(), 0)
        self.assertEqual(jev_client.find_owner_pid(override=4242), 4242)

    def test_add_cost_args(self):
        import argparse
        ap = argparse.ArgumentParser()
        jev_client.add_cost_args(ap)
        a = ap.parse_args(["--approved-usd", "0.5", "--owner-pid", "12", "--dry-run"])
        self.assertEqual((a.approved_usd, a.owner_pid, a.dry_run), (0.5, 12, True))
        a = ap.parse_args([])
        self.assertEqual((a.approved_usd, a.owner_pid, a.dry_run), (None, None, False))
        ap2 = argparse.ArgumentParser()
        ap2.add_argument("--dry-run", action="store_true")
        jev_client.add_cost_args(ap2)       # must not clash with an existing --dry-run

    def test_budget_preflight_accepts_approved_kwarg(self):
        self.credit(balance=5.0)
        r, _ = self.err(jev_client.budget_preflight, "replay", 10, "x")
        self.assertIsInstance(r, jev_client.BudgetExhausted)
        r, _ = self.err(jev_client.budget_preflight, "replay", 10, "x", approved_usd=1.0)
        self.assertTrue(r["ok"])


class CostChildTests(ChildExitTests):
    def setUp(self):
        ChildExitTests.setUp(self)
        for k in COST_ENV:
            os.environ.pop(k, None)

    def test_non_live_child_without_approval_exits_75(self):
        self.credit(balance=5.0)
        p = self.run_child("eval")
        self.assertEqual(p.returncode, 75, p.stderr.decode()[-400:])
        self.assertEqual(self.stub.count, 0)

    def test_non_live_child_with_approval_runs(self):
        self.credit(balance=5.0)
        os.environ["JEV_APPROVED_USD"] = "5"
        p = self.run_child("eval")
        self.assertEqual(p.returncode, 0, p.stderr.decode()[-400:])
        self.assertGreaterEqual(self.stub.count, 1)


class DisabledEntryPointTests(unittest.TestCase):
    """With the router switch off the paid runners print one line, make no call and write nothing."""

    def run_tool(self, script, *args):
        import shutil
        import subprocess
        import tempfile
        home = tempfile.mkdtemp(prefix="budget-off-")
        self.addCleanup(shutil.rmtree, home, True)
        env = dict(os.environ, AGENCY_HOME=home, JEV_ENDPOINT="http://127.0.0.1:9/v1/systemone",
                   JEV_ENV_FILE=os.devnull, PYTHONDONTWRITEBYTECODE="1")
        env.pop("AGENCY_SKILL_ROUTER", None)
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args), env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(os.listdir(home), [], "a disabled run wrote files")
        return p

    def test_drill_and_eval_dry_run_exit_0_when_disabled(self):
        for script in ("jev-drill.py", "skill-route-eval.py"):
            p = self.run_tool(script, "--dry-run")
            self.assertEqual(p.returncode, 0, script)
            self.assertIn("jev-budget:", p.stderr.decode(), script)
            self.assertIn("nothing run", p.stdout.decode(), script)


class DryRunEntryPointTests(BudgetCase):
    """Router on, endpoint is the local stub: --dry-run prints the estimate and exits 0 with no call; a real run
    without --approved-usd exits 75 with no call."""

    def run_tool(self, script, *args):
        import subprocess
        env = dict(os.environ, AGENCY_SKILL_ROUTER="1", PYTHONDONTWRITEBYTECODE="1")
        for k in COST_ENV:
            env.pop(k, None)
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, timeout=60)

    def test_drill_dry_run_and_unapproved(self):
        self.credit(balance=5.0)
        res = os.path.join(self.env.state_dir, "res")
        p = self.run_tool("jev-drill.py", "--dry-run", "--results-dir", res)
        self.assertEqual(p.returncode, 0, p.stderr.decode()[-300:])
        self.assertIn("jev-budget: jev-drill purpose=drill est_calls=1", p.stderr.decode())
        self.assertIn("DRY-RUN", p.stderr.decode())
        p = self.run_tool("jev-drill.py", "--results-dir", res)
        self.assertEqual(p.returncode, 75, p.stderr.decode()[-300:])
        self.assertIn("REFUSED", p.stderr.decode())
        self.assertFalse(os.path.exists(res))
        self.assertEqual(self.stub.count, 0)

    def test_eval_dry_run_and_unapproved(self):
        self.credit(balance=5.0)
        seed = os.path.join(self.env.state_dir, "seed.jsonl")
        with open(seed, "w") as fh:
            fh.write(json.dumps({"id": "t1", "task": "build a react page", "expected_skills": ["frontend"]}) + "\n")
        base = ["--router", "jev", "--seed", seed, "--feedback", os.path.join(self.env.state_dir, "none.jsonl"),
                "--skip-prerules", "--results-dir", os.path.join(self.env.state_dir, "res")]
        p = self.run_tool("skill-route-eval.py", "--dry-run", *base)
        self.assertEqual(p.returncode, 0, p.stderr.decode()[-300:])
        self.assertIn("est_calls=2", p.stderr.decode())          # two-stage: 2 Jev calls per case
        p = self.run_tool("skill-route-eval.py", *base)
        self.assertEqual(p.returncode, 75, p.stderr.decode()[-300:])
        self.assertEqual(self.stub.count, 0)


if __name__ == "__main__":
    unittest.main()
