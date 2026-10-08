# Skills Index

240+ reusable workflow skills for Claude Code. Invoke with `/skill-name`.

> **What discovery actually depends on — read before "fixing" missing frontmatter.**
> A skill is discovered by its **location on disk**, not by its metadata: every code
> path in this repo (`cli/commands/sync-assets.js` `syncSkills()`, `skill.js`,
> `init.js`, `upgrade.js`, `scripts/check-flat-skills.js`) resolves a skill as
> `skills/<name>/SKILL.md` existing, and none of them parses frontmatter. This file
> is documentation only — it is copied verbatim to installs and never read
> programmatically. Per the Claude Code skills contract, all frontmatter fields are
> optional: the invocation command comes from the **directory name** (`name` is only
> a display label for personal/project skills), and an omitted `description` falls
> back to the first paragraph of the markdown body. A `SKILL.md` with no frontmatter
> is therefore still discoverable and still invokable — it is a quality wart (a
> weaker auto-invocation trigger), not a broken skill.
>
> The checks in `scripts/skill-audit.py` (A2 frontmatter present, A3 `name` present,
> A4 `name` matches directory) encode this repo's **house style**, which is stricter
> than the harness requires. Treat A2/A3/A4 hits as consistency debt to schedule, not
> as evidence that a skill is inert. The genuinely risky variant is a **malformed**
> block — an opening `---` with no closing `---`, or a `description:` containing an
> unquoted `:` — because that is a parse failure rather than a clean absence. Those
> are worth fixing ahead of the merely-absent ones.
>
> Related known gap: some skills carry valid frontmatter in a live install while the
> copy published here does not. Because `skills/` is deliberately absent from
> `core/.preserve`, a sync overwrites the install from this repo — so repairs must
> land **here**, or an upgrade will undo them.

## Department Lifecycle

| Skill | Description |
|-------|-------------|
| `dept-resume` | Resume department head sessions — reads dept-state.md, spawns dept heads with lean briefings |
| `dept-wrap` | Freeze department state at session end — pairs with /dept-resume (renamed from dept-save-state) |
| `dept-save-state` | RENAMED → use `dept-wrap` instead |
| `dept-status` | Quick department status check — reads state files, returns compact digest |

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
| `lint-memory` | Audit and clean memory files — dead links, duplicates, outdated entries |
| `lessons-sync` | Sync lessons learned across projects and global memory |
| `obsidian-vault` | Obsidian vault integration — read, write, link notes |
| `notebooklm-memory` | NotebookLM notebook management — source ingestion, queries, memory sync |

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
| `nexus-gatekeeper` | reality-check blocking gate — tasks can't advance until cleared |
| `sync-md-json` | Bidirectional sync between .json and .md files |
| `respawn-self` | PD context-aware self-respawn at 80% context — saves state, writes continuation manifest |
| `coord-respawn-self` | Coord context-aware self-respawn at 80% context mid-L3 — saves state, notifies spawner |
| `agent-dispatch` | Decide act-directly vs delegate, pick the spawn type and skills, lookups before spawns, post-spawn ownership |
| `pd-routing` | Forward to a running PD or spawn one PD per project, parallel project work, RESPAWN_REQUEST handling |
| `context-pressure` | Context thresholds: PD above 75% finish and /save-state, at 80% respawn |
| `inbox-tasks` | Where an ownerless task's tracking file lives: the owning project first, else the inbox |
| `memory-crosslink` | Add `See also: [[stem]]` wikilinks to related memory files so the memory graph builds edges |
| `pd-showcase` | Toggle PD showcase mode for live demos — foreground spawn with verbose narration |
| `onboard` | Interactive first-run onboarding for the agency — install check, slash commands, MCP, first project |

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
| `pipeline-onboard` | New project onboarding: tech-stack profile -> CLAUDE.md setup -> memory init -> skill-routing check |
| `pipeline-research` | Research pipeline: auto-researcher -> firecrawl-agent -> graphify -> notebooklm-memory |

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
| `requesting-code-review` | Protocol for requesting structured code reviews |
| `receiving-code-review` | Protocol for receiving and processing code review feedback |
| `feedback-pipeline` | User feedback collection and processing pipeline |
| `cc-loop` | Iterative quality loop — fixer -> polish -> parallel critiques -> score, repeats until pass criteria met |
| `quality-loop-router` | Routes finished deliverables to Mode A (internal loop) or Mode B (external platform fix-plan + approval) |

## Content & Writing

