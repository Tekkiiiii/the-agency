# Skills Index

Skills are reusable workflows. Invoke them in Claude Code with `/skill-name`.

**Total skills: 166** (40 original + 126 new)

## Memory & Session

| Skill | Description | Category |
|-------|-------------|----------|
| `save-state` | Freeze session to memory files — logs, heartbeat, next-session brief, Pinecone upsert | memory |
| `recall` | Load project briefing from save-state files — outputs 6-field summary | memory |
| `pd-resume` | Resume one or all PDs at session start — parallel recall + spawn | memory |
| `wrap` | Freeze inbox task session — archive completed/abandoned, write session logs | memory |
| `unwrap` | Resume inbox tasks — briefing + spawn task workers | memory |
| `project-status` | Maintain machine-readable PROJECT.md status snapshots | memory |
| `context-mode` | Context mode — load/switch active project context | memory |
| `full-output-enforcement` | Override LLM truncation — enforce complete code generation and file output | memory |

## Coordination

| Skill | Description | Category |
|-------|-------------|----------|
| `swarm` | Portfolio-wide PD dispatch — parallel one-shot status/blocker/priority check | coordination |
| `delegate` | Snapshot context and hand off to a specialized subagent end-to-end | coordination |
| `pd-spawn` | Spawn another PD to do work on your behalf — inter-PD task protocol | coordination |
| `task-handoff` | Tier-A agent handoff — task store as the coordination layer, not conversation | coordination |
| `task-store` | SQLite-backed task store for multi-agent pipeline state tracking | coordination |
| `room-manager` | Poll agency rooms, route escalations, fan out PD statuses, send digests | coordination |
| `room-manager-digest` | Generate 12-hour dept head digests from rolling.md feeds | coordination |
| `nexus-gatekeeper` | Hard blocking gate in task pipeline — reality checker before shipping | coordination |

## Planning

| Skill | Description | Category |
|-------|-------------|----------|
| `autoplan` | Auto-review pipeline (CEO → design → eng) | planning |
| `plan-ceo-review` | CEO/founder-mode plan review | planning |
| `plan-eng-review` | Engineering plan review | planning |
| `plan-design-review` | Designer's-eye plan review | planning |
| `office-hours` | YC-style product framing | planning |
| `retro` | Structured retrospective — git history, patterns, wins/losses, velocity | planning |
| `project-expansion-scout` | Autonomous strategic growth agent — scan projects for expansion, BOD approval | planning |
| `seed` | Typed project incubator — guided ideation through graduation into buildable projects | planning |
| `tech-stack` | Tech Stack Advisor — evaluate and recommend tech choices for a project | planning |
| `openspec-explore` | Enter explore mode — thinking partner for ideas and problem investigation | planning |
| `openspec-propose` | Propose a new OpenSpec change with all artifacts generated in one step | planning |
| `openspec-apply-change` | Implement tasks from an OpenSpec change | planning |
| `openspec-archive-change` | Archive a completed OpenSpec change | planning |

## Execution

| Skill | Description | Category |
|-------|-------------|----------|
| `ship` | Automated ship: merge → test → review → PR | execution |
| `land-and-deploy` | Merge PR → deploy → canary verify | execution |
| `setup-deploy` | Configure deploy platform | execution |
| `canary` | Post-deploy monitoring loop | execution |
| `qa` | Iterative QA testing and bug fixing | execution |
| `qa-only` | Report-only QA (no fixes) | execution |
| `run-acceptance-tests` | Guide for running acceptance tests for a Terraform provider | execution |
| `webapp-testing` | Web application testing — automated browser-based test execution | execution |
| `sandbox-sdk` | Build sandboxed applications for secure code execution and AI coding agents | execution |

## Quality & Review

| Skill | Description | Category |
|-------|-------------|----------|
| `design-review` | Visual QA and design audit | quality |
| `codex` | OpenAI Codex second opinion | quality |
| `cso` | Security audit (OWASP Top 10) | quality |
| `document-release` | Post-ship documentation update | quality |
| `skill-creator` | Skill Creator — build and publish new skills from scratch | quality |
| `skill-quality` | Skill Quality — description critic gate for skill correctness | quality |
| `refactor-module` | Transform monolithic Terraform configurations into reusable modules | quality |

## Ops

