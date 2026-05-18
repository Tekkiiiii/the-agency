# Google Workspace — Tasks

Google Tasks management via `gws`.

## When to Apply

- Creating, listing, or updating tasks in Google Tasks
- Managing task lists
- Moving tasks, clearing completed tasks
- Subtasks and parent/child task relationships

## Prerequisites

Read `../gws-shared/SKILL.md` for auth, global flags, and security rules.
If missing: `gws generate-skills`

## Usage

```bash
gws tasks <resource> <method> [flags]
```

## Resources & Methods

**tasklists:**
- `list` — List all user's task lists (max 2000)
- `get`, `insert`, `update`, `patch`, `delete`

**tasks:**
- `list` — List tasks in a task list (max 20,000 non-hidden per list, 100,000 total)
- `get`, `insert`, `update`, `patch`, `delete`
- `move` — Move task to another position or list (can include subtasks)
- `clear` — Clear all completed tasks (marked "hidden")

## Key Limits

- Max 2,000 task lists per user
- Max 20,000 non-hidden tasks per list
- Max 100,000 tasks total
- Max 2,000 subtasks per task

## Discovery

```bash
gws tasks --help
gws schema tasks.<resource>.<method>
```

---

**Source:** https://officialskills.sh/googleworkspace/skills/gws-tasks