| Skill | Description |
|-------|-------------|
| `humanizer` | Remove signs of AI-generated writing from text |
| `humanizer-writing` | Spot and avoid AI writing — 43 tells from 2026-09 research, for writing time as well as edit time. `hw` is a thin alias skill that runs this one. |
| `hw` | Alias: `/hw` runs `/humanizer-writing` |
| `simple-english` | Plain, layman-readable English in the spirit of ASD-STE100: short sentences, active voice, one word one meaning, defined terms, no AI slop. Plain mode by default, Strict mode on request |
| `proofreader` | Proofread English or Vietnamese text — typos, grammar, clarity |
| `content-polish` | End-to-end polishing: humanizer -> anti-fragmentation -> proofreader (EN) / humanizer-vi -> grammar-checker-vi (VN) |
| `humanizer-vi` | Vietnamese humanizer — fix templated/flat/cliché VN prose, preserve author voice. 27-pattern catalog (lexical/discourse/structural/pragmatic) from 2026-09 research. |
| `translationese-cleaner-vi` | Remove English-influenced word order and phrasing from Vietnamese text |
| `grammar-checker-vi` | Vietnamese grammar/spelling/punctuation checker (deeper than proofreader's VN pass) |
| `style-guide-vi` | Vietnamese style consistency — terminology, pronouns, numbers/dates, capitalization |
| `content-creator` | 14 copywriting formulas, 18 psychology effects, 10 NLP techniques |
| `content-strategy` | Editorial calendars, content pillars, TOFU/MOFU/BOFU planning |
| `copywriting` | Conversion-focused copy for any medium |
| `stop-slop` | Detect and remove AI filler phrases, jargon, passive voice |
| `tech-writer` | Developer docs, API references, READMEs, tutorials, ADRs |
| `marp` | Professional slide decks from Markdown using Marp |
| `deck-narrative` | Deck argument/structure audit — action titles, Minto sequencing, table-vs-chart, decision slides, .pptx font-leak check |
| `markitdown` | Convert any file (PDF, DOCX, XLSX, etc.) to Markdown |
| `make-pdf` | Generate PDF documents |
| `promt-engineering` | Write, optimize, and debug LLM prompts |
| `full-output-enforcement` | Override default LLM truncation behavior |
| `xlsx-toolkit` | Full spreadsheet automation |
| `html-plan-style` | Locked palette, typography, and component system for HTML plans, reports, and review-ready deliverables |
| `strategic-deck` | Builds a 25-30 slide strategic pitch/audit deck — gradient hero slides, cream content slides, five-act narrative arc (pptxgenjs); brand colors resolve from the design-system SSOT |
| `vietnamese-language` | Vietnamese factual reference (formal docs, press releases, dialects, regulation, platform facts) — not a voice source |

## Engineering — Backend

| Skill | Description |
|-------|-------------|
| `backend` | Design APIs, DB schemas, server logic, auth, webhooks, microservices |
| `security` | Apply security best practices to code, architecture, workflows |
| `new-project` | New project scaffolding — directory structure, PD setup, registries |
| `webhook-security` | Webhook signature verification (Paymob, Stripe, Resend, HMAC) |
| `postgresql-schema` | PostgreSQL schemas: multi-tenant SaaS, reservations, CRM, e-commerce |
| `supabase-sql` | SQL for Supabase PostgreSQL engine |
| `supabase-postgres-best-practices` | Supabase PostgreSQL best practices |
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
| `huashu-design` | HTML-based hi-fi prototypes, demos, slide decks, and animation exploration — embodies the right design expert per task |
| `material-3` | Material Design 3 (M3) design system tokens and integration rules |

## Engineering — Video & Media

| Skill | Description |
|-------|-------------|
| `ffmpeg` | FFmpeg/FFprobe command reference — transcode, probe, extract, concat, filter |
| `video-use` | Edit any video by conversation |
| `musicgen` | AI music generation from text prompts via MusicGPT / AudioCraft MusicGen — BGM for video production |
| `subtitle-burner` | Burned-in subtitle workflow for short-form video — karaoke-style open captions via Whisper + ffmpeg |
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
| `image-prompt-engineer` | Prompt-writing methodology for any image generator — Midjourney, DALL-E, Stable Diffusion, Flux, Higgsfield |

## Engineering — AI/ML

| Skill | Description |
|-------|-------------|
| `agents-sdk` | AI agents on Cloudflare Workers using Agents SDK |
| `mcp-builder` | Build MCP servers |
| `benchmark` | Performance benchmarking |
| `benchmark-models` | ML model benchmarking |
| `graphify` | Any input -> knowledge graph -> clustered communities -> HTML + JSON |
| `cli-anything` | Turn any GUI-only software into an agent-usable CLI/REPL harness (Blender, GIMP, LibreOffice, etc.) |

## Deployment

| Skill | Description |
|-------|-------------|
| `github-deploy` | Deploy via GitHub Actions |
| `vercel-deploy` | Deploy to Vercel |
| `railway-deploy` | Deploy to Railway |
| `supabase-deploy` | Deploy to Supabase |

## Cloud — IaC & FinOps

| Skill | Description |
|-------|-------------|
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
| `browser-domain-skills` | Domain-specific browser skill patterns |
| `browser-harness` | Browser automation harness for agent tasks |
| `open-gstack-browser` | Open gstack browser interface |
| `setup-browser-cookies` | Browser cookie setup for authenticated agent sessions |
| `setup-gbrain` | GBrain knowledge graph setup and configuration |

## Skill Management

| Skill | Description |
|-------|-------------|
| `skill-creator` | Create new skills via Skill Seekers CLI |
| `skill-import` | Import skills from library into project CLAUDE.md |
| `skill-quality` | Rate and rewrite skill descriptions |
| `skillify` | Convert workflow to skill |
| `skill-tracker` | Track skill usage patterns and quality metrics |

## SEO & Marketing

| Skill | Description |
|-------|-------------|
| `seo-aeo-best-practices` | SEO, GEO, AEO knowledge base — 7 reference files |
| `inbound-sales` | Inbound sales workflows |
| `content-experimentation-best-practices` | A/B testing, experiment design, metrics |
| `content-modeling-best-practices` | Content modeling and schema design |
| `landing-report` | Landing page audit report — conversion, copy, UX analysis |

## Domain — Auth

| Skill | Description |
|-------|-------------|
| `better-auth-best-practices` | Better Auth integration |
| `better-auth-organization` | Better Auth organization patterns |
| `better-auth-two-factor` | Better Auth 2FA implementation |

## Domain — Business & Automation

| Skill | Description |
|-------|-------------|
| `n8n-automation` | n8n workflow JSON for common automation patterns |
| `legal-contract-review` | Review NDAs, SaaS contracts, MSAs, DPAs — clause-by-clause |
| `tech-stack` | Technology stack selection and architecture decisions |

## Domain — CMS

| Skill | Description |
|-------|-------------|
| `sanity-best-practices` | Sanity CMS: schema, GROQ, TypeGen, Visual Editing |

## Superpowers (gstack Workflow Skills)

| Skill | Description |
|-------|-------------|
| `superpowers-brainstorming` | Explore intent, requirements, design before code |
| `superpowers-dispatching-parallel-agents` | Parallel agent dispatch for independent problems |
| `superpowers-executing-plans` | Execute written implementation plans |
| `superpowers-finishing-a-development-branch` | Full ship pipeline on completion |
| `superpowers-receiving-code-review` | Process code review feedback |
| `superpowers-requesting-code-review` | Dispatch structured code review |
| `superpowers-subagent-driven-development` | Parallel subagent execution |
| `superpowers-systematic-debugging` | Root-cause debugging before any fix |
| `superpowers-test-driven-development` | RED-GREEN-REFACTOR cycle |
| `superpowers-unbundle` | Scope reduction — cut without losing value |
| `superpowers-using-git-worktrees` | Isolated Git worktree for clean work |
| `superpowers-using-superpowers` | Discover and invoke superpowers |
| `superpowers-writing-plans` | Write implementation plans from specs |
| `superpowers-writing-skills` | TDD for process documentation |

## OpenSpec (Experimental Workflow)

| Skill | Description |
|-------|-------------|
| `openspec-explore` | Explore mode — thinking partner for ideas and investigation |
| `openspec-propose` | Propose a new change with all artifacts |
| `openspec-apply-change` | Implement tasks from an OpenSpec change |
| `openspec-archive-change` | Archive a completed change |

## Career

| Skill | Description |
|-------|-------------|
| `career-ops` | Full job search pipeline — JD scraping, CV tailoring, application tracking |
| `cover-letter-gen` | ATS-optimized cover letters — company-specific, 4-paragraph structure |
| `resume-bod` | Board of Directors resume format — achievements-first, executive narrative |

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
/dept-resume [dept-slug]
/dept-wrap [dept-slug]
/dept-wrap all
/swarm
/pipeline-feature [description]
/pipeline-bugfix [bug]
/pipeline-content [topic]
/pipeline-audit [path]
/pipeline-deploy [target]
```

## Creating a Skill

See `core/agents/` for the full developer guide, or use `/skill-creator`.
