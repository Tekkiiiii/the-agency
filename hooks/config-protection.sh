#!/usr/bin/env bash
# config-protection.sh — PreToolUse hook for Edit and Write
# Blocks modification of existing linter/formatter configs. Allows first-time creation.
set -euo pipefail

PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
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

if [ -f "$FILE_PATH" ]; then
  printf '{"permissionDecision":"deny","message":"[config-protection] %s already exists. Fix the source code to satisfy the linter, not the config to ignore the violation."}\n' "$BASENAME"
else
  echo '{}'
fi
