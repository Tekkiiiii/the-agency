---
# do not read unless explicitly requested
# Full agent selection reference — loaded only when spawning subagents
---

# Agency Agent Selection Hierarchy

When spawning a subagent, follow this order — **general-purpose is last resort**:

## Step 0 — Check protocols first

Before matching agents or skills, check if an active protocol governs the task:

| Task pattern | Protocol | File |
|---|---|---|
| Content production (blog, email, ad, social, video script) | content-request | `agents/content-creation/protocols/content-request.md` |
| Marketing→Content handoff (strategic brief → artifact) | marketing-content-handoff | `agents/marketing/protocols/marketing-content-handoff.md` |
| Quality gate for any creative or code deliverable | quality-loop | `runbooks/quality-loop-protocol.md` |
| Cross-dept work not listed above | Check protocol-registry | `runbooks/protocol-registry.md` |
| Escalation, conflict, authority dispute | escalation-protocol | `runbooks/escalation-protocol.md` |
| Department initiative execution (D1→D6) | dept-coord-protocol | `runbooks/dept-coord-protocol.md` |

If a protocol matches → route through the protocol's owning department. Skills and agents are dispatched **within** the protocol flow, not instead of it.

## Step 0.5 — Spawn Delegator FIRST (mandatory, before using the table below)

**The Delegator is mandatory before any agent spawn.** Do NOT use the Step 1 table to self-route — use it only as a reference when briefing the Delegator or when applying the fast-path (see Step 1.5).

Spawn the Delegator (`~/.claude/agents/specialized/delegator.md`, sonnet). It reads the full agency catalog, org chart, protocol registry, and skill index, and returns a structured routing recommendation. It is a one-shot service agent — spawn, get answer, it dies.

Exceptions (Delegator NOT required): PD spawns via /pd-resume or /pd-spawn, Curator spawns, codebase-search spawns.

## Step 1 — Agency catalog reference (use with Delegator, or for fast-path only)

| Task domain | Prefer this agent type |
|---|---|
| Research, analysis, investigation | `Explore`, `Trend Researcher`, `research-pd` |
| Frontend, UI, design | `Frontend Developer`, `UI Designer`, `Design Lead` |
| Backend, API, database | `Backend Architect`, `Data Engineer` |
| Full-stack / feature work | `Senior Developer`, domain-specific PD |
| Sales, pipeline, revenue | `Sales Lead`, `Deal Strategist`, `Account Strategist` |
| Content creation, writing, copy, editorial, scripts, docs, decks | `Chief Content Officer`, `content-creation-lead` |
| Marketing strategy, growth experiments, social media engagement, SEO, China market | `Marketing Lead`, `Growth Hacker` |
| Operations, tracking, finance | `Operations Lead`, `Finance Tracker`, `Analytics Reporter` |
| Security, compliance, legal | `Security Engineer`, `Compliance Auditor` |
| Deployment, DevOps, infra | `DevOps Automator`, `Infrastructure Maintainer` |
| QA, testing, verification | `Testing Lead`, `Evidence Collector`, `qa` skill |
| Experiment design, A/B | `Experiment Tracker` |
| Proposal, RFP, deal | `Proposal Strategist`, `Deal Strategist` |
| Game dev | `Game Development Lead` |
| Spatial/VR/AR | `Spatial Computing Lead` |
| Knowledge retrieval, project context, history lookup | `curator` |
| Voice cloning, TTS, voice generation, text-to-speech, dubbing, voice design | `Voice & Cast Director` (`video-studio/vs-voice-director.md`) via OmniVoice Studio (default tool) — MCP: `mcp__omnivoice__generate_speech` |
| Video editing, transcription, color grade, subtitles, overlays, raw footage | `/video-use` skill (default), `content-creation-lead` for strategy |
| Video production (scripted, AI-generated, full pipeline) | Video Studio dept — `video-studio-lead` for strategy, `video-studio-coord` for production coordination |
| Quality gate for any creative deliverable | `quality-loop-router` skill — always the terminal step; determines Mode A (internal loop) or Mode B (external fix plan) |
| Code quality review (non-security) | `critique-code` agent or skill |
| Data/analytics/dashboard critique | `critique-data` agent or skill |
| Video deliverable critique | `critique-video` agent or skill |
| New project onboarding / tech stack decision | `pipeline-onboard` skill → `tech-stack` skill |
| Research task (multi-source synthesis) | `pipeline-research` skill → auto-researcher → firecrawl → graphify → notebooklm |
| Web scraping, crawling, data extraction from URLs | `Web Extraction Agent` (`specialized/web-extraction-agent.md`) — 3-layer routing + social ladder |
| Social media content extraction (FB/IG/LinkedIn/X/TikTok/YouTube/Reddit) | `Web Extraction Agent` — runs social decision ladder (API → Apify → session → FLAG) |
| Messaging platform read/write (TG/Discord/Slack/WA/Signal/Matrix) | `mcp__hermes__*` tools directly — no Web Extraction Agent needed |

## Cross-Department Protocol: Marketing ↔ Content Creation

Marketing owns **strategy** (what, who, when, where, why). Content Creation owns **execution** (the written artifact).
- Content production tasks → Content Creation (CCO receives strategic brief from Marketing)
- Content strategy, audience targeting, distribution, performance → Marketing
- Marketing briefs Content Creation → Content Creation produces → Marketing distributes → Marketing feeds back performance data → Content Creation optimizes

## Step 1.5 — Fast-path (rare exception — Delegator already handled in Step 0.5)

The Delegator was already made mandatory in Step 0.5. This section defines the ONLY pre-approved spawns that bypass Delegator. All other spawns require Delegator first.

**Pre-approved spawns** (no Delegator needed — these agents ARE the routing infrastructure):

| subagent_type | When allowed |
|---|---|
| `pd-coordinator` | PD spawns via /pd-resume or /pd-spawn only |
| `coord` | Spawned by a PD as part of PD-Coord architecture |
| `mini-coord` | Spawned by a Coord as part of PD-Coord architecture |
| `task-executor` | Spawned by a Coord as part of PD-Coord architecture |
| `curator` | Any session — mandatory service agent, spawn freely |
| `codebase-search` | Any session — mandatory service agent, spawn freely |
| `Delegator` | Any session — this IS Delegator |
| `Explore` | Read-only research (no writes, no agent spawns from within) |
| `Plan` | Planning mode (no writes, no agent spawns from within) |
| `statusline-setup` | System setup only |
| `general-purpose` | Only when prompt starts with "You are PD-" OR contains "DELEGATOR ROUTING:" block |

**All other agent spawns** require a `DELEGATOR ROUTING:` block in the prompt proving Delegator was consulted. The spawn-gate.sh hook enforces this at runtime.

Even for Explore and Plan: if you are unsure whether the task needs specialized domain knowledge, spawn Delegator first.

## Step 2 — Route to existing specialized agents before general-purpose.
Use `Explore` for research, domain-specific agents for domain work.

## Step 3 — Fallback is general-purpose.
Only use `general-purpose` when the task is truly generic and no catalog agent matches.