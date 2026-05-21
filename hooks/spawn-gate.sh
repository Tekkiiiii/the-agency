#!/usr/bin/env bash
# spawn-gate.sh — PreToolUse hook for Agent tool
# Enforces Delegator-first dispatch. Allowlisted spawns pass through.
# Non-allowlisted spawns require DELEGATOR ROUTING block in prompt.
# Returns {} (pass) or {"permissionDecision":"ask","message":"..."} (interrupt)
set -euo pipefail

PROFILE=$(cat "$HOME/.agency/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  echo '{}'
  exit 0
fi

INPUT=$(cat)

SUBAGENT_TYPE=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("subagent_type",""))' 2>/dev/null || true)

PROMPT=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("prompt",""))' 2>/dev/null || true)

# --- Allowlist by subagent_type (exact match) ---
case "$SUBAGENT_TYPE" in
  pd-coordinator|coord|mini-coord|task-executor|curator|codebase-search|Delegator|Explore|Plan|statusline-setup|general-purpose)
    echo '{}'
    exit 0
    ;;
esac

# --- Allowlist by prompt prefix: PD spawns ---
if printf '%s' "$PROMPT" | grep -q '^You are PD-'; then
  echo '{}'
  exit 0
fi

# --- Marker check: Delegator was consulted ---
if printf '%s' "$PROMPT" | grep -q 'DELEGATOR ROUTING'; then
  echo '{}'
  exit 0
fi

# --- Not allowlisted and no marker: interrupt ---
MSG="[spawn-gate] Agent spawn blocked. Delegator was not consulted before spawning subagent_type=\"${SUBAGENT_TYPE}\".

Before spawning any non-allowlisted agent, you must:
1. Spawn the Delegator: Agent({ subagent_type: \"Delegator\", prompt: \"Route this task: {your task description}\\nProject context: {project slug}\" })
2. Wait for Delegator's routing recommendation
3. Include the recommendation block in your agent prompt:

   DELEGATOR ROUTING:
   Task: {task}
   Route: {agent or skill}
   Recommendation.Primary: {primary recommendation}
   Reason: {reason}

Pre-approved spawns that bypass Delegator:
  pd-coordinator, coord, mini-coord, task-executor, curator, codebase-search,
  Delegator, Explore, Plan, statusline-setup,
  general-purpose (only when prompt starts with 'You are PD-' or contains 'DELEGATOR ROUTING')

See ~/.agency/memory/agency-dispatch.md Step 1.5 for the full allowlist."

MSG_ESCAPED=$(printf '%s' "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '%s' "$MSG" | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n')

printf '{"permissionDecision":"ask","message":%s}\n' "$MSG_ESCAPED"
