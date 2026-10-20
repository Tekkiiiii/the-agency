"""Unit tests for scripts/jev-gate-check.py (skill router readiness gate). Temp fixture dirs only; no network, no real logs.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_gate_check*' -v
Every input path is redirected through the JEV_GATE_* env overrides; JEV_GATE_NOW pins the clock.
"""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "jev-gate-check.py")

NOW = "2026-10-20T00:00:00Z"
RESULT_T = "2026-10-10T00:00:00Z"    # result timestamps (staleness is by content hash, not by time)
REAL_SCRIPTS = os.path.dirname(HERE)
AUTO = object()                      # "stamp the fixture's current inputs fingerprint on this result"
ENV_KEYS = ["JEV_GATE_SCRIPTS_DIR", "JEV_GATE_SKILL_ROUTE_RESULTS",
            "JEV_GATE_DRILL_RESULTS", "JEV_GATE_SKILL_ROUTE_SHADOW",
            "JEV_GATE_FEEDBACK", "JEV_FEEDBACK_LOG", "JEV_GATE_SKILL_ROUTE_MODE", "JEV_GATE_NOW",
            "AGENCY_SKILL_ROUTER", "AGENCY_HOME", "CLAUDE_CONFIG_DIR",
            "SKILL_ROUTE_SKILLS_DIR", "SKILL_ROUTE_OVERLAY", "SKILL_ROUTE_STATE_DIR"]


