// Git-state recovery helpers for `agency upgrade`.
//
// Built for the state a real clone was found in after the 2026-10-08 history
// purge (origin/main force-pushed with rewritten SHAs): a stale .git/index.lock
// from a crashed git process, a leftover UU file from an earlier stash pop, and
// local commits whose rewritten twins were now on origin — so `pull --rebase`
// replayed the old commits and conflicted.
//
// Every helper takes the repo directory explicitly and shells out with argument
// arrays (execFileSync, never a shell string), so paths with spaces are safe.
// upgrade.js is the orchestrator; nothing here prints except via the caller.

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const LOCK_STALE_MS = 10 * 60 * 1000;
const UPSTREAM = 'origin/main';

function git(repoDir, args, extraEnv) {
  const opts = { stdio: 'pipe', maxBuffer: 64 * 1024 * 1024 };
  if (extraEnv) opts.env = { ...process.env, ...extraEnv };
  return execFileSync('git', ['-C', repoDir, ...args], opts).toString();
}

function pad(n) { return String(n).padStart(2, '0'); }

// Local time, YYYYMMDD-HHMMSS — shared by the backup folder and backup branch
// of one run so the two are easy to match up.
function timestamp(d = new Date()) {
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-` +
         `${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function absoluteGitDir(repoDir) {
  try {
    return git(repoDir, ['rev-parse', '--absolute-git-dir']).trim();
  } catch (_) {
    return path.join(repoDir, '.git');
  }
}

// ─── backup folder ────────────────────────────────────────────────────────────
// ~/.agency/backups/<stamp>/ (on Windows %USERPROFILE%\.agency\backups\...),
// OUTSIDE the repo so no git operation can touch it. Created lazily — only when
// there is something to copy — and never merged with another run's folder: a
// second run in the same second gets <stamp>-2, -3, ...
function createBackup(repoDir, { stamp = timestamp(), home = os.homedir() } = {}) {
  let dir = null;
  return {
    stamp,
    get dir() { return dir; },
    ensureDir() {
      if (dir) return dir;
      const base = path.join(home, '.agency', 'backups');
      let candidate = path.join(base, stamp);
      for (let n = 2; fs.existsSync(candidate); n++) candidate = path.join(base, `${stamp}-${n}`);
      fs.mkdirSync(candidate, { recursive: true });
      dir = candidate;
      return dir;
    },
    // Copies repo-relative paths, preserving their relative layout. Paths that
    // no longer exist in the working tree (deletions) have nothing to copy and
    // are skipped. Throws on any copy failure — callers must not proceed to a
    // destructive step on a partial backup.
    copyPaths(relPaths) {
      const copied = [];
      for (const rel of relPaths) {
        const src = path.join(repoDir, rel);
        try { fs.lstatSync(src); } catch (_) { continue; }
        const dest = path.join(this.ensureDir(), rel);
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.cpSync(src, dest, { recursive: true, verbatimSymlinks: true, force: true });
        copied.push(rel);
      }
      return copied;
    },
  };
}

// ─── (i) index.lock ───────────────────────────────────────────────────────────
// A lock older than 10 minutes is a crashed git process's leftover: remove it.
// A younger one may belong to a live git process or an open editor — removing
// it could corrupt the index, so report it with the exact command and stop.
function removeLockCommand(lockPath, platform = process.platform) {
  if (platform === 'win32') return `del "${lockPath}"    (PowerShell: Remove-Item "${lockPath}")`;
  return `rm "${lockPath}"`;
}

function checkIndexLock(repoDir, { now = Date.now(), platform = process.platform } = {}) {
  const lock = path.join(absoluteGitDir(repoDir), 'index.lock');
  let st;
  try { st = fs.statSync(lock); } catch (_) { return { state: 'none', lock }; }
  const ageMs = now - st.mtimeMs;
  if (ageMs > LOCK_STALE_MS) {
    fs.unlinkSync(lock);
    return { state: 'removed', lock, ageMs };
  }
  return { state: 'fresh', lock, ageMs, removeCmd: removeLockCommand(lock, platform) };
}

// ─── (ii) unmerged paths ──────────────────────────────────────────────────────
function unmergedPaths(repoDir) {
  const out = git(repoDir, ['diff', '--name-only', '-z', '--diff-filter=U']);
  return [...new Set(out.split('\0').filter(Boolean))];
}

// Copy each unmerged file to the backup folder, then clear its unmerged index
// state while KEEPING the working-tree content (`git reset -q -- <paths>`), so
// `git stash` can run and the content rides along in it.
function rescueUnmerged(repoDir, backup) {
  const paths = unmergedPaths(repoDir);
  if (paths.length === 0) return { paths };
  backup.copyPaths(paths); // throws -> caller aborts before touching the index
  try {
    git(repoDir, ['reset', '-q', '--', ...paths], { GIT_LITERAL_PATHSPECS: '1' });
  } catch (_) {
    // `git reset` can exit non-zero just to report remaining unstaged changes;
    // what matters is whether the unmerged entries are gone.
  }
  const left = unmergedPaths(repoDir);
  if (left.length) throw new Error('could not clear the unmerged state of: ' + left.join(', '));
  return { paths, dir: backup.dir };
}

// Every changed / staged / untracked path (not ignored ones). -z output is
// unquoted, and a rename/copy entry is "XY new\0old\0" — keep the new path,
// which is the one that exists in the working tree.
function changedPaths(repoDir) {
  const parts = git(repoDir, ['status', '--porcelain=v1', '-z', '--untracked-files=all']).split('\0');
  const out = [];
  for (let i = 0; i < parts.length; i++) {
    const entry = parts[i];
    if (!entry) continue;
    out.push(entry.slice(3));
    if (entry[0] === 'R' || entry[0] === 'C') i++;
  }
  return out;
}

// ─── HEAD vs origin/main ──────────────────────────────────────────────────────
function revParse(repoDir, ref) {
  return git(repoDir, ['rev-parse', '--verify', '-q', ref + '^{commit}']).trim();
}

function isAncestor(repoDir, a, b) {
  try {
    execFileSync('git', ['-C', repoDir, 'merge-base', '--is-ancestor', a, b], { stdio: 'pipe' });
    return true;
  } catch (err) {
    if (err.status === 1) return false;
    throw err;
  }
}

// 'same' | 'ff' (HEAD behind) | 'ahead' (origin behind) | 'diverged'
function classify(repoDir, head, upstream = UPSTREAM) {
  const up = revParse(repoDir, upstream);
  if (head === up) return 'same';
  if (isAncestor(repoDir, head, up)) return 'ff';
  if (isAncestor(repoDir, up, head)) return 'ahead';
  return 'diverged';
}

function commitsIn(repoDir, range) {
  const out = git(repoDir, ['log', '--no-merges', '--reverse', '--format=%H%x1f%at%x1f%s', range]);
  return out.split('\n').filter(Boolean).map(line => {
    const [sha, at, ...rest] = line.split('\x1f');
    return { sha, at, subject: rest.join('\x1f') };
  });
}

// A history rewrite (filter-branch / filter-repo / amend chain) keeps each
// commit's author date and subject but changes its SHA. So a local commit with
// an upstream twin of identical author date + subject is a pre-rewrite copy;
// one without a twin is genuine local work the user must not lose.
function findCounterparts(repoDir, upstream = UPSTREAM) {
  const local = commitsIn(repoDir, `${upstream}..HEAD`);
  const remote = commitsIn(repoDir, `HEAD..${upstream}`);
  const keys = new Set(remote.map(c => c.at + '\x1f' + c.subject));
  const matched = [];
  const unmatched = [];
  for (const c of local) (keys.has(c.at + '\x1f' + c.subject) ? matched : unmatched).push(c);
  return { local, matched, unmatched };
}

function createBackupBranch(repoDir, stamp, sha) {
  let name = `agency-backup/${stamp}`;
  for (let n = 2; ; n++) {
    try {
      git(repoDir, ['show-ref', '--verify', '--quiet', `refs/heads/${name}`]);
      name = `agency-backup/${stamp}-${n}`; // exists — try the next suffix
    } catch (_) {
      break;
    }
  }
  git(repoDir, ['branch', name, sha]);
  return name;
}

module.exports = {
  LOCK_STALE_MS,
  timestamp,
  createBackup,
  removeLockCommand,
  checkIndexLock,
  unmergedPaths,
  rescueUnmerged,
  changedPaths,
  revParse,
  isAncestor,
  classify,
  commitsIn,
  findCounterparts,
  createBackupBranch,
};