| Skill | Description | Category |
|-------|-------------|----------|
| `self-healing` | Diagnose and fix broken workflows — structured diagnostic loop, escalation after 2 attempts | ops |
| `investigate` | Systematic root-cause debugging | ops |
| `guard` | Safety mode — destructive warnings + edit freeze | ops |
| `webhook-security` | Webhook Security Agent — HMAC verification and platform-specific security patterns | ops |
| `admin-shell-foundation` | Admin Shell Foundation — patterns for building admin CLI tools | ops |
| `lightpanda` | Lightpanda browser — drop-in headless replacement for Chrome in scraping tasks | ops |
| `agent-browser` | Agent browser installation and configuration | ops |
| `markitdown` | Convert any file (PDF, DOCX, XLSX, PPTX, HTML, images, audio) to clean Markdown | ops |
| `stop-slop` | Enforce high quality — reject vague, padded, or low-effort output | ops |

## Engineering

| Skill | Description | Category |
|-------|-------------|----------|
| `backend` | Design APIs, DB schemas, server logic | engineering |
| `frontend` | Build React/web interfaces | engineering |
| `tech-writer` | Write developer documentation | engineering |
| `github-deploy` | Deploy via GitHub Actions | deployment |
| `vercel-deploy` | Deploy to Vercel | deployment |
| `railway-deploy` | Deploy to Railway | deployment |
| `supabase-deploy` | Deploy to Supabase | deployment |
| `next-best-practices` | Next.js best practices — App Router, SSR, RSC, and performance patterns | engineering |
| `next-cache-components` | Cache Components for Next.js 16+ — PPR, use cache, cacheTag | engineering |
| `tailwind` | Tailwind CSS v4.2 browser-runtime patterns for HyperFrames compositions | engineering |
| `shadcn-ui` | shadcn/ui component integration — install, customize, and compose components | engineering |
| `multi-role-auth` | Multi-Role Auth Agent — role-based access control patterns | engineering |
| `better-auth-best-practices` | Better Auth best practices for authentication flows | engineering |
| `better-auth-organization` | Better Auth organization — multi-tenant org and team patterns | engineering |
| `better-auth-two-factor` | Better Auth two-factor authentication setup and enforcement | engineering |
| `postgresql-schema` | PostgreSQL Schema Designer — multi-tenant SaaS schema patterns | engineering |
| `supabase-sql` | Supabase SQL — schema design, RLS, migrations, and query patterns | engineering |
| `supabase-postgres-best-practices` | Supabase Postgres best practices — indexing, RLS, and performance | engineering |
| `neon-postgres` | Neon Postgres — serverless Postgres branching and connection patterns | engineering |
| `claimable-postgres` | Claimable Postgres — ephemeral database provisioning patterns | engineering |
| `sanity-best-practices` | Sanity schema design, GROQ queries, TypeGen, Visual Editing best practices | engineering |
| `laravel-builder` | Laravel Builder Agent — scaffolding Laravel 11 projects | engineering |
| `n8n-automation` | n8n Automation Agent — workflow patterns and integrations | engineering |
| `stripe-best-practices` | Stripe best practices — payments, subscriptions, webhooks | engineering |
| `upgrade-stripe` | Guide for upgrading Stripe API versions and SDKs | engineering |
| `promt-engineering` | Write, optimize, and debug LLM prompts — system prompts and task prompts | engineering |
| `graphify` | Convert any input (code, docs, papers, images) into a knowledge graph | engineering |

## Content & Writing

| Skill | Description | Category |
|-------|-------------|----------|
| `content-creator` | Complete content creation framework — 14 copywriting formulas, 18 psychology effects | content |
| `content-modeling-best-practices` | Structured content modeling — schema design, content architecture, governance | content |
| `content-polish` | End-to-end content polishing — humanizer and proofreader in sequence | content |
| `copywriting` | Copywriting Skill — persuasive writing patterns for marketing and sales | content |
| `humanizer` | Remove AI-generated writing signs — make text read naturally and conversationally | content |
| `proofreader` | Proofread in English or Vietnamese (or mixed) — typos, grammar, style | content |
| `marp` | Create professional slide decks from Markdown using Marp, outputting HTML/PDF | content |
| `seo-aeo-best-practices` | SEO, GEO, and AEO best practices — 7 on-demand reference files covering E-E-A-T | content |

## Design & UI

