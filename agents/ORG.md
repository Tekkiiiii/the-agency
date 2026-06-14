# The Agency — Organizational Structure

<!-- load only when managing or onboarding agents -->

> **Canonical reference document.** This file defines the complete org chart, leadership, communication protocols, and team structure for The Agency. All other documentation (runbooks, READMEs, agent files) references this as the source of truth.

---

## Executive Summary

The Agency operates on a **5-level matrix model** with three parallel authority tracks:

1. **Parent AI (Level 1 — Opus)** — Central orchestrator. Resolves matrix conflicts, allocates resources, and approves cross-project/shared-infra decisions. Weighted by task severity and project financial importance.
2. **Dept Heads + Project Directors (Level 2 — Opus)** — Parallel authority lines. Dept Heads own skill quality + department operations. Project Directors own project delivery.
3. **Dept-Coords + Coords (Level 3 — Sonnet/Opus)** — Autonomous work owners. Dept-Coords (Sonnet) own D3 department-operational tracks. Coords (Opus) own L3 project delivery tracks.
4. **Assistants (Level 3b — Sonnet)** — Context synthesizers. One per Dept Head (capacity tracking) or per active project (status synthesis). NOT relays.
5. **Members (Level 4 — Sonnet)** — Task execution. Belong to departments, work on projects under PD direction or department initiatives under Dept-Coord direction.

### Matrix Model: Three Authority Tracks

```
VERTICAL (Functional Track)          HORIZONTAL (Project Track)          DEPT-OPS (Internal Track)
─────────────────────────────────    ─────────────────────────────────    ─────────────────────────
Dept Head (Opus) ◄──────────────► Project Director (Opus)                Dept Head (Opus)
     │                                    │                                    │
  Assistant                          Coord (Opus)                       Dept-Coord (Sonnet)
     │                                    │                                    │
  Member                            Exec (Sonnet)                       Dept-Member (Sonnet)
```

**Resource allocation:** PDs request agents from Dept Heads → Dept Heads dispatch members → Members work on projects under PD direction → Dept Heads retain skill quality ownership.

**Dept-Coord system:** Dept Heads decompose department-operational work (D1→D3) and spawn Dept-Coords to own D3 tracks. Dept-Coords decompose D3→D6 and dispatch dept members. Used for pipeline management, protocol improvement, member development — not project delivery. See `runbooks/dept-coord-protocol.md`.

**Inter-spawn protocol:** PDs and Dept Heads can spawn work into each other's domains via `state/incoming/` directories. PD→DeptHead tasks go to `agents/{dept}/state/incoming/`. DeptHead→PD tasks go to `{project}/memory/inter-spawn-tasks/incoming/`.

**Conflict resolution:** PD ↔ Dept Head conflicts escalate to Parent AI (Level 1), weighted by severity and financial importance.

**PD bypass authority:** Project Directors have Tier 1 bypass authority within project scope, bounded by scope.json. Bypass is limited to: file edits <10 lines, read-only operations, documentation within project boundaries. Bypass does NOT include: shared infra changes, cross-project side effects, user-facing decisions, security/auth/payment operations, PII handling, or any scope.json-external changes. Directors must send decision logs to their Dept Head for visibility — not approval, just audit trail.

**Status reporting:** On-demand only. Dept heads request status from members/projects as needed. No automated loops. This keeps parent AI context at O(departments + exceptions) rather than O(agents).

**Model tiering:** All 161 agents tagged with `modelTier` in frontmatter. Leaders = Opus. Members = Sonnet. Planning/thinking = Opus. Execution = Sonnet. Menial tasks (scraping, research) = Haiku.

**Status loop policy:** Automated recurring loops are DISABLED. Use on-demand status checks only. Dept heads request status when needed — do not automate periodic pings. This avoids the token explosion risk of naive 15-30 min loop implementations (10k-21k reports/week without aggregation). See § on status reporting.

---

## Org Chart

