#!/usr/bin/env bash
# room-utils.sh — Agency Chat Room utilities
# Provides CRUD operations for ~/.claude/agency-rooms/{room-name}/
# Any agent can invoke these to manage rooms without knowing the file format.
#
# Usage: room-utils.sh <command> [args...]
#   room-utils.sh create <room-name> <description> [members...]
#   room-utils.sh send <room-name> <sender> <message>
#   room-utils.sh read <room-name> [limit]
#   room-utils.sh list
#   room-utils.sh members <room-name>
#   room-utils.sh add-member <room-name> <agent-name>
#   room-utils.sh remove-member <room-name> <agent-name>
#   room-utils.sh info <room-name>
#   room-utils.sh delete <room-name>
#   room-utils.sh rooms-for <agent-name>

set -euo pipefail

ROOMS_DIR="${AGENCY_ROOMS_DIR:-${HOME}/.claude/agency-rooms}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ─── Lock helpers (portable: uses Python fcntl on macOS/Linux) ───────────────
# flock-run <lockfile> <timeout_sec> <command> [args...]
# Runs command with exclusive lock on lockfile; exits 1 on lock failure.
flock-run() {
  local lock="$1"; local timeout="$2"; shift 2
  python3 ~/.claude/agents/scripts/flock.py "$lock" "$timeout" "$@"
}

# flock-nb <lockfile> <command> [args...]
# Non-blocking: exits 1 immediately if lock can't be acquired.
flock-nb() {
  local lock="$1"; shift
  python3 ~/.claude/agents/scripts/flock.py --nb "$lock" "$@"
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
room-utils.sh — Agency Chat Room utilities

Usage: room-utils.sh <command> [args...]

Commands:
  create <room-name> <description> [members...]  Create a new room
  send <room-name> <sender> <message>            Send a message to a room
  read <room-name> [limit]                       Read recent messages (default: 50)
  list                                          List all rooms
  members <room-name>                            List room members
  add-member <room-name> <agent-name>           Add an agent to a room
  remove-member <room-name> <agent-name>         Remove an agent from a room
  info <room-name>                               Show room metadata
  delete <room-name>                             Delete a room
  rooms-for <agent-name>                         List rooms an agent belongs to
  escalate <room-name> <sender> <tier> <summary>   Post an escalation to council-chair
  write-handoff <room> <id> <from> <to> <task> <content>  Write a NEXUS handoff doc
  complete-handoff <room> <handoff-id>               Mark a handoff complete
  read-handoffs <room> [pending|complete|all]       Read NEXUS handoffs
  set-topic <room-name> <topic>                  Set current discussion topic
  write-context <room-name> <filename> <content> Write a shared context file

Environment:
  AGENCY_ROOMS_DIR   Override the rooms directory (default: ~/.claude/agency-rooms)
EOF
  exit 1
}

room_dir() {
  local room="$1"
  echo "${ROOMS_DIR}/${room}"
}

room_exists() {
  local room="$1"
  [[ -d "${ROOMS_DIR}/${room}" ]]
}

require_room() {
  local room="$1"
  if ! room_exists "$room"; then
    echo "ERROR: Room '$room' does not exist." >&2
    exit 1
  fi
}

require_arg() {
  local arg="$1"
  local name="$2"
  if [[ -z "$arg" ]]; then
    echo "ERROR: $name is required." >&2
    usage
  fi
}

# ─── Commands ────────────────────────────────────────────────────────────────