| Skill | Description | Category |
|-------|-------------|----------|
| `impeccable` | Elite visual design judgment — audit, redesign, polish, and critique interfaces | design |
| `high-end-visual-design` | High-end agency design — exact fonts, spacing, color, and motion standards | design |
| `ui-ux-pro-max` | UI UX Pro Max — premium interface design and interaction patterns | design |
| `minimalist-ui` | Clean editorial-style interfaces — warm monochrome, typographic contrast | design |
| `industrial-brutalist-ui` | Raw mechanical interfaces — Swiss typographic print meets military terminal | design |
| `huashu-design` | Huashu-Design — high-fidelity HTML prototypes and interactive demos | design |
| `stitch-design-taste` | Semantic Design System for Google Stitch — agent-friendly DESIGN.md output | design |
| `extract-design` | Extract full design language from any website URL — outputs 8 reference files | design |
| `redesign-existing-projects` | Upgrade existing websites and apps to premium quality with full design audit | design |
| `figma-ui-ux-consistency` | Figma UI/UX Consistency — orchestration for design system audits | design |
| `brandkit` | Premium brand-kit image generation for high-end brand guidelines | design |
| `gpt-image-prompts` | Browse 476+ curated GPT-Image-2 prompts across 5 categories | design |
| `gpt-taste` | Elite UX/UI and Advanced GSAP Motion Engineer — enforces true randomization | design |
| `imagegen-frontend-web` | Elite frontend image-direction skill for premium web screenshot generation | design |
| `imagegen-frontend-mobile` | Elite mobile app image-generation for premium app-native screenshots | design |
| `image-to-code` | Elite website image-to-code — converts screenshots to implementation-ready code | design |
| `css-animations` | CSS animation adapter patterns for HyperFrames — keyframes, transitions | design |
| `animejs` | Anime.js adapter patterns for HyperFrames — timeline and stagger animations | design |
| `gsap` | GSAP animation reference for HyperFrames — gsap.to(), timeline, ScrollTrigger | design |
| `waapi` | Web Animations API adapter patterns for HyperFrames — element.animate() | design |
| `lottie` | Lottie and dotLottie adapter patterns for HyperFrames — embedding JSON animations | design |
| `three` | Three.js and WebGL adapter patterns for HyperFrames — deterministic 3D scenes | design |
| `remotion-best-practices` | Best practices for Remotion — video creation in React | design |
| `remotion-to-hyperframes` | Translate Remotion compositions into HyperFrames format | design |
| `hyperframes-cli` | HyperFrames CLI — init, lint, inspect, preview, render, transform | design |
| `hyperframes-registry` | Install and wire registry blocks and components into HyperFrames compositions | design |
| `website-to-hyperframes` | Website to HyperFrames — convert existing sites into HyperFrames compositions | design |

## Frameworks & Platforms

| Skill | Description | Category |
|-------|-------------|----------|
| `tinybird-best-practices` | Tinybird best practices — real-time analytics, pipes, and data sources | platform |
| `firecrawl-agent` | Firecrawl Agent — autonomous AI-powered web extraction | platform |
| `firecrawl-crawl` | Firecrawl Crawl — full-site crawl and sitemap extraction | platform |
| `firecrawl-scrape` | Firecrawl Scrape — single-page structured data extraction | platform |

## Infrastructure — Netlify

| Skill | Description | Category |
|-------|-------------|----------|
| `netlify-deploy` | Deploy web projects to Netlify using the Netlify CLI | netlify |
| `netlify-cli-and-deploy` | Netlify CLI guide — install, configure, and deploy sites | netlify |
| `netlify-caching` | Control caching on Netlify's CDN — cache headers, purge, and stale-while-revalidate | netlify |
| `netlify-blobs` | Netlify Blobs object storage — store files, images, documents at the edge | netlify |
| `netlify-db` | Netlify DB managed Neon Postgres — setup, queries, and migrations | netlify |
| `netlify-edge-functions` | Netlify Edge Functions — middleware, geolocation, and A/B testing patterns | netlify |
| `netlify-frameworks` | Deploy web frameworks on Netlify — Next.js, Astro, SvelteKit, Nuxt | netlify |
| `netlify-ai-gateway` | Netlify AI Gateway — access AI models with rate limiting and cost control | netlify |

## Infrastructure — Terraform