```
THE AGENCY
│
├── COUNCIL CHAIR (parent AI)
│
├── ENGINEERING ────────────────── 16 agents ── Backend Architect ★
│   ├── Sub-groups: security | blockchain
│   └── Members: Frontend Developer, Mobile App Builder, AI Engineer,
│       DevOps Automator, Rapid Prototyper, Senior Developer,
│       Security Engineer, Autonomous Optimization Architect,
│       Embedded Firmware Engineer, Incident Response Commander,
│       Solidity Smart Contract Engineer, Technical Writer,
│       Threat Detection Engineer, WeChat Mini Program Developer
│
├── DESIGN ─────────────────────── 8 agents ── Brand Guardian ★
│   └── Members: UI Designer, UX Researcher, UX Architect,
│       Visual Storyteller, Whimsy Injector, Image Prompt Engineer,
│       Inclusive Visuals Specialist
│
├── GAME DEVELOPMENT ────────────── 18 agents ── Game Designer ★
│   ├── Sub-groups: unity | unreal-engine | godot | roblox-studio
│   └── Members: Level Designer, Technical Artist, Game Audio Engineer,
│       Narrative Designer
│       + Unity: Unity Architect, Shader Graph Artist, Multiplayer Engineer,
│         Editor Tool Developer
│       + Unreal: Systems Engineer, Technical Artist, Multiplayer Architect,
│         World Builder
│       + Godot: Gameplay Scripter, Multiplayer Engineer, Shader Developer
│       + Roblox: Systems Scripter, Experience Designer, Avatar Creator
│
├── MARKETING ───────────────────── 17 agents ── Growth Hacker ★
│   ├── Sub-groups: china (8 agents)
│   ├── China team: Xiaohongshu Specialist, WeChat Official Account Manager,
│       Zhihu Strategist, Baidu SEO Specialist, Bilibili Content Strategist,
│       Carousel Growth Engine, China E-Commerce Operator, Kuaishou Strategist
│   └── Members: Content Creator, Twitter Engager, TikTok Strategist,
│       Instagram Curator, Reddit Community Builder, App Store Optimizer,
│       Social Media Strategist, SEO Specialist
│
├── CONTENT CREATION ────────────── 25 agents ── Chief Content Officer ★
│   ├── Sub-lead: Content Director (Opus)
│   ├── Sub-groups: social-media (12 agents)
│   ├── Social Media: LinkedIn Writer, Twitter/X Writer, Instagram Writer,
│   │   TikTok Writer, Reddit Writer, Threads Writer, Facebook Writer,
│   │   Discord Writer, YouTube Writer, Pinterest Writer, Quora Writer,
│   │   Telegram Writer
│   └── Members: Blog & Article Writer, Case Study & Whitepaper Writer,
│       Newsletter & Editorial Writer, Ad Copywriter, Landing Page Copywriter,
│       Email Campaign Writer, Video Script Writer, Technical Writer (Content),
│       Presentation Creator, Press & PR Writer, Content Editor
│
├── SALES ───────────────────────── 8 agents ── Sales Coach ★
│   └── Members: Outbound Strategist, Discovery Coach, Deal Strategist,
│       Sales Engineer, Proposal Strategist, Pipeline Analyst,
│       Account Strategist
│
├── PAID MEDIA ──────────────────── 7 agents ── PPC Campaign Strategist ★
│   └── Members: Search Query Analyst, Paid Media Auditor,
│       Tracking & Measurement Specialist, Ad Creative Strategist,
│       Programmatic & Display Buyer, Paid Social Strategist
│
├── PRODUCT ─────────────────────── 4 agents ── Sprint Prioritizer ★
│   └── Members: Trend Researcher, Feedback Synthesizer,
│       Behavioral Nudge Engine
│
├── PROJECT MANAGEMENT ─────────── 6 agents ── Studio Producer ★
│   └── Members: Project Shepherd, Jira Workflow Steward,
│       Senior Project Manager, Studio Operations, Experiment Tracker
│
├── TESTING ─────────────────────── 8 agents ── Reality Checker ★
│   ├── Sub-groups: validation | analysis | performance
│   └── Members: Evidence Collector, Test Results Analyzer,
│       Performance Benchmarker, API Tester, Tool Evaluator,
│       Workflow Optimizer, Accessibility Auditor
│
├── OPERATIONS ──────────────────── 6 agents ── Infrastructure Maintainer ★
│   └── Members: Support Responder, Analytics Reporter, Finance Tracker,
│       Legal Compliance Checker, Executive Summary Generator
│
├── CAREER ───────────────────────── 7 agents ── career-ops PD ★
│   └── Members: Offer Evaluator, Job Portal Scanner, CV Specialist,
│       Pipeline Strategist, Batch Processing Lead,
│       Pattern Analysis Specialist, Application Form Assistant
│
├── SPECIALIZED ───────────────── 17 agents ── Agents Orchestrator ★
│   ├── Sub-groups: infra | audit | advisory
│   ├── Infra team (5): Agents Orchestrator, Identity Graph Operator,
│       Agentic Identity & Trust Architect, LSP/Index Engineer,
│       RoomManager
│   ├── Audit team (3): Compliance Auditor, Blockchain Security Auditor,
│       Model QA Specialist
│   ├── Advisory team (1): Efficiency Advisor Loop
│   └── Members: Sales Data Extraction Agent, Data Consolidation Agent,
│       Report Distribution Agent, ZK Steward, Cultural Intelligence
│       Strategist, Developer Advocate, Vietnamese Text Agent,
│       Paperclip Control Plane ★
│
├── CRITIQUES ───────────────────── 12 agents ── Curmudgeon-in-Chief ★
│   └── Members: critique-design (Playwright, visual/contrast/layout),
│       critique-content (copy/voice/diacritics/AI-slop),
│       critique-marketing (positioning/funnel/ICP/CTA),
│       critique-pedagogy (teaching effectiveness/scaffolding/demo ratio),
│       critique-seo (SEO/GEO/AEO), critique-product (UX/IA/usability),
│       critique-security (injection/auth/misconfig),
│       critique-brand (voice/visual identity/positioning drift),
│       critique-video (pacing/captions/visual continuity/hook/audio sync),
│       critique-data (chart honesty/stat accuracy/accessibility/dashboard UX),
│       critique-code (readability/complexity/error handling/dead code)
│
├── SPATIAL COMPUTING ───────────── 6 agents ── XR Interface Architect ★
│   └── Members: macOS Spatial/Metal Engineer, XR Immersive Developer,
│       XR Cockpit Interaction Specialist, visionOS Spatial Engineer,
│       Terminal Integration Specialist
│
└── VIDEO STUDIO ────────────────── 17 agents ── Video Studio Director ★
    ├── Sub-groups: pre-production (3) | production (3) | post-production (5) | distribution (3) | qa (2)
    ├── Pre-production: Storyboard Artist, Shot Planner, Voice & Cast Director
    ├── Production: Screen Recording Director, AI Video Producer, Animation Director
    ├── Post-production: Video Editor, VFX & Motion Designer, Colorist & Audio Engineer,
    │   Captioning Specialist, Thumbnail Designer
    ├── Distribution: Platform Formatter, Video SEO Specialist, Upload Automator
    └── QA: Video Quality Reviewer, Video Accessibility Auditor
```

