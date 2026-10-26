"""live_log_guard.py: ONE guard that fails a test run if it touched a LIVE log. stdlib only, no import-time side effects.

WHY: un-isolated tests once leaked tu-1/tu-2 rows into logs/spawns.jsonl, and a later port run leaked 4 rows into
logs/artifact-verify.jsonl (ledger.verify wrote under the import-time root and ignored a patched HOME). Isolation is opt-in per test, so the guard watches the files instead of trusting each test.
Used by the test_zz_live_log_guard.py loader in mods/spawn-ledger/tests, hooks/tests and scripts/tests (test_zz sorts last).

HOW: baseline() snapshots every live log once (size, sha256 of the bytes, mtime_ns) the first time it is called; the suite
loads it from test_00_isolation.py, i.e. before any test runs. violations(baseline) compares at the end. Live logs =
  <root>/logs/**                       <root>/memory/**/*.jsonl      <root>/memory/metrics/*.{jsonl,log}
  <root>/metrics/*.jsonl               every spawns.jsonl ledger: <root>/projects/*/memory/,
  <home>/projects/*/memory/, <home>/projects/*/*/memory/
<root> = the agency root, resolved with the repo ladder AGENCY_HOME -> CLAUDE_CONFIG_DIR -> <home>/.claude (real_root()); the
default <home>/.claude is watched as well. With an explicit home= argument only <home>/.claude is watched (self-tests).
<home> = SPAWN_LEDGER_GUARD_HOME (explicit stand-in, used to demonstrate the guard biting), else LIVE_LOG_REAL_HOME (recorded by
test_home.isolate_process_home() BEFORE it moves HOME), else the passwd entry (not $HOME: tests patch HOME), else expanduser("~").
<root> likewise: SPAWN_LEDGER_GUARD_HOME/.claude, else LIVE_LOG_REAL_ROOT (recorded before isolation), else the ladder above.

THREE CLASSES, because real sessions legitimately append to some logs while a suite runs (so size/mtime alone would flake):
  SESSION  written by live hooks during any session (spawns, events, costs, write-evidence, skill-route*, spawn-plan*, jev-*, ...
           and every log not listed below). Fails on (i) existing bytes rewritten/truncated/deleted, (ii) an appended JSON row
           that carries a TEST FINGERPRINT: a tool_use_id that is not empty/`toolu_...`, or a fake path (C:\\Users\\t\\, D:/work/,
           /nope/, /home/t/, gone.pdf, zz-test-proj) in a path-like field (path, file, log_file, cwd, root, missing, found,
           transcript_path). Free text (prompt_excerpt, agent_excerpt, description) is NOT scanned: a live spawn prompt may quote
           those paths. A half-written last line (a writer mid-append) is ignored.
  STATIC   no live session writes it in a normal run: artifact-verify.jsonl, events-seed-archive.jsonl, *.bak*. ANY change
           (size, bytes, mtime) or a new file fails. Tradeoff: artifact-verify.jsonl DOES get a real row when a subagent claims
           DONE with a missing file; one landing inside a suite run (seconds) fails it. That is rare and the failure message names
           the file; re-run. Accepted: a leak there is exactly the 2026-10-13 bug.
  IGNORED  daemon / cron / lock files nobody here writes in a test: obsidian-mcp-*, pd-heartbeat*, canary-check*, *.lock,
           *reconcile-marker, *.tmp*.
Not detected on purpose: ts-equal bursts (save-state legitimately emits several events in one second; a real events.jsonl has many such).

API: real_home(env) / real_root(env) / watched(home) / classify(path) / snapshot_all(home) / baseline() / violations(before, home) / row_problems(line).
"""
import fnmatch
import glob
import hashlib
import json
import os
import re
try:
    import pwd
except ImportError:  # win32: no pwd
    pwd = None

STATIC, SESSION, IGNORED = "static", "session", "ignored"

_IGNORED = ("obsidian-mcp-*", "pd-heartbeat*", "canary-check*", "*.lock", "*reconcile-marker", "*.tmp*")
_STATIC = ("artifact-verify.jsonl", "events-seed-archive.jsonl", "*.bak*")

PATH_FIELDS = ("path", "file", "log_file", "cwd", "root", "missing", "found", "transcript_path")
FAKE_PATH = re.compile(r"[A-Za-z]:[\\/]+(?:Users[\\/]+t[\\/]|work[\\/])|/nope/|/home/t/|gone\.pdf|zz-test-proj")


def real_home(env=None):
    env = os.environ if env is None else env
    explicit = env.get("SPAWN_LEDGER_GUARD_HOME") or env.get("LIVE_LOG_REAL_HOME")
    if explicit:
        return explicit
    if pwd is not None and hasattr(os, "getuid"):
        try:
            return pwd.getpwuid(os.getuid()).pw_dir
        except KeyError:
            pass
    return os.path.expanduser("~")


