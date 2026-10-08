#!/usr/bin/env node
'use strict';

// hooks-merge.js — wire hooks/hooks.json into <root>/settings.json without
// touching anything the user owns.
//
// Why this exists: install.sh used to wire hooks ONLY when settings.json did not
// exist yet, and `agency upgrade` synced hook files but never wired them. Every
// user who already had Claude Code (i.e. almost everyone) ran zero agency hooks.
//
// Callers: install.sh, install.ps1, `agency init`, `agency upgrade`, and
// `agency hooks sync|remove`. Shell callers use the CLI form:
//   node cli/lib/hooks-merge.js sync|remove [--root <root>] [--manifest <file>]
//                                           [--auto] [--force] [--json]
//   --auto   called by an installer/upgrade: honour AGENCY_NO_HOOKS=1
//   --force  wire even on Windows when `bash` (Git Bash) is not on PATH
//
// Ownership (what counts as OURS — everything else is the user's and is never
// edited, moved or reordered):
//   an entry is ours iff its command, with the root spelled as `{root}`, equals
//     - a command in the current manifest, or
//     - a command in the manifest's `retired` list, or
//     - a command recorded in <root>/hooks/.agency-hooks-state.json (what we
//       wired last time).
//   A directory test ("any script under <root>/hooks/") is deliberately NOT
//   used: users keep personal scripts there (wired by hand) that a prune by
//   directory would silently delete.
//   Root spellings recognised: the resolved root, with forward or back slashes,
//   the MSYS form (/c/Users/...), and — only when root is <home>/.claude —
//   `~/.claude`, `$HOME/.claude`, `${HOME}/.claude`. A working `~/.claude` entry
//   is never rewritten into an absolute path.
//
// Safety: a timestamped copy settings.json.bak-YYYYMMDD-HHMMSS is written NEXT
// TO settings.json before any change (it travels with the root it belongs to,
// custom roots never collide, restore is one cp); the write itself is a temp
// file in the same directory + rename. No change => no write, no backup.
// Malformed settings.json => nothing is written; the caller prints the manual
// command.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { timestamp } = require('./git-recover.js');

const REPO_DIR = path.resolve(__dirname, '..', '..');
const DEFAULT_MANIFEST = path.join(REPO_DIR, 'hooks', 'hooks.json');
const STATE_NAME = '.agency-hooks-state.json';
const RESTART_LINE = 'Restart Claude Code to activate the hooks.';

// ---------------------------------------------------------------------------
// paths and command forms

function fwd(p) {
  return String(p).replace(/\\/g, '/').replace(/(.)\/+$/, '$1');
}

function isWinish(root, platform) {
  return platform === 'win32' || /^[A-Za-z]:[\\/]/.test(root) || String(root).includes('\\');
}

// Same ladder as hooks/lib/resolve-root.sh, cli/bin/agency.js, install.sh and
// install.ps1: AGENCY_HOME || CLAUDE_CONFIG_DIR || <home>/.claude.
function resolveRoot(root, { env = process.env, home = os.homedir(), platform = process.platform } = {}) {
  let r = root || env.AGENCY_HOME || env.CLAUDE_CONFIG_DIR || path.join(home, '.claude');
  // Git Bash hands node an MSYS path (/c/Users/me/.claude); native Windows node
  // cannot open that, so turn it into C:/Users/me/.claude.
  if (platform === 'win32') {
    const m = r.match(/^\/([A-Za-z])(\/.*)?$/);
    if (m) r = `${m[1].toUpperCase()}:${m[2] || '/'}`;
  }
  if (platform === process.platform && !path.isAbsolute(r)) r = path.resolve(r);
  return r;
}

// Characters that are safe unquoted in a shell word. Anything else in the root
// (a space in "C:/Users/John Smith", parentheses, ...) gets each path quoted.
const SAFE_ROOT = /^[A-Za-z0-9_.\/:~+@%,=-]+$/;

