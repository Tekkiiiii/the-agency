#!/usr/bin/env python3
"""ledger.py: JSONL writer for the spawn-ledger mod.

The mod (hooks/register.ts) is the event source; this file does the writes, so
the records stay byte-compatible with the shell hooks it replaces (hooks/spawn-logger.sh,
spawn-completion.sh, artifact-verify.sh). Field names, field order and value formats are theirs.

  ledger.py start     stdin {tool_use_id, subagent_type, description, prompt, model,
                             parent_spawn_id, parent_agent}  -> prints spawn_id
  ledger.py launched  stdin {tool_use_id, agent_id, resolved_model}
  ledger.py effort_applied
                      stdin {tool_use_id, agent_id, seen, applied, category}: the first time the turn.step relay applied the
                      effort policy to a subagent (seen = effort its request carried or null, applied = what was sent)
  ledger.py end       stdin: the classic SubagentStop hook input, verbatim
  ledger.py verify    stdin {text}  -> prints the ARTIFACT_MISSING warning, if any

WHERE THE ROWS GO: a spawn's rows land in {project root}/memory/spawns.jsonl (hooks/lib/spawn_project.py), e.g.
~/projects/my-app/memory/spawns.jsonl, where the project root comes from the Active Projects table in
{agency-root}/memory/medium-term.md. {agency-root}/logs/spawns.jsonl holds ONLY spawns with no project hint, so
looking there alone makes a healthy ledger look empty. Read them all: hooks/lib/spawn_project.all_logs.

OUTCOME / CONTINUATION (spawn_end; pinned by tests/test_outcome_unknown.py): `outcome` comes from detect_outcome(), a plain
substring scan of the agent's final message (SubagentHandback text, else last_assistant_message, else last text block):
KILLED > BLOCKED > ESCALATE > DONE/COMPLETE, else UNKNOWN. UNKNOWN therefore means "the final message carries no such
English token" (a terse acknowledgement, a Vietnamese-only report, a report whose token sits past the 300-char summary_excerpt),
or the spawn was a silent no-op (<5s, 0 work tools: silent_noop true). It is NOT a parse failure: the scan ignores CRLF and
works on any text that arrived as UTF-8 (only the em-dash forms "— BLOCKED"/"— ESCALATE" need real UTF-8; see
tests/test_utf8_roundtrip.py). `continuation: true` = this agent_id already had a spawn_end (resumed via SendMessage): the
transcript is cumulative (do not double-sum tokens) and the outcome is judged on THIS turn's last message only, so resumed
ends skew UNKNOWN. A Mac ledger (2026-10-15, source=subagent-stop) showed UNKNOWN on about a third of ends, continuations included.
ABANDONED rows come from the reconciliation sweep, never from here. Field list: skills/spawn-log/SKILL.md.

Why Python and not the mod: $.fs has no append (read+write would race the other
writers of spawns.jsonl), and cost comes from the shipped hooks/lib/claude_pricing.py, the
rate table cost-tracker.sh shares. FAILURE ISOLATION: always exits 0.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone

HOME = os.path.expanduser("~")


# Python twin of hooks/lib/resolve-root.sh, copied verbatim (enforced by
# .github/scripts/check-hardcoded-root.sh). resolve-root.sh explains the precedence
# and why the nt rewrite exists.
def agency_root(home):
    # MSYS-aware Python twin of hooks/lib/resolve-root.sh. That file documents
    # the precedence, why the /c/... rewrite is nt-only, and why this is inlined
    # at every call site instead of imported.
    root = os.environ.get('AGENCY_HOME') or os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(home, '.claude')
    if os.name == 'nt':
        m = re.fullmatch(r'/(?:cygdrive/)?([A-Za-z])(/.*)?', root)
        if m:
            root = m.group(1).upper() + ':' + (m.group(2) or '/')
    return root


# HOME only expands "~" in project paths; everything agency-owned lives under ROOT.
ROOT = agency_root(HOME)
sys.path.insert(0, os.path.join(ROOT, "hooks", "lib"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "hooks", "lib"))
try:
    import spawn_project  # shared project -> spawns.jsonl resolution (also used by hooks/lib/model-pin.py)
except Exception:  # fail open: without it every spawn lands in the global log
    spawn_project = None
try:
    import find_bash  # the bash to exec: never the Windows WSL launcher (System32\\bash.exe)
except Exception:  # fail open: reconcile then runs only where the old shutil.which("bash") check passed, off Windows
    find_bash = None


def find_bash_cmd():
    """argv[0] for the stale-spawn sweep, or None to skip it. POSIX: the bare name "bash". Windows: Git for Windows'
    bash.exe by full path (hooks/lib/find_bash.py): a bare "bash" there is the WSL launcher, which exits 1 silently."""
    try:
        if find_bash is not None:
            return find_bash.find_bash()
    except Exception:
        return None
    return None if os.name == "nt" else ("bash" if shutil.which("bash") else None)


def resolve_log_file(d=None):
    """spawns.jsonl for a spawn: SPAWN_LOG_FILE, else the project from the payload hint (Project: line in the prompt,
    parent_agent / subagent_type {slug}-pd), else CLAUDE_PROJECT_DIR/cwd, else logs/spawns.jsonl.
    See hooks/lib/spawn_project.py. Without a payload (end, whose hook input carries no hint) it is cwd-only."""
    override = os.environ.get("SPAWN_LOG_FILE", "")
    if override:
        return override
    if spawn_project is not None:
        try:
            # home=HOME: ONE home for the whole process. spawn_project's own default is expanduser("~"), which on
            # Windows reads USERPROFILE, not HOME: a test (or any caller) that moved ledger.HOME then resolved the
            # real home. The agency root itself still follows AGENCY_HOME -> CLAUDE_CONFIG_DIR -> <home>/.claude
            # inside spawn_project. hooks/lib/model-pin.py already passes home=HOME.
            return spawn_project.resolve_log_file(d if isinstance(d, dict) else None, home=HOME)
        except Exception:
            pass
    return os.path.join(ROOT, "logs", "spawns.jsonl")


def project_label(log_file):
    """The row's "project": the project dir of {root}/memory/spawns.jsonl. The global log ({agency-root}/logs/spawns.jsonl, a spawn
    that resolved to no project) is "global", not ".claude": the basename rule made it look like a project of its own."""
    try:
        glob_log = spawn_project.global_log(HOME) if spawn_project is not None else os.path.join(ROOT, "logs", "spawns.jsonl")
        if os.path.abspath(log_file) == os.path.abspath(glob_log):
            return "global"
    except Exception:
        pass
    return os.path.basename(os.path.dirname(os.path.dirname(log_file)))


def under_test():
    """True inside a test run: unittest/pytest imported in-process (the production hook runs `python3 ledger.py` and
    imports neither), or SPAWN_LEDGER_TEST=1 for subprocess-driven tests."""
    return os.environ.get("SPAWN_LEDGER_TEST") == "1" or "unittest" in sys.modules or "pytest" in sys.modules


def refuses_real_ledger(log_file):
    """A test run must never write a REAL ledger (global logs/spawns.jsonl or any project memory/spawns.jsonl): 2026-10-12
    an un-isolated test wrote tu-1/tu-2 rows there and the reconcile sweep later closed them as today's rows. A real
    ledger = a file named spawns.jsonl outside the system temp dir. Isolated tests (SPAWN_LOG_FILE in a tmp dir, a tmp HOME)
    are unaffected. Backstop only: scripts/tests + mods tests carry test_zz_real_ledger_guard.py, which catches any writer."""
    if not under_test() or os.path.basename(log_file) != "spawns.jsonl":
        return False
    tmp = os.path.realpath(tempfile.gettempdir())
    real = os.path.realpath(log_file)
    return not (real == tmp or real.startswith(tmp + os.sep))


def append(log_file, entry):
    if refuses_real_ledger(log_file):
        print("ledger.py: refusing to write real ledger %s from a test run (set SPAWN_LOG_FILE to a temp file)" % log_file,
              file=sys.stderr)
        return
    d = os.path.dirname(log_file)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_lines(log_file):
    try:
        with open(log_file, encoding="utf-8") as f:
            return f.readlines()
    except Exception:
        return []


def other_logs(primary):
    """Other spawns.jsonl files a spawn may have been logged to (log-file split: the SubagentStop hook
    resolves its log from the hook process cwd, which differs from the spawning session's cwd, so
    spawn_launched can sit in a project log while the end resolves the global one). Existing files only.
    With SPAWN_LOG_FILE set (tests) only SPAWN_LEDGER_EXTRA_LOGS (os.pathsep list) is searched.
    The list is built by hooks/lib/spawn_project.py all_logs (also used by model-pin.py's cap)."""
    if spawn_project is None:
        return []
    try:
        return spawn_project.all_logs(primary, home=HOME)
    except Exception:
        return []


def reconcile(log_file):
    # ponytail: win32 without Git for Windows' bash: stale-spawn reconcile skipped
    bash = find_bash_cmd()
    if not bash:
        return
    try:
        subprocess.run([bash, os.path.join(ROOT, "hooks", "lib", "reconcile-stale-spawns.sh"), log_file],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        pass


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---- start (was spawn-logger.sh) ------------------------------------------

def agent_def_model(subagent_type):
    try:
        for root, _dirs, files in os.walk(os.path.join(ROOT, "agents")):
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                with open(os.path.join(root, fn), encoding="utf-8", errors="ignore") as af:
                    head = af.read(2000)
                if not head.startswith("---"):
                    continue
                fm = head.split("---", 2)[1] if head.count("---") >= 2 else ""
                nm = re.search(r"^name:\s*[\"\x27]?(.+?)[\"\x27]?\s*$", fm, re.M)
                if nm and nm.group(1).strip() == subagent_type:
                    mm = re.search(r"^model:\s*[\"\x27]?([^\s\"\x27]+)", fm, re.M)
                    return (mm.group(1), "agent_def") if mm else ("inherit", "inherit")
    except Exception:
        pass
    return "", ""


def fire_shadow(spawn_id, d, subagent_type, prompt):
    """Jev SHADOW routing: detached `skill-route.py --shadow`, fire-and-forget. Never raises.

    skill-route.py decides what to log. Skipped unless
    AGENCY_SKILL_ROUTER=1, and when SKILL_ROUTE_CHILD=1, the kill switch state/skill-route-shadow.off exists, the hook
    profile is minimal, or the script is missing."""
    try:
        if os.environ.get("AGENCY_SKILL_ROUTER") != "1":  # the router is off by default
            return
        if os.environ.get("SKILL_ROUTE_CHILD") == "1":
            return
        state_dir = os.environ.get("SKILL_ROUTE_STATE_DIR") or os.path.join(ROOT, "state", "skill-route")
        if os.path.exists(os.path.join(state_dir, "skill-route-shadow.off")):
            return
        try:
            with open(os.path.join(ROOT, ".hook-profile"), encoding="utf-8") as pf:
                if pf.read().strip() == "minimal":
                    return
        except Exception:
            pass
        script = os.path.join(ROOT, "scripts", "skill-route.py")
        if not os.path.exists(script):
            return
        payload = json.dumps({
            "spawn_id": spawn_id,
            "subagent_type": subagent_type,
            "parent_agent": d.get("parent_agent", "") or "root",
            "description": d.get("description", "") or "",
            "prompt": prompt[:8000],
        })
        # Detach so the child outlives this process: POSIX new session, Windows detached process group.
        detach = ({"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0x8)
                   | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)}
                  if os.name == "nt" else {"start_new_session": True})
        p = subprocess.Popen([sys.executable or "python3", script, "--shadow"],
                             stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, **detach)
        p.stdin.write(payload.encode())
        p.stdin.close()
    except Exception:
        pass


def start(d):
    subagent_type = d.get("subagent_type") or "unknown"
    prompt = d.get("prompt", "") or ""
    model = d.get("model", "") or ""
    model_source = "explicit" if model else ""
    if not model:
        model, model_source = agent_def_model(subagent_type)
    if not model:
        model, model_source = "inherit", "inherit"
    skills = []
    for sl in re.findall(r"^\s*SKILLS:\s*(.+)$", prompt, re.M):
        skills += [x.strip(" `/") for x in re.split(r"[,\s]+", sl) if x.strip(" `/")]
    skills += re.findall(r"Skill\(\{\s*skill:\s*[\"\x27]([\w:.-]+)", prompt)
    log_file = resolve_log_file(d)
    spawn_id = str(uuid.uuid4())
    append(log_file, {
        "event": "spawn_start",
        "spawn_id": spawn_id,
        "tool_use_id": d.get("tool_use_id", ""),
        "parent_spawn_id": d.get("parent_spawn_id", "") or "",
        "parent_agent": d.get("parent_agent", "") or "root",
        "child_agent": subagent_type,
        "subagent_type": subagent_type,
        "description": d.get("description", "") or "",
        "prompt_hash": hashlib.sha256(prompt[:200].encode()).hexdigest()[:12],
        "prompt_excerpt": prompt[:200],
        "model": model,
        "model_source": model_source,
        "skills": sorted(set(skills)),
        "ts": now_iso(),
        "project": project_label(log_file),
    })
    fire_shadow(spawn_id, d, subagent_type, prompt)
    print(spawn_id)


# ---- launched / end (was spawn-completion.sh) -----------------------------

def find_start(lines, tool_use_id="", agent_id=""):
    """(spawn_id, tool_use_id); agent_id path: spawn_launched -> tool_use_id -> spawn_start."""
    if agent_id and not tool_use_id:
        for line in reversed(lines):
            if agent_id not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event") == "spawn_launched" and e.get("agent_id") == agent_id:
                tool_use_id = e.get("tool_use_id", "")
                if e.get("spawn_id"):
                    return e["spawn_id"], tool_use_id
                break
    if tool_use_id:
        for line in reversed(lines):
            if tool_use_id not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event") == "spawn_start" and e.get("tool_use_id") == tool_use_id:
                return e.get("spawn_id", ""), tool_use_id
    return "", tool_use_id


def locate_start(log_file, lines, agent_id):
    """(log_file, lines, spawn_id, tool_use_id) for a stopping agent. Looks in the resolved log first,
    then in the other known logs (see other_logs); the spawn_end is later appended next to the start."""
    spawn_id, tool_use_id = find_start(lines, agent_id=agent_id)
    if spawn_id or not agent_id:
        return log_file, lines, spawn_id, tool_use_id
    for other in other_logs(log_file):
        olines = read_lines(other)
        if not any(agent_id in l for l in olines):
            continue
        spawn_id, tool_use_id = find_start(olines, agent_id=agent_id)
        if spawn_id:
            return other, olines, spawn_id, tool_use_id
    return log_file, lines, "", tool_use_id


def find_row(lines, event, spawn_id, key="spawn_id"):
    """Last row of `event` whose spawn_id matches (substring pre-filter keeps it cheap)."""
    if not spawn_id:
        return {}
    for line in reversed(lines):
        if spawn_id not in line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event") == event and e.get(key) == spawn_id:
            return e
    return {}


def strip_ctx_suffix(model):
    """'claude-opus-5-5[1m]' -> 'claude-opus-5-5' (same id the transcript's `models` list carries)."""
    return re.sub(r"\[[^\]]*\]$", "", model or "")


def pick_model(by_model, launched_row, start_row_):
    """(model, source): dominant transcript model (highest cost; most output on a tie), else the
    harness-resolved model of the launch, else the start row's model unless it is a placeholder."""
    if by_model:
        top = max(by_model.items(), key=lambda kv: (kv[1].get("cost_usd", 0) or 0, kv[1].get("output", 0) or 0))
        return top[0], "transcript"
    resolved = strip_ctx_suffix(launched_row.get("resolved_model", ""))
    if resolved:
        return resolved, "launched"
    sm = (start_row_.get("model") or "").strip()
    if sm and sm not in ("inherit", "unknown"):
        return sm, "start"
    return "unknown", "unavailable"


def detect_outcome(content):
    if not content:
        return "UNKNOWN"
    text = str(content).upper()
    if "KILLED" in text:
        return "KILLED"
    if "BLOCKED:" in text or "STATUS: BLOCKED" in text or ": BLOCKED" in text or "— BLOCKED" in text:
        return "BLOCKED"
    if "ESCALATE:" in text or "STATUS: ESCALATE" in text or ": ESCALATE" in text or "— ESCALATE" in text:
        return "ESCALATE"
    if "DONE" in text or "COMPLETE" in text or "SAVE-STATE DONE" in text:
        return "DONE"
    return "UNKNOWN"


def skill_mismatch(content):
    m = re.search(r"^.*SKILL_MISMATCH.*$", content or "", re.M)
    return (True, m.group(0).strip()[:200]) if m else (False, "")


def iso_ms(a, b):
    try:
        fa = datetime.fromisoformat(a.replace("Z", "+00:00"))
        fb = datetime.fromisoformat(b.replace("Z", "+00:00"))
        return int((fb - fa).total_seconds() * 1000)
    except Exception:
        return 0


def locate_by_tool_use_id(tool_use_id):
    """(log_file, spawn_id) of the spawn_start row for a tool_use_id: the resolved log first, then every other known log.
    Not found anywhere -> (resolved log, ""). Shared by launched and effort_applied (payloads with no prompt)."""
    log_file = resolve_log_file()
    spawn_id, _ = find_start(read_lines(log_file), tool_use_id=tool_use_id)
    if not spawn_id and tool_use_id:
        for other in other_logs(log_file):
            olines = read_lines(other)
            if not any(tool_use_id in l for l in olines):
                continue
            spawn_id, _ = find_start(olines, tool_use_id=tool_use_id)
            if spawn_id:
                return other, spawn_id
    return log_file, spawn_id


def launched(d):
    """spawn_launched row, appended NEXT TO the spawn_start row it belongs to. The payload carries only the
    tool_use_id (no prompt), so the start row is looked up in the resolved log, then in every other known log;
    not found anywhere -> the resolved log (spawn_id empty), as before."""
    tool_use_id = d.get("tool_use_id", "")
    log_file, spawn_id = locate_by_tool_use_id(tool_use_id)
    reconcile(log_file)
    append(log_file, {
        "event": "spawn_launched",
        "spawn_id": spawn_id,
        "tool_use_id": tool_use_id,
        "agent_id": d.get("agent_id", ""),
        "resolved_model": d.get("resolved_model", ""),
        "ts": now_iso(),
    })


def effort_applied(d):
    """effort_applied row: the turn.step relay (hooks/register.ts) sent a subagent's first request with the effort
    hooks/lib/model-pin.py decided at spawn. seen = the effort the request carried (null: none), applied = what was
    sent, category = the policy category, changed = seen != applied. Appended next to the spawn_start row, like launched;
    no reconcile sweep (nothing here closes a spawn). The payload keys are the relay's; anything missing is stored empty."""
    tool_use_id = d.get("tool_use_id", "")
    log_file, spawn_id = locate_by_tool_use_id(tool_use_id)
    seen, applied = d.get("seen"), d.get("applied")
    append(log_file, {
        "event": "effort_applied",
        "spawn_id": spawn_id,
        "tool_use_id": tool_use_id,
        "agent_id": d.get("agent_id", ""),
        "seen": seen,
        "applied": applied,
        "category": d.get("category", ""),
        "changed": seen != applied,
        "ts": now_iso(),
    })


# ---- silent no-op guard ---------------------------------------------------
# An agent that stops in <5s with 0 tool uses did no work (same shape as a fabricated DONE).
# Both numbers must be known: no usage / no timestamps = no flag.
SILENT_NOOP_MAX_MS = 5000
SILENT_NOOP_MAX_TOOLS = 0
SILENT_NOOP_WARNING = (
    f"[spawn-ledger] silent no-op spawn: <{SILENT_NOOP_MAX_MS // 1000}s/{SILENT_NOOP_MAX_TOOLS} tools, treat as unverified"
)


def silent_noop(u, duration_ms):
    """True when usage and both timestamps are known and the spawn did no work.
    SubagentHandback is itself a tool_use in the transcript (the handback), so it is not work."""
    if not u or not u.get("first_ts") or not u.get("last_ts"):
        return False
    work_tools = (u.get("tool_uses") or 0) - (1 if u.get("handback_text") else 0)
    return duration_ms < SILENT_NOOP_MAX_MS and work_tools <= SILENT_NOOP_MAX_TOOLS


def emit_metric(event, **fields):
    """Append one event to the metrics stream (same line format as memory/metrics/emit-metric.sh,
    whose path SPAWN_LEDGER_METRICS_FILE overrides for tests). Never raises."""
    try:
        path = os.environ.get("SPAWN_LEDGER_METRICS_FILE") or os.path.join(ROOT, "memory", "metrics", "events.jsonl")
        rec = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "event": event}
        rec.update(fields)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def end(d):
    log_file = resolve_log_file()
    reconcile(log_file)
    lines = read_lines(log_file)
    agent_id = d.get("agent_id", "")
    tpath = d.get("agent_transcript_path", "")
    # The start may live in another log (split by cwd): write the end next to it so they join per file.
    resolved = log_file
    log_file, lines, spawn_id, tool_use_id = locate_start(log_file, lines, agent_id)
    if log_file != resolved:
        reconcile(log_file)  # the sweep is per log: keep it running for the log actually written
    # Harness-internal subagents (summarizers, classifiers) also stop: no agent_type,
    # no Agent-tool launch. Not spawns; skip so spawn_end stays 1:1 with spawns.
    if not spawn_id and not d.get("agent_type"):
        return
    from claude_pricing import usage_from_transcript
    u = usage_from_transcript(tpath) if tpath and os.path.exists(tpath) else None
    last = ((u or {}).get("handback_text") or d.get("last_assistant_message")
            or (u or {}).get("last_text") or "")
    mism, mline = skill_mismatch(last)
    t = u["totals"] if u else {}
    keys = ("input", "output", "cache_write_5m", "cache_write_1h", "cache_read")
    duration_ms = iso_ms(u["first_ts"], u["last_ts"]) if u and u["first_ts"] and u["last_ts"] else 0
    noop = silent_noop(u, duration_ms)
    prior_end = any(('"spawn_end"' in l and agent_id and agent_id in l) for l in lines)
    start_row_ = find_row(lines, "spawn_start", spawn_id)
    launched_row = find_row(lines, "spawn_launched", spawn_id)
    by_model = (u or {}).get("by_model", {})
    model, model_source = pick_model(by_model, launched_row, start_row_)
    entry = {
        "event": "spawn_end",
        "spawn_id": spawn_id,
        "tool_use_id": tool_use_id,
        "agent_id": agent_id,
        "agent_type": d.get("agent_type", "") or start_row_.get("subagent_type", ""),
        "outcome": "UNKNOWN" if noop else detect_outcome(last),
        "duration_ms": duration_ms,
        "tokens": sum(t.get(k, 0) for k in keys),
        "tokens_breakdown": {k: t.get(k, 0) for k in keys},
        "cost_usd": t.get("cost_usd", 0.0),
        "cost_source": "transcript" if u else "unavailable",
        "final_context_tokens": (u or {}).get("final_context_tokens", 0),
        "output_estimated_messages": (u or {}).get("output_estimated_messages", 0),
        "models": sorted(by_model.keys()),
        "model": model,
        "model_source": model_source,
        "tool_uses": (u or {}).get("tool_uses", 0),
        "skill_mismatch": mism,
        "summary_excerpt": (last or "")[:300],
        "source": "subagent-stop",
        "ts": now_iso(),
    }
    if mism:
        entry["skill_mismatch_line"] = mline
    if prior_end:
        entry["continuation"] = True  # resumed via SendMessage; cumulative transcript
    if noop:
        entry["silent_noop"] = True
    append(log_file, entry)
    if noop:
        emit_metric("silent_noop_spawn", agent_type=entry["agent_type"], duration_ms=duration_ms,
                    tool_uses=entry["tool_uses"], spawn_id=spawn_id)
        print(SILENT_NOOP_WARNING)  # register.ts relays stdout to the parent


