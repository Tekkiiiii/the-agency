# NEXUS Coordination Protocol

NEXUS is the coordination layer that lets agents work together across sessions.

## Core Principle

> Every agent writes what it knows. The next agent reads what it needs.

> **Note on handoff format:** The 6-phase coordination model (Register → Brief → Work → Handoff → Review → Archive) remains the doctrine. The handoff artifact is now a **JSON file** (not markdown) placed in `{room}/handoffs/`. See `core/runbooks/agency-rooms-protocol.md` for the full schema. RoomManager processes handoff files automatically and routes them to the receiving agent.

## The Six Phases

### Phase 0: Register
Create the project structure and task.

### Phase 1: Brief
Assign work with full context.

### Phase 2: Work
Execute, document incrementally.

### Phase 3: Handoff
Transfer with evidence and acceptance criteria.

### Phase 4: Review
Gate the work against acceptance criteria.

### Phase 5: Archive
Close out and record lessons.

## Key Rules

1. **Write before you stop** — never end a session without saving state
2. **Gate before handoff** — don't pass work that doesn't meet criteria
3. **Blockers surface fast** — escalate within one session
4. **Lessons from mistakes** — append, never overwrite

## Quick Reference

```
On spawn:        Read STATE.md → Read session log → Ask what to focus on
On work:         Update task → Execute → Document → Gate
On handoff:      Write context → Update task → Notify receiver
On session end:  /save-state → Update STATE.md → Report to PD
```

## Escalation Levels

| Level | Trigger | Action |
|---|---|---|
| tier-1 | Minor blocker | Note in session log, continue |
| tier-2 | Major blocker | Escalate to team-lead, pause task |
| tier-3 | Crisis | Escalate to council, stop work |
