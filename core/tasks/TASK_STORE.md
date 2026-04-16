# Task Store

Every task in The Agency lives in the SQLite task store: `~/.agency/task-store.db`.

## Schema

```sql
CREATE TABLE tasks (
  id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  project_slug    TEXT NOT NULL,
  task_name       TEXT NOT NULL,
  description     TEXT,
  status          TEXT DEFAULT 'pending',
  assigned_agent  TEXT,
  priority        TEXT DEFAULT 'normal',
  phase           TEXT,
  track           TEXT,
  retry_count     INT  DEFAULT 0,
  max_retries     INT  DEFAULT 3,
  blocked_by      TEXT DEFAULT '[]',
  gate_status     TEXT DEFAULT 'open',
  gate_verifier   TEXT,
  gate_timestamp  TEXT,
  created_at      TEXT DEFAULT (datetime('now')),
  updated_at      TEXT DEFAULT (datetime('now')),
  completed_at    TEXT,
  notes           TEXT
);
```

## Status Values

| Status | Meaning |
|---|---|
| `pending` | Not started |
| `in_progress` | Active work |
| `blocked` | Waiting on dependencies |
| `done` | Complete |
| `failed` | Exhausted retries |

## Gate System

Tasks advance through explicit quality gates. A gate must be passed before the task is marked done.

- `open` → gate not evaluated
- `passed` → gate cleared by verifier
- `failed` → gate failed, task must be reworked

## Blocking

A task with `blocked_by = '["task-id-1", "task-id-2"]'` cannot move to `in_progress` until all listed tasks reach `done`.

## Priority

`low` | `normal` | `high` | `critical`

## Example: Create a Task

```bash
sqlite3 ~/.agency/task-store.db \
  "INSERT INTO tasks (project_slug, task_name, description, priority) 
   VALUES ('my-project', 'Build auth', 'Add login flow', 'high');"
```

## Example: Check Blockers

```bash
sqlite3 ~/.agency/task-store.db \
  "SELECT task_name, status FROM tasks 
   WHERE id IN (SELECT value FROM tasks, json_each(blocked_by) 
   WHERE status != 'done');"
```
