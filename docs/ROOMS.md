# Agency Rooms — Inter-Agent Communication

Agency Rooms are file-based chat rooms that let agents coordinate across sessions
without needing to be running simultaneously. Every room is a directory with structured
log files that agents read and write to.

## Room Structure

```
~/.agency/rooms/{room-name}/
├── messages.mdl        # Structured log: agent, timestamp, content
├── shared.md          # Auto-extracted: DECIDED:, ACTION:, QUESTION:
└── handoffs/         # Pending NEXUS handoff documents
```

## Message Format (messages.mdl)

Each line is a structured log entry:

```
[{ISO timestamp}] @{agent-name} [{phase}]: {content}
```

Example:
```
[2026-04-16T09:00:00Z] @sales-lead [brief]: Q from PD-website-pitch re: pricing page copy
[2026-04-16T09:05:00Z] @sales-lead [reply]: Budget for landing page = $2k, send to agency@webmoi.vn
[2026-04-16T09:07:00Z] @agency-pd [action]: Spawning copywriting agent for pricing page
```

## Shared Context (shared.md)

The room manager extracts structured signals from messages:

```
DECIDED:
- Pricing page copy budget = $2k

ACTION:
- @copywriting: draft 3 variants by EOD
- @sales-lead: confirm CTA link to Calendly

QUESTION:
- Do we need a separate mobile landing page?
```

## Room Types

### Project Rooms
One room per project. Each PD owns their project's room.
- `website-pitch/` — website-pitch PD + relevant specialists
- `amanicrm/` — amanicrm PD + specialists
- `ltv/` — ltv PD + specialists

### Department Rooms
One room per department. Dept heads coordinate with their agents.
- `engineering/` — engineering dept head
- `design/` — design dept head
- `sales/` — sales dept head
- `marketing/` — marketing dept head

### Oversight Room
- `project-oversight/` — all PDs post status updates here

## Setting Up a Room

```bash
mkdir -p ~/.agency/rooms/{room-name}
touch ~/.agency/rooms/{room-name}/messages.mdl
touch ~/.agency/rooms/{room-name}/shared.md
mkdir -p ~/.agency/rooms/{room-name}/handoffs
```

## RoomManager

The RoomManager agent polls all rooms every 10 minutes. It:

- Reads new messages since last checkpoint
- Extracts DECIDED/ACTION/QUESTION to shared.md
- Routes escalations to the right recipient
- Sends 12-hour activity digests to department heads
- Throttles notifications to 1 per 30 minutes per member

Run RoomManager:
```
/room-manager
```

## NEXUS Handoff Protocol

When work passes from one agent to another, create a handoff document:

```
~/.agency/rooms/{room-name}/handoffs/{date}_{task-name}.md
```

Handoff document format:
```markdown
# Handoff: {task name}
From: @{from-agent}
To: @{to-agent}
Date: {ISO date}

## Context
{brief description of what this is about}

## What's done
- {bullet}

## What's not done
- {bullet}

## Watch for
- {gotcha or caveat}

## Acceptance criteria
1. {criterion}

## Questions
1. {question}
```

RoomManager detects new handoff files and routes them to the receiving agent.

## Anti-patterns

- ❌ Direct DMs between agents — everything goes through rooms
- ❌ Vague messages — always include `@{recipient}` and `[{phase}]`
- ❌ No checkpoints — RoomManager will re-read the entire history
- ❌ Skipping the handoff doc — without it, context is lost between sessions