def load():
    spec = importlib.util.spec_from_file_location("jev_gate_check_under_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def epoch(iso):
    return datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()


def load_fingerprint():
    spec = importlib.util.spec_from_file_location("jev_fingerprint_under_test", os.path.join(REAL_SCRIPTS, "jev_fingerprint.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ROUTE_STUB = (
    # fixture skill-route.py: DEFAULT_MODE here, the real menu builder (env-driven) behind load_menu
    'DEFAULT_MODE = "%s"   # eval decides\n'
    'import importlib.util\n'
    '_spec = importlib.util.spec_from_file_location("real_skill_route_for_fixture", %r)\n'
    '_m = importlib.util.module_from_spec(_spec)\n'
    '_spec.loader.exec_module(_m)\n'
    'load_menu = _m.load_menu\n')


def read_doc(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(doc, f)


def write_jsonl(path, recs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def skill_rows(n_ok, n_bad, holdout_ok=0, holdout_bad=0, jev_down=0, n_low=0):
    """Confident (gate=pass) rows: n_ok right, n_bad wrong; n_low extra low_confidence rows (top-1 miss, outside coverage)."""
    rows = [{"id": "d%d" % i, "split": "dev", "top1": True, "gate": "pass"} for i in range(n_ok)]
    rows += [{"id": "m%d" % i, "split": "dev", "top1": False, "gate": "pass"} for i in range(n_bad)]
    rows += [{"id": "ho%d" % i, "split": "holdout", "top1": True, "gate": "pass"} for i in range(holdout_ok)]
    rows += [{"id": "hm%d" % i, "split": "holdout", "top1": False, "gate": "pass"} for i in range(holdout_bad)]
    rows += [{"id": "lc%d" % i, "split": "dev", "top1": False, "gate": "low_confidence"} for i in range(n_low)]
    for i in range(jev_down):
        rows[i]["jev_down"] = True
    return rows


class Fx(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jev-gate-test-")
        self.saved = dict((k, os.environ.get(k)) for k in ENV_KEYS)
        t = self.tmp
        self.scripts = os.path.join(t, "scripts")
        os.makedirs(os.path.join(self.scripts, "skill-route"))
        self.write_route_stub("two-stage")
        for rel, txt in (("jev_client.py", '"""Client."""\nY = 1\n'),
                         (os.path.join("skill-route", "overlay.json"), "{}")):
            with open(os.path.join(self.scripts, rel), "w") as f:
                f.write(txt)
        self.sr = os.path.join(t, "evals", "skill-route")
        self.dr = os.path.join(t, "evals", "drill")
        self.logs = os.path.join(t, "logs")
        os.makedirs(self.logs)
        # minimal VALID skill menu in temp dirs: the gate must never read a real install's skills in tests
        self.skills = os.path.join(t, "skills")
        self.overlay = os.path.join(t, "overlay.json")
        self.state = os.path.join(t, "state")
        self.add_skill("alpha")
        write_json(self.overlay, {"version": 1, "domains": {"dev": "Writing code."},
                                  "skills": {"alpha": {"domain": "dev"}}})
        os.environ.update({
            "SKILL_ROUTE_SKILLS_DIR": self.skills, "SKILL_ROUTE_OVERLAY": self.overlay,
            "SKILL_ROUTE_STATE_DIR": self.state})
        os.environ.update({
            "JEV_GATE_SCRIPTS_DIR": self.scripts, "JEV_GATE_SKILL_ROUTE_RESULTS": self.sr,
            "JEV_GATE_DRILL_RESULTS": self.dr,
            "JEV_GATE_SKILL_ROUTE_SHADOW": os.path.join(self.logs, "sr-shadow.jsonl"),
            "JEV_GATE_FEEDBACK": os.path.join(self.logs, "fb.jsonl"), "JEV_GATE_NOW": NOW})
        os.environ.pop("JEV_GATE_SKILL_ROUTE_MODE", None)
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
        os.environ["AGENCY_HOME"] = t          # any default-root fallback lands in the temp dir
        os.environ.pop("AGENCY_SKILL_ROUTER", None)   # the gate is offline and works with the switch off
        os.environ.pop("JEV_FEEDBACK_LOG", None)
        self.mod = load()

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- fixture writers
    def add_skill(self, name):
        d = os.path.join(self.skills, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w") as f:
            f.write("---\nname: %s\ndescription: Test skill %s.\n---\nbody\n" % (name, name))

    def set_overlay(self, skills, domains=None):
        write_json(self.overlay, {"version": 1, "domains": domains or {"dev": "Writing code."},
                                  "skills": skills})

    def write_route_stub(self, mode):
        with open(os.path.join(self.scripts, "skill-route.py"), "w") as f:
            f.write(ROUTE_STUB % (mode, os.path.join(REAL_SCRIPTS, "skill-route.py")))

    def write_script(self, rel, txt):
        with open(os.path.join(self.scripts, rel), "w") as f:
            f.write(txt)

    def fp_now(self):
        return load_fingerprint().inputs_fingerprint(self.scripts)

    def stamp(self, doc, fp):
        fp = self.fp_now() if fp is AUTO else fp
        if fp is not None:
            doc["inputs_fingerprint"] = fp
        return doc

    def touch_everything(self):
        """Move the mtime of every input file (scripts, overlay, every skill dir file) far into the future."""
        t = epoch("2026-10-30T00:00:00Z")
        for base in (self.scripts, self.skills):
            for root, _d, files in os.walk(base):
                for fn in files:
                    os.utime(os.path.join(root, fn), (t, t))
        os.utime(self.overlay, (t, t))

    def skill_result(self, name="r.json", rows=None, router="jev", mode="two-stage", split="all", date=RESULT_T, fp=AUTO):
        rows = skill_rows(96, 4, 20, 0) if rows is None else rows
        write_json(os.path.join(self.sr, name), self.stamp(
            {"meta": {"date": date, "router": router, "mode": mode, "split": split, "n": len(rows)},
             "summary": {}, "rows": rows}, fp))

    def drill_result(self, name="2026-10-10.json", ts=RESULT_T, route=True, steps=None, overall=True, fp=AUTO):
        steps = ["s1", "s2", "s3", "s4"] if steps is None else steps
        write_json(os.path.join(self.dr, name), self.stamp({"ts": ts, "pass": overall, "tools": {
            "skill-route": {"pass": route, "steps_run": steps}}}, fp))

    def window_days_met(self):
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [{"ts": "2026-10-01T00:00:00Z", "tool": "skill-route", "project": "p",
                                                       "task_id": "T1", "pd_review": "agree"}])

    def window_count_met(self, n=50):
        write_jsonl(os.environ["JEV_GATE_SKILL_ROUTE_SHADOW"],
                    [{"ts": "2026-10-19T00:00:%02dZ" % (i % 60), "spawn_id": "s%d" % i, "actual_skills": ["frontend"]}
                     for i in range(n)])

    def all_pass(self):
        self.skill_result()
        self.drill_result()
        self.window_days_met()

    def check(self):
        res = self.mod.run()
        return res, dict((c["name"], c) for c in res["criteria"])

    def cli(self, *args):
        p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, env=dict(os.environ))
        return p.returncode, p.stdout, p.stderr


class TestGate(Fx):
    def test_all_pass(self):
        self.all_pass()
        res, c = self.check()
        self.assertTrue(res["overall"], res)
        self.assertEqual(sorted(c), ["menu-build", "outage-drill", "shadow-window", "skill-route-gated-accuracy"])
        self.assertTrue(all(x["pass"] for x in c.values()))

    def test_cli_pass_exit0_and_output_format(self):
        self.all_pass()
        rc, out, err = self.cli()
        self.assertEqual(rc, 0, out + err)
        lines = out.strip().splitlines()
        crit_lines = [l for l in lines if l.startswith(("PASS ", "FAIL "))]
        self.assertEqual(len(crit_lines), 4)
        self.assertTrue(all(l.startswith("PASS ") for l in crit_lines))
        self.assertRegex(crit_lines[0], r"^PASS menu-build: menu builds for skill-route\.py "
                                        r"\(1 skills, 0 excluded\) \(.+\) .+")
        self.assertRegex(crit_lines[1], r"^PASS skill-route-gated-accuracy: accuracy 96\.7% \| coverage 100\.0% .*"
                                        r"\(accuracy >= 0\.95 AND coverage >= 0\.7\) .+")
        self.assertEqual(lines[-1], "OVERALL PASS")
        self.assertIn("INFO skill-route holdout top-1: 100.0% (n=20)", out)
        self.assertIn("INFO skill-route raw top-1 (all scored rows, INFO): 96.7%", out)
        self.assertIn("INFO reviewer-agree rate (jev-feedback.jsonl): 100.0% (1 agree / 1 reviewed)", out)

    def test_cli_json(self):
        self.all_pass()
        rc, out, _ = self.cli("--json")
        self.assertEqual(rc, 0)
        doc = json.loads(out)
        self.assertTrue(doc["overall"])
        self.assertEqual(len(doc["criteria"]), 4)
        self.assertEqual(doc["criteria"][0]["name"], "menu-build")
        self.assertTrue(doc["criteria"][0]["pass"])
        self.assertAlmostEqual(doc["info"]["skill_route_coverage"], 1.0)
        self.assertEqual(doc["info"]["shadow"]["pd_agree_rate"], 1.0)

    def test_skill_route_fails_on_accuracy(self):
        self.all_pass()
        self.skill_result(rows=skill_rows(90, 10))      # coverage 100%, accuracy 90%
        res, c = self.check()
        self.assertFalse(res["overall"])
        self.assertFalse(c["skill-route-gated-accuracy"]["pass"])
        self.assertIn("accuracy 90.0% | coverage 100.0%", c["skill-route-gated-accuracy"]["value"])
        rc, out, _ = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("FAIL skill-route-gated-accuracy", out)
        self.assertEqual(out.strip().splitlines()[-1], "OVERALL FAIL")

    def test_skill_route_fails_on_coverage(self):
        self.all_pass()
        # 100% accurate when it answers, but it abstains on 40% of the tasks: coverage 60% < 70%
        self.skill_result(rows=skill_rows(60, 0, n_low=40))
        res, c = self.check()
        crit = c["skill-route-gated-accuracy"]
        self.assertFalse(crit["pass"])
        self.assertFalse(res["overall"])
        self.assertIn("accuracy 100.0% | coverage 60.0%", crit["value"])
        rc, out, _ = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("FAIL skill-route-gated-accuracy: accuracy 100.0% | coverage 60.0%", out)
        # the old metric would have failed this run on raw top-1 (60%); raw top-1 is only INFO now
        self.assertIn("INFO skill-route raw top-1 (all scored rows, INFO): 60.0%", out)

    def test_skill_route_passes_with_low_raw_top1(self):
        self.all_pass()
        # accuracy among confident 96/100, coverage 80% -> raw top-1 = 96/125 = 76.8%: passes, raw is INFO
        self.skill_result(rows=skill_rows(96, 4, n_low=25))
        res, c = self.check()
        self.assertTrue(c["skill-route-gated-accuracy"]["pass"], c["skill-route-gated-accuracy"])
        self.assertAlmostEqual(res["info"]["skill_route_raw_top1"], 96 / 125.0)
        self.assertAlmostEqual(res["info"]["skill_route_coverage"], 0.8)

    def test_coverage_floor_boundary(self):
        self.all_pass()
        self.assertEqual(self.mod.COVERAGE_FLOOR, 0.70)
        self.skill_result(rows=skill_rows(70, 0, n_low=30))        # exactly 70% -> pass
        self.assertTrue(self.check()[1]["skill-route-gated-accuracy"]["pass"])
        self.skill_result(rows=skill_rows(69, 0, n_low=31))        # 69% -> fail
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])
        self.skill_result(rows=skill_rows(699, 0, n_low=301))      # 69.9% must not round up to 70
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])

    def test_skill_route_errored_rows_are_outside_coverage(self):
        self.all_pass()
        rows = skill_rows(70, 0)
        rows += [{"id": "e%d" % i, "split": "dev", "top1": False, "gate": None, "error": "timeout"} for i in range(30)]
        self.skill_result(rows=rows)
        self.assertTrue(self.check()[1]["skill-route-gated-accuracy"]["pass"])   # 70/100
        rows += [{"id": "e99", "split": "dev", "top1": False, "gate": None, "error": "timeout"}]
        self.skill_result(rows=rows)
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])  # 70/101 < 70%

    def test_skill_route_no_gate_pass_rows_fails(self):
        self.all_pass()
        self.skill_result(rows=skill_rows(0, 0, n_low=20))
        c = self.check()[1]["skill-route-gated-accuracy"]
        self.assertFalse(c["pass"])
        self.assertIn("no gate=pass rows", c["value"])

    def test_skill_route_summary_fallback_when_rows_absent(self):
        self.all_pass()
        write_json(os.path.join(self.sr, "r.json"), self.stamp({
            "meta": {"date": RESULT_T, "router": "jev", "mode": "two-stage", "split": "all", "n": 100},
            "summary": {"overall": {"top1": 80.0, "top1_among_gate_pass": 96.0, "gate_pass_rate": 80.0, "n_gate_pass": 80}},
            "rows": []}, AUTO))
        c = self.check()[1]["skill-route-gated-accuracy"]
        self.assertTrue(c["pass"], c)
        self.assertIn("accuracy 96.0% | coverage 80.0%", c["value"])

    def test_skill_route_exact_threshold_passes_and_no_rounding_up(self):
        self.all_pass()
        self.skill_result(rows=skill_rows(95, 5))
        self.assertTrue(self.check()[1]["skill-route-gated-accuracy"]["pass"])
        # 949/1000 would round to 95.0% in the eval summary; the gate must use the raw rows
        self.skill_result(rows=skill_rows(949, 51))
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])

    def test_skill_route_unscored_rows_excluded(self):
        self.all_pass()
        # 95 right + 5 wrong = exactly 95%; adding 10 unscored wrong rows must not move the number, nor the n
        rows = skill_rows(95, 5, 20, 0)
        rows += [{"id": "u%d" % i, "split": "holdout", "top1": False, "gate": "pass", "unscored": True}
                 for i in range(10)]
        self.skill_result(rows=rows)
        res, c = self.check()
        self.assertTrue(c["skill-route-gated-accuracy"]["pass"], c["skill-route-gated-accuracy"])
        self.assertIn("(n=120, gate=pass 120,", c["skill-route-gated-accuracy"]["value"])   # unscored rows are not in coverage
        self.assertEqual(res["info"]["skill_route_unscored_n"], 10)
        self.assertEqual(res["info"]["skill_route_holdout_n"], 20)       # unscored holdout rows not counted
        self.assertEqual(res["info"]["skill_route_holdout_top1"], 1.0)
        # without the exclusion the same file would be 95/130 = 73%: prove the flag is what saves it
        for r in rows:
            r.pop("unscored", None)
        self.skill_result(rows=rows)
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])

    def test_skill_route_expected_none_rows(self):
        self.all_pass()
        rows = skill_rows(95, 5, 20, 0)
        # expected_none rows carrying the scorer's top1 verdict count like any other row
        rows += [{"id": "n1", "split": "dev", "top1": True, "gate": "pass", "expected_none": True, "skills": []}]
        self.skill_result(rows=rows)
        c = self.check()[1]["skill-route-gated-accuracy"]
        self.assertTrue(c["value"].startswith("accuracy 95.9%"), c["value"])   # 116/121 = 95.87%, passes the 95% bar
        self.assertTrue(c["pass"])
        # raw row without a top1 field is recomputed: none returned = correct, a skill returned = miss
        self.assertTrue(self.mod.row_top1({"expected_none": True, "skills": []}))
        self.assertFalse(self.mod.row_top1({"expected_none": True, "skills": ["media-use"]}))
        self.assertFalse(self.mod.row_top1({"expected_none": True, "skills": [], "error": "timeout"}))
        self.assertFalse(self.mod.row_top1({"skills": []}))
        self.assertTrue(self.mod.row_top1({"top1": True, "expected_none": True, "skills": ["x"]}))

    def test_skill_route_outage_rows_fail(self):
        self.all_pass()
        self.skill_result(rows=skill_rows(100, 0, jev_down=3))
        c = self.check()[1]["skill-route-gated-accuracy"]
        self.assertFalse(c["pass"])
        self.assertIn("outage", c["value"])

    def test_skill_route_only_matching_run_counts(self):
        self.all_pass()
        # newer but wrong mode / router / split must be ignored; good result stays the judge
        self.skill_result("a.json", rows=skill_rows(10, 90), mode="flat", date="2026-10-12T00:00:00Z")
        self.skill_result("b.json", rows=skill_rows(10, 90), router="haiku", date="2026-10-12T00:00:00Z")
        self.skill_result("c.json", rows=skill_rows(10, 90), split="dev", date="2026-10-12T00:00:00Z")
        self.assertTrue(self.check()[1]["skill-route-gated-accuracy"]["pass"])

    def test_skill_route_latest_run_wins(self):
        self.all_pass()
        self.skill_result("old.json", rows=skill_rows(100, 0), date="2026-10-08T00:00:00Z")
        self.skill_result("new.json", rows=skill_rows(50, 50), date="2026-10-12T00:00:00Z")
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])

    def test_default_mode_read_from_skill_route_py(self):
        self.write_route_stub("flat")
        self.skill_result()                                   # a two-stage result
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])
        self.skill_result("flat.json", mode="flat")
        self.assertTrue(self.check()[1]["skill-route-gated-accuracy"]["pass"])

    def test_drill_failing_tool(self):
        self.all_pass()
        self.drill_result(route=False)
        c = self.check()[1]["outage-drill"]
        self.assertFalse(c["pass"])
        self.assertIn("skill-route pass=False", c["value"])

    def test_drill_partial_run_does_not_count(self):
        self.all_pass()
        self.drill_result(steps=["s4"])
        c = self.check()[1]["outage-drill"]
        self.assertFalse(c["pass"])
        self.assertIn("partial", c["value"])

    def test_drill_overall_false_fails(self):
        self.all_pass()
        self.drill_result(overall=False)
        self.assertFalse(self.check()[1]["outage-drill"]["pass"])

    def test_drill_ts_with_offset(self):
        self.all_pass()
        self.drill_result(ts="2026-10-10T07:00:00+07:00")   # == 2026-10-10T00:00:00Z
        self.assertTrue(self.check()[1]["outage-drill"]["pass"])

    def test_timestamps_print_as_real_utc(self):
        self.all_pass()
        # local wall time with an offset must be converted, not relabelled "Z"
        self.drill_result(ts="2026-10-10T12:29:15+07:00")
        c = self.check()[1]["outage-drill"]
        self.assertTrue(c["pass"])
        self.assertIn("run 2026-10-10T05:29:15Z)", c["value"])
        self.assertNotIn("12:29:15", c["value"])
        self.assertEqual(self.mod.utc_stamp(self.mod.parse_ts("2026-10-10T01:00:00+07:00")), "2026-10-09T18:00:00Z")
        self.assertEqual(self.mod.utc_stamp(self.mod.parse_ts("2026-10-10T01:00:00Z")), "2026-10-10T01:00:00Z")
        self.assertEqual(self.mod.utc_stamp(self.mod.parse_ts("2026-10-10T01:00:00-05:00")), "2026-10-10T06:00:00Z")
        # same for eval result dates and the shadow-window start
        self.skill_result(date="2026-10-10T07:00:00+07:00")
        self.assertIn("run 2026-10-10T00:00:00Z)", self.check()[1]["skill-route-gated-accuracy"]["value"])

    def promoted(self):
        """Both fingerprint-guarded criteria present and fresh: skill-route eval, drill."""
        self.all_pass()
        res, c = self.check()
        self.assertTrue(res["overall"], res)
        self.assertIn("outage-drill", c)

    def assert_all_stale(self, detail=None):
        res, c = self.check()
        self.assertFalse(res["overall"])
        for n in ("skill-route-gated-accuracy", "outage-drill"):
            self.assertFalse(c[n]["pass"], n)
            self.assertTrue(c[n]["value"].startswith("stale - re-run "), c[n]["value"])
            if detail:
                self.assertIn(detail, c[n]["detail"] or "", n)
        self.assertIn("skill-route-eval.py --router jev --mode two-stage --split all", c["skill-route-gated-accuracy"]["value"])
        self.assertIn("jev-drill.py", c["outage-drill"]["value"])
        self.assertTrue(c["shadow-window"]["pass"])           # window is not an eval; staleness does not apply
        self.assertTrue(c["menu-build"]["pass"])

    def assert_all_fresh(self):
        res, c = self.check()
        self.assertTrue(res["overall"], res)
        for n in ("skill-route-gated-accuracy", "outage-drill"):
            self.assertTrue(c[n]["pass"], c[n])

    def test_proof_routable_skill_description_edit_stales_all(self):
        # PROOF (a): what the router can see of a routable skill changed -> every result is stale
        self.promoted()
        with open(os.path.join(self.skills, "alpha", "SKILL.md"), "w") as f:
            f.write("---\nname: alpha\ndescription: Totally different description now.\n---\nbody\n")
        self.assert_all_stale("inputs changed since the run (code or routable menu)")

    def test_proof_excluded_skill_and_touched_files_stay_fresh(self):
        # PROOF (b): a new excluded skill + overlay exclude entry, and every input file touched -> still fresh
        self.promoted()
        self.add_skill("beta")
        self.set_overlay({"alpha": {"domain": "dev"}, "beta": {"exclude": "internal"}})
        self.touch_everything()
        self.assert_all_fresh()

    def test_overlay_trigger_change_stales(self):
        # triggers live in the overlay (W6a): changing a routable skill's overlay triggers changes the menu fingerprint
        self.promoted()
        self.set_overlay({"alpha": {"domain": "dev", "triggers": ["brand new trigger"]}})
        self.assert_all_stale()

    def test_catalog_trigger_change_is_ignored(self):
        # the router no longer reads catalog triggers: a catalog-only trigger change leaves every result fresh
        self.promoted()
        write_json(os.path.join(self.skills, "INDEX.catalog.json"),
                   {"skills": [{"name": "alpha", "description": "x", "triggers": ["brand new trigger"]}]})
        self.assert_all_fresh()

    def test_overlay_domain_hint_change_stales(self):
        self.promoted()
        self.set_overlay({"alpha": {"domain": "dev", "hint": "prefer me"}})
        self.assert_all_stale()

    def test_code_change_in_jev_client_stales(self):
        self.promoted()
        self.write_script("jev_client.py", '"""Client."""\nY = 2\n')
        self.assert_all_stale()

    def test_code_change_in_skill_route_stales(self):
        self.promoted()
        with open(os.path.join(self.scripts, "skill-route.py"), "a") as f:
            f.write("EXTRA = 1\n")
        self.assert_all_stale()

    def test_comment_docstring_and_format_only_change_stays_fresh(self):
        self.promoted()
        self.write_script("skill-route.py", '"""A completely rewritten module docstring."""\n# new comment\n\n\nDEFAULT_MODE = "two-stage"   # eval decides\nimport importlib.util\n_spec = importlib.util.spec_from_file_location("real_skill_route_for_fixture", %r)\n_m = importlib.util.module_from_spec(_spec)\n_spec.loader.exec_module(_m)\nload_menu = _m.load_menu\n' % os.path.join(REAL_SCRIPTS, "skill-route.py"))
        self.write_script("jev_client.py", '# header comment\n"""Client, reworded."""\nY = 1\n')
        self.touch_everything()
        self.assert_all_fresh()

    def test_result_without_fingerprint_is_stale_with_rerun_hint(self):
        self.all_pass()
        for d in (self.sr, self.dr):
            for f in os.listdir(d):
                doc = read_doc(os.path.join(d, f))
                doc.pop("inputs_fingerprint")
                write_json(os.path.join(d, f), doc)
        self.assert_all_stale("result has no inputs_fingerprint (pre-content-hash result)")
        # null counts as missing
        self.skill_result(fp=None)
        doc = read_doc(os.path.join(self.sr, "r.json"))
        doc["inputs_fingerprint"] = None
        write_json(os.path.join(self.sr, "r.json"), doc)
        c = self.check()[1]["skill-route-gated-accuracy"]
        self.assertTrue(c["value"].startswith("stale - re-run "))

    def test_uncomputable_fingerprint_fails_without_crash(self):
        self.promoted()
        with open(self.overlay, "w") as f:
            f.write("{not json")
        res, c = self.check()
        self.assertFalse(res["overall"])
        for n in ("skill-route-gated-accuracy", "outage-drill"):
            self.assertFalse(c[n]["pass"], n)
            self.assertIn("cannot fingerprint inputs: ", c[n]["value"], n)
        self.assertFalse(c["menu-build"]["pass"])
        rc, out, err = self.cli()
        self.assertEqual(rc, 1, out + err)
        self.assertNotIn("Traceback", err)

    def test_json_info_carries_inputs_fingerprint(self):
        self.promoted()
        rc, out, err = self.cli("--json")
        info = json.loads(out)["info"]
        self.assertEqual(info["inputs_fingerprint"], self.fp_now())
        self.assertNotIn("newest_change", info)
        self.assertNotIn("newest_change_mtime", info)

    def test_window_met_by_count_before_seven_days(self):
        self.skill_result(); self.drill_result()
        self.window_count_met(50)
        c = self.check()[1]["shadow-window"]
        self.assertTrue(c["pass"], c)
        self.assertIn("50 gated tasks", c["value"])
        self.assertIn("met by count", c["value"])

    def test_window_not_met_49_tasks_1_day(self):
        self.skill_result(); self.drill_result()
        self.window_count_met(49)
        res, c = self.check()
        self.assertFalse(c["shadow-window"]["pass"])
        self.assertFalse(res["overall"])

    def test_window_met_by_days_with_one_record(self):
        self.skill_result(); self.drill_result()
        self.window_days_met()
        c = self.check()[1]["shadow-window"]
        self.assertTrue(c["pass"])
        self.assertIn("met by days", c["value"])

    def test_window_exactly_seven_days(self):
        self.skill_result(); self.drill_result()
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [{"ts": "2026-10-13T00:00:00Z", "tool": "skill-route", "task_id": "x"}])
        self.assertTrue(self.check()[1]["shadow-window"]["pass"])
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [{"ts": "2026-10-13T00:00:01Z", "tool": "skill-route", "task_id": "x"}])
        self.assertFalse(self.check()[1]["shadow-window"]["pass"])

    def test_window_start_is_earliest_across_both_files(self):
        self.skill_result(); self.drill_result()
        write_jsonl(os.environ["JEV_GATE_SKILL_ROUTE_SHADOW"], [{"ts": "2026-10-18T00:00:00Z", "actual_skills": ["a"]}])
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [{"ts": "2026-10-18T00:00:00Z", "tool": "skill-route", "task_id": "y"}])
        self.assertFalse(self.check()[1]["shadow-window"]["pass"])
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [{"ts": "2026-10-18T00:00:00Z", "tool": "skill-route", "task_id": "y"},
                                                      {"ts": "2026-10-02T00:00:00Z", "tool": "skill-route", "task_id": "z"}])
        self.assertTrue(self.check()[1]["shadow-window"]["pass"])

    def test_gate_deny_rows_do_not_open_or_move_the_window(self):
        # F4: jev-spawn-gate appends gate_deny rows to the skill-route shadow log; they are not routed tasks.
        self.skill_result(); self.drill_result()
        write_jsonl(os.environ["JEV_GATE_SKILL_ROUTE_SHADOW"],
                    [{"ts": "2026-09-01T00:00:00Z", "event": "gate_deny", "rule": "x", "spawner_skills": ["a"]}])
        res, c = self.check()
        self.assertFalse(c["shadow-window"]["pass"])
        self.assertIn("no shadow records", c["shadow-window"]["value"])
        write_jsonl(os.environ["JEV_GATE_SKILL_ROUTE_SHADOW"],
                    [{"ts": "2026-09-01T00:00:00Z", "event": "gate_deny", "rule": "x", "spawner_skills": ["a"]},
                     {"ts": "2026-10-18T00:00:00Z", "actual_skills": ["a"]}])
        res, c = self.check()
        self.assertFalse(c["shadow-window"]["pass"])
        self.assertEqual(res["info"]["shadow"]["window_start"], "2026-10-18T00:00:00Z")

    def test_sample_records_ignored(self):
        self.skill_result(); self.drill_result()
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [{"ts": "2026-09-01T00:00:00Z", "tool": "skill-route", "sample": True,
                                                       "pd_review": "disagree"}])
        res, c = self.check()
        self.assertFalse(c["shadow-window"]["pass"])
        self.assertIn("no shadow records", c["shadow-window"]["value"])
        self.assertEqual(res["info"]["shadow"]["pd_reviewed"], 0)

    def test_task_count_definition_and_dedupe(self):
        self.skill_result(); self.drill_result()
        write_jsonl(os.environ["JEV_GATE_SKILL_ROUTE_SHADOW"], [
            {"ts": "2026-10-18T00:00:00Z", "spawn_id": "s1", "actual_skills": ["a"]},
            {"ts": "2026-10-18T00:00:01Z", "spawn_id": "s2", "actual_skills": []}])          # no actual: not counted
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [
            {"ts": "2026-10-18T00:00:05Z", "tool": "skill-route", "task_id": "s1", "pd_review": "agree"},                   # dup
            {"ts": "2026-10-18T00:00:06Z", "tool": "skill-route", "task_id": "s7", "pd_review": "agree"},
            {"ts": "2026-10-18T00:00:07Z", "tool": "skill-route", "task_id": "s8", "pd_review": "disagree"}])
        res, _ = self.check()
        sh = res["info"]["shadow"]
        self.assertEqual((sh["tasks_skill_route"], sh["tasks_feedback_extra"]), (1, 2))
        self.assertEqual(sh["gated_tasks"], 3)
        self.assertEqual((sh["pd_agree"], sh["pd_reviewed"]), (2, 3))
        self.assertAlmostEqual(sh["pd_agree_rate"], 2 / 3.0)

    def test_pd_agree_rate_is_informational_only(self):
        self.all_pass()
        write_jsonl(os.environ["JEV_GATE_FEEDBACK"], [
            {"ts": "2026-10-01T00:00:00Z", "tool": "skill-route", "project": "p", "task_id": "T%d" % i, "pd_review": "disagree"}
            for i in range(5)])
        res, _ = self.check()
        self.assertTrue(res["overall"])
        self.assertEqual(res["info"]["shadow"]["pd_agree_rate"], 0.0)


