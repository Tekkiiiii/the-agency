#!/usr/bin/env node
'use strict';

// mods-merge.js — wire the repo's mods (mods/<name>/) into the user's
// settings.json as env.CLAUDE_CODE_PLUGIN_DIRS, record what we added, and remove
// exactly that on uninstall.
//
// Why this exists: the repo ships Claude Code mods (plugins of function hooks).
// Claude Code 2.1.287+ loads every entry of env.CLAUDE_CODE_PLUGIN_DIRS in the
// user settings file as `<name>@inline`. Without this, a mod is a folder nobody
// loads.
//
// Callers: install.sh, install.ps1, `agency init`, `agency upgrade` (all through
// autoSyncMods or the CLI form) and `agency mods sync|remove|status`:
//   node cli/lib/mods-merge.js sync|remove|status [--root <dir>] [--repo <repoDir>] [--auto] [--json]
//   --auto   called by an installer/upgrade: honour AGENCY_NO_MODS=1
//
// What it does, per mod, on `sync`:
//   1. copy mods/<dir> to <root>/mods/<dir> (the repo checkout can move or be
//      deleted; the settings entry must keep working), skipping node_modules,
//      __pycache__ and .claude-plugin/types
//   2. append the absolute path of that copy to the value (':' on Unix, ';' on
//      Windows), AFTER every entry the user already had, untouched and in order
//
// Dedupe is by manifest NAME, not by path: two entries that resolve to the same
// `name` in .claude-plugin/plugin.json both load, so hooks would fire twice. A mod
// whose name a user entry already provides (the entry is a plugin dir, or a
// folder whose immediate subfolders are plugin dirs) is skipped, reason
// "provided". A mod whose <root>/mods/<dir> already exists and is not ours (a
// maintainer's live checkout, say) is skipped, reason "exists", and never touched.
//
// Ownership (what `remove` and the next `sync` may delete): the entries and the
// dirs recorded in <root>/hooks/.agency-hooks-state.json under `mods`:
//   { "installed": ["<name>", ...], "entries": ["<abs path>", ...] }
// The two arrays are parallel (same index = same mod). hooks-merge.js carries the
// key through its own rewrites. A mod the repo stops shipping, or that the user
// now provides themselves, is pruned (entry and dir) on the next sync.
//
// Safety: same as hooks-merge.js. A timestamped settings.json.bak-* copy sits NEXT
// TO settings.json before any change; the write is a temp file plus rename; no
// change => no write, no backup. Malformed settings.json => nothing is written.
// Gate: Claude Code older than MIN_VERSION (or not found) => nothing is written.

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const hm = require('./hooks-merge.js');

const REPO_DIR = path.resolve(__dirname, '..', '..');
const MIN_VERSION = '2.1.287';
const KEY = 'CLAUDE_CODE_PLUGIN_DIRS';
const USAGE = 'Usage: node cli/lib/mods-merge.js sync|remove|status [--root <dir>] [--repo <repoDir>] [--auto] [--json]';
const RESTART_LINE = 'Restart Claude Code to load the mods.';

// ---------------------------------------------------------------------------
// version

function parseVersion(s) {
  const m = String(s == null ? '' : s).match(/(\d+)\.(\d+)\.(\d+)/);
  return m ? m[0] : null;
}

function cmpVersion(a, b) {
  const x = a.split('.').map(Number);
  const y = b.split('.').map(Number);
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
  return 0;
}

function detectClaudeVersion(env, platform) {
  if (env.AGENCY_CLAUDE_VERSION) return parseVersion(env.AGENCY_CLAUDE_VERSION);
  try {
    const r = spawnSync('claude', ['--version'], { encoding: 'utf8', timeout: 10000, shell: platform === 'win32' });
    if (r.error || r.status !== 0) return null;
    return parseVersion(r.stdout);
  } catch (_) {
    return null;
  }
}

function resolveVersion(ctx, opts) {
  if (opts.claudeVersion !== undefined) return opts.claudeVersion === null ? null : parseVersion(opts.claudeVersion);
  return detectClaudeVersion(ctx.env, ctx.platform);
}

// ---------------------------------------------------------------------------
// context and result

