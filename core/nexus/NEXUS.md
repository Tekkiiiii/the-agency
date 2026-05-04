# NEXUS — Inter-Agent Communication Protocol

NEXUS is the file-based communication system that allows agents to coordinate across sessions, machines, and time zones.

## Core Principle

Every agent writes what it knows to a shared file. The next agent reads what it needs. No conversation required.

## The Six Phases

### Phase 0 — Register
When a new project starts:
1. Create `~/.claude/projects/{project}/`
2. Create `~/.claude/sessions/{project}/`
3. Create `~/.claude/projects/{project}/STATE.md`
4. Create a task in the task store

### Phase 1 — Brief
When assigning work to another agent:
1. Write the full context to the task `notes`
2. Include: what, why, what was tried, acceptance criteria
3. Update `assigned_agent` in task store
4. Notify the receiving agent via session log

### Phase 2 — Work
The specialist executes:
1. Read task description + context
2. Update task to `in_progress`
3. Work incrementally — write session log every significant step
4. Don't wait until the end to document

### Phase 3 — Handoff
When completing or passing work:
1. Write: what's done, what's not done, what to watch for
2. Gate the task (if required)
3. Mark `done` or reassign
4. Update `STATE.md` with current status

### Phase 4 — Review
When reviewing another's work:
1. Read session log + task notes
2. Check evidence against acceptance criteria
3. Gate: `passed` or `failed`
4. If `failed`: explain what's wrong, send back to specialist

### Phase 5 — Archive
When a project or phase is complete:
1. Move session logs to `memory/`
2. Write a summary lesson
3. Update `STATE.md` to completed
4. Close tasks in task store

## Session Log Format

```markdown
# Session: {date}

## What I did
- {bullet}

## What I found
- {bullet}

## What's next
- {bullet}

## Blockers
- {bullet or "None"}
```

## Handoff Document Format

When passing work to another agent:

```markdown
# Handoff: {task name}

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
2. {criterion}

## Questions for receiver
1. {question}
```

## Rooms (Optional)

For teams using file-based rooms:

```
~/.claude/rooms/{project}/
├── messages.mdl   ← structured log (agent, timestamp, content)
├── shared.md      ← auto-extracted: DECIDED, ACTION, QUESTION
└── handoffs/     ← pending handoff documents
```
