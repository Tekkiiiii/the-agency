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

Rooms are plain files written by `agents/scripts/room-utils.sh`, and by the feedback-pipeline cron (it writes under `agency-rooms/feedback/`). There is no polling process: the room polling skill was archived in the 2026-10-08 dept sunset, so nothing auto-notifies members, auto-summarizes `context/shared.md`, or routes `ESCALATE:` messages. Read rooms on demand with `room-utils.sh read`.

---

## Quick Start

### Commands (room-utils.sh)

Any agent or the main session can use the utilities directly:

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

## Room Naming Conventions

- **Format**: `kebab-case` — `api-design-sync`, `content-campaign-q2`, `ux-research`
- **Scope prefix** (optional): `project-or-domain/room-name` — `engineering/api-design`, `content-creation/campaign-brief`
- **Avoid**: Spaces, special characters, names longer than 50 chars

---

## @Mention Syntax

Agents can mention other agents in messages by convention (`@{from-agent} @{to-agent} — ready for review`). Mentions are plain text; no process parses them.

---

## NEXUS Handoffs

Rooms track structured task handoffs between agents using the NEXUS handoff protocol:

```bash
# Write a handoff (creates handoffs/{id}.md + logs to messages.mdl)
room-utils.sh write-handoff <room> <handoff-id> <from> <to> <task> <content>
# Example:
room-utils.sh write-handoff {project} FE-impl-01 {from-agent} {to-agent} "Implement API endpoint for contact form" "..."

# Read pending handoffs
room-utils.sh read-handoffs <room> pending

# Mark a handoff complete
room-utils.sh complete-handoff <room> <handoff-id>
```

**Lifecycle:**
1. `from` agent completes their work, writes handoff via `room-utils.sh write-handoff`
2. The sender tells the `to` agent (or the main session) the handoff exists; a later `room-utils.sh read-handoffs <room> pending` also finds it
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

- **`context/shared.md`** — Shared summary (key decisions, action items, open questions); maintained by hand
- **`context/spec.md`** — Current specification or design doc
- **`context/decisions.md`** — Decision log
- **`context/todos.md`** — Action items

Example — writing to shared context:
```bash
room-utils.sh write-context my-room todos.md "# Open Items\n- [ ] Review schema proposal (assigned: @{agent})\n- [ ] Security audit scheduled for Friday"
```

---

## Message Pattern Conventions

Prefix messages so they are greppable and easy to lift into `context/shared.md` by hand:

| Pattern | Example | Meaning |
|---------|---------|---------|
| `DECIDED:`, `CONCLUSION:` | `DECIDED: Using REST with versioned paths` | Key decision |
| `ACTION:`, `TODO:` | `ACTION: @{to-agent} review PR #42` | Action item |
| `QUESTION:`, `UNRESOLVED:` | `QUESTION: Should we use JWT or sessions?` | Open question |
| `SUMMARY:` | `SUMMARY: Resolved by choosing option A because...` | Summary line |
| `ESCALATE:` | `ESCALATE: tier-2 — API spec delayed, blocking 3 tasks` | Needs the main session; use `room-utils.sh escalate`, then tell the main session directly (see `escalation-protocol.md`) |

---

## Room Lifecycle

### Creation
`room-utils.sh create <room> "<description>" [members...]` creates the directory and files; the creator becomes room owner and initial members go into `members.json`.

### Deletion
`room-utils.sh delete <room>` removes the directory and all files permanently. No archive.

### Ownership Transfer
Not supported via command. Edit the `owner` field in `members.json` by hand.

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

**No notifications arrive** — Expected: there is no polling process. Read the room with `room-utils.sh read <room>` or tell the recipient directly.
