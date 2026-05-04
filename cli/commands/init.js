const {
  existsSync,
  mkdirSync,
  copyFileSync,
  readdirSync,
  writeFileSync,
} = require('fs');
const path = require('path');

/**
 * agency init — Bootstrap the Agency system in ~/.claude/
 *
 * Creates:
 *   ~/.claude/               — root
 *   ~/.claude/projects/      — per-project state
 *   ~/.claude/sessions/      — per-project session logs
 *   ~/.claude/skills/        — installed skills (copied from source)
 *   ~/.claude/task-store.db  — SQLite task store
 */
module.exports = async function init({ args, AGENCY_ROOT, console }) {
  const agencyRoot = process.env.AGENCY_HOME
    ? process.env.AGENCY_HOME
    : require('path').resolve(process.env.HOME, '.claude');
  const sourceSkills = path.join(__dirname, '../../skills');

  console.log(`\nInitializing The Agency at ${agencyRoot}\n`);

  // 1. Root directory
  if (!existsSync(agencyRoot)) {
    mkdirSync(agencyRoot, { recursive: true });
    console.log('  ✓ Created ~/.claude/');
  } else {
    console.log('  ✓ ~/.claude/ already exists');
  }

  // 2. Subdirectories
  for (const dir of ['projects', 'sessions']) {
    const d = `${agencyRoot}/${dir}`;
    if (!existsSync(d)) {
      mkdirSync(d, { recursive: true });
      console.log(`  ✓ Created ~/.claude/${dir}/`);
    } else {
      console.log(`  ✓ ~/.claude/${dir}/ already exists`);
    }
  }

  // 3. Skills — copy from ~/the-agency/skills/
  const destSkills = `${agencyRoot}/skills`;
  if (existsSync(sourceSkills)) {
    const skillFiles = readdirSync(sourceSkills).filter(f => f.endsWith('.md'));
    if (skillFiles.length > 0) {
      mkdirSync(destSkills, { recursive: true });
      let installed = 0;
      for (const file of skillFiles) {
        if (!existsSync(`${destSkills}/${file}`)) {
          copyFileSync(`${sourceSkills}/${file}`, `${destSkills}/${file}`);
          installed++;
        }
      }
      console.log(
        `  ✓ ${installed}/${skillFiles.length} new skills installed to ~/.claude/skills/`
      );
      if (installed < skillFiles.length) {
        console.log(`       ${skillFiles.length - installed} skills already installed (preserved)`);
      }
    }
  } else {
    console.log('  ⚠ No skill source found at ~/the-agency/skills/ — skipping skills');
  }

  // 4. SQLite task store
  const dbPath = `${agencyRoot}/task-store.db`;
  if (!existsSync(dbPath)) {
    try {
      const Database = require('better-sqlite3');
      const db = new Database(dbPath);
      db.exec(require('./schema.js'));
      db.close();
      console.log('  ✓ Created ~/.claude/task-store.db');
    } catch {
      writeFileSync(dbPath, '');
      console.log('  ⚠ better-sqlite3 not installed — task-store.db is a placeholder');
      console.log('       Run: npm install better-sqlite3');
    }
  } else {
    console.log('  ✓ ~/.claude/task-store.db already exists');
  }

  console.log('\n✓ The Agency is ready.\n');
  console.log('Next steps:');
  console.log('  agency new <project-slug> "<description>"  Create your first project');
  console.log('  agency status                             Show all projects');
  console.log('  agency skill list                         View installed skills\n');
};
