# Skills Index

244 reusable workflow skills for Claude Code. Invoke with `/skill-name`.

## Memory & Session

| Skill | Description |
|-------|-------------|
| `save-state` | Freeze session to memory files — writes logs, heartbeat, next-session brief |
| `recall` | Load project briefing from save-state files — 6-field summary |
| `pd-resume` | Resume one or all PDs at session start — parallel recall + spawn |
| `wrap` | Freeze inbox task session — archive completed/abandoned, write logs |
| `unwrap` | Resume inbox tasks — briefing + spawn task workers |
| `project-status` | Machine-readable PROJECT.md status snapshots |
| `context-save` | Save current context for later restoration |
| `context-restore` | Restore previously saved context |
| `context-mode` | Context management mode control |
| `freeze` | Freeze current state |
| `unfreeze` | Unfreeze and resume |
| `learn` | Capture lessons from corrections |

## Coordination & Orchestration

| Skill | Description |
|-------|-------------|
| `swarm` | Portfolio-wide PD dispatch — parallel status/blocker/priority check |
| `delegate` | Snapshot context and hand off to a specialized subagent |
| `pd-spawn` | Spawn another PD to do work on your behalf — inter-PD protocol |
| `task-handoff` | Structured agent handoff via shared task store |
| `task-store` | SQLite-backed task store for multi-agent pipeline state |
| `room-manager` | Poll agency rooms, route escalations, fan out PD statuses |
| `room-manager-digest` | 12-hour dept head digests from rolling.md feeds |
| `nexus-gatekeeper` | Reality Checker blocking gate — tasks can't advance until cleared |
| `sync-md-json` | Bidirectional sync between .json and .md files |

## Planning & Review

| Skill | Description |
|-------|-------------|
| `autoplan` | Auto-review pipeline (CEO -> design -> eng) |
| `plan-ceo-review` | CEO/founder-mode plan review |
| `plan-eng-review` | Engineering plan review |
| `plan-design-review` | Designer's-eye plan review |
| `plan-devex-review` | Developer experience review |
| `plan-tune` | Fine-tune plan parameters |
| `office-hours` | YC-style product framing |
| `retro` | Structured retrospective — git history, patterns, wins/losses |
| `project-expansion-scout` | Autonomous strategic growth agent — scan projects for expansion |
| `seed` | Typed project incubator — guided ideation through graduation |

## Pipelines (Multi-Stage Workflows)

| Skill | Description |
|-------|-------------|
| `pipeline-feature` | Full feature: plan -> execute -> critique -> review -> QA -> ship -> deploy |
| `pipeline-bugfix` | Bug fix: investigate -> fix -> critique -> QA -> ship |
| `pipeline-content` | Content: research -> create -> critique -> humanize -> knowledge |
| `pipeline-audit` | Audit: parallel critiques -> aggregate -> QA -> report |
| `pipeline-deploy` | Deploy: security -> baseline -> deploy -> canary + benchmark |
| `pipeline-seo-geo-aeo` | SEO/GEO/AEO audit: technical SEO, structured data, E-E-A-T, AEO, GEO |

## Execution & Shipping

| Skill | Description |
|-------|-------------|
| `ship` | Automated ship: merge -> test -> review -> PR |
| `land-and-deploy` | Merge PR -> deploy -> canary verify |
| `setup-deploy` | Configure deploy platform |
| `canary` | Post-deploy monitoring loop |
| `qa` | Iterative QA testing and bug fixing |
| `qa-only` | Report-only QA (no fixes) |
| `run-acceptance-tests` | Run acceptance tests for Terraform providers |

## Quality & Critique

| Skill | Description |
|-------|-------------|
| `design-review` | Visual QA and design audit |
| `codex` | OpenAI Codex second opinion |
| `cso` | Security audit (OWASP Top 10) |
| `document-release` | Post-ship documentation update |
| `review` | Code review |
| `backend-critique` | Backend architecture critique |
| `design-critique` | Design system critique |
| `content-critique` | Content quality critique |
| `marketing-critique` | Marketing strategy critique |
| `operations-critique` | Operations efficiency critique |
| `product-critique` | Product strategy critique |
| `security-critique` | Security posture critique |
| `workflow-critique` | Workflow optimization critique |
| `devex-review` | Developer experience review |
| `careful` | Extra-careful review mode |

## Content & Writing

