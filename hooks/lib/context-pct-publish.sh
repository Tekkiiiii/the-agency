#!/usr/bin/env bash
# context-pct-publish.sh
# Reads context usage from Claude Code status line output and publishes it
# as an environment variable for agent self-monitoring (Self-Respawn Protocol).
#
# Called by: PostToolUse hook (any tool)
# Writes:    ~/.claude/state/context-pct.txt — current context percentage (integer 0-100)
#
# Agents read ~/.claude/state/context-pct.txt to monitor their own context budget.
# Thresholds:
#   70% — warn (log to scratch, complete current task, no new L3s)
#   80% — mandatory /save-state + respawn (max 3 respawns per project per 24h)

set -euo pipefail

STATE_DIR="$HOME/.claude/state"
PCT_FILE="$STATE_DIR/context-pct.txt"
RESPAWN_COUNTER_DIR="$STATE_DIR/respawn-counters"

mkdir -p "$STATE_DIR" "$RESPAWN_COUNTER_DIR"

# Read context percentage from CLAUDE_CONTEXT_PCT env (set by Claude Code harness)
# or fall back to parsing the CLAUDE_USAGE env var
PCT=""

if [ -n "${CLAUDE_CONTEXT_PCT:-}" ]; then
  PCT="$CLAUDE_CONTEXT_PCT"
elif [ -n "${CLAUDE_USAGE:-}" ]; then
  # Extract percentage from usage JSON: {"input_tokens":N,"context_window":M}
  INPUT=$(echo "$CLAUDE_USAGE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('input_tokens',0))" 2>/dev/null || echo "0")
  WINDOW=$(echo "$CLAUDE_USAGE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('context_window',200000))" 2>/dev/null || echo "200000")
  if [ "$WINDOW" -gt 0 ] 2>/dev/null; then
    PCT=$(python3 -c "print(int($INPUT * 100 / $WINDOW))" 2>/dev/null || echo "")
  fi
fi

# Write current percentage to state file
if [ -n "$PCT" ] && [ "$PCT" -ge 0 ] 2>/dev/null && [ "$PCT" -le 100 ] 2>/dev/null; then
  echo "$PCT" > "$PCT_FILE"
fi

# Emit threshold alerts to stderr (Claude Code picks these up as tool output metadata)
if [ -n "$PCT" ]; then
  if [ "$PCT" -ge 80 ] 2>/dev/null; then
    echo "CONTEXT_PCT_ALERT: ${PCT}% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now." >&2
  elif [ "$PCT" -ge 70 ] 2>/dev/null; then
    echo "CONTEXT_PCT_ALERT: ${PCT}% — WARNING THRESHOLD (70%). Complete current task. No new L3s." >&2
  fi
fi