function renderCommand(template, root) {
  const r = fwd(root);
  const quote = !SAFE_ROOT.test(r);
  return String(template).replace(/\{root\}([^\s"';&|<>()]*)/g, (_, rest) =>
    quote ? `"${r}${rest}"` : `${r}${rest}`);
}

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function normaliseCommand(cmd, { root, home = os.homedir(), platform = process.platform }) {
  let c = String(cmd == null ? '' : cmd);
  const winish = isWinish(root, platform);
  if (winish) c = c.replace(/\\/g, '/');
  const r = fwd(root);
  const forms = new Set([r]);
  if (winish) {
    const m = r.match(/^([A-Za-z]):(\/.*)$/);
    if (m) forms.add(`/${m[1].toLowerCase()}${m[2]}`);
  }
  const homeRoot = fwd(`${fwd(home)}/.claude`);
  if (winish ? homeRoot.toLowerCase() === r.toLowerCase() : homeRoot === r) {
    forms.add('~/.claude');
    forms.add('$HOME/.claude');
    forms.add('${HOME}/.claude');
  }
  const sorted = [...forms].sort((a, b) => b.length - a.length);
  for (const form of sorted) {
    c = c.replace(new RegExp(escapeRe(form) + '(?=/)', winish ? 'gi' : 'g'), '{root}');
  }
  c = c.replace(/(["'])(\{root\}[^"'\s]*)\1/g, '$2');
  return c.trim().replace(/\s+/g, ' ');
}

// ---------------------------------------------------------------------------
// manifest, state, settings

function loadManifest(manifestPath = DEFAULT_MANIFEST) {
  const m = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (!m || !Array.isArray(m.hooks)) throw new Error(`${manifestPath}: "hooks" must be an array`);
  const ids = new Set();
  for (const h of m.hooks) {
    for (const k of ['id', 'event', 'command', 'purpose']) {
      if (typeof h[k] !== 'string' || !h[k]) throw new Error(`${manifestPath}: hook ${JSON.stringify(h.id)} needs a non-empty "${k}"`);
    }
    if (typeof h.matcher !== 'string') throw new Error(`${manifestPath}: hook ${h.id} needs a "matcher" string ("" = all)`);
    if (ids.has(h.id)) throw new Error(`${manifestPath}: duplicate id ${h.id}`);
    ids.add(h.id);
  }
  m.retired = Array.isArray(m.retired) ? m.retired : [];
  return m;
}

function statePath(root) {
  return path.join(root, 'hooks', STATE_NAME);
}

function readState(root) {
  try {
    const s = JSON.parse(fs.readFileSync(statePath(root), 'utf8'));
    if (s && typeof s.hooks === 'object' && !Array.isArray(s.hooks)) return s;
  } catch (_) {}
  return { version: 1, hooks: {} };
}

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function readSettings(settingsPath) {
  if (!fs.existsSync(settingsPath)) return { exists: false, raw: null, data: {}, indent: '  ' };
  const raw = fs.readFileSync(settingsPath, 'utf8');
  let data;
  if (raw.trim() === '') {
    data = {};
  } else {
    try {
      data = JSON.parse(raw.replace(/^\uFEFF/, ''));
    } catch (e) {
      return { exists: true, raw, error: `not valid JSON (${e.message})` };
    }
  }
  if (!isPlainObject(data)) return { exists: true, raw, error: 'top level is not a JSON object' };
  if (data.hooks !== undefined) {
    if (!isPlainObject(data.hooks)) return { exists: true, raw, error: '"hooks" is not an object' };
    for (const [event, groups] of Object.entries(data.hooks)) {
      if (!Array.isArray(groups)) return { exists: true, raw, error: `"hooks.${event}" is not an array` };
      for (let i = 0; i < groups.length; i++) {
        const g = groups[i];
        if (!isPlainObject(g) || !Array.isArray(g.hooks)) {
          return { exists: true, raw, error: `"hooks.${event}[${i}]" is not a {matcher, hooks: [...]} group` };
        }
      }
    }
  }
  const m = raw.match(/^\{\r?\n([ \t]+)\S/);
  return { exists: true, raw, data, indent: m ? m[1] : '  ' };
}

function atomicWrite(target, text) {
  let real = target;
  try {
    if (fs.lstatSync(target).isSymbolicLink()) real = fs.realpathSync(target);
  } catch (_) {}
  const dir = path.dirname(real);
  fs.mkdirSync(dir, { recursive: true });
  let mode;
  try { mode = fs.statSync(real).mode & 0o777; } catch (_) {}
  const tmp = path.join(dir, `.${path.basename(real)}.agency-tmp-${process.pid}-${Date.now()}`);
  try {
    fs.writeFileSync(tmp, text, { mode: mode === undefined ? 0o644 : mode });
    if (mode !== undefined) fs.chmodSync(tmp, mode);
    fs.renameSync(tmp, real);
  } catch (e) {
    try { fs.unlinkSync(tmp); } catch (_) {}
    throw e;
  }
}

function writeBackup(settingsPath, raw, now) {
  const base = `${settingsPath}.bak-${timestamp(now)}`;
  let p = base;
  for (let n = 2; fs.existsSync(p); n++) p = `${base}-${n}`;
  // Same permissions as the original: settings.json can hold MCP tokens, and
  // a 0600 file must not leave a world-readable copy beside it.
  let mode = 0o600;
  try { mode = fs.statSync(settingsPath).mode & 0o777; } catch (_) {}
  fs.writeFileSync(p, raw, { mode });
  try { fs.chmodSync(p, mode); } catch (_) {}
  return p;
}

// ---------------------------------------------------------------------------
// planning (pure: mutates the settings object it is given)

function makeCtx(opts) {
  const platform = opts.platform || process.platform;
  const env = opts.env || process.env;
  const home = opts.home || os.homedir();
  const root = resolveRoot(opts.root, { env, home, platform });
  return { platform, env, home, root };
}

function ownedMap(manifest, state) {
  const owned = new Map();
  for (const r of manifest.retired) if (r && r.command) owned.set(r.command, { id: r.id || r.command, retired: true });
  for (const [id, s] of Object.entries(state.hooks || {})) if (s && s.command) owned.set(s.command, { id });
  for (const h of manifest.hooks) owned.set(h.command, h);
  return owned;
}

function removeEntry(group, entry, touched) {
  const i = group.hooks.indexOf(entry);
  if (i >= 0) group.hooks.splice(i, 1);
  touched.add(group);
}

// Drop groups and events that WE emptied. A group the user left empty is theirs.
function cleanup(data, touched, dropEmptyHooks) {
  if (!isPlainObject(data.hooks)) return;
  for (const event of Object.keys(data.hooks)) {
    const groups = data.hooks[event];
    const before = groups.length;
    data.hooks[event] = groups.filter(g => !(touched.has(g) && g.hooks.length === 0));
    if (before > 0 && data.hooks[event].length === 0) delete data.hooks[event];
  }
  if (dropEmptyHooks && Object.keys(data.hooks).length === 0 && touched.size > 0) delete data.hooks;
}

function planSync(data, manifest, state, ctx) {
  const norm = c => normaliseCommand(c, ctx);
  const current = new Map(manifest.hooks.map(h => [h.command, h]));
  const owned = ownedMap(manifest, state);
  const isOurs = c => owned.has(norm(c));
  const touched = new Set();
  const added = [];
  const updated = [];
  const removed = [];

  const groupsOf = event => (isPlainObject(data.hooks) && Array.isArray(data.hooks[event])) ? data.hooks[event] : [];
  const findIn = (event, cmd, except) => {
    for (const g of groupsOf(event)) for (const e of g.hooks) {
      if (e !== except && isPlainObject(e) && norm(e.command) === cmd) return { g, e };
    }
    return null;
  };
  const place = h => {
    if (!isPlainObject(data.hooks)) data.hooks = {};
    if (!Array.isArray(data.hooks[h.event])) data.hooks[h.event] = [];
    const groups = data.hooks[h.event];
    const entry = { type: 'command', command: renderCommand(h.command, ctx.root) };
    const target = groups.find(g => (g.matcher || '') === h.matcher && g.hooks.length > 0 &&
      g.hooks.every(e => isPlainObject(e) && isOurs(e.command)));
    if (target) target.hooks.push(entry);
    else groups.push({ matcher: h.matcher, hooks: [entry] });
  };

  // 1. updates: the manifest changed an entry we wired last time
  for (const h of manifest.hooks) {
    const prev = (state.hooks || {})[h.id];
    if (!prev || (prev.command === h.command && prev.matcher === h.matcher && prev.event === h.event)) continue;
    let found = null;
    for (const g of groupsOf(prev.event)) {
      if ((g.matcher || '') !== prev.matcher) continue;
      for (const e of g.hooks) if (isPlainObject(e) && norm(e.command) === prev.command) { found = { g, e }; break; }
      if (found) break;
    }
    if (!found) continue; // the user moved or deleted it: step 3 decides
    const newPresent = findIn(h.event, h.command, found.e);
    let change;
    if (prev.event === h.event && prev.matcher === h.matcher) {
      if (newPresent) removeEntry(found.g, found.e, touched);
      else found.e.command = renderCommand(h.command, ctx.root);
      change = 'command changed';
    } else {
      removeEntry(found.g, found.e, touched);
      if (!newPresent) place(h);
      change = prev.event === h.event
        ? `matcher "${prev.matcher}" -> "${h.matcher}"`
        : `event ${prev.event} -> ${h.event}`;
    }
    updated.push({ id: h.id, event: h.event, matcher: h.matcher, purpose: h.purpose, change });
  }

  // 2. prune: ours, but no longer shipped
  if (isPlainObject(data.hooks)) {
    for (const [event, groups] of Object.entries(data.hooks)) {
      for (const g of groups) {
        for (const e of g.hooks.slice()) {
          if (!isPlainObject(e)) continue;
          const n = norm(e.command);
          if (owned.has(n) && !current.has(n)) {
            removeEntry(g, e, touched);
            const id = owned.get(n).id;
            if (!removed.some(r => r.id === id)) removed.push({ id, event, matcher: g.matcher || '' });
          }
        }
      }
    }
  }

  // 3. add: shipped, not present in any equivalent form in that event
  for (const h of manifest.hooks) {
    if (findIn(h.event, h.command)) continue;
    if (updated.some(u => u.id === h.id)) continue;
    place(h);
    added.push({ id: h.id, event: h.event, matcher: h.matcher, purpose: h.purpose });
  }

  cleanup(data, touched, false);

  const newState = { version: 1, hooks: {} };
  let wired = 0;
  for (const h of manifest.hooks) {
    if (findIn(h.event, h.command)) {
      wired++;
      newState.hooks[h.id] = { event: h.event, matcher: h.matcher, command: h.command };
    }
  }
  return { added, updated, removed, newState, wired };
}

function planRemove(data, manifest, state, ctx) {
  const norm = c => normaliseCommand(c, ctx);
  const owned = ownedMap(manifest, state);
  const touched = new Set();
  const removed = [];
  if (isPlainObject(data.hooks)) {
    for (const [event, groups] of Object.entries(data.hooks)) {
      for (const g of groups) {
        for (const e of g.hooks.slice()) {
          if (!isPlainObject(e)) continue;
          const n = norm(e.command);
          if (!owned.has(n)) continue;
          removeEntry(g, e, touched);
          const id = owned.get(n).id;
          if (!removed.some(r => r.id === id)) removed.push({ id, event, matcher: g.matcher || '' });
        }
      }
    }
  }
  cleanup(data, touched, true);
  return { removed };
}

// ---------------------------------------------------------------------------
// commit

// Fixed argv, no shell string: nothing user-controlled reaches the process.
function defaultBashAvailable() {
  try {
    return spawnSync('bash', ['-c', 'exit 0'], { stdio: 'ignore' }).status === 0;
  } catch (_) {
    return false;
  }
}

function baseResult(action, ctx, opts) {
  return {
    action,
    status: null,
    reason: null,
    error: null,
    root: ctx.root,
    settingsPath: path.join(ctx.root, 'settings.json'),
    repoDir: opts.repoDir || REPO_DIR,
    created: false,
    backup: null,
    added: [],
    updated: [],
    removed: [],
    wired: 0,
  };
}

function commitSettings(res, settings, data, opts) {
  const text = JSON.stringify(data, null, settings.indent) + '\n';
  if (settings.exists && text === settings.raw) return false;
  if (settings.exists) res.backup = writeBackup(res.settingsPath, settings.raw, opts.now);
  atomicWrite(res.settingsPath, text);
  res.created = !settings.exists;
  return true;
}

function syncHooks(opts = {}) {
  const ctx = makeCtx(opts);
  const res = baseResult('sync', ctx, opts);
  const optOut = ctx.env.AGENCY_NO_HOOKS && ctx.env.AGENCY_NO_HOOKS !== '0';
  if (opts.auto && optOut) return Object.assign(res, { status: 'skipped', reason: 'opt-out' });
  const manifestPath = opts.manifestPath || DEFAULT_MANIFEST;
  let manifest;
  try {
    manifest = loadManifest(manifestPath);
  } catch (e) {
    return Object.assign(res, { status: fs.existsSync(manifestPath) ? 'error' : 'skipped', reason: 'no-manifest', error: e.message });
  }
  if (ctx.platform === 'win32' && !opts.force && !(opts.bashAvailable || defaultBashAvailable)()) {
    return Object.assign(res, { status: 'skipped', reason: 'no-bash' });
  }
  const settings = readSettings(res.settingsPath);
  if (settings.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath} is ${settings.error}` });
  const state = readState(ctx.root);
  const plan = planSync(settings.data, manifest, state, ctx);
  Object.assign(res, { added: plan.added, updated: plan.updated, removed: plan.removed, wired: plan.wired });
  const changed = plan.added.length + plan.updated.length + plan.removed.length > 0;
  try {
    if (changed) commitSettings(res, settings, settings.data, opts);
    // State follows settings.json: rewritten only when it is missing or stale,
    // so a no-op run stays a no-op on disk.
    const stateText = JSON.stringify(plan.newState, null, 2) + '\n';
    let stateOld = null;
    try { stateOld = fs.readFileSync(statePath(ctx.root), 'utf8'); } catch (_) {}
    if (stateOld !== stateText) atomicWrite(statePath(ctx.root), stateText);
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'write-failed', error: e.message });
  }
  res.status = changed ? 'changed' : 'unchanged';
  return res;
}

function removeHooks(opts = {}) {
  const ctx = makeCtx(opts);
  const res = baseResult('remove', ctx, opts);
  const manifestPath = opts.manifestPath || DEFAULT_MANIFEST;
  let manifest;
  try {
    manifest = loadManifest(manifestPath);
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'no-manifest', error: e.message });
  }
  const settings = readSettings(res.settingsPath);
  if (settings.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath} is ${settings.error}` });
  const state = readState(ctx.root);
  const plan = planRemove(settings.data, manifest, state, ctx);
  res.removed = plan.removed;
  try {
    if (plan.removed.length > 0 && settings.exists) commitSettings(res, settings, settings.data, opts);
    if (fs.existsSync(statePath(ctx.root))) fs.unlinkSync(statePath(ctx.root));
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'write-failed', error: e.message });
  }
  res.status = plan.removed.length > 0 ? 'changed' : 'unchanged';
  return res;
}

// ---------------------------------------------------------------------------
// messages

function manualCommands(repoDir, root) {
  return [
    'agency hooks sync',
    `node "${path.join(repoDir, 'cli', 'lib', 'hooks-merge.js')}" sync --root "${root}"`,
  ];
}

const REASONS = {
  'opt-out': 'AGENCY_NO_HOOKS=1 is set',
  'no-bash': '`bash` (Git Bash) was not found on PATH, and Claude Code runs these hooks with bash',
  'no-manifest': 'hooks/hooks.json is missing from the repo',
};

function pad(s, n) {
  s = String(s);
  return s.length >= n ? s + ' ' : s + ' '.repeat(n - s.length);
}

function where(event, matcher) {
  return matcher ? `${event} [${matcher}]` : event;
}

function formatResult(res) {
  const out = [];
  const file = res.settingsPath;
  if (res.status === 'skipped' || res.status === 'error') {
    const why = res.status === 'error' ? res.error : (REASONS[res.reason] || res.reason);
    if (res.action === 'remove') {
      out.push(`Hooks: NOT removed: ${why}. Nothing was changed.`);
      return out;
    }
    out.push(`Hooks: NOT wired: ${why}.${res.status === 'error' ? ' Nothing was changed.' : ''}`);
    const [a, b] = manualCommands(res.repoDir, res.root);
    out.push(res.reason === 'malformed' ? '  Fix the file, then set the hooks up with:' : '  To set them up, run:');
    out.push(`    ${a}`);
    out.push('  or, without the agency command:');
    out.push(`    ${b}`);
    if (res.reason === 'no-bash') out.push('  (install Git for Windows first, or add --force to wire them anyway)');
    out.push(`  Then: ${RESTART_LINE}`);
    return out;
  }
  if (res.action === 'remove') {
    if (res.status === 'unchanged') {
      out.push(`Hooks: no agency hooks wired in ${file}; nothing to remove`);
      return out;
    }
    out.push(`Hooks: removed ${res.removed.length} agency hook entr${res.removed.length === 1 ? 'y' : 'ies'} from ${file}`);
    for (const r of res.removed) out.push(`  - ${pad(r.id, 24)}${where(r.event, r.matcher)}`);
    if (res.backup) out.push(`  Backup of the previous file: ${res.backup}`);
    out.push(`  Your own hooks and settings were left as they were. Hook scripts stay in ${path.join(res.root, 'hooks')}.`);
    out.push('  Restart Claude Code to apply the change. Re-wire any time with: agency hooks sync');
    return out;
  }
  if (res.status === 'unchanged') {
    out.push(`Hooks: ${res.wired} wired, up to date`);
    return out;
  }
  out.push(res.created
    ? `Hooks: created ${file} with ${res.wired} hooks wired`
    : `Hooks: ${res.added.length} added, ${res.updated.length} updated, ${res.removed.length} removed in ${file}`);
  for (const a of res.added) out.push(`  + ${pad(a.id, 24)}${pad(where(a.event, a.matcher), 26)}${a.purpose}`);
  for (const u of res.updated) out.push(`  ~ ${pad(u.id, 24)}${pad(where(u.event, u.matcher), 26)}${u.purpose} (updated: ${u.change})`);
  for (const r of res.removed) out.push(`  - ${pad(r.id, 24)}${pad(r.event, 26)}removed: no longer shipped`);
  if (res.backup) out.push(`  Backup of the previous file: ${res.backup}`);
  if (!res.created) out.push('  Your own hooks and settings were left as they were.');
  out.push(`  ${RESTART_LINE}`);
  return out;
}

// For installers, `agency init` and `agency upgrade`: honours AGENCY_NO_HOOKS,
// never throws (wiring must never fail the install/upgrade), prints the block
// and returns the result so the caller can repeat the restart line at the end.
function autoSync({ root, repoDir, console = global.console, indent = '' }) {
  let res;
  try {
    res = syncHooks({ root, repoDir, manifestPath: path.join(repoDir, 'hooks', 'hooks.json'), auto: true });
  } catch (e) {
    res = Object.assign(baseResult('sync', makeCtx({ root }), { repoDir }), {
      status: 'error', reason: 'write-failed', error: e.message,
    });
  }
  for (const line of formatResult(res)) console.log(indent + line);
  return res;
}

// ---------------------------------------------------------------------------
// CLI

function parseArgs(argv) {
  const out = { cmd: argv[0], flags: {} };
  for (let i = 1; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json' || a === '--auto' || a === '--force') out.flags[a.slice(2)] = true;
    else if (a === '--root' || a === '--manifest' || a === '--repo') out.flags[a.slice(2)] = argv[++i];
    else if (/^--(root|manifest|repo)=/.test(a)) {
      const eq = a.indexOf('=');
      out.flags[a.slice(2, eq)] = a.slice(eq + 1);
    } else {
      out.bad = a;
    }
  }
  return out;
}

const USAGE = 'Usage: node cli/lib/hooks-merge.js sync|remove [--root <dir>] [--manifest <file>] [--auto] [--force] [--json]';

function runCli(argv, console = global.console) {
  const { cmd, flags, bad } = parseArgs(argv);
  if ((cmd !== 'sync' && cmd !== 'remove') || bad) {
    console.error(USAGE);
    return 2;
  }
  const opts = {
    root: flags.root,
    manifestPath: flags.manifest,
    repoDir: flags.repo,
    auto: !!flags.auto,
    force: !!flags.force,
  };
  const res = cmd === 'sync' ? syncHooks(opts) : removeHooks(opts);
  if (flags.json) console.log(JSON.stringify(res, null, 2));
  else for (const line of formatResult(res)) console.log(line);
  return res.status === 'error' ? 1 : 0;
}

module.exports = {
  DEFAULT_MANIFEST,
  STATE_NAME,
  RESTART_LINE,
  USAGE,
  resolveRoot,
  renderCommand,
  normaliseCommand,
  loadManifest,
  readSettings,
  planSync,
  planRemove,
  syncHooks,
  removeHooks,
  formatResult,
  manualCommands,
  autoSync,
  runCli,
};

if (require.main === module) {
  process.exitCode = runCli(process.argv.slice(2));
}