| Skill | Description |
|-------|-------------|
| `humanizer` | Remove signs of AI-generated writing from text |
| `proofreader` | Proofread English or Vietnamese text — typos, grammar, clarity |
| `content-polish` | End-to-end polishing: humanizer -> anti-fragmentation -> proofreader |
| `content-creator` | 14 copywriting formulas, 18 psychology effects, 10 NLP techniques |
| `content-strategy` | Editorial calendars, content pillars, TOFU/MOFU/BOFU planning |
| `copywriting` | Conversion-focused copy for any medium |
| `stop-slop` | Detect and remove AI filler phrases, jargon, passive voice |
| `tech-writer` | Developer docs, API references, READMEs, tutorials, ADRs |
| `marp` | Professional slide decks from Markdown using Marp |
| `markitdown` | Convert any file (PDF, DOCX, XLSX, etc.) to Markdown |
| `make-pdf` | Generate PDF documents |
| `promt-engineering` | Write, optimize, and debug LLM prompts |
| `full-output-enforcement` | Override default LLM truncation behavior |
| `xlsx-toolkit` | Full spreadsheet automation |
| `vietnamese-language` | Vietnamese language reference layer — 17-file modular KB |

## Engineering — Backend

| Skill | Description |
|-------|-------------|
| `backend` | Design APIs, DB schemas, server logic, auth, webhooks, microservices |
| `security` | Apply security best practices to code, architecture, workflows |
| `webhook-security` | Webhook signature verification (Paymob, Stripe, Resend, HMAC) |
| `postgresql-schema` | PostgreSQL schemas: multi-tenant SaaS, reservations, CRM, e-commerce |
| `supabase-sql` | SQL for Supabase PostgreSQL engine |
| `supabase-postgres-best-practices` | Supabase PostgreSQL best practices |
| `neon-postgres` | Neon Postgres patterns |
| `claimable-postgres` | Claimable Postgres patterns |
| `multi-role-auth` | Multi-role auth: NextAuth.js or Laravel Breeze with roles |
| `laravel-builder` | Laravel 11 scaffold: Breeze, Filament, PostgreSQL, Sail/Docker |
| `admin-shell-foundation` | Shared admin shell scaffold for domain skills |

## Engineering — Frontend

| Skill | Description |
|-------|-------------|
| `frontend` | Build React/web interfaces with design-first workflow |
| `shadcn-ui` | shadcn/ui component patterns |
| `cult-ui` | Animated shadcn-compatible components from Cult UI registry |
| `tailwind` | Tailwind CSS v4.2 browser-runtime patterns |
| `next-best-practices` | Next.js best practices |
| `next-cache-components` | Next.js caching and component patterns |
| `css-animations` | CSS animation adapter patterns |
| `image-to-code` | Website image-to-code conversion |
| `redesign-existing-projects` | Upgrade existing websites to premium quality |
| `svgl` | Fetch SVG logos for tech companies and frameworks via SVGL API |
| `excalidraw-diagram` | Create Excalidraw diagram JSON files |
| `extract-design` | Extract full design language from any website URL |

## Engineering — Design & UI/UX

| Skill | Description |
|-------|-------------|
| `ui-ux-pro-max` | Design-system-first UI/UX across React, Vue, Svelte, SwiftUI, Flutter |
| `impeccable` | Design, redesign, shape, critique, audit, polish, animate, colorize |
| `design-html` | High-fidelity HTML prototypes |
| `design-consultation` | Design consultation mode |
| `design-shotgun` | Rapid design exploration |
| `design-taste-frontend` | Senior UI/UX Engineer perspective |
| `stitch-design-taste` | Semantic Design System for Google Stitch |
| `high-end-visual-design` | Design like a high-end agency |
| `minimalist-ui` | Clean editorial-style interfaces |
| `industrial-brutalist-ui` | Raw mechanical Swiss typo + military terminal aesthetics |
| `emil-design-eng` | Emil Kowalski's UI polish philosophy |
| `gpt-taste` | Elite UX/UI & advanced motion engineering |
| `awesome-design-md` | Design resource collection |
| `figma-ui-ux-consistency` | Figma UI/UX consistency checks |
| `brandkit` | Premium brand-kit image generation |

## Engineering — Video & Media

| Skill | Description |
|-------|-------------|
| `ffmpeg` | FFmpeg/FFprobe command reference — transcode, probe, extract, concat, filter |
| `video-use` | Edit any video by conversation |
| `hyperframes` | HyperFrames HTML video compositions, animations, captions, voiceovers |
| `hyperframes-cli` | HyperFrames CLI — init, lint, preview, render, transcribe, tts |
| `hyperframes-media` | Asset preprocessing: TTS (Kokoro), transcription (Whisper), bg removal |
| `hyperframes-registry` | Install registry blocks into HyperFrames compositions |
| `website-to-hyperframes` | Convert website to HyperFrames composition |
| `remotion-best-practices` | Remotion video creation in React |
| `remotion-to-hyperframes` | Translate Remotion composition to HyperFrames |
| `lottie` | Lottie/dotLottie adapter patterns |
| `animejs` | Anime.js adapter patterns |
| `gsap` | GSAP animation reference |
| `waapi` | Web Animations API adapter patterns |
| `three` | Three.js/WebGL adapter patterns |
| `gpt-image-prompts` | 476+ curated GPT-Image-2 prompts across 5 categories |
| `imagegen-frontend-web` | Premium website design reference images |
| `imagegen-frontend-mobile` | Premium mobile app screen concepts |

