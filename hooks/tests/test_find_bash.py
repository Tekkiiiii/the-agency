#!/usr/bin/env python3
"""Tests for hooks/lib/find_bash.py: which `bash` a Python caller may exec.

Regression for a real windows-latest CI run (2026-10-14): the runner has
C:\\Windows\\System32\\bash.exe, the WSL launcher ("Windows Subsystem for Linux has no installed distributions", rc 1,
UTF-16 text on stdout, empty stderr). subprocess.run(["bash", ...]) resolves it through CreateProcess BEFORE PATH, while
shutil.which("bash") (PATH order) said Git's bash: so ledger.reconcile() was a silent no-op on real Windows and 6 shell
tests failed with "1 != 0 : <empty stderr>". The nt branch is exercised on any OS via injected environ/isfile/which
(ntpath logic, no mock of os.name); the real-host test only runs on Windows.
Run from the repo root: python3 -m unittest discover -s hooks/tests -p 'test_find_bash.py'
"""
import importlib.util
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("find_bash", os.path.join(HERE, "..", "lib", "find_bash.py"))
fb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fb)

SYS32 = r"C:\Windows\System32\bash.exe"
GIT_BIN = r"C:\Program Files\Git\bin\bash.exe"
GIT_USR = r"C:\Program Files\Git\usr\bin\bash.exe"
APPS = r"C:\Users\runneradmin\AppData\Local\Microsoft\WindowsApps\bash.exe"


def nt(path, files, which=None, **env):
    environ = {"PATH": path}
    environ.update(env)
    return fb.find_bash(nt=True, environ=environ, isfile=lambda p: p in files, which=which or (lambda n: None))


class WslLauncherIsNeverChosen(unittest.TestCase):
    def test_system32_first_on_path_is_skipped_for_git(self):
        self.assertEqual(nt(r"C:\Windows\System32;C:\Program Files\Git\bin", {SYS32, GIT_BIN}), GIT_BIN)

    def test_system32_only_returns_none(self):
        self.assertIsNone(nt(r"C:\Windows\System32", {SYS32}))

    def test_windowsapps_alias_is_skipped(self):
        self.assertIsNone(nt(r"C:\Users\runneradmin\AppData\Local\Microsoft\WindowsApps", {APPS}))

    def test_syswow64_and_sysnative_are_skipped(self):
        for d in ("SysWOW64", "Sysnative"):
            p = "C:\\Windows\\%s\\bash.exe" % d
            self.assertIsNone(nt("C:\\Windows\\%s" % d, {p}), d)

    def test_system32_path_with_forward_slashes_and_case_is_still_skipped(self):
        self.assertIsNone(nt("c:/windows/SYSTEM32", {r"c:\windows\SYSTEM32\bash.exe"}))

    def test_path_order_wins_among_good_candidates(self):
        self.assertEqual(nt(r"C:\Program Files\Git\usr\bin;C:\Program Files\Git\bin", {GIT_USR, GIT_BIN}), GIT_USR)

    def test_quoted_path_entries_are_unquoted(self):
        self.assertEqual(nt('"C:\\Program Files\\Git\\bin"', {GIT_BIN}), GIT_BIN)


class FallbackWhenGitIsNotOnPath(unittest.TestCase):
    def test_program_files(self):
        self.assertEqual(nt(r"C:\Windows\System32", {SYS32, GIT_BIN}, ProgramFiles=r"C:\Program Files"), GIT_BIN)

    def test_program_files_x86(self):
        x86 = r"C:\Program Files (x86)\Git\bin\bash.exe"
        self.assertEqual(nt("", {x86}, **{"ProgramFiles(x86)": r"C:\Program Files (x86)"}), x86)

    def test_per_user_git(self):
        usr = r"C:\Users\u\AppData\Local\Programs\Git\bin\bash.exe"
        self.assertEqual(nt("", {usr}, LOCALAPPDATA=r"C:\Users\u\AppData\Local"), usr)

    def test_next_to_git_exe(self):
        git = r"D:\tools\Git\cmd\git.exe"
        want = r"D:\tools\Git\bin\bash.exe"
        self.assertEqual(nt("", {want}, which=lambda n: git if n == "git" else None), want)

    def test_env_keys_are_case_insensitive_like_windows(self):
        self.assertEqual(nt(r"C:\Windows\System32", {GIT_BIN}, PROGRAMFILES=r"C:\Program Files"), GIT_BIN)

    def test_nothing_found_returns_none(self):
        self.assertIsNone(nt("", set()))


class PosixKeepsTheBareName(unittest.TestCase):
    """macOS/Linux argv must stay byte-identical: ["bash", script, log]."""

    def test_bare_bash_when_on_path(self):
        self.assertEqual(fb.find_bash(nt=False, which=lambda n: "/bin/bash"), "bash")

    def test_none_when_absent(self):
        self.assertIsNone(fb.find_bash(nt=False, which=lambda n: None))


@unittest.skipUnless(os.name == "nt", "real-host check: only meaningful on Windows")
class RealWindowsHost(unittest.TestCase):
    def test_found_bash_runs_a_script_and_is_not_the_wsl_launcher(self):
        b = fb.find_bash()
        self.assertIsNotNone(b, "Git for Windows bash not found on this host")
        self.assertNotIn("system32", b.lower())
        r = subprocess.run([b, "-c", "echo ok"], capture_output=True, text=True, timeout=30)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "ok"), r.stderr)


if __name__ == "__main__":
    unittest.main()
