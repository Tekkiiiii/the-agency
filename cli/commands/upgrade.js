const { execFileSync } = require('child_process');
const { existsSync } = require('fs');
const { resolve, join } = require('path');
const { syncSkills, syncAgents } = require('./sync-assets.js');

function findRepoRoot() {
  let dir = __dirname;
  for (let i = 0; i < 10; i++) {
    if (existsSync(join(dir, '.git'))) return dir;
    const parent = resolve(dir, '..');
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function hasInProgressOp(repoDir) {
  const gitDir = join(repoDir, '.git');
  if (existsSync(join(gitDir, 'REBASE_HEAD')) || existsSync(join(gitDir, 'rebase-merge')) || existsSync(join(gitDir, 'rebase-apply')))
    return 'rebase';
  if (existsSync(join(gitDir, 'MERGE_HEAD')))
    return 'merge';
  if (existsSync(join(gitDir, 'CHERRY_PICK_HEAD')))
    return 'cherry-pick';
  return null;
}

module.exports = async function upgrade({ args, AGENCY_ROOT, console }) {
  const repoDir = findRepoRoot();
  if (!repoDir) {
    console.error('Could not find .git directory. Is this installed from a git repo?');
    console.error('If stuck, run: bash rescue.sh (from the repo directory)');
    process.exit(1);
  }

  console.log('\nAgency Upgrade');
  console.log('==============');
  console.log('Repo: ' + repoDir);
  console.log('');

  // Detect in-progress git operations before doing anything
  const inProgress = hasInProgressOp(repoDir);
  if (inProgress) {
    console.error(`A git ${inProgress} is already in progress.`);
    console.error(`Run:  git -C "${repoDir}" ${inProgress === 'cherry-pick' ? 'cherry-pick' : inProgress} --abort`);
    console.error('Then re-run: agency upgrade');
    console.error('Or run: bash rescue.sh (handles this automatically)');
    process.exit(1);
  }

  // Fetch
  console.log('Fetching origin/main...');
  try {
    execFileSync('git', ['-C', repoDir, 'fetch', 'origin', 'main'], { stdio: 'pipe' });
  } catch (err) {
    console.error('git fetch failed: ' + (err.stderr ? err.stderr.toString().trim() : err.message));
    console.error('Check your network connection, then re-run: agency upgrade');
    process.exit(1);
  }

  // Stash local changes
  let stashed = false;
  try {
    const status = execFileSync('git', ['-C', repoDir, 'status', '--porcelain'], { stdio: 'pipe' }).toString().trim();
    if (status) {
      console.log('Stashing local changes...');
      try {
        execFileSync('git', ['-C', repoDir, 'stash', '--include-untracked'], { stdio: 'pipe' });
        stashed = true;
      } catch (stashErr) {
        console.error('git stash failed: ' + (stashErr.stderr ? stashErr.stderr.toString().trim() : stashErr.message));
        // Check if tree is still dirty
        const stillDirty = execFileSync('git', ['-C', repoDir, 'status', '--porcelain'], { stdio: 'pipe' }).toString().trim();
        if (stillDirty) {
          console.error('Cannot proceed with unstaged changes. Either:');
          console.error(`  git -C "${repoDir}" stash --include-untracked`);
          console.error(`  git -C "${repoDir}" checkout -- .`);
          console.error('Or run: bash rescue.sh');
          process.exit(1);
        }
      }
    }
  } catch (statusErr) {
    console.error('git status failed: ' + (statusErr.message || statusErr));
    process.exit(1);
  }

  // Pull with rebase
  try {
    const pullOutput = execFileSync('git', ['-C', repoDir, 'pull', '--rebase', 'origin', 'main'], { stdio: 'pipe' }).toString().trim();
    console.log(pullOutput || 'Already up to date.');
  } catch (err) {
    const stderr = err.stderr ? err.stderr.toString().trim() : err.message;
    console.error('git pull --rebase failed: ' + stderr);

    // Check if rebase is now in progress (started but hit conflicts)
    if (hasInProgressOp(repoDir) === 'rebase') {
      console.error('Aborting failed rebase...');
      try { execFileSync('git', ['-C', repoDir, 'rebase', '--abort'], { stdio: 'pipe' }); } catch (_) {}
    }

    if (stashed) {
      console.error('Your stashed changes are preserved. To restore:');
      console.error(`  git -C "${repoDir}" stash pop`);
    }

    console.error('Or run: bash rescue.sh');
    process.exit(1);
  }

  // Restore stashed changes
  if (stashed) {
    console.log('Restoring local changes...');
    try {
      execFileSync('git', ['-C', repoDir, 'stash', 'pop'], { stdio: 'pipe' });
    } catch (_) {
      console.log('  Stash pop had conflicts. Your changes are safe in the stash.');
      console.log(`  To see them:   git -C "${repoDir}" stash show -p`);
      console.log(`  To drop them:  git -C "${repoDir}" stash drop`);
    }
  }

  console.log('');

  // Sync skills and agents
  const agencyRoot = AGENCY_ROOT;
  const skillsDest = join(agencyRoot, 'skills');
  const agentsDest = join(agencyRoot, 'agents');

  const skills = syncSkills(repoDir, skillsDest, console);
  console.log('Skills:');
  if (skills.updated.length > 0) {
    console.log(`  Updated: ${skills.updated.length}`);
    for (const s of skills.updated) console.log(`    + ${s}`);
  }
  console.log(`  Preserved: ${skills.preserved.length}`);

  console.log('');

  const agents = syncAgents(repoDir, agentsDest, console);
  console.log(`Agents: ${agents.updated} updated, ${agents.preserved} preserved`);

  // Sync core docs
  const coreSrc = join(repoDir, 'core');
  const coreDest = join(agencyRoot, 'core');
  if (existsSync(coreSrc)) {
    const { mkdirSync } = require('fs');
    mkdirSync(coreDest, { recursive: true });
    try {
      execFileSync('cp', ['-r', coreSrc + '/.', coreDest + '/'], { stdio: 'pipe' });
      console.log('Core docs synced.');
    } catch (_) {}
  }

  console.log('\nUpgrade complete.\n');
};
