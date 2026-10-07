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

### 2026-10-06 - Generalist switch ACTIVE (specialists -> general-purpose + skills)

Specialist agents moved to `agents-archive/generalist-2026-10-06/<dept>/` under
their old relative path (including depth-3 folders such as
`content-creation/social-media/`, `specialized/audit/`, `specialized/infra/`), so
each restore is one move. Archived specialists are NOT spawnable agent types.
Spawn `general-purpose`, name 1-3 skills, and optionally point the agent at its
role file. The role -> skills table is `agents-archive/ROLE-MAP.md` (single
source of truth for spawners). Role files and the role map are runtime reading,
so installs copy `agents-archive/` to `{agency-root}/agents-archive/` (never under
`agents/`, so nothing registers).

Kept registered (structural): all `*-pd`, pd-coordinator, coord, mini-coord,
task-executor, the dept-coords, the dept leads (they spawn the dept-coords),
critique-* + sag-critique + Critiques Lead, Delegator, curator, codebase-search,
save-state-runner, project-scaffolder, and the understand-* workers (the
/understand skills spawn them by type). `qa-task-contract` was a contract doc,
not an agent: it is now `runbooks/qa-task-contract.md`.

**Restore one:** `mv {agency-root}/agents-archive/generalist-2026-10-06/<dept>/<file>.md {agency-root}/agents/<dept>/`
(use `git mv` inside a git checkout)
**Restore all:** `cd {agency-root} && for d in agents-archive/generalist-2026-10-06/*/; do mv "$d"* "agents/$(basename "$d")/"; done`
Then re-point the rows that `ROLE-MAP.md` lists back to the agent name. New
registration takes effect next session.
