#!/usr/bin/env bash
# spawn-logger.sh — PreToolUse/Agent hook (spawn event emitter)
# Appends one spawn_start JSONL line per agent spawn.
# Also injects [[CLAUDE_SPAWN_META: spawn_id=X parent_id=Y]] marker into spawn prompt
# so child agents can read their own lineage (env propagation is unreliable in CC hooks).
# FAILURE ISOLATION: errors NEVER block spawns. All failures return plain {}.
set +e

PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  printf '{}'
  exit 0
fi

INPUT=$(cat)

# All work happens in python3 — pass INPUT as argv to avoid stdin conflict
# Returns JSON: either {} (pass through) or {"toolInput": {...modified input...}} (prompt-marker injection)
RESULT=$(python3 -c '
import sys, json, hashlib, uuid, os, re
from datetime import datetime

def resolve_log_file(home):
    """Resolve spawns.jsonl path via medium-term.md longest-prefix match."""
    fallback = os.path.join(home, ".claude/logs/spawns.jsonl")
    medium_term = os.path.join(home, ".claude/memory/medium-term.md")
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    if not os.path.exists(medium_term):
        return fallback

    best_len = 0
    best_path = ""
    try:
        with open(medium_term) as f:
            for line in f:
                # Match table rows: | project | `path` | ...
                m = re.match(r"^\|[^|]+\|\s*`([^`]+)`", line)
                if not m:
                    continue
                raw = m.group(1).replace("~", home).rstrip("/")
                # Strip /memory suffix — medium-term stores memory paths
                project_root = raw[:-7] if raw.endswith("/memory") else raw
                project_root = project_root.rstrip("/")
                if project_root and cwd.startswith(project_root):
                    if len(project_root) > best_len:
                        best_len = len(project_root)
                        best_path = project_root
    except Exception:
        pass

    if best_path:
        log_dir = os.path.join(best_path, "memory")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "spawns.jsonl")
    return fallback

try:
    raw_input = sys.argv[1]
    home = os.path.expanduser("~")
    d = json.loads(raw_input)
    ti = d.get("tool_input", {})

    subagent_type = ti.get("subagent_type", "unknown")
    description = ti.get("description", "")
    model = ti.get("model", "unknown")
    prompt = ti.get("prompt", "")
    tool_use_id = d.get("tool_use_id", "")

    spawn_id = str(uuid.uuid4())
    prompt_hash = hashlib.sha256(prompt[:200].encode()).hexdigest()[:12]
    ts = datetime.now().astimezone().isoformat(timespec="seconds")

    parent_agent = os.environ.get("CLAUDE_AGENT_NAME", "root")

    # Extract parent_spawn_id from marker already in the outgoing prompt.
    # When an agent uses log-spawn-from-agent.sh (Bug 1 helper), it inserts its own
    # [[CLAUDE_SPAWN_META: spawn_id=PARENT_ID ...]] into the outgoing child prompt.
    # We read that here so the chain is preserved even without env propagation.
    parent_spawn_id = ""
    meta_in_prompt = re.search(
        r"\[\[CLAUDE_SPAWN_META:[^\]]*spawn_id=([^\s\]]+)",
        prompt
    )
    if meta_in_prompt:
        # The marker in the outgoing prompt was put there by the spawning agent.
        # Its spawn_id becomes our parent_spawn_id.
        parent_spawn_id = meta_in_prompt.group(1)

    # Fallback: env var (unreliable in CC sub-agents, but harmless to try)
    if not parent_spawn_id:
        parent_spawn_id = os.environ.get("CLAUDE_PARENT_SPAWN_ID", "")

    # Resolve project log file
    log_file = resolve_log_file(home)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    project_name = os.path.basename(os.path.dirname(os.path.dirname(log_file)))

    # Write spawn_start entry
    entry = {
        "event": "spawn_start",
        "spawn_id": spawn_id,
        "tool_use_id": tool_use_id,
        "parent_spawn_id": parent_spawn_id,
        "parent_agent": parent_agent,
        "child_agent": subagent_type,
        "subagent_type": subagent_type,
        "description": description,
        "prompt_hash": prompt_hash,
        "prompt_excerpt": prompt[:200],
        "model": model,
        "ts": ts,
        "project": project_name
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Inject spawn meta marker into prompt for child lineage tracking.
    # Strip any existing [[CLAUDE_SPAWN_META: ...]] markers first (avoid stacking
    # across generations when the agent forward-injected one from its own prompt).
    clean_prompt = re.sub(
        r"\n?\[\[CLAUDE_SPAWN_META:[^\n]*\]\]", "", prompt
    ).rstrip()
    marker = f"\n[[CLAUDE_SPAWN_META: spawn_id={spawn_id} parent_id={parent_spawn_id}]]"
    modified_prompt = clean_prompt + marker

    # Return modified toolInput so CC injects our marker into the spawned agent
    modified_ti = dict(ti)
    modified_ti["prompt"] = modified_prompt
    print(json.dumps({"toolInput": modified_ti}))

except Exception:
    # On any error: pass through without modification
    print("{}")
' "$INPUT" 2>/dev/null)

# If python3 failed or returned empty, pass through
if [ -z "$RESULT" ]; then
  printf '{}'
  exit 0
fi

printf '%s' "$RESULT"
exit 0
