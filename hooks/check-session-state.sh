#!/usr/bin/env bash
# check-session-state.sh — SessionStart hook
# Detects unclean prior exits (crash/Ctrl+C). Non-blocking.
set -euo pipefail

STATE_FILE="$HOME/.claude/session-state.json"

if [ ! -f "$STATE_FILE" ]; then
  python3 -c "
import json
with open('$STATE_FILE', 'w') as f:
    json.dump({'was_clean': True}, f)
" 2>/dev/null || true
  exit 0
fi

python3 -c "
import json
sf = '$STATE_FILE'
try:
    with open(sf) as f:
        state = json.load(f)
    if not state.get('was_clean', True):
        last = state.get('last_stop', 'unknown')
        print(f'NOTICE: Previous session may have ended uncleanly (last clean stop: {last}).')
        print('  Run /recall [slug] or /save-state [slug] to check project state.')
    if state.get('stall_detected'):
        tool = state.get('stall_tool', 'unknown')
        at = state.get('stall_at', 'unknown')
        print(f'WARNING: Stall was detected in previous session ({tool} at {at}).')
        print('  An agent was looping on the same call 5+ times. Check if the task completed.')
        state.pop('stall_detected', None)
        state.pop('stall_tool', None)
        state.pop('stall_at', None)
    state['was_clean'] = False
    with open(sf, 'w') as f:
        json.dump(state, f, indent=2)
except:
    pass
" 2>/dev/null || true
