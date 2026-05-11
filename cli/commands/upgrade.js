const { execFileSync } = require('child_process');
const { existsSync, statSync, copyFileSync, readdirSync, mkdirSync } = require('fs');
const { resolve, join } = require('path');
const os = require('os');

module.exports = async function upgrade({ args, AGENCY_ROOT, console }) {
  // 1. Find the repo root
  let repoDir = __dirname;
  let found = false;
  for (let i = 0; i < 10; i++) {
    if (existsSync(join(repoDir, '.git'))) {
      found = true;
      break;
    }
    const parent = resolve(repoDir, '..');
    if (parent === repoDir) break;
    repoDir = parent;
  }

  if (!found) {
    console.error('Could not find .git directory. Is this installed from a git repo?');
    process.exit(1);
  }

  console.log('\nAgency Upgrade');
  console.log('==============');
  console.log('Repo: ' + repoDir);
  console.log('');

  // 2. Git fetch + pull
  console.log('Fetching origin/main...');
  try {
    execFileSync('git', ['-C', repoDir, 'fetch', 'origin', 'main'], { stdio: 'pipe' });
  } catch (err) {
    console.error('git fetch failed: ' + (err.stderr ? err.stderr.toString().trim() : err.message));
    process.exit(1);
  }

  try {
    const pullOutput = execFileSync('git', ['-C', repoDir, 'pull', '--rebase', 'origin', 'main'], { stdio: 'pipe' }).toString().trim();
    console.log(pullOutput || 'Already up to date.');
  } catch (err) {
    console.error('git pull --rebase failed: ' + (err.stderr ? err.stderr.toString().trim() : err.message));
    process.exit(1);
  }

  console.log('');

  const agencyRoot = process.env.AGENCY_HOME || resolve(os.homedir(), '.claude');

  // 3. Sync skills — repo flat files → ~/.claude/skills/{name}/SKILL.md
  const skillsSrc = join(repoDir, 'skills');
  const skillsDest = join(agencyRoot, 'skills');

  if (existsSync(skillsSrc)) {
    const skillFiles = readdirSync(skillsSrc).filter(
      f => f.endsWith('.md') && f !== 'INDEX.md' && f !== 'README.md'
    );

    mkdirSync(skillsDest, { recursive: true });

    const updated = [];
    const preserved = [];

    for (const file of skillFiles) {
      const name = file.replace('.md', '');
      const src = join(skillsSrc, file);
      const destDir = join(skillsDest, name);
      const dest = join(destDir, 'SKILL.md');

      mkdirSync(destDir, { recursive: true });

      if (!existsSync(dest)) {
        copyFileSync(src, dest);
        updated.push(name);
      } else {
        const srcMtime = statSync(src).mtimeMs;
        const destMtime = statSync(dest).mtimeMs;
        if (srcMtime > destMtime) {
          copyFileSync(src, dest);
          updated.push(name);
        } else {
          preserved.push(name);
        }
      }
    }

    // Copy INDEX.md
    const indexSrc = join(skillsSrc, 'INDEX.md');
    if (existsSync(indexSrc)) {
      copyFileSync(indexSrc, join(skillsDest, 'INDEX.md'));
    }

    console.log('Skills:');
    if (updated.length > 0) {
      console.log(`  Updated: ${updated.length}`);
      for (const s of updated) console.log(`    + ${s}`);
    }
    console.log(`  Preserved: ${preserved.length}`);
  } else {
    console.log('No skills/ directory in repo — skipping.');
  }

  console.log('');

  // 4. Sync agents — preserve department structure
  const agentsSrc = join(repoDir, 'agents');
  const agentsDest = join(agencyRoot, 'agents');

  if (existsSync(agentsSrc)) {
    mkdirSync(agentsDest, { recursive: true });
    let agentUpdated = 0;
    let agentPreserved = 0;

    const syncDir = (srcDir, destDir) => {
      const entries = readdirSync(srcDir, { withFileTypes: true });
      for (const entry of entries) {
        const srcPath = join(srcDir, entry.name);
        const destPath = join(destDir, entry.name);

        if (entry.isDirectory()) {
          mkdirSync(destPath, { recursive: true });
          syncDir(srcPath, destPath);
        } else if (entry.name.endsWith('.md')) {
          if (!existsSync(destPath)) {
            copyFileSync(srcPath, destPath);
            agentUpdated++;
          } else {
            const srcMtime = statSync(srcPath).mtimeMs;
            const destMtime = statSync(destPath).mtimeMs;
            if (srcMtime > destMtime) {
              copyFileSync(srcPath, destPath);
              agentUpdated++;
            } else {
              agentPreserved++;
            }
          }
        }
      }
    };

    syncDir(agentsSrc, agentsDest);
    console.log(`Agents: ${agentUpdated} updated, ${agentPreserved} preserved`);
  } else {
    console.log('No agents/ directory in repo — skipping.');
  }

  console.log('\nUpgrade complete.\n');
};
