#!/usr/bin/env python3
"""Project resolution for a Windows project root (D:\\Dev\\WorkFiles\\proj), end to end, on any OS.

Why: a real Windows machine logged ALL 54 spawn_start rows with project ".claude" although the project root is on D:\\.
Chain: medium-term.md row -> hooks/lib/spawn_project.py (the ONE resolver) -> ledger.py (log file + "project" label);
scripts/skill-route.py (_spawn_project, the recorder) and hooks/lib/resolve-project.sh must resolve the same way.
Synthetic fixtures only: made-up prompts, root D:\\Dev\\WorkFiles\\proj. Everything runs in temp dirs.
Run: python3 -m unittest -v <repo>/hooks/tests/test_win32_project_resolution.py
CI: hooks/tests is collected by .github/workflows/installers.yml (windows job) (stdlib + scripts/skill-route.py, no skills submodule).
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "lib")
SCRIPTS = os.path.join(HERE, "..", "..", "scripts")
sys.path.insert(0, LIB)
import test_home  # noqa: E402
import find_bash  # noqa: E402

WHOME = "C:\\Users\\tester"  # the explicit home passed to spawn_project: a Windows-shaped one
# One table, every spelling a Windows machine can produce for a project root.
TABLE = "\n".join([
    "| Project | Memory Path | PD | Flag |",
    "|---|---|---|---|",
    "| proj | `D:\\Dev\\WorkFiles\\proj\\memory` | proj-pd | active |",
    "| proj2 | `D:\\Dev\\WorkFiles\\proj2\\memory\\` | proj2-pd | active |",
    "| fwd | `D:/Dev/WorkFiles/fwd/memory/` | fwd-pd | active |",
    "| gitbash | `/e/Dev/gb/memory/` | gitbash-pd | active |",
    "| inhome | `~/.claude/projects/inhome/memory/` | inhome-pd | active |",
    "",
])
TABLE_ONLY_PROJ = "\n".join(TABLE.split("\n")[:3] + [""])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Table(unittest.TestCase):
    """Writes the fixture table to a temp file and points SPAWN_MEDIUM_TERM at it."""
    TEXT = TABLE

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="win-proj-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.mt = os.path.join(self.tmp, "medium-term.md")
        with open(self.mt, "w", encoding="utf-8", newline="") as f:
            f.write(self.TEXT)
        p = mock.patch.dict(os.environ, {"SPAWN_MEDIUM_TERM": self.mt})
        p.start()
        self.addCleanup(p.stop)
        for k in ("SPAWN_LOG_FILE", "CLAUDE_PROJECT_DIR", "SKILL_ROUTE_MEDIUM_TERM"):
            os.environ.pop(k, None)
        self.sp = load("spawn_project_winproj_%d" % id(self), os.path.join(LIB, "spawn_project.py"))


class DriveRoot(Table):
    def rows(self):
        return self.sp.project_rows(WHOME)

    def test_every_spelling_of_the_root_matches(self):
        r = self.rows()
        for path in (r"D:\Dev\WorkFiles\proj", r"D:\Dev\WorkFiles\proj\src\x", "D:/Dev/WorkFiles/proj/src",
                     r"d:\dev\workfiles\PROJ", r"D:\DEV\WORKFILES\Proj\a"):
            self.assertEqual(self.sp.longest_prefix(path, r), "proj", path)
        for path in (r"D:\Dev\WorkFiles\fwd", "d:/dev/workfiles/FWD/x", r"D:\Dev\WorkFiles\fwd\x"):
            self.assertEqual(self.sp.longest_prefix(path, r), "fwd", path)

    def test_sibling_prefix_never_cross_matches(self):
        r = self.rows()
        self.assertEqual(self.sp.longest_prefix(r"D:\Dev\WorkFiles\proj2\x", r), "proj2")
        self.assertEqual(self.sp.longest_prefix(r"D:\Dev\WorkFiles\proj3", r), None)
        self.assertEqual(self.sp.longest_prefix(r"D:\Dev\WorkFiles\projx\a", r), None)
        only = [("proj", "D:/Dev/WorkFiles/proj")]
        self.assertEqual(self.sp.longest_prefix(r"D:\Dev\WorkFiles\proj2\x", only), None)

    def test_other_drive_does_not_match(self):
        self.assertIsNone(self.sp.longest_prefix(r"C:\Dev\WorkFiles\proj", self.rows()))

    def test_tilde_row_expands_against_the_explicit_home(self):
        self.assertEqual(self.sp.longest_prefix(WHOME + r"\.claude\projects\inhome\x", self.rows()), "inhome")

    def test_git_bash_cwd_matches_a_drive_root(self):
        """CLAUDE_PROJECT_DIR / cwd in Git-Bash spelling (/d/..., /mnt/d/..., /cygdrive/d/...) vs a D:\\ table row."""
        r = self.rows()
        for path in ("/d/Dev/WorkFiles/proj", "/d/Dev/WorkFiles/proj/src", "/mnt/d/Dev/WorkFiles/proj/src",
                     "/cygdrive/d/Dev/WorkFiles/proj/src", "/D/dev/workfiles/proj/x"):
            self.assertEqual(self.sp.longest_prefix(path, r), "proj", path)
        self.assertEqual(self.sp.longest_prefix("/d/Dev/WorkFiles/proj2/x", r), "proj2")
        self.assertIsNone(self.sp.longest_prefix("/d/Dev/WorkFiles/projx", r))
        self.assertIsNone(self.sp.longest_prefix("/c/Dev/WorkFiles/proj", r))

    def test_git_bash_table_row_matches_a_drive_cwd(self):
        r = self.rows()
        self.assertEqual(self.sp.longest_prefix(r"E:\Dev\gb\sub", r), "gitbash")
        self.assertEqual(self.sp.longest_prefix("/e/Dev/gb/sub", r), "gitbash")
        self.assertIsNone(self.sp.longest_prefix(r"E:\Dev\gbx", r))

    def test_posix_msys_looking_paths_are_untouched(self):
        """No drive-letter root anywhere: /d/x is just a POSIX path (byte-identical behaviour)."""
        rows = [("a", "/d/x"), ("b", "/mnt/d/y")]
        self.assertEqual(self.sp.longest_prefix("/d/x/z", rows), "a")
        self.assertEqual(self.sp.longest_prefix("/mnt/d/y/z", rows), "b")
        self.assertIsNone(self.sp.longest_prefix("/d/xy", rows))
        self.assertIsNone(self.sp.longest_prefix("/mnt/d/x", rows))

    def test_git_bash_row_log_file_is_a_drive_path_on_windows(self):
        with mock.patch.object(self.sp, "_SEP", "\\"), mock.patch.object(self.sp.os.path, "join", __import__("ntpath").join), \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": r"E:\Dev\gb\sub"}):
            self.assertEqual(self.sp.resolve_log_file({}, WHOME), "E:\\Dev\\gb\\memory\\spawns.jsonl")

    def test_spawn_project_from_project_dir_every_spelling(self):
        for cwd in (r"D:\Dev\WorkFiles\proj", r"d:\dev\workfiles\PROJ\sub", "D:/Dev/WorkFiles/proj/sub",
                    "/d/Dev/WorkFiles/proj/sub"):
            with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": cwd}):
                self.assertEqual(self.sp.spawn_project({}, "do it", WHOME), "proj", cwd)
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": r"D:\Dev\WorkFiles\proj2\sub"}):
            self.assertEqual(self.sp.spawn_project({}, "do it", WHOME), "proj2")

    def test_spawn_project_from_the_project_line(self):
        for line in (r"Project: D:\Dev\WorkFiles\proj\memory", "Project: d:/dev/workfiles/PROJ/x",
                     "Project: /d/Dev/WorkFiles/proj", "Project: proj"):
            self.assertEqual(self.sp.spawn_project({}, line + "\nTask: x", WHOME), "proj", line)
        self.assertEqual(self.sp.spawn_project({}, r"Project: D:\Dev\WorkFiles\proj2\x", WHOME), "proj2")

    def test_spawn_project_from_the_pd_name(self):
        self.assertEqual(self.sp.spawn_project({"parent_agent": "proj-pd"}, "x", WHOME), "proj")
        self.assertEqual(self.sp.spawn_project({"subagent_type": "proj2-pd"}, "x", WHOME), "proj2")

    def test_log_file_uses_one_native_spelling(self):
        """Windows: D:\\Dev\\WorkFiles\\proj\\memory\\spawns.jsonl, no mixed C:/x\\memory spelling."""
        with mock.patch.object(self.sp, "_SEP", "\\"), mock.patch.object(self.sp.os.path, "join", __import__("ntpath").join), \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": r"d:\dev\workfiles\PROJ\sub"}):
            self.assertEqual(self.sp.resolve_log_file({}, WHOME), "D:\\Dev\\WorkFiles\\proj\\memory\\spawns.jsonl")

    def test_crlf_table_parses(self):
        with open(self.mt, "w", encoding="utf-8", newline="") as f:
            f.write(TABLE.replace("\n", "\r\n"))
        self.assertEqual(self.sp.longest_prefix(r"D:\Dev\WorkFiles\proj\x", self.rows()), "proj")
        self.assertEqual(dict(self.rows())["proj"], "D:/Dev/WorkFiles/proj")


class SkillRoute(Table):
    """scripts/skill-route.py _spawn_project (the recorder) must give the same answers as spawn_project."""

    def setUp(self):
        super().setUp()
        self.sr = load("skill_route_winproj", os.path.join(SCRIPTS, "skill-route.py"))
        self.home = test_home.hermetic_home(os.path.join(self.tmp, "home"))
        os.makedirs(os.path.join(self.tmp, "home"))
        self.home.__enter__()
        self.addCleanup(self.home.__exit__, None, None, None)
        os.environ.pop("SPAWN_MEDIUM_TERM", None)
        os.environ["SKILL_ROUTE_MEDIUM_TERM"] = self.mt

    def test_cwd_every_spelling(self):
        for cwd in (r"D:\Dev\WorkFiles\proj", r"d:\dev\workfiles\PROJ\sub", "D:/Dev/WorkFiles/proj/sub",
                    "/d/Dev/WorkFiles/proj/sub"):
            with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": cwd}):
                self.assertEqual(self.sr._spawn_project(), "proj", cwd)

    def test_sibling_prefix(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": r"D:\Dev\WorkFiles\proj2\x"}):
            self.assertEqual(self.sr._spawn_project(), "proj2")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": r"D:\Dev\WorkFiles\proj3\x"}):
            self.assertEqual(self.sr._spawn_project(), "global")

    def test_project_line_path_and_pd_name(self):
        self.assertEqual(self.sr._spawn_project({}, r"Project: D:\Dev\WorkFiles\proj\memory"), "proj")
        self.assertEqual(self.sr._spawn_project({}, "Project: d:/dev/workfiles/PROJ/x"), "proj")
        self.assertEqual(self.sr._spawn_project({"parent_agent": "proj2-pd"}, "x"), "proj2")

    def test_the_env_override_still_selects_the_table(self):
        other = os.path.join(self.tmp, "other.md")
        with open(other, "w", encoding="utf-8") as f:
            f.write("| Project | Memory Path | PD | Flag |\n|---|---|---|---|\n| alt | `D:\\alt\\memory` | alt-pd | a |\n")
        with mock.patch.dict(os.environ, {"SKILL_ROUTE_MEDIUM_TERM": other, "CLAUDE_PROJECT_DIR": r"D:\alt\x"}):
            self.assertEqual(self.sr._spawn_project(), "alt")
        with mock.patch.dict(os.environ, {"SKILL_ROUTE_MEDIUM_TERM": os.path.join(self.tmp, "missing.md")}):
            self.assertEqual(self.sr._spawn_project({}, "Project: proj"), "global")

    def test_posix_rows_behave_as_before(self):
        with open(self.mt, "w", encoding="utf-8") as f:
            f.write("| Project | Memory Path | PD | Flag |\n|---|---|---|---|\n"
                    "| alpha | `/srv/p/alpha/memory/` | alpha-pd | a |\n| alpha-sub | `/srv/p/alpha/sub/memory/` | s | a |\n")
        for cwd, want in (("/srv/p/alpha/x", "alpha"), ("/srv/p/alpha/sub/x", "alpha-sub"), ("/srv/p/alphabet", "global"),
                          ("/d/srv/p/alpha", "global")):
            with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": cwd}):
                self.assertEqual(self.sr._spawn_project(), want, cwd)


@unittest.skipIf(find_bash.find_bash() is None, "no bash on this machine")
class ResolveProjectSh(Table):
    """hooks/lib/resolve-project.sh: SPAWN_LOG_FILE for a cwd. The roots are on Z:\\ so that, on a real Windows runner,
    the script's mkdir -p cannot create anything on a real drive; cwd of the child is the temp dir either way."""
    TEXT = TABLE.replace("D:", "Z:")
    SH = os.path.join(LIB, "resolve-project.sh")

    def run_sh(self, cwd, text=None):
        if text is not None:
            with open(self.mt, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        env = test_home.home_env(os.path.join(self.tmp, "home"))
        env.update({"SPAWN_MEDIUM_TERM": self.mt, "CLAUDE_PROJECT_DIR": cwd})
        env.pop("SPAWN_LOG_FILE", None)
        out = subprocess.run([find_bash.find_bash(), "-c", 'source "$1" && resolve_project_path && printf %s "$SPAWN_LOG_FILE"',
                              "x", self.SH.replace("\\", "/")], cwd=self.tmp, env=env, capture_output=True, text=True,
                             timeout=60)
        return out.stdout.strip().replace("\\", "/")

    def glog(self):
        return os.path.join(self.tmp, "home", ".claude", "logs", "spawns.jsonl").replace("\\", "/")

    def test_drive_root_matches_every_spelling(self):
        for cwd in (r"Z:\Dev\WorkFiles\proj", r"z:\dev\workfiles\PROJ\sub", "Z:/Dev/WorkFiles/proj/sub"):
            self.assertEqual(self.run_sh(cwd), "Z:/Dev/WorkFiles/proj/memory/spawns.jsonl", cwd)

    def test_sibling_prefix_does_not_cross_match(self):
        self.assertEqual(self.run_sh(r"Z:\Dev\WorkFiles\proj2\x"), "Z:/Dev/WorkFiles/proj2/memory/spawns.jsonl")
        self.assertEqual(self.run_sh(r"Z:\Dev\WorkFiles\proj2\x", TABLE_ONLY_PROJ.replace("D:", "Z:")), self.glog())
        self.assertEqual(self.run_sh(r"Z:\Dev\WorkFiles\projx", TABLE_ONLY_PROJ.replace("D:", "Z:")), self.glog())

    def test_home_row_matches_and_unrelated_goes_global(self):
        home = os.path.join(self.tmp, "home")
        self.assertEqual(self.run_sh(os.path.join(home, ".claude", "projects", "inhome", "x"), TABLE),
                         os.path.join(home, ".claude", "projects", "inhome", "memory", "spawns.jsonl").replace("\\", "/"))
        self.assertEqual(self.run_sh(os.path.join(self.tmp, "elsewhere")), self.glog())

    def test_posix_sibling_prefix(self):
        root = os.path.join(self.tmp, "p", "proj").replace("\\", "/")
        text = "| Project | Memory Path | PD | Flag |\n|---|---|---|---|\n| a | `%s/memory/` | a-pd | a |\n" % root
        self.assertEqual(self.run_sh(root + "2/x", text), self.glog())
        self.assertEqual(self.run_sh(root + "/x", text), root + "/memory/spawns.jsonl")

    def test_explicit_override_is_honoured(self):
        env = test_home.home_env(os.path.join(self.tmp, "home"))
        env["SPAWN_LOG_FILE"] = "/tmp/explicit.jsonl"
        out = subprocess.run([find_bash.find_bash(), "-c", 'source "$1" && resolve_project_path && printf %s "$SPAWN_LOG_FILE"',
                              "x", self.SH.replace("\\", "/")], cwd=self.tmp, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stdout, "/tmp/explicit.jsonl")


if __name__ == "__main__":
    unittest.main()
