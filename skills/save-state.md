---
name: save-state
description: Persist session to memory files
category: memory
trigger: "/save-state" | end of session
---

# Save State

Use this skill at the end of every session. It writes the current session's work to persistent memory files so the next agent can resume exactly where you left off.

## When to use

- End of every Claude Code session
- Before switching to a different project
- Before a long-running task
- On `ESCALATE` or `DECLINED` signal

## What it saves

1. **Session log**: `~/.agency/sessions/{project}/{date}.md`
2. **Project state**: `~/.agency/projects/{project}/STATE.md`
3. **Lessons**: new lessons appended to `~/.agency/lessons/{stack}.md`

## How to run

```
/save-state
```

Or manually write to the files.

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

## Open tasks
- {task-id}: {task-name}
```

## State Update Format

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
2. {next step}
```

## Key Rules

- Append lessons to `lessons/{stack}.md`, never overwrite
- Keep state concise — the next agent reads it
- Note blockers explicitly — don't hide them
