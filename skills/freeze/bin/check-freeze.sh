#!/usr/bin/env bash
# check-freeze.sh — PreToolUse hook for /freeze skill
# Reads JSON from stdin, checks if file_path is within the freeze boundary.
# Returns {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny",
# "permissionDecisionReason":"..."}} to block, or {} to allow. (FORK (claude-council):
# the decision MUST be nested under hookSpecificOutput; Claude Code ignores a top-level one.)
set -euo pipefail

# FORK (claude-council): Claude Code only honors the decision nested under
# hookSpecificOutput; a top-level permissionDecision/message is silently ignored
# (the hook never blocks). Same output shape as upstream gstack; upstream builds it
# with gstack_hook_decision (careful/bin/hook-extract.sh), which this fork does not
# carry. Take upstream's version of this file on merge (FORK-NOTES D1).
# Reason text is JSON-escaped here so file paths / commands cannot break the JSON.
_hook_decision() {
  local _r="$2"
  _r=${_r//\\/\\\\}; _r=${_r//\"/\\\"}
  _r=${_r//$'\n'/\\n}; _r=${_r//$'\r'/\\r}; _r=${_r//$'\t'/\\t}
  _r=$(printf '%s' "$_r" | LC_ALL=C tr -d '\000-\010\013\014\016-\037')
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' "$1" "$_r"
}

# Read stdin
INPUT=$(cat)

# Locate the freeze directory state file
STATE_DIR="${CLAUDE_PLUGIN_DATA:-$HOME/.gstack}"
FREEZE_FILE="$STATE_DIR/freeze-dir.txt"

# If no freeze file exists, allow everything (not yet configured)
if [ ! -f "$FREEZE_FILE" ]; then
  echo '{}'
  exit 0
fi

FREEZE_DIR=$(tr -d '[:space:]' < "$FREEZE_FILE")

# If freeze dir is empty, allow
if [ -z "$FREEZE_DIR" ]; then
  echo '{}'
  exit 0
fi

# Extract file_path from tool_input JSON
# Try grep/sed first, fall back to Python for escaped quotes
FILE_PATH=$(printf '%s' "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//;s/"$//' || true)

# Python fallback if grep returned empty
if [ -z "$FILE_PATH" ]; then
  FILE_PATH=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)
fi

# If we couldn't extract a file path, allow (don't block on parse failure)
if [ -z "$FILE_PATH" ]; then
  echo '{}'
  exit 0
fi

# Resolve file_path to absolute if it isn't already
case "$FILE_PATH" in
  /*) ;; # already absolute
  *)
    FILE_PATH="$(pwd)/$FILE_PATH"
    ;;
esac

# Normalize: remove double slashes and trailing slash
FILE_PATH=$(printf '%s' "$FILE_PATH" | sed 's|/\+|/|g;s|/$||')

# Resolve symlinks and .. sequences (POSIX-portable, works on macOS)
_resolve_path() {
  local _dir _base
  _dir="$(dirname "$1")"
  _base="$(basename "$1")"
  _dir="$(cd "$_dir" 2>/dev/null && pwd -P || printf '%s' "$_dir")"
  printf '%s/%s' "$_dir" "$_base"
}
FILE_PATH=$(_resolve_path "$FILE_PATH")
FREEZE_DIR=$(_resolve_path "$FREEZE_DIR")

# Check: does the file path start with the freeze directory?
case "$FILE_PATH" in
  "${FREEZE_DIR}/"*|"${FREEZE_DIR}")
    # Inside freeze boundary — allow
    echo '{}'
    ;;
  *)
    # Outside freeze boundary — deny
    # Log hook fire event. Local append only, and only when ~/.gstack/analytics already
    # exists (never creates it).
    if [ -d ~/.gstack/analytics ]; then
      echo '{"event":"hook_fire","skill":"freeze","pattern":"boundary_deny","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","repo":"'$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "unknown")'"}' >> ~/.gstack/analytics/skill-usage.jsonl 2>/dev/null || true
    fi

    _hook_decision deny "[freeze] Blocked: $FILE_PATH is outside the freeze boundary ($FREEZE_DIR). Only edits within the frozen directory are allowed."
    ;;
esac
