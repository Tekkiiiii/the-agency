const { execFileSync, spawnSync } = require('child_process');
const { existsSync, chmodSync, readFileSync, writeFileSync, mkdirSync, realpathSync, readdirSync } = require('fs');
const { resolve, join } = require('path');
const os = require('os');
const { syncSkills, syncAgents, syncScripts } = require('./sync-assets.js');

// Repo skill count vs installed skill count — a silent mismatch is exactly
// the failure mode this whole sync rewrite exists to catch (see
// skill-sync-structural-fix). Never fail silently: warn loudly instead.
function verifySkillCount(repoCount, skillsDest, console) {
  const installedCount = existsSync(skillsDest)
    ? readdirSync(skillsDest, { withFileTypes: true }).filter(
        e => e.isDirectory() && existsSync(join(skillsDest, e.name, 'SKILL.md'))
      ).length
    : 0;
  if (installedCount !== repoCount) {
    console.log(`  ⚠ Skill count mismatch: repo has ${repoCount}, installed has ${installedCount}`);
  }
}

const AGENCY_CONFIG_DIR = join(os.homedir(), '.agency');
const AGENCY_CONFIG_PATH = join(AGENCY_CONFIG_DIR, 'config.json');

// Loop guard env var. When set, the process knows it was re-exec'd after a pull
// and must skip fetch/pull entirely — preventing an infinite restart loop.
const REEXEC_ENV = 'AGENCY_UPGRADE_REEXEC';

// Compare two paths by real (symlink-resolved) location, not just string form.
// `resolve()` alone is not enough: Node's require()/__dirname resolves symlinks
// (e.g. macOS /tmp -> /private/tmp), while a bare `readlink` does not. Without
// this, any repo path that crosses a symlinked directory component makes the
// comparison below think an already-correct symlink is stale on every single
// run, forcing a needless re-link. Falls back to resolve() when either side
// can't be realpath'd (e.g. a dangling symlink — treat as a real mismatch).
function samePath(a, b) {
  try {
    return realpathSync(a) === realpathSync(b);
  } catch (_) {
    return resolve(a) === resolve(b);
  }
}

function readTier() {
  if (!existsSync(AGENCY_CONFIG_PATH)) return null;
  try {
    const cfg = JSON.parse(readFileSync(AGENCY_CONFIG_PATH, 'utf8'));
    return cfg.tier || null;
  } catch {
    return null;
  }
}

function restoreTier(tier) {
  if (!tier) return;
  try {
    let cfg = {};
    if (existsSync(AGENCY_CONFIG_PATH)) {
      try { cfg = JSON.parse(readFileSync(AGENCY_CONFIG_PATH, 'utf8')); } catch (_) {}
    }
    if (cfg.tier !== tier) {
      cfg.tier = tier;
      if (!existsSync(AGENCY_CONFIG_DIR)) mkdirSync(AGENCY_CONFIG_DIR, { recursive: true });
      writeFileSync(AGENCY_CONFIG_PATH, JSON.stringify(cfg, null, 2) + '\n');
    }
  } catch (_) {}
}

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

function getHead(repoDir) {
  try {
    return execFileSync('git', ['-C', repoDir, 'rev-parse', 'HEAD'], { stdio: 'pipe' })
      .toString().trim();
  } catch {
    return null;
  }
}

