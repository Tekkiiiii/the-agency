#!/usr/bin/env bash
# track-edits.sh — PostToolUse hook for Edit and Write
# Appends edited file paths to a session buffer for batch checking at Stop.
set -euo pipefail

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

INPUT=$(cat)
BUFFER="$AGENCY_ROOT/.edit-buffer.txt"

FILE_PATH=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)

if [ -n "$FILE_PATH" ]; then
  echo "$FILE_PATH" >> "$BUFFER"
fi
