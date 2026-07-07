# Agents Archive Manifest

Deprecated/retired agent definitions live here, **outside** `agents/` (top-level
sibling directory). Claude Code registers agent rosters recursively under
`agents/` — keeping archived defs there means they're still injected into
every session's roster, defeating the purpose of archiving them.

## Restore-Beats-Create Rule

Before creating a new agent definition for a task, check this manifest first.
If a matching archived def exists, restore it (move back to the correct
`agents/{department}/` path) rather than authoring a new one from scratch.

## Archived Agents

(none yet — this manifest is created empty as part of the 2026-07-07
token-efficiency sync; populate as agents are retired)
