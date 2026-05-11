const {
  existsSync,
  mkdirSync,
  copyFileSync,
  readdirSync,
  writeFileSync,
  statSync,
} = require('fs');
const path = require('path');
const os = require('os');

/**
 * agency init — Bootstrap The Agency into ~/.claude/
 *
 * Installs:
 *   ~/.claude/skills/{name}/SKILL.md  — one directory per skill
 *   ~/.claude/agents/{dept}/{name}.md — agent definitions by department
 *   ~/.claude/projects/               — per-project state
 *   ~/.claude/sessions/               — per-project session logs
 *   ~/.claude/task-store.db           — SQLite task store
 */
module.exports = async function init({ args, AGENCY_ROOT, console }) {
  const agencyRoot = process.env.AGENCY_HOME || path.resolve(os.homedir(), '.claude');
  const repoRoot = path.resolve(__dirname, '../..');
  const sourceSkills = path.join(repoRoot, 'skills');
  const sourceAgents = path.join(repoRoot, 'agents');

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

  // 3. Skills — copy as {name}/SKILL.md directories
  const destSkills = path.join(agencyRoot, 'skills');
  mkdirSync(destSkills, { recursive: true });

  if (existsSync(sourceSkills)) {
    const skillFiles = readdirSync(sourceSkills).filter(
      f => f.endsWith('.md') && f !== 'INDEX.md' && f !== 'README.md'
    );
    let installed = 0;
    let preserved = 0;

    for (const file of skillFiles) {
      const name = file.replace('.md', '');
      const skillDir = path.join(destSkills, name);
      const destFile = path.join(skillDir, 'SKILL.md');
      const srcFile = path.join(sourceSkills, file);

      mkdirSync(skillDir, { recursive: true });

      if (!existsSync(destFile)) {
        copyFileSync(srcFile, destFile);
        installed++;
      } else {
        const srcMtime = statSync(srcFile).mtimeMs;
        const destMtime = statSync(destFile).mtimeMs;
        if (srcMtime > destMtime) {
          copyFileSync(srcFile, destFile);
          installed++;
        } else {
          preserved++;
        }
      }
    }

    // Copy INDEX.md to skills root
    const indexSrc = path.join(sourceSkills, 'INDEX.md');
    if (existsSync(indexSrc)) {
      copyFileSync(indexSrc, path.join(destSkills, 'INDEX.md'));
    }

    console.log(`  ✓ ${installed} skills installed, ${preserved} preserved (${skillFiles.length} total)`);
  } else {
    console.log('  ⚠ No skills/ directory in repo — skipping');
  }

  // 4. Agents — copy preserving department structure
  const destAgents = path.join(agencyRoot, 'agents');
  mkdirSync(destAgents, { recursive: true });

  if (existsSync(sourceAgents)) {
    let agentCount = 0;
    let agentPreserved = 0;

    const copyAgentDir = (srcDir, destDir) => {
      if (!existsSync(srcDir)) return;
      const entries = readdirSync(srcDir, { withFileTypes: true });

      for (const entry of entries) {
        const srcPath = path.join(srcDir, entry.name);
        const destPath = path.join(destDir, entry.name);

        if (entry.isDirectory()) {
          mkdirSync(destPath, { recursive: true });
          copyAgentDir(srcPath, destPath);
        } else if (entry.name.endsWith('.md')) {
          if (!existsSync(destPath)) {
            copyFileSync(srcPath, destPath);
            agentCount++;
          } else {
            const srcMtime = statSync(srcPath).mtimeMs;
            const destMtime = statSync(destPath).mtimeMs;
            if (srcMtime > destMtime) {
              copyFileSync(srcPath, destPath);
              agentCount++;
            } else {
              agentPreserved++;
            }
          }
        }
      }
    };

    copyAgentDir(sourceAgents, destAgents);
    console.log(`  ✓ ${agentCount} agents installed, ${agentPreserved} preserved`);
  } else {
    console.log('  ⚠ No agents/ directory in repo — skipping');
  }

  // 5. SQLite task store
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

  console.log(`\n✓ The Agency is ready — ${destSkills}\n`);
  console.log('Next steps:');
  console.log('  agency new <project-slug> "<description>"  Create your first project');
  console.log('  agency status                             Show all projects');
  console.log('  agency skill list                         View installed skills\n');
};
