#!/usr/bin/env python3
"""Windows-simulation tests for hooks/lib/model-pin.py and hooks/lib/spawn_project.py.

There is no Windows machine in the loop: the win32 behaviour is simulated on POSIX (no fcntl, a fake msvcrt,
cp1252 stdio, Windows-shaped path strings). Everything runs in temp dirs; the real ledger / logs are never touched.
Run from the repo root: python3 -m unittest -v hooks/tests/test_win32_model_pin.py
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
SCRIPT = os.path.join(LIB, "model-pin.py")
NOW = 1_791_000_000
CAP = {"max": 1, "stale_after_sec": 7200, "types": ["general-purpose"]}
_LOADS = [0]


def load_model_pin(**fake_modules):
    """Import model-pin.py fresh. fake_modules: name -> module, or None (= `import name` raises ImportError)."""
    _LOADS[0] += 1
    with mock.patch.dict(sys.modules, fake_modules):
        spec = importlib.util.spec_from_file_location("model_pin_win32_%d" % _LOADS[0], SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


def load_spawn_project():
    spec = importlib.util.spec_from_file_location("spawn_project_win32", os.path.join(LIB, "spawn_project.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_msvcrt(calls, fail=None):
    """msvcrt stand-in recording locking(fd, mode, nbytes). fail = exception to raise from locking()."""
    m = types.ModuleType("msvcrt")
    m.LK_LOCK, m.LK_UNLCK = 1, 0

    def locking(fd, mode, nbytes):
        calls.append(("LK_LOCK" if mode == m.LK_LOCK else "LK_UNLCK", nbytes))
        if fail is not None:
            raise fail
    m.locking = locking
    return m


class CapBase(unittest.TestCase):
    """In-process cap_check against temp state / log dirs."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="win32-model-pin-")
        self.state = os.path.join(self.tmp, "state")
        self.home = os.path.join(self.tmp, "home")
        self.log = os.path.join(self.tmp, "logs", "spawns.jsonl")
        os.makedirs(os.path.dirname(self.log))
        open(self.log, "w").close()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("MODEL_PIN_", "SPAWN_")) and k not in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR")}
        env.update({"SPAWN_LOG_FILE": self.log, "MODEL_PIN_STATE_DIR": self.state, "MODEL_PIN_HOME": self.home,
                    "MODEL_PIN_GLOBAL_LOG": "", "MODEL_PIN_NOW": str(NOW)})
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def two_spawns(self, mod):
        a = mod.cap_check(CAP, "P1", "test-pd", "tu-1", NOW)
        b = mod.cap_check(CAP, "P1", "test-pd", "tu-2", NOW)
        return a, b

    def slots(self):
        with open(os.path.join(self.state, "spawn-slots.jsonl")) as f:
            return [json.loads(l) for l in f if l.strip()]


class TestLocking(CapBase):
    EXPECT = (("ok", False, 0, "pd:test-pd"), ("ok", True, 1, "pd:test-pd"))

    def test_loads_without_fcntl(self):
        mod = load_model_pin(fcntl=None, msvcrt=None)
        self.assertIsNone(mod.fcntl)

    def test_posix_path_unchanged_uses_flock_ex_then_un(self):
        calls = []
        fake = types.ModuleType("fcntl")
        fake.LOCK_EX, fake.LOCK_UN = 2, 8
        fake.flock = lambda fh, op: calls.append(op)
        mod = load_model_pin(fcntl=fake, msvcrt=None)
        a, b = self.two_spawns(mod)
        self.assertEqual((a, b), self.EXPECT)
        self.assertEqual(calls, [2, 8, 2, 8])

    def test_real_posix_result_is_the_reference(self):
        mod = load_model_pin()
        self.assertEqual(self.two_spawns(mod), self.EXPECT)

    def test_msvcrt_locks_then_unlocks(self):
        calls = []
        mod = load_model_pin(fcntl=None, msvcrt=fake_msvcrt(calls))
        a, b = self.two_spawns(mod)
        self.assertEqual((a, b), self.EXPECT)
        self.assertEqual(calls, [("LK_LOCK", 1), ("LK_UNLCK", 1), ("LK_LOCK", 1), ("LK_UNLCK", 1)])

    def test_msvcrt_unlocks_on_exempt_early_return(self):
        calls = []
        mod = load_model_pin(fcntl=None, msvcrt=fake_msvcrt(calls))
        res = mod.cap_check(CAP, "", "", "tu-x", NOW)  # no parent, no PD: exempt, returns inside the lock
        self.assertEqual(res[0], "exempt")
        self.assertEqual(calls, [("LK_LOCK", 1), ("LK_UNLCK", 1)])

    def test_no_lock_primitive_still_counts_and_reserves(self):
        mod = load_model_pin(fcntl=None, msvcrt=None)
        a, b = self.two_spawns(mod)
        self.assertEqual((a, b), self.EXPECT)
        self.assertEqual([r["tool_use_id"] for r in self.slots()], ["tu-1"])

    def test_locking_oserror_is_swallowed(self):
        calls = []
        mod = load_model_pin(fcntl=None, msvcrt=fake_msvcrt(calls, fail=OSError(36, "deadlock")))
        a, b = self.two_spawns(mod)  # lock and unlock both raise; the cap logic must still run
        self.assertEqual((a, b), self.EXPECT)
        self.assertEqual(calls, [("LK_LOCK", 1), ("LK_UNLCK", 1), ("LK_LOCK", 1), ("LK_UNLCK", 1)])


