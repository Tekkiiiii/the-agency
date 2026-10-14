"""Tests for the automatic spawn RECORDER in scripts/skill-route.py (shadow_run), the route cache / route_id wiring
and gate_route. NO network (jev_stub), temp dirs only: every log, state dir, medium-term file and project dir is an
env override inside tr.RouterEnv, so nothing here can touch the real ~/.claude/logs or ~/.claude/state.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_recorder*' -v
"""
import contextlib
import io
import json
import os
import sys
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
import test_jev_router as tr  # noqa: E402  (RouterEnv, run_main, sr)
import jev_spawn  # noqa: E402

sr = tr.sr
RouterEnv = tr.RouterEnv
J = ["frontend", "tailwind"]


def put_cache(skills=None, gate="pass", router="jev", confidential=False, none_fired=False, jev_down=False):
    """A deterministic route cache entry (no Jev call); returns the route id."""
    rid = jev_spawn.cache_put({"skills": list(J if skills is None else skills), "gate": gate, "router": router,
                               "domain": "frontend-ui", "jev_down": jev_down},
                              {"role": "exec", "none_fired": none_fired, "confidential": confidential})
    assert rid
    return rid


def payload(prompt, **kw):
    d = {"spawn_id": "sp-1", "subagent_type": "general-purpose", "parent_agent": "some-pd",
         "description": "Build the landing page", "prompt": prompt}
    d.update(kw)
    return json.dumps(d)


class RecEnv(RouterEnv):
    """RouterEnv + a counting feedback module wrapper (real append_spawn_record, counted no-op reconcile)."""

    def __enter__(self):
        super(RecEnv, self).__enter__()
        self.real = sr._feedback_module()
        assert self.real is not None
        self.reconciles = []
        self.appended = []
        outer = self

        def append(rec, path=None):
            errs = outer.real.append_spawn_record(rec, path)
            outer.appended.append((rec, errs))
            return errs

        self.fake = types.SimpleNamespace(append_spawn_record=append, validate_record=self.real.validate_record,
                                          reconcile=lambda *a, **k: self.reconciles.append(1) or {})
        self._saved = sr._feedback_module
        sr._feedback_module = lambda: self.fake
        return self

    def __exit__(self, *exc):
        sr._feedback_module = self._saved
        return super(RecEnv, self).__exit__(*exc)

    def record(self, raw):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            sr.shadow_run(raw)
        assert (out.getvalue(), err.getvalue()) == ("", ""), (out.getvalue(), err.getvalue())

    def valid(self, rec):
        return self.real.validate_record(rec)


