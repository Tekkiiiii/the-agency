---
name: pd-resume
description: >
  Orchestrate a multi-PD session: recall + spawn PDs in parallel, all fully autonomous.
  Invoke as /pd-resume all (resume all projects) or /pd-resume [project-slug] (resume one project only).
  When a slug is given, only that single PD is spawned — never all. When "all" is used,
  every active project's save-state files are read in parallel, a recall briefing is assembled
  per project, and all PD coordinators are spawned simultaneously with briefings pre-loaded
  so they begin work instantly.
  Blocked projects surface as such. Useful when starting a session with multiple
  active projects — no manual reading required. Also for quickly auditing which
  projects are stale (stale last_session dates), for spinning up context on a
  new project before exploring it manually, and for confirming what each PD's
  next action should be without re-deriving it from memory files.
---

# PD Standard Protocol

**This section applies to ALL spawned PDs, every time they run.** Embed it verbatim in
every spawn prompt — no exceptions.

## Rule 1 — Decompose First

When you receive any task or work item — regardless of size — your **first action**
is to break it into the smallest possible independent sub-tasks.

Rule of thumb: if a sub-task can be done without waiting for another sub-task's
output, it is independent. Split along those lines.

Examples:
- ❌ "Build the auth flow" (one monolithic task)
- ✅ "Create user table schema", "Write /auth/register endpoint", "Write /auth/login endpoint",
  "Add JWT middleware", "Write login page component", "Write register page component"
  (six independent sub-tasks)

## Rule 2 — Agent Selection Hierarchy (MANDATORY)

When spawning a subagent, follow this order — do NOT default to general-purpose:

**Step 1 — Match from The Agency catalog first.**
Check if a named department lead, coordinator, or specialist agent fits the task domain:

| Task domain | Prefer this agent type |
|---|---|
| Research, analysis, investigation | `research-pd`, `Explore`, `Trend Researcher` |
| Frontend, UI, design | `Frontend Developer`, `UI Designer`, `Design Lead` |
| Backend, API, database | `Backend Architect`, `Data Engineer` |
| Full-stack / feature work | `Senior Developer`, domain-specific PD |
| Sales, pipeline, revenue | `Sales Lead`, `Deal Strategist`, `Account Strategist` |
| Marketing, content, growth | `Marketing Lead`, `Growth Hacker`, `Content Creator` |
| Operations, tracking, finance | `Operations Lead`, `Finance Tracker`, `Analytics Reporter` |
| Security, compliance, legal | `Security Engineer`, `Compliance Auditor` |
| Deployment, DevOps, infra | `DevOps Automator`, `Infrastructure Maintainer` |
| QA, testing, verification | `Testing Lead`, `Evidence Collector`, `qa` skill agent |
| Experiment design, A/B | `Experiment Tracker` |
| Proposal, RFP, deal | `Proposal Strategist`, `Deal Strategist` |
| HR, culture, ops | `Studio Operations` |
| Game dev | `Game Development Lead` |
| Spatial/VR/AR | `Spatial Computing Lead` |

**Step 2 — Route to existing specialized agents before general-purpose.**
Use `Agent({ subagent_type: "Explore" })` for research, `Agent({ subagent_type: "general-purpose" })` only as an absolute last resort when no named or domain agent fits.

**Step 3 — Fallback is general-purpose.**
Only use `general-purpose` when the task is truly generic and no catalog agent matches.

**All subagent spawn calls go in one message.** Do not wait for one to finish before
spawning the next.

## Rule 3 — Report Every Completion to team-lead

**Do NOT wait until all sub-tasks are done.** Send a message to "team-lead" via
SendMessage after EACH subagent finishes.

Completion format:
```
{subtask-label}: DONE — [1-sentence description of what was done]
```

Blocker format:
```
{subtask-label}: BLOCKED — [reason] — [suggested path forward or workaround]
```

The main session receives a live, chronological feed of progress. This is not optional
and not a courtesy — it is how the operator tracks portfolio-wide work in real time.

## Skeleton Prompt for PD Spawn

Use this as the spawn prompt for every PD (fill in project-specific fields):

