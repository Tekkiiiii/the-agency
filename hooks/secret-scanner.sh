#!/usr/bin/env bash
# secret-scanner.sh — PreToolUse hook for Bash
# Scans bash commands for credential-looking patterns. Profile-aware.
# Returns {} (pass) or {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask|deny",
# "permissionDecisionReason":"..."}} (ask under standard, deny under strict).
# A top-level permissionDecision/message is silently ignored.
set -euo pipefail

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

PROFILE=$(cat "$AGENCY_ROOT/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
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

# Emit a PreToolUse decision in the shape Claude Code honours. A top-level
# {"permissionDecision":..,"message":..} is silently ignored. json.dumps keeps quotes/newlines valid.
emit_decision() { # $1=deny|ask $2=reason
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":sys.argv[1],"permissionDecisionReason":sys.argv[2]}}))' "$1" "$2"
}

if [ -n "$FOUND" ]; then
  emit_decision "$DECISION" "[secret-scanner] Command contains what looks like a $FOUND. Use env vars or keychain instead of inline credentials."
else
  echo '{}'
fi