function makeCtx(opts) {
  const platform = opts.platform || process.platform;
  const env = opts.env || process.env;
  const home = opts.home || os.homedir();
  const root = hm.resolveRoot(opts.root, { env, home, platform });
  const repoDir = path.resolve(opts.repoDir || REPO_DIR);
  return { platform, env, home, root, repoDir, sep: platform === 'win32' ? ';' : ':' };
}

function baseResult(action, ctx) {
  return {
    action,
    status: null,
    reason: null,
    error: null,
    root: ctx.root,
    settingsPath: path.join(ctx.root, 'settings.json'),
    repoDir: ctx.repoDir,
    version: null,
    backup: null,
    added: [],
    kept: [],
    skipped: [],
    pruned: [],
    copied: [],
    removed: [],
  };
}

// ---------------------------------------------------------------------------
// paths

function pathApi(platform) {
  return platform === 'win32' ? path.win32 : path.posix;
}

function lastSegment(p) {
  const parts = String(p).split(/[\\/]+/).filter(Boolean);
  return parts.length ? parts[parts.length - 1] : '';
}

// The string recorded in settings.json for <root>/mods/<dir>.
function entryFor(ctx, dir) {
  const p = path.resolve(ctx.root, 'mods', dir);
  return ctx.platform === 'win32' ? p.replace(/\//g, '\\') : p;
}

function expandHome(entry, home) {
  return (entry === '~' || /^~[\\/]/.test(entry)) ? home + entry.slice(1) : entry;
}

// Split a CLAUDE_CODE_PLUGIN_DIRS value. With ';' that is a plain split. With ':'
// a colon is NOT a separator when it is a drive-letter colon: it sits at the start
// of an entry, right after exactly one ASCII letter, and is followed by '\' or '/'
// (C:\x, c:/x). A value can hold such entries whichever separator the platform
// uses (hand-edited values, Git Bash paths, Windows temp dirs under an injected
// Unix platform), and cutting them apart orphans every entry we own.
function splitValue(raw, sep) {
  const s = String(raw);
  if (sep !== ':') return s.split(sep).map(x => x.trim()).filter(Boolean);
  const out = [];
  let start = 0;
  for (let i = 0; i < s.length; i++) {
    if (s[i] !== ':') continue;
    const next = s[i + 1];
    if (/^[A-Za-z]$/.test(s.slice(start, i).trim()) && (next === '\\' || next === '/')) continue;
    out.push(s.slice(start, i));
    start = i + 1;
  }
  out.push(s.slice(start));
  return out.map(x => x.trim()).filter(Boolean);
}

// ---------------------------------------------------------------------------
// plugin dirs

function readManifestName(dir, platform) {
  const file = path.join(dir, '.claude-plugin', 'plugin.json');
  if (!fs.existsSync(file)) return null;
  try {
    const m = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (m && typeof m.name === 'string' && m.name) return m.name;
  } catch (_) {}
  return lastSegment(dir);
}

// Names a user entry makes Claude Code load: the plugin itself, or every
// immediate subfolder that is a plugin, or (no manifest anywhere) the basename.
function providedNames(entry, ctx) {
  const dir = expandHome(entry, ctx.home);
  if (!pathApi(ctx.platform).isAbsolute(dir)) return []; // Claude Code skips relative entries
  const own = readManifestName(dir, ctx.platform);
  if (own) return [own];
  const names = [];
  try {
    for (const d of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1))) {
      let isDir = d.isDirectory();
      if (!isDir && d.isSymbolicLink()) { try { isDir = fs.statSync(path.join(dir, d.name)).isDirectory(); } catch (_) {} }
      if (!isDir) continue;
      const n = readManifestName(path.join(dir, d.name), ctx.platform);
      if (n) names.push(n);
    }
  } catch (_) {}
  return names.length ? names : [lastSegment(dir)];
}