class RouteIdTests(unittest.TestCase):
    def test_route_returns_route_id_cache_and_logs(self):
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            res = sr.route("build a responsive landing page in tailwind", log=True)
            self.assertEqual(list(res.keys()), tr.CONTRACT_KEYS)
            self.assertEqual(res["route_id"], res["route_id"].lower())
            self.assertRegex(res["route_id"], r"^[0-9a-f]{8}$")
            path = os.path.join(e.state_dir, "jev-route-cache", res["route_id"] + ".json")
            self.assertTrue(os.path.exists(path))
            entry = tr.read_json(path)
            self.assertEqual(entry["skills"], res["skills"])
            self.assertEqual(entry["router"], "jev")
            self.assertEqual(entry["role"], None)
            self.assertNotIn("landing", json.dumps(entry))          # NO task text in the cache
            self.assertEqual(e.decisions()[-1]["route_id"], res["route_id"])

    def test_cache_written_even_without_log(self):
        with RouterEnv() as e:
            res = sr.route("build a responsive landing page in tailwind", log=False)
            self.assertTrue(res["route_id"])
            self.assertEqual(e.decisions(), [])
            self.assertIsNotNone(jev_spawn.cache_get(res["route_id"]))

    def test_cli_json_has_route_id_with_no_log(self):
        with RouterEnv() as e:
            rc, out, err = tr.run_main(["--no-log", "build a responsive landing page in tailwind"])
            self.assertEqual(rc, 0)
            res = json.loads(out)
            self.assertEqual(list(res.keys()), tr.CONTRACT_KEYS)
            self.assertRegex(res["route_id"], r"^[0-9a-f]{8}$")
            self.assertTrue(os.path.exists(os.path.join(e.state_dir, "jev-route-cache", res["route_id"] + ".json")))

    def test_explicit_passthrough_and_grep_also_get_route_id(self):
        with RouterEnv() as e:
            r1 = sr.route("/frontend build X", log=False)
            self.assertEqual(r1["router"], "passthrough")
            self.assertTrue(r1["route_id"])
            r2 = sr.route("build X", router="grep", log=False)
            self.assertTrue(r2["route_id"])
            self.assertNotEqual(r1["route_id"], r2["route_id"])
            self.assertEqual(e.stub.count, 0)

    def test_missing_jev_spawn_gives_empty_route_id(self):
        with RouterEnv():
            saved = sys.modules.get("jev_spawn")
            sys.modules["jev_spawn"] = None      # `import jev_spawn` raises ImportError
            try:
                res = sr.route("build a responsive landing page in tailwind", log=False)
            finally:
                sys.modules["jev_spawn"] = saved
            self.assertEqual(res["route_id"], "")
            self.assertEqual(list(res.keys()), tr.CONTRACT_KEYS)

    def test_cache_write_failure_gives_empty_route_id(self):
        with RouterEnv() as e:
            open(os.path.join(e.state_dir, "jev-route-cache"), "w").close()   # a FILE where the dir should be
            res = sr.route("build a responsive landing page in tailwind", log=False)
            self.assertEqual(res["route_id"], "")


class GateRouteTests(unittest.TestCase):
    PROMPT = ("Skills: /frontend, tailwind. You are an Exec.\n"
              "Jev[r=0a1b2c3d]: modify — Jev missed the Tailwind side\n"
              "Task: build a responsive landing page with /frontend.")

    def test_gate_route_disables_passthrough_and_is_live(self):
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            out = sr.gate_route(self.PROMPT, "Build the landing page", "general-purpose", "some-pd")
            self.assertEqual(len(out), 3)
            res, meta, actual = out
            self.assertEqual(actual, ["frontend", "tailwind"])
            self.assertEqual(res["router"], "jev")                    # passthrough disabled: the /frontend token
            self.assertGreater(e.stub.count, 0)                       # did NOT short-circuit
            self.assertRegex(res["route_id"], r"^[0-9a-f]{8}$")
            self.assertIsNotNone(jev_spawn.cache_get(res["route_id"]))
            self.assertIsInstance(meta, dict)
            self.assertEqual(meta["role"], "exec")
            state = e.stub.requests[0]["json"]["state"]
            self.assertNotIn("Skills:", state)
            self.assertNotIn("Jev[r=", state)
            self.assertNotIn("/frontend", state)
            self.assertIn("landing page", state)
            jev = [u for u in e.usage_records() if u["router"] == "jev"]
            self.assertTrue(jev and all(u["shadow"] is False for u in jev))   # LIVE usage accounting
            self.assertEqual(e.decisions(), [])                       # gate writes no decision log

    def test_gate_route_role_for_lead(self):
        with RouterEnv() as e:
            res, meta, actual = sr.gate_route("Task: coordinate the work", "x", "coord", "pd")
            self.assertEqual(meta["role"], "lead")

    def test_spawn_text_is_shared_and_shadow_identical_without_line(self):
        with RouterEnv():
            names = list(sr.load_menu()["skills"])
            prompt = "Skills: /frontend, tailwind\nBuild a responsive landing page with /frontend."
            full, text = sr._spawn_text(prompt, "Build the landing page", names)
            old_body = sr._SKILLS_CLAUSE_RE.sub("", prompt)
            old_full = sr.strip_slash_tokens("Build the landing page" + "\n" + old_body, names).strip()
            self.assertEqual((full, text), (old_full, sr._routed_text(old_full)[:sr.SHADOW_TEXT_CAP]))
            full2, _ = sr._spawn_text(prompt + "\nJev[r=0a1b2c3d]: accept", "Build the landing page", names)
            self.assertEqual(full2, full)                              # the Jev line never reaches the router


