#!/usr/bin/env bash
# batch-check.sh — Stop hook
# Runs lightweight checks on files edited this session. Clears buffer after.
set -euo pipefail

PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  rm -f "$HOME/.claude/.edit-buffer.txt"
  exit 0
fi

BUFFER="$HOME/.claude/.edit-buffer.txt"

if [ ! -f "$BUFFER" ] || [ ! -s "$BUFFER" ]; then
  exit 0
fi

FILES=$(sort -u "$BUFFER")
rm -f "$BUFFER"

TOTAL=$(printf '%s\n' "$FILES" | wc -l | tr -d ' ')
echo "[batch-check] $TOTAL file(s) edited this session" >&2

TS_FILES=$(printf '%s\n' "$FILES" | grep -E '\.(ts|tsx)$' | head -20 || true)
SHELL_FILES=$(printf '%s\n' "$FILES" | grep -E '\.sh$' | head -20 || true)

if [ -n "$TS_FILES" ]; then
  TS_COUNT=$(printf '%s\n' "$TS_FILES" | wc -l | tr -d ' ')
  echo "  TypeScript: $TS_COUNT file(s)" >&2
  FIRST_TS=$(printf '%s\n' "$TS_FILES" | head -1)
  CHECK_DIR=$(dirname "$FIRST_TS")
  TSCONFIG=""
  for _ in 1 2 3 4; do
    if [ -f "$CHECK_DIR/tsconfig.json" ]; then
      TSCONFIG="$CHECK_DIR/tsconfig.json"
      break
    fi
    CHECK_DIR=$(dirname "$CHECK_DIR")
  done
  if [ -n "$TSCONFIG" ]; then
    TSCONFIG_DIR=$(dirname "$TSCONFIG")
    if ! (cd "$TSCONFIG_DIR" && npx tsc --noEmit --skipLibCheck 2>&1 | tail -5) >&2 2>&1; then
      echo "  TYPECHECK ERRORS — review before next session" >&2
    else
      echo "  Typecheck: clean" >&2
    fi
  fi
fi

if [ -n "$SHELL_FILES" ]; then
  SH_COUNT=$(printf '%s\n' "$SHELL_FILES" | wc -l | tr -d ' ')
  echo "  Shell: $SH_COUNT file(s)" >&2
  if command -v shellcheck &>/dev/null; then
    printf '%s\n' "$SHELL_FILES" | while read -r f; do
      [ -f "$f" ] && shellcheck -S warning "$f" 2>&1 | head -5 >&2 || true
    done
  fi
fi
