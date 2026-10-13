#!/usr/bin/env python3
"""Tests for hooks/lib/spawn_project.py (shared spawn -> project -> spawns.jsonl resolution).

Temp dirs and env overrides only (SPAWN_MEDIUM_TERM, SPAWN_LOG_FILE, SPAWN_LEDGER_EXTRA_LOGS,
CLAUDE_PROJECT_DIR, an explicit home=); the real logs and the real medium-term.md are never touched.
Run from the repo root: python3 -m unittest discover -s hooks/tests -p 'test_spawn_project.py'
"""
import importlib.util
import os
import shutil
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("spawn_project", os.path.join(HERE, "..", "lib", "spawn_project.py"))
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="spawn-project-test-"))
        self.home = os.path.join(self.tmp, "home")
        self.x = os.path.join(self.tmp, "x")
        self.tilde_root = os.path.join(self.tmp, "with~tilde")
        os.makedirs(os.path.join(self.home, ".claude", "memory"))
        self.mt = os.path.join(self.tmp, "medium-term.md")
        with open(self.mt, "w") as f:
            f.write("# Medium-Term\n\n| Project | Memory Path | PD | Flag |\n|---|---|---|---|\n")
            f.write("| alpha | `%s/alpha/memory/` | alpha-pd | active |\n" % self.x)
            f.write("| alpha-nested | `%s/alpha/nested/memory/` | alpha-nested-pd | active |\n" % self.x)
            f.write("| beta | `~/.claude/projects/beta/memory/` | beta-pd | active |\n")
            f.write("| tilde | `%s/memory/` | tilde-pd | active |\n" % self.tilde_root)
            f.write("| bare | `~/.claude/projects/bare/` | - | dormant |\n")
            f.write("| tracked | tracked under `alpha` project | - | dormant |\n")
        self.env = mock.patch.dict(os.environ, {"SPAWN_MEDIUM_TERM": self.mt, "CLAUDE_PROJECT_DIR": self.tmp})
        self.env.start()
        for k in ("SPAWN_LOG_FILE", "SPAWN_LEDGER_EXTRA_LOGS", "AGENCY_HOME", "CLAUDE_CONFIG_DIR"):
            os.environ.pop(k, None)  # the agency root must come from home=, never from the caller's env

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def slug(self, data=None, prompt=None):
        return sp.spawn_project(data, prompt, home=self.home)

    def log(self, data=None):
        return sp.resolve_log_file(data, home=self.home)

    def glog(self):
        return os.path.join(self.home, ".claude", "logs", "spawns.jsonl")


class ResolutionOrder(Base):
    def test_project_line_with_path(self):
        p = "Project: system -- %s/alpha/sub/\nrest" % self.x
        self.assertEqual(self.slug({}, p), "alpha")

    def test_project_line_with_tilde_path(self):
        self.assertEqual(self.slug({}, "Project: beta -- ~/.claude/projects/beta/memory/"), "beta")
        self.assertEqual(self.slug({}, "Project: ~/.claude/projects/beta/"), "beta")

    def test_project_line_slug_first_word(self):
        self.assertEqual(self.slug({}, "intro\nProject: beta\nbody"), "beta")
        self.assertEqual(self.slug({}, "Project: beta -- anything"), "beta")

    def test_project_line_path_wins_over_first_word(self):
        self.assertEqual(self.slug({}, "Project: alpha -- ~/.claude/projects/beta/"), "beta")

    def test_parent_agent_pd(self):
        self.assertEqual(self.slug({"parent_agent": "beta-pd"}, ""), "beta")

    def test_subagent_type_pd(self):
        self.assertEqual(self.slug({"subagent_type": "alpha-pd"}, ""), "alpha")

    def test_cwd_longest_prefix(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.x + "/alpha/nested/deep"}):
            self.assertEqual(self.slug({}, ""), "alpha-nested")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.x + "/alpha/other"}):
            self.assertEqual(self.slug({}, ""), "alpha")

    def test_global_fallback(self):
        self.assertIsNone(self.slug({}, ""))
        self.assertEqual(self.log({}), self.glog())

    def test_no_args(self):
        self.assertIsNone(sp.spawn_project(home=self.home))

    def test_precedence(self):
        data = {"parent_agent": "beta-pd", "subagent_type": "alpha-pd"}
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.tilde_root}):
            self.assertEqual(self.slug(data, "Project: alpha-nested"), "alpha-nested")  # prompt first
            self.assertEqual(self.slug(data, ""), "beta")  # then parent
            self.assertEqual(self.slug({"subagent_type": "alpha-pd"}, ""), "alpha")  # then subagent_type
            self.assertEqual(self.slug({}, ""), "tilde")  # then cwd

    def test_unknown_slug_falls_through(self):
        self.assertEqual(self.slug({"parent_agent": "beta-pd"}, "Project: nosuch -- foo"), "beta")
        self.assertEqual(self.slug({"parent_agent": "nosuch-pd", "subagent_type": "alpha-pd"}, ""), "alpha")
        self.assertIsNone(self.slug({"parent_agent": "nosuch-pd"}, "Project: /not/a/project/path"))

    def test_resolve_log_file_paths(self):
        self.assertEqual(self.log({"prompt": "Project: alpha"}), os.path.join(self.x, "alpha", "memory", "spawns.jsonl"))
        self.assertEqual(self.log({"parent_agent": "beta-pd"}),
                         os.path.join(self.home, ".claude", "projects", "beta", "memory", "spawns.jsonl"))
        # table path without a trailing /memory: log stays {root}/memory/spawns.jsonl
        self.assertEqual(self.log({"prompt": "Project: bare"}),
                         os.path.join(self.home, ".claude", "projects", "bare", "memory", "spawns.jsonl"))

    def test_spawn_log_file_override_first(self):
        with mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": "/tmp/override.jsonl"}):
            self.assertEqual(self.log({"prompt": "Project: alpha", "parent_agent": "beta-pd"}), "/tmp/override.jsonl")

    def test_missing_table_falls_back_global_never_raises(self):
        with mock.patch.dict(os.environ, {"SPAWN_MEDIUM_TERM": os.path.join(self.tmp, "nope.md")}):
            self.assertIsNone(self.slug({"parent_agent": "beta-pd"}, "Project: alpha"))
            self.assertEqual(self.log({"parent_agent": "beta-pd"}), self.glog())

    def test_garbage_input_never_raises(self):
        self.assertIsNone(self.slug("not a dict", None))
        self.assertIsNone(self.slug({"parent_agent": 5, "subagent_type": None}, 12))