def real_root(env=None):
    """The agency root the live writers use: SPAWN_LEDGER_GUARD_HOME/.claude (stand-in), else LIVE_LOG_REAL_ROOT (recorded by
    test_home.isolate_process_home() before it clears AGENCY_HOME / CLAUDE_CONFIG_DIR), else the repo ladder
    AGENCY_HOME -> CLAUDE_CONFIG_DIR -> <real home>/.claude."""
    env = os.environ if env is None else env
    stand_in = env.get("SPAWN_LEDGER_GUARD_HOME")
    if stand_in:
        return os.path.join(stand_in, ".claude")
    return env.get("LIVE_LOG_REAL_ROOT") or env.get("AGENCY_HOME") or env.get("CLAUDE_CONFIG_DIR") or os.path.join(real_home(env), ".claude")


def classify(path):
    name = os.path.basename(path)
    if any(fnmatch.fnmatch(name, p) for p in _IGNORED):
        return IGNORED
    if any(fnmatch.fnmatch(name, p) for p in _STATIC):
        return STATIC
    return SESSION


def _walk(root, want):
    out = []
    for dirpath, _dirs, files in os.walk(root):
        out += [os.path.join(dirpath, f) for f in files if want(f)]
    return out


def watched(home=None):
    h = home or real_home()
    roots = {os.path.join(h, ".claude")} if home else {real_root(), os.path.join(h, ".claude")}
    paths = []
    for c in sorted(roots):
        paths += _walk(os.path.join(c, "logs"), lambda f: True)
        paths += _walk(os.path.join(c, "memory"), lambda f: f.endswith(".jsonl"))
        paths += glob.glob(os.path.join(c, "memory", "metrics", "*.log"))
        paths += glob.glob(os.path.join(c, "metrics", "*.jsonl"))
        paths += glob.glob(os.path.join(c, "projects", "*", "memory", "spawns.jsonl"))
    for pat in (os.path.join(h, "projects", "*", "memory", "spawns.jsonl"), os.path.join(h, "projects", "*", "*", "memory", "spawns.jsonl")):
        paths += glob.glob(pat)
    return sorted(set(os.path.normpath(p) for p in paths if os.path.isfile(p)))


def _stat(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        core = data[:data.rfind(b"\n") + 1]  # whole lines only: a writer may be mid-append at snapshot time
        return {"size": len(core), "sha": hashlib.sha256(core).hexdigest(), "full": len(data), "mtime_ns": os.stat(path).st_mtime_ns}
    except OSError:
        return None


def snapshot_all(home=None):
    return {p: _stat(p) for p in watched(home)}


_BASELINE = None


def baseline():
    """The snapshot taken the FIRST time this is called (the suite's test_00_isolation.py does it before any test runs)."""
    global _BASELINE
    if _BASELINE is None:
        _BASELINE = snapshot_all()
    return _BASELINE


def row_problems(line):
    """Why one appended JSONL row looks like a test fixture, or None."""
    try:
        d = json.loads(line)
    except ValueError:
        return "non-JSON line appended: %.80r" % line
    if not isinstance(d, dict):
        return None
    tuid = d.get("tool_use_id")
    if tuid and not str(tuid).startswith("toolu_"):
        return "test row appended (tool_use_id=%r)" % (tuid,)
    for k in PATH_FIELDS:
        v = d.get(k)
        if v and FAKE_PATH.search(json.dumps(v)):
            return "test row appended (%s=%.80s)" % (k, json.dumps(v))
    return None


def _complete_lines(data):
    text = data.decode("utf-8", "replace")
    lines = text.split("\n")
    return [l for l in lines[:-1] if l.strip()]  # the last segment has no newline yet: a writer mid-append


def violations(before, home=None):
    """Human-readable problems between `before` ({path: snapshot|None}) and now; [] = clean."""
    problems = []
    for path in sorted(set(before) | set(watched(home))):
        klass = classify(path)
        if klass == IGNORED:
            continue
        was, now = before.get(path), _stat(path)
        if now is None:
            if was:
                problems.append("%s: live log disappeared during the test run" % path)
            continue
        if klass == STATIC:
            if was is None:
                problems.append("%s: a test run CREATED a log nobody writes in a normal session" % path)
            elif (was["full"], was["sha"], was["mtime_ns"]) != (now["full"], now["sha"], now["mtime_ns"]):
                problems.append("%s: a log no live session writes changed during the test run (size %d -> %d)" % (path, was["full"], now["full"]))
            continue
        with open(path, "rb") as f:
            data = f.read()
        base = was["size"] if was else 0
        if was and hashlib.sha256(data[:base]).hexdigest() != was["sha"]:
            problems.append("%s: existing rows were rewritten or truncated during the test run" % path)
            continue
        if not path.endswith(".jsonl"):
            continue
        for line in _complete_lines(data[base:]):
            why = row_problems(line)
            if why:
                problems.append("%s: %s" % (path, why))
    return problems
