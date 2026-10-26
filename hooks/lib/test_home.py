"""test_home.py: ONE shared helper that makes a test's "home directory" hermetic on every OS. stdlib only.

WHY: os.path.expanduser("~") reads $HOME on POSIX but %USERPROFILE% (then HOMEDRIVE+HOMEPATH) on Windows, and ignores
$HOME there. A test that patches only HOME (what the first isolation pass did) is hermetic on macOS/Linux and silently
NOT hermetic on a real Windows runner: every module that calls expanduser per call (hooks/lib/spawn_project.py, the
shell writers' python3 -c blocks, ...) resolves the REAL runner home. 2026-10-14 a real windows-latest CI run: 15 failures
+ 1 error from exactly that, and ledger.refuses_real_ledger() (correctly) refused the writes. Simulating Windows by
patching HOME alone hid it. Do not write another HOME-only patch: use this module.

API (all pure, no import-time side effects):
  home_env(home, base=None) -> dict
      The environment variables that define "home" on both OS families: HOME, USERPROFILE, HOMEDRIVE, HOMEPATH.
      `base` (default: a copy of os.environ) is returned updated, ready for subprocess.run(env=...).
  hermetic_home(home)  -- context manager
      mock.patch.dict(os.environ, home_env-vars): expanduser("~") == home on macOS, Linux AND Windows inside it.
  windows_expanduser()  -- context manager
      Simulates Windows on any OS: os.path.expanduser becomes ntpath.expanduser (USERPROFILE only, never HOME).
      Use it to prove a code path does not depend on $HOME. Combine with hermetic_home(...) for the "good" case, or
      set USERPROFILE to a decoy to prove the code under test uses its explicit home, not the process home.
  shell_env(home, **extra) -> dict
      home_env(home) minus the vars that make a child resolve a different agency root; for subprocess.run(env=).

  isolate_process_home(real_claude=None) -> IsolatedHome(home, claude, real_home, mirrored, skipped)
      THE repo-wide "tests never write live logs" bootstrap (2026-10-14). Moves HOME/USERPROFILE/HOMEDRIVE/HOMEPATH of THIS
      process (and so of every subprocess a test starts) to a fresh temp tree BEFORE any module that computes its home at
      import time loads. Every live writer in this repo (ledger.py verify/emit_metric, emit-metric.sh, cost-tracker.sh,
      write-evidence.sh, bg-job-warn.sh, jev_client, skill-route, spawn-plan, jev-feedback, skill-tiers, model-pin, ...) derives
      its log path from the home, so a test that forgot to isolate writes into the temp tree, not into the real agency root.
        <home>/.claude/{logs,state,memory,projects}  fresh, empty, REAL dirs (all data the writers touch lives here)
        <home>/.claude/{hooks,scripts,mods,agents,evals,tools,commands,skills,design-system}  SYMLINKS to the real code, so tests
            and scripts that read code at expanduser("~") + "/.claude/..." keep working. In the repo the "real code" is the checkout root.
            Symlink refused (Windows without the privilege) -> small dirs (<= 16 MB, never skills/tools) are copied, the rest are
            SKIPPED and listed in `skipped`; a test that needs a skipped dir must skip with a clear message, never pass silently.
      Also: records the real home in LIVE_LOG_REAL_HOME and the real agency root (AGENCY_HOME -> CLAUDE_CONFIG_DIR -> <home>/.claude)
      in LIVE_LOG_REAL_ROOT (live_log_guard reads both), sets SPAWN_LEDGER_TEST=1 (ledger.py then refuses
      any non-temp spawns.jsonl) and TEST_HOME_ISOLATED=1, and drops AGENCY_HOME / CLAUDE_CONFIG_DIR plus every per-writer path
      override (WRITER_ENV) that might point at a real log. Idempotent; the tree is removed at exit with remove_tree().
  remove_tree(path)
      Deletes a tree WITHOUT ever following a symlink: every symlink is unlinked first, then rmtree. A plain rmtree on a mirror
      is only safe where rmtree itself refuses to follow links; do not rely on that, this is the dangerous failure mode (it would
      delete real code). Tested in hooks/tests/test_live_log_guard.py.

Used by mods/spawn-ledger/tests/*, hooks/tests/*, scripts/tests/* (each suite's test_00_isolation.py calls isolate_process_home()).
Keep this API stable (add, do not rename).
"""
import atexit
import collections
import contextlib
import ntpath
import os
import shutil
import tempfile
from unittest import mock

CODE_ENTRIES = ("hooks", "scripts", "mods", "agents", "evals", "tools", "commands", "skills", "design-system", "statusline.sh")
NEVER_COPY = ("skills", "tools")  # symlink or skip: skills is a huge submodule, tools holds ~1.5 GB
COPY_LIMIT = 16 * 1024 * 1024
DATA_DIRS = ("logs", "state", "memory", "projects")
WRITER_ENV = ("SPAWN_LOG_FILE", "SPAWN_LEDGER_METRICS_FILE", "SPAWN_LEDGER_EXTRA_LOGS", "SPAWN_MEDIUM_TERM", "ARTIFACT_VERIFY_LOG",
              "JEV_USAGE_LOG", "JEV_NOTIFY_LOG", "JEV_FEEDBACK_LOG", "SKILL_ROUTE_LOG", "SKILL_ROUTE_SHADOW_LOG",
              "SKILL_ROUTE_STATE_DIR", "SPAWN_PLAN_LOG", "SPAWN_PLAN_SHADOW_LOG", "MODEL_PIN_HOME", "MODEL_PIN_STATE_DIR",
              "JEV_GATE_HOME", "STATUS_FILE", "SPAWNS_FILE", "AGENCY_HOME", "CLAUDE_CONFIG_DIR", "CLAUDE_PROJECT_DIR")