**Before spawning, check if the project has an identity file.**
If `{project}/memory/{slug}-pd.md` exists, read it — it contains the PD's skills, context files, and spawner protocol.
If it does NOT exist, create it before spawning. See `/pd-spawn` SKILL.md for the format.

```
You are resuming work on {project-name}. Your recall briefing from the last session is below.
Read it carefully — this is your context. Start the stated 'Next' action immediately.

## Task Startup Behavior

**On every session start, read only `memory/tasks/ongoing/`** — not `completed/` or `revisions/`.
- Tasks in `ongoing/` = active work (INCOMING, IN_PROGRESS)
- Tasks in `completed/` = archived, not re-read unless asked
- Tasks in `revisions/` = superseded by revisions, read only when doing a revision

============================================
{recall-briefing}
============================================

## PD Directory (do not read — always embedded here)

| Project | Inbox name | Project Directory | Task Folder |
|---------|-----------|-------------------|-------------|
| {Project A} | {project-a}-pd | `{project-a-directory}` | `memory/tasks/` |
| {Project B} | {project-b}-pd | `{project-b-directory}` | `memory/tasks/` |

(Populate from your medium-term.md — this is the SSOT for project paths.)

## PD Standard Protocol — NON-NEGOTIABLE

You are bound by the following protocol on every task, every time:

1. DECOMPOSE: Break every task into the smallest possible independent sub-tasks.
   Do not do any work yourself until sub-tasks are decomposed.

2. PARALLELIZE: In a SINGLE message, spawn one Agent per sub-task.
   All subagents must be launched simultaneously. Do not wait between spawns.

3. REPORT: After EACH subagent completes, send a SendMessage to "team-lead":
   - DONE: "{subtask-label}: DONE — [brief description]"
   - BLOCKED: "{subtask-label}: BLOCKED — [reason] — [workaround]"
   Report immediately on completion, not at the end of all work.

Agent template: {path to PD .md file}

Start immediately on 'Next'. Do not re-read project docs unless the briefing says to.
When a task block is complete or you are blocked, run /save-state [{slug}] then stop.
```

---

# /pd-resume

Fully autonomous: spawns recall subagents, collects briefings, spawns PDs with briefings pre-loaded.

## SSOT: medium-term.md

The **primary source of truth** for project locations is `~/.claude/memory/medium-term.md`
— the Active Projects table. Read it FIRST.

## If Slug Not Found

1. Check `~/.claude/memory/medium-term.md` Active Projects table — the SSOT.
2. If not in medium-term.md → output:

   ```
   PROJECT NOT FOUND: {slug}
   Hint: Check ~/.claude/memory/medium-term.md for the current project list.
   ```

   **Stop.**

## Step 1 — Resolve Targets

Accept an argument: `all` (resume all projects from medium-term.md) or a single
project slug (resume only that project).
- `all` → resume every project listed in medium-term.md
- `{slug}` → resume only that project — spawn exactly one PD
- Multiple slugs separated by comma → resume listed projects only (not all)

**Important:** `/pd-resume [slug]` without the word `all` resumes exactly one project.
Use `all` only when you intentionally want to resume all active projects simultaneously.

## Step 2 — Spawn Recall Subagents in Parallel

For each target project, spawn an **Explore sonnet subagent** that reads the project's
save-state files and writes the briefing to a temp file. Spawn all in parallel.

For each target, spawn:

Subagent prompt:

"Read-only briefing for {project}. Do NOT write any files except your output file.

FILES TO READ:
- {project}/memory/next-session.md
- {project}/memory/heartbeat.md
- {project}/memory/decisions.md
- {project}/memory/tasks/ongoing/delegated-*.md (read ALL — check for "Completion" or "Blocker" sections)

OUTPUT FORMAT (write exactly this to /tmp/pd-resume-{slug}.briefing):

RECALL — {slug}