class TestSpawnProjectWindows(unittest.TestCase):
    def setUp(self):
        self.sp = load_spawn_project()
        self.tmp = tempfile.mkdtemp(prefix="win32-spawn-project-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.table = os.path.join(self.tmp, "medium-term.md")
        rows = [
            "| fwd | `C:/home/t/proj` | x |",
            "| back | `D:\\Work\\Back\\memory` | x |",
            "| unc | `\\\\srv\\share\\unc` | x |",
            "| tilde | `~\\tilde` | x |",
            "| tildefwd | `~/tildefwd/` | x |",
            "| posix | `/home/t/posix` | x |",
            "| bs | `/home/t/odd\\name` | x |",
        ]
        with open(self.table, "w", encoding="utf-8") as f:
            f.write("| slug | path | note |\n|---|---|---|\n" + "\n".join(rows) + "\n")
        p = mock.patch.dict(os.environ, {"SPAWN_MEDIUM_TERM": self.table})
        p.start()
        self.addCleanup(p.stop)
        self.home = "C:\\home\\t"

    def roots(self):
        return dict(self.sp.project_rows(self.home))

    def hit(self, path):
        return self.sp.longest_prefix(path, self.sp.project_rows(self.home))

    def test_rows_are_normalised(self):
        r = self.roots()
        self.assertEqual(r["fwd"], "C:/home/t/proj")
        self.assertEqual(r["back"], "D:/Work/Back")
        self.assertEqual(r["unc"], "//srv/share/unc")
        self.assertEqual(r["tilde"], "C:/home/t/tilde")
        self.assertEqual(r["tildefwd"], "C:/home/t/tildefwd")
        self.assertEqual(r["posix"], "/home/t/posix")

    def test_windows_cwd_against_forward_slash_root(self):
        self.assertEqual(self.hit("C:\\home\\t\\proj\\sub"), "fwd")
        self.assertEqual(self.hit("C:\\home\\t\\proj"), "fwd")
        self.assertEqual(self.hit("C:\\home\\t\\proj\\"), "fwd")
        self.assertEqual(self.hit("C:/home/t/proj/sub"), "fwd")

    def test_windows_cwd_against_backslash_root(self):
        self.assertEqual(self.hit("D:\\Work\\Back\\deep\\er"), "back")

    def test_drive_letter_paths_compare_case_insensitively(self):
        self.assertEqual(self.hit("c:\\HOME\\T\\PROJ\\sub"), "fwd")
        self.assertEqual(self.hit("d:/work/back/x"), "back")

    def test_boundary_still_enforced(self):
        self.assertIsNone(self.hit("C:\\home\\t\\projX"))
        self.assertIsNone(self.hit("C:\\home\\t\\proj-other\\sub"))

    def test_unc(self):
        self.assertEqual(self.hit("\\\\srv\\share\\unc\\sub"), "unc")

    def test_tilde_backslash_expansion_with_windows_home(self):
        self.assertEqual(self.sp._expand("~\\x", self.home).replace("\\", "/"), "C:/home/t/x")
        self.assertEqual(self.hit("C:\\home\\t\\tilde\\a"), "tilde")
        self.assertEqual(self.hit("C:\\home\\t\\tildefwd\\a"), "tildefwd")

    def test_tilde_backslash_with_posix_home(self):
        self.assertEqual(self.sp._expand("~\\x\\y", "/home/t"), "/home/t/x/y")

    def test_posix_unchanged(self):
        self.assertEqual(self.hit("/home/t/posix/sub"), "posix")
        self.assertIsNone(self.hit("/home/t/posixx"))
        self.assertEqual(self.sp._expand("~/x", "/home/t"), "/home/t/x")
        self.assertEqual(self.sp._expand("/x/a~b", "/home/t"), "/x/a~b")

    def test_posix_path_with_backslash_is_untouched(self):
        self.assertEqual(self.roots()["bs"], "/home/t/odd\\name")
        self.assertEqual(self.hit("/home/t/odd\\name/sub"), "bs")
        self.assertIsNone(self.hit("/home/t/odd/name/sub"))
        self.assertEqual(self.sp._norm("/home/t/odd\\name/"), "/home/t/odd\\name/")

    def test_resolve_log_file_for_windows_cwd(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "C:\\home\\t\\proj\\sub"}):
            os.environ.pop("SPAWN_LOG_FILE", None)
            got = self.sp.resolve_log_file({}, home=self.home).replace("\\", "/")
        self.assertEqual(got, "C:/home/t/proj/memory/spawns.jsonl")

    def test_project_line_with_windows_path(self):
        self.assertEqual(self.sp.spawn_project({"prompt": "Project: C:\\home\\t\\proj\\sub"}, home=self.home), "fwd")
        self.assertEqual(self.sp.spawn_project({"prompt": "Project: `~\\tilde\\a`, more"}, home=self.home), "tilde")
        self.assertEqual(self.sp.spawn_project({"prompt": "Project: /home/t/posix/x"}, home=self.home), "posix")
        self.assertEqual(self.sp.spawn_project({"prompt": "Project: https://example.com/a"}, home=self.home), None)


