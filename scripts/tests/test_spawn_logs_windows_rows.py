"""Spawn-log discovery in scripts/jev-feedback.py must read medium-term.md
through hooks/lib/spawn_project (the ONE resolver), not an ad-hoc POSIX-only regex.

Why: that copy split the table row on "/" only, expanded every "~" (not just a leading one) and stripped only a
"/memory" suffix. A Windows row (`C:\\Users\\x\\proj\\memory\\`) became the garbage path
`C:\\Users\\x\\proj\\memory\\/memory/spawns.jsonl`, so that project's spawn rows were never read.
Table: a Windows backslash row, its sibling proj2 (path-boundary case: proj must not swallow or hide proj2), a POSIX
row whose directory name holds a "~", and a leading-"~" row. Asserts hold on macOS (project_rows folds C:\\x to C:/x and
_native leaves it as is) and on Windows (_native gives the backslash spelling; file-system parts are skipped there).
Temp dirs only: HOME is hermetic, the cwd is a temp dir, nothing touches the real agency root.

Run: python3 -m unittest discover -s scripts/tests -p 'test_spawn_logs_windows_rows*' -v
"""
import contextlib
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, os.path.normpath(os.path.join(SCRIPTS, "..", "hooks", "lib")))
import spawn_project as sp  # noqa: E402
import test_home  # noqa: E402


def load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


jf = load("jev_feedback_wrows", "jev-feedback.py")


def log_of(root):
    """Where the resolver puts the log of a project root (OS spelling)."""
    return os.path.join(sp._native(root), "memory", "spawns.jsonl")


@unittest.skipIf(os.name == "nt", "creates C:/Users/x/... under a temp cwd; the Windows spelling is covered by hooks/tests")
class WindowsRowSpawnLogs(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.cwd = os.path.join(self.tmp, "cwd")
        self.posix_root = os.path.join(self.tmp, "a~b", "posix")  # a "~" that is NOT leading
        self.root = os.path.join(self.home, "agency")  # the agency root, handed over as AGENCY_HOME
        os.makedirs(os.path.join(self.root, "memory"))
        os.makedirs(self.cwd)
        self.mt = os.path.join(self.root, "memory", "medium-term.md")
        with open(self.mt, "w", encoding="utf-8") as f:
            f.write("\n".join([
                "| Project | Memory Path | PD | Flag |",
                "|---|---|---|---|",
                "| proj | `C:\\Users\\x\\proj\\memory\\` | proj-pd | active |",
                "| proj2 | `C:\\Users\\x\\proj2\\memory\\` | proj2-pd | active |",
                "| posix | `%s/memory/` | posix-pd | active |" % self.posix_root,
                "| tilde | `~/tproj/memory/` | tilde-pd | active |",
                "| none | tracked under `tilde` | - | dormant |",
                "",
            ]))
        self.roots = ["C:/Users/x/proj", "C:/Users/x/proj2", self.posix_root, self.home + "/tproj"]
        self.glob_log = os.path.join(self.root, "logs", "spawns.jsonl")
        self.expected = [self.glob_log] + [log_of(r) for r in self.roots]  # discovery order = global, then table order
        old = os.getcwd()
        os.chdir(self.cwd)  # the relative C:/Users/x/proj/... spelling resolves under this temp dir
        self.addCleanup(os.chdir, old)
        for p in self.expected[1:]:  # every project log exists; the global one does not
            d = os.path.dirname(os.path.abspath(p))
            os.makedirs(d, exist_ok=True)
            with open(os.path.abspath(p), "w") as f:
                f.write("{}\n")

    def hermetic(self):
        stack = contextlib.ExitStack()
        stack.enter_context(test_home.hermetic_home(self.home))
        stack.enter_context(mock.patch.dict(os.environ, {"AGENCY_HOME": self.root}))
        return stack

    def check_no_mangling(self, paths):
        for p in paths:
            self.assertNotIn("\\", p, "a backslash row was not folded: %r" % p)
            self.assertNotIn("/memory/memory", p)

    def test_jev_feedback_default_spawn_logs(self):
        with self.hermetic():
            got = jf.default_spawn_logs()
        self.check_no_mangling(got)
        self.assertEqual(got, self.expected)  # same order, deduped, missing files kept (the old contract)

    def test_sibling_projects_are_two_distinct_logs(self):
        # proj / proj2: neither log hides or replaces the other (path boundary, not a string prefix)
        with self.hermetic():
            got = jf.default_spawn_logs()
        a, b = log_of("C:/Users/x/proj"), log_of("C:/Users/x/proj2")
        self.assertIn(a, got)
        self.assertIn(b, got)
        self.assertNotEqual(a, b)
        self.assertEqual(len(got), len(set(got)))


if __name__ == "__main__":
    unittest.main()