function listRepoMods(repoDir) {
  const modsDir = path.join(repoDir, 'mods');
  let dirs;
  try {
    dirs = fs.readdirSync(modsDir, { withFileTypes: true });
  } catch (_) {
    return null;
  }
  const out = [];
  for (const d of dirs.sort((a, b) => (a.name < b.name ? -1 : 1))) {
    const src = path.join(modsDir, d.name);
    try { if (!fs.statSync(src).isDirectory()) continue; } catch (_) { continue; }
    if (!fs.existsSync(path.join(src, '.claude-plugin', 'plugin.json'))) continue;
    out.push({ name: readManifestName(src) || d.name, dir: d.name, src });
  }
  return out;
}

// ---------------------------------------------------------------------------
// copying

function excluded(rel) {
  const segs = rel.split('/');
  if (segs.includes('node_modules') || segs.includes('__pycache__')) return true;
  return rel === '.claude-plugin/types' || rel.startsWith('.claude-plugin/types/');
}

function walk(dir, rel, visit) {
  for (const d of fs.readdirSync(path.join(dir, rel), { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1))) {
    const r = rel ? `${rel}/${d.name}` : d.name;
    if (excluded(r)) continue;
    visit(r, d);
    if (d.isDirectory()) walk(dir, r, visit);
  }
}

function signature(dir) {
  const h = crypto.createHash('sha1');
  walk(dir, '', (rel, d) => {
    h.update(`${d.isDirectory() ? 'd' : 'f'}:${rel}\0`);
    if (d.isSymbolicLink()) h.update(fs.readlinkSync(path.join(dir, rel)));
    else if (d.isFile()) h.update(fs.readFileSync(path.join(dir, rel)));
  });
  return h.digest('hex');
}

function copyTree(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  walk(src, '', (rel, d) => {
    const from = path.join(src, rel);
    const to = path.join(dest, rel);
    if (d.isDirectory()) fs.mkdirSync(to, { recursive: true });
    else if (d.isSymbolicLink()) fs.symlinkSync(fs.readlinkSync(from), to);
    else if (d.isFile()) fs.copyFileSync(from, to);
  });
}

// Replace dest fully with a copy of src (temp sibling + rename).
function replaceDir(src, dest) {
  const tmp = `${dest}.agency-tmp-${process.pid}`;
  fs.rmSync(tmp, { recursive: true, force: true });
  try {
    copyTree(src, tmp);
    fs.rmSync(dest, { recursive: true, force: true });
    fs.renameSync(tmp, dest);
  } catch (e) {
    fs.rmSync(tmp, { recursive: true, force: true });
    throw e;
  }
}

function safeDirName(dir) {
  return !!dir && dir !== '.' && dir !== '..';
}

function removeOwnedDir(ctx, dir) {
  if (!safeDirName(dir)) return;
  fs.rmSync(path.join(ctx.root, 'mods', dir), { recursive: true, force: true });
}

function removeModsDirIfEmpty(ctx) {
  const d = path.join(ctx.root, 'mods');
  try { if (fs.readdirSync(d).length === 0) fs.rmdirSync(d); } catch (_) {}
}

// ---------------------------------------------------------------------------
// state (the `mods` key of the hooks state file)

function ownedPairs(state) {
  const m = state.mods;
  if (!hm.isPlainObject(m)) return [];
  const entries = Array.isArray(m.entries) ? m.entries.filter(e => typeof e === 'string') : [];
  const names = Array.isArray(m.installed) ? m.installed.filter(n => typeof n === 'string') : [];
  return entries.map((entry, i) => ({
    entry,
    dir: lastSegment(entry),
    name: names.length === entries.length ? names[i] : lastSegment(entry),
  }));
}

// Write state.mods (or drop it), keeping every other key of the state file. A
// state that ends up empty is deleted: readState() returns the same default.
function writeModsState(ctx, mods) {
  const file = hm.statePath(ctx.root);
  const exists = fs.existsSync(file);
  if (!exists && !mods) return;
  const s = hm.readState(ctx.root);
  if (hm.isPlainObject(s.disabled) && Object.keys(s.disabled).length === 0) delete s.disabled;
  delete s.mods;
  if (mods) s.mods = mods;
  if (!s.mods && Object.keys(s.hooks).length === 0 && !s.disabled) {
    if (exists) {
      fs.unlinkSync(file);
      try { fs.rmdirSync(path.dirname(file)); } catch (_) {}
    }
    return;
  }
  hm.writeStateIfChanged(ctx.root, s);
}

