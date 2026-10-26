#!/usr/bin/env bash
# unsaid-check.sh - PreToolUse hook (Write|Edit|Bash|SendMessage|Agent). WARN only, never deny/ask/allow.
# Flags brief lines (PD briefs, revision/incoming files, SendMessage) that carry instructions the user never said.
# Emits {} or {"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"UNSAID-CHECK: ..."}}.
# Main session only (subagent calls carry agent_id). Any error -> {} (fail open). Core: scripts/unsaid_check.py --hook.
. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

PROFILE=$(cat "$AGENCY_ROOT/.hook-profile" 2>/dev/null | tr -d '[:space:]')
if [ "$PROFILE" = "minimal" ]; then echo '{}'; exit 0; fi

INPUT=$(cat)

# subagent call -> pass (cheap grep, no python)
if printf '%s' "$INPUT" | grep -Eq '"agent_id" *: *"[^"]+"'; then echo '{}'; exit 0; fi
# Bash fast path: only inter-spawn-tasks commands are candidates
case "$INPUT" in
  *'"tool_name":"Bash"'*|*'"tool_name": "Bash"'*)
    case "$INPUT" in *inter-spawn-tasks*) ;; *) echo '{}'; exit 0 ;; esac ;;
esac

CORE="$(cd "$(dirname "$0")/.." && pwd)/scripts/unsaid_check.py"
OUT=$(printf '%s' "$INPUT" | python3 "$CORE" --hook 2>/dev/null) || OUT=''
if [ -z "$OUT" ]; then echo '{}'; else printf '%s\n' "$OUT"; fi
exit 0
