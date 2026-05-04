const { execSync } = require('child_process');
const { existsSync, statSync, copyFileSync, readdirSync, mkdirSync } = require('fs');
const { resolve, join } = require('path');

/**
 * agency upgrade — Pull latest changes from git and re-sync skills
 *
 * Usage:
 *   agency upgrade
 */
module.exports = async function upgrade({ args, AGENCY_ROOT, console }) {
  // 1. Find the repo root by walking up from this file to find .git
  let repoDir = __dirname;
  let found = false;
  for (let i = 0; i < 10; i++) {
    if (existsSync(join(repoDir, '.git'))) {
      found = true;
      break;
    }
    const parent = resolve(repoDir, '..');
    if (parent === repoDir) break; // filesystem root
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

  // 2. Git fetch + pull --rebase
  console.log('Fetching origin/main...');
  try {
    execSync('git -C ' + repoDir + ' fetch origin main', { stdio: 'pipe' });
  } catch (err) {
    console.error('git fetch failed: ' + (err.stderr ? err.stderr.toString().trim() : err.message));
    process.exit(1);
  }

  let pullOutput = '';
  try {
    pullOutput = execSync('git -C ' + repoDir + ' pull --rebase origin main', { stdio: 'pipe' }).toString().trim();
    console.log(pullOutput || 'Already up to date.');
  } catch (err) {
    console.error('git pull --rebase failed: ' + (err.stderr ? err.stderr.toString().trim() : err.message));
    process.exit(1);
  }

  console.log('');

  // 3. Re-sync skills — only copy if dest doesn't exist or source is newer
  const skillsSrc = join(repoDir, 'skills');
  const skillsDest = process.env.AGENCY_HOME
    ? resolve(process.env.AGENCY_HOME, 'skills')
    : resolve(process.env.HOME, '.claude', 'skills');

  if (!existsSync(skillsSrc)) {
    console.log('No skills/ directory in repo — skipping skill sync.');
    console.log('\nUpgrade complete.\n');
    return;
  }

  const skillFiles = readdirSync(skillsSrc).filter(f => f.endsWith('.md'));
  if (skillFiles.length === 0) {
    console.log('No skill files found in repo — skipping skill sync.');
    console.log('\nUpgrade complete.\n');
    return;
  }

  if (!existsSync(skillsDest)) {
    mkdirSync(skillsDest, { recursive: true });
  }

  const updated   = [];
  const preserved = [];

  for (const file of skillFiles) {
    const src  = join(skillsSrc, file);
    const dest = join(skillsDest, file);

    if (!existsSync(dest)) {
      // New skill — always copy
      copyFileSync(src, dest);
      updated.push(file);
    } else {
      const srcMtime  = statSync(src).mtimeMs;
      const destMtime = statSync(dest).mtimeMs;
      if (srcMtime > destMtime) {
        // Source is newer — update
        copyFileSync(src, dest);
        updated.push(file);
      } else {
        // Destination is same age or newer (customized) — preserve
        preserved.push(file);
      }
    }
  }

  console.log('Skill sync results:');
  if (updated.length > 0) {
    console.log('  Updated (' + updated.length + '):');
    for (const f of updated) {
      console.log('    + ' + f);
    }
  }
  if (preserved.length > 0) {
    console.log('  Preserved (' + preserved.length + ') — already up to date or customized:');
    for (const f of preserved) {
      console.log('    = ' + f);
    }
  }

  console.log('\nUpgrade complete.\n');
};