class PathBoundary(Base):
    def test_sibling_prefix_does_not_match(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.x + "/alphabet"}):
            self.assertIsNone(self.slug({}, ""))
            self.assertEqual(self.log({}), self.glog())
        self.assertIsNone(self.slug({}, "Project: " + self.x + "/alphabet/"))

    def test_exact_and_sub_match(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.x + "/alpha"}):
            self.assertEqual(self.slug({}, ""), "alpha")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.x + "/alpha/sub"}):
            self.assertEqual(self.slug({}, ""), "alpha")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.x + "/alpha/"}):
            self.assertEqual(self.slug({}, ""), "alpha")

    def test_longest_prefix_helper(self):
        rows = [("a", "/x/alpha"), ("b", "/x/alpha/nested")]
        self.assertEqual(sp.longest_prefix("/x/alpha/nested/z", rows), "b")
        self.assertEqual(sp.longest_prefix("/x/alphabet", rows), None)
        self.assertEqual(sp.longest_prefix("/x/alpha", rows), "a")
        self.assertIsNone(sp.longest_prefix("", rows))

    def test_non_leading_tilde_not_mangled(self):
        rows = dict(sp.project_rows(home=self.home))
        self.assertEqual(rows["tilde"], self.tilde_root)
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.tilde_root + "/sub"}):
            self.assertEqual(self.slug({}, ""), "tilde")
            self.assertEqual(self.log({}), os.path.join(self.tilde_root, "memory", "spawns.jsonl"))

    def test_leading_tilde_expanded_with_given_home(self):
        rows = dict(sp.project_rows(home=self.home))
        self.assertEqual(rows["beta"], os.path.join(self.home, ".claude", "projects", "beta"))
        self.assertEqual(rows["bare"], os.path.join(self.home, ".claude", "projects", "bare"))
        self.assertNotIn("tracked", rows)


class AllLogs(Base):
    def touch(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "a").close()
        return path

    def test_all_logs_collects_existing_deduped_and_excludes_primary(self):
        g = self.touch(self.glog())
        a = self.touch(os.path.join(self.x, "alpha", "memory", "spawns.jsonl"))
        b = self.touch(os.path.join(self.home, ".claude", "projects", "beta", "memory", "spawns.jsonl"))
        self.touch(os.path.join(self.home, ".claude", "projects", "other", "memory", "spawns.jsonl"))  # glob only
        out = sp.all_logs(a, home=self.home)
        self.assertNotIn(os.path.abspath(a), out)
        self.assertIn(os.path.abspath(g), out)
        self.assertIn(os.path.abspath(b), out)  # table AND glob hit: once
        self.assertEqual(len(out), len(set(out)))
        self.assertTrue(any(p.endswith("/other/memory/spawns.jsonl") for p in out))
        self.assertFalse(any(p.endswith("/nested/memory/spawns.jsonl") for p in out))  # missing files skipped

    def test_all_logs_spawn_log_file_set_uses_extra_logs_only(self):
        g = self.touch(self.glog())
        e = self.touch(os.path.join(self.tmp, "extra.jsonl"))
        prim = self.touch(os.path.join(self.tmp, "prim.jsonl"))
        with mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": prim, "SPAWN_LEDGER_EXTRA_LOGS": os.pathsep.join([e, prim, "/no/such"])}):
            self.assertEqual(sp.all_logs(prim, home=self.home), [os.path.abspath(e)])
        with mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": prim}):
            self.assertEqual(sp.all_logs(prim, home=self.home), [])
        self.assertNotIn(g, [])

    def test_all_logs_never_raises_without_table(self):
        with mock.patch.dict(os.environ, {"SPAWN_MEDIUM_TERM": os.path.join(self.tmp, "nope.md")}):
            g = self.touch(self.glog())
            self.assertEqual(sp.all_logs(os.path.join(self.tmp, "p.jsonl"), home=self.home), [os.path.abspath(g)])


if __name__ == "__main__":
    unittest.main()
