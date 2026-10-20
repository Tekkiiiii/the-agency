"""Unit tests for scripts/jev_spawn.py (Jev binding-spawn core). unittest style; NO network; the route cache
uses a temp SKILL_ROUTE_STATE_DIR and never touches a real install.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_spawn*' -v
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import jev_spawn as js  # noqa: E402

RID = "3fa9c1d2"


def jev(skills=("a", "b"), gate="pass", router="jev", none_fired=False, confidential=False, jev_down=False):
    return {"skills": list(skills), "gate": gate, "router": router, "none_fired": none_fired,
            "confidential": confidential, "jev_down": jev_down}


def _w(path, text):
    with open(path, "w") as f:
        f.write(text)


def L(verdict, reason="", rid=RID):
    return {"id": rid, "verdict": verdict, "reason": reason, "line": "x"}


class GrammarTests(unittest.TestCase):
    def test_spec_examples(self):
        r = js.parse_verdict_line("Jev[r=3fa9c1d2]: accept")
        self.assertEqual((r["id"], r["verdict"], r["reason"]), (RID, "accept", ""))
        r = js.parse_verdict_line("Jev[r=3fa9c1d2]: modify — Jev missed the Tailwind side")
        self.assertEqual((r["id"], r["verdict"], r["reason"]), (RID, "modify", "Jev missed the Tailwind side"))
        r = js.parse_verdict_line("Jev: reject — fixed graphify extraction prompt, no skills")
        self.assertEqual((r["id"], r["verdict"], r["reason"]),
                         (None, "reject", "fixed graphify extraction prompt, no skills"))
        self.assertEqual(r["line"], "Jev: reject — fixed graphify extraction prompt, no skills")

    def test_negatives(self):
        for t in (None, "", "no line here", "Jev: maybe — x", "Jev[r=XYZ]: accept", "see Jev: accept later",
                  "The Jev: accept is mid-line", "Jev accept", "Jevx: accept"):
            self.assertIsNone(js.parse_verdict_line(t), t)

    def test_prefixes(self):
        for pre in ("- ", "* ", "> ", "  ", "> - ", "\t* "):
            r = js.parse_verdict_line("body\n%sJev[r=%s]: accept — ok\nmore" % (pre, RID))
            self.assertEqual(r["verdict"], "accept", pre)
            self.assertEqual(r["reason"], "ok")

    def test_case_insensitive(self):
        r = js.parse_verdict_line("JEV[R=3FA9C1D2]: MODIFY — Why")
        self.assertEqual((r["id"], r["verdict"], r["reason"]), (RID, "modify", "Why"))

    def test_separators(self):
        for sep in ("—", "–", "-", ":", "--", " — ", " - ", ": "):
            r = js.parse_verdict_line("Jev: modify%s because" % sep)
            self.assertEqual(r["reason"], "because", repr(sep))
        self.assertEqual(js.parse_verdict_line("Jev: modify because")["reason"], "because")

    def test_reason_cap_and_strip(self):
        r = js.parse_verdict_line("Jev: reject — " + "x" * 500 + "   ")
        self.assertEqual(len(r["reason"]), js.REASON_CAP)
        self.assertEqual(js.REASON_CAP, 200)
        self.assertEqual(js.parse_verdict_line("Jev: accept —    spaced   ")["reason"], "spaced")

    def test_first_match_wins_and_unavailable(self):
        r = js.parse_verdict_line("Jev: reject — one\nJev: accept — two")
        self.assertEqual((r["verdict"], r["reason"]), ("reject", "one"))
        self.assertEqual(js.parse_verdict_line("Jev[r=%s]: unavailable — router=haiku" % RID)["verdict"],
                         "unavailable")

    def test_strip_verdict_line(self):
        self.assertEqual(js.strip_verdict_line("a\nJev: accept\nb\n- Jev[r=%s]: modify — x\nc" % RID), "a\nb\nc")
        self.assertEqual(js.strip_verdict_line("keep\r\n  line  \n"), "keep\r\n  line  \n")
        self.assertEqual(js.strip_verdict_line("no jev: here\nuse Jev: accept inline"),
                         "no jev: here\nuse Jev: accept inline")
        self.assertEqual(js.strip_verdict_line(None), "")
        self.assertEqual(js.strip_verdict_line("Jev: accept"), "")
        self.assertEqual(js.strip_verdict_line("x\nJev: accept\n"), "x\n")

    def test_format_line(self):
        self.assertEqual(js.format_line(RID, "modify", "why"), "Jev[r=%s]: modify — why" % RID)
        self.assertEqual(js.format_line(RID, "accept", ""), "Jev[r=%s]: accept" % RID)
        self.assertEqual(js.format_line("", "reject", "why"), "Jev: reject — why")
        self.assertEqual(js.format_line(None, "accept", ""), "Jev: accept")
        # round trip
        r = js.parse_verdict_line(js.format_line(RID, "modify", "why"))
        self.assertEqual((r["id"], r["verdict"], r["reason"]), (RID, "modify", "why"))


class BindingTests(unittest.TestCase):
    NAMED = ("codebase-search", "save-state-runner", "project-scaffolder", "Delegator", "Explore",
             "Plan", "statusline-setup", "claude-code-guide", "architecture-analyzer", "article-analyzer",
             "assemble-reviewer", "domain-analyzer", "file-analyzer", "graph-reviewer",
             "knowledge-graph-guide", "project-scanner", "tour-builder")

    def test_every_named_type_exempt(self):
        for t in self.NAMED:
            self.assertFalse(js.is_binding(t), t)
            self.assertFalse(js.is_binding(t.upper()), t)
        self.assertEqual({t.lower() for t in js.EXEMPT_TYPES}, {t.lower() for t in self.NAMED})

    def test_prefix_suffix(self):
        for t in ("critique-seo", "Critique-X", "council-fable", "caveman:cavecrew", "seo-critique",
                  "backend-critique"):
            self.assertFalse(js.is_binding(t), t)
        self.assertEqual(js.EXEMPT_PREFIXES, ("critique-", "council-", "caveman:"))
        self.assertEqual(js.EXEMPT_SUFFIXES, ("-critique", "-pd"))

    def test_pd_spawns_exempt(self):
        # F3 (PD decision 2026-10-19): *-pd identity spawns carry their own skills; exempt = no enforcement/feedback
        for t in ("demo-project-pd", "foo-pd", "Demo-PD", "example-pd"):
            self.assertFalse(js.is_binding(t), t)

    def test_coord_family_stays_binding(self):
        for t in ("coord", "mini-coord", "pd-coordinator"):
            self.assertTrue(js.is_binding(t), t)

    def test_fork_exempt(self):
        self.assertFalse(js.is_binding("general-purpose", fork=True))
        self.assertFalse(js.is_binding(None, fork=True))

    def test_binding(self):
        for t in ("general-purpose", "claude", "", None, "coord", "mini-coord", "pd-coordinator",
                  "unknown-thing", "critique", "Explorer", "councilor", "curator"):
            self.assertTrue(js.is_binding(t), repr(t))

    def test_emptying_constants_makes_all_binding(self):
        old = js.EXEMPT_TYPES, js.EXEMPT_PREFIXES, js.EXEMPT_SUFFIXES
        try:
            js.EXEMPT_TYPES = js.EXEMPT_PREFIXES = js.EXEMPT_SUFFIXES = ()
            self.assertTrue(js.is_binding("codebase-search"))
            self.assertTrue(js.is_binding("critique-x"))
        finally:
            js.EXEMPT_TYPES, js.EXEMPT_PREFIXES, js.EXEMPT_SUFFIXES = old


class NormaliseTests(unittest.TestCase):
    def test_rows(self):
        n = js.normalise_verdict
        self.assertEqual(n(["a", "b"], ["b", "a"]), "accept")
        self.assertEqual(n(["/a"], ["a"]), "accept")
        self.assertEqual(n(["a", "c"], ["a", "b"]), "modify")
        self.assertEqual(n(["c"], ["a", "b"]), "reject")
        self.assertEqual(n([], ["a"]), "reject")
        self.assertEqual(n([], []), "accept")
        self.assertEqual(n(["a"], []), "reject")

    def test_is_outage(self):
        self.assertFalse(js.is_outage(jev(router="jev")))
        self.assertFalse(js.is_outage(jev(router="passthrough")))
        self.assertTrue(js.is_outage(jev(router="haiku")))
        self.assertTrue(js.is_outage(jev(router="grep")))
        self.assertFalse(js.is_outage(jev(router="grep", confidential=True)))


class EvaluateTests(unittest.TestCase):
    def ev(self, j, s, line, **kw):
        kw.setdefault("route_id", RID)
        out = js.evaluate(j, s, line, **kw)
        self.assertEqual(set(out), {"decision", "spawn_verdict", "verdict_source", "reason", "inject_skills",
                                    "inject_line", "deny_message"})
        return out

    def assertDeny(self, out, rule):
        self.assertEqual(out["decision"], "deny")
        self.assertIsNone(out["spawn_verdict"])
        self.assertIsNone(out["verdict_source"])
        self.assertIsNone(out["inject_line"])
        self.assertEqual(out["inject_skills"], [])
        self.assertIn(rule, out["deny_message"])
        self.assertIn(RID, out["deny_message"])

    # row 1
    def test_outage_with_line(self):
        out = self.ev(jev(router="haiku"), ["x"], L("modify", "r"))
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]), ("pass", "reject", "explicit"))
        self.assertIsNone(out["inject_line"])
        self.assertEqual(out["inject_skills"], [])

    # row 2
    def test_outage_no_line(self):
        out = self.ev(jev(router="grep"), ["x"], None)
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                         ("rewrite", "unreviewed", "jev_unavailable"))
        self.assertEqual(out["inject_line"], "Jev[r=%s]: unavailable — router=grep" % RID)
        self.assertEqual(out["inject_skills"], [])

    def test_outage_flag_override(self):
        out = self.ev(jev(router="jev"), ["a", "b"], None, outage=True)
        self.assertEqual(out["verdict_source"], "jev_unavailable")
        out = self.ev(jev(router="haiku"), ["a", "b"], None, outage=False)
        self.assertEqual(out["verdict_source"], "auto_match")

    # row 3
    def test_accept_empty_spawner_injects_skills(self):
        out = self.ev(jev(), [], L("accept"))
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                         ("rewrite", "accept", "explicit"))
        self.assertEqual(out["inject_skills"], ["a", "b"])
        self.assertIsNone(out["inject_line"])  # line already carries the id

    def test_accept_empty_spawner_line_without_id_adds_id(self):
        out = self.ev(jev(), [], L("accept", "ok", rid=None))
        self.assertEqual(out["inject_skills"], ["a", "b"])
        self.assertEqual(out["inject_line"], "Jev[r=%s]: accept — ok" % RID)

    def test_reason_checks_precede_accept_rewrite(self):
        # Coord decision: low_confidence accept with no reason is denied even when S is empty
        out = self.ev(jev(gate="low_confidence"), [], L("accept"))
        self.assertDeny(out, "reason required on low_confidence")
        out = self.ev(jev(gate="low_confidence"), [], L("accept", "checked Jev list"))
        self.assertEqual((out["decision"], out["inject_skills"]), ("rewrite", ["a", "b"]))
        # gate pass: accept with empty S and no reason is still the row-3 rewrite
        self.assertEqual(self.ev(jev(), [], L("accept"))["decision"], "rewrite")
        # differing-skills accept on low_confidence without a reason: reason rule wins
        self.assertDeny(self.ev(jev(gate="low_confidence"), ["a"], L("accept")), "reason required on low_confidence")

    # row 4
    def test_accept_but_differs(self):
        self.assertDeny(self.ev(jev(), ["a"], L("accept")), "accept but Skills differ: use modify")
        self.assertDeny(self.ev(jev(skills=()), ["a"], L("accept")), "accept but Skills differ: use modify")

    # row 5
    def test_low_confidence_reason_required(self):
        for gate_kw in ({"gate": "low_confidence"}, {"none_fired": True}, {"confidential": True, "router": "grep"}):
            for v in ("modify", "reject", "accept"):
                out = self.ev(jev(**gate_kw), ["a", "b"], L(v))
                self.assertDeny(out, "reason required on low_confidence")

    # row 6
    def test_modify_reject_reason_required(self):
        for v in ("modify", "reject"):
            self.assertDeny(self.ev(jev(), ["a", "c"], L(v)), "reason required for modify/reject")

    # row 7
    def test_valid_line_passes(self):
        out = self.ev(jev(), ["a", "c"], L("modify", "tailwind"))
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]), ("pass", "modify", "explicit"))
        self.assertIsNone(out["inject_line"])
        self.assertEqual(out["reason"], "tailwind")
        out = self.ev(jev(), ["a", "b"], L("accept"))
        self.assertEqual((out["decision"], out["spawn_verdict"]), ("pass", "accept"))
        out = self.ev(jev(), ["z"], L("reject", "none fit"))
        self.assertEqual((out["decision"], out["spawn_verdict"]), ("pass", "reject"))
        out = self.ev(jev(gate="low_confidence"), ["a", "b"], L("accept", "checked"))
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]), ("pass", "accept", "explicit"))

    def test_valid_line_missing_id_rewrites(self):
        out = self.ev(jev(), ["a", "c"], L("modify", "why", rid=None))
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                         ("rewrite", "modify", "explicit"))
        self.assertEqual(out["inject_line"], "Jev[r=%s]: modify — why" % RID)
        self.assertEqual(out["inject_skills"], [])
        # no route id known -> nothing to add
        out = self.ev(jev(), ["a", "c"], L("modify", "why", rid=None), route_id="")
        self.assertEqual(out["decision"], "pass")

    def test_accept_both_empty_passes(self):
        out = self.ev(jev(skills=()), [], L("accept"))
        self.assertEqual((out["decision"], out["spawn_verdict"]), ("pass", "accept"))

    # row 8
    def test_no_line_default(self):
        out = self.ev(jev(), [], None)
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                         ("rewrite", "accept", "auto_default"))
        self.assertEqual(out["inject_skills"], ["a", "b"])
        self.assertEqual(out["inject_line"], "Jev[r=%s]: accept — auto: Jev default (gate pass)" % RID)

    # row 9
    def test_no_line_match(self):
        out = self.ev(jev(), ["b", "a"], None)
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                         ("rewrite", "accept", "auto_match"))
        self.assertEqual(out["inject_skills"], [])
        self.assertEqual(out["inject_line"], "Jev[r=%s]: accept — auto: matches Jev (gate pass)" % RID)

    # row 10
    def test_no_line_differs(self):
        self.assertDeny(self.ev(jev(), ["a"], None), "no Jev line and Skills differ from Jev")

    # row 11
    def test_no_line_low_confidence(self):
        for kw in ({"gate": "low_confidence"}, {"none_fired": True}, {"gate": None}):
            self.assertDeny(self.ev(jev(**kw), ["a", "b"], None), "no Jev line and gate is low_confidence")
        # J non-empty, S empty, low_confidence: still a deny (the spawner must say why it ignores Jev's picks)
        self.assertDeny(self.ev(jev(gate="low_confidence"), [], None), "no Jev line and gate is low_confidence")
        # S non-empty with J empty and no line: unchanged deny (F1 only covers empty/empty)
        self.assertDeny(self.ev(jev(skills=(), gate="low_confidence", none_fired=True), ["a"], None),
                        "no Jev line and gate is low_confidence")

    # F1: both empty + no line -> auto pass (rewrite injects the line so the recorder sees it)
    def test_no_line_both_empty_auto_empty(self):
        line = "Jev[r=%s]: accept — auto: Jev found nothing, spawner lists nothing" % RID
        for kw in ({"gate": "pass"}, {"gate": "low_confidence"}, {"none_fired": True},
                   {"gate": "low_confidence", "none_fired": True}, {"gate": None}):
            out = self.ev(jev(skills=(), **kw), [], None)
            self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                             ("rewrite", "accept", "auto_empty"), kw)
            self.assertEqual(out["inject_line"], line)
            self.assertEqual(out["inject_skills"], [])
            self.assertIsNone(out["deny_message"])
        # the injected line round-trips through the grammar
        self.assertEqual(js.parse_verdict_line(line)["verdict"], "accept")

    def test_no_line_both_empty_unchanged_when_line_present(self):
        out = self.ev(jev(skills=(), gate="low_confidence", none_fired=True), [], L("accept"))
        self.assertDeny(out, "reason required on low_confidence")
        out = self.ev(jev(skills=(), gate="low_confidence"), [], L("accept", "nothing fits"))
        self.assertEqual((out["decision"], out["verdict_source"]), ("pass", "explicit"))

    def test_both_empty_outage_still_unavailable(self):
        out = self.ev(jev(skills=(), router="haiku"), [], None)
        self.assertEqual(out["verdict_source"], "jev_unavailable")

    # F2: confidential (router=grep, so not an outage) + no line -> rewrite unreviewed, never a deny
    def test_confidential_no_line_rewrites_local(self):
        line = "Jev[r=%s]: unavailable — confidential: routed locally (grep), not reviewed" % RID
        for j_skills, s in ((("a", "b"), ["a", "b"]), (("a", "b"), []), (("a", "b"), ["z"]), ((), []), ((), ["z"])):
            out = self.ev(jev(skills=j_skills, confidential=True, router="grep", gate="low_confidence",
                              none_fired=True), s, None)
            self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                             ("rewrite", "unreviewed", "confidential_local"), (j_skills, s))
            self.assertEqual(out["inject_line"], line)
            self.assertEqual(out["inject_skills"], [])
            self.assertIsNone(out["deny_message"])
        out = self.ev(jev(confidential=True, router="grep"), ["a", "b"], None)  # even with gate=pass
        self.assertEqual(out["verdict_source"], "confidential_local")
        self.assertEqual(js.parse_verdict_line(line)["verdict"], "unavailable")

    def test_confidential_with_line_unchanged(self):
        j = jev(confidential=True, router="grep")
        self.assertDeny(self.ev(j, ["a", "b"], L("accept")), "reason required on low_confidence")
        out = self.ev(j, ["a", "b"], L("accept", "checked"))
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]), ("pass", "accept", "explicit"))
        out = self.ev(j, ["z"], L("reject", "none fit"))
        self.assertEqual((out["decision"], out["verdict_source"]), ("pass", "explicit"))

    # row 12
    def test_deny_cap_loop_guard(self):
        out = self.ev(jev(), ["a", "c"], None, denies=2)
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]), ("pass", "modify", "deny_cap"))
        self.assertIsNone(out["deny_message"])
        self.assertIsNone(out["inject_line"])
        out = self.ev(jev(gate="low_confidence"), ["z"], L("reject"), denies=5)
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]), ("pass", "reject", "deny_cap"))
        out = self.ev(jev(), ["a"], None, denies=1)
        self.assertEqual(out["decision"], "deny")  # below the cap
        # non-deny rows are unaffected by denies
        out = self.ev(jev(), ["a", "b"], None, denies=9)
        self.assertEqual(out["verdict_source"], "auto_match")

    def test_missing_keys_tolerated(self):
        out = js.evaluate({}, [], None)
        self.assertIn(out["decision"], ("pass", "rewrite", "deny"))
        out = js.evaluate(None, None, None)
        self.assertEqual(out["decision"], "rewrite")  # outage (router None) and no line

    def test_deny_message_content(self):
        j = jev(skills=("frontend", "tailwind"), gate="low_confidence", router="haiku")
        msg = js.build_deny_message(RID, j, ["backend"], "some rule", role="lead")
        for needle in (RID, "gate=low_confidence", "router=haiku", "/frontend, /tailwind", "/backend", "some rule",
                       "Jev[r=%s]: accept — " % RID, "Jev[r=%s]: modify — " % RID, "Jev[r=%s]: reject — " % RID,
                       'python3 %s --role lead "<task>"' % os.path.join(SCRIPTS, "skill-route.py"),
                       "Re-issue the same Agent call with the line added"):
            self.assertIn(needle, msg)
        self.assertIn("--role exec", js.build_deny_message(RID, j, [], "r"))
        self.assertIn("(none)", js.build_deny_message(RID, {}, [], "r"))
        for line in msg.splitlines():
            if line.startswith("Jev["):
                self.assertIsNotNone(js.parse_verdict_line(line))


class GateDenyReplayTests(unittest.TestCase):
    """The five 2026-10-19 JEV_SPAWN_DENY evidence rows (example session) replayed through the core."""

    def test_rows_1_2_pd_spawn_exempt(self):
        # main -> demo-project-pd, no Jev line, low_confidence: now exempt, the gate never evaluates it
        self.assertFalse(js.is_binding("demo-project-pd"))
        self.assertFalse(js.is_binding("demo-project-pd", fork=False))

    def test_row_3_accept_but_skills_differ_still_denies(self):
        self.assertTrue(js.is_binding("coord"))
        j = jev(skills=("supabase-sql",), gate="pass")
        s = ["supabase-sql", "superpowers-test-driven-development"]
        out = js.evaluate(j, s, L("accept"), route_id=RID)
        self.assertEqual(out["decision"], "deny")
        self.assertIn("accept but Skills differ", out["deny_message"])

    def test_row_4_empty_empty_none_fired_passes(self):
        self.assertTrue(js.is_binding("coord"))
        j = jev(skills=(), gate="low_confidence", none_fired=True)
        out = js.evaluate(j, [], None, route_id=RID)
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                         ("rewrite", "accept", "auto_empty"))
        self.assertEqual(out["inject_line"],
                         "Jev[r=%s]: accept — auto: Jev found nothing, spawner lists nothing" % RID)

    def test_row_5_confidential_grep_rewrites_unreviewed(self):
        self.assertTrue(js.is_binding("coord"))
        j = jev(skills=("superpowers-systematic-debugging", "superpowers-test-driven-development",
                        "superpowers-writing-plans"),
                gate="low_confidence", router="grep", none_fired=True, confidential=True)
        out = js.evaluate(j, [], None, route_id=RID)
        self.assertEqual((out["decision"], out["spawn_verdict"], out["verdict_source"]),
                         ("rewrite", "unreviewed", "confidential_local"))
        self.assertEqual(out["inject_skills"], [])
        self.assertEqual(out["inject_line"],
                         "Jev[r=%s]: unavailable — confidential: routed locally (grep), not reviewed" % RID)


class ApplyDecisionTests(unittest.TestCase):
    def test_append_line(self):
        d = {"inject_line": "Jev[r=%s]: accept" % RID, "inject_skills": []}
        self.assertEqual(js.apply_decision("do it", d), "do it\nJev[r=%s]: accept" % RID)
        self.assertEqual(js.apply_decision("do it\n", d), "do it\nJev[r=%s]: accept" % RID)
        self.assertEqual(js.apply_decision("", d), "Jev[r=%s]: accept" % RID)

    def test_replace_line(self):
        d = {"inject_line": "Jev[r=%s]: modify — why" % RID, "inject_skills": []}
        out = js.apply_decision("top\n- Jev: modify — why\nbottom", d)
        self.assertEqual(out, "top\nJev[r=%s]: modify — why\nbottom" % RID)
        self.assertEqual(js.parse_verdict_line(out)["id"], RID)

    def test_prepend_skills(self):
        d = {"inject_line": None, "inject_skills": ["a", "b"]}
        self.assertEqual(js.apply_decision("task", d), "Skills: /a, /b\ntask")

    def test_never_duplicates_skills_line(self):
        d = {"inject_line": None, "inject_skills": ["a"]}
        p = "intro\nSkills: /z\ntask"
        self.assertEqual(js.apply_decision(p, d), p)
        p = "- skills to load: /z"
        self.assertEqual(js.apply_decision(p, d), p)

    def test_noop_and_both(self):
        self.assertEqual(js.apply_decision("x", {"inject_line": None, "inject_skills": []}), "x")
        self.assertEqual(js.apply_decision(None, {}), "")
        out = js.apply_decision("task", {"inject_line": "Jev[r=%s]: accept" % RID, "inject_skills": ["a"]})
        self.assertEqual(out, "Skills: /a\ntask\nJev[r=%s]: accept" % RID)

    def test_roundtrip_with_evaluate(self):
        d = js.evaluate(jev(), [], None, route_id=RID)
        out = js.apply_decision("do the thing", d)
        self.assertIn("Skills: /a, /b", out)
        self.assertEqual(js.parse_verdict_line(out)["id"], RID)
        self.assertEqual(js.strip_verdict_line(out), "Skills: /a, /b\ndo the thing")


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jev-spawn-test-")
        self._old = os.environ.get("SKILL_ROUTE_STATE_DIR")
        os.environ["SKILL_ROUTE_STATE_DIR"] = self.tmp

    def tearDown(self):
        if self._old is None:
            os.environ.pop("SKILL_ROUTE_STATE_DIR", None)
        else:
            os.environ["SKILL_ROUTE_STATE_DIR"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    RES = {"skills": ["frontend", "tailwind"], "gate": "pass", "router": "jev", "domain": "ui", "jev_down": False,
           "model": "sonnet", "tools": ["Read"], "scores": {"a": 1}}
    META = {"none_fired": False, "confidential": False, "role": "exec"}

    def path(self, rid):
        return os.path.join(js.cache_dir(), rid + ".json")

    def test_cache_stores_lang_from_res(self):
        # effort policy (model-pin.py reads the entry directly): content + lang vi -> xhigh
        rid = js.cache_put(dict(self.RES, domain="writing-en", lang="vi"), self.META)
        self.assertEqual(js.cache_get(rid)["lang"], "vi")
        rid = js.cache_put(dict(self.RES, lang="en"), self.META)
        self.assertEqual(js.cache_get(rid)["lang"], "en")

    def test_cache_lang_absent_is_none(self):
        self.assertIsNone(js.cache_get(js.cache_put(self.RES, self.META))["lang"])

    def test_cache_dir_reads_env_at_call_time(self):
        self.assertEqual(js.cache_dir(), os.path.join(self.tmp, "jev-route-cache"))
        os.environ["SKILL_ROUTE_STATE_DIR"] = self.tmp + "-b"
        self.assertEqual(js.cache_dir(), os.path.join(self.tmp + "-b", "jev-route-cache"))
        os.environ.pop("SKILL_ROUTE_STATE_DIR")
        saved = os.environ.get("AGENCY_HOME")
        os.environ["AGENCY_HOME"] = self.tmp + "-root"   # default state dir = {root}/state/skill-route
        try:
            self.assertEqual(js.cache_dir(), os.path.join(self.tmp + "-root", "state", "skill-route", "jev-route-cache"))
            self.assertEqual(js.spawner_dir(), os.path.join(self.tmp + "-root", "state", "skill-route", "jev-gate-denies"))
        finally:
            if saved is None:
                os.environ.pop("AGENCY_HOME", None)
            else:
                os.environ["AGENCY_HOME"] = saved

    def test_put_get_roundtrip_and_key_set(self):
        rid = js.cache_put(dict(self.RES, task="SECRET TASK TEXT"), dict(self.META, text="SECRET TASK TEXT"))
        self.assertRegex(rid, r"^[0-9a-f]{8}$")
        e = js.cache_get(rid)
        self.assertEqual(set(e), {"route_id", "ts", "skills", "gate", "router", "domain", "lang", "role", "none_fired",
                                  "confidential", "jev_down", "denies"})
        self.assertEqual((e["route_id"], e["skills"], e["gate"], e["router"], e["domain"], e["role"], e["denies"]),
                         (rid, ["frontend", "tailwind"], "pass", "jev", "ui", "exec", 0))
        self.assertFalse(e["none_fired"] or e["confidential"] or e["jev_down"])
        self.assertAlmostEqual(e["ts"], time.time(), delta=5)
        with open(self.path(rid), encoding="utf-8") as f:
            self.assertNotIn("SECRET", f.read())
        # no leftover tmp files
        self.assertEqual([n for n in os.listdir(js.cache_dir()) if n.startswith(".tmp-")], [])

    def test_meta_flags_and_none_meta(self):
        rid = js.cache_put(dict(self.RES, jev_down=True), {"none_fired": True, "confidential": True, "role": "lead"})
        e = js.cache_get(rid)
        self.assertTrue(e["none_fired"] and e["confidential"] and e["jev_down"])
        self.assertEqual(e["role"], "lead")
        rid = js.cache_put(self.RES)
        e = js.cache_get(rid)
        self.assertIsNone(e["role"])
        self.assertFalse(e["none_fired"])

    def test_ids_unique(self):
        ids = {js.cache_put(self.RES, self.META) for _ in range(30)}
        self.assertEqual(len(ids), 30)

    def test_get_validates_id(self):
        for bad in (None, "", "zzzzzzzz", "ABCDEF12", "3fa9c1d", "3fa9c1d2x", "../../etc", 12345678):
            self.assertIsNone(js.cache_get(bad), repr(bad))
        self.assertIsNone(js.cache_get("deadbeef"))  # valid id, missing file

    def test_get_does_not_create_dirs(self):
        shutil.rmtree(self.tmp)
        self.assertIsNone(js.cache_get("deadbeef"))
        self.assertFalse(os.path.exists(self.tmp))

    def test_ttl_expiry_by_ts(self):
        rid = js.cache_put(self.RES, self.META)
        p = self.path(rid)
        with open(p) as f:
            e = json.load(f)
        e["ts"] = time.time() - js.CACHE_TTL_SECONDS - 60
        _w(p, json.dumps(e))
        self.assertIsNone(js.cache_get(rid))

    def test_ttl_expiry_by_mtime(self):
        rid = js.cache_put(self.RES, self.META)
        old = time.time() - js.CACHE_TTL_SECONDS - 60
        os.utime(self.path(rid), (old, old))
        self.assertIsNone(js.cache_get(rid))
        self.assertEqual(js.CACHE_TTL_SECONDS, 48 * 3600)

    def test_within_ttl_still_valid(self):
        rid = js.cache_put(self.RES, self.META)
        old = time.time() - js.CACHE_TTL_SECONDS + 600
        os.utime(self.path(rid), (old, old))
        self.assertIsNotNone(js.cache_get(rid))

    def test_corrupt_file_returns_none(self):
        rid = js.cache_put(self.RES, self.META)
        open(self.path(rid), "w").write("{not json")
        self.assertIsNone(js.cache_get(rid))
        open(self.path(rid), "w").write("[1,2]")
        self.assertIsNone(js.cache_get(rid))
        open(self.path(rid), "w").write("")
        self.assertIsNone(js.cache_get(rid))
        self.assertEqual(js.cache_bump_denies(rid), 0)

    def test_prune_expired_over_threshold(self):
        d = js.cache_dir()
        os.makedirs(d)
        old = time.time() - js.CACHE_TTL_SECONDS - 3600
        for i in range(js.CACHE_PRUNE_THRESHOLD + 5):
            p = os.path.join(d, "%08x.json" % i)
            _w(p, "{}")
            os.utime(p, (old, old))
        rid = js.cache_put(self.RES, self.META)
        left = [n for n in os.listdir(d) if n.endswith(".json")]
        self.assertEqual(left, [rid + ".json"])

    def test_prune_drops_oldest_when_still_over(self):
        d = js.cache_dir()
        os.makedirs(d)
        now = time.time()
        n = js.CACHE_PRUNE_THRESHOLD + 20
        for i in range(n):
            p = os.path.join(d, "%08x.json" % i)
            _w(p, "{}")
            t = now - 3600 + i  # all fresh, increasing age order: i=0 oldest
            os.utime(p, (t, t))
        js.cache_put(self.RES, self.META)
        left = {x for x in os.listdir(d) if x.endswith(".json")}
        self.assertEqual(len(left), js.CACHE_PRUNE_THRESHOLD)
        self.assertNotIn("%08x.json" % 0, left)
        self.assertIn("%08x.json" % (n - 1), left)

    def test_no_prune_under_threshold(self):
        d = js.cache_dir()
        os.makedirs(d)
        old = time.time() - js.CACHE_TTL_SECONDS - 3600
        p = os.path.join(d, "%08x.json" % 1)
        _w(p, "{}")
        os.utime(p, (old, old))
        js.cache_put(self.RES, self.META)
        self.assertTrue(os.path.exists(p))  # cheap path: not pruned below the threshold

    def test_bump_denies(self):
        rid = js.cache_put(self.RES, self.META)
        self.assertEqual(js.cache_bump_denies(rid), 1)
        self.assertEqual(js.cache_bump_denies(rid), 2)
        self.assertEqual(js.cache_get(rid)["denies"], 2)
        e = js.cache_get(rid)
        self.assertEqual(e["skills"], ["frontend", "tailwind"])
        self.assertEqual([n for n in os.listdir(js.cache_dir()) if n.startswith(".tmp-")], [])

    def test_bump_denies_failures(self):
        self.assertEqual(js.cache_bump_denies("deadbeef"), 0)
        self.assertEqual(js.cache_bump_denies("nope"), 0)
        self.assertEqual(js.cache_bump_denies(None), 0)

    def test_bump_denies_concurrent_threads(self):
        import threading
        rid = js.cache_put(self.RES, self.META)
        got = []
        ts = [threading.Thread(target=lambda: got.append(js.cache_bump_denies(rid))) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(got), list(range(1, 9)))
        self.assertEqual(js.cache_get(rid)["denies"], 8)

    def test_unwritable_dir_never_raises(self):
        blocker = os.path.join(self.tmp, "blocker")
        _w(blocker, "x")
        os.environ["SKILL_ROUTE_STATE_DIR"] = os.path.join(blocker, "sub")  # a file in the path
        self.assertEqual(js.cache_put(self.RES, self.META), "")
        self.assertIsNone(js.cache_get(RID))
        self.assertEqual(js.cache_bump_denies(RID), 0)

    def test_garbage_input_never_raises(self):
        self.assertTrue(js.cache_put(None, None))  # empty contract still caches
        self.assertEqual(js.cache_put({"skills": object()}, None), "")
        self.assertEqual(js.cache_put("not a dict", 5), "")


class SpawnerGuardTests(unittest.TestCase):
    """Second deny loop-guard: per spawner + task (jev-gate-denies/<key>.json, TTL 1h). Temp state dir only."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jev-spawner-guard-")
        self._old = os.environ.get("SKILL_ROUTE_STATE_DIR")
        os.environ["SKILL_ROUTE_STATE_DIR"] = self.tmp

    def tearDown(self):
        if self._old is None:
            os.environ.pop("SKILL_ROUTE_STATE_DIR", None)
        else:
            os.environ["SKILL_ROUTE_STATE_DIR"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, key):
        return os.path.join(js.spawner_dir(), key + ".json")

    def test_key_shape_and_determinism(self):
        k = js.spawner_key("sp-1", "Build a landing page")
        self.assertRegex(k, r"^[0-9a-f]{16}$")
        self.assertEqual(k, js.spawner_key("sp-1", "Build a landing page"))

    def test_key_separates_spawner_and_task(self):
        a = js.spawner_key("sp-1", "Build a landing page")
        self.assertNotEqual(a, js.spawner_key("sp-2", "Build a landing page"))
        self.assertNotEqual(a, js.spawner_key("sp-1", "Build a pricing page"))
        self.assertEqual(js.spawner_key("", "t"), js.spawner_key("root", "t"))   # empty spawner = root
        self.assertEqual(js.spawner_key(None, "t"), js.spawner_key("root", "t"))
        # the NUL separator keeps (a, bc) and (ab, c) apart
        self.assertNotEqual(js.spawner_key("a", "bc"), js.spawner_key("ab", "c"))

    def test_key_never_raises(self):
        self.assertRegex(js.spawner_key(object(), None), r"^[0-9a-f]{16}$")

    def test_denies_start_at_zero_and_count_up(self):
        k = js.spawner_key("sp-1", "task")
        self.assertEqual(js.spawner_denies(k), 0)
        self.assertEqual(js.spawner_bump_denies(k), 1)
        self.assertEqual(js.spawner_denies(k), 1)
        self.assertEqual(js.spawner_bump_denies(k), 2)
        self.assertEqual(js.spawner_denies(k), 2)

    def test_independent_per_key(self):
        a, b = js.spawner_key("sp-1", "task"), js.spawner_key("sp-2", "task")
        js.spawner_bump_denies(a)
        js.spawner_bump_denies(a)
        self.assertEqual(js.spawner_denies(a), 2)
        self.assertEqual(js.spawner_denies(b), 0)

    def test_ttl_expiry_resets_count(self):
        k = js.spawner_key("sp-1", "task")
        js.spawner_bump_denies(k)
        js.spawner_bump_denies(k)
        old = time.time() - js.SPAWNER_TTL_SECONDS - 60
        with open(self.path(k), "w") as f:
            json.dump({"key": k, "ts": old, "denies": 2}, f)
        os.utime(self.path(k), (old, old))
        self.assertEqual(js.spawner_denies(k), 0)
        self.assertEqual(js.spawner_bump_denies(k), 1)      # a bump on an expired entry restarts at 1

    def test_inside_ttl_still_counts(self):
        k = js.spawner_key("sp-1", "task")
        recent = time.time() - js.SPAWNER_TTL_SECONDS + 300
        os.makedirs(js.spawner_dir(), exist_ok=True)
        with open(self.path(k), "w") as f:
            json.dump({"key": k, "ts": recent, "denies": 2}, f)
        os.utime(self.path(k), (recent, recent))
        self.assertEqual(js.spawner_denies(k), 2)

    def test_ttl_is_one_hour(self):
        self.assertEqual(js.SPAWNER_TTL_SECONDS, 3600)

    def test_corrupt_file_is_zero(self):
        k = js.spawner_key("sp-1", "task")
        os.makedirs(js.spawner_dir())
        for junk in ("{not json", "[]", "null", '{"denies": "x"}', ""):
            with open(self.path(k), "w") as f:
                f.write(junk)
            self.assertEqual(js.spawner_denies(k), 0, junk)
        with open(self.path(k), "w") as f:
            f.write("{garbage")
        self.assertEqual(js.spawner_bump_denies(k), 1)       # corrupt counts as 0 and is overwritten
        self.assertEqual(js.spawner_denies(k), 1)

    def test_bad_key_is_inert(self):
        for bad in (None, "", "nope", "../../etc/passwd", 5, "x" * 16):
            self.assertEqual(js.spawner_denies(bad), 0)
            self.assertEqual(js.spawner_bump_denies(bad), 0)
        self.assertFalse(os.path.exists(js.spawner_dir()))

    def test_atomic_file_shape_and_location(self):
        k = js.spawner_key("sp-1", "task")
        js.spawner_bump_denies(k)
        self.assertEqual(os.path.dirname(self.path(k)), os.path.join(self.tmp, "jev-gate-denies"))
        with open(self.path(k)) as f:
            e = json.load(f)
        self.assertEqual((e["key"], e["denies"]), (k, 1))
        self.assertNotIn("task", json.dumps(e))               # no task text stored
        self.assertEqual([n for n in os.listdir(js.spawner_dir()) if n.startswith(".tmp-")], [])

    def test_prune_removes_expired_over_threshold(self):
        os.makedirs(js.spawner_dir())
        old = time.time() - js.SPAWNER_TTL_SECONDS - 60
        for i in range(js.CACHE_PRUNE_THRESHOLD + 5):
            p = os.path.join(js.spawner_dir(), "%016x.json" % i)
            with open(p, "w") as f:
                json.dump({"key": "%016x" % i, "ts": old, "denies": 1}, f)
            os.utime(p, (old, old))
        js.spawner_bump_denies(js.spawner_key("sp-1", "task"))
        left = [n for n in os.listdir(js.spawner_dir()) if n.endswith(".json")]
        self.assertLessEqual(len(left), js.CACHE_PRUNE_THRESHOLD)
        self.assertTrue(os.path.exists(self.path(js.spawner_key("sp-1", "task"))))

    def test_unwritable_dir_never_raises(self):
        with open(os.path.join(self.tmp, "jev-gate-denies"), "w") as f:     # a FILE where the dir should be
            f.write("x")
        k = js.spawner_key("sp-1", "task")
        self.assertEqual(js.spawner_bump_denies(k), 0)
        self.assertEqual(js.spawner_denies(k), 0)


class ImportSideEffectTests(unittest.TestCase):
    def test_import_creates_nothing(self):
        import subprocess
        tmp = tempfile.mkdtemp(prefix="jev-spawn-import-")
        try:
            env = dict(os.environ, SKILL_ROUTE_STATE_DIR=os.path.join(tmp, "state"))
            code = "import sys; sys.path.insert(0, %r); import jev_spawn" % SCRIPTS
            subprocess.check_call([sys.executable, "-c", code], env=env)
            self.assertEqual(os.listdir(tmp), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