---

## Leadership Table

| # | Leader | Department | Sub-groups | Key Responsibilities |
|---|--------|-----------|------------|---------------------|
| 1 | Backend Architect | Engineering | security, blockchain | API design, database architecture, scalability, technical standards |
| 2 | Brand Guardian | Design | — | Brand consistency, visual identity, creative direction |
| 3 | Game Designer | Game Development | unity, unreal-engine, godot, roblox-studio | Game mechanics, narrative, cross-engine creative vision |
| 4 | Growth Hacker | Marketing | china (8 agents) | Growth strategy, user acquisition, China market expansion |
| 5 | Chief Content Officer | Content Creation | social-media (12 agents) | Editorial standards, content pipeline, quality gates, all content formats |
| 6 | Sales Coach | Sales | — | Deal strategy, pipeline health, team enablement |
| 7 | PPC Campaign Strategist | Paid Media | — | Paid acquisition, campaign optimization, ROI |
| 8 | Sprint Prioritizer | Product | — | Roadmap prioritization, sprint planning, feature scoping |
| 9 | Studio Producer | Project Management | — | Production pipeline, milestone tracking, cross-team coordination |
| 10 | Reality Checker | Testing | validation, analysis, performance | Test strategy, quality gates, performance benchmarks |
| 11 | Infrastructure Maintainer | Operations | — | Systems reliability, analytics, finance/legal/compliance |
| 12 | Agents Orchestrator | Specialized | infra, audit | Agent lifecycle, identity/trust, code intelligence, auditing |
| 13 | career-ops PD | Career | — | Job search pipeline: scanning, evaluation, CV generation, tracking, rejection analysis |
| 14 | XR Interface Architect | Spatial Computing | — | XR/AR/VR strategy, visionOS, Apple platform spatial experiences |
| 15 | Paperclip Control Plane | Specialized | — | Zero-human company orchestration, agent workforce management, cost governance |
| 16 | RoomManager | Specialized | infra | Multi-agent chat rooms, active polling, member notifications, shared context management |
| 17 | Video Studio Director | Video Studio | pre-production, production, post-production, distribution, qa | Video quality standards, production workflows, platform distribution, script-to-screen pipeline |
| 17 | Curmudgeon-in-Chief | Critiques | — | Scored multi-axis critique of any deliverable; routes to specialist critics |

