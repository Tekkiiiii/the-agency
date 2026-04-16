---
name: recall
description: Load project state from memory
category: memory
trigger: "/recall" | start of session
---

# Recall

Use this skill at the start of every session. It loads the project's current state from persistent memory so you have full context before starting work.

## When to use

- Start of every Claude Code session
- Switching to a different project
- On `RESUME` signal

## How to run

```
/recall
```

Or manually read the files.

## What to read (in order)

1. `~/.agency/projects/{project}/STATE.md` — current status, phase, blockers
2. `~/.agency/sessions/{project}/` — recent session logs
3. `~/.agency/lessons/{stack}.md` — relevant lessons
4. `~/.agency/decisions/` — architectural decisions that apply

## State File Format

```markdown
# {Project Name} — STATE

**Last updated**: {date}
**Phase**: {phase}
**Status**: {active|paused|blocked|complete}

## Current work
{brief description}

## Blockers
- {bullet or "None"}

## Next session
1. {next step}
```

## Output Format

After reading, give a tight briefing:

```
Project: {name}
Phase: {phase}
Status: {status}
Last: {what happened}
Next: {what to do first}
Blockers: {blockers or "None"}
```

Keep it under 6 lines. The point is context, not history.

## Key Rules

- If STATE.md doesn't exist → this is a new project, initialize
- If session log exists → read the most recent one first
- Lessons are append-only → read all that apply
- Decisions are authoritative → don't redo what's been decided
