---
name: pd-spawn
description: >
  Spawn another Project Director to do work on your behalf. The caller PD
  creates a briefing, tags the spawned PD in both projects' memory, then waits
  for a report. Use when the operator says "spawn {other-pd} to do X". The spawned PD
  works in its own project, reads only its identity + your briefing, and reports
  back when done.
triggerPatterns:
  - "work with {slug}-pd to"
  - "have {slug}-pd do"
  - "{slug}-pd, work on"
  - "{slug}-pd, can you"
---

# PD Spawn Protocol

Spawns another PD on the operator's command. Caller PD creates the briefing, spawns
the other PD, tracks the delegation in its own memory, and waits.

## Activation Triggers

This skill activates in two ways:

1. **Slash command:** `/pd-spawn`
2. **Natural language:** Any phrase matching one of these patterns:
   - `"work with {slug}-pd to do {task}"`
   - `"have {slug}-pd do {task}"`
   - `"{slug}-pd, work on {task}"`
   - `"{slug}-pd, can you {task}"`

When you hear a phrase matching any pattern above, invoke this skill immediately
— do not attempt to do the work yourself.

## SSOT: medium-term.md

The list of active PDs and their project paths is in `~/.claude/memory/medium-term.md`.

## Step 1 — Identify the Target PD

From medium-term.md, find:
- `{target-slug}` — the project slug
- `{target-pd-name}` — the PD's agent name (e.g. `{project}-pd`)
- `{target-memory-path}` — the project's memory directory

## Step 2 — Create the Task ID

Generate: `{YYYYMMDD}-{slug}-{n}` e.g. `20260416-{project}-1`

## Step 3 — Create Incoming Briefing

Write to the **target PD's** inter-spawn-tasks folder:
`{target-memory-path}/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md`

```markdown
# Inter-Spawn Task — {task-id}

**Created by:** {caller-pd-name} (on behalf of the operator)
**Created at:** {ISO timestamp} UTC
**From PD:** {caller-pd-name}
**To PD:** {target-pd-name}
**Status:** INCOMING

## End Goal
[Taken verbatim from the operator's instruction — state the outcome, not the method]

## Available Assets & Context
- Branding: [paths from operator's instruction or project memory]
- Content: [paths or "none specified — use best judgment"]
- Stack: [from target project's CLAUDE.md if known]
- Other: [any other context provided]

## Constraints
- [Any constraints named]
- Default: work in spawned PD's own project directory
```

## Step 4 — Create Caller's Delegation Task

Write `{caller-project}/memory/tasks/ongoing/delegated-{task-id}.md`:

```markdown
# Delegated Task — {task-id}

**Delegated by:** {caller-pd-name}
**Delegated to:** {target-pd-name}
**Status:** DELEGATED — awaiting report

## What Was Delegated
[End goal from Step 3]

## Briefing File
{target-memory-path}/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md

## Callback Required
Mark this task DONE only after {target-pd-name} sends completion message.

## Revision History
(none yet)
```

## Step 5 — Spawn the Target PD

Use the Agent tool to spawn the target PD:

```
prompt: |
  You are {target-pd-name}, resuming work as Project Director for {target-slug}.
  You have been spawned by {caller-pd-name} to complete an inter-spawn task.

  YOUR IDENTITY FILE (read first):
  {target-memory-path}/{target-slug}-pd.md

  YOUR BRIEFING (read second — this is your task):
  {target-memory-path}/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md

  PROTOCOL — read and follow:

  1. Read your identity file: {target-memory-path}/{target-slug}-pd.md
  2. Read the briefing: {target-memory-path}/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md
     (confirm it exists, update status to IN_PROGRESS)
  3. Do the work in {target-project-root}/ only
  4. When done: Write completion record to caller's delegation task file (see Step 5b below)
  5. Move briefing from inter-spawn-tasks/incoming/ to inter-spawn-tasks/completed/
  6. Run /save-state [{target-slug}]
  7. Stop.

  Do NOT use SendMessage to notify the caller PD — background headless agents
  do not have active sessions and cannot receive direct messages. The message
  would land in the parent session instead of the caller PD's context, and
  neither would act on it. Always use the filesystem completion protocol below.

  Do NOT read any files in {caller-project}/.
  Do NOT write any files to {caller-project}/.

  Start now. Read your identity file first.
```

Spawn config:
- `subagent_type`: general-purpose
- `model`: opus
- `run_in_background`: true
- `team_name`: {target-slug}

## Step 5b — Filesystem Completion Protocol (MANDATORY)

When the spawned PD completes, it writes a completion record directly to the
caller's filesystem — NOT via SendMessage. Background headless agents cannot
receive direct messages; the caller's session is already closed by the time
completion happens.

