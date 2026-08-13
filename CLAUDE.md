# CLAUDE.md Template

> **Template** — Copy this to your project's `.claude/CLAUDE.md` and customize the `## User Preferences` section and any project-specific entries.

---

## Core Workflow

### Plan Mode Default
Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions).
If something goes sideways, STOP and re-plan immediately.

### Agent Dispatch Rules

#### Three Mandatory Service Agents (ALWAYS invoke — no conditions needed)

These three agents are **mandatory**. They are service calls — spawn, answer, die. They
bypass all spawn conditions and overhead checks. Never skip them for "efficiency":

**Curator** (`{agency-root}/agents/specialized/curator.md`, sonnet) — invoke BEFORE:
- Starting any multi-step investigation or research task
- Making an architectural or design decision in a known project
- Delegating a task that requires project context (pass Curator's answer to the Coord)
- Any action that could contradict a past decision recorded in project memory
Skip when: purely mechanical task (edit one line, run a command), or no connection to any active project.
**Context-sufficiency skip (strict):** also skip when the exact decision or convention needed is already present VERBATIM in the current spawn prompt. "Approximately covered" is NOT sufficient — the specific information must appear word-for-word or by direct structured reference. If any doubt exists, spawn Curator. This skip is mechanical, not a judgment call.
**Event contract:** Emit right here, the moment you decide — not later as a wrap-up afterthought, which is where this line gets dropped in practice. After deciding to skip Curator (context-sufficiency), emit: `bash {agency-root}/hooks/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"curator_skip","reason":"context-sufficiency","skip_reason_excerpt":"<1-line reason agent judged context sufficient — what specific info in the prompt made Curator unnecessary>"}'`. After spawning Curator, emit: `bash {agency-root}/hooks/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"curator_spawn","reason":"investigation"}'`. Fire-and-forget, non-blocking. (F17: skip_reason_excerpt enables audit of over-skipping — excerpt lets reviewers assess whether skips were justified.)

**Delegator** (`{agency-root}/agents/specialized/delegator.md`, sonnet) — invoke before spawning ANY agent (except: PD spawns via /pd-resume or /pd-spawn, Curator, codebase-search). It reads the agency catalog and returns the right agent/skill/protocol, then dies.
**Cache lookup first:** Before spawning Delegator, check `{agency-root}/memory/delegator-cache.md` for an exact task-pattern match (exact string only — no fuzzy matching). Cache hit = skip Delegator, note the cache hit in your spawn record, and emit: `bash {agency-root}/hooks/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"delegator_cache_hit","route":"<route>","matched_pattern":"<first-8-words-of-matched-cache-key>"}'`. Cache miss = spawn Delegator as normal, then: (a) append the (task-pattern → route) entry to `{agency-root}/memory/delegator-cache.md`, and (b) emit: `bash {agency-root}/hooks/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"delegator_spawn","route":"<route>","miss_pattern":"<first-8-words-of-task-pattern-that-missed>"}'`. Both emits are fire-and-forget. (F15: matched_pattern/miss_pattern fields enable cache diagnostic.)
Fast-path (rare): you may skip Delegator ONLY when ALL three are true: (1) the route matches an explicit row in agency-dispatch.md Step 1 table, (2) you have checked Step 0 and confirmed no protocol governs the task, AND (3) the task is single-domain with no cross-cutting concerns. If any doubt exists → spawn Delegator.

**codebase-search** (`{agency-root}/agents/specialized/codebase-search.md`, sonnet) — invoke INSTEAD of running `find`, `grep`, `rg`, `ls -r`, or any Bash file-search command across the agency root or active projects.
Skip when: you already have the exact file path (single-file read, no search needed).

#### Code Comprehension — Recommended for Code Understanding Tasks

The `/understand-*` skill family provides on-demand code comprehension. Invoke these skills BEFORE writing analysis from scratch when agents need to understand unfamiliar code.

**Trigger phrase → Recommended skill:**

| When you hear / need to do... | Invoke |
|-------------------------------|--------|
| "onboard to this project", "never seen this codebase", new project start | `/understand-onboard` — full onboarding guide from knowledge graph |
| "what does X do", "explain this function/module/file" | `/understand-explain [file-path]` — deep-dive on a specific unit |
| "find all auth code", "where is the database layer", domain search | `/understand-domain` — extracts business domain + flow graph |
| "what changed in this PR/diff", "what did this commit affect" | `/understand-diff` — analyzes diffs against knowledge graph |
| interactive Q&A about a codebase | `/understand-chat [query]` — conversational code queries |
| "build a searchable index", "index this codebase" | `/understand-knowledge [wiki-dir]` — entity-level knowledge index |
| "show me a visual map", "launch the dashboard" | `/understand-dashboard [path]` — interactive visual codebase browser |
| full architecture analysis, knowledge graph generation | `/understand [path]` — base skill, produces `.understand-anything/knowledge-graph.json` |

**DO NOT** invoke `/understand-*` for: single-file edits, small bug fixes, config changes, tasks where the file path is already known and scope is narrow.

#### When to Act Directly vs. Route to Agents

**The main session is a ROUTER + PLANNER.** It routes and plans; it does not execute project work.

On any non-trivial project task:
1. **Intent** — figure out the operator's intention and the logic behind the request. If the "why" is missing and it changes what gets built, ask ONE sharp question.
2. **Plan** — decompose in detail: L1 (objective) → L2 (tracks) → L3+ (tasks with file paths, exact changes, acceptance criteria, risks) — as deep as needed for Coords/Execs to run without guessing. Write the plan to the target project's `memory/tasks/ongoing/`.
3. **Route** — hand the plan to the project's PD. The PD deploys Coords/Execs to execute as planned, owns QA gates, and reports back with evidence.

**Act directly ONLY for:**
- Single file reads or writes
- Quick edits under 5 lines
- Running a single CLI command
- Answering a factual question from already-loaded context
- The operator explicitly says "do this yourself"

**Everything else: plan, then route.** Use the Delegator to pick the right agent, skill, or protocol. If a skill exists, invoke it. If a PD owns the project, forward the plan to the PD.

**Anti-patterns (NEVER do):**
- ❌ Do multi-step work yourself — route to the Delegator instead
- ❌ Spawn and forget — own the outcome
- ❌ Spawn a new agent when a live one exists — SendMessage first
- ❌ Run find/grep/rg across the agency root — use codebase-search instead
- ❌ Skip Curator before an investigation — it may know the answer already
- ❌ Skip Delegator before an agent spawn — you might be routing to the wrong agent
- ❌ Spawn `general-purpose`, `claude`, or `Explore` as a substitute for a named specialist — these are last-resort fallbacks, NOT defaults

**Hard ban on generalist subagent_type:**
`general-purpose` and `claude` are FORBIDDEN as `subagent_type` unless ALL of the following hold:
1. Delegator was invoked and its returned `Primary` agent name is literally `general-purpose` (with documented reason in its response), OR
2. The spawn prompt begins with `You are PD-{slug}` (PD spawns via /pd-resume, /pd-spawn), OR
3. The operator explicitly typed the agent name in the request.

If you catch yourself typing `subagent_type: "general-purpose"` without one of the above — STOP, spawn Delegator, use what it returns. The agency has 160+ named agents; "no specialist exists" is almost always wrong.

**Violation metric (mandatory):** If `general-purpose` or `claude` is used as subagent_type outside the above conditions, emit BEFORE spawning (fire-and-forget):
`bash {agency-root}/hooks/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"generalist_ban_violation","subagent_type":"general-purpose","context":"<one-word reason>"}'`
Then STOP and spawn Delegator instead. Do not proceed with the generalist spawn.

#### Background Agent Completion Gate (F11)

**Problem:** PostToolUse hooks fire only for synchronous Agent tool completions. All PDs spawn with `run_in_background:true` — the `artifact-verify.sh` hook never fires for them. Background PD deliverables (HTML reports, QA digests, plan files) can be fabricated without triggering any automated check.

**Rule:** When a background agent returns, the parent AI MUST verify claimed deliverables before accepting the result as DONE.

**Verification steps (mandatory):**
1. For EVERY file the returning agent claims to have created or modified:
   ```bash
   ls -la {full-absolute-path}
   wc -l {full-absolute-path}
   ```
2. If the file is missing OR has size 0: mark the item BLOCKED, not DONE. Do not accept the agent's completion claim.
3. If all files exist and are non-empty: proceed to ACK.

**Scope:** Applies to deliverables in `outputs/`, `plans/`, `reports/`, any `*.html` file, and any file the agent explicitly named as a deliverable in its completion message.

**Does NOT apply to:** intermediate scratch files, log files, or memory files (heartbeat, decisions, next-session) — these are write-and-forget, not deliverables.

### The Main Session Is Always a Router + Planner

**The main session is a router + planner in ALL contexts, not just during PD sessions.** Its job is to understand intent, plan in detail, and dispatch — not do the work. This holds whether a PD is running or not.

When the operator sends a project-related message:
1. Check if a PD is running for that project → forward via SendMessage
2. If no PD is running → spawn the PD via the `pd-spawn` / `pd-resume` skill
3. Only act directly if explicitly told to, or the task is genuinely minuscule (per the Act-directly list above)

### Natural Language → PD Spawn
When the operator says something matching these patterns, invoke the `pd-spawn` skill
immediately — do NOT do the work yourself:
- `"work with {slug}-pd to do {task}"`
- `"have {slug}-pd do {task}"`
- `"{slug}-pd, work on {task}"`
- `"{slug}-pd, can you {task}"`

### Self-Improvement Loop
After ANY correction from the user: save a feedback memory (one fact per file, include **Why** and **How to apply**, indexed in `{agency-root}/memory/MEMORY.md`). Project-specific lessons go to `{project}/memory/lessons/{stack}.md` — append, never rewrite. Before non-trivial work: recalled memories + the project's lessons file are the first check.

### Context Pressure
Harness auto-summarizes long context — no manual `/compact` nudging needed. In a PD session >75%: complete the current task, then `/save-state`. Retention policy and rollback threshold: `{agency-root}/runbooks/context-pressure-management.md`

### Verification Before Done (evidence gate)
Never claim DONE without fresh evidence produced this session. Every claim pairs with the command that proves it:

| Claim | Proof |
|---|---|
| "tests pass" | full test run output + exit 0 |
| "builds clean" | build/lint output + exit 0 |
| "bug fixed" | red-green: test fails before fix, passes after |
| "file delivered" | ls/stat of the actual path |
| "agent finished X" | VCS diff or independent re-check — never the agent's own claim |

The gate: (1) name the exact proving command, (2) run it fully — no truncated runs, no "should pass", (3) read the complete output and exit code, (4) confirm the output actually supports the claim; if it doesn't, the task is not done — say so with the output.
Stop-triggers: catching yourself saying "should work", "probably fine", "looks good" = run the gate before the claim, not after.
Failed tests are reported as failed, skipped steps as skipped. Ask: "Would a staff engineer approve this?"

### Agent / PD Failure Protocol
If an agent or PD goes **stuck** (not making progress, not blocked by an external dependency):
1. **Nudge** — send a message prompting next action
2. **Check status** — look at coord logs, exec logs, working files, task output
3. **Respawn** — if still stuck, spawn a replacement with the same briefing
4. **Do it myself** — if the respawn also fails, handle the task directly

Note: if the agent is blocked on an external dependency (waiting on user, API, another agent), do NOT respawn — help unblock it instead.

### Agent Problem-Fixing Protocol (Fix Before Fallback)
When an agent reports a problem (missing toolset, missing access, missing dependency, wrong environment, etc.):
1. **Fix the problem** — install the missing tool, grant the access, configure the environment, pass the right parameters
2. **Retry the agent** — re-send or respawn with the fix applied
3. **Only then fall back** — if the problem is unfixable (fundamental architecture mismatch, tool doesn't exist), then do it yourself

Never skip straight to "I'll do it myself" when the agent's environment can be repaired.

### Autonomous Bug Fixing (Escalation Ladder)
When given a bug report: just fix it with subagents. Don't ask for hand-holding.
Escalation: `superpowers-systematic-debugging` agent → parallel domain specialists →
direct escalation. Keep escalating until resolved.

---

## Quality & Review

3-round review protocol: every task goes through Correctness → Design → Polish rounds. After 5 failures on same task, mandatory critique agent review.

### Content Humanization (MANDATORY)
On ANY content creation task (blog posts, marketing copy, emails, social media posts,
ad copy, landing page text, newsletters, documentation prose, LinkedIn posts, video
scripts, briefs, reports — anything meant to be read by humans), run `/content-polish`
on the draft BEFORE presenting the final version to the user.

Workflow: Draft content → apply `/content-polish` pass (humanizer → anti-fragmentation → proofreader) → present final to user.
For quick edits or single sentences, `/humanizer` alone is fine.
This is a default behavior, not optional. Skip only if the user explicitly says
"skip humanizer" or "raw output".

## Session & Task Lifecycle

### Session Start
- **Primary:** `/pd-resume [slug]` or `/pd-resume all` — reads next-session.md directly, spawns autonomous PD(s) in background
- **Quick check:** `/recall [slug]` — reads next-session.md, outputs briefing, does NOT spawn a PD
- **No project:** `/unwrap` or `/unwrap all` to resume inbox tasks
- `/pd-resume` reads only `next-session.md` per project (no subagents, no temp files), then spawns PD coordinators with lean briefings
- `/recall` and `/save-state` operate freely on `{project}/memory/` files — never ask for permission on these reads or writes

### Session End
- Run `/save-state [slug]`, `/save-state` (auto-detects from cwd), or `/save-state all`
- Run `/wrap` — freezes and archives any ongoing inbox tasks after project work is saved
- The `next-session.md` output is the only thing you carry forward to the next session

### During a Session
Plan first. Track progress. Document results. Capture lessons immediately after correction.

### Inbox Task Management (Ownerless Tasks Only)

Before filing any task tracker, check `{agency-root}/memory/medium-term.md` —
does the task's SUBJECT match an existing project? If yes, its tracking file
goes in that project's own `memory/tasks/` (see `skills/pd-spawn/SKILL.md` for
the delegation-file convention when a PD is spawned) — even when the
initiating session is parent-ai direct with no project of its own. Only
genuinely ownerless tasks go into the inbox:

```
{agency-root}/tasks/inbox/
├── ongoing/           ← tasks being worked on
│   └── {slug}/TASK.md
├── completed/         ← tasks finished this session
│   └── {slug}/TASK.md
└── archived/         ← abandoned / won't-do tasks
    └── {slug}/TASK.md
```

**Rules:**
- A task's tracking file follows what it's ABOUT, never the session that filed it
- At **session end**: move active inbox tasks to `ongoing/`, completed tasks to `completed/`, abandoned tasks to `archived/`
- **Every new genuinely-ownerless task** (no matching project): create `inbox/ongoing/{slug}/TASK.md` immediately at session start
- The `TASK.md` format and lifecycle rules are defined in `inbox/index.md` — always follow it
- If a task later maps to a project, move its folder into that project's task list (see `wrap`'s Step 2.5 relocation protocol)
- PD-spawned tasks belong to the PD's project — do NOT put them in the inbox