## Engineering — AI/ML

| Skill | Description |
|-------|-------------|
| `sandbox-sdk` | Build sandboxed applications for secure code execution |
| `agents-sdk` | AI agents on Cloudflare Workers using Agents SDK |
| `mcp-builder` | Build MCP servers |
| `benchmark` | Performance benchmarking |
| `benchmark-models` | ML model benchmarking |
| `graphify` | Any input -> knowledge graph -> clustered communities -> HTML + JSON |

## Deployment

| Skill | Description |
|-------|-------------|
| `github-deploy` | Deploy via GitHub Actions |
| `vercel-deploy` | Deploy to Vercel |
| `railway-deploy` | Deploy to Railway |
| `supabase-deploy` | Deploy to Supabase |
| `netlify-deploy` | Deploy to Netlify via CLI |
| `netlify-cli-and-deploy` | Netlify CLI and deployment guide |

## Cloud — Cloudflare

| Skill | Description |
|-------|-------------|
| `cloudflare` | Cloudflare platform: Workers, Pages, KV, D1, R2, AI, networking |
| `cloudflare-email-service` | Transactional email with Cloudflare Email Routing |
| `workers-best-practices` | Cloudflare Workers production best practices |
| `wrangler` | Cloudflare Workers CLI for deploying and managing Workers |
| `durable-objects` | Cloudflare Durable Objects |

## Cloud — Netlify

| Skill | Description |
|-------|-------------|
| `netlify-config` | netlify.toml configuration reference |
| `netlify-functions` | Serverless functions |
| `netlify-edge-functions` | Edge functions |
| `netlify-forms` | HTML form handling |
| `netlify-blobs` | Object storage |
| `netlify-db` | Managed Neon Postgres |
| `netlify-caching` | CDN caching control |
| `netlify-image-cdn` | Image optimization and transformation |
| `netlify-frameworks` | Web framework deployment |
| `netlify-ai-gateway` | AI model access gateway |

## Cloud — Terraform / IaC

| Skill | Description |
|-------|-------------|
| `terraform-style-guide` | HashiCorp official style conventions |
| `terraform-test` | Writing and running Terraform tests |
| `terraform-stacks` | HashiCorp Terraform Stacks guide |
| `terraform-search-import` | Discover and bulk import existing cloud resources |
| `new-terraform-provider` | Scaffold a new Terraform provider |
| `provider-actions` | Terraform Provider actions (Plugin Framework) |
| `provider-resources` | Terraform Provider resources and data sources |
| `provider-test-patterns` | Provider acceptance test patterns |
| `azure-verified-modules` | Azure Verified Modules (AVM) best practices |
| `refactor-module` | Transform monolithic Terraform into reusable modules |
| `finops` | Cloud financial operations |

## Google Workspace

| Skill | Description |
|-------|-------------|
| `gws` | Google Workspace CLI — Gmail, Drive, Docs, Sheets, Calendar |
| `gws-chat` | Google Chat integration |
| `gws-forms` | Google Forms integration |
| `gws-slides` | Google Slides integration |
| `gws-tasks` | Google Tasks integration |

## Ops & Debugging

| Skill | Description |
|-------|-------------|
| `self-healing` | Diagnose and fix broken workflows — structured diagnostic loop |
| `investigate` | Systematic root-cause debugging |
| `guard` | Safety mode — destructive warnings + edit freeze |
| `health` | System health checks |
| `web-perf` | Web performance analysis via Chrome DevTools |
| `webapp-testing` | Web application testing |

## Browser & Scraping

| Skill | Description |
|-------|-------------|
| `browse` | Fast headless browser for QA testing and dogfooding |
| `agent-browser` | Native Rust headless browser CLI for AI agents |
| `lightpanda` | Lightpanda browser — fast, light, no graphical rendering |
| `scrape` | Web scraping |
| `firecrawl-agent` | Firecrawl agent integration |
| `firecrawl-crawl` | Firecrawl website crawling |
| `firecrawl-scrape` | Firecrawl page scraping |
| `pair-agent` | Pair a remote AI agent with your browser |
| `connect-chrome` | Connect to Chrome browser |

## Skill Management

| Skill | Description |
|-------|-------------|
| `skill-creator` | Create new skills via Skill Seekers CLI |
| `skill-import` | Import skills from library into project CLAUDE.md |
| `skill-quality` | Rate and rewrite skill descriptions |
| `skillify` | Convert workflow to skill |