| Skill | Description | Category |
|-------|-------------|----------|
| `new-terraform-provider` | Scaffold a new Terraform provider from scratch | terraform |
| `terraform-search-import` | Discover cloud resources and bulk import them into Terraform state | terraform |
| `terraform-stacks` | HashiCorp Terraform Stacks — stack configuration and deployment patterns | terraform |
| `terraform-style-guide` | Generate Terraform HCL following HashiCorp official style conventions | terraform |
| `azure-verified-modules` | Azure Verified Modules — certified AVM patterns for Terraform | terraform |
| `provider-actions` | Implement Terraform Provider actions using the Plugin Framework | terraform |
| `provider-resources` | Implement Terraform Provider resources and data sources | terraform |

## Business & Commerce

| Skill | Description | Category |
|-------|-------------|----------|
| `hotel-pms` | Hotel PMS Agent — property management system schema and operations | commerce |
| `reservation-booking` | Reservation/Booking System Agent — schema and booking workflows | commerce |
| `restaurant-pos` | Restaurant POS Agent — point-of-sale schema and transaction patterns | commerce |
| `inbound-sales` | Inbound Sales Skill — lead qualification and conversion patterns | commerce |
| `crm-onboarding` | CRM Onboarding Agent — customer data modeling and onboarding workflows | commerce |
| `legal-contract-review` | Review NDAs, SaaS contracts, MSAs, DPAs with clause-level risk tagging | commerce |

## Superpowers (Development Workflows)

| Skill | Description | Category |
|-------|-------------|----------|
| `superpowers-autoplan` | AutoPlan pipeline — DEPRECATED, use `/autoplan` | superpowers |
| `superpowers-brainstorming` | Use before writing any code — explore the problem space first | superpowers |
| `superpowers-canary` | Canary — post-deploy monitoring (DEPRECATED, use `/canary`) | superpowers |
| `superpowers-codex` | Codex — cross-model review and challenge (DEPRECATED, use `/codex`) | superpowers |
| `superpowers-design-review` | Design Review — live site visual audit (DEPRECATED, use `/design-review`) | superpowers |
| `superpowers-dispatching-parallel-agents` | Use when multiple independent problems exist — dispatch parallel agents | superpowers |
| `superpowers-document-release` | Document Release — post-ship doc sync (DEPRECATED, use `/document-release`) | superpowers |
| `superpowers-executing-plans` | Use when executing a written implementation plan in the current session | superpowers |
| `superpowers-finishing-a-development-branch` | Use when all plan tasks are complete — run the full ship pipeline | superpowers |
| `superpowers-guard` | Guard Mode (DEPRECATED, use `/guard`) | superpowers |
| `superpowers-land-and-deploy` | Land and Deploy (DEPRECATED, use `/land-and-deploy`) | superpowers |
| `superpowers-office-hours` | Office Hours (DEPRECATED, use `/office-hours`) | superpowers |
| `superpowers-plan-design-review` | Plan Design Review — designer's eye on implementation plans | superpowers |
| `superpowers-plan-eng-review` | Plan Engineering Review — lock in the plan before coding | superpowers |
| `superpowers-qa-only` | QA Only — report without fixing (DEPRECATED, use `/qa-only`) | superpowers |
| `superpowers-requesting-code-review` | How and when to request code review in the development workflow | superpowers |
| `superpowers-retro` | Engineering Retrospective (DEPRECATED, use `/retro`) | superpowers |
| `superpowers-subagent-driven-development` | Execute plans with independent tasks dispatched to fresh subagents | superpowers |
| `superpowers-systematic-debugging` | Use when encountering any bug — systematic root-cause investigation | superpowers |
| `superpowers-test-driven-development` | Use when writing new code — enforce TDD red/green/refactor cycle | superpowers |
| `superpowers-unbundle` | Unbundle — scope reduction mode for overgrown tasks | superpowers |
| `superpowers-using-git-worktrees` | Use after design approval — create isolated git worktrees for implementation | superpowers |
| `superpowers-using-superpowers` | Use at conversation start — establish how to discover and apply superpowers | superpowers |
| `superpowers-verification-before-completion` | Verify correctness before marking any task done | superpowers |
| `superpowers-writing-plans` | Writing Plans Skill — structure implementation plans correctly | superpowers |

---

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
/unwrap all
/wrap
```

## Creating a Skill

See `core/agents/` for the full developer guide.