---

## Agency Council

The **Agency Council** is the governing body for all cross-department decisions. It consists of all 14 department leaders reporting to the Council Chair (the parent AI).

### Council Members

| Member | Role | Department | Communication |
|--------|------|-----------|---------------|
| Backend Architect | engineering-lead | Engineering | SendMessage to `engineering-lead` |
| Brand Guardian | design-lead | Design | SendMessage to `design-lead` |
| Game Designer | game-development-lead | Game Development | SendMessage to `game-development-lead` |
| Growth Hacker | marketing-lead | Marketing | SendMessage to `marketing-lead` |
| Chief Content Officer | content-creation-lead | Content Creation | SendMessage to `content-creation-lead` |
| Sales Coach | sales-lead | Sales | SendMessage to `sales-lead` |
| PPC Campaign Strategist | paid-media-lead | Paid Media | SendMessage to `paid-media-lead` |
| Sprint Prioritizer | product-lead | Product | SendMessage to `product-lead` |
| Studio Producer | pm-lead | Project Management | SendMessage to `pm-lead` |
| Reality Checker | testing-lead | Testing | SendMessage to `testing-lead` |
| Infrastructure Maintainer | operations-lead | Operations | SendMessage to `operations-lead` |
| Agents Orchestrator | specialized-lead | Specialized | SendMessage to `specialized-lead` |
| XR Interface Architect | spatial-lead | Spatial Computing | SendMessage to `spatial-lead` |
| Curmudgeon-in-Chief | critiques-lead | Critiques | SendMessage to `critiques-lead` |

### Council Communication Protocol

Leaders communicate with the Council Chair (parent AI) using this format:

```
TO: council-chair
TYPE: [coordination_request | approval_request | status_report | escalation | handoff]
DEPARTMENT: [your department]
PRIORITY: [low | medium | high | critical]
IMPACT: [tier-1 | tier-2 | tier-3]
---
[Message content]
```

For full protocol details, see `runbooks/department-lead-protocol.md`.

---

## Department Directory

