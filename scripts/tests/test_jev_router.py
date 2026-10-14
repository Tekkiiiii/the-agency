"""Unit tests for scripts/skill-route.py (the Jev skill router). NO network: a local counting stub server
stands in for Jev (jev_stub.JevStub) and a fake `claude` script stands in for the Haiku fallback.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_router*' -v
Fixtures: scripts/tests/fixtures/jev/router-skills/ (skills dir) + router-overlay.json. Tests copy them to a
temp dir so mtime-based cache tests never touch the repo.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
import jev_stub  # noqa: E402
import jev_client  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "jev")
ROUTER_PATH = os.path.join(SCRIPTS, "skill-route.py")


def load_router():
    spec = importlib.util.spec_from_file_location("skill_route_under_test", ROUTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sr = load_router()
CONTRACT_KEYS = ["skills", "model", "tools", "scores", "domain", "router", "gate", "pre_rules", "lang",
                 "jev_down", "route_id"]


class RouterEnv(object):
    """jev_test_env + fixture skills/overlay copied to a temp dir + router log paths."""

    def __init__(self, **kw):
        self.kw = kw
        self.cm = None

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="router-fx-")
        self.skills_dir = os.path.join(self.tmp, "skills")
        shutil.copytree(os.path.join(FIX, "router-skills"), self.skills_dir)
        self.overlay = os.path.join(self.tmp, "overlay.json")
        shutil.copy(os.path.join(FIX, "router-overlay.json"), self.overlay)
        self.decision_log = os.path.join(self.tmp, "skill-route.jsonl")
        self.shadow_log = os.path.join(self.tmp, "shadow.jsonl")
        # the shadow recorder also appends to jev-feedback.jsonl and resolves a project from medium-term.md: both
        # (and the project dir) live in the temp dir so no test can touch a real install
        self.feedback_log = os.path.join(self.tmp, "jev-feedback.jsonl")
        self.medium_term = os.path.join(self.tmp, "medium-term.md")
        open(self.medium_term, "w").close()
        extra = {"SKILL_ROUTE_SKILLS_DIR": self.skills_dir, "SKILL_ROUTE_OVERLAY": self.overlay,
                 "SKILL_ROUTE_LOG": self.decision_log, "SKILL_ROUTE_SHADOW_LOG": self.shadow_log,
                 "JEV_FEEDBACK_LOG": self.feedback_log, "SKILL_ROUTE_MEDIUM_TERM": self.medium_term,
                 "CLAUDE_PROJECT_DIR": self.tmp}
        extra.update(self.kw.pop("extra_env", {}) or {})
        self.cm = jev_stub.jev_test_env(extra_env=extra, **self.kw)
        self.env = self.cm.__enter__()
        for k, v in extra.items():
            if v is None:       # extra_env value None = variable removed (jev_test_env restores it on exit)
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        r = self.cm.__exit__(*exc)
        shutil.rmtree(self.tmp, ignore_errors=True)
        return r

    def __getattr__(self, name):
        return getattr(self.env, name)

    def decisions(self):
        return jev_stub._read_jsonl(self.decision_log)

    def shadows(self):
        return jev_stub._read_jsonl(self.shadow_log)

    def feedbacks(self):
        return jev_stub._read_jsonl(self.feedback_log)


def read_text(path):
    with open(path) as fh:
        return fh.read()


def read_json(path):
    return json.loads(read_text(path))


def write_json(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh)


def run_main(argv, stdin_text=""):
    out, err = io.StringIO(), io.StringIO()
    old_in = sys.stdin
    sys.stdin = io.StringIO(stdin_text)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = sr.main(argv)
    finally:
        sys.stdin = old_in
    return rc, out.getvalue(), err.getvalue()


def req_questions(stub, i):
    return stub.requests[i]["json"]["questions"]


class FrontmatterTests(unittest.TestCase):
    def test_scalar_styles(self):
        fm = sr.parse_frontmatter(
            '---\nname: x\ndescription: "He said \\"hi\\" and\n  left."\nother: 1\n---\nbody')
        self.assertEqual(fm["description"], 'He said "hi" and left.')
        fm = sr.parse_frontmatter("---\nname: x\ndescription: 'it''s fine'\n---\n")
        self.assertEqual(fm["description"], "it's fine")
        fm = sr.parse_frontmatter("---\nname: x\ndescription: |\n  line one\n  line two\nlicense: MIT\n---\n")
        self.assertEqual(fm["description"], "line one line two")
        fm = sr.parse_frontmatter("---\nname: x\ndescription: >-\n  folded a\n  folded b\n---\n")
        self.assertEqual(fm["description"], "folded a folded b")
        fm = sr.parse_frontmatter("---\nname: x\ndescription: plain text here\nmetadata:\n  version: \"1\"\n---\n")
        self.assertEqual(fm["description"], "plain text here")
        self.assertEqual(sr.parse_frontmatter("no frontmatter"), {})


class MenuTests(unittest.TestCase):
    def test_menu_build_and_universe(self):
        with RouterEnv() as e:
            menu = sr.load_menu()
            names = set(menu["skills"])
            self.assertEqual(names, {"frontend", "tailwind", "humanizer", "humanizer-vi", "proofreader",
                                     "grammar-checker-vi", "simple-english", "content-polish",
                                     "gws-gmail-send", "code-review"})
            self.assertEqual(menu["excluded"], {"old-thing": "sunset"})
            self.assertNotIn("_hidden", names)
            self.assertNotIn("nested-skill", names)  # depth 1 only
            self.assertEqual(menu["skills"]["frontend"]["triggers"][0], "build a landing page")
            self.assertIn("landing page", menu["skills"]["frontend"]["description"])  # dq unquoted
            self.assertEqual(menu["skills"]["code-review"]["domain"], "code-quality-testing")  # synthetic
            self.assertIn("not for grammar", menu["skills"]["humanizer"]["hint"])
            self.assertEqual(menu["vi_map"]["humanizer"], "humanizer-vi")
            self.assertEqual(menu["en_only"], ["simple-english"])
            self.assertTrue(os.path.exists(os.path.join(e.state_dir, "skill-route-menu.json")))

    def test_triggers_come_from_overlay_not_catalog(self):
        with RouterEnv() as e:
            # catalog says one thing, overlay another: the overlay wins, catalog triggers are ignored
            with open(os.path.join(e.skills_dir, "INDEX.catalog.json"), "w") as f:
                json.dump({"skills": [{"name": "frontend", "triggers": ["catalog only phrase"]},
                                      {"name": "tailwind", "triggers": ["catalog tailwind phrase"]}]}, f)
            with open(e.overlay) as f:
                ov = json.load(f)
            ov["skills"]["frontend"]["triggers"] = ["overlay phrase one", "overlay phrase two"]
            ov["skills"]["humanizer"]["triggers"] = "not a list"
            ov["synthetic"]["code-review"]["triggers"] = ["synthetic phrase"]
            with open(e.overlay, "w") as f:
                json.dump(ov, f)
            menu = sr.load_menu(rebuild=True)
            self.assertEqual(menu["skills"]["frontend"]["triggers"], ["overlay phrase one", "overlay phrase two"])
            self.assertEqual(menu["skills"]["tailwind"]["triggers"], [])      # catalog-only triggers: ignored
            self.assertEqual(menu["skills"]["humanizer"]["triggers"], [])     # non-list overlay value: []
            self.assertEqual(menu["skills"]["code-review"]["triggers"], ["synthetic phrase"])

    def test_cache_reuse_and_invalidation(self):
        with RouterEnv() as e:
            m1 = sr.load_menu()
            time.sleep(1.1)
            m2 = sr.load_menu()
            self.assertEqual(m1["built_at"], m2["built_at"])  # served from cache (second-resolution stamps)
            # a newer SKILL.md invalidates
            time.sleep(1.1)
            p = os.path.join(e.skills_dir, "tailwind", "SKILL.md")
            with open(p, "a") as fh:
                fh.write("\nmore\n")
            m3 = sr.load_menu()
            self.assertNotEqual(m2["built_at"], m3["built_at"])
            # a newer overlay invalidates
            time.sleep(1.1)
            os.utime(e.overlay, None)
            m4 = sr.load_menu()
            self.assertNotEqual(m3["built_at"], m4["built_at"])
            # --rebuild-menu forces
            time.sleep(1.1)
            m5 = sr.load_menu(rebuild=True)
            self.assertNotEqual(m4["built_at"], m5["built_at"])

    def test_added_skill_dir_invalidates_cache(self):
        with RouterEnv() as e:
            sr.load_menu()
            d = os.path.join(e.skills_dir, "newskill")
            os.makedirs(d)
            with open(os.path.join(d, "SKILL.md"), "w") as fh:
                fh.write("---\nname: newskill\ndescription: new\n---\n")
            with self.assertRaises(sr.MenuError) as cm:  # new skill has no overlay entry -> loud
                sr.load_menu()
            self.assertIn("newskill", str(cm.exception))

    def test_fail_loud_unassigned_and_unknown_domain(self):
        with RouterEnv() as e:
            ov = read_json(e.overlay)
            del ov["skills"]["tailwind"]
            ov["skills"]["proofreader"]["domain"] = "no-such-domain"
            ov["skills"]["humanizer"] = {"hint": "no domain, no exclude"}
            write_json(e.overlay, ov)
            with self.assertRaises(sr.MenuError) as cm:
                sr.load_menu()
            msg = str(cm.exception)
            for needle in ("no overlay entry: tailwind", "no-such-domain", "proofreader", "no domain: humanizer"):
                self.assertIn(needle, msg)
            self.assertFalse(os.path.exists(os.path.join(e.state_dir, "skill-route-menu.json")))
            # CLI: exit 2, list on stderr, nothing on stdout
            rc, out, err = run_main(["--no-log", "hello world"])
            self.assertEqual(rc, 2)
            self.assertEqual(out, "")
            self.assertIn("proofreader", err)   # the CLI is lenient about an unassigned skill (tailwind), not about the rest
            # route() raises ONLY MenuError
            with self.assertRaises(sr.MenuError):
                sr.route("anything", log=False)

    def test_also_domains_offered_in_stage_two(self):
        with RouterEnv(winners={"domain": "writing-en", "skill": "humanizer", "model": "opus",
                                "tools": "web"}) as e:
            ov = read_json(e.overlay)
            ov["skills"]["gws-gmail-send"]["also_domains"] = ["writing-en", "google-workspace"]  # own domain ignored
            write_json(e.overlay, ov)
            menu = sr.load_menu()
            self.assertEqual(menu["skills"]["gws-gmail-send"]["domain"], "google-workspace")
            self.assertEqual(menu["skills"]["gws-gmail-send"]["also"], ["writing-en"])
            sr.route("make this less robotic", log=False)
            q2 = req_questions(e.stub, 1)
            self.assertEqual(sorted(q2["skill"]["criteria"]),
                             ["content-polish", "gws-gmail-send", "humanizer", "none", "proofreader",
                              "simple-english"])

    def test_also_domains_unknown_domain_raises(self):
        with RouterEnv() as e:
            ov = read_json(e.overlay)
            ov["skills"]["tailwind"]["also_domains"] = ["no-such-domain"]
            write_json(e.overlay, ov)
            with self.assertRaises(sr.MenuError) as cm:
                sr.load_menu()
            self.assertIn("unknown also_domains", str(cm.exception))
            self.assertIn("tailwind", str(cm.exception))
            self.assertFalse(os.path.exists(os.path.join(e.state_dir, "skill-route-menu.json")))

    def test_shadow_swallows_menu_error(self):
        with RouterEnv() as e:
            ov = read_json(e.overlay)
            ov["skills"]["tailwind"]["domain"] = "no-such-domain"
            write_json(e.overlay, ov)
            rc, out, err = run_main(["--shadow"], json.dumps({"description": "build a page", "prompt": "x"}))
            self.assertEqual((rc, out, err), (0, "", ""))
            self.assertEqual(e.shadows(), [])
            self.assertEqual(e.stub.count, 0)


class PreRuleTests(unittest.TestCase):
    def test_explicit_passthrough_no_api(self):
        with RouterEnv() as e:
            res = sr.route("/frontend build X", log=False)
            self.assertEqual(list(res.keys()), CONTRACT_KEYS)
            self.assertEqual(res["skills"], ["frontend"])
            self.assertEqual(res["router"], "passthrough")
            self.assertEqual(res["gate"], "pass")
            self.assertEqual(res["pre_rules"], ["explicit"])
            self.assertEqual(e.stub.count, 0)
            self.assertEqual(e.usage_records(), [])
            # paths and unknown slashes are not passthrough
            res = sr.route("look at /home/x/frontend/src and /usr/bin/env", log=False)
            self.assertNotEqual(res["router"], "passthrough")
            res = sr.route("see https://example.com/frontend and ./tailwind /nope", log=False)
            self.assertNotEqual(res["router"], "passthrough")
            res = sr.route("use /tailwind and /frontend and /humanizer and /proofreader", log=False)
            self.assertEqual(res["skills"], ["tailwind", "frontend", "humanizer"])  # max 3, order kept

    def test_outage_falls_back_to_haiku(self):
        with RouterEnv() as e:
            e.stub.set_mode("500")
            res = sr.route("Build a responsive landing page for our pricing", log=False)
            self.assertEqual(res["router"], "haiku")
            self.assertTrue(jev_stub.fake_claude_records(e.fake_claude))

    def test_plain_text_hits_jev(self):
        with RouterEnv() as e:
            res = sr.route("build a landing page", log=False)
            self.assertEqual(res["router"], "jev")
            self.assertEqual(e.stub.count, 2)  # two-stage default
            self.assertEqual(res["pre_rules"], [])

    def test_vietnamese_detection(self):
        self.assertEqual(sr.detect_lang("Viết bài về sản phẩm"), "vi")
        self.assertEqual(sr.detect_lang("do it in Vietnamese please"), "vi")
        self.assertEqual(sr.detect_lang("write it in tiếng Việt"), "vi")
        self.assertEqual(sr.detect_lang("the VN market launch"), "vi")
        self.assertEqual(sr.detect_lang("invoice for the VNX group"), "en")
        self.assertEqual(sr.detect_lang("a café résumé"), "en")  # acute/grave alone do not count
        self.assertEqual(sr.detect_lang("Tạo bài viết về sản phẩm"), "vi")

    def test_vietnamese_maps_to_vi_variants(self):
        with RouterEnv(stub_mode="ok", winners={"domain": "writing-en", "skill": "humanizer"}) as e:
            res = sr.route("Làm cho đoạn văn này tự nhiên hơn", log=False)
            self.assertEqual(res["lang"], "vi")
            self.assertIn("vietnamese", res["pre_rules"])
            self.assertEqual(res["skills"][0], "humanizer-vi")
            self.assertNotIn("humanizer", res["skills"])
            self.assertIn("humanizer-vi", res["scores"])
            # proofreader -> grammar-checker-vi
            e.stub.winners = {"domain": "writing-en", "skill": "proofreader"}
            res = sr.route("Soát lỗi chính tả đoạn này", log=False)
            self.assertEqual(res["skills"][0], "grammar-checker-vi")
            # en_only dropped; if that empties the list content-polish (handles both) is used
            e.stub.winners = {"domain": "writing-en", "skill": "simple-english"}
            e.stub.peak = 0.99
            res = sr.route("Viết lại đơn giản hơn cho người đọc", log=False)
            self.assertNotIn("simple-english", res["skills"])
            self.assertEqual(res["skills"], ["content-polish"])
            # English text untouched
            e.stub.winners = {"domain": "writing-en", "skill": "humanizer"}
            res = sr.route("make this less robotic", log=False)
            self.assertEqual(res["skills"][0], "humanizer")
            self.assertEqual(res["lang"], "en")

    def test_vietnamese_grep_folds_diacritics(self):
        with RouterEnv():
            res = sr.route("Kiểm tra chính tả văn bản tiếng Việt", router="grep", log=False)
            self.assertEqual(res["lang"], "vi")
            self.assertEqual(res["skills"][0], "grammar-checker-vi")


class TwoStageTests(unittest.TestCase):
    def test_request_shapes_and_contract(self):
        with RouterEnv(winners={"domain": "writing-en", "skill": "humanizer", "model": "opus",
                                "tools": "web"}) as e:
            res = sr.route("make this less robotic", log=False)
            self.assertEqual(list(res.keys()), CONTRACT_KEYS)
            self.assertEqual((res["skills"], res["model"], res["tools"]), (["humanizer"], "opus", "web"))
            self.assertEqual((res["domain"], res["router"], res["gate"]), ("writing-en", "jev", "pass"))
            # raw stage-2 probabilities (5 options incl. `none`: rest = 0.2/4); `none` is never a score key
            self.assertEqual(res["scores"], {"humanizer": 0.8, "content-polish": 0.05, "proofreader": 0.05})
            self.assertFalse(res["jev_down"])
            self.assertEqual(e.stub.count, 2)
            q1, q2 = req_questions(e.stub, 0), req_questions(e.stub, 1)
            self.assertEqual(list(q1), ["domain"])
            self.assertEqual(q1["domain"]["type"], "choice")
            self.assertNotIn("unused-domain", q1["domain"]["criteria"])  # no routable skill -> not offered
            self.assertEqual(q1["domain"]["criteria"]["writing-en"],
                             "Writing, editing and polishing English prose.")
            self.assertEqual(e.stub.requests[0]["json"]["state"], "make this less robotic")
            self.assertEqual(sorted(q2), ["model", "skill", "tools"])
            self.assertEqual(sorted(q2["skill"]["criteria"]),
                             ["content-polish", "humanizer", "none", "proofreader", "simple-english"])
            self.assertEqual(list(q2["skill"]["criteria"])[-1], "none")  # last: stubs/LLMs default to first
            self.assertEqual(sorted(q2["model"]["criteria"]), ["haiku", "opus", "sonnet"])
            self.assertEqual(sorted(q2["tools"]["criteria"]), ["edit", "full", "read-only", "web"])
            self.assertIn("Hint: use for AI-sounding prose", q2["skill"]["criteria"]["humanizer"])
            # usage log: purpose skill-route, not shadow
            recs = [r for r in e.usage_records() if r["router"] == "jev"]
            self.assertEqual(len(recs), 2)
            self.assertTrue(all(r["purpose"] == "skill-route" and r["shadow"] is False for r in recs))

    def test_gate_thresholds_via_router(self):
        # the stub gives the same peak to the domain and the skill question: combined p = peak * peak,
        # combined margin = peak * (peak - rest) with rest = (1 - peak) / 4 (5 options incl. `none`)
        with RouterEnv(winners={"domain": "writing-en", "skill": "humanizer"}, peak=0.3) as e:
            res = sr.route("make this less robotic", log=False)
            self.assertEqual(res["gate"], "low_confidence")
            self.assertEqual(res["skills"][0], "humanizer")
            self.assertEqual(len(res["skills"]), 3)  # others at 0.175 >= 0.15 (none is not a skill)
            for peak in (0.5, 0.6, 0.7, 0.8, 0.95):
                e.stub.peak = peak
                res = sr.route("make this less robotic", log=False)
                rest = (1 - peak) / 4
                want = "pass" if (peak * peak >= sr.TS_T1 and peak * (peak - rest) >= sr.TS_T2) else "low_confidence"
                self.assertEqual(res["gate"], want, peak)
                self.assertEqual(res["skills"][0], "humanizer")

    def test_select_gate_math(self):
        sel = sr._select
        self.assertEqual(sel([("a", 0.44), ("b", 0.1)])[2], "low_confidence")
        self.assertEqual(sel([("a", 0.45), ("b", 0.35)])[2], "pass")
        self.assertEqual(sel([("a", 0.46), ("b", 0.37)])[2], "low_confidence")  # gap < 0.10
        self.assertEqual(sel([("a", 0.6)])[2], "pass")
        self.assertEqual(sel([])[2], "low_confidence")
        skills, scores, _ = sel([("a", 0.6), ("b", 0.2), ("c", 0.14), ("d", 0.06)])
        self.assertEqual(skills, ["a", "b"])
        self.assertEqual(scores, {"a": 0.6, "b": 0.2, "c": 0.14})
        self.assertEqual(sel([("a", 0.5), ("b", 0.2), ("c", 0.15), ("d", 0.15)])[0], ["a", "b", "c"])  # max 3

    def test_stage2_failure_degrades_to_domain_grep(self):
        with RouterEnv() as e:
            real_ask = jev_client.ask
            calls = {"n": 0}

            def flaky(*a, **k):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise jev_client.RouterUnavailable("stage 2 down")
                return real_ask(*a, **k)

            orig = jev_client.ask
            jev_client.ask = flaky
            try:
                e.stub.winners = {"domain": "frontend-ui"}
                res = sr.route("tailwind responsive styling", log=False)
            finally:
                jev_client.ask = orig
            self.assertEqual(res["router"], "grep")
            self.assertEqual(res["gate"], "low_confidence")
            self.assertEqual(res["domain"], "frontend-ui")
            self.assertTrue(set(res["skills"]) <= {"frontend", "tailwind"})
            self.assertEqual(res["skills"][0], "tailwind")

    def test_router_haiku_skips_jev(self):
        with RouterEnv() as e:
            res = sr.route("build a landing page", router="haiku", log=False)
            self.assertEqual(res["router"], "haiku")
            self.assertEqual(e.stub.count, 0)
            self.assertEqual(len(jev_stub.fake_claude_records(e.fake_claude)), 2)

    def test_jev_outage_falls_back_haiku_then_grep(self):
        with RouterEnv(stub_mode="401") as e:
            res = sr.route("build a landing page", log=False)
            self.assertEqual(res["router"], "haiku")
            self.assertTrue(res["jev_down"])  # flag set by the client
            jev_stub.set_fake_behavior(e.fake_claude, "exit_nonzero")
            res = sr.route("tailwind responsive styling", log=False)
            self.assertEqual(res["router"], "grep")
            self.assertEqual(res["gate"], "low_confidence")
            self.assertEqual((res["model"], res["tools"]), ("sonnet", "edit"))
            self.assertTrue(res["jev_down"])

    def test_child_env_never_calls_claude(self):
        with RouterEnv(stub_mode="401", extra_env={"SKILL_ROUTE_CHILD": "1"}) as e:
            res = sr.route("tailwind responsive styling", log=False)
            self.assertEqual(res["router"], "grep")
            self.assertEqual(jev_stub.fake_claude_records(e.fake_claude), [])


class FlatTests(unittest.TestCase):
    def test_flat_small_menu_single_skill_question(self):
        with RouterEnv(winners={"skill": "gws-gmail-send", "model": "haiku", "tools": "web"}) as e:
            res = sr.route("send an email to the team", mode="flat", log=False)
            self.assertEqual(e.stub.count, 1)
            q = req_questions(e.stub, 0)
            self.assertEqual(sorted(q), ["model", "skill", "tools"])
            self.assertEqual(len(q["skill"]["criteria"]), 11)  # every routable skill + `none` (last)
            self.assertEqual(list(q["skill"]["criteria"])[-1], "none")
            self.assertEqual(res["skills"][0], "gws-gmail-send")
            self.assertEqual(res["domain"], "google-workspace")
            self.assertEqual((res["model"], res["tools"]), ("haiku", "web"))

    def _big_menu(self, n):
        names = ["s%03d" % i for i in range(n)]
        menu = {"skills": dict((nm, {"description": "skill number %s does a thing" % nm, "triggers": [],
                                     "domain": "d", "hint": ""}) for nm in names),
                "domains": {"d": "the only domain"}, "excluded": {}, "vi_map": {}, "en_only": [], "built_at": "x"}
        return menu, names

    def test_chunking_364(self):
        menu, names = self._big_menu(364)
        qs, keys = sr._skill_questions(menu, names, 140, 120)
        self.assertEqual(keys, ["skill_1", "skill_2"])
        total = 0
        for k in keys:
            crit = qs[k]["criteria"]
            self.assertLessEqual(len(crit), 255)  # Jev choice limit incl. `none`
            self.assertIn("none", crit)
            total += len(crit) - 1
        self.assertEqual(total, 364)
        # 254 skills + `none` = 255 options -> single question; 255 skills -> chunked
        qs, keys = sr._skill_questions(menu, names[:254], 140, 120)
        self.assertEqual(keys, ["skill"])
        self.assertEqual(len(qs["skill"]["criteria"]), 255)
        self.assertIn("none", qs["skill"]["criteria"])
        self.assertEqual(sr._skill_questions(menu, names[:255], 140, 120)[1], ["skill_1", "skill_2"])

    def test_merge_formula(self):
        answers = {
            "skill_1": {"probabilities": {"a": 0.6, "b": 0.1, "none": 0.3}},
            "skill_2": {"probabilities": {"c": 0.5, "d": 0.1, "none": 0.4}},
        }
        ranked, min_none = sr._merge_chunks(answers, ["skill_1", "skill_2"])
        raw = {"a": 0.6 * 0.7, "b": 0.1 * 0.7, "c": 0.5 * 0.6, "d": 0.1 * 0.6}
        tot = sum(raw.values())
        got = dict(ranked)
        for k, v in raw.items():
            self.assertAlmostEqual(got[k], v / tot, places=9)
        self.assertAlmostEqual(sum(got.values()), 1.0, places=9)
        self.assertEqual([k for k, _ in ranked], ["a", "c", "b", "d"])
        self.assertAlmostEqual(min_none, 0.3)

    def test_flat_364_single_request_end_to_end(self):
        with RouterEnv() as e:
            menu, names = self._big_menu(364)
            # a real >255 menu: reuse the fixture machinery by monkeypatching load_menu
            orig = sr.load_menu
            sr.load_menu = lambda rebuild=False, strict=True: menu
            try:
                e.stub.winners = {"skill_1": "none", "skill_2": "s300"}
                e.stub.peak = 0.9
                res = sr.route("do the thing", mode="flat", log=False)
            finally:
                sr.load_menu = orig
            self.assertEqual(e.stub.count, 1)  # ONE request, k chunk questions + model + tools
            q = req_questions(e.stub, 0)
            self.assertEqual(sorted(q), ["model", "skill_1", "skill_2", "tools"])
            self.assertEqual(res["skills"][0], "s300")
            self.assertEqual(res["router"], "jev")

    def test_flat_all_none_is_low_confidence(self):
        with RouterEnv() as e:
            menu, names = self._big_menu(300)
            orig = sr.load_menu
            sr.load_menu = lambda rebuild=False, strict=True: menu
            try:
                e.stub.winners = {"skill_1": "none", "skill_2": "none"}
                e.stub.peak = 0.9
                res = sr.route("something unrelated", mode="flat", log=False)
            finally:
                sr.load_menu = orig
            self.assertEqual(res["gate"], "low_confidence")


class GrepTests(unittest.TestCase):
    def test_grep_contract(self):
        with RouterEnv() as e:
            res = sr.route("build a landing page", router="grep", log=False)
            self.assertEqual(list(res.keys()), CONTRACT_KEYS)
            self.assertEqual(res["router"], "grep")
            self.assertEqual(res["gate"], "low_confidence")
            self.assertEqual((res["model"], res["tools"]), ("sonnet", "edit"))
            self.assertEqual(res["skills"][0], "frontend")
            self.assertEqual(e.stub.count, 0)
            self.assertEqual(jev_stub.fake_claude_records(e.fake_claude), [])

    def test_grep_no_overlap_and_empty(self):
        with RouterEnv():
            res = sr.route("zzz qqq", router="grep", log=False)
            self.assertEqual(res["skills"], [])
            self.assertEqual(res["gate"], "low_confidence")
            res = sr.route("   ", log=False)
            self.assertEqual((res["skills"], res["router"], res["gate"]), ([], "grep", "low_confidence"))


class LogAndCliTests(unittest.TestCase):
    def test_decision_log_and_no_log(self):
        with RouterEnv() as e:
            rc, out, err = run_main(["build a landing page"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            res = json.loads(out)  # stdout is exactly one JSON object
            self.assertEqual(list(res.keys()), CONTRACT_KEYS)
            self.assertEqual(len(e.decisions()), 1)
            self.assertEqual(e.decisions()[0]["calls"], 2)
            rc, out, err = run_main(["--no-log", "build a landing page"])
            self.assertEqual(len(e.decisions()), 1)  # unchanged
            self.assertEqual(len(e.usage_records()), 4)  # jev-usage is ALWAYS written

    def test_cli_options_and_stdin(self):
        with RouterEnv() as e:
            rc, out, _ = run_main(["--no-log", "--router", "grep", "--mode", "flat"], "build a landing page")
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out)["router"], "grep")
            rc, out, _ = run_main(["--no-log", "--project", "some-project", "--router", "grep", "x page"])
            self.assertEqual(json.loads(out)["pre_rules"], [])          # --project is only recorded, never a pre-rule
            rc, out, err = run_main([], "")
            self.assertEqual(rc, 2)
            self.assertEqual(out, "")
            rc, out, err = run_main(["--rebuild-menu"], "")
            self.assertEqual(rc, 0)
            stats = json.loads(out)
            self.assertEqual((stats["routable"], stats["excluded"]), (10, 1))
            self.assertEqual(stats["domains"]["writing-en"], 4)

    def test_rebuild_menu_and_shadow_report_never_read_stdin(self):
        class Boom(object):  # an open non-EOF pipe: any read would block forever
            def isatty(self):
                return False

            def read(self, *a):
                raise AssertionError("stdin must not be read")

        with RouterEnv():
            old_in = sys.stdin
            sys.stdin = Boom()
            try:
                for argv in (["--rebuild-menu"], ["--shadow-report"]):
                    out, err = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        rc = sr.main(argv)
                    self.assertEqual(rc, 0, argv)
                    self.assertEqual(err.getvalue(), "")
                    self.assertTrue(out.getvalue().strip(), argv)
            finally:
                sys.stdin = old_in

    def test_rebuild_menu_does_not_block_on_open_pipe(self):
        with RouterEnv() as e:
            env = dict(os.environ)
            proc = subprocess.Popen([sys.executable, ROUTER_PATH, "--rebuild-menu"], env=env,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                proc.wait(timeout=20)  # NOT communicate(): that would close stdin; the pipe must stay open
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                self.fail("--rebuild-menu blocked on an open stdin pipe")
            finally:
                out = proc.stdout.read()
                proc.stdout.close()
                proc.stderr.close()
                proc.stdin.close()
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(json.loads(out)["routable"], 10)

    def test_default_mode_constant(self):
        self.assertEqual(sr.DEFAULT_MODE, "two-stage")
        self.assertEqual((sr.T1, sr.T2, sr.RANK_MIN_PROB), (0.45, 0.10, 0.15))

    def test_key_never_printed(self):
        with RouterEnv(stub_mode="401") as e:
            rc, out, err = run_main(["build a landing page"])
            blob = out + err + read_text(e.decision_log) + read_text(e.usage_log)
            self.assertNotIn(jev_stub.BOGUS_KEY, blob)


class ShadowTests(unittest.TestCase):
    def payload(self, **kw):
        d = {"spawn_id": "sp-1", "subagent_type": "general-purpose", "parent_agent": "some-pd",
             "description": "Build the landing page",
             "prompt": "Skills: /frontend, tailwind\nBuild a responsive landing page with /frontend."}
        d.update(kw)
        return json.dumps(d)

    def test_shadow_record_and_agreement(self):
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            rc, out, err = run_main(["--shadow"], self.payload())
            self.assertEqual((rc, out, err), (0, "", ""))
            recs = e.shadows()
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r["spawn_id"], "sp-1")
            self.assertEqual(r["actual_skills"], ["frontend", "tailwind"])
            self.assertEqual(r["router_skills"][0], "frontend")
            self.assertEqual(r["router"], "jev")
            self.assertEqual((r["agree_top1"], r["agree_any"]), (True, True))
            self.assertEqual(set(r), {"ts", "spawn_id", "subagent_type", "parent_agent", "task_excerpt",
                                      "actual_skills", "router_skills", "router", "domain", "gate",
                                      "agree_top1", "agree_any", "agree_family", "role",
                                      "route_id", "verdict", "verdict_source"})
            # no Jev line in the prompt: inferred verdict, no route id
            self.assertEqual((r["route_id"], r["verdict_source"]), ("", "inferred"))
            self.assertEqual(r["verdict"], "accept" if set(r["actual_skills"]) == set(r["router_skills"])
                             else "modify")   # S={frontend,tailwind} vs Jev's pick: overlap -> modify
            # slash tokens + Skills: line stripped from what Jev sees; passthrough disabled
            state = e.stub.requests[0]["json"]["state"]
            self.assertNotIn("/frontend", state)
            self.assertNotIn("Skills:", state)
            self.assertIn("landing page", state)
            self.assertEqual(e.stub.count, 2)  # routed through Jev, not passthrough
            # usage log lines flagged shadow
            jev = [u for u in e.usage_records() if u["router"] == "jev"]
            self.assertTrue(jev and all(u["shadow"] is True for u in jev))
            # no decision log from shadow
            self.assertEqual(e.decisions(), [])

    def test_shadow_disagree_and_no_actual(self):
        with RouterEnv(winners={"domain": "writing-en", "skill": "humanizer"}) as e:
            run_main(["--shadow"], self.payload(prompt="SKILLS: gws-gmail-send, bogus-name\nSend it."))
            run_main(["--shadow"], self.payload(spawn_id="sp-2", prompt="no skills named here"))
            a, b = e.shadows()
            self.assertEqual(a["actual_skills"], ["gws-gmail-send"])  # menu names only
            self.assertEqual((a["agree_top1"], a["agree_any"]), (False, False))
            self.assertEqual(b["actual_skills"], [])
            self.assertEqual((b["agree_top1"], b["agree_any"]), (None, None))

    def test_shadow_kill_switch_and_child_guard(self):
        with RouterEnv() as e:
            open(os.path.join(e.state_dir, "skill-route-shadow.off"), "w").close()
            rc, out, err = run_main(["--shadow"], self.payload())
            self.assertEqual((rc, out, err), (0, "", ""))
            self.assertEqual(e.shadows(), [])
            self.assertEqual(e.stub.count, 0)
            os.remove(os.path.join(e.state_dir, "skill-route-shadow.off"))
            os.environ["SKILL_ROUTE_CHILD"] = "1"
            try:
                rc, out, err = run_main(["--shadow"], self.payload())
            finally:
                del os.environ["SKILL_ROUTE_CHILD"]
            self.assertEqual((rc, out, err), (0, "", ""))
            self.assertEqual(e.shadows(), [])
            self.assertEqual(e.stub.count, 0)

    def test_shadow_never_raises(self):
        with RouterEnv() as e:
            for raw in ("", "not json", "[1,2]", "null", '{"prompt": 5, "description": null}', "{}"):
                rc, out, err = run_main(["--shadow"], raw)
                self.assertEqual((rc, out, err), (0, "", ""), raw)
            # process level: exit 0 and silent even with a hostile env
            env = dict(os.environ)
            p = subprocess.run([sys.executable, ROUTER_PATH, "--shadow"], input=self.payload().encode(),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            self.assertEqual(p.returncode, 0)
            self.assertEqual((p.stdout, p.stderr), (b"", b""))

    def test_shadow_text_cap_and_secret_redaction(self):
        with RouterEnv() as e:
            run_main(["--shadow"], self.payload(description="x plain", prompt="y" * 5000))
            self.assertLessEqual(len(e.stub.requests[0]["json"]["state"]), 3000)
            self.assertLessEqual(len(e.shadows()[0]["task_excerpt"]), 200)
            # a credential-shaped string is redacted before it reaches Jev, the log or the Haiku prompt
            secret = "sk-ant-" + "a" * 30
            run_main(["--shadow"], self.payload(spawn_id="sp-9", description="x " + secret, prompt="y" * 5000))
            self.assertEqual(len(e.shadows()), 2)
            self.assertNotIn(secret, json.dumps(e.shadows()))
            self.assertNotIn(secret, json.dumps([r["body"] for r in e.stub.requests]))
            self.assertNotIn(secret, json.dumps(jev_stub.fake_claude_records(e.fake_claude)))

    def test_shadow_report(self):
        with RouterEnv() as e:
            rows = [
                {"ts": "2026-10-08T01:00:00Z", "router": "jev", "actual_skills": ["a"], "agree_top1": True,
                 "agree_any": True},
                {"ts": "2026-10-08T02:00:00Z", "router": "jev", "actual_skills": ["a"], "agree_top1": False,
                 "agree_any": True},
                {"ts": "2026-10-08T03:00:00Z", "router": "haiku", "actual_skills": [], "agree_top1": None,
                 "agree_any": None},
                {"ts": "2026-10-08T04:00:00Z", "router": "grep", "actual_skills": ["b"], "agree_top1": False,
                 "agree_any": False},
            ]
            with open(e.shadow_log, "w") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
            with open(e.usage_log, "w") as fh:
                for u in [{"router": "jev", "shadow": True, "usd": 0.001, "ok": True, "input_tokens": 100,
                           "purpose": "skill-route"},
                          {"router": "jev", "shadow": False, "usd": 0.5, "ok": True, "input_tokens": 1},
                          {"router": "haiku", "shadow": True, "usd": 0.007, "ok": True, "input_tokens": 9},
                          {"router": "jev", "shadow": True, "usd": 0.002, "ok": True, "input_tokens": 50,
                           "purpose": "skill-route"}]:
                    fh.write(json.dumps(u) + "\n")
            rc, out, err = run_main(["--shadow-report"])
            self.assertEqual(rc, 0)
            self.assertIn("window start: 2026-10-08T01:00:00Z", out)
            self.assertIn("records: 4", out)
            self.assertIn("records with actual skills: 3", out)
            self.assertIn("top-1 agreement: 33.3% (1/3)", out)
            self.assertIn("any agreement:   66.7% (2/3)", out)
            self.assertIn("jev    records 2", out)
            self.assertIn("$0.003000", out)  # only shadow:true jev lines
            self.assertIn("Haiku fallback cost to date (shadow calls, shown separately): $0.007000", out)

    def test_shadow_report_empty(self):
        with RouterEnv():
            rc, out, err = run_main(["--shadow-report"])
            self.assertEqual(rc, 0)
            self.assertIn("records: 0", out)


LIVE_OVERLAY = os.path.join(SCRIPTS, "skill-route", "overlay.json")
BUILTINS = ("plugin-authoring", "claude-api", "update-config", "keybindings-help", "fewer-permission-prompts",
            "dataviz", "code-review", "simplify", "security-review")


class BuiltinMenuTests(unittest.TestCase):
    def test_live_overlay_has_routable_builtins(self):
        ov = read_json(LIVE_OVERLAY)
        syn = ov["synthetic"]
        for name in BUILTINS:
            self.assertIn(name, syn, name)
            self.assertIn(syn[name]["domain"], ov["domains"], name)
            self.assertTrue(10 <= len(syn[name]["description"]) <= 260, name)
            for d in syn[name].get("also_domains") or []:
                self.assertIn(d, ov["domains"], name)
        for name in ("init", "loop", "schedule", "run"):  # interactive / session-level: not routable
            self.assertNotIn(name, syn, name)
        self.assertEqual(syn["plugin-authoring"]["domain"], "claude-system-ops")
        self.assertEqual(syn["dataviz"]["domain"], "decks-docs-reports-charts")

    def test_synthetic_entry_supports_also_domains(self):
        with RouterEnv(winners={"domain": "writing-en", "skill": "humanizer"}) as e:
            ov = read_json(e.overlay)
            ov["synthetic"]["code-review"]["also_domains"] = ["writing-en", "code-quality-testing"]
            write_json(e.overlay, ov)
            menu = sr.load_menu()
            self.assertEqual(menu["skills"]["code-review"]["also"], ["writing-en"])  # own domain dropped
            sr.route("make this less robotic", log=False)
            self.assertIn("code-review", req_questions(e.stub, 1)["skill"]["criteria"])
            ov["synthetic"]["code-review"]["also_domains"] = ["no-such-domain"]
            write_json(e.overlay, ov)
            with self.assertRaises(sr.MenuError) as cm:
                sr.load_menu(rebuild=True)
            self.assertIn("code-review", str(cm.exception))


class NoneFitsTests(unittest.TestCase):
    def test_none_info_pure(self):
        one = {"skill": {"probabilities": {"a": 0.5, "b": 0.2, "none": 0.3}}}
        self.assertEqual(sr._none_info(one, ["skill"]), (0.3, False))
        one = {"skill": {"probabilities": {"a": 0.3, "b": 0.2, "none": 0.5}}}
        self.assertEqual(sr._none_info(one, ["skill"]), (0.5, True))
        two = {"skill_1": {"probabilities": {"a": 0.3, "none": 0.7}},
               "skill_2": {"probabilities": {"c": 0.6, "none": 0.4}}}
        self.assertEqual(sr._none_info(two, ["skill_1", "skill_2"]), (0.4, False))  # chunk 2 has a fit
        two["skill_2"]["probabilities"] = {"c": 0.2, "none": 0.8}
        self.assertEqual(sr._none_info(two, ["skill_1", "skill_2"]), (0.7, True))   # every chunk says none
        self.assertEqual(sr._none_info({"skill": {"probabilities": {"a": 1.0}}}, ["skill"]), (0.0, False))

    def test_none_fires_rule(self):
        self.assertTrue(sr._none_fires(0.2, True))           # none wins
        self.assertTrue(sr._none_fires(sr.NONE_T, False))    # none holds >= threshold
        self.assertFalse(sr._none_fires(sr.NONE_T - 0.01, False))
        self.assertTrue(0.0 < sr.NONE_T <= 0.5)

    def test_two_stage_none_wins_returns_empty(self):
        with RouterEnv(winners={"domain": "writing-en", "skill": "none"}, peak=0.7) as e:
            res = sr.route("tune the eval thresholds on the dev split", log=True)
            self.assertEqual(list(res.keys()), CONTRACT_KEYS)
            self.assertEqual(res["skills"], [])
            self.assertEqual(res["gate"], "low_confidence")
            self.assertEqual(res["domain"], "writing-en")   # stage-1 answer kept as info
            self.assertEqual(res["router"], "jev")
            self.assertNotIn("none", res["scores"])
            self.assertTrue(res["scores"])                   # best real candidates kept as info only
            rec = e.decisions()[-1]
            self.assertEqual(rec["none_p"], 0.7)
            self.assertTrue(rec["none_fired"])
            # Vietnamese text: an empty pick stays empty (no content-polish injection)
            res = sr.route("Điều chỉnh ngưỡng đánh giá trên tập dev", log=False)
            self.assertEqual(res["skills"], [])

    def test_two_stage_single_skill_domain_still_asks_with_none(self):
        with RouterEnv(winners={"domain": "code-quality-testing"}) as e:
            res = sr.route("review the diff", log=False)
            q2 = req_questions(e.stub, 1)
            self.assertEqual(list(q2["skill"]["criteria"]), ["code-review", "none"])
            self.assertEqual(res["skills"], ["code-review"])

    def test_flat_none_wins_returns_empty(self):
        with RouterEnv(winners={"skill": "none"}, peak=0.9) as e:
            res = sr.route("something no skill covers", mode="flat", log=False)
            self.assertEqual(res["skills"], [])
            self.assertEqual(res["gate"], "low_confidence")
            self.assertNotIn("none", res["scores"])


class CombinedGateTests(unittest.TestCase):
    def test_gate_combined_math(self):
        g = sr._gate_combined
        t1, t2 = sr.TS_T1, sr.TS_T2
        self.assertEqual(g(1.0, [("a", t1), ("b", 0.0)]), "pass" if t1 >= t2 else "low_confidence")
        self.assertEqual(g(1.0, [("a", t1 - 0.01), ("b", 0.0)]), "low_confidence")
        self.assertEqual(g(0.5, [("a", 1.0)]), "pass" if 0.5 >= t1 and 0.5 >= t2 else "low_confidence")
        # domain uncertainty alone can fail a confident stage-2 pick
        self.assertEqual(g(t1 * 0.9, [("a", 1.0)]), "low_confidence")
        # margin is on the combined scale
        p1 = min(1.0, t1 + t2)
        self.assertEqual(g(1.0, [("a", p1), ("b", p1 - t2 + 0.001)]), "low_confidence")
        self.assertEqual(g(1.0, [("a", p1), ("b", p1 - t2 - 0.001)]), "pass")
        self.assertEqual(g(1.0, []), "low_confidence")
        self.assertEqual(g(None, [("a", 1.0)]), "low_confidence")

    def test_decision_log_has_combined_fields(self):
        with RouterEnv(winners={"domain": "writing-en", "skill": "humanizer"}, peak=0.8) as e:
            sr.route("make this less robotic", log=True)
            rec = e.decisions()[-1]
            self.assertEqual(rec["domain_p"], 0.8)
            self.assertEqual(rec["skill_p"], 0.8)
            self.assertEqual(rec["p_combined"], 0.64)
            self.assertEqual(rec["none_p"], 0.05)
            self.assertFalse(rec["none_fired"])

    def test_flat_keeps_single_stage_constants(self):
        self.assertEqual((sr.T1, sr.T2), (0.45, 0.10))
        self.assertTrue(0.0 < sr.TS_T1 < 1.0 and 0.0 <= sr.TS_T2 < 1.0)


if __name__ == "__main__":
    unittest.main()
