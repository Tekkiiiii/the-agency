# Agency Rooms Protocol

> How to create, join, message, and manage multi-agent chat rooms in The Agency.

---

## Overview

Agency Rooms are persistent, file-based chat spaces where agents communicate across sessions. Unlike `SendMessage` (fire-and-forget), rooms persist all messages, maintain shared context, and support cross-session continuity.

```
{agency-root}/agency-rooms/{room-name}/
├── room.json       # Metadata (name, description, topic, created_by)
├── members.json    # Member list with roles and join timestamps
├── messages.mdl    # Message log (append-only, markdown format)
└── context/
    └── shared.md   # Auto-summarized shared context
```

Rooms are managed by the **RoomManager** agent and powered by `room-utils.sh`.

---

## Quick Start

### For a Human / Parent AI

**Create a room:**
```
TO: room-manager
ACTION: create_room
ROOM_NAME: game-engine-sync
DESCRIPTION: Weekly sync between Unity and Unreal leads on shared architecture
MEMBERS: [unity-architect, unreal-systems-engineer, game-designer]
```

**Send a message:**
```
TO: room-manager
ACTION: send_message
ROOM: game-engine-sync
MESSAGE: We've finalized the ECS approach. @unity-architect please review the benchmark results.
```

**List all rooms:**
```
TO: room-manager
ACTION: list_rooms
```

**Add a member:**
```
TO: room-manager
ACTION: add_member
ROOM: game-engine-sync
MEMBER: godot-gameplay-scripter
```

### For an Agent (via room-utils.sh)

Any agent can use the utilities directly:

```bash
# Create a room
room-utils.sh create my-room "Description here" member1 member2

# Send a message
room-utils.sh send my-room my-agent "Hello everyone!"

# Read recent messages
room-utils.sh read my-room 20

# List all rooms
room-utils.sh list

# Add/remove members
room-utils.sh add-member my-room new-agent
room-utils.sh remove-member my-room old-agent

# Set discussion topic
room-utils.sh set-topic my-room "Q2 architecture review"

# Write shared context (reference docs, specs, decisions)
room-utils.sh write-context my-room architecture.md "# Architecture Decision..."

# List rooms an agent belongs to
room-utils.sh rooms-for my-agent
```

---

## RoomManager Actions Reference

| Action | Parameters | Description |
|--------|-----------|-------------|
| `create_room` | `ROOM_NAME`, `DESCRIPTION`, `MEMBERS` (optional) | Create a new room |
| `delete_room` | `ROOM_NAME` | Delete a room (confirms first) |
| `add_member` | `ROOM`, `MEMBER` | Add an agent to a room |
| `remove_member` | `ROOM`, `MEMBER` | Remove an agent (not the owner) |
| `list_rooms` | — | List all agency rooms |
| `room_info` | `ROOM` | Show room metadata + stats |
| `set_topic` | `ROOM`, `TOPIC` | Set/change discussion topic |
| `send_message` | `ROOM`, `MESSAGE` | Post a message to the room |
| `read_room` | `ROOM`, `LIMIT` (default 50) | Read recent messages |
| `escalate` | `ROOM`, `SENDER`, `TIER`, `SUMMARY` | Post an escalation (auto-routed to council-chair) |
| `write_handoff` | `ROOM`, `ID`, `FROM`, `TO`, `TASK`, `CONTENT` | Write a NEXUS handoff doc |
| `complete_handoff` | `ROOM`, `HANDOFF_ID` | Mark a handoff as complete |
| `read_handoffs` | `ROOM`, `FILTER` (pending/complete/all) | Read handoff docs |
| `poll` | — | Internal: run polling cycle (called by cron) |
| `check_escalations` | — | Check and route pending escalations |
| `check_handoffs` | — | Check for new pending handoffs and notify recipients |
| `help` | — | Show this reference |

---

## Room Naming Conventions

- **Format**: `kebab-case` — `game-engine-sync`, `marketing-campaign-q2`, `ux-research`
- **Scope prefix** (optional): `dept-name/room-name` — `engineering/api-design`, `marketing/china-strategy`
- **Avoid**: Spaces, special characters, names longer than 50 chars

---

## @Mention Syntax

Agents can mention other agents in messages:
```
@backend-architect @frontend-developer — ready for review
```

The RoomManager parses these and sends targeted notifications to mentioned agents.

---

## NEXUS Handoffs

Rooms track structured task handoffs between agents using the NEXUS handoff protocol:

```bash
# Write a handoff (creates handoffs/{id}.md + logs to messages.mdl)
room-utils.sh write-handoff <room> <handoff-id> <from> <to> <task> <content>
# Example:
room-utils.sh write-handoff {project} FE-impl-01 backend-architect frontend-developer "Implement API endpoint for contact form" "..."

# Read pending handoffs
room-utils.sh read-handoffs <room> pending

# Mark a handoff complete
room-utils.sh complete-handoff <room> <handoff-id>
```