# ---- verify (was artifact-verify.sh) --------------------------------------

SIGNALS = ["BUILD COMPLETE", "DONE", "COMPLETE", "SUCCESS", "FINISHED", "FILE READY",
           "RENDER COMPLETE", "OUTPUT READY", "SHIPPED", "FULLY COMPLETE", "TASK COMPLETE",
           "ALL DONE", "SAVE-STATE DONE"]
EXTS = (r"(?:mp4|mp3|wav|aac|ogg|flac|pdf|html|htm|docx|xlsx|pptx|"
        r"png|jpg|jpeg|gif|webp|svg|zip|json|csv|wasm|exe|dmg))")


def verify(d):
    text = d.get("text", "") or ""
    if not any(s in text.upper() for s in SIGNALS):
        return
    paths = set(re.findall(r'(?:^|[\s`"\'])(/[^\s"\'<>(){}|,;]+\.' + EXTS + r'(?=[\s"\'<>(){}|,;]|$)',
                           text, re.IGNORECASE | re.MULTILINE))
    paths.update(re.findall(r'(~/[^\s"\'<>(){}|,;]+\.' + EXTS + r'(?=[\s"\'<>(){}|,;]|$)',
                            text, re.IGNORECASE | re.MULTILINE))
    if os.name == "nt":  # also C:\x\y.pdf, C:/x/y.pdf and ~\x.pdf; POSIX regexes and results stay as they were
        paths.update(re.findall(r'(?:^|[\s`"\'])([A-Za-z]:[\\/][^\s"\'<>(){}|,;]+\.' + EXTS + r'(?=[\s"\'<>(){}|,;]|$)',
                                text, re.IGNORECASE | re.MULTILINE))
        paths.update(re.findall(r'(~\\[^\s"\'<>(){}|,;]+\.' + EXTS + r'(?=[\s"\'<>(){}|,;]|$)',
                                text, re.IGNORECASE | re.MULTILINE))
    missing, found = [], []
    for p in paths:
        p = p.strip()
        ap = os.path.join(HOME, p[2:]) if p.startswith(("~/", "~\\")) else p
        (found if os.path.isfile(ap) else missing).append(ap)
    if not missing:
        return
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    out = [f"[artifact-verify] {ts} ARTIFACT_MISSING WARNING",
           "[artifact-verify] Agent claimed DONE/COMPLETE but these files do NOT exist on disk:"]
    out += [f"  MISSING: {p}" for p in missing] + [f"  OK:      {p}" for p in found]
    out += ["[artifact-verify] Do NOT relay this completion to the user.",
            "[artifact-verify] Verify the agent's work before marking done."]
    print("\n".join(out))
    # ARTIFACT_VERIFY_LOG (tests only; unset in production = the same path as always) redirects the log. The default
    # is ROOT, computed at import (AGENCY_HOME -> CLAUDE_CONFIG_DIR -> <home>/.claude): a test that patches HOME
    # after import does NOT move it, which is how test rows once leaked into the real log. Patch ledger.ROOT or set
    # the env var; the isolation bootstrap (hooks/lib/test_home.py) does both before import.
    log_path = os.environ.get("ARTIFACT_VERIFY_LOG") or os.path.join(ROOT, "logs", "artifact-verify.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "event": "ARTIFACT_MISSING", "missing": missing,
                            "found": found, "agent_excerpt": text[:500]}) + "\n")


def _utf8_stdio():
    """Node sends UTF-8 JSON (Vietnamese included); Windows' default stdio codec is the locale code page."""
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if hasattr(s, "reconfigure"):
                s.reconfigure(encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    _utf8_stdio()
    try:
        cmd = sys.argv[1]
        payload = json.loads(sys.stdin.read() or "{}")
        {"start": start, "launched": launched, "effort_applied": effort_applied, "end": end, "verify": verify}[cmd](payload)
    except Exception:
        pass
    sys.exit(0)