class RecorderTests(unittest.TestCase):
    def test_cache_hit_no_jev_call_pre_consult(self):
        with RecEnv() as e:
            rid = put_cache()
            e.stub.reset()
            e.record(payload("Skills: /frontend, /tailwind\nJev[r=%s]: accept\nTask: build a landing page" % rid))
            self.assertEqual(e.stub.count, 0)
            (fb,) = e.feedbacks()
            self.assertEqual(e.valid(fb), [])
            self.assertEqual((fb["consult"], fb["task_id"], fb["route_id"]), ("pre", rid, rid))
            self.assertEqual((fb["spawn_verdict"], fb["verdict_source"], fb["verdict_raw"]),
                             ("accept", "explicit", "accept"))
            self.assertEqual((fb["pd_review"], fb["tool"], fb["source"]), ("agree", "skill-route", "spawn"))
            self.assertEqual((fb["jev_verdict"], fb["jev_skills"], fb["spawner_skills"]),
                             ("frontend", J, J))
            self.assertEqual((fb["gate"], fb["router"], fb["role"]), ("pass", "jev", "exec"))
            self.assertEqual((fb["outcome"], fb["outcome_mismatch"]), (None, None))
            self.assertEqual((fb["spawn_id"], fb["subagent_type"], fb["parent_agent"]),
                             ("sp-1", "general-purpose", "some-pd"))
            self.assertEqual(fb["project"], "global")
            self.assertIn("landing page", fb["task_text"])
            (sh,) = e.shadows()                                         # shadow record from the cached result
            self.assertEqual((sh["router_skills"], sh["router"], sh["gate"], sh["domain"]),
                             (J, "jev", "pass", "frontend-ui"))
            self.assertEqual((sh["route_id"], sh["verdict"], sh["verdict_source"]), (rid, "accept", "explicit"))
            self.assertEqual((sh["agree_top1"], sh["agree_any"]), (True, True))

    def test_no_cache_hit_routes_and_is_post(self):
        with RecEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            e.record(payload("Skills: /frontend\nJev[r=deadbeef]: accept\nTask: build a landing page"))
            self.assertGreater(e.stub.count, 0)
            (fb,) = e.feedbacks()
            self.assertEqual(e.valid(fb), [])
            self.assertEqual((fb["consult"], fb["task_id"], fb["route_id"]), ("post", "deadbeef", "deadbeef"))
            self.assertEqual(fb["jev_skills"][0], "frontend")
            # routed in shadow accounting, and NOT a second cache entry
            jev = [u for u in e.usage_records() if u["router"] == "jev"]
            self.assertTrue(jev and all(u["shadow"] is True for u in jev))
            self.assertFalse(os.path.exists(os.path.join(e.state_dir, "jev-route-cache")))

    def test_line_without_id_routes_post(self):
        with RecEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            e.record(payload("Skills: /frontend\nJev: reject — fixed prompt, no skills\nTask: build"))
            (fb,) = e.feedbacks()
            self.assertEqual((fb["consult"], fb["verdict_raw"], fb["pd_reason"]),
                             ("post", "reject", "fixed prompt, no skills"))
            self.assertEqual(fb["task_id"], "sp-1")                    # no id anywhere: spawn_id

    def test_no_line_inferred_and_both_reasons(self):
        with RecEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            e.record(payload("Skills: /frontend\nBuild a landing page", spawn_id="a1"))
            e.record(payload("Build a landing page, nothing named", spawn_id="a2"))
            a, b = e.feedbacks()
            self.assertEqual((a["verdict_source"], a["pd_reason"], a["verdict_raw"], a["consult"]),
                             ("inferred", "inferred: no Jev line", None, "post"))
            self.assertEqual((b["verdict_source"], b["pd_reason"], b["spawn_verdict"], b["pd_review"]),
                             ("inferred", "inferred: zero skills named", "reject", "disagree"))
            self.assertEqual(b["spawner_skills"], [])
            self.assertEqual((a["task_id"], b["task_id"]), ("a1", "a2"))
            for fb in (a, b):
                self.assertEqual(e.valid(fb), [])

    def test_task_id_generated_without_ids(self):
        with RecEnv() as e:
            e.record(json.dumps({"subagent_type": "general-purpose", "prompt": "Build a landing page"}))
            (fb,) = e.feedbacks()
            self.assertRegex(fb["task_id"], r"^spawn-\d+$")
            self.assertEqual(e.valid(fb), [])

    def test_normalisation_cases(self):
        cases = [("Skills: /frontend, /tailwind", "accept", "agree"),
                 ("Skills: /frontend", "modify", "disagree"),
                 ("Skills: /frontend, /proofreader", "modify", "disagree"),
                 ("Skills: /proofreader", "reject", "disagree"),
                 ("No skills line here", "reject", "disagree")]
        for skills_line, want, review in cases:
            with RecEnv() as e:
                rid = put_cache()
                e.record(payload("%s\nJev[r=%s]: accept — whatever\nTask: build" % (skills_line, rid)))
                (fb,) = e.feedbacks()
                self.assertEqual((fb["spawn_verdict"], fb["pd_review"], fb["verdict_raw"]), (want, review, "accept"),
                                 skills_line)
                self.assertEqual(e.valid(fb), [])

    def test_unavailable_is_unreviewed(self):
        with RecEnv() as e:
            rid = put_cache(skills=[], gate="low_confidence", router="haiku", jev_down=True)
            e.record(payload("Skills: /frontend\nJev[r=%s]: unavailable — router=haiku\nTask: build" % rid))
            (fb,) = e.feedbacks()
            self.assertEqual((fb["spawn_verdict"], fb["verdict_source"], fb["pd_review"], fb["consult"]),
                             ("unreviewed", "jev_unavailable", "unreviewed", "gate"))
            self.assertEqual((fb["verdict_raw"], fb["pd_reason"], fb["jev_verdict"]),
                             ("unavailable", "router=haiku", "(none)"))
            self.assertEqual(e.valid(fb), [])
            self.assertEqual(e.stub.count, 0)

    def test_auto_sources_and_gate_consult(self):
        with RecEnv() as e:
            rid = put_cache()
            e.record(payload("Skills: /frontend, /tailwind\nJev[r=%s]: accept — auto: Jev default (gate pass)\nT" % rid,
                             spawn_id="d1"))
            e.record(payload("Skills: /frontend, /tailwind\nJev[r=%s]: accept — auto: matches Jev (gate pass)\nT" % rid,
                             spawn_id="d2"))
            d1, d2 = e.feedbacks()
            self.assertEqual((d1["verdict_source"], d1["consult"], d1["spawn_verdict"]), ("auto_default", "gate", "accept"))
            self.assertEqual((d2["verdict_source"], d2["consult"], d2["spawn_verdict"]), ("auto_match", "gate", "accept"))
            for fb in (d1, d2):
                self.assertEqual(e.valid(fb), [])
            self.assertEqual([s["verdict_source"] for s in e.shadows()], ["auto_default", "auto_match"])

    def test_exempt_types_get_shadow_record_but_no_feedback(self):
        for kw in ({"subagent_type": "Explore"}, {"subagent_type": "critique-code"},
                   {"subagent_type": "general-purpose", "fork": True}, {"subagent_type": "codebase-search"}):
            with RecEnv() as e:
                rid = put_cache()
                e.record(payload("Skills: /frontend\nJev[r=%s]: modify — x\nTask: build" % rid, **kw))
                self.assertEqual(len(e.shadows()), 1, kw)
                self.assertEqual(e.shadows()[0]["verdict"], "modify")
                self.assertEqual(e.feedbacks(), [], kw)
                self.assertEqual(e.appended, [])

    def test_binding_types(self):
        for st in ("general-purpose", "", "coord", "demo-project-pd", "something-new"):
            with RecEnv() as e:
                e.record(payload("Skills: /frontend\nBuild", subagent_type=st))
                self.assertEqual(len(e.feedbacks()), 1, st)

    def test_module_absent_or_erroring_is_silent(self):
        with RecEnv() as e:
            sr._feedback_module = lambda: None
            e.record(payload("Skills: /frontend\nBuild a landing page"))
            self.assertEqual(len(e.shadows()), 1)
            self.assertEqual(e.feedbacks(), [])
            bad = types.SimpleNamespace(append_spawn_record=lambda rec, path=None: ["unknown key: x"],
                                        reconcile=lambda: 1 / 0)
            sr._feedback_module = lambda: bad
            e.record(payload("Skills: /frontend\nBuild a landing page"))
            self.assertEqual(len(e.shadows()), 2)
            raising = types.SimpleNamespace(append_spawn_record=lambda rec, path=None: 1 / 0, reconcile=lambda: 1 / 0)
            sr._feedback_module = lambda: raising
            e.record(payload("Skills: /frontend\nBuild a landing page"))
            self.assertEqual(len(e.shadows()), 3)
            self.assertEqual(e.feedbacks(), [])

    def test_real_feedback_module_loads_and_writes(self):
        with RouterEnv() as e:
            sr._FEEDBACK_MOD = None
            mod = sr._feedback_module()
            self.assertTrue(hasattr(mod, "append_spawn_record") and hasattr(mod, "reconcile"))
            rid = put_cache()
            # reconcile would scan the real spawn logs: keep it a counted no-op, the writer stays real
            mod.reconcile = lambda *a, **k: {}
            tr.run_main(["--shadow"], payload("Skills: /frontend, /tailwind\nJev[r=%s]: accept\nTask: build" % rid))
            (fb,) = e.feedbacks()
            self.assertEqual(mod.validate_record(fb), [])

    def test_hourly_reconcile(self):
        with RecEnv() as e:
            stamp = os.path.join(e.state_dir, "jev-feedback-reconcile.ts")
            self.assertFalse(os.path.exists(stamp))
            e.record(payload("Skills: /frontend\nBuild one", spawn_id="h1"))
            self.assertTrue(os.path.exists(stamp))
            self.assertEqual(len(e.reconciles), 1)
            m1 = os.path.getmtime(stamp)
            e.record(payload("Skills: /frontend\nBuild two", spawn_id="h2"))
            e.record(payload("Skills: /frontend\nBuild three", spawn_id="h3"))
            self.assertEqual(len(e.reconciles), 1)                      # not again within the hour
            self.assertEqual(os.path.getmtime(stamp), m1)
            old = time.time() - 3700
            os.utime(stamp, (old, old))
            e.record(payload("Skills: /frontend\nBuild four", spawn_id="h4"))
            self.assertEqual(len(e.reconciles), 2)
            self.assertGreater(os.path.getmtime(stamp), old + 3000)
            self.assertEqual(len(e.feedbacks()), 4)

    def test_reconcile_stamp_written_before_reconcile_runs(self):
        with RecEnv() as e:
            stamp = os.path.join(e.state_dir, "jev-feedback-reconcile.ts")
            seen = []
            e.fake.reconcile = lambda *a, **k: seen.append(os.path.exists(stamp))
            e.record(payload("Skills: /frontend\nBuild"))
            self.assertEqual(seen, [True])

    def test_old_shadow_fields_unchanged(self):
        with RecEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            e.record(payload("Skills: /frontend, tailwind\nBuild a responsive landing page with /frontend."))
            (r,) = e.shadows()
            old = {"ts", "spawn_id", "subagent_type", "parent_agent", "task_excerpt", "actual_skills",
                   "router_skills", "router", "domain", "gate", "agree_top1", "agree_any", "agree_family", "role"}
            self.assertEqual(set(r), old | {"route_id", "verdict", "verdict_source"})
            self.assertEqual(r["actual_skills"], ["frontend", "tailwind"])
            self.assertEqual(r["router"], "jev")
            self.assertEqual(r["role"], "exec")
            self.assertEqual((r["agree_top1"], r["agree_any"]), (True, True))
            self.assertEqual(r["route_id"], "")

    def test_guards_and_garbage_never_raise_or_print(self):
        with RecEnv() as e:
            for raw in ("not json", "[]", "null", "", "   ", "{}", '{"prompt": 5, "description": null}',
                        '{"prompt": "\\u0000\\ud800", "subagent_type": 7, "fork": "x"}', None, 12):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    sr.shadow_run(raw)
                self.assertEqual((out.getvalue(), err.getvalue()), ("", ""), repr(raw))
            os.environ["SKILL_ROUTE_CHILD"] = "1"
            try:
                before = len(e.shadows())
                e.record(payload("Skills: /frontend\nBuild"))
                self.assertEqual(len(e.shadows()), before)
            finally:
                del os.environ["SKILL_ROUTE_CHILD"]
            open(os.path.join(e.state_dir, "skill-route-shadow.off"), "w").close()
            before = len(e.shadows())
            e.record(payload("Skills: /frontend\nBuild"))
            self.assertEqual(len(e.shadows()), before)

    def test_main_shadow_cli_is_silent(self):
        with RecEnv() as e:
            rid = put_cache()
            rc, out, err = tr.run_main(["--shadow"], payload("Skills: /frontend, /tailwind\nJev[r=%s]: accept" % rid))
            self.assertEqual((rc, out, err), (0, "", ""))
            self.assertEqual(len(e.feedbacks()), 1)


