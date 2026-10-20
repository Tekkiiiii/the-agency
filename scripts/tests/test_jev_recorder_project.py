"""Tests for the spawn recorder's project resolution (skill-route.py _spawn_project, gap 2). Order under test:
1 prompt `Project:` path (longest prefix) or bare table slug > 2 parent_agent `{slug}-pd` > 3 subagent_type `{slug}-pd`
> 4 CLAUDE_PROJECT_DIR/cwd longest prefix > 5 "global". Never raises. Temp dirs only (RouterEnv/RecEnv env overrides:
JEV_FEEDBACK_LOG, SKILL_ROUTE_MEDIUM_TERM, ...), so the real ~/.claude/logs/jev-feedback.jsonl is never written.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_recorder_project*' -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_jev_recorder as tj  # noqa: E402  (RecEnv, payload, SpawnProjectTests.table)

sr = tj.sr
RecEnv = tj.RecEnv
payload = tj.payload


class ProjectResolutionTests(unittest.TestCase):
    def setUp(self):
        self.e = RecEnv()
        self.e.__enter__()
        self.addCleanup(self.e.__exit__, None, None, None)
        self.base = os.path.join(self.e.tmp, "projects")
        self.rows = [("alpha", self.base + "/alpha/memory/"), ("alpha-sub", self.base + "/alpha/sub"),
                     ("beta", self.base + "/beta/memory/"), ("gamma", "~/zz-gamma-proj/memory/"),
                     ("social-feed", self.base + "/content-pipeline/memory/")]
        tj.SpawnProjectTests().table(self.e, self.rows)
        os.environ["CLAUDE_PROJECT_DIR"] = self.e.tmp + "/elsewhere"      # not under any project

    def res(self, data=None, prompt=""):
        return sr._spawn_project(data if data is not None else {}, prompt)

    # branch 1: prompt path / bare slug
    def test_prompt_path_resolves(self):
        p = "Project: alpha -- %s/alpha/\nTask: do it" % self.base
        self.assertEqual(self.res({}, p), "alpha")

    def test_prompt_path_longest_prefix_and_boundary(self):
        self.assertEqual(self.res({}, "Project: %s/alpha/sub/deep/file.py" % self.base), "alpha-sub")
        self.assertEqual(self.res({}, "Project: %s/alpha/src" % self.base), "alpha")
        self.assertEqual(self.res({}, "Project: %s/alphabet" % self.base), "global")     # not a path-boundary match

    def test_prompt_path_memory_suffix_and_tilde(self):
        self.assertEqual(self.res({}, "Project: %s/beta/memory/" % self.base), "beta")
        self.assertEqual(self.res({}, "Project: gamma -- ~/zz-gamma-proj/"), "gamma")
        self.assertEqual(self.res({}, "Project: ~/zz-gamma-proj/sub"), "gamma")

    def test_prompt_path_slug_differs_from_dir(self):
        self.assertEqual(self.res({}, "Project: %s/content-pipeline/" % self.base), "social-feed")

    def test_prompt_bare_slug(self):
        self.assertEqual(self.res({}, "Project: beta\nTask"), "beta")
        self.assertEqual(self.res({}, "intro\n  project: beta -- the beta thing\nTask"), "beta")

    def test_unknown_slug_and_path_fall_through(self):
        self.assertEqual(self.res({}, "Project: nonesuch -- /nowhere/at/all"), "global")
        self.assertEqual(self.res({"parent_agent": "gamma-pd"}, "Project: nonesuch"), "gamma")

    def test_no_project_line_is_not_scanned(self):
        # a path mentioned in the body is not a Project: declaration
        self.assertEqual(self.res({}, "see %s/alpha/x for context" % self.base), "global")

    # branch 2 / 3
    def test_parent_agent(self):
        self.assertEqual(self.res({"parent_agent": "beta-pd"}), "beta")
        self.assertEqual(self.res({"parent_agent": "social-feed-pd"}), "social-feed")

    def test_subagent_type(self):
        self.assertEqual(self.res({"subagent_type": "gamma-pd"}), "gamma")

    def test_unknown_pd_falls_through(self):
        self.assertEqual(self.res({"parent_agent": "zzz-pd", "subagent_type": "yyy-pd"}), "global")
        self.assertEqual(self.res({"parent_agent": "zzz-pd", "subagent_type": "beta-pd"}), "beta")
        self.assertEqual(self.res({"parent_agent": "beta", "subagent_type": "general-purpose"}), "global")  # no -pd

    # branch 4 / 5
    def test_cwd_fallback_and_global(self):
        os.environ["CLAUDE_PROJECT_DIR"] = self.base + "/alpha/sub/x"
        self.assertEqual(self.res({"parent_agent": "zzz-pd"}, "no project here"), "alpha-sub")
        self.assertEqual(sr._spawn_project(), "alpha-sub")                    # legacy no-arg form still works
        os.environ["CLAUDE_PROJECT_DIR"] = self.e.tmp + "/elsewhere"
        self.assertEqual(self.res({}, ""), "global")

    # precedence
    def test_precedence_chain(self):
        os.environ["CLAUDE_PROJECT_DIR"] = self.base + "/alpha"                # branch 4 = alpha
        data = {"parent_agent": "beta-pd", "subagent_type": "gamma-pd"}
        self.assertEqual(self.res(data, "Project: %s/alpha/sub" % self.base), "alpha-sub")   # 1 beats all
        self.assertEqual(self.res(data, "Project: beta"), "beta")
        self.assertEqual(self.res(data, ""), "beta")                           # 2 beats 3 and 4
        self.assertEqual(self.res({"subagent_type": "gamma-pd"}, ""), "gamma")  # 3 beats 4
        self.assertEqual(self.res({}, ""), "alpha")                             # 4 beats 5
        self.assertEqual(self.res(data, "Project: gamma"), "gamma")             # 1 (slug) beats 2

    def test_precedence_prompt_beats_parent(self):
        self.assertEqual(self.res({"parent_agent": "beta-pd"}, "Project: alpha"), "alpha")

    # never raises
    def test_garbage_never_raises(self):
        for data, prompt in ((None, None), ("str", 5), ([], {}), ({"parent_agent": 7, "subagent_type": ["x"]}, b"\xff"),
                             ({"parent_agent": None}, "Project:"), ({}, "Project: \x00\x00 ~"), ({}, "Project: ~"),
                             ({}, "Project: " + "/" * 5000), ({"parent_agent": "-pd"}, "Project: --")):
            try:
                out = sr._spawn_project(data, prompt)
            except Exception as exc:  # noqa: BLE001
                self.fail("raised %r for %r" % (exc, (data, prompt)))
            self.assertIsInstance(out, str)

    def test_missing_table_file_falls_to_global(self):
        os.remove(self.e.medium_term)
        self.assertEqual(self.res({"parent_agent": "beta-pd"}, "Project: beta"), "global")


class RecorderEndToEndTests(unittest.TestCase):
    def test_shadow_run_record_project_from_prompt(self):
        with RecEnv() as e:
            tj.SpawnProjectTests().table(e, [("demo-project", "~/.claude/projects/demo-project/memory/")])
            os.environ["CLAUDE_PROJECT_DIR"] = os.path.expanduser("~/.claude")       # the real-world PD cwd
            e.record(payload("Skills: /frontend\nProject: demo-project -- ~/.claude/projects/demo-project/\nBuild",
                             parent_agent="x"))
            (fb,) = e.feedbacks()
            self.assertEqual(fb["project"], "demo-project")
            self.assertEqual(e.valid(fb), [])
            self.assertTrue(e.feedback_log.startswith(e.tmp))

    def test_shadow_run_record_project_from_parent_and_absent_keys(self):
        with RecEnv() as e:
            tj.SpawnProjectTests().table(e, [("billing-app", "/home/dev/projects/billing-app/memory/")])
            os.environ["CLAUDE_PROJECT_DIR"] = os.path.expanduser("~/.claude")
            e.record(payload("Skills: /frontend\nBuild", parent_agent="billing-app-pd"))
            # a {slug}-pd subagent_type is exempt (F3): shadow row only, NO feedback record
            e.record(payload("Skills: /frontend\nBuild 2", parent_agent=None, subagent_type="billing-app-pd"))
            e.record(payload("Skills: /frontend\nBuild 3", parent_agent=None))
            self.assertEqual([f["project"] for f in e.feedbacks()], ["billing-app", "global"])


if __name__ == "__main__":
    unittest.main()