| Department | Directory |
|-----------|-----------|
| Career | `career/` |
| Engineering | `engineering/` |
| Design | `design/` |
| Game Development | `game-development/` |
| Marketing | `marketing/` |
| Marketing (China sub-team) | `marketing/china/` |
| Content Creation | `content-creation/` |
| Content Creation (Social Media sub-team) | `content-creation/social-media/` |
| Sales | `sales/` |
| Paid Media | `paid-media/` |
| Product | `product/` |
| Project Management | `project-management/` |
| Testing | `testing/` |
| Operations | `operations/` |
| Specialized | `specialized/` |
| Specialized (Infra sub-team) | `specialized/infra/` |
| **Rooms Infrastructure** | `~/.claude/agency-rooms/` — persistent file-based chat rooms for inter-agent communication, NEXUS handoffs, and escalation routing |
| **RoomManager** | `specialized/infra/room-manager.md` — always-on via 15-min cron polling |
| Specialized (Audit sub-team) | `specialized/audit/` |
| Spatial Computing | `spatial-computing/` |

---

## Team Infrastructure

### Team Types

| Team | Purpose | Members | Created By |
|------|---------|---------|------------|
| **Agency Council** | Governing body for cross-dept strategy and approval | All 12 leaders + Council Chair | See below |
| **Project Teams** | Temporary teams for specific deliverables | Relevant leaders + members per project type | Run kickoff protocol |
| **Department Teams** | Standing teams within each department | Leader + their members | Implicit; members exist at department paths |

### Project Team Templates

Reference `runbooks/project-team-templates.md` for pre-defined compositions:

| Template | Use Case |
|----------|----------|
| `template-full-team` | Complex multi-domain, strategic initiatives |
| `template-engineering-team` | Feature development, product builds, infrastructure |
| `template-gtm-team` | Launches, campaigns, customer acquisition |
| `template-games-team` | Game projects, interactive experiences |
| `template-custom-team` | Focused projects with clear boundaries |

### Coordination Convention

```
Human / Parent AI
       │
       ▼ (assigns work)
  Council Chair
       │
       ├──► Department Leader (approves Tier 1, escalates Tier 2/3)
       │         │
       │         └──► Department Member (executes)
       │
       ▼ (council assembly for cross-dept problems)
  Agency Council (all 12 leaders)
```

Leaders message the Council Chair. Members report to their leader. Cross-dept requests go through leaders to the Council Chair for routing.

---

## Approval Tiers Summary

Reference `runbooks/escalation-protocol.md` for the full detail.

| Tier | Approver | Examples | Response |
|------|----------|----------|----------|
| **Tier 1** | Department Leader | File edits <10 lines, read-only commands, documentation, code review | Immediate |
| **Tier 2** | Council Chair (parent AI) | New files, code changes >10 lines, config changes, deps, migrations | Within session |
| **Tier 3** | Human | Destructive ops, deployments, external comms, secrets, financial | Human availability |

---

## Department Operations (Dept-Coord System)

Each department has a persistent operational state at `{dept}/state/`, `{dept}/pipelines/`, `{dept}/protocols/`, and `{dept}/memory/`. This enables department heads to manage pipelines, improve protocols, and track member utilization across sessions.

### Department Decomposition Levels (D-Levels)

| Level | Owner | Ceiling | Example |
|-------|-------|---------|---------|
| D1 | Dept Head | — | "Improve content production pipeline" |
| D2 | Dept Head | — | "Writer briefing", "Quality gate automation" |
| D3 | Dept Head breaks, Dept-Coord takes | Hard stop for Dept Head | "Redesign writer briefing" |
| D4-D5 | Dept-Coord | — | "Draft brief sections", "Create example" |
| D6 | Dept-Coord assigns, Dept-Member executes | Hard stop for Dept-Coord | "Write the template — one file" |

### Department State Structure

```
{dept}/
├── state/
│   ├── dept-state.md          # Live snapshot (max 20 lines) — read on every spawn
│   ├── member-roster.md       # Utilization + skill tracking
│   ├── active-coords.md       # Append-only DC status log
│   └── incoming/              # Inter-spawn tasks from PDs
├── pipelines/
│   ├── INDEX.md               # Pipeline registry (name, version, status)
│   └── {name}/pipeline.md     # Versioned pipeline definition
├── protocols/
│   ├── INDEX.md               # Protocol registry
│   └── {name}.md              # Versioned protocol definition
├── memory/
│   ├── decisions.md           # Dept-level decisions (append-only)
│   ├── lessons.md             # Dept-level lessons (append-only)
│   └── retros/                # Monthly retrospective records
└── scratch/
    ├── dept-scratch.md        # Active session scratch
    └── coords/                # DC-* scratch files
```

