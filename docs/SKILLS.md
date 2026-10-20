# Skills Guide

Skills are reusable workflows that agents invoke to handle common tasks. Each skill is a SKILL.md file in the `skills/` directory.

## Overview

235+ skills are installed to `{agency-root}/skills/` as `{name}/SKILL.md` directories. Invoke any skill with `/skill-name` in Claude Code.

## Skill Categories

### Memory & Session

| Skill | What it does | When to use |
|---|---|---|
| `save-state` | Persist session to memory files — next-session.md, logs, heartbeat | End of every project session |
| `recall` | Load project briefing from save-state files | Start of every project session |
| `pd-resume` | Resume one or all PDs — parallel recall + spawn | Resume project work |
| `wrap` | Freeze inbox task session — archive, write logs | End of inbox session |
| `unwrap` | Resume inbox tasks — briefing + spawn task workers | Start inbox session |

```
/save-state taskboard
/recall taskboard
/pd-resume all
```

### Multi-Stage Pipelines

End-to-end automated workflows with quality gates between stages.

| Skill | Stages | When to use |
|---|---|---|
| `pipeline-feature` | plan → execute → critique → review → QA → ship → deploy | Full feature development |
| `pipeline-bugfix` | investigate → fix → critique → QA → ship | Fix a bug with discipline |
| `pipeline-content` | research → strategy → create → critique → humanize → knowledge | Any written content |
| `pipeline-audit` | parallel critiques → aggregate → QA → report | Pre-launch or periodic audit |
| `pipeline-deploy` | security → baseline → deploy → canary + benchmark | Safe deployment |
| `pipeline-seo-geo-aeo` | audit → optimise for search, generative and answer engines | Search visibility work |

```
/pipeline-feature "add user auth with JWT"
/pipeline-bugfix "login fails on mobile Safari"
/pipeline-content topic="AI agents" type="blog" audience="developers"
/pipeline-audit scope=full url=https://myapp.com
/pipeline-deploy target=railway production-url=https://myapp.com
```

A pipeline chains skills with a gate between stages. `/pipeline-content "How AI agents handle memory"` runs research, draft, a critique gate, a humanize pass, then knowledge capture.

### Critique Skills

Structured reviews by senior domain experts. Each produces an A-F grade with severity-tiered findings. Run standalone or as part of a pipeline.

| Skill | Expert Role | Dimensions |
|---|---|---|
| `backend-critique` | Senior backend engineer | Correctness, API design, DB, security, errors, performance, observability, maintainability |
| `security-critique` | App security engineer | Auth/authz, injection, data exposure, secrets, dependencies, CI/CD, business logic, config |
| `design-critique` | UX/product designer | Hierarchy, visual clarity, layout, interaction, accessibility, typography, components, mobile |
| `content-critique` | Content strategist | Clarity, accuracy, tone, structure, SEO/value, consistency |
| `marketing-critique` | Performance marketer | Offer, targeting, message match, CTA, conversion, channel fit, measurement |
| `operations-critique` | DevOps/platform engineer | Pipeline, deployment safety, infra efficiency, observability, incident response, security, cost |
| `product-critique` | Senior PM | Problem clarity, user fit, solution, GTM, competitive, metrics, feasibility |
| `workflow-critique` | Workflow engineer | Step logic, error handling, handoffs, observability, efficiency, scalability, failure recovery |

