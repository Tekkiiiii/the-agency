# Agency Rooms — Inter-Agent Communication

Agency Rooms are file-based chat rooms that let agents coordinate across sessions
without needing to be running simultaneously. Every room is a directory with structured
log files that agents read and write to.

## Room Directory Structure

```
{agency-root}/agency-rooms/{room}/
├── messages.mdl        # Append-only message log
├── room.json           # Room metadata and member list
├── members.json        # Active members
├── handoffs/           # Pending NEXUS handoffs (JSON)
└── context/
    ├── shared.md       # Extracted DECIDED/ACTION/QUESTION items
    └── rolling.md      # Dept head status feed (dept rooms only)
```

### room.json schema

```json
{
  "name": "{room-name}",
  "type": "project | department | oversight",
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
[2026-04-16T09:05:00Z] @sales-lead [reply]: Budget for landing page = $2k
[2026-04-16T09:07:00Z] @{project}-pd [action]: Spawning copywriting agent for pricing page
```

## Room Types

### Project Rooms
One room per active project. The project's PD owns the room and manages membership.

```
{agency-root}/agency-rooms/{project}/
```

### Department Rooms
One room per department. Department heads coordinate specialists here.

```
{agency-root}/agency-rooms/engineering/
{agency-root}/agency-rooms/testing/
{agency-root}/agency-rooms/design/
{agency-root}/agency-rooms/marketing/
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

When an agent needs help from another department:

1. Agent writes a message to the relevant **department room**:
   ```
   [{timestamp}] @{requesting-agent} [request]: @{dept-head} need X for {project}. Context: {brief description}.
   ```
2. RoomManager fans the request out to the department head.
3. Department head replies in the same room thread.
4. If the request requires spawning a specialist, the department head creates a handoff JSON in `handoffs/`.

## RoomManager Behavior

RoomManager polls all rooms on a configurable interval (default: 10 minutes). On each poll it:

1. Reads `messages.mdl` since the last checkpoint timestamp
2. Extracts structured signals into `context/shared.md`:
   - Lines starting with `DECIDED:` → append to DECIDED section
   - Lines starting with `ACTION:` → append to ACTION section
   - Lines starting with `QUESTION:` → append to QUESTION section
3. Appends department-head messages to `context/rolling.md` in department rooms
4. Detects new files in `handoffs/` and routes them to the named receiving agent
5. Throttles notifications: max 1 per 30 minutes per member
6. Emits a 12-hour activity digest to each department head

Run RoomManager:
```
/room-manager
```

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

RoomManager processes new handoff files automatically and notifies the receiving agent.
See `core/runbooks/agency-rooms-protocol.md` for the full schema specification.

## Setting Up a Room

```bash
ROOM="{agency-root}/agency-rooms/{room-name}"
mkdir -p "$ROOM/handoffs" "$ROOM/context"
touch "$ROOM/messages.mdl" "$ROOM/context/shared.md"
```

For department rooms, also create `context/rolling.md`:
```bash
touch "$ROOM/context/rolling.md"
```

## Anti-patterns

- Do NOT send direct messages between agents — everything goes through rooms
- Do NOT write vague messages — always include `@{recipient}` and `[{phase}]`
- Do NOT omit checkpoints — RoomManager will re-read the entire history without them
- Do NOT skip the handoff JSON — without it, context is lost between sessions
- Do NOT implement recurring status loops — use on-demand reads via `/swarm`
