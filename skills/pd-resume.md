---
name: pd-resume
description: >
  Orchestrate a multi-PD session: recall + spawn PDs in parallel, all fully autonomous.
  Invoke as /pd-resume [all | project-slug]. At session start, /pd-resume reads
  each project's save-state files (next-session.md, heartbeat.md, decisions.md),
  assembles a brief but specific recall briefing per project, then spawns all PD
  coordinators simultaneously with briefings pre-loaded so they begin work instantly.
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

## Rule 2 — Parallel Subagent Deployment

After decomposing, deploy **one subagent per sub-task** in a single message using the
`Agent` tool. All subagents launch simultaneously — never sequentially.

Spawn format per subagent:
- `description`: short label for tracking (e.g. "auth-endpoint", "login-ui")
- `prompt`: the sub-task with full context — goal, file paths, constraints
- `subagent_type`: match the task domain (frontend, backend, general-purpose, etc.)
- `run_in_background: true`

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
and not a courtesy — it is how Tekki tracks portfolio-wide work in real time.

## Skeleton Prompt for PD Spawn

Use this as the spawn prompt for every PD (fill in project-specific fields):

```
You are resuming work on {project-name}. Your recall briefing from the last session is below.
Read it carefully — this is your context. Start the stated 'Next' action immediately.

============================================
{recall-briefing}
============================================

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

Accept an argument: `all` (default) or a specific project slug.
- `all` → resume all projects from medium-term.md
- `marketsenseapp` → resume only MarketSenseApp
- Multiple slugs separated by comma → resume listed projects

## Step 2 — Spawn Recall Subagents in Parallel

For each target project, spawn a **general-purpose sonnet subagent** that reads the project's
save-state files and writes the briefing to a temp file. Spawn all in parallel.

For each target, spawn:

Subagent prompt:

"Read-only briefing for {project}. Do NOT write any files except your output file.

FILES TO READ:
- {project}/memory/next-session.md
- {project}/memory/heartbeat.md
- {project}/memory/decisions.md
- {project}/.claude/save-state-state.json (if it exists)

OUTPUT FORMAT (write exactly this to /tmp/pd-resume-{slug}.briefing):

RECALL — {slug}

Phase: [current phase or status]
Next: [specific action — one sentence]
Blockers: [list one per line, or "none"]
Decisions: [top 2 locked decisions, one per line, or "none"]
Mid-flight: [1-2 mid-flight files, one per line, or "none"]
Context: [what was happening last session — 1-2 sentences]

RULES:
- Read-only. Do NOT write or edit any project files.
- If a file doesn't exist, skip that field and note "N/A".
- Keep every field to 1-2 lines max.
- Be specific — "fix BottomNav.tsx mobile layout" not "fix bugs".
- Output to /tmp/pd-resume-{slug}.briefing only. Then stop. No other files."

subagent_type: general-purpose
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

## Step 4 — Spawn PD Coordinator with Briefing

For each project, spawn a **pd-coordinator** subagent (Opus) with the briefing
pre-loaded. Spawn all in parallel.

Agent template: `~/.claude/agents/project-management/pd-coordinator.md`

Spawn prompt for each target:

```
You are PD-{slug}, resuming work on {project-name}.
Your recall briefing from the last session is below.
Read it carefully — this is your context. Start the stated 'Next' action immediately.

============================================
{recall-briefing}
============================================

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

**Subagent config:**
- `subagent_type`: general-purpose
- `model`: opus (overrides default — pd-coordinator requires Opus)

Wait for all PD Coordinators to report back. Then output:

```
PD RESUME — {n} projects

{slug} — [phase from briefing] — spawned
  next: [next action]
  blockers: [blockers or "none"]

[...one per project...]

All PDs running. Results arrive as each completes.
```