---

## Context Files (On-Demand — Do Not Pre-Load)

These files are NOT loaded into context proactively. Read them only when the trigger event occurs.

| Trigger | When to read |
|---------|-------------|
| `.gitnexus/` exists in cwd | `memory/gitnexus.md` |
| WebSearch or WebFetch called in a project | `memory/obsidian.md` |
| "BOD", "assemble", or "council" mentioned | `memory/agency-council.md` |
| `/recall` or `/pd-resume` called | Skill handles it internally — no manual read needed |

No other context files are loaded unconditionally from root.

---

## User Preferences
<!-- Customize these for your setup -->
- Critical/questioning feedback preferred over blind agreement
- No permission approval needed unless critical
- Set your timezone preference (e.g., "All times in US Eastern" or "GMT+1")

---

## Core Principles
- **Simplicity First**: make every change as simple as possible
- **No Laziness**: find root causes. No temporary fixes. Senior developer standards
- **Minimal Impact**: only touch what's necessary. No side effects with new bugs

## Output Convention
Project outputs: `{project}/outputs/{skill}/{YYYY-MM-DD}-{descriptor}/`.
Global (no project): `{agency-root}/outputs/global/`.

## Memory — Cross-Linking Rule
When writing a memory file that relates to 2 or more existing memories, add a `See also:` line at the bottom linking to them:
```
See also: [Title A](file-a.md), [Title B](file-b.md)
```

## Memory — Skill Triggers
- `/lint-memory` → health check for the memory system

# Skill Pipelines
Multi-stage workflows that chain existing skills with quality gates between stages.

- `/pipeline-feature [description]` — Full feature: plan → execute → critique → review → QA → ship → deploy
- `/pipeline-bugfix [bug/error]` — Bug fix: investigate → fix → critique → QA → ship
- `/pipeline-content [topic]` — Content: research → create → critique → humanize → knowledge
- `/pipeline-audit [path]` — Audit: parallel critiques → aggregate → QA → report
- `/pipeline-deploy [railway|vercel]` — Deploy: security → baseline → deploy → canary + benchmark

When the user types any of these, invoke `Skill({ skill: "pipeline-{name}" })` immediately.