cmd_create() {
  local room="$1"; shift
  local description="$1"; shift
  local members=("$@")

  require_arg "$room" "room-name"
  require_arg "$description" "description"

  if room_exists "$room"; then
    echo "ERROR: Room '$room' already exists." >&2
    exit 1
  fi

  local dir="${ROOMS_DIR}/${room}"
  mkdir -p "${dir}/context"

  # room.json
  cat > "${dir}/room.json" <<EOF
{
  "name": "${room}",
  "description": "${description}",
  "topic": null,
  "created_by": "${AGENT_NAME:-unknown}",
  "created_at": "${TIMESTAMP}",
  "visibility": "private",
  "tags": []
}
EOF

  # members.json — creator is the owner
  local creator="${AGENT_NAME:-unknown}"
  local first=true
  local entries=""
  for m in "${members[@]:-}"; do
    if $first; then
      entries="    { \"name\": \"$m\", \"role\": \"member\", \"joined_at\": \"${TIMESTAMP}\", \"added_by\": \"$creator\" }"
      first=false
    else
      entries="${entries},
    { \"name\": \"$m\", \"role\": \"member\", \"joined_at\": \"${TIMESTAMP}\", \"added_by\": \"$creator\" }"
    fi
  done
  printf '%s\n' '{' '  "members": [' "${entries}" '  ],' "  \"owner\": \"$creator\"" '}' > "${dir}/members.json"
  chmod 600 "${dir}/members.json"

  # messages.mdl — create the log file with header
  cat > "${dir}/messages.mdl" <<EOF
## Room: ${room} — Message Log
*Created: ${TIMESTAMP} by ${creator}*
*Description: ${description}*

---

EOF

  # shared.md — default shared context
  cat > "${dir}/context/shared.md" <<EOF
# ${room} — Shared Context
*Last updated: ${TIMESTAMP}*

## Purpose
${description}

## Key Decisions

## Open Questions

## Relevant Files

EOF

  echo "OK: Room '$room' created."
  if [[ ${#members[@]} -gt 0 ]]; then
    echo "     Members: ${members[*]}"
  fi
}

cmd_send() {
  local room="$1"; shift
  local sender="$1"; shift
  local message="$*"

  require_arg "$room" "room-name"
  require_arg "$sender" "sender"
  require_arg "$message" "message"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/messages.mdl"
  local lock="${file}.lock"

  # Escape any closing h3 markers in the message to avoid markdown corruption
  local escaped="${message//###/---}"
  escaped="${escaped//---/&#x7E;&#x7E;&#x7E;}"

  # Lock-protected append via Python (macOS has no system flock)
  python3 /dev/stdin <<'PYEOF'
import fcntl, os, sys
lockfile, msgfile, marker = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.dirname(lockfile) or ".", exist_ok=True)
fd = os.open(lockfile, os.O_CREAT | os.O_RDWR, 0o600)
try:
    fcntl.flock(fd, fcntl.LOCK_EX)
    with open(msgfile, "a") as f:
        f.write("\n" + marker + "\n")
except Exception as e:
    sys.stderr.write(f"LOCK ERROR: {e}\n")
    sys.exit(1)
finally:
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
PYEOF
  python3 -c "
import fcntl, os
lockfile='${lock}'; msgfile='${file}'
msg='\n### [${TIMESTAMP}] ${sender}\n${escaped}\n---'
os.makedirs(os.path.dirname(lockfile), exist_ok=True)
fd=os.open(lockfile, os.O_CREAT|os.O_RDWR, 0o600)
try:
    fcntl.flock(fd, fcntl.LOCK_EX)
    open(msgfile,'a').write(msg)
except Exception as e:
    print('ERROR: Could not acquire lock on room messages.', file=__import__('sys').stderr)
    raise SystemExit(1)
finally:
    fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)
" || exit 1

  echo "OK: Message sent to '$room' by $sender."
}

cmd_read() {
  local room="$1"; shift
  local limit="${1:-50}"

  require_arg "$room" "room-name"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/messages.mdl"
  if [[ ! -f "$file" ]]; then
    echo "(no messages yet)"
    return
  fi

  # Restore escaped markers and show recent messages
  tail -n "$(( limit * 4 ))" "$file" | sed 's/&#x7E;&#x7E;&#x7E;/###/g'
}

cmd_list() {
  if [[ ! -d "$ROOMS_DIR" ]]; then
    echo "(no rooms)"
    return
  fi

  local count=0
  for dir in "${ROOMS_DIR}"/*/; do
    [[ -d "$dir" ]] || continue
    local room
    room=$(basename "$dir")

    local description="—"
    local member_count=0

    if [[ -f "${dir}/room.json" ]]; then
      description=$(jq -r '.description // "—" ' "${dir}/room.json" 2>/dev/null || echo "—")
    fi
    if [[ -f "${dir}/members.json" ]]; then
      member_count=$(jq '.members | length' "${dir}/members.json" 2>/dev/null || echo "0")
    fi

    printf "%-30s %2d members  %s\n" "$room" "$member_count" "$description"
    ((count++))
  done

  if [[ $count -eq 0 ]]; then
    echo "(no rooms)"
  fi
}

cmd_members() {
  local room="$1"
  require_arg "$room" "room-name"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/members.json"
  local owner
  owner=$(jq -r '.owner' "$file" 2>/dev/null || echo "unknown")

  echo "Owner: $owner"
  echo "Members:"
  jq -r '.members[] | "  \(.name) — \(.role) (joined \(.joined_at))"' "$file" 2>/dev/null || cat "$file"
}

cmd_add_member() {
  local room="$1"; shift
  local agent="$1"

  require_arg "$room" "room-name"
  require_arg "$agent" "agent-name"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/members.json"

  # Check if already a member
  if jq -e --arg name "$agent" '.members[] | select(.name == $name)' "$file" > /dev/null 2>&1; then
    echo "WARN: $agent is already a member of '$room'."
    return
  fi

  local added_by="${AGENT_NAME:-unknown}"
  local temp=$(mktemp)

  jq --arg name "$agent" --arg ts "$TIMESTAMP" --arg by "$added_by" \
    '.members += [{ name: $name, role: "member", joined_at: $ts, added_by: $by }]' \
    "$file" > "$temp" && mv "$temp" "$file"

  echo "OK: $agent added to '$room'."
}

cmd_remove_member() {
  local room="$1"; shift
  local agent="$1"

  require_arg "$room" "room-name"
  require_arg "$agent" "agent-name"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/members.json"

  # Check if owner
  local owner
  owner=$(jq -r '.owner' "$file" 2>/dev/null || echo "")
  if [[ "$owner" == "$agent" ]]; then
    echo "ERROR: Cannot remove the room owner. Transfer ownership first." >&2
    exit 1
  fi

  local temp=$(mktemp)
  jq --arg name "$agent" 'del(.members[] | select(.name == $name))' \
    "$file" > "$temp" && mv "$temp" "$file"

  echo "OK: $agent removed from '$room'."
}

cmd_info() {
  local room="$1"
  require_arg "$room" "room-name"
  require_room "$room"

  local dir="${ROOMS_DIR}/${room}"
  jq '.' "${dir}/room.json" 2>/dev/null
  echo ""
  echo "Members: $(jq '.members | length' "${dir}/members.json" 2>/dev/null || echo '?')"
  echo "Messages: $(($(wc -l < "${dir}/messages.mdl") / 4)) entries"
}

cmd_delete() {
  local room="$1"; shift
  local force=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -y|--force) force=true; shift ;;
      *) echo "Unknown flag: $1" >&2; usage ;;
    esac
  done

  require_arg "$room" "room-name"
  require_room "$room"

  local dir="${ROOMS_DIR}/${room}"

  if $force || [[ -n "${AGENT_MODE:-}" ]]; then
    rm -rf "$dir"
    echo "OK: Room '$room' deleted."
  else
    read -p "Delete room '$room' and all its messages? (y/N) " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      rm -rf "$dir"
      echo "OK: Room '$room' deleted."
    else
      echo "Cancelled."
    fi
  fi
}

cmd_rooms_for() {
  local agent="$1"
  require_arg "$agent" "agent-name"

  if [[ ! -d "$ROOMS_DIR" ]]; then
    echo "(no rooms)"
    return
  fi

  local found=0
  for dir in "${ROOMS_DIR}"/*/; do
    [[ -d "$dir" ]] || continue
    local room
    room=$(basename "$dir")
    local members_file="${dir}/members.json"

    if [[ -f "$members_file" ]] && jq -e --arg name "$agent" \
      '[.members[].name, (.owner == $name)] | any' "$members_file" > /dev/null 2>&1; then
      echo "$room"
      found=1
    fi
  done

  if [[ $found -eq 0 ]]; then
    echo "(no rooms for $agent)"
  fi
}

cmd_set_topic() {
  local room="$1"; shift
  local topic="$*"

  require_arg "$room" "room-name"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/room.json"
  local temp=$(mktemp)

  jq --arg topic "$topic" '.topic = $topic' "$file" > "$temp" && mv "$temp" "$file"
  echo "OK: Topic set to '$topic'."
}

# ─── Escalation ─────────────────────────────────────────────────────────────

# ESCALATE: tier body → written to messages.mdl, flagged for RoomManager → council-chair
cmd_escalate() {
  local room="$1"; shift
  local sender="$1"; shift
  local tier="$1"; shift
  local summary="$*"

  require_arg "$room" "room-name"
  require_arg "$sender" "sender"
  require_arg "$tier" "tier (1, 2, or 3)"
  require_arg "$summary" "summary"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/messages.mdl"
  local lock="${file}.lock"
  local escaped="${summary//###/---}"
  escaped="${escaped//---/&#x7E;&#x7E;&#x7E;}"

  {
    flock -e -w 5 "$lock" || { echo "ERROR: Could not acquire lock on '$room'." >&2; exit 1; }
    cat >> "$file" <<EOF

### [${TIMESTAMP}] ${sender}
ESCALATE: tier-${tier}
${escaped}
---
EOF
  } 200>"$lock"

  # Mark room as having a pending escalation (for RoomManager polling)
  local meta="${ROOMS_DIR}/${room}/.escalation"
  {
    flock -e -w 5 "$meta.lock" || { echo "WARN: Could not lock escalation file." >&2; exit 1; }
    echo "${tier}|${TIMESTAMP}|${sender}|${summary}" >> "$meta"
  } 200>"${meta}.lock"

  echo "OK: Escalation posted to '$room' (tier-${tier}). RoomManager will notify council-chair."
}

# ─── NEXUS Handoffs ─────────────────────────────────────────────────────────

cmd_write_handoff() {
  local room="$1"; shift
  local handoff_id="$1"; shift
  local from="$1"; shift
  local to="$1"; shift
  local task="$1"; shift
  local content="$*"

  require_arg "$room" "handoff-id"
  require_arg "$handoff_id" "handoff-id"
  require_arg "$from" "from-agent"
  require_arg "$to" "to-agent"
  require_arg "$task" "task"
  require_room "$room"

  local dir="${ROOMS_DIR}/${room}/handoffs"
  mkdir -p "$dir"

  local ts_short=$(date -u +"%Y%m%dT%H%M%SZ")
  local filename="${ts_short}-${handoff_id}.md"
  local msg_file="${ROOMS_DIR}/${room}/messages.mdl"
  local lock="${msg_file}.lock"

  # Hold room lock for both handoff file write + messages append
  {
    flock -e -w 10 "$lock" || { echo "ERROR: Could not acquire lock on '$room'." >&2; exit 1; }

    cat > "${dir}/${filename}" <<EOF
---
handoff_id: ${handoff_id}
from: ${from}
to: ${to}
task: ${task}
created_at: ${TIMESTAMP}
room: ${room}
status: pending
---

# NEXUS Handoff — ${handoff_id}

## Metadata
| Field | Value |
|-------|-------|
| **From** | ${from} |
| **To** | ${to} |
| **Task** | ${task} |
| **Room** | ${room} |
| **Created** | ${TIMESTAMP} |

${content}
EOF

    cat >> "$msg_file" <<EOF

### [${TIMESTAMP}] system
HANDOFF: ${handoff_id} — ${from} → ${to}: ${task}
---
EOF
  } 200>"$lock"

  echo "OK: Handoff '${handoff_id}' written. File: ${dir}/${filename}"
}

cmd_read_handoffs() {
  local room="$1"; shift
  local filter="${1:-all}"

  require_arg "$room" "room-name"
  require_room "$room"

  local dir="${ROOMS_DIR}/${room}/handoffs"
  if [[ ! -d "$dir" ]]; then
    echo "(no handoffs in '$room')"
    return
  fi

  local count=0
  for f in "${dir}"/*.md; do
    [[ -f "$f" ]] || continue
    local status
    status=$(grep -m1 '^status: ' "$f" | sed 's/^status: //')

    if [[ "$filter" == "all" ]] || [[ "$status" == "$filter" ]]; then
      echo "═══ $(basename "$f") ═══"
      grep '^## Metadata' -A 6 "$f" | head -10
      echo "---"
      ((count++))
    fi
  done

  if [[ $count -eq 0 ]]; then
    echo "(no ${filter} handoffs in '$room')"
  fi
}

cmd_complete_handoff() {
  local room="$1"; shift
  local handoff_id="$1"

  require_arg "$room" "room-name"
  require_arg "$handoff_id" "handoff-id"
  require_room "$room"

  local dir="${ROOMS_DIR}/${room}/handoffs"
  local msg_file="${ROOMS_DIR}/${room}/messages.mdl"
  local lock="${msg_file}.lock"
  local found=false

  {
    flock -e -w 10 "$lock" || { echo "ERROR: Could not acquire lock on '$room'." >&2; exit 1; }
    for f in "${dir}"/*.md; do
      [[ -f "$f" ]] || continue
      local fid
      fid=$(grep -m1 '^handoff_id: ' "$f" | sed 's/^handoff_id: //')
      if [[ "$fid" == "$handoff_id" ]]; then
        local temp=$(mktemp)
        sed 's/^status: pending$/status: complete/' "$f" > "$temp" && mv "$temp" "$f"
        echo "OK: Handoff '${handoff_id}' marked complete."
        found=true
        break
      fi
    done
  } 200>"$lock"

  if ! $found; then
    echo "ERROR: Handoff '${handoff_id}' not found in '${room}'." >&2
    exit 1
  fi
}

cmd_write_context() {
  local room="$1"; shift
  local filename="$1"; shift
  local content="$*"

  require_arg "$room" "room-name"
  require_arg "$filename" "filename"
  require_room "$room"

  local dir="${ROOMS_DIR}/${room}/context"
  local lock="${ROOMS_DIR}/${room}/messages.mdl.lock"

  {
    flock -e -w 5 "$lock" || { echo "ERROR: Could not acquire lock on '$room'." >&2; exit 1; }
    echo "$content" > "${dir}/${filename}"
  } 200>"$lock"
  echo "OK: Context file '${filename}' written to room '$room'."
}

cmd_read_context() {
  local room="$1"; shift
  local filename="$1"

  require_arg "$room" "room-name"
  require_arg "$filename" "filename"
  require_room "$room"

  local file="${ROOMS_DIR}/${room}/context/${filename}"
  if [[ ! -f "$file" ]]; then
    echo "ERROR: Context file '$filename' not found in room '$room'." >&2
    exit 1
  fi

  cat "$file"
}

# ─── Dispatch ────────────────────────────────────────────────────────────────

COMMAND="${1:-}"; shift || true

case "$COMMAND" in
  create)        cmd_create "$@" ;;
  send)          cmd_send "$@" ;;
  read)          cmd_read "$@" ;;
  list)          cmd_list ;;
  members)       cmd_members "$@" ;;
  add-member)    cmd_add_member "$@" ;;
  remove-member) cmd_remove_member "$@" ;;
  info)          cmd_info "$@" ;;
  delete)        cmd_delete "$@" ;;
  rooms-for)     cmd_rooms_for "$@" ;;
  set-topic)     cmd_set_topic "$@" ;;
  escalate)      cmd_escalate "$@" ;;
  write-handoff) cmd_write_handoff "$@" ;;
  complete-handoff) cmd_complete_handoff "$@" ;;
  read-handoffs) cmd_read_handoffs "$@" ;;
  write-context) cmd_write_context "$@" ;;
  read-context)  cmd_read_context "$@" ;;
  help|--help|-h) usage ;;
  *)             echo "Unknown command: $COMMAND" >&2; usage ;;
esac
