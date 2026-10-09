// retired-prune.js - delete files the repo RETIRED from an installed agency root.
//
// syncSkills/syncAgents/... only add or update files, so a skill, agent, runbook
// or core doc the repo later deleted stays installed (and registered) forever.
// retired-manifest.json (generated from git history by
// scripts/gen-retired-manifest.py) lists every such path with the sha256 of
// every version the repo ever shipped there. This step reads it:
//
//   installed file's hash is a shipped version  -> untouched leftover: deleted
//   hash is NOT a shipped version (user edited) -> collected, listed under
//        "You changed these", then archived to <root>/archive/agency-retired-<date>/
//        or deleted, per --retired=archive|delete|ask (ask on a terminal, archive
//        without one; nothing edited is ever deleted unless the choice is delete)
//   path not in the manifest                    -> never touched
//
// Layout: skills/ agents/ runbooks/ core/ map 1:1 under <root>, exactly as
// install.sh, install.ps1 and cli/commands/sync-assets.js write them. (Only
// exception: the installers copy agents/ as *.md only, so a retired non-.md file
// under agents/ is simply absent from an install; harmless here.)
//
// Safety, in order: the repo checkout itself is always refused (even with
// force); a root that is a git work tree is skipped unless force (a live,
// git-managed root can legitimately hold files the repo dropped); symlinks are
// never followed; a manifest path outside the four trees is ignored.
//
// Used by: install.sh / install.ps1 (CLI form), `agency upgrade` and
// `agency init` (autoPrune), `agency prune`.
//
//   node cli/lib/retired-prune.js prune|status [--root <dir>] [--repo <repoDir>]
//        [--dry-run] [--force] [--json] [--retired=archive|delete|ask]
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { resolveRoot } = require('./hooks-merge.js');

const TREES = ['skills', 'agents', 'runbooks', 'core'];
const MANIFEST_NAME = 'retired-manifest.json';
const LOG_REL = path.join('logs', 'agency-retired.log');
const CHOICES = ['archive', 'delete', 'ask'];

const fwd = (p) => String(p).split(path.sep).join('/');
const sha256Lf = (buf) =>
  crypto.createHash('sha256').update(Buffer.from(buf.toString('latin1').replace(/\r\n/g, '\n'), 'latin1')).digest('hex');

