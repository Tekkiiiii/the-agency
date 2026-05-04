const { resolve } = require('path');

/**
 * agency tasks — SQLite CRUD wrapper for the task store
 *
 * Usage:
 *   agency tasks list [project]              Show all tasks, optionally filter by project
 *   agency tasks add <project> <name>        Add a new task
 *   agency tasks done <task-id>              Mark task completed
 *   agency tasks status <task-id> <status>   Update task status
 */
module.exports = async function tasks({ args, AGENCY_ROOT, console }) {
  const [subcmd, ...rest] = args;

  if (!subcmd) {
    console.log('Usage:');
    console.log('  agency tasks list [project]              Show all tasks');
    console.log('  agency tasks add <project> <name>        Add a new task');
    console.log('  agency tasks done <task-id>              Mark task completed');
    console.log('  agency tasks status <task-id> <status>   Update task status');
    return;
  }

  const dbPath = process.env.AGENCY_HOME
    ? resolve(process.env.AGENCY_HOME, 'task-store.db')
    : resolve(process.env.HOME, '.claude', 'task-store.db');

  let db;
  try {
    const Database = require('better-sqlite3');
    db = new Database(dbPath);
    // Ensure schema exists
    db.exec(require('./schema.js'));
  } catch (err) {
    if (err.code === 'MODULE_NOT_FOUND') {
      console.error('better-sqlite3 is not installed.');
      console.error('Run: npm install better-sqlite3');
      process.exit(1);
    }
    console.error('Database error: ' + err.message);
    process.exit(1);
  }

  if (subcmd === 'list') {
    const [project] = rest;
    let rows;
    if (project) {
      rows = db.prepare(
        'SELECT id, project_slug, task_name, status, priority, created_at FROM tasks WHERE project_slug = ? ORDER BY created_at DESC'
      ).all(project);
    } else {
      rows = db.prepare(
        'SELECT id, project_slug, task_name, status, priority, created_at FROM tasks ORDER BY project_slug, created_at DESC'
      ).all();
    }

    if (rows.length === 0) {
      console.log(project ? 'No tasks found for project "' + project + '".' : 'No tasks found.');
      db.close();
      return;
    }

    // Column widths
    const idW     = 10;
    const projW   = Math.max(7,  ...rows.map(r => r.project_slug.length));
    const nameW   = Math.max(9,  ...rows.map(r => r.task_name.length));
    const statusW = Math.max(6,  ...rows.map(r => r.status.length));
    const prioW   = Math.max(8,  ...rows.map(r => (r.priority || '').length));

    const pad     = (str, len) => String(str || '').padEnd(len);
    const divider = '-'.repeat(idW + projW + nameW + statusW + prioW + 11);

    console.log('');
    console.log(pad('ID', idW) + '  ' + pad('PROJECT', projW) + '  ' + pad('TASK NAME', nameW) + '  ' + pad('STATUS', statusW) + '  ' + pad('PRIORITY', prioW));
    console.log(divider);
    for (const r of rows) {
      console.log(pad(r.id.slice(0, 8), idW) + '  ' + pad(r.project_slug, projW) + '  ' + pad(r.task_name, nameW) + '  ' + pad(r.status, statusW) + '  ' + pad(r.priority, prioW));
    }
    console.log('');
    console.log(rows.length + ' task(s) found.');
    console.log('');
    db.close();
    return;
  }

  if (subcmd === 'add') {
    const [project, ...nameParts] = rest;
    if (!project || nameParts.length === 0) {
      console.error('Usage: agency tasks add <project> <name>');
      process.exit(1);
    }
    const name = nameParts.join(' ');
    const stmt = db.prepare('INSERT INTO tasks (project_slug, task_name) VALUES (?, ?)');
    const result = stmt.run(project, name);
    const row = db.prepare('SELECT id FROM tasks WHERE rowid = ?').get(result.lastInsertRowid);
    console.log('\nTask added.');
    console.log('  ID:      ' + row.id);
    console.log('  Project: ' + project);
    console.log('  Name:    ' + name + '\n');
    db.close();
    return;
  }

  if (subcmd === 'done') {
    const [taskId] = rest;
    if (!taskId) {
      console.error('Usage: agency tasks done <task-id>');
      process.exit(1);
    }
    const result = db.prepare(
      "UPDATE tasks SET status = 'completed', completed_at = datetime('now'), updated_at = datetime('now') WHERE id LIKE ?"
    ).run(taskId + '%');
    if (result.changes === 0) {
      console.error('No task found matching ID: ' + taskId);
      process.exit(1);
    }
    console.log('\nTask marked as completed.\n');
    db.close();
    return;
  }

  if (subcmd === 'status') {
    const [taskId, status] = rest;
    if (!taskId || !status) {
      console.error('Usage: agency tasks status <task-id> <status>');
      process.exit(1);
    }
    const result = db.prepare(
      "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE id LIKE ?"
    ).run(status, taskId + '%');
    if (result.changes === 0) {
      console.error('No task found matching ID: ' + taskId);
      process.exit(1);
    }
    console.log('\nTask status updated to "' + status + '".\n');
    db.close();
    return;
  }

  console.error('Unknown subcommand: ' + subcmd);
  console.error('Run "agency tasks" for usage.');
  process.exit(1);
};