module.exports = async function upgrade({ args, AGENCY_ROOT, console }) {
  const repoDir = findRepoRoot();
  if (!repoDir) {
    console.error('Could not find .git directory. Is this installed from a git repo?');
    console.error('If stuck, run: bash rescue.sh (from the repo directory)');
    process.exit(1);
  }

  // Capture current tier BEFORE any git/sync operations so we can restore it
  // after the upgrade completes. Upgrade does not intentionally write the tier,
  // but capturing and restoring it here is a defensive guarantee against any
  // future change in the upgrade flow accidentally resetting the user's tier.
  const tierBefore = readTier();

  // ─── RE-EXEC PATH ──────────────────────────────────────────────────────────
  // When this process was spawned by a prior upgrade run after a successful
  // pull (AGENCY_UPGRADE_REEXEC=1), skip fetch/pull entirely and jump straight
  // to the post-pull sync steps. This is the loop guard: without it, the fresh
  // process would pull again and potentially re-exec forever.
  const isReexec = process.env[REEXEC_ENV] === '1';

  if (isReexec) {
    console.log('\nAgency Upgrade (continuing with fresh code)');
    console.log('===========================================');
    console.log('Repo: ' + repoDir);
    if (tierBefore) console.log('Tier: ' + tierBefore + ' (will be preserved)');
    console.log('');
    // Skip directly to post-pull steps below.
  } else {
    // ─── NORMAL FIRST-RUN PATH ────────────────────────────────────────────────
    console.log('\nAgency Upgrade');
    console.log('==============');
    console.log('Repo: ' + repoDir);
    if (tierBefore) console.log('Tier: ' + tierBefore + ' (will be preserved)');
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

    // Snapshot HEAD before pull — used to detect whether new code was fetched.
    const headBefore = getHead(repoDir);
    // Set if `git stash pop` below leaves unresolved conflicts. When true, the
    // working tree is in an unknown state — do NOT re-exec fresh code on top
    // of it, and do NOT report success at the end (see checks below).
    let stashPopConflict = false;

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
      // Pull FAILED — do NOT re-exec. Exit so the user sees the error.
      process.exit(1);
    }

    // Restore stashed changes
    if (stashed) {
      console.log('Restoring local changes...');
      try {
        execFileSync('git', ['-C', repoDir, 'stash', 'pop'], { stdio: 'pipe' });
      } catch (_) {
        stashPopConflict = true;
        console.log('  Stash pop had conflicts. Your changes are safe in the stash.');
        console.log(`  To see them:   git -C "${repoDir}" stash show -p`);
        console.log(`  To drop them:  git -C "${repoDir}" stash drop`);
      }
    }

    // Do NOT proceed (re-exec, sync, or re-link) on top of an unresolved
    // stash-pop conflict — the working tree (including cli/bin/agency.js,
    // the very file the global `agency` command points to) is in an unknown
    // state. Silently continuing here previously let the process print
    // "Upgrade complete" over a broken tree — the exact failure mode that
    // let a stale/conflicted CLI entry point get symlinked as if healthy.
    if (stashPopConflict) {
      console.error('');
      console.error('Upgrade halted: local changes could not be restored cleanly.');
      console.error(`Resolve the conflict, then re-run: agency upgrade`);
      console.error(`  git -C "${repoDir}" status`);
      console.error(`  git -C "${repoDir}" stash show -p`);
      process.exit(1);
    }

    // ─── RE-EXEC CHECK ─────────────────────────────────────────────────────────
    // Compare HEAD before and after the pull. If HEAD moved, new code is on disk.
    // Re-exec this upgrade under the freshly-pulled Node module so the remaining
    // sync + tier-restore steps run with the latest logic.
    //
    // Critical conditions for re-exec:
    //   1. headBefore must be known (git was readable before pull)
    //   2. HEAD must have changed (something was actually pulled)
    //   3. The new CLI bin must exist (sanity check before spawning)
    //   4. We are NOT already a re-exec'd run (loop guard — checked above via isReexec)
    const headAfter = getHead(repoDir);
    if (headBefore && headAfter && headBefore !== headAfter) {
      const freshBin = join(repoDir, 'cli', 'bin', 'agency.js');
      if (existsSync(freshBin)) {
        console.log('');
        console.log('New code pulled — re-launching with fresh upgrade.js...');
        const childEnv = { ...process.env, [REEXEC_ENV]: '1' };
        const result = spawnSync(process.execPath, [freshBin, 'upgrade', ...args], {
          stdio: 'inherit',
          env: childEnv,
        });
        // Propagate child exit code exactly. Do not run post-pull steps in the
        // old process — the fresh child handles all of them.
        process.exit(result.status ?? 1);
      }
    }
    // HEAD unchanged (already up to date) — fall through to post-pull steps below.
    console.log('');
  }
  // ─── POST-PULL STEPS (run in fresh re-exec'd process OR when HEAD unchanged) ─

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
  verifySkillCount(skills.skillCount, skillsDest, console);

  console.log('');

  const agents = syncAgents(repoDir, agentsDest, console);
  console.log(`Agents: ${agents.updated} updated, ${agents.preserved} preserved`);

  const scriptsDest = join(agencyRoot, 'scripts');
  const scripts = syncScripts(repoDir, scriptsDest, console);
  console.log(`Scripts: ${scripts.updated} updated, ${scripts.preserved} preserved`);

  // Sync core docs
  const coreSrc = join(repoDir, 'core');
  const coreDest = join(agencyRoot, 'core');
  if (existsSync(coreSrc)) {
    mkdirSync(coreDest, { recursive: true });
    try {
      execFileSync('cp', ['-r', coreSrc + '/.', coreDest + '/'], { stdio: 'pipe' });
      console.log('Core docs synced.');
    } catch (_) {}
  }

  // Restore tier — ensure the upgrade has not altered the user's tier setting.
  // The re-exec'd child reads the tier fresh itself (~/  .agency/config.json is
  // never touched by git pull — blast-radius confirmed). No env passing needed.
  if (tierBefore) {
    restoreTier(tierBefore);
    console.log(`Tier preserved: ${tierBefore}`);
  }

  // Re-link CLI binary to ensure symlink points into the repo being upgraded.
  // Critical: if the symlink pointed to a different/older clone, re-link it now
  // so future `agency` invocations run from THIS repo.
  const cliBin = join(repoDir, 'cli', 'bin', 'agency.js');
  if (existsSync(cliBin)) {
    try {
      chmodSync(cliBin, 0o755);
    } catch (_) {}
    const linkTargets = ['/usr/local/bin/agency', join(os.homedir(), '.local', 'bin', 'agency')];
    for (const target of linkTargets) {
      try {
        const actual = execFileSync('readlink', [target], { stdio: 'pipe' }).toString().trim();
        if (!samePath(actual, cliBin)) {
          // Symlink points to a different location — re-link to this repo
          console.log(`Re-linking CLI:`);
          console.log(`  was: ${actual}`);
          console.log(`  now: ${cliBin}`);
          execFileSync('ln', ['-sf', cliBin, target], { stdio: 'pipe' });
          console.log(`  ✓ ${target} updated`);
        } else {
          console.log(`CLI symlink OK: ${target} -> ${cliBin}`);
        }
      } catch (_) {
        // target doesn't exist or readlink failed — skip silently
      }
    }
  }

  // Show current version (HEAD commit)
  let headCommit = '';
  try {
    headCommit = execFileSync('git', ['-C', repoDir, 'log', '-1', '--format=%h %s'], { stdio: 'pipe' })
      .toString().trim();
  } catch (_) {}

  console.log('\nUpgrade complete.');
  if (headCommit) console.log(`Version: ${headCommit}`);
  console.log('See what changed: CHANGELOG.md');
  console.log('');
  console.log('Quick check: agency tier get   (shows your orchestration tier)');
  console.log('');
};