function localDate(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function localStamp(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${localDate(d)} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function lstatOrNull(p) {
  try { return fs.lstatSync(p); } catch { return null; }
}
function realOrNull(p) {
  try { return fs.realpathSync(p); } catch { return null; }
}
const samePath = (a, b) => (process.platform === 'win32' || process.platform === 'darwin'
  ? a.toLowerCase() === b.toLowerCase() : a === b);

function isGitWorkTree(root, env) {
  if (lstatOrNull(path.join(root, '.git'))) return true;
  const e = { ...(env || process.env) };
  delete e.GIT_DIR; delete e.GIT_WORK_TREE; delete e.GIT_INDEX_FILE;
  try {
    const r = spawnSync('git', ['-C', root, 'rev-parse', '--is-inside-work-tree'], { encoding: 'utf8', env: e, timeout: 10000 });
    return r.status === 0 && String(r.stdout).trim() === 'true';
  } catch { return false; }
}

// "skills/foo/SKILL.md" -> {kind:'skill', name:'foo'}
function classify(p) {
  const parts = p.split('/');
  const base = parts[parts.length - 1].replace(/\.md$/, '');
  switch (parts[0]) {
    case 'skills': return { kind: 'skill', name: parts.length > 2 ? parts[1] : base };
    case 'agents': return { kind: 'agent', name: base };
    case 'runbooks': return { kind: 'runbook', name: base };
    default: return { kind: 'core', name: parts.slice(1).join('/') };
  }
}

function safeManifestPath(p) {
  if (typeof p !== 'string' || !p || p.includes('\\') || p.includes('\0') || path.isAbsolute(p) || /^[A-Za-z]:/.test(p)) return false;
  const parts = p.split('/');
  if (parts.length < 2 || parts.some((s) => s === '' || s === '.' || s === '..')) return false;
  return TREES.includes(parts[0]);
}

function loadManifest(file) {
  let raw;
  try { raw = fs.readFileSync(file, 'utf8'); } catch (e) {
    return e.code === 'ENOENT' ? { missing: true } : { error: `cannot read ${file}: ${e.message}` };
  }
  try {
    const m = JSON.parse(raw);
    if (!m || typeof m !== 'object' || !m.paths || typeof m.paths !== 'object' || Array.isArray(m.paths)) {
      return { error: `${file} has no "paths" object` };
    }
    return { manifest: m };
  } catch (e) { return { error: `${file} is not valid JSON: ${e.message}` }; }
}

// First free target: <dir>/<P>, then <P>.1, <P>.2 ...
function freeTarget(archiveDir, rel) {
  const first = path.join(archiveDir, ...rel.split('/'));
  if (!lstatOrNull(first)) return first;
  for (let i = 1; ; i++) if (!lstatOrNull(`${first}.${i}`)) return `${first}.${i}`;
}

function moveFile(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  try { fs.renameSync(src, dest); } catch (e) {
    if (e.code !== 'EXDEV') throw e;
    fs.copyFileSync(src, dest);
    fs.unlinkSync(src);
  }
}

// Remove dirs emptied by this run, walking up from each touched file's dir and
// stopping at (never removing) the tree root. A dir with ANY entry stays.
function removeEmptyDirs(root, relFiles) {
  const removed = [];
  const dirs = new Set();
  for (const rel of relFiles) {
    const parts = rel.split('/');
    for (let n = parts.length - 1; n >= 2; n--) dirs.add(parts.slice(0, n).join('/'));
  }
  for (const rel of [...dirs].sort((a, b) => b.split('/').length - a.split('/').length)) {
    const abs = path.join(root, ...rel.split('/'));
    const st = lstatOrNull(abs);
    if (!st || !st.isDirectory() || st.isSymbolicLink()) continue;
    try {
      if (fs.readdirSync(abs).length === 0) { fs.rmdirSync(abs); removed.push(rel); }
    } catch { /* keep it */ }
  }
  return removed;
}

function defaultPrompter() {
  let rl = null;
  return {
    ask(question) {
      const readline = require('readline');
      if (!rl) rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      return new Promise((resolve) => {
        rl.once('close', () => resolve(''));
        rl.question(question, (a) => resolve(a));
      });
    },
    close() { if (rl) { rl.removeAllListeners('close'); rl.close(); } },
  };
}
const firstLetter = (a) => String(a == null ? '' : a).trim().toLowerCase().charAt(0);

function resolveMode(opts, env, isTTY) {
  let requested = opts.retired || env.AGENCY_RETIRED || '';
  requested = String(requested).toLowerCase();
  if (!CHOICES.includes(requested)) requested = '';
  const explicit = requested === 'archive' || requested === 'delete';
  let mode = requested || 'ask';
  let degraded = false;
  if (mode === 'ask' && !isTTY) { mode = 'archive'; degraded = true; }
  return { mode, explicit, degraded };
}

async function pruneRetired(opts = {}) {
  const env = opts.env || process.env;
  const platform = opts.platform || process.platform;
  const now = opts.now instanceof Date ? opts.now : new Date();
  const out = opts.console;
  const say = (l) => { if (out && typeof out.log === 'function') out.log(l); };
  const root = resolveRoot(opts.root, { env, platform });
  const repoDir = path.resolve(opts.repoDir || path.join(__dirname, '..', '..'));
  const manifestPath = opts.manifestPath || path.join(repoDir, MANIFEST_NAME);
  const dryRun = !!opts.dryRun;
  const res = {
    status: 'unchanged', reason: '', root, dryRun,
    removed: [], archived: [], skipped: [], dirsRemoved: [], edited: [],
    archiveDir: null, mode: null, note: [], logFile: null,
  };

  const realRoot = realOrNull(root);
  if (!realRoot) { res.status = 'skipped'; res.reason = 'no-root'; return res; }
  const realRepo = realOrNull(repoDir);
  if (realRepo && samePath(realRoot, realRepo)) { res.status = 'skipped'; res.reason = 'repo-root'; return res; }
  if (!opts.force && isGitWorkTree(root, env)) { res.status = 'skipped'; res.reason = 'git-root'; return res; }

  const loaded = loadManifest(manifestPath);
  if (loaded.missing) { res.status = 'skipped'; res.reason = 'no-manifest'; res.manifestPath = manifestPath; return res; }
  if (loaded.error) { res.status = 'error'; res.reason = loaded.error; return res; }
  const paths = loaded.manifest.paths;

  // 1. Scan: classify every manifest path that is present on disk.
  const unmodified = [];
  const edited = [];
  for (const p of Object.keys(paths).sort()) {
    if (!safeManifestPath(p)) continue;
    const parts = p.split('/');
    let cur = root;
    let symlinkAncestor = false;
    let missing = false;
    for (let i = 0; i < parts.length - 1; i++) {
      cur = path.join(cur, parts[i]);
      const st = lstatOrNull(cur);
      if (!st) { missing = true; break; }
      if (st.isSymbolicLink()) { symlinkAncestor = true; break; }
      if (!st.isDirectory()) { missing = true; break; }
    }
    if (missing) continue;
    const file = path.join(root, ...parts);
    if (symlinkAncestor) {
      if (fs.existsSync(file)) res.skipped.push({ path: p, reason: 'symlink' });
      continue;
    }
    const st = lstatOrNull(file);
    if (!st) continue;
    if (st.isSymbolicLink()) { res.skipped.push({ path: p, reason: 'symlink' }); continue; }
    if (!st.isFile()) { res.skipped.push({ path: p, reason: 'not-a-file' }); continue; }
    try {
      const h = sha256Lf(fs.readFileSync(file));
      const shipped = Array.isArray(paths[p]) ? paths[p] : [];
      (shipped.includes(h) ? unmodified : edited).push(p);
    } catch (e) { res.skipped.push({ path: p, reason: `error: ${e.code || e.message}` }); }
  }

  // 2. Edited files: note, then decide (archive / delete / ask) before touching anything.
  const decisions = new Map(); // path -> 'archive' | 'delete'
  const { mode, explicit, degraded } = resolveMode(opts, env, opts.isTTY !== undefined ? !!opts.isTTY : !!(process.stdin.isTTY && process.stdout.isTTY));
  res.mode = mode;
  if (edited.length) {
    res.note.push('You changed these');
    res.note.push('Upstream retired these files; your copy has local edits:');
    for (const p of edited) {
      const c = classify(p);
      res.edited.push({ path: p, kind: c.kind, name: c.name, decision: 'archive' });
      res.note.push(`  ${c.kind} ${c.name}  ${p}`);
    }
    for (const l of res.note) say(l);

    if (mode === 'delete') {
      for (const p of edited) decisions.set(p, 'delete');
    } else if (mode === 'ask' && !dryRun) {
      const prompter = opts.prompt ? { ask: opts.prompt, close() {} } : defaultPrompter();
      try {
        const a = firstLetter(await prompter.ask('[a]rchive all / [d]elete all / [c]hoose per item: '));
        if (a === 'd') for (const p of edited) decisions.set(p, 'delete');
        else if (a === 'c') {
          for (const e of res.edited) {
            const x = firstLetter(await prompter.ask(`  ${e.kind} ${e.name}  ${e.path}  [a]rchive/[d]elete: `));
            decisions.set(e.path, x === 'd' ? 'delete' : 'archive');
          }
        }
      } finally { prompter.close(); }
    } else if (degraded || (!explicit && mode !== 'ask')) {
      const msg = 'Not asked (no terminal). Archived. To choose: agency prune --retired=delete|ask';
      res.note.push(msg); say(msg);
    }
    for (const p of edited) if (!decisions.has(p)) decisions.set(p, 'archive');
    for (const e of res.edited) e.decision = decisions.get(e.path);
  }

  // 3. Apply (or, for dry-run, just report).
  const archiveName = `agency-retired-${localDate(now)}`;
  const archiveDir = path.join(root, 'archive', archiveName);
  const touched = [];
  const doDelete = (p) => {
    if (!dryRun) fs.unlinkSync(path.join(root, ...p.split('/')));
    res.removed.push(p); touched.push(p);
  };
  for (const p of unmodified) {
    try { doDelete(p); } catch (e) { res.skipped.push({ path: p, reason: `error: ${e.code || e.message}` }); }
  }
  for (const p of edited) {
    try {
      if (decisions.get(p) === 'delete') doDelete(p);
      else {
        const to = freeTarget(archiveDir, p);
        if (!dryRun) moveFile(path.join(root, ...p.split('/')), to);
        res.archived.push({ path: p, to }); touched.push(p);
      }
    } catch (e) { res.skipped.push({ path: p, reason: `error: ${e.code || e.message}` }); }
  }
  if (res.archived.length) res.archiveDir = archiveDir;
  if (!dryRun) res.dirsRemoved = removeEmptyDirs(root, touched);

  // 4. Log every real run that found edited files.
  if (edited.length && !dryRun) {
    try {
      const logFile = path.join(root, LOG_REL);
      fs.mkdirSync(path.dirname(logFile), { recursive: true });
      const lines = [`[${localStamp(now)}] retired-files prune (mode: ${mode})`, ...res.note];
      for (const e of res.edited) {
        const a = res.archived.find((x) => x.path === e.path);
        lines.push(`  ${e.decision === 'delete' ? 'deleted' : 'archived'}: ${e.path}${a ? ` -> ${fwd(path.relative(root, a.to))}` : ''}`);
      }
      fs.appendFileSync(logFile, lines.join('\n') + '\n\n');
      res.logFile = logFile;
    } catch { /* the log is a convenience; never fail the prune over it */ }
  }

  res.status = res.removed.length || res.archived.length ? 'changed' : 'unchanged';
  return res;
}

function formatResult(res) {
  const lines = [];
  if (res.status === 'skipped') {
    if (res.reason === 'git-root') lines.push(`Retired files: skipped (${res.root} is a git work tree; run: agency prune --force)`);
    else if (res.reason === 'repo-root') lines.push(`Retired files: skipped (${res.root} is the agency repo checkout itself)`);
    else if (res.reason === 'no-manifest') lines.push('Retired files: skipped (no retired-manifest.json in the agency repo)');
    else if (res.reason === 'no-root') lines.push(`Retired files: skipped (${res.root} does not exist)`);
    else lines.push(`Retired files: skipped (${res.reason})`);
    return lines;
  }
  if (res.status === 'error') return [`Retired files: error (${res.reason})`];
  const n = res.removed.length;
  const m = res.archived.length;
  if (!n && !m) lines.push('Retired files: none to remove');
  else if (res.dryRun) lines.push(`Retired files: ${n} would be removed, ${m} would be archived (modified)`);
  else lines.push(`Retired files: ${n} removed, ${m} archived (modified)`);
  for (const a of res.archived) {
    lines.push(`Retired file kept (you edited it): ${a.path} -> ${fwd(path.relative(res.root, a.to))}`);
  }
  if (m && res.archiveDir) lines.push(`Archived in: ${res.archiveDir}`);
  if (res.logFile) lines.push(`Details logged to: ${res.logFile}`);
  for (const s of res.skipped) lines.push(`Retired file skipped (${s.reason}): ${s.path}`);
  return lines;
}

// Never throws and, without a terminal, never blocks: safe to call from the
// installers and from upgrade/init after the asset sync.
async function autoPrune({ root, repoDir, console: out, indent = '', retired, isTTY, env, prompt, force, dryRun } = {}) {
  const pre = (l) => `${indent}${l}`;
  const wrapped = out ? { log: (l) => out.log(pre(l)), error: (l) => (out.error || out.log).call(out, pre(l)) } : undefined;
  let res;
  try {
    res = await pruneRetired({ root, repoDir, console: wrapped, retired, isTTY, env, prompt, force, dryRun });
  } catch (e) {
    res = { status: 'error', reason: e && e.message ? e.message : String(e), root, removed: [], archived: [], skipped: [], dirsRemoved: [], edited: [], note: [] };
  }
  if (wrapped) for (const l of formatResult(res)) wrapped.log(l);
  return res;
}

const USAGE = [
  'Usage: agency prune [status] [--dry-run] [--force] [--json] [--root <dir>] [--retired=archive|delete|ask]',
  '  Removes files the agency repo retired (skills/agents/runbooks/core) from your agency root.',
  '  An untouched retired file is deleted; one you edited is archived to archive/agency-retired-<date>/',
  '  (or deleted/asked per --retired). Anything not in retired-manifest.json is never touched.',
  '  --force  also prune a root that is a git work tree (never the agency repo checkout itself)',
];

async function runCli(argv, con = console, defaults = {}) {
  const args = [...argv];
  let sub = 'prune';
  if (args[0] === 'prune' || args[0] === 'status') sub = args.shift();
  const o = { root: defaults.root, repoDir: defaults.repoDir };
  let json = false;
  const unknown = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--dry-run') o.dryRun = true;
    else if (a === '--force') o.force = true;
    else if (a === '--json') json = true;
    else if (a === '--root' && args[i + 1]) o.root = args[++i];
    else if (/^--root=./.test(a)) o.root = a.slice(7);
    else if (a === '--repo' && args[i + 1]) o.repoDir = args[++i];
    else if (/^--repo=./.test(a)) o.repoDir = a.slice(7);
    else if (a === '--retired' && args[i + 1]) o.retired = args[++i];
    else if (/^--retired=./.test(a)) o.retired = a.slice(10);
    else unknown.push(a);
  }
  if (o.retired !== undefined && !CHOICES.includes(String(o.retired).toLowerCase())) unknown.push(`--retired=${o.retired}`);
  if (unknown.length) {
    con.error(`Unknown option: ${unknown.join(' ')}`);
    for (const l of USAGE) con.error(l);
    return 1;
  }
  if (sub === 'status') o.dryRun = true;
  const res = await pruneRetired({ ...o, console: json ? undefined : con });
  if (json) con.log(JSON.stringify(res, null, 2));
  else for (const l of formatResult(res)) con.log(l);
  return res.status === 'error' ? 1 : 0;
}

module.exports = { pruneRetired, autoPrune, formatResult, runCli, classify, sha256Lf, TREES, MANIFEST_NAME };

if (require.main === module) {
  runCli(process.argv.slice(2), console).then((code) => { process.exitCode = code; });
}
