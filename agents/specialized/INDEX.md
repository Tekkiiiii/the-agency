# Specialized Department

**Call this department when you need something that doesn't fit elsewhere** — agent infrastructure (GitNexus, identity/trust, LSP indexing), financial and compliance audits (SOC 2, ML models), data extraction from Excel, live sales dashboards, knowledge-base management (ZK/Zettelkasten), cultural intelligence, CLI harness engineering, and autonomous project expansion scanning.

**Leader**: Specialized Agents Lead
**Sub-teams**: infra | audit — see below
**Model tier**: Members = Sonnet, Leaders = Opus

## Members

Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md. Rows below are the agents still registered.

| Agent | What it does |
|---|---|
| Example Project PD | Project Director for a specific product/app — one PD is spawned per active project via `/new-project` (see Project Scaffolder) |
| Task-Executor | Leaf implementation agent — executes exactly what Coord assigns, no decomposition authority, Sonnet model |
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

## Infra Sub-team

See [infra/INDEX.md](infra/INDEX.md) — agent lifecycle, identity/trust, code intelligence.

| Agent | What it does |
|---|---|

## Audit Sub-team

See [audit/INDEX.md](audit/INDEX.md) — compliance and ML model audits.

## Parent Directory

[← Agency Directory](../INDEX.md)
