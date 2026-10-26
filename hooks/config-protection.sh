#!/usr/bin/env bash
# config-protection.sh — PreToolUse hook for Edit and Write
# Blocks modification of existing linter/formatter configs. Allows first-time creation.
# Returns {} (pass) or {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny",
# "permissionDecisionReason":"..."}}. A top-level permissionDecision/message is silently ignored.
set -euo pipefail

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

PROFILE=$(cat "$AGENCY_ROOT/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  echo '{}'
  exit 0
fi

INPUT=$(cat)

FILE_PATH=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)

if [ -z "$FILE_PATH" ]; then
  echo '{}'
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")

PROTECTED=false
case "$BASENAME" in
  .eslintrc|.eslintrc.*|eslint.config.*) PROTECTED=true ;;
  .prettierrc|.prettierrc.*|prettier.config.*) PROTECTED=true ;;
  biome.json|biome.jsonc) PROTECTED=true ;;
  .ruff.toml|ruff.toml) PROTECTED=true ;;
  .shellcheckrc) PROTECTED=true ;;
  .stylelintrc|.stylelintrc.*) PROTECTED=true ;;
  .markdownlint*) PROTECTED=true ;;
esac

if [ "$PROTECTED" = "false" ]; then
  echo '{}'
  exit 0
fi

# Emit a PreToolUse decision in the shape Claude Code honours. A top-level
# {"permissionDecision":..,"message":..} is silently ignored. json.dumps keeps quotes/newlines valid.
emit_decision() { # $1=deny|ask $2=reason
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":sys.argv[1],"permissionDecisionReason":sys.argv[2]}}))' "$1" "$2"
}

if [ -f "$FILE_PATH" ]; then
  emit_decision deny "[config-protection] $BASENAME already exists. Fix the source code to satisfy the linter, not the config to ignore the violation."
else
  echo '{}'
fi
