---
name: task-store
description: >
  Structured task coordination backed by a local SQLite database. The task store is
  the source of truth for multi-agent pipeline state — not conversation context. Use
  when: spawning agents with upstream dependencies; tracking gate verdicts across
  agent handoffs; surfacing blocked tasks in a pipeline; coordinating parallel workstreams
  that must merge at a gate. Key capabilities: SQLite-backed persistence (survives
  session restarts), gate protocol with verifier tracking, blocked_by dependency chains,
  retry counting, priority ordering. Pairs with /task-handoff for the full Tier-A
  agent coordination protocol.
---

# task-store

Structured task coordination backed by a local SQLite database. The task store is the source of truth for pipeline state — not conversation context.

## When to Use

- Before spawning an agent, check whether upstream gates are cleared in the task store
- After completing work, record the outcome in the task store so downstream agents can proceed
- When blocked, update `blocked_by` so the orchestrator can surface the dependency chain
- Use `status=blocked` as a hard gate — never advance a blocked task to `in_progress`

## Database

**Location:** `~/.claude/task-store.db`

## Schema

```sql
tasks (
  id              TEXT PRIMARY KEY  -- UUID v4
  project_slug    TEXT NOT NULL
  task_name       TEXT NOT NULL
  description     TEXT
  status          TEXT DEFAULT 'pending'   -- pending|in_progress|blocked|done|failed
  assigned_agent  TEXT
  priority        TEXT DEFAULT 'normal'    -- low|normal|high|critical
  phase           TEXT                    -- e.g. phase0, phase1
  track           TEXT                    -- e.g. security, foundation, hygiene
  retry_count     INT  DEFAULT 0
  max_retries     INT  DEFAULT 3
  blocked_by      TEXT DEFAULT '[]'        -- JSON array of task IDs
  gate_status     TEXT DEFAULT 'open'     -- open|passed|failed
  gate_verifier   TEXT                    -- agent that cleared the gate
  gate_timestamp  TEXT
  created_at      TEXT
  updated_at      TEXT
  completed_at    TEXT
  notes           TEXT
)
```

Indexes: `idx_tasks_project`, `idx_tasks_status`, `idx_tasks_phase`, `idx_tasks_gate`

## Core Operations

### Create a task

```bash
ts-create() {
  local project="$1" name="$2" desc="$3" phase="${4:-}" priority="${5:-normal}"
  local id=$(sqlite3 ~/.claude/task-store.db \
    "SELECT lower(hex(randomblob(16)))")
  sqlite3 ~/.claude/task-store.db \
    "INSERT INTO tasks (id,project_slug,task_name,description,phase,priority)
     VALUES ('$id','$project','$name','$desc','$phase','$priority');
     SELECT '$id';"
}
```

### Query tasks by project

```bash
ts-project() {
  sqlite3 ~/.claude/task-store.db \
    "SELECT id, task_name, status, priority, gate_status, blocked_by
     FROM tasks WHERE project_slug='$1'
     ORDER BY priority DESC, created_at ASC;"
}
```

### Advance a task

```bash
ts-status() {
  sqlite3 ~/.claude/task-store.db \
    "UPDATE tasks SET status='$2', updated_at=datetime('now')
     WHERE id='$1' AND status NOT IN ('done','failed');
     SELECT changes();"
}
```

### Set gate

```bash
ts-gate() {
  local task_id="$1" verdict="$2" verifier="$3"  # verdict: passed|failed
  sqlite3 ~/.claude/task-store.db \
    "UPDATE tasks SET gate_status='$verdict', gate_verifier='$verifier',
     gate_timestamp=datetime('now'), updated_at=datetime('now')
     WHERE id='$task_id';"
}
```

### Check if task is blocked

```bash
ts-blocked() {
  local blocked=$(sqlite3 ~/.claude/task-store.db \
    "SELECT blocked_by FROM tasks WHERE id='$1';")
  echo "$blocked" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if not d else 1)" 2>/dev/null
  return $?
}
```

### List all tasks with gate status

```bash
ts-report() {
  sqlite3 -header -column ~/.claude/task-store.db \
    "SELECT id, project_slug, task_name, status, gate_status,
            datetime(created_at) as created, datetime(updated_at) as updated
     FROM tasks ORDER BY project_slug, priority DESC;"
}
```

## Gate Protocol

1. After any implementation task, invoke Reality Checker agent to assess
2. Parse verdict: `PASS` → set `gate_status=passed`, `NEEDS_WORK` or `FAIL` → set `gate_status=failed`
3. If `gate_status=failed`, the task stays blocked regardless of status
4. Gate can only be cleared by explicit agent intervention (not automatic retry)
5. Record `gate_verifier` and `gate_timestamp` when gate is cleared

## Usage Example

```bash
# 1. Create downstream task
downstream_id=$(ts-create "myproject" "implement-api" "Build REST API" "phase1" "high")

# 2. Upstream task is done — check gate
ts-status "$upstream_id" "done"

# 3. Downstream task is no longer blocked
ts-blocked "$downstream_id" || echo "blocked"

# 4. Run gatekeeper
# -> Reality Checker verdict: PASS
ts-gate "$downstream_id" "passed" "reality-checker"

# 5. Advance downstream
ts-status "$downstream_id" "in_progress"
```

## Anti-patterns

- **Never** store pipeline state in conversation context — use the task store
- **Never** advance a `blocked` task to `in_progress`
- **Never** skip gate protocol for "quick" tasks
