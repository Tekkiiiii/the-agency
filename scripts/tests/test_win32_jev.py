"""Windows-hostile spots in scripts/jev_client.py, simulated on any OS (mock sys.platform / os.getuid).
Proves the code PATHS take the right branch; it does not prove a real Windows run (see mods/README.md Windows status).
Isolation: no real notification (subprocess.run is mocked), the notify log and the temp dir are temp paths, and
AGENCY_HOME / CLAUDE_CONFIG_DIR point at a temp dir so nothing resolves to a real agency root.
Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_win32_jev*' -v"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import jev_client  # noqa: E402


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
        with mock.patch.object(os, "getuid", create=True):
            del os.getuid  # what Windows looks like; mock.patch restores it on exit
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
