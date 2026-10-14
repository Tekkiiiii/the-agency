"""Windows-hostile spots in scripts/jev_client.py and scripts/jev-spawn-gate.py, simulated on any OS (mock sys.platform / os.getuid).
Proves the code PATHS take the right branch; it does not prove a real Windows run (see mods/README.md Windows status).
Isolation: no real notification (subprocess.run is mocked), the notify log and the temp dir are temp paths, and
AGENCY_HOME / CLAUDE_CONFIG_DIR point at a temp dir so nothing resolves to a real agency root.
Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_win32_jev*' -v"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import jev_client  # noqa: E402

GATE = os.path.join(SCRIPTS, "jev-spawn-gate.py")
gate = None
if os.path.isfile(GATE):  # a copy of scripts/ without the gate (older layout): the gate class below skips
    _spec = importlib.util.spec_from_file_location("jev_spawn_gate_win32", GATE)
    gate = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(gate)


class _Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="win32-jev-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"AGENCY_HOME": self.tmp, "CLAUDE_CONFIG_DIR": self.tmp})
        env.start()
        self.addCleanup(env.stop)


class Notify(_Isolated):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(jev_client, "_notify_log_path", lambda: os.path.join(self.tmp, "notify.log"))
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop("JEV_NOTIFY", None)

    def notify(self, platform):
        with mock.patch.object(sys, "platform", platform), mock.patch.object(jev_client.subprocess, "run") as run:
            jev_client._notify("down", "t", "m")
        return run

    def test_win32_skips_osascript_but_logs(self):
        self.assertEqual(self.notify("win32").call_count, 0)
        with open(os.path.join(self.tmp, "notify.log"), encoding="utf-8") as f:
            self.assertIn("\tdown", f.read())

    def test_linux_skips_osascript(self):
        self.assertEqual(self.notify("linux").call_count, 0)

    def test_darwin_still_calls_osascript(self):
        run = self.notify("darwin")
        run.assert_called_once()
        self.assertEqual(run.call_args[0][0][0], "osascript")

    def test_darwin_respects_jev_notify_off(self):
        os.environ["JEV_NOTIFY"] = "0"
        self.assertEqual(self.notify("darwin").call_count, 0)


class HaikuCwd(_Isolated):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(jev_client.tempfile, "gettempdir", lambda: self.tmp)
        p.start()
        self.addCleanup(p.stop)

    def test_without_getuid_falls_back_to_username(self):
        # Windows looks like "os has no getuid". Remove it by hand and put it back by hand: mock.patch(create=True)
        # cannot do this, on a real Windows os (no getuid to begin with) its exit-time delattr raises AttributeError.
        had = hasattr(os, "getuid")
        saved = getattr(os, "getuid", None)
        if had:
            del os.getuid
        self.addCleanup(lambda: setattr(os, "getuid", saved) if had else None)
        with mock.patch("getpass.getuser", return_value="winuser"):
            try:
                d = jev_client._haiku_cwd()
            except AttributeError as e:
                self.fail("_haiku_cwd raised without os.getuid: %s" % e)
        self.assertEqual(d, os.path.join(self.tmp, "jev-haiku-cwd-winuser"))
        self.assertTrue(os.path.isdir(d))

    def test_posix_dir_name_is_numeric_uid(self):
        if not hasattr(os, "getuid"):
            self.skipTest("no os.getuid on this platform")
        self.assertEqual(jev_client._haiku_cwd(), os.path.join(self.tmp, "jev-haiku-cwd-%d" % os.getuid()))


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(gate is None, "scripts/jev-spawn-gate.py not present")
class GateUtf8(_Isolated):
    def test_helper_reconfigures_cp1252_streams_to_utf8(self):
        helper = getattr(gate, "_utf8_stdio", None)
        self.assertIsNotNone(helper, "jev-spawn-gate._utf8_stdio missing")
        s_in = io.TextIOWrapper(io.BytesIO("ệ".encode("utf-8")), encoding="cp1252")
        s_out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        s_err = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        with mock.patch.object(sys, "stdin", s_in), mock.patch.object(sys, "stdout", s_out), \
                mock.patch.object(sys, "stderr", s_err):
            helper()
        self.assertEqual([s.encoding for s in (s_in, s_out, s_err)], ["utf-8"] * 3)

    def test_main_reads_stdin_as_utf8_when_locale_is_cp1252(self):
        """main() entry: a cp1252 stdin carrying UTF-8 Vietnamese must reach decide() undamaged."""
        raw_in = json.dumps({"prompt": "Viết báo cáo tháng"}, ensure_ascii=False).encode("utf-8")
        s_in = io.TextIOWrapper(io.BytesIO(raw_in), encoding="cp1252")
        # Windows text mode translates "\n" to "\r\n" on write (newline=None does it there, os.linesep); simulate it on any
        # OS so the byte contract (exactly one JSON line ending in a bare LF) is tested where it can break.
        s_out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="\r\n")
        seen = {}

        def fake_decide(raw):
            seen["raw"] = raw
            return {"action": "pass"}

        with mock.patch.object(sys, "stdin", s_in), mock.patch.object(sys, "stdout", s_out), \
                mock.patch.object(sys, "stderr", io.StringIO()), mock.patch.object(gate, "decide", fake_decide):
            with self.assertRaises(SystemExit) as cm:
                gate.main()
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(seen.get("raw"), raw_in.decode("utf-8"))
        s_out.flush()
        self.assertEqual(s_out.buffer.getvalue(), b'{"action": "pass"}\n')

    def test_cli_cp1252_locale_vietnamese_prompt_one_json_line_exit_0(self):
        env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1", JEV_GATE_OFF="1",
                   AGENCY_HOME=self.tmp, SKILL_ROUTE_STATE_DIR=os.path.join(self.tmp, "state"))
        env.pop("AGENCY_SKILL_ROUTER", None)  # disabled by default; JEV_GATE_OFF=1 pins pass either way
        req = {"subagent_type": "general-purpose", "description": "báo cáo",
               "prompt": "Viết báo cáo tháng bằng tiếng Việt: ệ ầ ữ"}
        r = subprocess.run([sys.executable, GATE], input=json.dumps(req, ensure_ascii=False).encode("utf-8"),
                           env=env, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.decode("ascii").splitlines()
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertEqual(json.loads(lines[0]), {"action": "pass"})
