# The Agency Memory System

The Agency has three memory layers — short-term, medium-term, and long-term. Every agent reads from and writes to this system.

## Short-Term Memory: Session Logs

Location: `~/.claude/sessions/{project}/`

Created: at the start of every session
Read by: the spawned agent on resume
Written by: the agent during session via `/save-state`
Format: freeform markdown, but structured sections encouraged

## Medium-Term Memory: Project State

Location: `~/.claude/projects/{project}/STATE.md`

Created: when a project is first registered
Read by: PD on spawn, team-lead on review
Written by: PD continuously
Contains: current phase, open blockers, metrics, next-session prompt

## Long-Term Memory: Lessons

Location: `~/.claude/lessons/{stack}.md`

Created: after any correction or significant decision
Read by: any agent on spawn
Format: root-cause → lesson → avoid pattern
Rules:
- Append only — never edit history
- One entry per lesson
- Cross-reference other lesson files with `→ see {stack}`

## Cross-Project Memory: Decisions

Location: `~/.claude/decisions/`

Created: when a cross-cutting architectural decision is made
Read by: team-lead, any agent needing context
Format: one file per decision

## Memory Initialization

On first run, `agency init` creates:
```
~/.claude/
├── sessions/
├── projects/
├── lessons/
├── decisions/
└── memory/
```

Do NOT create content in these directories — only the directory structure.
