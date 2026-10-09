#!/usr/bin/env python3
"""ledger.py: JSONL writer for the spawn-ledger mod.

The mod (hooks/register.ts) is the event source; this file does the writes, so
the records stay byte-compatible with the shell hooks it replaces (hooks/spawn-logger.sh,
spawn-completion.sh, artifact-verify.sh). Field names, field order and value formats are theirs.

  ledger.py start     stdin {tool_use_id, subagent_type, description, prompt, model,
                             parent_spawn_id, parent_agent}  -> prints spawn_id
  ledger.py launched  stdin {tool_use_id, agent_id, resolved_model}
  ledger.py end       stdin: the classic SubagentStop hook input, verbatim
  ledger.py verify    stdin {text}  -> prints the ARTIFACT_MISSING warning, if any

Why Python and not the mod: $.fs has no append (read+write would race the other
writers of spawns.jsonl), and cost comes from the shipped hooks/lib/claude_pricing.py, the
rate table cost-tracker.sh shares. FAILURE ISOLATION: always exits 0.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
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


def resolve_log_file():
    """spawns.jsonl via medium-term.md longest-prefix match (resolve-project.sh)."""
    override = os.environ.get("SPAWN_LOG_FILE", "")
    if override:
        return override
    fallback = os.path.join(ROOT, "logs", "spawns.jsonl")
    medium_term = os.path.join(ROOT, "memory", "medium-term.md")
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    if not os.path.exists(medium_term):
        return fallback
    best_len, best_path = 0, ""
    try:
        with open(medium_term) as f:
            for line in f:
                m = re.match(r"^\|[^|]+\|\s*`([^`]+)`", line)
                if not m:
                    continue
                raw = m.group(1).replace("~", HOME).rstrip("/")
                root = (raw[:-7] if raw.endswith("/memory") else raw).rstrip("/")
                if root and cwd.startswith(root) and len(root) > best_len:
                    best_len, best_path = len(root), root
    except Exception:
        pass
    if best_path:
        return os.path.join(best_path, "memory", "spawns.jsonl")
    return fallback


def append(log_file, entry):
    d = os.path.dirname(log_file)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_lines(log_file):
    try:
        with open(log_file) as f:
            return f.readlines()
    except Exception:
        return []


def other_logs(primary):
    """Other spawns.jsonl files a spawn may have been logged to (log-file split: the SubagentStop hook
    resolves its log from the hook process cwd, which differs from the spawning session's cwd, so
    spawn_launched can sit in a project log while the end resolves the global one). Existing files only.
    With SPAWN_LOG_FILE set (tests) only SPAWN_LEDGER_EXTRA_LOGS (os.pathsep list) is searched."""
    cands = []
    if os.environ.get("SPAWN_LOG_FILE"):
        cands += [x for x in os.environ.get("SPAWN_LEDGER_EXTRA_LOGS", "").split(os.pathsep) if x]
    else:
        cands.append(os.path.join(ROOT, "logs", "spawns.jsonl"))
        try:
            with open(os.path.join(ROOT, "memory", "medium-term.md")) as f:
                for line in f:
                    m = re.match(r"^\|[^|]+\|\s*`([^`]+)`", line)
                    if m:
                        raw = m.group(1).replace("~", HOME).rstrip("/")
                        root = (raw[:-7] if raw.endswith("/memory") else raw).rstrip("/")
                        if root:
                            cands.append(os.path.join(root, "memory", "spawns.jsonl"))
        except Exception:
            pass
        import glob
        cands += sorted(glob.glob(os.path.join(ROOT, "projects", "*", "memory", "spawns.jsonl")))
    seen, out = {os.path.abspath(primary)}, []
    for c in cands:
        a = os.path.abspath(c)
        if a not in seen and os.path.isfile(a):
            seen.add(a)
            out.append(a)
    return out


def reconcile(log_file):
    try:
        subprocess.run(["bash", os.path.join(ROOT, "hooks", "lib", "reconcile-stale-spawns.sh"), log_file],
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
                with open(os.path.join(root, fn), errors="ignore") as af:
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
            with open(os.path.join(ROOT, ".hook-profile")) as pf:
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
        p = subprocess.Popen([sys.executable or "python3", script, "--shadow"],
                             stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
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
    log_file = resolve_log_file()
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
        "project": os.path.basename(os.path.dirname(os.path.dirname(log_file))),
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


def launched(d):
    log_file = resolve_log_file()
    reconcile(log_file)
    tool_use_id = d.get("tool_use_id", "")
    spawn_id, _ = find_start(read_lines(log_file), tool_use_id=tool_use_id)
    append(log_file, {
        "event": "spawn_launched",
        "spawn_id": spawn_id,
        "tool_use_id": tool_use_id,
        "agent_id": d.get("agent_id", ""),
        "resolved_model": d.get("resolved_model", ""),
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
        with open(path, "a") as f:
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
    log_file, lines, spawn_id, tool_use_id = locate_start(log_file, lines, agent_id)
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
    missing, found = [], []
    for p in paths:
        p = p.strip()
        ap = os.path.join(HOME, p[2:]) if p.startswith("~/") else p
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
    log_dir = os.path.join(ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "artifact-verify.jsonl"), "a") as f:
        f.write(json.dumps({"ts": ts, "event": "ARTIFACT_MISSING", "missing": missing,
                            "found": found, "agent_excerpt": text[:500]}) + "\n")


if __name__ == "__main__":
    try:
        cmd = sys.argv[1]
        payload = json.loads(sys.stdin.read() or "{}")
        {"start": start, "launched": launched, "end": end, "verify": verify}[cmd](payload)
    except Exception:
        pass
    sys.exit(0)
