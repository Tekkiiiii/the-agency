#!/usr/bin/env bash
# log-spawn-from-agent.sh — called by PD/Coord/Mini-Coord BEFORE each Agent({...}) call.
# Writes a spawn_start JSONL entry and outputs a fresh spawn_id to stdout.
#
# Usage:
#   spawn_id=$(bash ~/.claude/hooks/lib/log-spawn-from-agent.sh \
#     --parent-agent "PD-myproject" \
#     --child-subagent-type "coord" \
#     --description "L3 task: auth" \
#     --prompt-excerpt "You are Coord-auth-Gatekeeper...")
#
# FAILURE ISOLATION: on any error, outputs a UUID and exits 0 (spawn is never blocked).
set +e

# Parse arguments
PARENT_AGENT="unknown"
CHILD_TYPE="unknown"
DESCRIPTION=""
PROMPT_EXCERPT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --parent-agent)
      PARENT_AGENT="$2"
      shift 2
      ;;
    --child-subagent-type)
      CHILD_TYPE="$2"
      shift 2
      ;;
    --description)
      DESCRIPTION="$2"
      shift 2
      ;;
    --prompt-excerpt)
      PROMPT_EXCERPT="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

SPAWN_ID=$(python3 -c "
import sys, json, os, re, uuid, hashlib
from datetime import datetime

def resolve_log_file(home):
    fallback = os.path.join(home, '.claude/logs/spawns.jsonl')
    medium_term = os.path.join(home, '.claude/memory/medium-term.md')
    cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
    if not os.path.exists(medium_term):
        return fallback
    best_len = 0
    best_path = ''
    try:
        with open(medium_term) as f:
            for line in f:
                m = re.match(r'^\|[^|]+\|\s*\`([^\`]+)\`', line)
                if not m:
                    continue
                raw = m.group(1).replace('~', home).rstrip('/')
                project_root = raw[:-7] if raw.endswith('/memory') else raw
                project_root = project_root.rstrip('/')
                if project_root and cwd.startswith(project_root):
                    if len(project_root) > best_len:
                        best_len = len(project_root)
                        best_path = project_root
    except Exception:
        pass
    if best_path:
        log_dir = os.path.join(best_path, 'memory')
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, 'spawns.jsonl')
    return fallback

try:
    home = os.path.expanduser('~')
    parent_agent = sys.argv[1] if len(sys.argv) > 1 else 'unknown'
    child_type = sys.argv[2] if len(sys.argv) > 2 else 'unknown'
    description = sys.argv[3] if len(sys.argv) > 3 else ''
    prompt_excerpt = sys.argv[4] if len(sys.argv) > 4 else ''

    spawn_id = str(uuid.uuid4())
    ts = datetime.now().astimezone().isoformat(timespec='seconds')
    prompt_hash = hashlib.sha256(prompt_excerpt[:200].encode()).hexdigest()[:12]

    # Resolve log file and project
    log_file = resolve_log_file(home)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    project_name = os.path.basename(os.path.dirname(os.path.dirname(log_file)))

    entry = {
        'event': 'spawn_start',
        'spawn_id': spawn_id,
        'tool_use_id': '',
        'parent_spawn_id': os.environ.get('CLAUDE_PARENT_SPAWN_ID', ''),
        'parent_agent': parent_agent,
        'child_agent': child_type,
        'subagent_type': child_type,
        'description': description,
        'prompt_hash': prompt_hash,
        'prompt_excerpt': prompt_excerpt[:200],
        'model': 'unknown',
        'ts': ts,
        'project': project_name,
        'source': 'agent-instrumented'
    }
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')

    # Print spawn_id to stdout for caller to capture
    print(spawn_id, end='')
except Exception:
    # Failure: output a valid UUID so caller can still use it
    import uuid as _uuid
    print(str(_uuid.uuid4()), end='')
" "$PARENT_AGENT" "$CHILD_TYPE" "$DESCRIPTION" "$PROMPT_EXCERPT" 2>/dev/null)

# If python3 failed completely, generate a UUID via bash
if [ -z "$SPAWN_ID" ]; then
  SPAWN_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))" 2>/dev/null || echo "00000000-0000-0000-0000-000000000000")
fi

# Output spawn_id to stdout — caller captures this
printf '%s' "$SPAWN_ID"
exit 0
