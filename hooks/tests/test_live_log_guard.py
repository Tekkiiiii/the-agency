"""Tests for hooks/lib/live_log_guard.py (the shared "tests never write live logs" guard) and
hooks/lib/test_home.isolate_process_home() (the shared bootstrap). Everything runs on stand-in trees under the temp dir:
no real log is read or written. Run from the repo root: python3 -m unittest discover -s hooks/tests -v
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "lib")
sys.path.insert(0, LIB)
import live_log_guard as g  # noqa: E402


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        f.write(text)


def slurp(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def row(**kw):
    import json
    return json.dumps(kw) + "\n"


class StandIn(unittest.TestCase):
    """A stand-in 'real home' with one file of every class."""

    def setUp(self):
        self.h = tempfile.mkdtemp(prefix="llg-")
        self.addCleanup(shutil.rmtree, self.h, True)
        self.c = os.path.join(self.h, ".claude")
        self.av = os.path.join(self.c, "logs", "artifact-verify.jsonl")      # STATIC
        self.sp = os.path.join(self.c, "logs", "spawns.jsonl")                # SESSION
        self.ev = os.path.join(self.c, "memory", "metrics", "events.jsonl")   # SESSION
        self.proj = os.path.join(self.c, "projects", "p", "memory", "spawns.jsonl")
        self.daemon = os.path.join(self.c, "logs", "obsidian-mcp-http.out.log")  # IGNORED
        write(self.av, row(ts="2026-01-01T00:00:00", event="ARTIFACT_MISSING", missing=["/x/real.pdf"]))
        write(self.sp, row(event="spawn_start", tool_use_id="toolu_01abc"))
        write(self.ev, row(event="save_state"))
        write(self.proj, row(event="spawn_start", tool_use_id="toolu_02"))
        write(self.daemon, "daemon line\n")
        self.before = g.snapshot_all(self.h)

    def problems(self):
        return g.violations(self.before, self.h)


class Discovery(StandIn):
    def test_watches_logs_memory_jsonl_and_project_ledgers(self):
        got = {os.path.relpath(p, self.h).replace(os.sep, "/") for p in g.watched(self.h)}
        self.assertEqual(got, {".claude/logs/artifact-verify.jsonl", ".claude/logs/spawns.jsonl",
                               ".claude/logs/obsidian-mcp-http.out.log", ".claude/memory/metrics/events.jsonl",
                               ".claude/projects/p/memory/spawns.jsonl"})

    def test_classes(self):
        self.assertEqual(g.classify(self.av), g.STATIC)
        self.assertEqual(g.classify(self.sp), g.SESSION)
        self.assertEqual(g.classify(self.ev), g.SESSION)
        self.assertEqual(g.classify(self.daemon), g.IGNORED)
        self.assertEqual(g.classify(os.path.join(self.c, "logs", "brand-new-log.jsonl")), g.SESSION)

    def test_real_home_precedence(self):
        env = {"SPAWN_LEDGER_GUARD_HOME": "/a", "LIVE_LOG_REAL_HOME": "/b"}
        self.assertEqual(g.real_home(env), "/a")
        self.assertEqual(g.real_home({"LIVE_LOG_REAL_HOME": "/b"}), "/b")
        self.assertTrue(g.real_home({}))

    def test_real_root_follows_the_repo_ladder(self):
        """AGENCY_HOME -> CLAUDE_CONFIG_DIR -> <home>/.claude; the recorded LIVE_LOG_REAL_ROOT and the stand-in beat the ladder."""
        home = {"LIVE_LOG_REAL_HOME": "/h"}
        self.assertEqual(g.real_root(home), os.path.join("/h", ".claude"))
        self.assertEqual(g.real_root(dict(home, CLAUDE_CONFIG_DIR="/cfg")), "/cfg")
        self.assertEqual(g.real_root(dict(home, CLAUDE_CONFIG_DIR="/cfg", AGENCY_HOME="/ah")), "/ah")
        self.assertEqual(g.real_root(dict(home, AGENCY_HOME="/ah", LIVE_LOG_REAL_ROOT="/rec")), "/rec")
        self.assertEqual(g.real_root(dict(home, LIVE_LOG_REAL_ROOT="/rec", SPAWN_LEDGER_GUARD_HOME="/s")), os.path.join("/s", ".claude"))

    def test_default_watch_covers_the_agency_root_not_only_home_dot_claude(self):
        root = tempfile.mkdtemp(prefix="llg-root-")
        self.addCleanup(shutil.rmtree, root, True)
        write(os.path.join(root, "logs", "spawns.jsonl"), row(event="spawn_start"))
        old = {k: os.environ.get(k) for k in ("LIVE_LOG_REAL_ROOT", "SPAWN_LEDGER_GUARD_HOME")}
        os.environ["LIVE_LOG_REAL_ROOT"] = root
        os.environ.pop("SPAWN_LEDGER_GUARD_HOME", None)
        try:
            self.assertIn(os.path.normpath(os.path.join(root, "logs", "spawns.jsonl")), g.watched())
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class Clean(StandIn):
    def test_nothing_changed_is_clean(self):
        self.assertEqual(self.problems(), [])

    def test_real_session_appends_pass(self):
        write(self.sp, row(event="spawn_end", tool_use_id="toolu_03") + row(event="spawn_end", tool_use_id=""), "a")
        write(self.ev, row(event="x", path="/Users/you/proj/a.md"), "a")
        write(self.daemon, "more daemon output\n", "a")
        self.assertEqual(self.problems(), [])

    def test_free_text_mentioning_test_paths_is_not_a_fingerprint(self):
        # a live session's spawn prompt may legitimately quote /nope/a.pdf (this very task did)
        write(self.sp, row(event="spawn_start", tool_use_id="toolu_04", prompt_excerpt="fix /nope/a.pdf C:\\Users\\t\\out.pdf"), "a")
        self.assertEqual(self.problems(), [])

    def test_half_written_last_line_is_ignored(self):
        write(self.sp, '{"event": "spawn_start", "tool_use_id": "toolu_0', "a")  # a live writer mid-append
        self.assertEqual(self.problems(), [])


class Bites(StandIn):
    def test_test_tool_use_id_fails(self):
        write(self.sp, row(event="spawn_end", tool_use_id="tu-1"), "a")
        self.assertEqual(len(self.problems()), 1)
        self.assertIn("tu-1", self.problems()[0])

    def test_fake_path_field_fails(self):
        for i, (field, value) in enumerate([("path", "C:\\Users\\t\\out.pdf"), ("path", "D:/work/report.docx"),
                                            ("cwd", "/nope/a"), ("log_file", "/home/t/.claude/x"), ("missing", ["gone.pdf"])]):
            with self.subTest(field=field, value=value):
                before = g.snapshot_all(self.h)
                write(self.ev, row(event="x", **{field: value}), "a")
                self.assertEqual(len(g.violations(before, self.h)), 1)

    def test_rewrite_and_truncate_fail(self):
        write(self.sp, row(event="spawn_start", tool_use_id="toolu_ZZZZZZ"))
        self.assertIn("rewritten", self.problems()[0])
        write(self.sp, "")
        self.assertIn("rewritten", self.problems()[0])

    def test_static_log_append_fails_even_with_a_clean_looking_row(self):
        write(self.av, row(ts="2026-10-14T00:00:00", event="ARTIFACT_MISSING", missing=["/real/looking.pdf"]), "a")
        self.assertEqual(len(self.problems()), 1)
        self.assertIn("artifact-verify.jsonl", self.problems()[0])

    def test_static_log_mtime_only_touch_fails(self):
        st = os.stat(self.av)
        os.utime(self.av, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
        self.assertEqual(len(self.problems()), 1)

    def test_new_static_file_and_vanished_file_fail(self):
        write(os.path.join(self.c, "memory", "metrics", "events-seed-archive.jsonl"), row(event="x"))
        self.assertEqual(len(self.problems()), 1)
        os.remove(self.sp)
        self.assertEqual(len(self.problems()), 2)

    def test_new_session_file_with_test_row_fails(self):
        write(os.path.join(self.c, "logs", "jev-usage.jsonl"), row(event="u", tool_use_id="t1"))
        self.assertEqual(len(self.problems()), 1)

    def test_project_ledger_covered(self):
        write(self.proj, row(event="spawn_end", tool_use_id="x"), "a")
        self.assertEqual(len(self.problems()), 1)


class Bootstrap(unittest.TestCase):
    """isolate_process_home() runs in a child interpreter: it moves HOME for the whole process."""

    def child(self, code, real_claude, extra_env=None, boot=True):
        env = dict(os.environ, PYTHONPATH=LIB, PYTHONDONTWRITEBYTECODE="1")
        for k in ("LIVE_LOG_REAL_HOME", "LIVE_LOG_REAL_ROOT", "TEST_HOME_ISOLATED", "SPAWN_LOG_FILE", "JEV_USAGE_LOG", "AGENCY_HOME", "CLAUDE_CONFIG_DIR"):
            env.pop(k, None)
        env.update(extra_env or {})
        pre = "import os, sys, test_home\n" + ("iso = test_home.isolate_process_home(real_claude=%r)\n" % real_claude if boot else "")
        r = subprocess.run([sys.executable, "-c", pre + code], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip().splitlines()

    def setUp(self):
        self.real = tempfile.mkdtemp(prefix="llg-real-")
        self.addCleanup(shutil.rmtree, self.real, True)
        for d in ("hooks", "scripts"):
            write(os.path.join(self.real, d, "keep.txt"), "precious\n")
        write(os.path.join(self.real, "logs", "spawns.jsonl"), "live\n")
        write(os.path.join(self.real, "memory", "medium-term.md"), "live\n")

    def test_home_is_moved_everywhere_and_code_is_visible_but_data_is_not(self):
        out = self.child(
            "c = iso.claude\n"
            "print(os.path.expanduser('~') == iso.home == os.environ['HOME'] == os.environ['USERPROFILE'])\n"
            "print(iso.home.startswith(__import__('tempfile').gettempdir()) or iso.home.startswith(os.path.realpath(__import__('tempfile').gettempdir())))\n"
            "print(sorted(os.listdir(c)))\n"
            "print(open(os.path.join(c, 'hooks', 'keep.txt')).read().strip())\n"
            "print(os.environ['LIVE_LOG_REAL_HOME'], os.environ['SPAWN_LEDGER_TEST'])\n"
            "print(os.listdir(os.path.join(c, 'logs')), os.path.exists(os.path.join(c, 'memory', 'medium-term.md')))\n",
            self.real, {"SPAWN_LOG_FILE": "/real/logs/spawns.jsonl", "AGENCY_HOME": "/real", "CLAUDE_CONFIG_DIR": "/real"})
        self.assertEqual(out[0], "True")
        self.assertEqual(out[1], "True")
        self.assertEqual(out[2], "['hooks', 'logs', 'memory', 'projects', 'scripts', 'state']")
        self.assertEqual(out[3], "precious")
        self.assertEqual(out[4], "%s 1" % g.real_home({}))
        self.assertEqual(self.child("print(os.environ['LIVE_LOG_REAL_ROOT'])", self.real, {"AGENCY_HOME": "/real"}), ["/real"])
        self.assertEqual(out[5], "[] False")

    def test_writer_overrides_pointing_at_real_logs_are_dropped(self):
        out = self.child("print(os.environ.get('SPAWN_LOG_FILE'), os.environ.get('JEV_USAGE_LOG'), os.environ.get('AGENCY_HOME'))",
                         self.real, {"SPAWN_LOG_FILE": "/real/spawns.jsonl", "JEV_USAGE_LOG": "/real/u.jsonl", "AGENCY_HOME": "/real"})
        self.assertEqual(out, ["None None None"])

    def test_writes_land_in_the_isolated_tree_and_cleanup_never_touches_real_data(self):
        out = self.child(
            "c = iso.claude\n"
            "open(os.path.join(c, 'logs', 'spawns.jsonl'), 'a').write('leak\\n')\n"
            "open(os.path.join(c, 'hooks', 'new-file-through-symlink.txt'), 'w').write('x')\n"  # goes to the REAL dir by design (code dirs)
            "print(iso.home)\n", self.real)
        home = out[0]
        self.assertFalse(os.path.exists(home), "isolated tree must be removed at exit")
        self.assertEqual(slurp(os.path.join(self.real, "logs", "spawns.jsonl")), "live\n")
        self.assertEqual(slurp(os.path.join(self.real, "hooks", "keep.txt")), "precious\n")
        self.assertEqual(slurp(os.path.join(self.real, "scripts", "keep.txt")), "precious\n")

    def test_remove_tree_unlinks_symlinks_and_never_follows_them(self):
        import test_home
        target = tempfile.mkdtemp(prefix="llg-target-")
        self.addCleanup(shutil.rmtree, target, True)
        write(os.path.join(target, "sub", "precious.txt"), "keep\n")
        tree = tempfile.mkdtemp(prefix="llg-tree-")
        try:
            os.symlink(target, os.path.join(tree, "linked-dir"), target_is_directory=True)
            os.symlink(os.path.join(target, "sub", "precious.txt"), os.path.join(tree, "linked-file"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable here")
        write(os.path.join(tree, "real", "x.txt"), "x")
        test_home.remove_tree(tree)
        self.assertFalse(os.path.exists(tree))
        self.assertEqual(slurp(os.path.join(target, "sub", "precious.txt")), "keep\n")

    def test_idempotent_second_call_returns_the_same_tree(self):
        out = self.child("a = iso.home\nb = test_home.isolate_process_home(real_claude=%r).home\nprint(a == b)\n" % self.real, self.real)
        self.assertEqual(out, ["True"])

    def test_copy_fallback_is_small_dirs_only_and_never_skills(self):
        write(os.path.join(self.real, "skills", "big", "SKILL.md"), "s\n")
        out = self.child(
            "from unittest import mock\n"
            "with mock.patch('os.symlink', side_effect=OSError('no privilege')):\n"
            "    iso = test_home.isolate_process_home(real_claude=%r)\n"
            "print(sorted(iso.mirrored), sorted(iso.skipped))\n"
            "print(os.path.islink(os.path.join(iso.claude, 'hooks')), open(os.path.join(iso.claude, 'hooks', 'keep.txt')).read().strip(),"
            " os.path.exists(os.path.join(iso.claude, 'skills')))\n" % self.real, self.real, boot=False)
        self.assertEqual(out[0], "['hooks', 'scripts'] ['skills']")
        self.assertEqual(out[1], "False precious False")


if __name__ == "__main__":
    unittest.main()
