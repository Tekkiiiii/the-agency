const { existsSync, mkdirSync, writeFileSync } = require('fs');
const path = require('path');
const { syncSkills, syncAgents } = require('./sync-assets.js');

module.exports = async function init({ args, AGENCY_ROOT, console }) {
  const agencyRoot = AGENCY_ROOT;
  const repoRoot = path.resolve(__dirname, '../..');

  console.log(`\nInitializing The Agency at ${agencyRoot}\n`);

  // 1. Root directory
  if (!existsSync(agencyRoot)) {
    mkdirSync(agencyRoot, { recursive: true });
    console.log('  ✓ Created root directory');
  } else {
    console.log('  ✓ Root directory exists');
  }

  // 2. Subdirectories
  for (const dir of ['projects', 'sessions', 'memory']) {
    const d = path.join(agencyRoot, dir);
    if (!existsSync(d)) {
      mkdirSync(d, { recursive: true });
      console.log(`  ✓ Created ${dir}/`);
    } else {
      console.log(`  ✓ ${dir}/ exists`);
    }
  }

  // 3. Skills
  const skillsDest = path.join(agencyRoot, 'skills');
  const skills = syncSkills(repoRoot, skillsDest, console);
  console.log(`  ✓ ${skills.updated.length} skills installed, ${skills.preserved.length} preserved`);

  // 4. Agents
  const agentsDest = path.join(agencyRoot, 'agents');
  const agents = syncAgents(repoRoot, agentsDest, console);
  console.log(`  ✓ ${agents.updated} agents installed, ${agents.preserved} preserved`);

  // 5. Core docs
  const coreSrc = path.join(repoRoot, 'core');
  const coreDest = path.join(agencyRoot, 'core');
  if (existsSync(coreSrc)) {
    mkdirSync(coreDest, { recursive: true });
    const { execFileSync } = require('child_process');
    try {
      execFileSync('cp', ['-r', coreSrc + '/.', coreDest + '/'], { stdio: 'pipe' });
      console.log('  ✓ Core docs installed');
    } catch (_) {
      console.log('  ⚠ Could not copy core docs');
    }
  }

  // 6. SQLite task store
  const dbPath = path.join(agencyRoot, 'task-store.db');
  if (!existsSync(dbPath)) {
    try {
      const Database = require('better-sqlite3');
      const db = new Database(dbPath);
      db.exec(require('./schema.js'));
      db.close();
      console.log('  ✓ Created task-store.db');
    } catch {
      writeFileSync(dbPath, '');
      console.log('  ⚠ better-sqlite3 not installed — task-store.db is a placeholder');
      console.log('       Run: npm install better-sqlite3');
    }
  } else {
    console.log('  ✓ task-store.db exists');
  }

  console.log(`\n✓ The Agency is ready — ${skillsDest}\n`);
  console.log('Next steps:');
  console.log('  agency new <project-slug> "<description>"  Create your first project');
  console.log('  agency status                             Show all projects');
  console.log('  agency skill list                         View installed skills\n');
};