**The spawned PD (target) writes this to the caller's delegation task file:**

Append to `{caller-project}/memory/tasks/ongoing/delegated-{task-id}.md`:

```markdown
## Completion — {ISO timestamp} UTC
**Status:** DONE — [1-sentence summary of what was delivered]
```

Then append the same to the briefing file:
`{target-memory-path}/inter-spawn-tasks/completed/inter-spawn-{task-id}.md`

**This is the ONLY way the caller learns the task is done.** The caller must
read its own `delegated-{task-id}.md` to know when the task completed — it
cannot wait for a SendMessage that will never arrive.

## Step 6 — Confirm

Output:
```
PD SPAWN: {task-id}
  Caller: {caller-pd-name}
  Spawned: {target-pd-name}
  Project: {target-slug}
  Briefing: {target-memory-path}/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md
  Delegation task: {caller-project}/memory/tasks/ongoing/delegated-{task-id}.md

Spawned PD running. Completion record written to caller's `delegated-{task-id}.md` on finish — caller learns via /pd-resume.
```

## Handling the Completion — Filesystem Protocol

The caller PD does NOT wait for a SendMessage (it will never arrive).
Instead, it polls its own `memory/tasks/ongoing/delegated-{task-id}.md` file.

**Trigger:** When `/pd-resume [{caller-slug}]` is run and the delegation task
is found with a "Completion" section, the caller PD:
1. Reads the completion record from `delegated-{task-id}.md`
2. Moves `memory/tasks/ongoing/delegated-{task-id}.md` → `memory/tasks/completed/`
3. Logs the completion to the operator: "✅ {task-id} complete — [summary from completion record]"
4. Runs /save-state [{caller-slug}]

**How the caller knows a task is done between sessions:**
`/pd-resume [{caller-slug}]` reads `memory/tasks/ongoing/delegated-*.md` files.
Any with a "Completion" section are marked done, others remain "DELEGATED — awaiting report."

## Handling Failure / Blocker — Filesystem Protocol

If the spawned PD encounters a blocker, it writes to the caller's delegation task:

Append to `{caller-project}/memory/tasks/ongoing/delegated-{task-id}.md`:
```markdown
## Blocker — {ISO timestamp} UTC
**Reason:** [what is blocking progress]
**Suggested path forward:** [workaround or escalation]
```

Caller reads this on next `/pd-resume`. Do NOT use SendMessage for blockers either.

## Revision Protocol — "Not Satisfied, Adjust and Continue"

When the operator or the caller PD is unsatisfied with the result:

**Trigger:** "revision needed on {task-id}" or "{project} PD, revise the landing page"

**Step 1 — The requesting PD (caller):**
1. Move `{caller}/memory/tasks/completed/delegated-{task-id}.md` → `memory/tasks/revisions/delegated-{task-id}.md`
2. Append revision note to the revision copy:

```markdown
## Revision — {YYYY-MM-DD HH:MM UTC}
**Requested by:** {caller-pd-name or "operator"}
**Reason:** [what is wrong or needs changing]
**Instructions:** [specific adjustments required]
```

3. Create new briefing `{target-memory-path}/inter-spawn-tasks/incoming/inter-spawn-{task-id}-r{n}.md`:

```markdown
# Inter-Spawn Task — {task-id}-r{n}

**Revision of:** {task-id}
**Created by:** {caller-pd-name}
**Status:** INCOMING — REVISION {n}

## Prior Work
Task {task-id} delivered: [1-sentence summary of what was done]
Prior task file: {target-memory-path}/inter-spawn-tasks/completed/inter-spawn-{task-id}.md

## Revision Request
**What to change:** [specific changes required]
**What to keep:** [aspects to preserve]

## Available Context
- Prior task: {target-memory-path}/inter-spawn-tasks/completed/inter-spawn-{task-id}.md
- Delegation: {caller-project}/memory/tasks/revisions/delegated-{task-id}.md
- Branding: [same paths as original]
```

4. Create new delegation task: `memory/tasks/ongoing/delegated-{task-id}-r{n}.md`
5. Spawn the same PD with the revision briefing

**The spawned PD on revision:**
1. Reads its identity + revision briefing
2. Reads prior task: `{target-memory-path}/inter-spawn-tasks/completed/inter-spawn-{task-id}.md`
3. Applies only the requested adjustments — does NOT discard prior work
4. Writes completion record to caller's `delegated-{task-id}-r{n}.md` (same as Step 5b above)
5. Moves briefing to inter-spawn-tasks/completed/
6. /save-state → stops

**Revision counter:** r1, r2, r3... originating task ID preserved for traceability.

**Escalation:** If a revision is rejected twice, caller PD escalates to the operator: "⚠️ {task-id} rejected twice — needs your call."
