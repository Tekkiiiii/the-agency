# Agency Rooms — Inter-Agent Communication

Agency Rooms are file-based chat rooms that let agents coordinate across sessions
without needing to be running simultaneously. Every room is a directory with structured
log files that agents read and write to. Rooms are plain files: `agents/scripts/room-utils.sh` writes them (and the feedback-pipeline cron writes under `agency-rooms/feedback/`). There is no polling process; the `room-manager` skill was archived in the 2026-10-08 department sunset, so nothing auto-notifies members, auto-summarizes `context/shared.md`, or routes handoffs. Read a room on demand with `room-utils.sh read`.

## Room Directory Structure

```
{agency-root}/agency-rooms/{room}/
├── messages.mdl        # Append-only message log
├── room.json           # Room metadata and member list
├── members.json        # Active members
├── handoffs/           # Pending NEXUS handoffs (JSON)
└── context/
    ├── shared.md       # Shared summary (DECIDED/ACTION/QUESTION), maintained by hand
    └── rolling.md      # Append-only status feed (oversight room)
```

### room.json schema

```json
{
  "name": "{room-name}",
  "type": "project | oversight",
  "owner": "{agent-id}",
  "created": "{ISO timestamp}",
  "members": ["{agent-id}", "..."]
}
```

### members.json schema

```json
{
  "active": ["{agent-id}", "..."],
  "lastSeen": {
    "{agent-id}": "{ISO timestamp}"
  }
}
```

## Message Format (messages.mdl)

Each line is a structured log entry:

```
[{ISO timestamp}] @{agent-name} [{phase}]: {content}
```

Example:
```
[2026-04-16T09:00:00Z] @{project}-pd [brief]: Q from PD re: pricing page copy
[2026-04-16T09:05:00Z] @design-agent [reply]: Budget for landing page = $2k
[2026-04-16T09:07:00Z] @{project}-pd [action]: Spawning copywriting agent for pricing page
```

## Room Types

### Project Rooms
One room per active project. The project's PD owns the room and manages membership.

```
{agency-root}/agency-rooms/{project}/
```

### Oversight Room
All PDs post status updates to `project-oversight/`. The main session reads this room
on demand for portfolio-wide status.

```
{agency-root}/agency-rooms/project-oversight/
```

## PD Status Protocol

PDs write status to the oversight room via `context/rolling.md` (append-only):

```
[{ISO timestamp}] @{project}-pd: STATUS={status} PHASE={phase} BLOCKER={none|description}
```

The main session reads `project-oversight/context/rolling.md` on demand — never
on a polling loop. Use `/swarm` to trigger a portfolio-wide status sweep.

Do NOT implement recurring status pings. See **Status Loop Prohibition** in
`docs/ARCHITECTURE.md`.

## Agent Request Protocol

When an agent needs help from another agent or project:

1. Write a message to the relevant room:
   ```
   [{timestamp}] @{requesting-agent} [request]: @{recipient} need X for {project}. Context: {brief description}.
   ```
2. Tell the recipient (or the main session) that the request exists. Mentions are plain text; no process parses them or notifies anyone.
3. The recipient replies in the same room thread.
4. If the request needs a worker (`general-purpose` + skills), the PD or Coord creates a handoff JSON in `handoffs/` (`room-utils.sh write-handoff`).

## NEXUS Handoff JSON Format

Handoff artifacts in `handoffs/` are JSON files (not markdown). Filename convention:
`{ISO-date}_{task-id}.json`

```json
{
  "handoffId": "{task-id}",
  "from": "{from-agent}",
  "to": "{to-agent}",
  "project": "{project}",
  "created": "{ISO timestamp}",
  "phase": "handoff",
  "context": "Brief description of what this is about.",
  "done": [
    "Bullet — what was completed"
  ],
  "notDone": [
    "Bullet — what remains"
  ],
  "watchFor": [
    "Gotcha or caveat"
  ],
  "acceptanceCriteria": [
    "Criterion 1"
  ],
  "questions": [
    "Open question"
  ]
}
```

The sender tells the receiving agent the handoff exists; `room-utils.sh read-handoffs <room> pending` also finds it. Mark it done with `room-utils.sh complete-handoff`.
See `core/runbooks/agency-rooms-protocol.md` for the full schema specification.

## Setting Up a Room

```bash
ROOM="{agency-root}/agency-rooms/{room-name}"
mkdir -p "$ROOM/handoffs" "$ROOM/context"
touch "$ROOM/messages.mdl" "$ROOM/context/shared.md"
```

For the oversight room, also create `context/rolling.md`:
```bash
touch "$ROOM/context/rolling.md"
```

## Anti-patterns

- Do NOT send direct messages between agents — everything goes through rooms
- Do NOT write vague messages — always include `@{recipient}` and `[{phase}]`
- Do NOT skip the handoff JSON — without it, context is lost between sessions
- Do NOT implement recurring status loops — use on-demand reads via `/swarm`