// ---------------------------------------------------------------------------
// planning (read-only)

function readValue(data) {
  if (data.env === undefined) return { raw: undefined };
  if (!hm.isPlainObject(data.env)) return { error: '"env" is not an object' };
  const raw = data.env[KEY];
  if (raw !== undefined && typeof raw !== 'string') return { error: `"env.${KEY}" is not a string` };
  return { raw };
}

function setValue(data, value) {
  if (value === null) {
    if (hm.isPlainObject(data.env)) {
      delete data.env[KEY];
      if (Object.keys(data.env).length === 0) delete data.env;
    }
    return;
  }
  if (!hm.isPlainObject(data.env)) data.env = {};
  data.env[KEY] = value;
}

function sameList(a, b) {
  return a.length === b.length && a.every((x, i) => x === b[i]);
}

function planSync(ctx, data, state, repoMods) {
  const cur = readValue(data);
  if (cur.error) return { error: cur.error };
  const entries = cur.raw === undefined ? [] : splitValue(cur.raw, ctx.sep);
  const owned = ownedPairs(state);
  const ownedEntries = new Set(owned.map(p => p.entry));
  const ownedDirs = new Set(owned.map(p => p.dir));
  const user = entries.filter(e => !ownedEntries.has(e));

  const provided = new Map();
  for (const e of user) for (const n of providedNames(e, ctx)) if (!provided.has(n)) provided.set(n, e);

  const installs = [];
  const skipped = [];
  for (const mod of repoMods) {
    if (provided.has(mod.name)) {
      skipped.push({ name: mod.name, dir: mod.dir, reason: 'provided', entry: provided.get(mod.name) });
      continue;
    }
    const dest = path.join(ctx.root, 'mods', mod.dir);
    if (fs.existsSync(dest) && !ownedDirs.has(mod.dir)) {
      skipped.push({ name: mod.name, dir: mod.dir, reason: 'exists' });
      continue;
    }
    const entry = entryFor(ctx, mod.dir);
    let copy = true;
    try { copy = !fs.existsSync(dest) || signature(dest) !== signature(mod.src); } catch (_) {}
    installs.push(Object.assign({ entry, dest, copy, wasOwned: ownedDirs.has(mod.dir) }, mod));
  }
  const installDirs = new Set(installs.map(i => i.dir));
  const pruned = owned.filter(p => !installDirs.has(p.dir));

  const wanted = user.concat(installs.map(i => i.entry));
  const valueChanged = !sameList(wanted, entries) && !(cur.raw === undefined && installs.length === 0);
  const newMods = installs.length
    ? { installed: installs.map(i => i.name), entries: installs.map(i => i.entry) }
    : null;
  return {
    installs, skipped, pruned, entries, wanted, valueChanged, newMods,
    added: installs.filter(i => !i.wasOwned || !entries.includes(i.entry)).map(i => i.name),
    kept: installs.filter(i => i.wasOwned && entries.includes(i.entry)).map(i => i.name),
    copied: installs.filter(i => i.copy).map(i => i.name),
  };
}

function fillFromPlan(res, plan) {
  res.added = plan.added;
  res.kept = plan.kept;
  res.copied = plan.copied;
  res.pruned = plan.pruned.map(p => p.name);
  res.skipped = plan.skipped;
}

// ---------------------------------------------------------------------------
// public API

function gate(ctx, opts, res) {
  const optOut = ctx.env.AGENCY_NO_MODS && ctx.env.AGENCY_NO_MODS !== '0';
  if (opts.auto && optOut) return Object.assign(res, { status: 'skipped', reason: 'opt-out' });
  res.version = resolveVersion(ctx, opts);
  if (!res.version || cmpVersion(res.version, MIN_VERSION) < 0) return Object.assign(res, { status: 'skipped', reason: 'version' });
  return null;
}

