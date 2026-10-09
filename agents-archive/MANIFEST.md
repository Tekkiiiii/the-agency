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

## retired-2026-10-08
- task-executor.md (+ core-task-executor.md mirror copy): retired (REV004 D5). Execs = general-purpose + Skills; spawn template = agents/project-management/coord.md "Exec spawn message". Not spawnable.

## dept-sunset-2026-10-08
Department sunset (2026-10-08): the 8 department leads and 7 department coordinators (15 agent files) are archived, plus the dept data files that shipped in `agents/<dept>/`. Routing is now PD -> Coord -> general-purpose Exec; critics (`critique-*`, `sag-critique`) are spawned directly by the PD or Coord. Nothing deleted. Role-to-skills replacement rows: `ROLE-MAP.md` ("Department sunset 2026-10-08").

| Archived (now in `agents-archive/dept-sunset-2026-10-08/`) | Was |
|---|---|
| `<dept>/<dept>-lead.md` x8 | content-creation, critiques, design, engineering, project-management, specialized, testing, video-studio |
| `<dept>/<dept>-coord.md` x7 | content-creation, design, engineering, project-management, specialized, testing, video-studio |
| `content-creation/protocols/content-request.md`, `content-creation/protocols/INDEX.md` | dept content-request protocol; folded into `runbooks/content-request-protocol.md` v2.0.0 (PD -> Coord -> writer -> /content-polish -> critics via /cc-loop) |
| `content-creation/social-media/INDEX.md`, `specialized/audit/INDEX.md`, `specialized/infra/INDEX.md` | sub-team indexes |
| `ORG.md.pre-sunset` | `agents/ORG.md` before the rewrite (byte-identical to the pre-sunset file) |
| `runbooks/` + `core/runbooks/` (same 5 names in each) | `dept-coord-protocol.md`, `department-lead-protocol.md`, `department-lead-template.md`, `dept-boot-sequence.md`, `protocol-registry.md` (citers repointed to `runbooks/quality-loop-protocol.md`) |
| `skills/dept-resume/`, `skills/dept-save-state/`, `skills/dept-status/`, `skills/dept-wrap/`, `skills/room-manager/`, `skills/room-manager-digest/` | the six dept/room skills; archived under `agents-archive/dept-sunset-2026-10-08/skills/<name>/`, never under `skills/`, because installers copy `skills/` subdirectories wholesale |

Kept in `agents/`: Coord definitions (`coord`, `mini-coord`, `pd-coordinator`), `critique-*` + `sag-critique` (+ `critiques/memory/`, `critiques/INDEX.md`), `council/` (4 seats, added in this wave), service agents (`delegator`, `curator`, `codebase-search`, `save-state-runner`, `project-scaffolder`, `understand-*`), `design/memory/design-quality-principles.md`. The dept folders `agents/<dept>/` stay as PD homes, each with a short `INDEX.md` (the project-scaffolder appends PD rows there). The `agency-rooms/` directory stays. `runbooks/agency-rooms-protocol.md` documents the kept rooms directory (rewritten, not archived).

**Restore all:** `cd {agency-root} && A=agents-archive/dept-sunset-2026-10-08; for d in $A/*/; do n=$(basename "$d"); [ -f "$d$n-lead.md" ] && git mv "$d$n-lead.md" agents/$n/; [ -f "$d$n-coord.md" ] && git mv "$d$n-coord.md" agents/$n/; done`
(data files: `git mv $A/content-creation/protocols agents/content-creation/protocols`, same for `content-creation/social-media`, `specialized/audit`, `specialized/infra`; restore `ORG.md.pre-sunset` over `agents/ORG.md`; skills: `git mv $A/skills/<name> skills/<name>`; runbooks: `git mv $A/runbooks/<file> runbooks/` and `$A/core/runbooks/<file> core/runbooks/`).
Restore one: `git mv {agency-root}/agents-archive/dept-sunset-2026-10-08/<dept>/<dept>-lead.md agents/<dept>/`.
Then re-add the routing rows in `core/memory/agency-dispatch.md`; registration takes effect next session.
