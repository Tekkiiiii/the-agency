---
name: dept-resume
description: Read dept-state.md and spawn a Dept Head with a lean briefing. Department-operations parallel of /pd-resume.
category: dept-ops
version: 1.0.0
---

# dept-resume

Spawns a Dept Head agent for the given department with a pre-built briefing from `dept-state.md`. Lean context, fast start.

## Usage

```
/dept-resume [dept-slug]
/dept-resume content-creation
/dept-resume engineering
/dept-resume all
```

## Argument Resolution

| Argument | Action |
|---|---|
| `[dept-slug]` | Resume exactly one department |
| `all` | Resume all active departments (spawns in parallel) |
| no arg | Fail with usage hint |

## What It Does

1. Reads `~/.agency/agents/{dept}/state/dept-state.md`
2. Checks `~/.agency/agents/{dept}/state/incoming/` for pending inter-spawn tasks
3. Spawns the Dept Head with dept-state.md inline — no extra reads on spawn
4. Dept Head boots per `core/runbooks/dept-boot-sequence.md` Mode 1

## Dept Head Boot Context

The spawn prompt includes:
- dept-state.md content (inline, no file read needed)
- incoming task count and any HIGH-priority items
- The dept head's agent definition path

**Target context on spawn: ~400 tokens.** Everything else is lazy-loaded per Mode 2 (Route).

## Output

```
dept-resume done — {dept}
  Head: {head-agent-name}
  Priority: {current-priority from dept-state}
  Active coords: {n or "none"}
  Incoming tasks: {n or "none"}
```

## Notes

- If `dept-state.md` doesn't exist, output: `No dept-state found for {dept}. Run /dept-save-state to initialize.`
- Dept Heads do NOT start their session by reading every pipeline and protocol file — that is lazy-loaded
- The incoming check is part of the boot sequence and runs before any other dept work

## References

- Dept boot sequence: `core/runbooks/dept-boot-sequence.md`
- Dept-Coord protocol: `core/runbooks/dept-coord-protocol.md`
- Parallel: `/pd-resume` for project directors, `/dept-status` for read-only check
