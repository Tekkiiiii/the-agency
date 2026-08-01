#!/usr/bin/env bash
# session-end.sh — Stop hook
# Marks session as cleanly ended. Idempotent (safe to call from both Stop and SessionEnd).
set -euo pipefail

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

STATE_FILE="$AGENCY_ROOT/session-state.json"
STATE_DIR=$(dirname "$STATE_FILE")
STATE_BASE=$(basename "$STATE_FILE")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Same idiom as hooks/emit-metric.sh (Wave 13, 3383ea9): cd into STATE_FILE's
# directory and hand python a bare filename, never the MSYS-style absolute
# path a Windows box's native python3 cannot open.
( cd "$STATE_DIR" 2>/dev/null || exit 0
  python3 -c "
import json
sf = '$STATE_BASE'
ts = '$TIMESTAMP'
try:
    with open(sf) as f:
        state = json.load(f)
except:
    state = {}
state['last_stop'] = ts
state['was_clean'] = True
with open(sf, 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true
)
