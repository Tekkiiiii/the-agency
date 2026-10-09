# Specialized — PD home and service agents

This folder is a home for Project Director (PD) agent definitions plus the agency's service agents. The department layer (department heads and department coordinators) was sunset 2026-10-08: routing is PD -> Coord -> general-purpose Exec (spawner picks model + skills); critics (`critique-*`) are spawned directly by the PD or Coord. Role-to-skills map for archived specialists: `{agency-root}/agents-archive/ROLE-MAP.md`. Archived dept files (including the audit and infra sub-team indexes): `{agency-root}/agents-archive/dept-sunset-2026-10-08/` (see `{agency-root}/agents-archive/MANIFEST.md`).

## Members

Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md. Rows below are the agents still registered.

| Agent | What it does |
|---|---|
| Example Project PD | Project Director for a specific product/app — one PD is spawned per active project via `/new-project` (see Project Scaffolder) |
| Delegator | Routing agent: knows the agents, skills, protocols and pipelines; guides a caller to the right agent and skills. Read-only |
| Curator | Project knowledge retrieval across memory files and research notebooks. Read-only |
| Save-State Runner | One-project save-state reconstructor for subagent mode (`/save-state all`, crash recovery) |
| Project Scaffolder | Autonomous project + PD scaffolding agent — creates all files and registries for /new-project |
| Codebase Search | Fast read-only file/symbol search across {agency-root}/, projects, and skill library — replaces Explore for system searches |
| Overseer PD | Meta-overseer PD — monitors all other PDs, reads heartbeat/next-session/dept-state files, flags STALE (>3 days) and BLOCKED, ships daily digest. Reports only — no auto-poke. |

## Understand-Anything Sub-team

Code comprehension agents from the Understand-Anything tool (`~/.claude/tools/understand-anything/`). Invoked by `/understand-*` skills — not spawned directly. Listed here so Delegator can route comprehension tasks correctly.

| Agent | What it does |
|---|---|
| understand-architecture-analyzer | Analyzes file structure, imports, and summaries to identify logical architectural layers |
| understand-domain-analyzer | Extracts business domain knowledge, maps how business logic flows through code |
| understand-file-analyzer | Analyzes source file batches to produce knowledge graph nodes and edges |
| understand-graph-reviewer | Validates knowledge graphs for correctness, completeness, and quality |
| understand-knowledge-graph-guide | Guides users through querying and interpreting knowledge graphs |
| understand-project-scanner | Scans codebase directory to produce structured file inventory with languages and frameworks |
| understand-tour-builder | Designs guided learning tours through codebases (5-15 pedagogical steps) |
| understand-assemble-reviewer | Reviews merged batch graphs for semantic issues |
| understand-article-analyzer | Analyzes markdown/wiki files to extract knowledge graph nodes and edges |

**Route via skills:** Use `/understand-*` skills (see `~/.claude/memory/skill-triggers.md`) — they invoke these agents internally. Do NOT spawn these agents directly.

## Parent Directory

[← Agency Directory](../INDEX.md)
