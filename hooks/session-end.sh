#!/usr/bin/env bash
# session-end.sh — Stop hook
# Marks session as cleanly ended. Idempotent (safe to call from both Stop and SessionEnd).
set -euo pipefail

STATE_FILE="$HOME/.claude/session-state.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 -c "
import json
sf = '$STATE_FILE'
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