class TestUtf8Stdio(unittest.TestCase):
    def test_utf8_stdio_reconfigures_cp1252_streams(self):
        mod = load_model_pin()
        old = sys.stdin, sys.stdout, sys.stderr
        sys.stdin = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="backslashreplace")
        try:
            mod._utf8_stdio()
            seen = [(s.encoding, s.errors) for s in (sys.stdin, sys.stdout, sys.stderr)]
        finally:
            sys.stdin, sys.stdout, sys.stderr = old
        self.assertEqual([e for e, _ in seen], ["utf-8"] * 3)
        self.assertEqual(seen[2][1], "backslashreplace")  # stderr error policy not weakened/changed

    def test_utf8_stdio_never_raises_on_odd_streams(self):
        mod = load_model_pin()
        old = sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout, sys.stderr = None, io.StringIO(), object()
        try:
            mod._utf8_stdio()
        finally:
            sys.stdin, sys.stdout, sys.stderr = old


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="win32-model-pin-cli-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = os.path.join(self.tmp, "spawns.jsonl")
        self.map = os.path.join(self.tmp, "map.json")
        with open(self.map, "w", encoding="utf-8") as f:
            json.dump({"default": "sonnet", "categories": {}, "ghi_chu": "Đường dẫn tiếng Việt"}, f, ensure_ascii=False)
        os.makedirs(os.path.join(self.tmp, "home", ".claude"))
        os.makedirs(os.path.join(self.tmp, "agents"))
        os.makedirs(os.path.join(self.tmp, "state"))

    def env(self, **extra):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("MODEL_PIN_", "SPAWN_", "PYTHON", "LC_", "LANG"))
             and k not in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR")}
        e.update({"SPAWN_LOG_FILE": self.log, "MODEL_PIN_MAP": self.map,
                  "MODEL_PIN_AGENTS_DIR": os.path.join(self.tmp, "agents"),
                  "MODEL_PIN_STATE_DIR": os.path.join(self.tmp, "state"),
                  "MODEL_PIN_HOME": os.path.join(self.tmp, "home"), "MODEL_PIN_GLOBAL_LOG": "",
                  "MODEL_PIN_NOW": str(NOW), "PYTHONDONTWRITEBYTECODE": "1"})
        e.update(extra)
        return e

    def run_cli(self, env):
        payload = {"subagent_type": "general-purpose", "model": "opus", "fork": False, "is_teammate": False,
                   "workflow": False, "parent_spawn_id": "", "parent_agent": "root", "tool_use_id": "toolu_vi",
                   "description": "Đường dẫn", "prompt": "Viết báo cáo tiếng Việt: Đường Nguyễn Huệ, người Việt Nam"}
        r = subprocess.run([sys.executable, SCRIPT], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                           capture_output=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = [l for l in r.stdout.decode("utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lines), 1, r.stdout)
        return json.loads(lines[0])

    def test_vietnamese_prompt_on_cp1252_stdio(self):
        out = self.run_cli(self.env(PYTHONIOENCODING="cp1252"))
        self.assertEqual(out["reason"], "gp_category_map")  # decoded and decided, not the fail-open "error: ..." pass
        self.assertEqual((out["action"], out["new"]), ("rewrite", "sonnet"))

    def test_non_ascii_content_files_under_ascii_locale(self):
        # the map file holds UTF-8 text; the default open() encoding is the locale one (cp125x on Windows)
        out = self.run_cli(self.env(PYTHONIOENCODING="cp1252", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0",
                                    LC_ALL="C"))
        self.assertEqual(out["reason"], "gp_category_map")
        self.assertEqual(out["action"], "rewrite")


if __name__ == "__main__":
    unittest.main()