All critique skills:
- Grade A-F (A = ship it, F = don't ship)
- Flag Critical / High / Medium / Low issues
- Cite exact file:line or specific location for every finding
- Never rewrite — critique only

```
/backend-critique
/security-critique
/content-critique
/design-critique [figma-url or screenshot]
```

### Planning & Review

| Skill | What it does | When to use |
|---|---|---|
| `autoplan` | Full plan review pipeline: CEO → design → eng | Before starting any feature |
| `plan-ceo-review` | Founder/CEO perspective on a plan | Strategy and scope review |
| `plan-eng-review` | Engineering architecture review | Technical plan validation |
| `review` | Code review — structure, scope drift, tests, adversarial | Before shipping code |
| `investigate` | Systematic root-cause debugging — 3-strike rule | Something is broken |
| `retro` | Structured retrospective — git history, wins/losses | Weekly or sprint close |

```
/autoplan
/review
/investigate "auth fails for users with special characters in email"
```

### Research

| Skill | What it does | When to use |
|---|---|---|
| `auto-researcher` | Proactive research — search, synthesize, present with sources and confidence levels | Any topic needing current information |
| `content-strategy` | Editorial calendars, content pillars, TOFU/MOFU/BOFU funnel planning | Building a content strategy |

```
/auto-researcher "latest developments in AI agent memory"
/content-strategy
```

### Quality & Shipping

| Skill | What it does |
|---|---|
| `ship` | Automated ship: merge → test → review → PR |
| `qa` | Iterative QA testing and bug fixing |
| `qa-only` | Report-only QA (no fixes) |
| `canary` | Post-deploy monitoring loop |
| `land-and-deploy` | Merge PR → deploy → canary verify |

```
/ship
/qa https://localhost:3000
/qa-only http://localhost:3000
```

### Content & Writing

| Skill | What it does |
|---|---|
| `humanizer` | Remove AI-writing patterns from text |
| `proofreader` | Proofread for typos, grammar, clarity |
| `content-polish` | Humanizer → anti-fragmentation → proofreader in sequence (EN) / humanizer-vi → grammar-checker-vi (VN) |
| `content-creator` | 14 copywriting formulas, 18 psychology effects, 10 NLP techniques |
| `content-strategy` | Editorial calendars, pillars, funnel planning |
| `copywriting` | Conversion-focused copy for any medium |
| `tech-writer` | Developer docs, API references, tutorials, ADRs |
| `stop-slop` | Detect and remove AI filler phrases, jargon |

```
/content-polish
/content-creator type=landing-page audience=developers
/humanizer
```

### Coordination and Planning Extras

| Skill | What it does |
|---|---|
| `swarm` | One-shot status check across all projects |
| `delegate`, `pd-spawn`, `task-handoff` | Hand work to an agent, spawn a PD, hand a task over |
| `task-store`, `nexus-gatekeeper`, `sync-md-json` | Task pipeline, NEXUS gate checks, markdown/JSON sync |
| `plan-design-review`, `plan-devex-review`, `plan-tune`, `office-hours`, `seed`, `project-expansion-scout` | Further planning and review passes |

### Engineering, Design and Operations

The full categorized registry is [`skills/INDEX.md`](../skills/INDEX.md). By domain:

- **Backend**: `backend`, `security`, `webhook-security`, `postgresql-schema`, `supabase-sql`, `multi-role-auth`, `laravel-builder`, `admin-shell-foundation`
- **Frontend**: `frontend`, `shadcn-ui`, `cult-ui`, `tailwind`, `next-best-practices`, `css-animations`, `image-to-code`, `svgl`, `extract-design`, `excalidraw-diagram`
- **Design and UI/UX**: `ui-ux-pro-max`, `impeccable`, `design-html`, `high-end-visual-design`, `minimalist-ui`, `industrial-brutalist-ui`, `emil-design-eng`, `gpt-taste`, `brandkit`, `figma-ui-ux-consistency`
- **Video and media**: `ffmpeg`, `video-use`, `hyperframes`, `hyperframes-cli`, `hyperframes-media`, `remotion-best-practices`, `lottie`, `animejs`, `gsap`, `waapi`, `three`, `gpt-image-prompts`, `imagegen-frontend-web`, `imagegen-frontend-mobile`
- **Deployment**: `github-deploy`, `vercel-deploy`, `railway-deploy`, `supabase-deploy`
- **Cloud and infrastructure**: `agents-sdk`, `refactor-module`, `finops`
- **Ops and debugging**: `self-healing`, `investigate`, `guard`, `health`, `web-perf`, `webapp-testing`
- **Browser and scraping**: `browse`, `agent-browser`, `lightpanda`, `scrape`, `firecrawl-agent`, `firecrawl-crawl`, `firecrawl-scrape`, `pair-agent`
- **Quality and critique extras**: `design-review`, `codex`, `cso`, `document-release`, `devex-review`, `careful`, `run-acceptance-tests`
- **Content and document extras**: `marp`, `markitdown`, `make-pdf`, `xlsx-toolkit`, `vietnamese-language`, `promt-engineering`
- **Workflow (14 `superpowers-*` skills)**: `superpowers-brainstorming`, `superpowers-systematic-debugging`, `superpowers-dispatching-parallel-agents`, `superpowers-executing-plans`, `superpowers-writing-plans`, `superpowers-test-driven-development`, and the rest of the family
- **Domain-specific**: `better-auth-best-practices`, `legal-contract-review`, `n8n-automation`, `sanity-best-practices`, `tech-stack`

## Installing Skills

All skills are installed with the agency setup:

```bash
bash install.sh        # Windows: .\install.ps1
```

Or install a single skill:

```bash
agency skill install save-state
```

## Skill Invocation

In Claude Code, type `/skill-name` to invoke:

```
/save-state taskboard
/pipeline-feature "add search functionality"
/security-critique
/swarm
```

## Creating Custom Skills

See [Developer Guide](DEVELOPER.md#adding-a-skill) for how to create a new skill.

Each skill needs at minimum a `SKILL.md` file with:
- `name:` — the invocation slug
- `description:` — when to use this skill
- Core behavior: purpose, trigger conditions, key steps, output format

## Skill Router (optional, off by default)

`scripts/skill-route.py` can pick 1-3 skills for a task text, plus a model tier and a tool profile, through the Jev routing service with a Haiku and a local grep fallback. **It is off.** Nothing calls it, it makes no network request while off, and routing stays "pick 1-3 skills from `skills/INDEX.md`". The Agency ships no key.

With it on, spawners run it before each spawn and put a `Jev[r=<route_id>]: accept|modify|reject — <reason>` line in the spawn prompt (rules JB1-JB9 in `runbooks/service-lookups.md`, section Routing); with it off there is no such line. The Jev spawn gate that can deny a spawn missing that line ships disabled too: the `spawn-ledger` mod calls `scripts/jev-spawn-gate.py` only when `AGENCY_SKILL_ROUTER=1` (see [MODS.md](MODS.md)).

To enable it, get your own key, put `TYPESAFE_API_KEY=...` in `~/.config/typesafe/.env`, set `AGENCY_SKILL_ROUTER=1` (the `env` block of `settings.json` works), and rebuild the menu with `skill-route.py --rebuild-menu`. Exact steps for macOS, Linux and Windows, the output contract, fallback and cost logging: [`scripts/skill-route/README.md`](../scripts/skill-route/README.md).

## Effort Policy

On by default. The `effort` section of `hooks/lib/exec-model-map.json` sets the reasoning effort of each subagent by task type:

| Task type | Effort |
|---|---|
| Project Director | medium |
| Complex coding | high |
| Routine coding | medium |
| Visual work | high |
| English content | high |
| Vietnamese content | xhigh |
| Everything else | medium |
| Lookups | low |

The `spawn-ledger` mod enforces it on every request of the subagent, so it overrides the caller's `effort` param and an agent file's `effort:` line. With the skill router off there is no Jev line, so `general-purpose` spawns get `medium` unless the prompt carries `MODEL-CATEGORY: <name>`; PDs and the named agents classify without the router. Kill switches: `EFFORT_POLICY_OFF=1`, `state/effort-policy.off`, `effort.enabled: false`. Ledger rows and details: [`mods/README.md`](../mods/README.md). Windows: CI unit and TS tests only; the live `turn.step` relay is unproven on a real Windows session.

## Skill Priority

Skills loaded from `{agency-root}/skills/` override any built-in behaviors. If multiple skills match a trigger, the most specific one wins.