## SEO & Marketing

| Skill | Description |
|-------|-------------|
| `seo-aeo-best-practices` | SEO, GEO, AEO knowledge base — 7 reference files |
| `inbound-sales` | Inbound sales workflows |
| `content-experimentation-best-practices` | A/B testing, experiment design, metrics |
| `content-modeling-best-practices` | Content modeling and schema design |

## Domain — Payments & E-Commerce

| Skill | Description |
|-------|-------------|
| `stripe-best-practices` | Stripe integration best practices |
| `upgrade-stripe` | Upgrade Stripe API versions and SDKs |

## Domain — Auth

| Skill | Description |
|-------|-------------|
| `better-auth-best-practices` | Better Auth integration |
| `better-auth-organization` | Better Auth organization patterns |
| `better-auth-two-factor` | Better Auth 2FA implementation |

## Domain — Hospitality & Business

| Skill | Description |
|-------|-------------|
| `hotel-pms` | Hotel Property Management System in Laravel or Next.js |
| `restaurant-pos` | Restaurant POS system — menu, tables, orders, KDS, tips |
| `reservation-booking` | Reservation/booking system — slots, calendar, payments |
| `n8n-automation` | n8n workflow JSON for common automation patterns |
| `legal-contract-review` | Review NDAs, SaaS contracts, MSAs, DPAs — clause-by-clause |
| `tech-stack` | Technology stack selection and architecture decisions |

## Domain — CMS

| Skill | Description |
|-------|-------------|
| `sanity-best-practices` | Sanity CMS: schema, GROQ, TypeGen, Visual Editing |
| `tinybird-best-practices` | Tinybird analytics best practices |

## Superpowers (gstack Workflow Skills)

| Skill | Description |
|-------|-------------|
| `superpowers-autoplan` | Run CEO + design + eng reviews sequentially |
| `superpowers-brainstorming` | Explore intent, requirements, design before code |
| `superpowers-canary` | Post-deploy canary monitoring |
| `superpowers-codex` | OpenAI Codex CLI wrapper |
| `superpowers-cso` | Security audit mode |
| `superpowers-design-review` | Visual QA across all pages |
| `superpowers-dispatching-parallel-agents` | Parallel agent dispatch for independent problems |
| `superpowers-document-release` | Post-ship documentation |
| `superpowers-executing-plans` | Execute written implementation plans |
| `superpowers-finishing-a-development-branch` | Full ship pipeline on completion |
| `superpowers-guard` | Maximum safety mode |
| `superpowers-land-and-deploy` | Merge + deploy + canary |
| `superpowers-office-hours` | Product exploration and validation |
| `superpowers-plan-ceo-review` | CEO-level plan review |
| `superpowers-plan-design-review` | Designer's eye plan review |
| `superpowers-plan-eng-review` | Engineering plan review |
| `superpowers-qa-only` | Report-only QA |
| `superpowers-receiving-code-review` | Process code review feedback |
| `superpowers-requesting-code-review` | Dispatch structured code review |
| `superpowers-retro` | Weekly retrospective |
| `superpowers-subagent-driven-development` | Parallel subagent execution |
| `superpowers-systematic-debugging` | Root-cause debugging before any fix |
| `superpowers-test-driven-development` | RED-GREEN-REFACTOR cycle |
| `superpowers-unbundle` | Scope reduction — cut without losing value |
| `superpowers-using-git-worktrees` | Isolated Git worktree for clean work |
| `superpowers-using-superpowers` | Discover and invoke superpowers |
| `superpowers-verification-before-completion` | Fresh verification before claiming done |
| `superpowers-writing-plans` | Write implementation plans from specs |
| `superpowers-writing-skills` | TDD for process documentation |

## OpenSpec (Experimental Workflow)

| Skill | Description |
|-------|-------------|
| `openspec-explore` | Explore mode — thinking partner for ideas and investigation |
| `openspec-propose` | Propose a new change with all artifacts |
| `openspec-apply-change` | Implement tasks from an OpenSpec change |
| `openspec-archive-change` | Archive a completed change |

## Research

| Skill | Description |
|-------|-------------|
| `auto-researcher` | Proactive research — search, synthesize, present with sources |

## Using Skills

In Claude Code, invoke any skill with:

```
/skill-name
```

Common combinations:

```
/autoplan
/pd-resume all
/pd-resume [slug]
/save-state
/save-state [slug]
/save-state all
/swarm
/pipeline-feature [description]
/pipeline-bugfix [bug]
/pipeline-content [topic]
/pipeline-audit [path]
/pipeline-deploy [target]
```

## Creating a Skill

See `core/agents/` for the full developer guide, or use `/skill-creator`.
