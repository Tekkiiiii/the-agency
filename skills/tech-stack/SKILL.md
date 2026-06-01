---
name: tech-stack
description: >
  Two modes: (1) Tech Stack Advisor — recommend a stack for new projects, grounded in
  team context, scale, and operational reality. (2) Tech Stack Profiler — scan an existing
  project directory and produce a structured tech profile for use by pipeline-onboard,
  Curator agents, and memory systems. Trigger when: the user asks "what tech should I use",
  "which framework", "help me pick a database", "recommend a stack", "what's best for building X?";
  OR when asked to profile, scan, or describe the tech stack of an existing project; OR
  when pipeline-onboard needs a tech profile as its first step. Key capabilities: structured
  recommendation format (recommended stack, alternatives, trade-offs, migration path); project
  scanning (reads package.json, Gemfile, requirements.txt, go.mod, Cargo.toml, CLAUDE.md,
  and source files to detect languages, frameworks, databases, deployment targets); outputs
  a structured TECH_PROFILE.md at {project}/memory/tech-profile.md. Never recommends the
  newest thing without weighing operational cost.
---

# Tech Stack Skill

Two modes. Read the trigger to pick the right one.

**Profiler mode** — triggered when:
- Called from `pipeline-onboard` as Stage 1
- User says "scan the tech stack", "profile this project", "what's the stack here"
- A specific project directory is given

**Advisor mode** — triggered when:
- User asks "what should I use", "recommend a stack", "help me pick"
- No existing project is implied

---

## Profiler Mode — Scan Existing Project

### Step 1: Collect signals

Read these files in parallel (skip missing ones):

- `{project}/package.json` — Node.js: framework, runtime, key deps
- `{project}/Gemfile` or `{project}/Gemfile.lock` — Ruby: gems, Rails version
- `{project}/requirements.txt` or `{project}/pyproject.toml` — Python: packages
- `{project}/go.mod` — Go: module, dependencies
- `{project}/Cargo.toml` — Rust: crates
- `{project}/pom.xml` or `{project}/build.gradle` — Java/Kotlin
- `{project}/CLAUDE.md` — project-specific conventions, deploy commands, test commands
- `{project}/README.md` — overview, badges, setup instructions
- `{project}/.env.example` or `{project}/.env.template` — env var names reveal services
- `{project}/docker-compose.yml` — services: databases, caches, queues
- `{project}/vercel.json`, `{project}/railway.toml`, `{project}/fly.toml` — deploy target
- `{project}/supabase/config.toml` — Supabase project
- `{project}/.github/workflows/*.yml` — CI/CD stack

Also scan directory structure for signals:
```bash
ls {project}/
ls {project}/src/ 2>/dev/null || true
ls {project}/app/ 2>/dev/null || true
```

### Step 2: Classify the stack

From collected signals, determine:

**Language(s):** TypeScript / JavaScript / Python / Ruby / Go / Rust / Java / other

**Frontend framework:** Next.js / Nuxt / SvelteKit / Remix / CRA / Vite+React / Vue / none

**Backend framework:** Express / Fastify / Hono / FastAPI / Rails / Sinatra / Gin / Echo / none

**Database:** PostgreSQL / MySQL / SQLite / MongoDB / Redis / Supabase / PlanetScale / Neon / other

**ORM/Query layer:** Prisma / Drizzle / Sequelize / TypeORM / ActiveRecord / SQLAlchemy / none

**Auth:** better-auth / NextAuth / Clerk / Supabase Auth / Passport / Devise / custom / none

**Styling:** Tailwind / CSS Modules / styled-components / Sass / none

**UI library:** shadcn/ui / Radix / Material UI / Ant Design / none

**Deployment:** Vercel / Railway / Fly.io / Render / AWS / GCP / self-hosted

**Testing:** Jest / Vitest / Pytest / RSpec / none

**CI/CD:** GitHub Actions / GitLab CI / CircleCI / none

### Step 3: Build the tech profile

Collect confidence signals:
- DETECTED (found in config file) vs INFERRED (guessed from file structure)

Write `{project}/memory/tech-profile.md`:

```markdown
# Tech Profile — {project-name}

**Generated:** {date}
**Confidence:** DETECTED (found in config files) unless noted

## Core Stack

| Layer | Technology | Version | Source |
|-------|-----------|---------|--------|
| Language | TypeScript 5.x | from package.json | DETECTED |
| Frontend | Next.js 15 (App Router) | from package.json | DETECTED |
| Backend | Next.js API routes | inferred from /app/api/ | INFERRED |
| Database | PostgreSQL (via Supabase) | from supabase/config.toml | DETECTED |
| ORM | Prisma 5.x | from package.json | DETECTED |
| Auth | better-auth | from package.json | DETECTED |
| Styling | Tailwind CSS 3.x | from package.json | DETECTED |
| UI Library | shadcn/ui | from package.json | DETECTED |
| Deployment | Vercel | from vercel.json | DETECTED |

## Commands (from CLAUDE.md or package.json scripts)

| Command | What it does |
|---------|-------------|
| `{dev-command}` | Local dev server |
| `{test-command}` | Run tests |
| `{build-command}` | Build for production |
| `{deploy-command}` | Deploy |

## Environment Variables Required

| Var | Service | Notes |
|-----|---------|-------|
| `DATABASE_URL` | PostgreSQL | Supabase connection string |
| ... | ... | ... |

## Key Directories

| Dir | Purpose |
|-----|---------|
| `app/` | Next.js App Router pages and API routes |
| `components/` | Shared UI components |
| `lib/` | Shared utilities |
| ... | ... |

## Observations

- {any notable patterns, conventions, or quirks observed during scan}

## Skills Relevant to This Stack

Based on this profile, these skills are directly applicable:
- {skill-name} — {why}
- ...
```

### Step 4: Output summary

Print:
```
TECH PROFILE — {project-name}
Stack: {language} + {frontend} + {database} + {deployment}
Profile written: {project}/memory/tech-profile.md
Confidence: {N detected, M inferred}
```

---

## Advisor Mode — Recommend a Stack for New Projects

### Step 1: Clarify requirements

Before recommending, ask about:
- Team size and existing expertise
- Scale expectations (users, data volume, timeline)
- Budget constraints (open source vs paid)
- Deployment environment (cloud, on-prem, edge)
- MVP vs long-term build

### Step 2: Structure recommendation

- **Recommended Stack** — brief rationale
- **Alternatives Considered** — and why not chosen
- **Trade-offs** — honestly stated
- **Migration path** — if switching from something existing

### Common Stack Patterns

**Web App (Full Stack)**
- Modern solo/small team: Next.js + TypeScript + Supabase + Tailwind + Vercel
- Scaling: Next.js + TypeScript + PostgreSQL (Neon) + Prisma + Railway
- Enterprise: Java Spring Boot / .NET + React + Oracle/MSSQL

**Mobile**
- Cross-platform: React Native or Flutter
- Native performance critical: Swift (iOS), Kotlin (Android)

**Data / AI**
- Python stack: FastAPI + SQLAlchemy + Pandas/Polars + PostgreSQL
- ML serving: FastAPI + PyTorch/TensorFlow + Redis cache

**Microservices**
- Node.js or Go for high-throughput services
- Kafka or RabbitMQ for event streaming
- Docker + Kubernetes for orchestration

### Principles

- Prefer boring, proven technology for core infrastructure
- Match stack to team's existing knowledge when possible
- Avoid over-engineering for early-stage projects
- Always consider operational complexity, not just development speed