class TestMenuBuild(Fx):
    """menu-build: a skill dir without an overlay entry kills the router (MenuError); the gate must say so."""

    FIX = "add overlay entries: python3 " + os.path.join(REAL_SCRIPTS, "skill-route-overlay-add.py")

    def mb(self):
        res, c = self.check()
        return res, c["menu-build"]

    def test_pass_reports_counts_and_overlay_source(self):
        self.all_pass()
        self.add_skill("beta")
        self.set_overlay({"alpha": {"domain": "dev"}, "beta": {"exclude": "internal"}})
        res, c = self.mb()
        self.assertTrue(c["pass"], c)
        self.assertEqual(c["value"], "menu builds for skill-route.py (1 skills, 1 excluded)")
        # live-state independence: the source is the TEMP overlay, never the shipped scripts/skill-route/overlay.json
        self.assertEqual(c["source"], self.overlay)
        self.assertNotIn("skill-route/overlay.json", c["source"])
        self.assertTrue(res["overall"])
        # the menu cache went to the temp state dir, not a real install
        self.assertTrue(os.path.isfile(os.path.join(self.state, "skill-route-menu.json")))

    def test_criterion_is_first(self):
        self.all_pass()
        self.assertEqual(self.check()[0]["criteria"][0]["name"], "menu-build")

    def test_fail_names_skills_and_fix_and_fails_overall(self):
        self.all_pass()
        self.add_skill("newone")
        self.add_skill("another")        # neither is in the overlay
        res, c = self.mb()
        self.assertFalse(c["pass"])
        self.assertFalse(res["overall"])
        self.assertIn("no overlay entry: another, newone", c["value"])
        self.assertIn(self.FIX + " <name>", c["value"])
        self.assertIn("skill-route.py", c["value"])
        self.assertEqual(c["value"].count("no overlay entry"), 1)
        self.assertNotIn("\n", c["value"])
        self.assertEqual(c["source"], self.overlay)
        rc, out, err = self.cli()
        self.assertEqual(rc, 1, out + err)
        self.assertNotIn("Traceback", err)
        line = [l for l in out.splitlines() if l.startswith("FAIL menu-build: ")]
        self.assertEqual(len(line), 1, out)
        self.assertIn("no overlay entry: another, newone", line[0])
        self.assertEqual(out.strip().splitlines()[-1], "OVERALL FAIL")

    def test_fail_value_is_not_truncated_for_many_skills(self):
        self.all_pass()
        names = ["skill%02d" % i for i in range(25)]
        for n in names:
            self.add_skill(n)
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("no overlay entry: " + ", ".join(names), c["value"])

    def test_other_problems_are_kept_and_collapsed(self):
        self.all_pass()
        self.set_overlay({"alpha": {"domain": "nope"}})
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("unknown domain", c["value"])
        self.assertIn("alpha", c["value"])
        self.assertNotIn("\n", c["value"])

    def test_skill_route_path_only_failure_is_reported(self):
        self.all_pass()
        real = self.mod._load_module

        def fake(filename, tag):
            if filename != "skill-route.py":
                return real(filename, tag)

            class SR:
                def load_menu(self, rebuild=False):
                    raise ValueError("boom")
            return SR()
        self.mod._load_module = fake
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("skill-route.py: ", c["value"])
        self.assertIn("boom", c["value"])

    def test_both_paths_called_with_rebuild_true(self):
        self.all_pass()
        real = self.mod._load_module
        calls = []

        def spy(filename, tag):
            mod = real(filename, tag)
            if filename == "skill-route.py":
                orig = mod.load_menu
                mod.load_menu = lambda rebuild=False: (calls.append(("skill-route", rebuild)), orig(rebuild=rebuild))[1]
            return mod
        self.mod._load_module = spy
        self.assertTrue(self.mb()[1]["pass"])
        self.assertEqual(calls[0], ("skill-route", True))

    def test_module_names_are_unique_per_load(self):
        self.all_pass()
        self.mod.check_menu_build()
        self.mod.check_menu_build()       # a second load in the same process must not collide
        self.assertTrue(self.mb()[1]["pass"])

    def test_corrupt_overlay_is_fail_not_crash(self):
        self.all_pass()
        with open(self.overlay, "w") as f:
            f.write("{not json")
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("cannot read overlay", c["value"])
        rc, out, err = self.cli()
        self.assertEqual(rc, 1, out + err)
        self.assertNotIn("Traceback", err)

    def test_non_menuerror_exception_is_fail_not_crash(self):
        self.all_pass()
        real = self.mod._load_module

        def boom(filename, tag):
            if filename == "skill-route.py":
                raise ImportError("cannot import jev_client")
            return real(filename, tag)
        self.mod._load_module = boom
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("ImportError", c["value"])
        self.assertIn("cannot import jev_client", c["value"])

    def test_system_exit_during_build_is_fail_not_crash(self):
        # a sys.exit() at module import time (SystemExit is not an Exception) must FAIL the criterion
        self.all_pass()
        real = self.mod._load_module

        def exits(filename, tag):
            if filename == "skill-route.py":
                raise SystemExit(3)
            return real(filename, tag)
        self.mod._load_module = exits
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("SystemExit", c["value"])
        self.assertTrue(c["value"].startswith("menu build FAILED"), c["value"])

    def test_system_exit_in_both_builds_is_fail_not_crash(self):
        self.all_pass()
        self.mod._load_module = lambda filename, tag: (_ for _ in ()).throw(SystemExit("bye"))
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("SystemExit", c["value"])

    def test_missing_entries_and_other_problems_print_both_fixes(self):
        self.all_pass()
        self.add_skill("orphan")                         # no overlay entry
        self.set_overlay({"alpha": {"domain": "nope"}})  # plus an unknown domain
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("no overlay entry: orphan", c["value"])
        self.assertIn("unknown domain", c["value"])
        self.assertIn(self.FIX + " <name>", c["value"])                  # add-entries fix
        self.assertIn("fix the overlay", c["value"])                     # generic overlay fix
        self.assertIn("--rebuild-menu", c["value"])
        self.assertNotIn("\n", c["value"])

    def test_only_missing_entries_prints_only_the_add_fix(self):
        self.all_pass()
        self.add_skill("orphan")
        c = self.mb()[1]
        self.assertIn(self.FIX + " <name>", c["value"])
        self.assertNotIn("fix the overlay", c["value"])

    def test_only_other_problems_prints_only_the_generic_fix(self):
        self.all_pass()
        self.set_overlay({"alpha": {"domain": "nope"}})
        c = self.mb()[1]
        self.assertIn("fix the overlay", c["value"])
        self.assertNotIn("add overlay entries", c["value"])

    def test_module_load_failure_with_broken_script_dir_is_fail(self):
        self.all_pass()
        self.mod._load_module = lambda filename, tag: (_ for _ in ()).throw(OSError("no such file"))
        c = self.mb()[1]
        self.assertFalse(c["pass"])
        self.assertIn("no such file", c["value"])

    def test_missing_skills_dir_is_empty_menu_fail(self):
        self.all_pass()
        os.environ["SKILL_ROUTE_SKILLS_DIR"] = os.path.join(self.tmp, "does-not-exist")
        self.set_overlay({})
        self.assertFalse(self.mb()[1]["pass"])

    def test_not_subject_to_staleness_guard(self):
        self.all_pass()
        with open(os.path.join(self.scripts, "skill-route.py"), "a") as f:   # a real code change: every eval/drill result is now stale
            f.write("EXTRA = 99\n")
        res, c = self.check()
        self.assertTrue(c["menu-build"]["pass"])
        self.assertFalse(c["outage-drill"]["pass"])

    def test_loads_from_gate_dir_not_from_scripts_dir_env(self):
        # JEV_GATE_SCRIPTS_DIR points at a stub whose skill-route.py only holds DEFAULT_MODE: must not be used for the build
        self.all_pass()
        self.assertTrue(self.mb()[1]["pass"])
        self.assertEqual(self.mod.GATE_DIR, os.path.dirname(SCRIPT))

    def test_json_contains_menu_build_failure(self):
        self.all_pass()
        self.add_skill("orphan")
        rc, out, err = self.cli("--json")
        self.assertEqual(rc, 1, out + err)
        doc = json.loads(out)
        self.assertFalse(doc["overall"])
        mb = [c for c in doc["criteria"] if c["name"] == "menu-build"]
        self.assertEqual(len(mb), 1)
        self.assertFalse(mb[0]["pass"])
        self.assertIn("no overlay entry: orphan", mb[0]["value"])
        self.assertEqual(mb[0]["source"], self.overlay)