class SpawnProjectTests(unittest.TestCase):
    def table(self, e, rows):
        with open(e.medium_term, "w") as fh:
            fh.write("| Project | Path | PD | Status |\n|---|---|---|---|\n")
            for slug, path in rows:
                fh.write("| %s | `%s` | %s-pd | active |\n" % (slug, path, slug))

    def test_longest_prefix_boundary_fallback(self):
        with RouterEnv() as e:
            base = os.path.join(e.tmp, "projects")
            self.table(e, [("alpha", base + "/alpha/memory/"), ("alpha-sub", base + "/alpha/sub"),
                           ("alp", base + "/alp")])
            for cwd, want in ((base + "/alpha", "alpha"), (base + "/alpha/src/x", "alpha"),
                              (base + "/alpha/sub", "alpha-sub"), (base + "/alpha/sub/deep", "alpha-sub"),
                              (base + "/alphabet", "global"),            # path-boundary: alp/alpha are not prefixes
                              (base + "/alp/zz", "alp"), (e.tmp + "/other", "global"), (base, "global")):
                os.environ["CLAUDE_PROJECT_DIR"] = cwd
                self.assertEqual(sr._spawn_project(), want, cwd)
            os.environ["CLAUDE_PROJECT_DIR"] = base + "/alpha/"
            self.assertEqual(sr._spawn_project(), "alpha")

    def test_tilde_expansion_cwd_fallback_and_missing_file(self):
        with RouterEnv() as e:
            self.table(e, [("home-proj", "~/zz-test-proj/memory/")])
            os.environ["CLAUDE_PROJECT_DIR"] = os.path.expanduser("~/zz-test-proj/sub")
            self.assertEqual(sr._spawn_project(), "home-proj")
            del os.environ["CLAUDE_PROJECT_DIR"]
            self.assertEqual(sr._spawn_project(), "global")               # cwd is not under that project
            os.remove(e.medium_term)
            self.assertEqual(sr._spawn_project(), "global")

    def test_project_lands_in_feedback_record(self):
        with RecEnv() as e:
            proj = os.path.join(e.tmp, "projects", "demo")
            self.table(e, [("demo", proj + "/memory/")])
            os.environ["CLAUDE_PROJECT_DIR"] = proj
            e.record(payload("Skills: /frontend\nBuild"))
            (fb,) = e.feedbacks()
            self.assertEqual(fb["project"], "demo")
            self.assertEqual(e.valid(fb), [])


if __name__ == "__main__":
    unittest.main()
