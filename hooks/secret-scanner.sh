#!/usr/bin/env bash
# secret-scanner.sh — PreToolUse hook for Bash
# Scans bash commands for credential-looking patterns. Profile-aware.
set -euo pipefail

PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  echo '{}'
  exit 0
fi

INPUT=$(cat)

CMD=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)

if [ -z "$CMD" ]; then
  echo '{}'
  exit 0
fi

DECISION="ask"
if [ "$PROFILE" = "strict" ]; then
  DECISION="deny"
fi

FOUND=""

if printf '%s' "$CMD" | grep -qE 'eyJ[A-Za-z0-9_-]{50,}' 2>/dev/null; then
  FOUND="JWT token"
elif printf '%s' "$CMD" | grep -qE 'ghp_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}|github_pat_' 2>/dev/null; then
  FOUND="GitHub token"
elif printf '%s' "$CMD" | grep -qE 'xoxb-[0-9]+-[0-9]+-[a-zA-Z0-9]+|xoxp-[0-9]+-' 2>/dev/null; then
  FOUND="Slack token"
elif printf '%s' "$CMD" | grep -qE 'ya29\.[A-Za-z0-9_\-]{50,}' 2>/dev/null; then
  FOUND="Google OAuth token"
elif printf '%s' "$CMD" | grep -qE 'AKIA[A-Z0-9]{16}' 2>/dev/null; then
  FOUND="AWS access key"
elif printf '%s' "$CMD" | grep -qE '(ANTHROPIC_API_KEY|OPENAI_API_KEY|api_key|secret_key|access_token)[[:space:]]*=[[:space:]]*["\x27][A-Za-z0-9_\-]{20,}' 2>/dev/null; then
  FOUND="API key assignment"
fi

if [ -n "$FOUND" ]; then
  printf '{"permissionDecision":"%s","message":"[secret-scanner] Command contains what looks like a %s. Use env vars or keychain instead of inline credentials."}\n' "$DECISION" "$FOUND"
else
  echo '{}'
fi
