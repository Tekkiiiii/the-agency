"""Windows-hostile spots in ledger.py, simulated on any OS (mock os.name / shutil.which / subprocess).
Proves the code PATHS take the right branch; it does not prove a real Windows run.
Isolation (CRITICAL, commit 66561de): ledger.HOME is a temp dir, SPAWN_LOG_FILE is a temp file, no test writes a real
ledger or <root>/logs. Every subprocess child gets HOME=<tmp> and SPAWN_LOG_FILE=<tmp>, and no AGENCY_HOME.
Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PY = os.path.join(HERE, "..", "bin", "ledger.py")
spec = importlib.util.spec_from_file_location("ledger_win32", LEDGER_PY)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)

D = {"description": "x", "parent_agent": "proj-pd", "prompt": "Skills: /frontend"}


class Home(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.log = os.path.join(self.home, "spawns.jsonl")
        os.makedirs(os.path.join(self.home, ".claude/scripts"))
        os.makedirs(os.path.join(self.home, ".claude/state"))
        open(os.path.join(self.home, ".claude/scripts/skill-route.py"), "w").close()
        for p in (mock.patch.object(ledger, "HOME", self.home),
                  mock.patch.object(ledger, "ROOT", os.path.join(self.home, ".claude")),
                  mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": self.log, "AGENCY_SKILL_ROUTER": "1",
                                               "SKILL_ROUTE_STATE_DIR": os.path.join(self.home, ".claude/state")})):
            p.start()
            self.addCleanup(p.stop)
        for k in ("SKILL_ROUTE_CHILD", "AGENCY_HOME", "CLAUDE_CONFIG_DIR"):
            os.environ.pop(k, None)  # patch.dict restores the caller's env afterwards


class Reconcile(Home):
    SCRIPT_PARTS = (".claude", "hooks", "lib", "reconcile-stale-spawns.sh")

    def test_no_bash_skips_cleanly(self):
        with mock.patch.object(ledger, "find_bash_cmd", return_value=None), \
                mock.patch.object(ledger.subprocess, "run") as run:
            ledger.reconcile(self.log)
        run.assert_not_called()

    def test_bash_present_argv_unchanged(self):
        # Built from components, not a literal "a/b/c": on Windows os.path.join yields backslashes only, and the
        # old mixed literal ("...\\.claude/hooks/lib/x.sh") never matched there (the-agency run 38510443081).
        with mock.patch.object(ledger, "find_bash_cmd", return_value="bash"), \
                mock.patch.object(ledger.subprocess, "run") as run:
            ledger.reconcile(self.log)
        run.assert_called_once()
        self.assertEqual(run.call_args[0][0], ["bash", os.path.join(self.home, *self.SCRIPT_PARTS), self.log])

    @unittest.skipIf(os.name == "nt", "posix argv contract")
    def test_posix_argv_is_the_bare_name_via_the_real_finder(self):
        with mock.patch("shutil.which", return_value="/bin/bash"), \
                mock.patch.object(ledger.subprocess, "run") as run:
            ledger.reconcile(self.log)
        self.assertEqual(run.call_args[0][0][0], "bash")


class FinderMissingFailsOpen(Home):
    """A half-deployed tree (hooks/lib/find_bash.py absent) must never break a live session."""

    def test_posix_falls_back_to_which(self):
        with mock.patch.object(ledger, "find_bash", None), mock.patch.object(os, "name", "posix"), \
                mock.patch("shutil.which", return_value="/bin/bash"):
            self.assertEqual(ledger.find_bash_cmd(), "bash")

    def test_nt_skips_rather_than_risk_the_wsl_launcher(self):
        with mock.patch.object(ledger, "find_bash", None), mock.patch.object(os, "name", "nt"), \
                mock.patch("shutil.which", return_value=r"C:\Windows\System32\bash.exe"):
            self.assertIsNone(ledger.find_bash_cmd())

    def test_finder_exception_means_skip(self):
        class Boom:
            @staticmethod
            def find_bash():
                raise RuntimeError("x")
        with mock.patch.object(ledger, "find_bash", Boom):
            self.assertIsNone(ledger.find_bash_cmd())


class ShadowPopen(Home):
    def popen_kwargs(self, name):
        with mock.patch.object(os, "name", name), mock.patch.object(ledger.subprocess, "Popen") as pop:
            ledger.fire_shadow("sid", dict(D), "general-purpose", D["prompt"])
        pop.assert_called_once()
        return pop.call_args[1]

    def test_nt_uses_creationflags_not_start_new_session(self):
        kw = self.popen_kwargs("nt")
        self.assertNotIn("start_new_session", kw)
        self.assertEqual(kw.get("creationflags"), 0x8 | 0x200)

    def test_posix_keeps_start_new_session(self):
        kw = self.popen_kwargs("posix")
        self.assertIs(kw.get("start_new_session"), True)
        self.assertNotIn("creationflags", kw)


class VerifyPaths(Home):
    def run_verify(self, name, text):
        out = io.StringIO()
        with mock.patch.object(os, "name", name), contextlib.redirect_stdout(out):
            ledger.verify({"text": text})
        return out.getvalue()

    def test_log_row_lands_under_the_patched_home_or_the_override_never_the_real_log(self):
        """2026-10-13: 4 test rows leaked into the REAL logs/artifact-verify.jsonl (a port whose verify() ignored the patched HOME)."""
        default = os.path.join(self.home, ".claude", "logs", "artifact-verify.jsonl")
        self.run_verify("posix", "DONE /nope/a.pdf")
        self.assertEqual(len(open(default, encoding="utf-8").read().splitlines()), 1)
        elsewhere = os.path.join(self.home, "elsewhere", "av.jsonl")
        with mock.patch.dict(os.environ, {"ARTIFACT_VERIFY_LOG": elsewhere}):
            self.run_verify("posix", "DONE /nope/b.pdf")
        self.assertEqual(len(open(elsewhere, encoding="utf-8").read().splitlines()), 1)
        self.assertEqual(len(open(default, encoding="utf-8").read().splitlines()), 1)

    def test_nt_flags_missing_drive_letter_backslash_path(self):
        out = self.run_verify("nt", "DONE wrote C:\\Users\\t\\out.pdf for you")
        self.assertIn("MISSING: C:\\Users\\t\\out.pdf", out)

    def test_nt_flags_missing_drive_letter_forward_slash_path(self):
        out = self.run_verify("nt", "DONE wrote D:/work/report.docx now")
        self.assertIn("MISSING: D:/work/report.docx", out)

    def test_nt_expands_tilde_backslash_against_home(self):
        open(os.path.join(self.home, "present.pdf"), "w").close()
        out = self.run_verify("nt", "DONE ~\\present.pdf and ~\\gone.pdf")
        self.assertIn("MISSING: " + os.path.join(self.home, "gone.pdf"), out)
        self.assertIn("OK:      " + os.path.join(self.home, "present.pdf"), out)

    def test_posix_does_not_flag_drive_letter_path(self):
        self.assertEqual(self.run_verify("posix", "DONE wrote C:\\x.pdf and D:/y/z.pdf"), "")

    def test_posix_still_flags_abs_and_tilde(self):
        out = self.run_verify("posix", "DONE /nope/a.pdf and ~/nope/b.pdf")
        self.assertIn("MISSING: /nope/a.pdf", out)
        self.assertIn("MISSING: " + os.path.join(self.home, "nope/b.pdf"), out)


class Utf8Stdio(unittest.TestCase):
    def test_reconfigures_cp1252_streams_to_utf8(self):
        helper = getattr(ledger, "_utf8_stdio", None)
        self.assertIsNotNone(helper, "ledger._utf8_stdio missing")
        s_in = io.TextIOWrapper(io.BytesIO("ệ".encode("utf-8")), encoding="cp1252")
        s_out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        s_err = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        with mock.patch.object(sys, "stdin", s_in), mock.patch.object(sys, "stdout", s_out), \
                mock.patch.object(sys, "stderr", s_err):
            helper()
        self.assertEqual([s.encoding for s in (s_in, s_out, s_err)], ["utf-8"] * 3)
        self.assertEqual(s_in.read(), "ệ")

    def test_streams_without_reconfigure_are_left_alone(self):
        helper = getattr(ledger, "_utf8_stdio", None)
        self.assertIsNotNone(helper, "ledger._utf8_stdio missing")
        with mock.patch.object(sys, "stdin", object()), mock.patch.object(sys, "stdout", object()), \
                mock.patch.object(sys, "stderr", object()):
            helper()  # must not raise

    def test_cli_cp1252_locale_roundtrips_vietnamese(self):
        """Real subprocess, PYTHONIOENCODING=cp1252 (a Windows code page), Vietnamese path in/out. Isolated HOME."""
        home = tempfile.mkdtemp()
        env = {k: v for k, v in os.environ.items() if k not in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR")}
        env.update(HOME=home, USERPROFILE=home, PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1",
                   SPAWN_LOG_FILE=os.path.join(home, "spawns.jsonl"))
        text = "DONE saved /nope/bao-cao-việt.pdf"
        r = subprocess.run([sys.executable, LEDGER_PY, "verify"], input=json.dumps({"text": text}).encode("utf-8"),
                           env=env, capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 0)
        self.assertIn("MISSING: /nope/bao-cao-việt.pdf".encode("utf-8"), r.stdout)


if __name__ == "__main__":
    unittest.main()