**Lifecycle:**
1. `from` agent completes their work, writes handoff via `room-utils.sh write-handoff`
2. RoomManager polling detects pending handoff → sends `SendMessage` to `to` agent
3. `to` agent reads handoff content and begins work
4. `to` agent marks complete with `room-utils.sh complete-handoff`

**Handoff content should include:**
- Task ID and description
- Acceptance criteria
- Reference files
- Dependencies
- What the recipient needs to know

---

## Shared Context Files

Each room has a `context/` subdirectory. Agents write shared documents there:

- **`context/shared.md`** — Auto-summarized by RoomManager (key decisions, action items, open questions)
- **`context/spec.md`** — Current specification or design doc
- **`context/decisions.md`** — Decision log
- **`context/todos.md`** — Action items

Example — writing to shared context:
```bash
room-utils.sh write-context my-room todos.md "# Open Items\n- [ ] Review ECS proposal (assigned: @unity-architect)\n- [ ] Security audit scheduled for Friday"
```

---

## Message Patterns Recognized by RoomManager

These prefixes auto-populate `context/shared.md` and/or trigger routing actions:

| Pattern | Example | Effect |
|---------|---------|--------|
| `DECIDED:`, `CONCLUSION:` | `DECIDED: Using REST with versioned paths` | → Key Decisions section |
| `ACTION:` | `ACTION: @backend-architect review PR #42` | → Action Items section |
| `TODO:` | `TODO: Document the auth flow` | → Action Items section |
| `QUESTION:` | `QUESTION: Should we use JWT or sessions?` | → Open Questions section |
| `UNRESOLVED:` | `UNRESOLVED: Database choice TBD` | → Open Questions section |
| `SUMMARY:` | `SUMMARY: Resolved by choosing option A because...` | → Updates shared summary |
| `ESCALATE:` | `ESCALATE: tier-2 — API spec delayed, blocking 3 tasks` | **→ Routed to council-chair by RoomManager** |

---

## Active Polling

The RoomManager polls every **15 minutes** via `CronCreate`. On each poll:
1. Reads `state.json` for last check timestamps per room
2. Checks `messages.mdl` for new entries since last poll
3. Identifies members with unread messages
4. Sends `SendMessage` notifications with summaries
5. Updates `context/shared.md` with new decisions/actions/questions
6. Updates `state.json` with new checkpoints

**Throttling**: Members aren't re-notified for the same room within 30 minutes.

---

## Room Lifecycle

### Creation
1. RoomManager creates directory and files
2. Creator becomes room owner
3. Initial members added to `members.json`
4. Room appears in `list_rooms`
5. Members receive welcome notification

### Deletion
1. Owner or parent AI requests `delete_room`
2. RoomManager confirms with `y/N`
3. Directory and all files permanently removed
4. No archive (rooms are not preserved on deletion)

### Ownership Transfer
- Not currently supported via command
- To transfer: remove current owner as member, re-add as member, manually update `members.json` owner field

---

## Integration with SendMessage

Rooms don't replace `SendMessage` — they complement it:

| Use Case | Tool |
|----------|------|
| Formal task handoff | `SendMessage` (direct) |
| Project discussions | Room |
| Architectural decisions | Room + shared context |
| Urgent requests | `SendMessage` (immediate) |
| Cross-session threads | Room |
| Status updates | Room |
| Context sharing | Room + context files |

---

## Spawning the RoomManager

The RoomManager is activated like any other agent:

```
/spawn room-manager
```

Or via the parent AI spawning it with its definition file.

To activate polling on first spawn, the RoomManager will `CronCreate` with:
```
cron: "*/15 * * * *"
prompt: "Run RoomManager polling cycle"
durable: true
```

---

## Best Practices

1. **Name rooms for purpose, not participants** — `architecture-decisions` beats `alice-bob-chat`
2. **Keep messages actionable** — use `ACTION:`, `DECIDED:`, `QUESTION:` patterns
3. **Write shared context** — specs, decisions, and files in `context/` outlive the message thread
4. **Use @mentions sparingly** — too many mentions cause notification fatigue
5. **Delete stale rooms** — inactive rooms create noise; clean them up
6. **One room per topic** — don't conflate unrelated discussions

---

## Troubleshooting

**"Room not found"** — Check spelling with `room-utils.sh list`

**"Already a member"** — The agent is already in the room; no action needed

**"Cannot remove owner"** — Transfer ownership first by editing `members.json` manually

**Agent not receiving notifications** — Check that the agent name in `members.json` matches exactly (case-sensitive)

**Messages not appearing** — Verify `room-utils.sh send` succeeded (should print `OK:`)

**RoomManager not polling** — Re-spawn the RoomManager agent; it re-registers its cron on activation
