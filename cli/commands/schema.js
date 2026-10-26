module.exports = `
CREATE TABLE IF NOT EXISTS tasks (
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

CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_slug);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_gate ON tasks(gate_status);
`;