class TestMissingInputs(Fx):
    def test_everything_missing_is_fail_not_crash(self):
        res, c = self.check()          # no results dirs, no logs
        self.assertFalse(res["overall"])
        # menu-build is computed live from the (valid) temp menu, so it passes; every result-file criterion fails
        self.assertTrue(c.pop("menu-build")["pass"])
        self.assertTrue(all(not x["pass"] for x in c.values()))
        rc, out, err = self.cli()
        self.assertEqual(rc, 1, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(out.strip().splitlines()[-1], "OVERALL FAIL")

    def test_corrupt_result_files_are_skipped(self):
        self.all_pass()
        for d in (self.sr, self.dr):
            with open(os.path.join(d, "zzz-corrupt.json"), "w") as f:
                f.write("{not json")
        with open(os.environ["JEV_GATE_FEEDBACK"], "a") as f:
            f.write("garbage line\n")
        self.assertTrue(self.check()[0]["overall"])

    def test_empty_results_dir_fails(self):
        self.all_pass()
        for d in (self.sr, self.dr):
            shutil.rmtree(d)
            os.makedirs(d)
        res, c = self.check()          # no eval and no drill result: both criteria FAIL with a run hint, never a crash
        self.assertFalse(res["overall"])
        self.assertFalse(c["skill-route-gated-accuracy"]["pass"])
        self.assertFalse(c["outage-drill"]["pass"])
        self.assertIn("run:", c["skill-route-gated-accuracy"]["value"] + (c["skill-route-gated-accuracy"]["detail"] or ""))

    def test_missing_staleness_reference_files_exit_2(self):
        shutil.rmtree(self.scripts)
        rc, out, err = self.cli()
        self.assertEqual(rc, 2, out + err)
        self.assertIn("input error", err)

    def test_unparseable_default_mode_exit_2(self):
        with open(os.path.join(self.scripts, "skill-route.py"), "w") as f:
            f.write("X = 1\n")
        self.assertEqual(self.cli()[0], 2)

    def test_bad_args_exit_2(self):
        self.assertEqual(self.cli("--nope")[0], 2)

    def test_bad_now_exit_2(self):
        os.environ["JEV_GATE_NOW"] = "yesterday"
        self.assertEqual(self.cli()[0], 2)

    def test_mode_env_override(self):
        self.all_pass()
        os.environ["JEV_GATE_SKILL_ROUTE_MODE"] = "flat"
        self.assertFalse(self.check()[1]["skill-route-gated-accuracy"]["pass"])


class TestFingerprint(Fx):
    """jev_fingerprint: what counts toward the inputs fingerprint and what does not."""

    def digest(self, src):
        p = os.path.join(self.tmp, "m.py")
        with open(p, "w") as f:
            f.write(src)
        return load_fingerprint().code_digest(p)

    def test_code_digest_ignores_comments_docstrings_format_and_mtime(self):
        base = self.digest('"""Mod."""\nclass A:\n    """Doc."""\n    def f(self):\n        """f doc."""\n        return 1\n')
        same = self.digest('# c\n"""Other module doc."""\nclass A:\n    """Changed."""\n    def f(self):\n        # why\n        """x"""\n        return  1  # t\n')
        self.assertEqual(base, same)

    def test_code_digest_changes_on_code(self):
        a = self.digest("def f():\n    return 1\n")
        self.assertNotEqual(a, self.digest("def f():\n    return 2\n"))
        self.assertNotEqual(a, self.digest("def g():\n    return 1\n"))
        # a non-docstring string statement is code, not a docstring
        self.assertNotEqual(self.digest("X = 1\n'a'\n"), self.digest("X = 1\n"))

    def test_code_digest_unparseable_falls_back_to_bytes(self):
        a, b = self.digest("def (:\n"), self.digest("def (:  \n")
        self.assertNotEqual(a, b)
        self.assertEqual(a, self.digest("def (:\n"))

    def menu(self, **kw):
        m = {"skills": {"b": {"description": "d", "triggers": ["t"], "domain": "dev", "also": [], "hint": ""},
                        "a": {"description": "d", "triggers": [], "domain": "dev", "also": [], "hint": ""}},
             "domains": {"dev": "Code."}, "vi_map": {}, "en_only": [], "excluded": {"x": "internal"},
             "built_at": "t1", "sig": "s1"}
        m.update(kw)
        return m

    def test_menu_digest_ignores_built_at_sig_excluded(self):
        fp = load_fingerprint()
        a = fp.menu_digest(self.menu())
        b = fp.menu_digest(self.menu(built_at="t2", sig="s2", excluded={"y": "z", "x": "internal"}))
        self.assertEqual(a, b)

    def test_menu_digest_sees_routable_changes(self):
        fp = load_fingerprint()
        base = fp.menu_digest(self.menu())
        m = self.menu()
        m["skills"]["a"]["triggers"] = ["new"]
        self.assertNotEqual(base, fp.menu_digest(m))
        self.assertNotEqual(base, fp.menu_digest(self.menu(domains={"dev": "Other."})))
        self.assertNotEqual(base, fp.menu_digest(self.menu(vi_map={"a": "b"})))
        self.assertNotEqual(base, fp.menu_digest(self.menu(en_only=["a"])))

    def test_inputs_fingerprint_format_and_missing_file(self):
        fp = load_fingerprint()
        a = fp.inputs_fingerprint(self.scripts)
        self.assertRegex(a, r"^sha256:[0-9a-f]{64}$")
        os.remove(os.path.join(self.scripts, "jev_client.py"))
        self.assertNotEqual(a, fp.inputs_fingerprint(self.scripts))        # "missing" is a value, not a crash

    def test_fingerprint_fields_never_raise(self):
        fp = load_fingerprint()
        ok = fp.fingerprint_fields(self.scripts)
        self.assertEqual(ok, {"inputs_fingerprint": fp.inputs_fingerprint(self.scripts)})
        with open(self.overlay, "w") as f:
            f.write("{not json")
        bad = fp.fingerprint_fields(self.scripts)
        self.assertIsNone(bad["inputs_fingerprint"])
        self.assertIn("cannot read overlay", bad["inputs_fingerprint_error"])


class TestRealFiles(unittest.TestCase):
    def test_real_default_mode_parses(self):
        saved = dict((k, os.environ.pop(k, None)) for k in ENV_KEYS)
        try:
            self.assertIn(load().default_mode(), ("two-stage", "flat"))
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
