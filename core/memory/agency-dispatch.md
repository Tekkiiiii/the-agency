---
# do not read unless explicitly requested
# Full agent selection reference — loaded only when spawning subagents
---

# Agency Agent Selection Hierarchy

When spawning a subagent, follow this order — since 2026-10-06 (generalist switch ACTIVE) **`general-purpose` + 1-3 skills named in the prompt is the DEFAULT**; specialist roles are archived (`agents-archive/ROLE-MAP.md`):

## Step 0 — Check protocols first

Before matching agents or skills, check if an active protocol governs the task:

| Task pattern | Protocol | File |
|---|---|---|
| Content production (blog, email, ad, social, video script) | content-request | `agents/content-creation/protocols/content-request.md` |
| Quality gate for any creative or code deliverable | quality-loop | `runbooks/quality-loop-protocol.md` |
| Cross-dept work not listed above | Check protocol-registry | `runbooks/protocol-registry.md` |
| Escalation, conflict, authority dispute | escalation-protocol | `runbooks/escalation-protocol.md` |
| Department initiative execution (D1→D6) | dept-coord-protocol | `runbooks/dept-coord-protocol.md` |

If a protocol matches → route through the protocol's owning department. Skills and agents are dispatched **within** the protocol flow, not instead of it.

## Step 0.5 — Lookup-first, Delegator second

**Check `core/memory/delegator-cache.md` for an exact task-pattern match before spawning anything.** Cache hit → use the cached route, skip Delegator, log `delegator_cache_hit`. See `runbooks/service-lookups.md` for the full lookup-first protocol.

No cache hit → spawn the Delegator (`agents/specialized/delegator.md`, haiku). It reads the full agency catalog, org chart, protocol registry, and skill index, and returns a structured routing recommendation. It is a one-shot service agent — spawn, get answer, it dies. Append its answer to the cache and emit `delegator_spawn`.

Exceptions (Delegator NOT required): PD spawns via /pd-resume or /pd-spawn, Curator spawns, codebase-search spawns.

## Step 1 — Agency catalog reference (use with Delegator, or for fast-path only)

| Task domain | Prefer this agent type |
|---|---|
| Research, analysis, investigation | `Explore`, `research-pd` |
| Frontend, UI, design | general-purpose + /frontend, /next-best-practices, /tailwind (role file: agents-archive/generalist-2026-10-06/engineering/engineering-frontend-developer.md); UI: general-purpose + /ui-ux-pro-max, /impeccable (role file: agents-archive/generalist-2026-10-06/design/design-ui-designer.md); `Design Lead` |
| Backend, API, database | general-purpose + /backend, /postgresql-schema, /plan-eng-review (role file: agents-archive/generalist-2026-10-06/engineering/engineering-backend-architect.md); data: + /xlsx-toolkit (role file: agents-archive/generalist-2026-10-06/engineering/engineering-data-engineer.md) |
| Full-stack / feature work, Laravel/PHP stack | general-purpose + /laravel-builder, /review (role file: agents-archive/generalist-2026-10-06/engineering/engineering-senior-developer.md), domain-specific PD |
| Full-stack / feature work, non-Laravel stack (Node.js, Python, bash, docs, etc.) | `coord` (or general-purpose + stack-appropriate skills), domain-specific PD — do NOT use the Laravel/PHP-scoped senior-developer role file on other stacks |
| Content creation, writing, copy, editorial, scripts, docs, decks | `Chief Content Officer`, `content-creation-lead` |
| Security, compliance, legal | general-purpose + /security, /cso (role file: agents-archive/generalist-2026-10-06/engineering/engineering-security-engineer.md; review: `critique-security`); compliance: + /legal-contract-review (role file: agents-archive/generalist-2026-10-06/specialized/audit/compliance-auditor.md) |
| Deployment, DevOps, infra | general-purpose + /pipeline-deploy, /vercel-deploy, /railway-deploy (role file: agents-archive/generalist-2026-10-06/engineering/engineering-devops-automator.md) |
| QA, testing, verification | `Testing Lead`, general-purpose + /qa-only, /browse, /webapp-testing (role file: agents-archive/generalist-2026-10-06/testing/testing-evidence-collector.md), `qa` skill |
| Experiment design, A/B | general-purpose + /content-experimentation-best-practices, /project-status (role file: agents-archive/generalist-2026-10-06/project-management/project-management-experiment-tracker.md) |
| Knowledge retrieval, project context, history lookup | `curator` |
| Task planning, decomposition, DAG structuring, sprint planning | general-purpose + /superpowers-writing-plans (role file: agents-archive/generalist-2026-10-06/specialized/task-planner.md) |
| Voice cloning, TTS, voice generation, text-to-speech, dubbing, voice design | general-purpose (no skill; role file: agents-archive/generalist-2026-10-06/video-studio/vs-voice-director.md) via OmniVoice Studio (default tool) — MCP: `mcp__omnivoice__generate_speech` |
| Video editing, transcription, color grade, subtitles, overlays, raw footage | `/video-use` skill (default), `content-creation-lead` for strategy |
| Video production (scripted, AI-generated, full pipeline) | Video Studio dept — `video-studio-lead` for strategy, `video-studio-coord` for production coordination |
| Quality gate for any creative deliverable | `quality-loop-router` skill — always the terminal step; determines Mode A (internal loop) or Mode B (external fix plan) |
| Code quality review (non-security) | `critique-code` agent or skill |
| Data/analytics/dashboard critique | `critique-data` agent or skill |
| Video deliverable critique | `critique-video` agent or skill |
| New project onboarding / tech stack decision | `pipeline-onboard` skill → `tech-stack` skill |
| Research task (multi-source synthesis) | `pipeline-research` skill → auto-researcher → firecrawl → graphify → notebooklm |
| Web scraping, crawling, data extraction from URLs | general-purpose + /lightpanda, /scrape, /firecrawl-crawl (role file: agents-archive/generalist-2026-10-06/specialized/web-extraction-agent.md) — 3-layer routing + social ladder |
| Social media content extraction (FB/IG/LinkedIn/X/TikTok/YouTube/Reddit) | general-purpose + /lightpanda, /scrape, /firecrawl-crawl (role file above) — runs social decision ladder (API → Apify → session → FLAG) |
| Messaging platform read/write (TG/Discord/Slack/WA/Signal/Matrix) | `mcp__hermes__*` tools directly — no web-extraction spawn needed |

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
| `general-purpose` | DEFAULT since 2026-10-06 — name 1-3 skills (and a role file from ROLE-MAP when the role matters) in the prompt; the spawner picks the skills |

**Other agent types** need a `DELEGATOR ROUTING:` / `HARDCODED ROUTING:` marker in the prompt. spawn-gate.sh asks (never blocks) on an unknown `subagent_type`, which catches typos and stale archived specialist names.

If unsure which skills fit, use `agents-archive/ROLE-MAP.md` / skills/INDEX.md; spawn Delegator only for ambiguous or cross-domain tasks.

## Step 2 — Pick skills from the role map.
Use `Explore` for research; for domain work spawn general-purpose + the skills listed in `agents-archive/ROLE-MAP.md` (role file when expertise matters). Kept named agents (`*-pd`, Coords, critique-*, dept heads) stay spawnable by name.

## Step 3 — general-purpose is the default.
No ROLE-MAP row? general-purpose + the 1-3 skills from `skills/INDEX.md` that fit the task.