function syncMods(opts = {}) {
  const ctx = makeCtx(opts);
  const res = baseResult('sync', ctx);
  if (gate(ctx, opts, res)) return res;
  const repoMods = listRepoMods(ctx.repoDir);
  if (!repoMods) return Object.assign(res, { status: 'skipped', reason: 'no-mods' });
  const settings = hm.readSettings(res.settingsPath);
  if (settings.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath} is ${settings.error}` });
  const state = hm.readState(ctx.root);
  const plan = planSync(ctx, settings.data, state, repoMods);
  if (plan.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath}: ${plan.error}` });
  fillFromPlan(res, plan);
  const changed = plan.valueChanged || plan.copied.length > 0 || plan.pruned.length > 0;
  try {
    // Order matters: record ownership first (a half-finished run is then
    // re-done, never mistaken for a user's dir), settings next, deletions last
    // (settings never points at a dir that is already gone).
    writeModsState(ctx, plan.newMods);
    for (const i of plan.installs) if (i.copy) replaceDir(i.src, i.dest);
    if (plan.valueChanged) {
      setValue(settings.data, plan.wanted.join(ctx.sep));
      hm.commitSettings(res, settings, settings.data, opts);
    }
    for (const p of plan.pruned) removeOwnedDir(ctx, p.dir);
    if (plan.pruned.length) removeModsDirIfEmpty(ctx);
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'write-failed', error: e.message });
  }
  res.status = changed ? 'changed' : 'unchanged';
  return res;
}

function removeMods(opts = {}) {
  const ctx = makeCtx(opts);
  const res = baseResult('remove', ctx);
  const settings = hm.readSettings(res.settingsPath);
  if (settings.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath} is ${settings.error}` });
  const state = hm.readState(ctx.root);
  const owned = ownedPairs(state);
  const cur = readValue(settings.data);
  if (cur.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath}: ${cur.error}` });
  const ownedEntries = new Set(owned.map(p => p.entry));
  const entries = cur.raw === undefined ? [] : splitValue(cur.raw, ctx.sep);
  const rest = entries.filter(e => !ownedEntries.has(e));
  const valueChanged = rest.length !== entries.length;
  res.removed = owned.map(p => p.name);
  try {
    if (valueChanged) {
      setValue(settings.data, rest.length ? rest.join(ctx.sep) : null);
      hm.commitSettings(res, settings, settings.data, opts);
    }
    for (const p of owned) removeOwnedDir(ctx, p.dir);
    if (owned.length) removeModsDirIfEmpty(ctx);
    if (state.mods !== undefined) writeModsState(ctx, null);
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'write-failed', error: e.message });
  }
  res.status = (valueChanged || owned.length > 0 || state.mods !== undefined) ? 'changed' : 'unchanged';
  return res;
}

// Read-only: what is owned, what a sync would do now.
function statusMods(opts = {}) {
  const ctx = makeCtx(opts);
  const res = baseResult('status', ctx);
  res.version = resolveVersion(ctx, opts);
  res.gated = !res.version || cmpVersion(res.version, MIN_VERSION) < 0;
  const repoMods = listRepoMods(ctx.repoDir);
  if (!repoMods) return Object.assign(res, { status: 'skipped', reason: 'no-mods' });
  const settings = hm.readSettings(res.settingsPath);
  if (settings.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath} is ${settings.error}` });
  const plan = planSync(ctx, settings.data, hm.readState(ctx.root), repoMods);
  if (plan.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath}: ${plan.error}` });
  fillFromPlan(res, plan);
  res.owned = ownedPairs(hm.readState(ctx.root)).map(p => p.name);
  res.status = 'unchanged';
  return res;
}

// ---------------------------------------------------------------------------
// messages

function skippedLines(res) {
  return res.skipped.map(s => (s.reason === 'provided'
    ? `  skipped ${s.name} (already provided by ${s.entry})`
    : `  skipped ${s.name} (${path.join(res.root, 'mods', s.dir || s.name)} already exists and is not ours; left alone)`));
}

