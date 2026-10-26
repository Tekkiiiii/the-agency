"""find_bash.py: which `bash` may a Python caller exec? ONE answer for ledger.py and the tests. stdlib only.

  find_bash() -> str | None
      POSIX: the bare name "bash" when it is on PATH (argv stays byte-identical to what callers always ran), else None.
      Windows: the full path of a Git for Windows bash.exe, else None (callers skip, as they always did without bash).

WHY: a Windows host has C:\\Windows\\System32\\bash.exe, the WSL launcher. subprocess.run(["bash", ...]) finds it through
CreateProcess's search order (system directory BEFORE PATH), even when shutil.which("bash") (PATH order) reports Git's bash.
Without a distro the launcher prints UTF-16 "Windows Subsystem for Linux has no installed distributions" to stdout and
exits 1; callers that discard output (ledger.reconcile) silently do nothing. Proven on windows-latest 2026-10-14.
So on Windows the full path is resolved here and System32 / SysWOW64 / Sysnative / WindowsApps are never returned.
Search order: PATH entries in order, then %ProgramFiles%, %ProgramW6432%, %ProgramFiles(x86)%, %LOCALAPPDATA%\\Programs
(Git\\bin, Git\\usr\\bin), then the directory that holds git.exe (..\\bin).

Test seam (find_bash(nt=, environ=, isfile=, which=)): the Windows branch is pure ntpath logic, runnable on any OS.
"""
import ntpath
import os
import shutil

_REJECT = ("\\windows\\system32\\", "\\windows\\syswow64\\", "\\windows\\sysnative\\", "\\windowsapps\\")


def _wsl_launcher(path):
    p = ntpath.normcase(ntpath.normpath(path)).replace("/", "\\")
    return any(r in p for r in _REJECT)


def _candidates(environ, which):
    for d in environ.get("PATH", "").split(";"):
        d = d.strip().strip('"')
        if d:
            yield ntpath.join(d, "bash.exe")
    for key, sub in (("PROGRAMFILES", "Git"), ("PROGRAMW6432", "Git"), ("PROGRAMFILES(X86)", "Git"),
                     ("LOCALAPPDATA", ntpath.join("Programs", "Git"))):
        root = environ.get(key)
        if root:
            for leaf in ("bin", ntpath.join("usr", "bin")):
                yield ntpath.join(root, sub, leaf, "bash.exe")
    git = which("git")
    if git:
        yield ntpath.join(ntpath.dirname(ntpath.dirname(git)), "bin", "bash.exe")


def find_bash(nt=None, environ=None, isfile=None, which=None):
    nt = (os.name == "nt") if nt is None else nt
    which = which or shutil.which
    if not nt:
        return "bash" if which("bash") else None
    isfile = isfile or os.path.isfile
    env = {k.upper(): v for k, v in (os.environ if environ is None else environ).items()}
    for cand in _candidates(env, which):
        if not _wsl_launcher(cand) and isfile(cand):
            return cand
    return None
