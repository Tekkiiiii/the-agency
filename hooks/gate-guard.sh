#!/usr/bin/env bash
# gate-guard.sh — PreToolUse hook for Edit and Write
# Gates writes to sensitive system files. Profile-aware.
# Returns {"permissionDecision":"ask","message":"..."} or {}
set -euo pipefail

PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  echo '{}'
  exit 0
fi

INPUT=$(cat)

FILE_PATH=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)

CONTENT=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json
d=json.loads(sys.stdin.read())
ti=d.get("tool_input",{})
print(ti.get("content","") or ti.get("new_string",""))' 2>/dev/null || true)

if [ -z "$FILE_PATH" ]; then
  echo '{}'
  exit 0
fi

DECISION="ask"
if [ "$PROFILE" = "strict" ]; then
  DECISION="deny"
fi

WARN=""

case "$FILE_PATH" in
  *settings.json|*settings.local.json)
    WARN="Writing to settings file. Verify: no new plaintext secrets, hook commands reference existing scripts, permission changes are intentional."
    ;;
esac

if [ -z "$WARN" ]; then
  case "$FILE_PATH" in
    */.claude/agents/*.md|*/agents/*.md)
      WARN="Writing to agent definition: $(basename "$FILE_PATH"). Verify: modelTier matches role, skills list is accurate."
      ;;
  esac
fi

if [ -z "$WARN" ]; then
  case "$FILE_PATH" in
    */.claude/hooks/*.sh)
      WARN="Writing to hook script: $(basename "$FILE_PATH"). Hook scripts run on every matching tool call — verify no side effects on allowed operations."
      ;;
  esac
fi

if [ -z "$WARN" ]; then
  case "$FILE_PATH" in
    */SKILL.md)
      WARN="Writing to SKILL.md: $(basename "$(dirname "$FILE_PATH")")/SKILL.md. Skills are session-global — verify frontmatter is valid YAML."
      ;;
  esac
fi

if [ -z "$WARN" ] && [ -n "$CONTENT" ]; then
  if printf '%s' "$CONTENT" | grep -qE \
    '(eyJ[A-Za-z0-9_-]{50,}|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|xoxb-[0-9]+-|ya29\.[A-Za-z0-9_-]+|Bearer [A-Za-z0-9._-]{20,})' 2>/dev/null; then
    WARN="Content contains what looks like a JWT, API key, or bearer token. Use keychain or env references instead of inline secrets."
  fi
fi

if [ -n "$WARN" ]; then
  WARN_ESCAPED=$(printf '%s' "$WARN" | sed 's/"/\\"/g')
  printf '{"permissionDecision":"%s","message":"[gateguard] %s"}\n' "$DECISION" "$WARN_ESCAPED"
else
  echo '{}'
fi
