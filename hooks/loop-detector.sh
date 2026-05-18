#!/usr/bin/env bash
# loop-detector.sh — PostToolUse hook (all tools)
# Tracks recent tool calls. If 5 identical calls in a row, writes a stall marker.
# The stall marker is read by check-session-state.sh on next SessionStart.
# Also prints a warning to stderr visible to the running agent.
set -euo pipefail

PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  exit 0
fi

INPUT=$(cat)
TRACKER="$HOME/.claude/.tool-call-tracker.jsonl"

# Extract tool name and key input (file_path or command, truncated to 200 chars)
ENTRY=$(printf '%s' "$INPUT" | python3 -c "
import sys, json, hashlib
try:
    d = json.loads(sys.stdin.read())
    tool = d.get('tool_name', 'unknown')
    ti = d.get('tool_input', {})
    key = ti.get('file_path', '') or ti.get('command', '')[:200] or str(ti)[:200]
    sig = hashlib.sha256(f'{tool}:{key}'.encode()).hexdigest()[:16]
    print(json.dumps({'tool': tool, 'sig': sig}))
except:
    print('')
" 2>/dev/null || true)

if [ -z "$ENTRY" ] || [ "$ENTRY" = "" ]; then
  exit 0
fi

# Append to tracker (keep last 10 entries only)
echo "$ENTRY" >> "$TRACKER"
tail -10 "$TRACKER" > "$TRACKER.tmp" && mv "$TRACKER.tmp" "$TRACKER"

# Check for stall: 5 identical signatures in a row
STALL=$(python3 -c "
import json, sys
lines = open('$TRACKER').readlines()
if len(lines) < 5:
    sys.exit(0)
sigs = []
for line in lines:
    line = line.strip()
    if not line:
        continue
    try:
        sigs.append(json.loads(line).get('sig', ''))
    except:
        pass
if len(sigs) >= 5 and len(set(sigs[-5:])) == 1:
    print('STALL')
" 2>/dev/null || true)

if [ "$STALL" = "STALL" ]; then
  TOOL_NAME=$(python3 -c "import json; print(json.loads('$ENTRY').get('tool','unknown'))" 2>/dev/null || echo "unknown")
  echo "[loop-detector] STALL DETECTED: 5 identical $TOOL_NAME calls in a row." >&2
  echo "[loop-detector] You are likely in an infinite loop. Stop retrying and:" >&2
  echo "  1. Restate your objective in one sentence" >&2
  echo "  2. Verify the actual world state (read the file, check git status)" >&2
  echo "  3. Try a DIFFERENT approach, not the same command again" >&2
  echo "  4. If still blocked, /save-state and stop." >&2

  # Write stall marker for cross-session visibility
  python3 -c "
import json, datetime
state_file = '$HOME/.claude/session-state.json'
try:
    with open(state_file) as f:
        state = json.load(f)
except:
    state = {}
state['stall_detected'] = True
state['stall_tool'] = '$TOOL_NAME'
state['stall_at'] = datetime.datetime.now().isoformat()
with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true

  # Clear tracker to give one fresh chance
  rm -f "$TRACKER"
fi
