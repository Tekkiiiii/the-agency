const { existsSync, mkdirSync, copyFileSync, readdirSync, readFileSync, chmodSync } = require('fs');
const { join } = require('path');
const { createHash } = require('crypto');

function fileHash(path) {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

// Content-hash comparison. mtime/size are unreliable here: git checkout resets
// mtimes on every clone, and same-size edits (common in short skill diffs) are
// invisible to a size check. Hash is the only comparison that can't lie.
function shouldCopy(srcPath, destPath) {
  if (!existsSync(destPath)) return true;
  return fileHash(srcPath) !== fileHash(destPath);
}

// Never sync macOS junk or Python bytecode cache regardless of caller filter.
// Checked against entry.name before the isDirectory() branch in syncDir, so
// this already covers directories too — '__pycache__' skips the whole dir.
const ALWAYS_SKIP = new Set(['.DS_Store', '__pycache__']);

// Recursively copies files under `src` into `dest`, hash-comparing each one.
// `include(filename)` gates which files get copied at each level (agents/
// stays .md-only, matching its pre-hash-rewrite behavior; skills/ passes
// everything since multi-file skills ship non-.md assets, e.g.
// html-plan-style/style.css). Returns { updated: [...], preserved: [...] }
// with paths relative to the root passed in by the caller.
function syncDir(src, dest, rootLabel, result, include = () => true) {
  mkdirSync(dest, { recursive: true });
  const entries = readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    if (ALWAYS_SKIP.has(entry.name)) continue;
    const srcPath = join(src, entry.name);
    const destPath = join(dest, entry.name);
    const label = rootLabel ? `${rootLabel}/${entry.name}` : entry.name;

    if (entry.isDirectory()) {
      syncDir(srcPath, destPath, label, result, include);
    } else if (include(entry.name)) {
      if (shouldCopy(srcPath, destPath)) {
        copyFileSync(srcPath, destPath);
        result.updated.push(label);
      } else {
        result.preserved.push(label);
      }
    }
  }
}

// Canonical layout is directory-only: skills/<name>/SKILL.md (+ any
// supporting files, e.g. full-scan.md). Flat skills/<name>.md is no longer
// valid — see scripts/check-flat-skills.js, which fails CI if one reappears.
//
// Returns { updated, preserved } as arrays of skill NAMES (not file paths) —
// a skill counts as "updated" if any file inside its directory changed.
// `skillCount` is the total number of repo skill directories, for the
// repo-vs-installed count check callers run post-sync.
function syncSkills(repoDir, destDir, console) {
  const srcDir = join(repoDir, 'skills');
  const result = { updated: [], preserved: [], skillCount: 0 };

  if (!existsSync(srcDir)) {
    console.log('  ⚠ No skills/ directory in repo — skipping');
    return result;
  }

  mkdirSync(destDir, { recursive: true });

  const skillDirs = readdirSync(srcDir, { withFileTypes: true }).filter(
    e => e.isDirectory() && existsSync(join(srcDir, e.name, 'SKILL.md'))
  );

  for (const entry of skillDirs) {
    const name = entry.name;
    const fileResult = { updated: [], preserved: [] };
    syncDir(join(srcDir, name), join(destDir, name), name, fileResult);
    if (fileResult.updated.length > 0) {
      result.updated.push(name);
    } else {
      result.preserved.push(name);
    }
  }

  const indexSrc = join(srcDir, 'INDEX.md');
  if (existsSync(indexSrc)) {
    copyFileSync(indexSrc, join(destDir, 'INDEX.md'));
  }

  result.skillCount = skillDirs.length;
  return result;
}

// Simple recursive copy with the same hash-compare skip logic, no
// updated/preserved bookkeeping — used by `agency skill install <name>`
// where the caller only needs the files on disk, not a change report.
function syncDirRecursive(src, dest) {
  const result = { updated: [], preserved: [] };
  syncDir(src, dest, '', result);
  return result;
}

function syncAgents(repoDir, destDir, console) {
  const srcDir = join(repoDir, 'agents');
  const result = { updated: [], preserved: [] };

  if (!existsSync(srcDir)) {
    console.log('  ⚠ No agents/ directory in repo — skipping');
    return { updated: 0, preserved: 0 };
  }

  // Agents keep the pre-hash-rewrite .md-only filter — agents/scripts/*.sh,
  // *.py, and other support files were never synced to installs before this
  // change and stay out of scope here (skills/ is the only layout this task
  // fixes; widening agents/ sync scope is a separate decision).
  syncDir(srcDir, destDir, '', result, name => name.endsWith('.md'));
  return { updated: result.updated.length, preserved: result.preserved.length };
}

// Generic top-level-directory sync. Everything under repo/<dirName> is copied
// into destDir, hash-compared, with __pycache__/.DS_Store excluded via
// ALWAYS_SKIP. `chmodExec` marks copied .sh/.py/.js +x so direct invocation
// (./scripts/foo.sh) works. Returns counts, mirroring syncAgents' shape.
//
// This is the single mechanism behind every non-skill, non-agent asset tree
// the deployed layout needs. Adding a new one is a one-line wrapper below —
// which matters, because every gap in this list is a class of dangling
// reference in shipped agent/runbook docs (see the deploy matrix in
// docs/INSTALL-LAYOUT.md).
function syncTree(repoDir, destDir, dirName, console, { chmodExec = false } = {}) {
  const srcDir = join(repoDir, dirName);
  const result = { updated: [], preserved: [] };

  if (!existsSync(srcDir)) {
    console.log(`  ⚠ No ${dirName}/ directory in repo — skipping`);
    return { updated: 0, preserved: 0 };
  }

  // Belt-and-suspenders: __pycache__ dirs are excluded by ALWAYS_SKIP inside
  // syncDir already, but also gate stray .pyc files here in case one ever
  // lands outside a __pycache__ dir.
  syncDir(srcDir, destDir, '', result, name => !name.endsWith('.pyc'));

  if (chmodExec) {
    for (const label of result.updated) {
      if (/\.(sh|py|js)$/.test(label)) {
        try { chmodSync(join(destDir, label), 0o755); } catch (_) {}
      }
    }
  }

  return { updated: result.updated.length, preserved: result.preserved.length };
}

// scripts/ ships the .py/.sh/.js support tooling that shipped skills invoke
// by absolute path (e.g. `python3 {agency-root}/scripts/save-state.py`).
function syncScripts(repoDir, destDir, console) {
  return syncTree(repoDir, destDir, 'scripts', console, { chmodExec: true });
}

// hooks/ ships the lifecycle hooks AND emit-metric.sh, which shipped agent
// defs, runbooks and scripts invoke as `{agency-root}/hooks/emit-metric.sh`.
// install.sh already deployed hooks/; the CLI path did not, so a CLI-only
// install had ~90 dangling metric-emit references. Same +x treatment as
// scripts/ — these are executed directly by settings.json hook wiring.
function syncHooks(repoDir, destDir, console) {
  return syncTree(repoDir, destDir, 'hooks', console, { chmodExec: true });
}

// runbooks/ ships the protocol docs that deployed agents/ files reference by
// `{agency-root}/runbooks/...` path. Nothing deployed runbooks/ before this,
// so every one of those references 404'd in every install. Docs only — no +x.
function syncRunbooks(repoDir, destDir, console) {
  return syncTree(repoDir, destDir, 'runbooks', console);
}

module.exports = {
  syncSkills, syncAgents, syncScripts, syncHooks, syncRunbooks,
  syncTree, syncDirRecursive, shouldCopy, fileHash,
};
