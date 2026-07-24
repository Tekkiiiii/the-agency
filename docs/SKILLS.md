# Skills Guide

Skills are reusable workflows that agents invoke to handle common tasks. Each skill is a SKILL.md file in the `skills/` directory.

## Overview

185+ skills are installed to `{agency-root}/skills/` as `{name}/SKILL.md` directories. Invoke any skill with `/skill-name` in Claude Code.

## Skill Categories

### Department Lifecycle

Manage department head sessions — resume, save, and check status without spawning subagents.

| Skill | What it does | When to use |
|---|---|---|
| `dept-resume` | Resume department head sessions — reads dept-state.md, spawns dept heads with lean briefings | Start of session for one or all departments |
| `dept-save-state` | Freeze department state at session end — writes dept-state.md, updates rosters, archives scratch | End of department session |
| `dept-status` | Quick read-only status check — reads state files, returns compact digest | Check what a department is working on |

```
/dept-resume all
/dept-resume engineering
/dept-save-state marketing
/dept-status all
```

### Memory & Session

| Skill | What it does | When to use |
|---|---|---|
| `save-state` | Persist session to memory files — next-session.md, logs, heartbeat | End of every project session |
| `recall` | Load project briefing from save-state files | Start of every project session |
| `pd-resume` | Resume one or all PDs — parallel recall + spawn | Resume project work |
| `wrap` | Freeze inbox task session — archive, write logs | End of inbox session |
| `unwrap` | Resume inbox tasks — briefing + spawn task workers | Start inbox session |

```
/save-state my-project
/recall my-project
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

```
/pipeline-feature "add user auth with JWT"
/pipeline-bugfix "login fails on mobile Safari"
/pipeline-content topic="AI agents" type="blog" audience="developers"
/pipeline-audit scope=full url=https://myapp.com
/pipeline-deploy target=railway production-url=https://myapp.com
```

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
/qa-only https://my-staging.app
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

### Engineering

See `skills/INDEX.md` for the full engineering skills catalog, including:

- **Backend**: `backend`, `security`, `webhook-security`, `postgresql-schema`, `supabase-sql`, `neon-postgres`
- **Frontend**: `frontend`, `shadcn-ui`, `tailwind`, `next-best-practices`, `cult-ui`
- **Design**: `ui-ux-pro-max`, `impeccable`, `design-consultation`, `high-end-visual-design`
- **AI/ML**: `sandbox-sdk`, `agents-sdk`, `mcp-builder`, `graphify`
- **Deployment**: `vercel-deploy`, `railway-deploy`, `netlify-deploy`, `github-deploy`
- **Cloudflare**: `cloudflare`, `workers-best-practices`, `wrangler`, `durable-objects`
- **Netlify**: `netlify-config`, `netlify-functions`, `netlify-edge-functions`, `netlify-db`
- **Terraform**: `terraform-style-guide`, `terraform-stacks`, `new-terraform-provider`

## Installing Skills

All skills are installed with the agency setup:

```bash
curl -fsSL https://github.com/Tekkiiiii/the-agency/raw/main/install | bash
```

Or install a single skill:

```bash
agency skill install dept-resume
```

## Skill Invocation

In Claude Code, type `/skill-name` to invoke:

```
/save-state my-project
/pipeline-feature "add search functionality"
/security-critique
/dept-status all
```

## Creating Custom Skills

See [Developer Guide](DEVELOPER.md#adding-a-skill) for how to create a new skill.

Each skill needs at minimum a `SKILL.md` file with:
- `name:` — the invocation slug
- `description:` — when to use this skill
- Core behavior: purpose, trigger conditions, key steps, output format

## Skill Priority

Skills loaded from `{agency-root}/skills/` override any built-in behaviors. If multiple skills match a trigger, the most specific one wins.
