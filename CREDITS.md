# Credits

Not everything in The Agency was made by one person. This system stands on other people's work: ideas I read and borrowed, skills I copied in and bent to fit, and tools I lean on every day. This page names them, links to where they live, and says what each one is for. If I got a name, a licence or a description wrong, please open an issue and I will fix it.

Licences below are the upstream project's own, as listed on its repository. The Agency itself is MIT (see the README). Where a source ships without a licence file, it is listed as such, not guessed at. Every folder under `skills/` that was copied or adapted from a licensed upstream carries that upstream's licence text (`LICENSE`, plus `NOTICE` where the upstream has one) next to its `SKILL.md`.

## Ideas and patterns

Ideas are not code. Nothing here was copied; the design follows or is inspired by the source.

| Idea | Author | Source | What it shaped |
|---|---|---|---|
| LLM Wiki | Andrej Karpathy | [gist: llm-wiki.md](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026) | The memory design is inspired by it: an index plus plain markdown pages that the agents write and maintain, cross-links between related pages, and a periodic lint pass for orphans, dead links and stale entries. See `core/memory/` and `skills/lint-memory`. We keep the idea (a compounding wiki, not re-retrieval), not his exact layers or his ingest/log files. |
| Karpathy's raw-folder workflow | Andrej Karpathy | same gist and his public posts | `skills/graphify` is built around the same habit: drop anything into a folder and get a structured, linked view of it. |
| Everything Claude Code (ECC) patterns | Affaan Mustafa ([affaan-m](https://github.com/affaan-m/everything-claude-code)), MIT | repository | Reference patterns for hooks, loop safety, council decisions, evals and cost tracking, written up in `docs/ecc-patterns.md`. Ideas reviewed and adopted with changes; no code copied. |
| Signs of AI writing | WikiProject AI Cleanup, [Wikipedia](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) | Wikipedia | The pattern catalogue behind `skills/humanizer` and `skills/humanizer-writing`. |
| Hermes Agent self-improvement loop | Nous Research ([NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)), MIT | repository | `skills/self-healing` is inspired by the way Hermes Agent recovers and learns from failed turns. Idea credit only; the skill is a short triage-then-escalate checklist and no Hermes code was copied (checked against the repository's recovery modules). |
| Lazy-senior-dev discipline ("ponytail:" shortcut comments) | Dietrich Gebert | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail), MIT | The `ponytail:` comment convention in `hooks/` and `mods/` marks deliberate shortcuts. The plugin itself is installed separately, not shipped here. |

## Token saving: caveman and ponytail

Two community plugins carry most of the token-saving behaviour, and I use them every day.

- **caveman** by Julius Brussee ([JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman), Apache-2.0). Ultra-compressed reply mode that cuts output tokens while keeping the technical content. This repo ships `hooks/caveman-statusline.sh` (the mode badge for the status line, adapted from the plugin's statusline script) and documents it in `docs/HOOKS.md`. `hooks/spawn-gate.sh` lets caveman's own subagent types through. The plugin itself is installed separately.
- **ponytail** by Dietrich Gebert ([DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail), MIT). A "laziest solution that works" mode: stdlib first, no speculative abstractions. We use it as an installed plugin and borrow its `ponytail:` comment convention (see above). The compact startup rules for both are described in the README under `voice-compact`.

## Skills and code we ship

"Vendored" means copied in with little or no change. "Adapted" means copied and then edited, merged or renamed for this system. Upstream authorship stays with the original authors.

### Writing and language

| Skill | Author | Licence | Use | Ships in |
|---|---|---|---|---|
| humanizer | Siqi Chen ([blader](https://github.com/blader/humanizer)) | MIT | Vendored (frozen copy) | `skills/humanizer` |
| humanizer-writing, hw | Derivative of blader/humanizer at 2.11.2 | MIT | Adapted | `skills/humanizer-writing`, `skills/hw` |
| humanizer-vi, grammar-checker-vi, style-guide-vi, translationese-cleaner-vi | Hàng Nhựt Long ([longhang2004](https://github.com/longhang2004/vietnamese-humanizer)) | MIT | Vendored, then extended with extra patterns | `skills/humanizer-vi`, `skills/grammar-checker-vi`, `skills/style-guide-vi`, `skills/translationese-cleaner-vi` |
| stop-slop | Hardik Pandya ([hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop)) | MIT | Adapted: upstream's AI-tell checklist, extended with a scoring rubric | `skills/stop-slop` |
| simple-english | Amin Boulegroun ([AminBlg](https://github.com/AminBlg/SimpleEnglish)) | MIT | Vendored | `skills/simple-english` |
| markitdown | Microsoft ([microsoft/markitdown](https://github.com/microsoft/markitdown)) | MIT | Hand-written skill wrapping the library | `skills/markitdown` |

### Design and frontend

| Skill | Author | Licence | Use | Ships in |
|---|---|---|---|---|
| design-taste-frontend, high-end-visual-design, minimalist-ui, industrial-brutalist-ui, redesign-existing-projects, stitch-design-taste, full-output-enforcement, gpt-taste, brandkit, image-to-code, imagegen-frontend-web, imagegen-frontend-mobile | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | MIT | Vendored (renamed) | `skills/<same names>` |
| impeccable | Paul Bakaus ([pbakaus/impeccable](https://github.com/pbakaus/impeccable)); based on Anthropic's frontend-design skill | Apache-2.0 | Vendored | `skills/impeccable` |
| emil-design-eng | Emil Kowalski ([emilkowalski/skills](https://github.com/emilkowalski/skills)) | MIT | Vendored | `skills/emil-design-eng` |
| huashu-design | 花叔 / alchaincyf ([alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design)) | MIT | Vendored | `skills/huashu-design` |
| shadcn-ui | Google Labs ([stitch-skills](https://github.com/google-labs-code/stitch-skills)) | Apache-2.0 | Vendored | `skills/shadcn-ui` |
| extract-design | Manavarya Singh ([Manavarya09/design-extract](https://github.com/Manavarya09/design-extract)) | MIT | Vendored | `skills/extract-design` |
| awesome-design-md | VoltAgent ([VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)) | MIT | Adapted: a workflow skill around that design-system library; the skill's own header names VoltAgent as author | `skills/awesome-design-md` |
| excalidraw-diagram | Cole Medin ([coleam00](https://github.com/coleam00/excalidraw-diagram-skill)) | no licence file (see below) | Vendored | `skills/excalidraw-diagram` |
| gpt-image-prompts | EvoLinkAI ([awesome-gpt-image-2 prompts](https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts)) | CC0-1.0 | Vendored (upstream renamed) | `skills/gpt-image-prompts` |
| material-3 | Material Design docs, [m3.material.io](https://m3.material.io) | Apache-2.0 (as stated in the skill header) | Adapted from public docs | `skills/material-3` |

### Video and browser

| Skill | Author | Licence | Use | Ships in |
|---|---|---|---|---|
| hyperframes, hyperframes-cli, hyperframes-registry, remotion-to-hyperframes, plus the motion-library adapter skills (gsap, animejs, lottie, three, tailwind, waapi, css-animations, hyperframes-media, website-to-hyperframes) | HeyGen ([heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)) | Apache-2.0 | Vendored | `skills/hyperframes*`, and the adapter skills named at left |
| remotion-best-practices | Remotion ([remotion-dev/skills](https://github.com/remotion-dev/skills)) | no licence file (see below) | Vendored | `skills/remotion-best-practices` |
| video-use | Browser Use ([browser-use/video-use](https://github.com/browser-use/video-use)) | MIT | Vendored | `skills/video-use` |
| browser-harness | Browser Use ([browser-use/browser-harness](https://github.com/browser-use/browser-harness)) | MIT | Vendored | `skills/browser-harness` |
| lightpanda | Pierre Tachoire, Lightpanda ([lightpanda-io/agent-skill](https://github.com/lightpanda-io/agent-skill)) | Apache-2.0 | Vendored | `skills/lightpanda` |
| webapp-testing, mcp-builder | Anthropic ([anthropics/skills](https://github.com/anthropics/skills)) | Apache-2.0 (upstream `LICENSE.txt` shipped in each folder) | Vendored | `skills/webapp-testing`, `skills/mcp-builder` |

### Engineering and platforms

| Skill | Author | Licence | Use | Ships in |
|---|---|---|---|---|
| web-perf, agents-sdk | Cloudflare ([cloudflare/skills](https://github.com/cloudflare/skills)) | Apache-2.0 | Vendored (agents-sdk lightly edited) | `skills/web-perf`, `skills/agents-sdk` |
| refactor-module, run-acceptance-tests | HashiCorp ([hashicorp/agent-skills](https://github.com/hashicorp/agent-skills)) | MPL-2.0 | Vendored | `skills/refactor-module`, `skills/run-acceptance-tests` |
| sanity-best-practices, content-modeling-best-practices, content-experimentation-best-practices, seo-aeo-best-practices | Sanity ([sanity-io/agent-toolkit](https://github.com/sanity-io/agent-toolkit)) | MIT | Vendored | `skills/<same names>` |
| supabase-postgres-best-practices | Supabase ([supabase/agent-skills](https://github.com/supabase/agent-skills)) | MIT (as stated in the skill header and upstream) | Vendored | `skills/supabase-postgres-best-practices` |
| better-auth-best-practices, better-auth-organization, better-auth-two-factor | Better Auth ([better-auth/skills](https://github.com/better-auth/skills)) | no licence file (see below) | Vendored | `skills/better-auth-*` |
| firecrawl-agent, firecrawl-crawl, firecrawl-scrape | Firecrawl ([firecrawl/skills](https://github.com/firecrawl/skills)) | ISC | Vendored | `skills/firecrawl-*` |
| gws-chat, gws-forms, gws-slides, gws-tasks (and the `gws` skill) | Google Workspace ([googleworkspace/cli](https://github.com/googleworkspace/cli)) | Apache-2.0 | Vendored | `skills/gws*` |
| openspec-explore, openspec-propose, openspec-apply-change, openspec-archive-change | Fission AI ([OpenSpec](https://github.com/Fission-AI/OpenSpec)) | MIT (as stated in each skill header) | Vendored | `skills/openspec-*` |
| skill-creator | wraps [Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) by yusufkaraaslan | MIT | Skill that drives that CLI | `skills/skill-creator` |
| cli-anything | HKUDS ([HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything)) | Apache-2.0 | Adapted: the 7-phase harness method condensed from its `HARNESS.md` | `skills/cli-anything` |
| career-ops | Santiago Fernández de Valderrama ([career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops)) | MIT | Adapted: router skill built on its mode set (scan, oferta, pipeline, pdf, tracker and the rest); the routing text is ours | `skills/career-ops` |
| graphify | Graphify ([Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)) | Apache-2.0 | Adapted skill around the tool | `skills/graphify` |

### Workflow skills

| Skill | Author | Licence | Use | Ships in |
|---|---|---|---|---|
| The review, QA, planning, ship and safety skills that carry the gstack marker: office-hours, plan-ceo-review, plan-eng-review, plan-design-review, plan-devex-review, design-consultation, design-review, design-html, design-shotgun, devex-review, review, qa, qa-only, ship, land-and-deploy, canary, careful, freeze, unfreeze, guard, cso, investigate, retro, learn, health, document-release, autoplan, benchmark, benchmark-models, browse, scrape, make-pdf, context-save, context-restore, pair-agent, plan-tune, setup-browser-cookies, setup-deploy, setup-gbrain, open-gstack-browser (folder `connect-chrome`), landing-report, github-deploy, railway-deploy, vercel-deploy, supabase-deploy, skillify, codex, and the `*-critique` skills | Garry Tan ([garrytan/gstack](https://github.com/garrytan/gstack)) | MIT | Adapted: gstack's workflows, edited for this system's agents and paths | `skills/<same names>` |
| superpowers-* (brainstorming, writing-plans, executing-plans, test-driven-development, systematic-debugging, subagent-driven-development, dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch, requesting/receiving-code-review, writing-skills, using-superpowers, unbundle) | Jesse Vincent ([obra/superpowers](https://github.com/obra/superpowers)) | MIT | Adapted | `skills/superpowers-*` |

### Skills from Claude Code plugins and apps

These nine skills came into the library through Claude Code plugins and apps that I installed. I could not match their text to any plugin or repository that is installed on my machine today, so the original plugin name, author and licence are not recorded here and I am not guessing them. If you recognise one of these, please open an issue with the link and I will credit it properly and add its licence file.

| Skill | Origin | Licence | Ships in |
|---|---|---|---|
| ffmpeg | A Claude Code plugin/app (source not pinned) | not recorded | `skills/ffmpeg` |
| xlsx-toolkit | A Claude Code plugin/app (source not pinned) | not recorded | `skills/xlsx-toolkit` |
| n8n-automation | A Claude Code plugin/app (source not pinned) | not recorded | `skills/n8n-automation` |
| postgresql-schema | A Claude Code plugin/app (source not pinned) | not recorded | `skills/postgresql-schema` |
| laravel-builder | A Claude Code plugin/app (source not pinned) | not recorded | `skills/laravel-builder` |
| webhook-security | A Claude Code plugin/app (source not pinned) | not recorded | `skills/webhook-security` |
| admin-shell-foundation | A Claude Code plugin/app (source not pinned) | not recorded | `skills/admin-shell-foundation` |
| subtitle-burner | A Claude Code plugin/app (source not pinned). Its text says it replaces the `jurczykpawel/subtitle-burner` project (now ReelStack), which is too heavy for caption-only use; the implementation here is Whisper plus ffmpeg and no ReelStack code is used | not recorded | `skills/subtitle-burner` |
| self-healing | A Claude Code plugin/app (source not pinned); inspired by Hermes Agent, see Ideas and patterns above | not recorded | `skills/self-healing` |

### Agent catalog heritage

| Source | Author | Licence | Use | Ships in |
|---|---|---|---|---|
| agency-agents | [msitarzewski](https://github.com/msitarzewski/agency-agents) | MIT | Early agent definitions and their tooling derive from it | `agents/` |

## Tools and platforms

These are what the system runs on. We do not ship them; we call them, document them or wire into them.

| Tool | Author | Licence | What it does for us |
|---|---|---|---|
| Claude Code | Anthropic | commercial, see Anthropic's terms | The host: agents, skills, hooks, mods and the status line all run inside it. |
| Hermes Agent ([NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)) | Nous Research | MIT | Optional second agent runtime the setup docs and bootstrap script cater for. |
| Codex CLI ([openai/codex](https://github.com/openai/codex)) | OpenAI | Apache-2.0 | Second-opinion runtime used by the `codex` skill. |
| Marp CLI ([marp-team/marp-cli](https://github.com/marp-team/marp-cli)) | Marp team | MIT | Markdown to slide decks, wrapped by `skills/marp`. |
| Lightpanda browser ([lightpanda-io/browser](https://github.com/lightpanda-io/browser)) | Lightpanda | AGPL-3.0 | Headless browser behind the `lightpanda` skill. Installed by the user, not redistributed here. |
| Google Workspace CLI ([googleworkspace/cli](https://github.com/googleworkspace/cli)) | Google | Apache-2.0 | The `gws` command the Google skills drive. |
| gbrain ([garrytan/gbrain](https://github.com/garrytan/gbrain)) | Garry Tan | MIT | Memory tool that `skills/setup-gbrain` installs and configures. |
