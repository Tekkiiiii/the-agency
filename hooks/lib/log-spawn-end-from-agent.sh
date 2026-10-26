#!/usr/bin/env bash
# log-spawn-end-from-agent.sh — called by PD/Coord/Mini-Coord AFTER each Agent({...}) returns.
# Writes a spawn_end JSONL entry for the given spawn_id.
#
# Usage:
#   bash {agency-root}/hooks/lib/log-spawn-end-from-agent.sh \
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

def resolve_log_file(home, root, lib_arg):
    # Testability override: honor a pre-exported SPAWN_LOG_FILE (points at a
    # /tmp copy in tests). Otherwise hooks/lib/spawn_project, the ONE resolver
    # (path-boundary prefix match, Windows drive rows, only a leading ~ expands;
    # it resolves the agency root itself). lib_arg = this script's directory.
    override = os.environ.get('SPAWN_LOG_FILE', '')
    if override:
        return override

    try:
        for lib in (lib_arg, os.path.join(root, 'hooks', 'lib')):
            if lib and os.path.isfile(os.path.join(lib, 'spawn_project.py')):
                sys.path.insert(0, lib)
                import spawn_project
                return spawn_project.resolve_log_file(home=home)
    except Exception:
        pass
    return os.path.join(root, 'logs/spawns.jsonl')

try:
    home = os.path.expanduser('~')
    spawn_id = sys.argv[1] if len(sys.argv) > 1 else ''
    outcome = sys.argv[2] if len(sys.argv) > 2 else 'UNKNOWN'
    summary = sys.argv[3] if len(sys.argv) > 3 else ''

    if not spawn_id:
        sys.exit(0)

    root = agency_root(home)
    log_file = resolve_log_file(home, root, sys.argv[4] if len(sys.argv) > 4 else '')
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
" "$SPAWN_ID" "$OUTCOME" "$SUMMARY" "$(cd "$(dirname "$0")" && pwd)" 2>/dev/null || true

exit 0