Phase: [current phase or status]
Next: [specific action — one sentence]
Blockers: [list one per line, or "none"]
Decisions: [top 2 locked decisions, one per line, or "none"]
Mid-flight: [1-2 mid-flight files, one per line, or "none"]
Delegated tasks: [list each delegated-*.md that has a "Completion" section → mark DONE; each with "Blocker" section → BLOCKED; each with neither → awaiting report]
Last Session: [from heartbeat.md Session End block: what was happening last session — 1-2 sentences; if no Session End block, use next-session.md content]

RULES:
- Read-only. Do NOT write or edit any project files.
- If a file doesn't exist, skip that field and note "N/A".
- Keep every field to 1-2 lines max.
- Be specific — "fix BottomNav.tsx mobile layout" not "fix bugs".
- Output to /tmp/pd-resume-{slug}.briefing only. Then stop. No other files."

subagent_type: Explore
model: sonnet

Collect all briefings. Wait for all subagents to complete.

## Step 3 — Read Briefings

For each project, read `/tmp/pd-resume-{slug}.briefing`. If a briefing file is missing or empty,
use this fallback for that project:

```
Phase: unknown
Next: read project docs and assess current state
Blockers: none
Decisions: none
Mid-flight: none
Context: no prior session found
```

## Step 3.5 — Graph enrichment (caller-side, parallel per project)

For each target project, call in parallel:

```
mcp__graphify__query_graph(question="{slug} architecture dependencies")
```

Append the top 5 returned node labels to each project's briefing as a **Graph context:** section before passing it to the PD coordinator in Step 4:

```
Graph context: <node1>, <node2>, <node3>, <node4>, <node5>
```

If the graphify MCP tool is unavailable, skip silently.

## Step 4 — Spawn PD Coordinator(s)

**If a single slug was given:** spawn exactly one PD coordinator with that briefing only.
**If `all` was given:** spawn one pd-coordinator per project in parallel.

Agent template: `~/.claude/agents/project-management/pd-coordinator.md`

Spawn prompt for each target:

```
You are PD-{slug}, resuming work on {project-name}.
Your recall briefing from the last session is below.
Read it carefully — this is your context. Start the stated 'Next' action immediately.

============================================
{recall-briefing}
============================================

## PD Directory (do not read — always embedded here)

| Project | Inbox name | Project Directory | Task Folder |
|---------|-----------|-------------------|-------------|
| {Project A} | {project-a}-pd | `{project-a-directory}` | `memory/tasks/` |
| {Project B} | {project-b}-pd | `{project-b-directory}` | `memory/tasks/` |

(Populate from your medium-term.md — this is the SSOT for project paths.)

## PD Standard Protocol — NON-NEGOTIABLE

You are bound by the following protocol on every task, every time:

1. DECOMPOSE: Break every task into the smallest possible independent sub-tasks.
   Do not do any work yourself until sub-tasks are decomposed.

2. PARALLELIZE: In a SINGLE message, spawn one Agent per sub-task.
   All subagents must be launched simultaneously. Do not wait between spawns.

3. REPORT: After EACH subagent completes, send a SendMessage to "team-lead":
   - DONE: "{subtask-label}: DONE — [brief description]"
   - BLOCKED: "{subtask-label}: BLOCKED — [reason] — [workaround]"
   Report immediately on completion, not at the end of all work.

Agent template: {path to pd-coordinator.md}
Model: Opus (pd-coordinator uses Opus, Coords use Opus, Executors use Sonnet)

Start immediately on 'Next'. Do not re-read project docs unless the briefing says to.
When a task block is complete or you are blocked, run /save-state [{slug}] then stop.
```

**Subagent config — MANDATORY HIERARCHY:**
- `subagent_type`: pd-coordinator (from Agency catalog — match domain first)
- `model`: opus
- **Never use general-purpose as default. Only fall back to general-purpose when no named or domain agent fits the task.**
- When spawning subagents FOR the PD coordinator's tasks, follow Rule 2 Agent Selection Hierarchy (check domain match first from the Agency catalog).

Wait for all PD Coordinators to report back. Then output:

```
PD RESUME — {n} projects

{slug} — [phase from briefing] — spawned
  next: [next action]
  blockers: [blockers or "none"]

[...one per project...]

All PDs running. Results arrive as each completes.
```