### Key Skills

| Skill | Purpose |
|-------|---------|
| `/dept-resume [slug]` | Read dept-state.md, spawn dept head with lean briefing |
| `/dept-wrap [slug]` | Write dept-state.md + member-roster.md at session end |
| `/dept-status [slug]` | Read-only status digest (no spawns) |

### Key Runbooks

| Runbook | Purpose |
|---------|---------|
| `dept-coord-protocol.md` | Full operational manual for the dept-coord system |
| `dept-boot-sequence.md` | Two-mode dept head startup (spawn + route) |
| `protocol-registry.md` | Cross-department protocol index |

---

## How to Spawn the Agency Council

### Trigger Phrases

Any of these activate the full Agency Council:

> **"BOD"** / **"assemble"** / **"assemble the board"** / **"the board"** / **"the council"** / **"activate the agency council"**

Also: *"convene the council"*, *"call the board to order"*, *"full agency"*, *"all hands"*, *"agency-wide [project]"*.

For focused teams, the trigger phrases include project type:
- *"engineering team for [project]"*
- *"gtm team for [launch]"*
- *"marketing campaign"*

### Spawning Steps

```
1. Use TeamCreate to create a team named "agency-council"
2. Spawn leaders in TWO WAVES to avoid team config race conditions:
   Wave 1 (6 agents): engineering-lead, design-lead, game-development-lead,
                       marketing-lead, content-creation-lead, sales-lead
   Wave 2 (7 agents): paid-media-lead, product-lead, pm-lead, testing-lead,
                       operations-lead, specialized-lead, spatial-lead
   Wait for Wave 1 to join (~30s) before spawning Wave 2.
3. Each spawn: Load the leader's agent definition file and instruct them to
   join "agency-council" and send their intro to "team-lead"
4. You (parent AI) are the council chair
5. Send a welcome brief to all leaders explaining current priorities
6. Leaders operate per runbooks/department-lead-protocol.md
```

**Important:** Spawning more than 6 agents in parallel causes race-condition
writes to the team config file, breaking late-joiners. Always use two waves.

For a project-specific team, use the kickoff protocol in `runbooks/project-kickoff-protocol.md`.

---

---

## Project Scope Management

Every active project has a `scope.json` defining its boundaries. This is the contract between the Project Director and the parent AI.

### scope.json Schema

```json
{
  "id": "project-slug",
  "name": "Project Name",
  "directories": ["path/**"],
  "filePatterns": ["*.ext"],
  "excludedPaths": [],
  "departments": ["engineering", "design"],
  "financialImportance": "low | medium | high",
  "directorId": "project-slug-pd",
  "assistantId": null,
  "memberIds": []
}
```

### Scope Enforcement Rules

1. **PD actions within scope**: File edits, read-only ops, documentation — Tier 1 bypass, no approval needed.
2. **PD actions outside scope**: All changes to files/paths not in scope.json require parent AI approval (Tier 2).
3. **Shared infra / cross-project**: Always requires parent AI approval regardless of scope.
4. **Scope review cadence**: scope.json is reviewed quarterly or when project scope changes materially.
5. **Approvals directory**: Each project has a `/{project}/approvals/` directory for logging approval requests and outcomes.

### Project Directory Structure

Each project directory follows this memory structure:
```
{project}/
├── scope.json           # Director: boundaries and authority
├── approvals/           # Director: approval request log
└── memory/
    ├── sessions/        # All: session logs (append-only)
    ├── decisions.md    # Director: architectural decisions (append-only)
    ├── lessons/        # All: synced from root lessons
    └── status/         # PM: on-demand status summaries (append-only)
```

---

*Last updated: 2026-05-02*
