#!/usr/bin/env bash
# log-spawn-end-from-agent.sh — called by PD/Coord/Mini-Coord AFTER each Agent({...}) returns.
# Writes a spawn_end JSONL entry for the given spawn_id.
#
# Usage:
#   bash ~/.claude/hooks/lib/log-spawn-end-from-agent.sh \
#     --spawn-id "uuid-from-log-spawn-from-agent" \
#     --outcome "DONE" \
#     --summary "First 300 chars of agent result..."
#
# FAILURE ISOLATION: silent on all errors — never blocks the caller.
set +e

SPAWN_ID=""
OUTCOME="UNKNOWN"
SUMMARY=""

while [ $# -gt 0 ]; do
  case "$1" in
    --spawn-id)
      SPAWN_ID="$2"
      shift 2
      ;;
    --outcome)
      OUTCOME="$2"
      shift 2
      ;;
    --summary)
      SUMMARY="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [ -z "$SPAWN_ID" ]; then
  exit 0
fi

python3 -c "
import sys, json, os, re
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
    spawn_id = sys.argv[1] if len(sys.argv) > 1 else ''
    outcome = sys.argv[2] if len(sys.argv) > 2 else 'UNKNOWN'
    summary = sys.argv[3] if len(sys.argv) > 3 else ''

    if not spawn_id:
        sys.exit(0)

    log_file = resolve_log_file(home)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    ts = datetime.now().astimezone().isoformat(timespec='seconds')

    entry = {
        'event': 'spawn_end',
        'spawn_id': spawn_id,
        'tool_use_id': '',
        'outcome': outcome,
        'duration_ms': 0,
        'tokens': 0,
        'tool_uses': 0,
        'summary_excerpt': summary[:300],
        'ts': ts,
        'source': 'agent-instrumented'
    }
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
except Exception:
    pass
" "$SPAWN_ID" "$OUTCOME" "$SUMMARY" 2>/dev/null || true

exit 0