function formatResult(res) {
  const out = [];
  if (res.status === 'skipped') {
    if (res.reason === 'opt-out') return ['Mods: skipped (AGENCY_NO_MODS is set). To wire them later: agency mods sync'];
    if (res.reason === 'version') {
      return [`Mods: skipped (needs Claude Code ${MIN_VERSION}+, found ${res.version || 'none'}). After updating: agency mods sync`];
    }
    return [`Mods: skipped (no mods/ folder in ${res.repoDir})`];
  }
  if (res.status === 'error') {
    out.push(`Mods: could not update ${res.settingsPath}: ${res.error}`);
    out.push('  Nothing was written. Fix the file, then run: agency mods sync');
    return out;
  }
  if (res.action === 'remove') {
    if (res.status === 'unchanged') return ['Mods: nothing to remove'];
    out.push(`Mods: removed ${res.removed.length ? res.removed.join(', ') : 'our settings entries'}`);
    out.push(`  ${RESTART_LINE}`);
    return out;
  }
  if (res.action === 'status') {
    out.push(`Mods: Claude Code ${res.version || 'not found'}${res.gated ? ` (needs ${MIN_VERSION}+, sync would be skipped)` : ''}`);
    out.push(`  wired by us: ${res.owned.length ? res.owned.join(', ') : 'none'}`);
    if (res.added.length) out.push(`  would wire: ${res.added.join(', ')}`);
    if (res.pruned.length) out.push(`  would remove: ${res.pruned.join(', ')}`);
    return out.concat(skippedLines(res));
  }
  if (res.status === 'unchanged') {
    out.push(`Mods: up to date (${res.kept.length} wired)`);
    return out.concat(skippedLines(res));
  }
  const parts = [];
  if (res.added.length) parts.push(`wired ${res.added.join(', ')}`);
  const refreshed = res.copied.filter(n => !res.added.includes(n));
  if (refreshed.length) parts.push(`refreshed ${refreshed.join(', ')}`);
  if (res.pruned.length) parts.push(`removed ${res.pruned.join(', ')}`);
  out.push(`Mods: ${parts.length ? parts.join('; ') : 'updated'}`);
  out.push(...skippedLines(res));
  out.push(`  ${RESTART_LINE}`);
  return out;
}

// For installers, `agency init` and `agency upgrade`: honours AGENCY_NO_MODS,
// never throws (wiring must never fail the install/upgrade), prints the lines and
// returns the result.
function autoSyncMods({ root, repoDir, console = global.console, indent = '' } = {}) {
  let res;
  try {
    res = syncMods({ root, repoDir, auto: true });
  } catch (e) {
    let base;
    try { base = baseResult('sync', makeCtx({ root, repoDir })); } catch (_) { base = { action: 'sync', skipped: [], added: [], kept: [], pruned: [], copied: [] }; }
    res = Object.assign(base, { status: 'error', reason: 'write-failed', error: e.message });
  }
  try {
    for (const line of formatResult(res)) console.log(indent + line);
  } catch (_) {}
  return res;
}

// ---------------------------------------------------------------------------
// CLI

function parseArgs(argv) {
  const out = { cmd: argv[0], flags: {} };
  for (let i = 1; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json' || a === '--auto') out.flags[a.slice(2)] = true;
    else if (a === '--root' || a === '--repo') out.flags[a.slice(2)] = argv[++i];
    else if (/^--(root|repo)=/.test(a)) {
      const eq = a.indexOf('=');
      out.flags[a.slice(2, eq)] = a.slice(eq + 1);
    } else out.bad = a;
  }
  return out;
}

function runCli(argv, console = global.console) {
  const { cmd, flags, bad } = parseArgs(argv);
  if (!['sync', 'remove', 'status'].includes(cmd) || bad) {
    console.error(USAGE);
    return 2;
  }
  const opts = { root: flags.root, repoDir: flags.repo, auto: !!flags.auto };
  const res = cmd === 'sync' ? syncMods(opts) : cmd === 'remove' ? removeMods(opts) : statusMods(opts);
  if (flags.json) console.log(JSON.stringify(res, null, 2));
  else for (const line of formatResult(res)) console.log(line);
  return res.status === 'error' ? 1 : 0;
}

module.exports = {
  MIN_VERSION,
  USAGE,
  syncMods,
  removeMods,
  statusMods,
  autoSyncMods,
  formatResult,
  runCli,
  splitValue,
};

if (require.main === module) {
  process.exitCode = runCli(process.argv.slice(2));
}
