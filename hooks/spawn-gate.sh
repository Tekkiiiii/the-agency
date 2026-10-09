#!/usr/bin/env bash
# spawn-gate.sh — PreToolUse hook for Agent tool
# Since 2026-10-06 (generalist switch ACTIVE): `general-purpose` + 1-3 named
# skills is the DEFAULT spawn and passes without an ask. The specialist agents are
# archived; their role -> skills table is {agency-root}/agents-archive/ROLE-MAP.md.
# Kept structural types pass too. Only an unknown type with no routing marker is
# interrupted (an ask, never a block), so a typo or a stale archived name is caught.
# Returns {} (pass) or {"permissionDecision":"ask","message":"..."} (interrupt)
set -euo pipefail

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

# This read used to be "$HOME/.agency/.hook-profile" — the only one of the eight
# profile-reading hooks that looked anywhere other than $AGENCY_ROOT. Nothing
# has ever written that path: install.sh deploys the template to
# $AGENCY_ROOT/.hook-profile, and README/docs both document
# `echo minimal > ~/.claude/.hook-profile`. So the documented way to turn this
# gate off did nothing, on every platform, since the profile system existed.
PROFILE=$(cat "$AGENCY_ROOT/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  echo '{}'
  exit 0
fi

INPUT=$(cat)

SUBAGENT_TYPE=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("subagent_type",""))' 2>/dev/null || true)

PROMPT=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("prompt",""))' 2>/dev/null || true)

# --- Default + structural types (exact or pattern match) ---
case "$SUBAGENT_TYPE" in
  general-purpose|claude|"" \
  | pd-coordinator|coord|mini-coord|curator|codebase-search|Delegator|save-state-runner|project-scaffolder \
  | *-pd|critique-*|*-critique \
  | architecture-analyzer|article-analyzer|assemble-reviewer|domain-analyzer|file-analyzer|graph-reviewer|knowledge-graph-guide|project-scanner|tour-builder \
  | Explore|Plan|statusline-setup|claude-code-guide|fork|caveman:*)
    echo '{}'
    exit 0
    ;;
esac

# --- PD spawns by prompt prefix ---
if printf '%s' "$PROMPT" | grep -q '^You are PD-'; then
  echo '{}'
  exit 0
fi

# --- Explicit routing marker or a skill-owned spawn pattern ---
if printf '%s' "$PROMPT" | grep -qE 'DELEGATOR ROUTING|HARDCODED ROUTING:|SKILL SPAWN:|^You own the (save-state ritual|cc-loop ritual)|^You are [A-Za-z-]+-[A-Za-z-]+, resuming work|^You are resuming work on inbox task'; then
  echo '{}'
  exit 0
fi

# --- Unknown type: ask (catches typos and archived specialist names) ---
MSG="[spawn-gate] Unknown subagent_type=\"${SUBAGENT_TYPE}\".

The default since 2026-10-06 is general-purpose + 1-3 skills named in the prompt.
If this was a specialist name, it is archived: see ${AGENCY_ROOT}/agents-archive/ROLE-MAP.md
for its skills and role file, and spawn general-purpose instead.
To keep this type anyway, add 'HARDCODED ROUTING: {task-type} -> {agent}' to the prompt."

MSG_ESCAPED=$(printf '%s' "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '%s' "$MSG" | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n')

printf '{"permissionDecision":"ask","message":%s}\n' "$MSG_ESCAPED"
