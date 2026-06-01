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

# --- Allowlist by subagent_type (exact match, no conditions) ---
# NOTE: general-purpose is NOT in this list — it must pass prompt checks below.
# Putting general-purpose here would nullify all enforcement for the most common spawn type.
case "$SUBAGENT_TYPE" in
  pd-coordinator|coord|mini-coord|task-executor|curator|codebase-search|Delegator|Explore|Plan|statusline-setup)
    echo '{}'
    exit 0
    ;;
esac

# --- Allowlist by prompt prefix: PD spawns ---
if printf '%s' "$PROMPT" | grep -q '^You are PD-'; then
  echo '{}'
  exit 0
fi

# --- Marker check: Delegator was consulted OR hardcoded routing was applied ---
if printf '%s' "$PROMPT" | grep -qE 'DELEGATOR ROUTING|HARDCODED ROUTING:'; then
  echo '{}'
  exit 0
fi

# --- Skill-spawn allowlist: structured skill subagents (save-state, pd-spawn, unwrap, etc.) ---
# These have well-known ownership patterns from skill definitions. They are mechanical
# subagents spawned by skills — not generic agent dispatches by the parent AI.
if printf '%s' "$PROMPT" | grep -qE '^You own the (save-state ritual|cc-loop ritual)|^You are [A-Za-z-]+-[A-Za-z-]+, resuming work|^You are resuming work on inbox task|SKILL SPAWN:'; then
  echo '{}'
  exit 0
fi

# --- Not allowlisted and no marker: interrupt ---
MSG="[spawn-gate] Agent spawn blocked. No routing marker found for subagent_type=\"${SUBAGENT_TYPE}\".

Two valid paths for non-allowlisted spawns:

Option A — Hardcoded routing (single-domain, obvious named agent):
  Include in your spawn prompt: HARDCODED ROUTING: {task-type} → {agent-name}
  Use only when the agent choice is unambiguous from the task type alone.

Option B — Delegator routing (cross-domain, protocol tasks, ambiguous):
1. Spawn: Agent({ subagent_type: \"Delegator\", prompt: \"Route this task: {description}\" })
2. Include the result block in your agent prompt:
   DELEGATOR ROUTING:
   Task: {task}
   Route: {agent or skill}
   Recommendation.Primary: {primary}
   Reason: {reason}

Pre-approved spawns (no marker needed):
  pd-coordinator, coord, mini-coord, task-executor, curator, codebase-search,
  Delegator, Explore, Plan, statusline-setup
  Any prompt starting with 'You are PD-' or a known skill-ownership pattern.

See {agency-root}/memory/agency-dispatch.md Step 1.5 for the routing protocol."

MSG_ESCAPED=$(printf '%s' "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '%s' "$MSG" | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n')

printf '{"permissionDecision":"ask","message":%s}\n' "$MSG_ESCAPED"
