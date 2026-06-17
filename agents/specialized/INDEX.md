# Specialized Department

**Call this department when you need something that doesn't fit elsewhere** — agent infrastructure (GitNexus, identity/trust, LSP indexing), financial and compliance audits (SOC 2, blockchain, ML models), data extraction from Excel, live sales dashboards, knowledge-base management (ZK/Zettelkasten), cultural intelligence, CLI harness engineering, and autonomous project expansion scanning.

**Leader**: Agents Orchestrator
**Sub-teams**: infra | audit — see below
**Model tier**: Members = Sonnet, Leaders = Opus

## Members

| Agent | What it does |
|---|---|
| Agents Orchestrator | Pipeline manager, agent orchestration, cross-agent workflows |
| Efficiency Advisor Loop | Scans active projects for efficiency opportunities |
| PD Status Loop | 2-hour PD heartbeat ping + digest aggregation |
| Project Expansion Scout | Scans for expansion opportunities, BOD approval workflow |
| Sales Data Extraction Agent | Monitors Excel files, extracts MTD/YTD/Year End sales metrics |
| Data Consolidation Agent | Builds live sales dashboards from extracted data |
| Report Distribution Agent | Distributes reports to reps by territory |
| Cultural Intelligence Strategist | Detects exclusion, global context research, authentic resonance |
| Developer Advocate | Community building, DX optimization, technical content |
| ZK Steward | Niklas Luhmann Zettelkasten, atomic notes, cross-domain decisions |
| Task Planner | Breaks down complex tasks into actionable implementation plans |
| CLI-Anything Agent | Transforms any GUI app into agent-usable CLI harness via 7-phase pipeline (Blender, GIMP, LibreOffice, Inkscape, Shotcut, OBS, Audacity, etc.) |
| MarketSenseApp PD | Project Director for MarketSenseApp — Vietnamese financial news RSS + Ollama Tauri app |
| Amani CRM PD | Project Director for Amani CRM — inventory/production management CRM (Next.js + FastAPI) |
| ltv PD | Project Director for LTV school fees management app (Tauri 2 + Rust + React 19) |
| Accounts Payable Agent | Vendor payments, contractor invoices, multi-rail (crypto/fiat/stablecoins) |
| Vietnamese Text Agent | Vietnamese text → URL slugs and markdown-safe formats via correct Unicode NFD decomposition |
| Paperclip Control Plane | Zero-human company orchestration via Paperclip — manages agent workforce, org charts, heartbeats, budgets, and governance. The 2nd in command under you. |
| Task-Executor | Leaf implementation agent — executes exactly what Coord assigns, no decomposition authority, Sonnet model |
| Integration-Tester | Phase B cross-L3 system integration QA. Spawned by PD after all per-L3 Coord QA gates pass. Tests that multiple L3 outputs work together as a system — contract verification, cross-L3 dependency resolution, integration smoke tests. Reports INTEGRATION_PASS/WARN/FAIL to PD. |
| Project Scaffolder | Autonomous project + PD scaffolding agent — creates all files and registries for /new-project |
| Codebase Search | Fast read-only file/symbol search across {agency-root}/, projects, and skill library — replaces Explore for system searches |
| Web Extraction Agent | Routes web data-extraction and crawling tasks to the right tool based on task type — Lightpanda (default), Firecrawl (bulk/scale), Playwright (visual/interaction/login), social decision ladder (API → Apify → session → FLAG) |
| Morpheus PD | Meta-overseer PD — monitors all other PDs, reads heartbeat/next-session/dept-state files, flags STALE (>3 days) and BLOCKED, ships daily digest. Reports only — no auto-poke. |

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
| Agents Orchestrator | (shared with parent) — pipeline management |
| Identity Graph Operator | Canonical entity resolution across agents |
| Agentic Identity & Trust Architect | Agent authentication, authorization, audit trails |
| LSP/Index Engineer | LSP client orchestration, semantic indexing |

## Audit Sub-team

See [audit/INDEX.md](audit/INDEX.md) — compliance, blockchain, ML model audits.

| Agent | What it does |
|---|---|
| Compliance Auditor | SOC 2, ISO 27001, HIPAA, PCI-DSS readiness |
| Blockchain Security Auditor | Smart contract vulnerabilities, formal verification |
| Model QA Specialist | ML/statistical model end-to-end audit, calibration, interpretability |

## Parent Directory

[← Agency Directory](../INDEX.md)