IsolatedHome = collections.namedtuple("IsolatedHome", "home claude real_home mirrored skipped")
_ISOLATED = None


def home_env(home, base=None):
    env = dict(os.environ if base is None else base)
    drive, tail = ntpath.splitdrive(home)
    env.update({"HOME": home, "USERPROFILE": home, "HOMEDRIVE": drive, "HOMEPATH": tail or home})
    return env


def shell_env(home, **extra):
    env = home_env(home)
    for k in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR"):
        env.pop(k, None)
    env.update(extra)
    return env


@contextlib.contextmanager
def hermetic_home(home):
    keys = ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")
    env = home_env(home, base={})
    with mock.patch.dict(os.environ, {k: env[k] for k in keys}):
        yield home


@contextlib.contextmanager
def windows_expanduser():
    with mock.patch("os.path.expanduser", ntpath.expanduser):
        yield


def _tree_size(path):
    if not os.path.isdir(path) or os.path.islink(path):
        return os.path.getsize(path) if os.path.exists(path) else 0
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
        if total > COPY_LIMIT:
            break
    return total


def remove_tree(path):
    """rmtree that never follows a symlink: unlink every link first (a mirror's links point at REAL code)."""
    for dirpath, dirnames, filenames in os.walk(path, topdown=True, followlinks=False):
        for name in list(dirnames) + list(filenames):
            p = os.path.join(dirpath, name)
            if os.path.islink(p):
                try:
                    os.unlink(p)
                except OSError:
                    os.rmdir(p)  # a Windows directory symlink / junction
        dirnames[:] = [d for d in dirnames if os.path.isdir(os.path.join(dirpath, d)) and not os.path.islink(os.path.join(dirpath, d))]
    shutil.rmtree(path, ignore_errors=True)


def _mirror(real, fake, mirrored, skipped, label):
    if not os.path.lexists(real):
        return
    try:
        os.symlink(real, fake, target_is_directory=os.path.isdir(real))
        mirrored.append(label)
        return
    except (OSError, NotImplementedError):
        pass
    if label.split("/")[0] in NEVER_COPY or _tree_size(real) > COPY_LIMIT:
        skipped.append(label)
    elif os.path.isdir(real):
        shutil.copytree(real, fake, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        mirrored.append(label)
    else:
        shutil.copy2(real, fake)
        mirrored.append(label)


def isolate_process_home(real_claude=None):
    """See the module docstring. Call it first thing in a suite (test_00_isolation.py), before importing code under test."""
    global _ISOLATED
    if _ISOLATED is not None:
        return _ISOLATED
    if os.environ.get("TEST_HOME_ISOLATED") == "1":  # a child of an isolated process: reuse, do not nest
        home = os.path.expanduser("~")
        return IsolatedHome(home, os.path.join(home, ".claude"), os.environ.get("LIVE_LOG_REAL_HOME", ""), [], [])
    import live_log_guard  # same directory; imported lazily so test_home stays importable on its own
    real_home = os.environ.get("LIVE_LOG_REAL_HOME") or live_log_guard.real_home({k: v for k, v in os.environ.items() if k != "SPAWN_LEDGER_GUARD_HOME"})
    real_claude = real_claude or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    home = os.path.realpath(tempfile.mkdtemp(prefix="claude-test-home-"))
    claude = os.path.join(home, ".claude")
    os.makedirs(claude)
    for d in DATA_DIRS:
        os.makedirs(os.path.join(claude, d))
    mirrored, skipped = [], []
    for entry in CODE_ENTRIES:
        _mirror(os.path.join(real_claude, entry), os.path.join(claude, entry), mirrored, skipped, entry)
    emit = os.path.join(real_claude, "memory", "metrics", "emit-metric.sh")  # the one memory/ file scripts invoke
    if os.path.isfile(emit):
        os.makedirs(os.path.join(claude, "memory", "metrics"))
        _mirror(emit, os.path.join(claude, "memory", "metrics", "emit-metric.sh"), mirrored, skipped, "memory/metrics/emit-metric.sh")
    real_root = os.environ.get("LIVE_LOG_REAL_ROOT") or live_log_guard.real_root({k: v for k, v in os.environ.items() if k != "SPAWN_LEDGER_GUARD_HOME"})
    for k in WRITER_ENV:
        os.environ.pop(k, None)
    os.environ.update(home_env(home, base={}))
    os.environ.update({"LIVE_LOG_REAL_HOME": real_home, "LIVE_LOG_REAL_ROOT": real_root, "SPAWN_LEDGER_TEST": "1", "TEST_HOME_ISOLATED": "1"})
    atexit.register(remove_tree, home)
    _ISOLATED = IsolatedHome(home, claude, real_home, mirrored, skipped)
    return _ISOLATED
