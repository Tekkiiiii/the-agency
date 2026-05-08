---
name: wrap
description: >
  Freezes and wraps up inbox task work — reads ongoing tasks, updates their status,
  writes per-task session logs, archives completed/abandoned tasks. Similar to /save-state
  but scoped entirely to ~/.claude/tasks/inbox/ (no project memory files). Trigger
  when the session ends with inbox tasks in progress, when switching focus away from
  inbox work, or when the user says "wrap up" or "wrap" for non-project tasks.
---

# Wrap — Inbox Task Session Freeze

Spawns a subagent that reads ongoing inbox tasks, updates their status, writes
per-task session logs, and archives completed/abandoned tasks. Caller spawns and
waits — zero work done in the calling session.

## Step 1 — Spawn Subagent

Use the Agent tool to spawn a general-purpose sonnet subagent. The subagent owns
the entire ritual — do not do any reading or writing yourself.

Subagent prompt:

"You own the wrap ritual for inbox tasks. Run it completely.

PERMISSIONS: read-write-create on ALL paths below. No restrictions.

## Scope
- Inbox root: ~/.claude/tasks/inbox/
- Ongoing dir: ~/.claude/tasks/inbox/ongoing/
- Completed dir: ~/.claude/tasks/inbox/completed/
- Archived dir: ~/.claude/tasks/inbox/archived/
- Task session dir: ~/.claude/tasks/inbox/ongoing/{slug}/sessions/
- Active task dirs: ~/.claude/tasks/inbox/ongoing/*/TASK.md

## Step 1 — Inventory Ongoing Tasks

Read every ~/.claude/tasks/inbox/ongoing/*/TASK.md simultaneously.
Collect per task: slug (folder name), title, status, priority, description.
Build a brief summary for each.

## Step 2 — Present Summary

Summarize each ongoing task clearly:
- slug, title, priority, one-line description

Then ask the user (via the calling session) to classify each:
- Which are DONE this session?
- Which are ABANDONED?
- Which remain ONGOING (still in progress)?

Wait for user input before proceeding.

## Step 3 — Archive Tasks

For each task marked DONE:
1. Update TASK.md status to "done"
2. Move folder to ~/.claude/tasks/inbox/completed/

For each task marked ABANDONED:
1. Update TASK.md status to "abandoned"
2. Move folder to ~/.claude/tasks/inbox/archived/

For each task marked ONGOING:
1. Leave in ~/.claude/tasks/inbox/ongoing/
2. Append session notes to TASK.md
3. Create per-task session log (see Step 4)

## Step 4 — Write Per-Task Session Logs

For each ONGOING task, create:
~/.claude/tasks/inbox/ongoing/{slug}/sessions/YYYY-MM-DD.md

## Session — YYYY-MM-DD HH:MM UTC

**was_doing**: [what was being worked on]
**just_finished**: [what completed before stopping]
**doing_next**: [specific next action]

### Notes
- [any session notes]

## Step 5 — Update TASK.md for Ongoing Tasks

Append to the Notes section of each ongoing task's TASK.md:

---
## Session Wrap — YYYY-MM-DD
**status_check**: still in progress
**last_action**: [brief description]
**next_action**: [specific next step]
**blockers**: [any blockers hit, or "none"]
---

## Step 6 — Confirm

Output only: wrap done!
Then stop. No further narration.

subagent_type: general-purpose
model: sonnet

Wait for the subagent to complete. You (the caller) do nothing else.
