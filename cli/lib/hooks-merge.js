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
//   node cli/lib/hooks-merge.js sync|remove|disable <id>|enable <id> [--root <root>] [--manifest <file>]
//                                           [--auto] [--force] [--json]
//   --auto   called by an installer/upgrade: honour AGENCY_NO_HOOKS=1
//   --force  wire even on Windows when Git Bash (bash.exe) cannot be found
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
// Opt-out: an id the state file records as wired, whose entry is then gone from
// settings.json under both its recorded and its current command, was removed by
// the user. It is moved to state.disabled, never re-added, and reported
// ("skipped <id> (you removed it; agency hooks enable <id> to restore)") on
// every sync. `disable <id>` does the same on purpose; `enable <id>` undoes it.
// With no state file (first-ever install) nothing is treated as deleted.
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
const GIT_FOR_WINDOWS_URL = 'https://git-scm.com/downloads/win';

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
    if (s && typeof s.hooks === 'object' && !Array.isArray(s.hooks)) {
      if (!isPlainObject(s.disabled)) s.disabled = {};
      return s;
    }
  } catch (_) {}
  return { version: 1, hooks: {}, disabled: {} };
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
  // Opt-outs: ids the user removed (or `agency hooks disable`d). id -> {event, matcher, command}
  const disabled = Object.assign({}, state.disabled || {});
  const newlyDisabled = new Set();

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

  // 0. opt-out: an id we wired last time (recorded in state) whose entry is now
  // gone from settings.json under BOTH its recorded and its current command was
  // removed by the user. Mark it disabled instead of putting it back. A changed
  // command whose old form is still present is an update (step 1), not this.
  // No state (first-ever install) means nothing is ever treated as deleted.
  for (const h of manifest.hooks) {
    if (disabled[h.id]) {
      // wired by hand again: the opt-out is over
      if (findIn(h.event, h.command)) delete disabled[h.id];
      continue;
    }
    const prev = (state.hooks || {})[h.id];
    if (!prev) continue;
    if (findIn(h.event, h.command) || findIn(prev.event, prev.command)) continue;
    disabled[h.id] = { event: prev.event, matcher: prev.matcher, command: prev.command };
    newlyDisabled.add(h.id);
  }

  // 1. updates: the manifest changed an entry we wired last time
  for (const h of manifest.hooks) {
    if (disabled[h.id]) continue;
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
    if (disabled[h.id]) continue;
    if (findIn(h.event, h.command)) continue;
    if (updated.some(u => u.id === h.id)) continue;
    place(h);
    added.push({ id: h.id, event: h.event, matcher: h.matcher, purpose: h.purpose });
  }

  cleanup(data, touched, false);

  const newState = { version: 1, hooks: {} };
  const skipped = [];
  let wired = 0;
  for (const h of manifest.hooks) {
    if (disabled[h.id]) {
      // kept only while the manifest still ships the id
      newState.disabled = newState.disabled || {};
      newState.disabled[h.id] = disabled[h.id];
      skipped.push({ id: h.id, event: h.event, matcher: h.matcher, newly: newlyDisabled.has(h.id) });
    } else if (findIn(h.event, h.command)) {
      wired++;
      newState.hooks[h.id] = { event: h.event, matcher: h.matcher, command: h.command };
    }
  }
  return { added, updated, removed, newState, wired, skipped };
}

// `agency hooks disable <id>`: take our entry for <id> out of settings.json and
// record the opt-out, so sync/upgrade/install never put it back.
function planDisable(data, manifest, state, ctx, id) {
  const norm = c => normaliseCommand(c, ctx);
  const h = manifest.hooks.find(x => x.id === id);
  const cmds = new Set([h.command]);
  const prev = (state.hooks || {})[id];
  if (prev && prev.command) cmds.add(prev.command);
  const touched = new Set();
  let removedEntries = 0;
  if (isPlainObject(data.hooks)) {
    for (const groups of Object.values(data.hooks)) {
      for (const g of groups) {
        for (const e of g.hooks.slice()) {
          if (!isPlainObject(e) || !cmds.has(norm(e.command))) continue;
          removeEntry(g, e, touched);
          removedEntries++;
        }
      }
    }
  }
  cleanup(data, touched, false);
  return { removedEntries, entry: { event: prev ? prev.event : h.event, matcher: prev ? prev.matcher : h.matcher, command: h.command } };
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

// ---------------------------------------------------------------------------
// Git Bash resolver (Windows)
//
// Claude Code runs a command hook inside Git Bash when Git for Windows is
// installed (docs: hooks `shell` defaults to "bash", or to "powershell" on
// Windows when Git Bash is not installed), so the hook commands stay
// `bash {root}/hooks/x.sh`. Whether wiring them makes sense depends on Git
// Bash existing, and the PowerShell PATH that install.ps1 runs with often does
// not contain it. So look for bash.exe the way Claude Code does instead of
// asking the current shell.
//
// Order (first hit wins):
//   1. env CLAUDE_CODE_GIT_BASH_PATH, if that file exists
//   2. `git --exec-path`: C:/Program Files/Git/mingw64/libexec/git-core, so
//      Git\bin\bash.exe is THREE levels up. Levels 2, 3 and 4 are checked
//      (mingw64\bin, Git\bin, <parent>\bin). MSYS-style output
//      (/mingw64/...) cannot be resolved from node and is skipped.
//   3. %ProgramFiles%\Git\bin\bash.exe
//   4. %LOCALAPPDATA%\Programs\Git\bin\bash.exe
//   5. a bash.exe on PATH, EXCEPT %WINDIR%\System32\bash.exe and anything
//      under \WindowsApps\: those are the WSL launcher and would run the
//      hooks inside WSL, not Git Bash.
// Dependency-injected (env, exists, gitExecPath, pathLookup) so it is testable
// on any OS. Paths are always handled with path.win32.

const W = path.win32;

function envGet(env, name) {
  if (env[name] !== undefined) return env[name];
  const k = Object.keys(env).find(x => x.toLowerCase() === name.toLowerCase());
  return k === undefined ? undefined : env[k];
}

// Fixed argv, no shell string: nothing user-controlled reaches the process.
function defaultGitExecPath() {
  try {
    const r = spawnSync('git', ['--exec-path'], { encoding: 'utf8' });
    return r.status === 0 ? String(r.stdout).trim() : null;
  } catch (_) {
    return null;
  }
}

function defaultPathLookup({ env, exists }) {
  const raw = envGet(env, 'PATH') || '';
  const out = [];
  for (const dir of raw.split(';')) {
    const d = dir.trim().replace(/^"|"$/g, '');
    if (!d) continue;
    const cand = W.join(d, 'bash.exe');
    if (exists(cand)) out.push(cand);
  }
  return out;
}

function isWslLauncher(p, env) {
  const n = W.normalize(p).toLowerCase();
  if (n.includes('\\windowsapps\\')) return true;
  const winDir = envGet(env, 'WINDIR') || envGet(env, 'SystemRoot') || 'C:\\Windows';
  const win = W.normalize(winDir).toLowerCase().replace(/\\+$/, '');
  return n === `${win}\\system32\\bash.exe` || n === `${win}\\sysnative\\bash.exe` ||
    /\\system32\\bash\.exe$/.test(n) || /\\sysnative\\bash\.exe$/.test(n);
}

// -> { found: {path, source, standard} | null, notes: [string] }
function locateGitBash(deps = {}) {
  const env = deps.env || process.env;
  const exists = deps.exists || (p => { try { return fs.existsSync(p); } catch (_) { return false; } });
  const gitExecPath = deps.gitExecPath || defaultGitExecPath;
  const pathLookup = deps.pathLookup || defaultPathLookup;
  const notes = [];
  const hit = (p, source, standard) => ({ found: { path: p, source, standard: !!standard }, notes });

  // 1. explicit override
  const forced = envGet(env, 'CLAUDE_CODE_GIT_BASH_PATH');
  if (forced) {
    if (exists(forced)) return hit(forced, 'env', true);
    notes.push(`CLAUDE_CODE_GIT_BASH_PATH is set to ${forced}, but that file does not exist; looking elsewhere`);
  }
  // 2. git --exec-path
  let ep = null;
  try { ep = gitExecPath(); } catch (_) {}
  if (ep && /^[A-Za-z]:[\\/]/.test(ep)) {
    let dir = W.normalize(ep).replace(/[\\]+$/, '');
    for (let up = 1; up <= 4; up++) {
      dir = W.dirname(dir);
      if (up < 2) continue;
      const cand = W.join(dir, 'bin', 'bash.exe');
      if (exists(cand)) return hit(cand, 'git-exec-path', false);
    }
  }
  // 3. %ProgramFiles%\Git\bin\bash.exe
  const pf = envGet(env, 'ProgramFiles');
  if (pf) {
    const cand = W.join(pf, 'Git', 'bin', 'bash.exe');
    if (exists(cand)) return hit(cand, 'program-files', true);
  }
  // 4. %LOCALAPPDATA%\Programs\Git\bin\bash.exe
  const la = envGet(env, 'LOCALAPPDATA');
  if (la) {
    const cand = W.join(la, 'Programs', 'Git', 'bin', 'bash.exe');
    if (exists(cand)) return hit(cand, 'local-appdata', true);
  }
  // 5. PATH, never the WSL launcher
  let onPath = [];
  try { onPath = pathLookup({ env, exists }) || []; } catch (_) {}
  for (const cand of onPath) {
    if (!isWslLauncher(cand, env)) return hit(cand, 'path', false);
  }
  return { found: null, notes };
}

// -> { path, source } | null
function resolveGitBash(deps = {}) {
  const { found } = locateGitBash(deps);
  return found ? { path: found.path, source: found.source } : null;
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
    skipped: [],
    notes: [],
    bash: null,
    bashHint: false,
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

// State follows settings.json: rewritten only when it is missing or stale, so a
// no-op run stays a no-op on disk.
function writeStateIfChanged(root, newState) {
  const stateText = JSON.stringify(newState, null, 2) + '\n';
  let stateOld = null;
  try { stateOld = fs.readFileSync(statePath(root), 'utf8'); } catch (_) {}
  if (stateOld !== stateText) atomicWrite(statePath(root), stateText);
}

// Unknown or retired id for enable/disable -> an error result that lists the valid ids.
function badHookId(res, manifest, id) {
  const valid = manifest.hooks.map(h => h.id);
  const isRetired = manifest.retired.some(r => r && r.id === id);
  const what = isRetired ? `"${id}" is retired (no longer shipped), so it cannot be ${res.action}d`
    : `unknown hook id ${JSON.stringify(id == null ? '' : id)}`;
  return Object.assign(res, {
    status: 'error',
    reason: 'unknown-id',
    error: `${what}. Valid ids: ${valid.join(', ')}`,
  });
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
  if (opts.enable !== undefined) {
    res.action = 'enable';
    if (!manifest.hooks.some(h => h.id === opts.enable)) return badHookId(res, manifest, opts.enable);
  }
  if (ctx.platform === 'win32' && !opts.force) {
    let bash = null;
    if (opts.bashAvailable) {
      // Caller-supplied check: a boolean, or a {path, source} like the resolver's.
      const v = opts.bashAvailable();
      bash = v && typeof v === 'object' ? { path: v.path, source: v.source, standard: true } : (v ? { path: null, source: 'override', standard: true } : null);
    } else {
      const loc = locateGitBash(Object.assign({ env: ctx.env }, opts.bashDeps || {}));
      res.notes = loc.notes;
      bash = loc.found;
    }
    if (!bash) return Object.assign(res, { status: 'skipped', reason: 'no-bash' });
    res.bash = { path: bash.path, source: bash.source };
    res.bashHint = !bash.standard && !!bash.path;
  }
  const settings = readSettings(res.settingsPath);
  if (settings.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath} is ${settings.error}` });
  const state = readState(ctx.root);
  if (opts.enable !== undefined) {
    res.enable = { id: opts.enable, wasDisabled: !!state.disabled[opts.enable] };
    delete state.disabled[opts.enable];
  }
  const plan = planSync(settings.data, manifest, state, ctx);
  Object.assign(res, { added: plan.added, updated: plan.updated, removed: plan.removed, wired: plan.wired, skipped: plan.skipped });
  const changed = plan.added.length + plan.updated.length + plan.removed.length > 0;
  try {
    if (changed) commitSettings(res, settings, settings.data, opts);
    writeStateIfChanged(ctx.root, plan.newState);
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'write-failed', error: e.message });
  }
  res.status = changed ? 'changed' : 'unchanged';
  return res;
}

function disableHook(opts = {}) {
  const ctx = makeCtx(opts);
  const res = baseResult('disable', ctx, opts);
  const manifestPath = opts.manifestPath || DEFAULT_MANIFEST;
  let manifest;
  try {
    manifest = loadManifest(manifestPath);
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'no-manifest', error: e.message });
  }
  const id = opts.id;
  if (!manifest.hooks.some(h => h.id === id)) return badHookId(res, manifest, id);
  const settings = readSettings(res.settingsPath);
  if (settings.error) return Object.assign(res, { status: 'error', reason: 'malformed', error: `${res.settingsPath} is ${settings.error}` });
  const state = readState(ctx.root);
  const wasDisabled = !!state.disabled[id];
  const plan = planDisable(settings.data, manifest, state, ctx, id);
  res.disable = { id, wasDisabled, removedEntries: plan.removedEntries };
  const newState = { version: 1, hooks: Object.assign({}, state.hooks) };
  delete newState.hooks[id];
  const disabled = Object.assign({}, state.disabled, { [id]: wasDisabled ? state.disabled[id] : plan.entry });
  for (const k of Object.keys(disabled)) if (!manifest.hooks.some(h => h.id === k)) delete disabled[k];
  newState.disabled = disabled;
  try {
    if (plan.removedEntries > 0 && settings.exists) commitSettings(res, settings, settings.data, opts);
    writeStateIfChanged(ctx.root, newState);
  } catch (e) {
    return Object.assign(res, { status: 'error', reason: 'write-failed', error: e.message });
  }
  res.skipped = [{ id, event: plan.entry.event, matcher: plan.entry.matcher, newly: !wasDisabled }];
  res.status = (plan.removedEntries > 0 || !wasDisabled) ? 'changed' : 'unchanged';
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
  'no-bash': 'Git Bash (bash.exe) was not found, and Claude Code runs these hooks with bash',
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
  const skippedLines = () => (res.skipped || []).map(k =>
    `  skipped ${k.id} (you removed it; agency hooks enable ${k.id} to restore)`);
  if (res.reason === 'unknown-id') {
    out.push(`Hooks: ${res.error}`);
    out.push('  Nothing was changed.');
    return out;
  }
  if (res.status === 'skipped' || res.status === 'error') {
    const why = res.status === 'error' ? res.error : (REASONS[res.reason] || res.reason);
    if (res.action === 'remove') {
      out.push(`Hooks: NOT removed: ${why}. Nothing was changed.`);
      return out;
    }
    if (res.action === 'disable') {
      out.push(`Hooks: NOT disabled: ${why}. Nothing was changed.`);
      return out;
    }
    out.push(`Hooks: NOT wired: ${why}.${res.status === 'error' ? ' Nothing was changed.' : ''}`);
    const [a, b] = manualCommands(res.repoDir, res.root);
    if (res.reason === 'no-bash') {
      for (const n of res.notes || []) out.push(`  Note: ${n}.`);
      out.push(`  Install Git for Windows: ${GIT_FOR_WINDOWS_URL}`);
      out.push(`  then run: ${a}`);
      out.push('  or, without the agency command:');
      out.push(`    ${b}`);
      out.push('  (or add --force to wire them anyway)');
      out.push(`  Then: ${RESTART_LINE}`);
      return out;
    }
    out.push(res.reason === 'malformed' ? '  Fix the file, then set the hooks up with:' : '  To set them up, run:');
    out.push(`    ${a}`);
    out.push('  or, without the agency command:');
    out.push(`    ${b}`);
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
  if (res.action === 'disable') {
    const id = res.disable.id;
    if (res.status === 'unchanged') {
      out.push(`Hooks: ${id} is already disabled. Restore it with: agency hooks enable ${id}`);
      return out;
    }
    const n = res.disable.removedEntries;
    out.push(n > 0
      ? `Hooks: disabled ${id} (removed ${n} entr${n === 1 ? 'y' : 'ies'} from ${file})`
      : `Hooks: disabled ${id} (it was not wired; the opt-out is recorded)`);
    out.push(`  It stays off across install, upgrade and sync. Restore it with: agency hooks enable ${id}`);
    if (res.backup) out.push(`  Backup of the previous file: ${res.backup}`);
    if (n > 0) out.push(`  ${RESTART_LINE}`);
    return out;
  }
  if (res.status === 'unchanged') {
    if (res.enable && !res.enable.wasDisabled) out.push(`Hooks: ${res.enable.id} is already enabled`);
    else if (res.enable) out.push(`Hooks: enabled ${res.enable.id} (it was already wired in ${file})`);
    else out.push(`Hooks: ${res.wired} wired, up to date`);
    out.push(...skippedLines());
    return out;
  }
  out.push(res.created
    ? `Hooks: created ${file} with ${res.wired} hooks wired`
    : `Hooks: ${res.added.length} added, ${res.updated.length} updated, ${res.removed.length} removed in ${file}`);
  for (const a of res.added) out.push(`  + ${pad(a.id, 24)}${pad(where(a.event, a.matcher), 26)}${a.purpose}`);
  for (const u of res.updated) out.push(`  ~ ${pad(u.id, 24)}${pad(where(u.event, u.matcher), 26)}${u.purpose} (updated: ${u.change})`);
  for (const r of res.removed) out.push(`  - ${pad(r.id, 24)}${pad(r.event, 26)}removed: no longer shipped`);
  out.push(...skippedLines());
  if (res.backup) out.push(`  Backup of the previous file: ${res.backup}`);
  if (!res.created) out.push('  Your own hooks and settings were left as they were.');
  for (const n of res.notes || []) out.push(`  Note: ${n}.`);
  if (res.bashHint) {
    out.push(`  Git Bash found at ${res.bash.path} (via ${res.bash.source}). If Claude Code cannot find Git Bash, set "env": {"CLAUDE_CODE_GIT_BASH_PATH": ${JSON.stringify(res.bash.path)}} in settings.json.`);
  }
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
    } else if ((out.cmd === 'disable' || out.cmd === 'enable') && !a.startsWith('--') && out.id === undefined) {
      out.id = a;
    } else {
      out.bad = a;
    }
  }
  return out;
}

const USAGE = 'Usage: node cli/lib/hooks-merge.js sync|remove|disable <id>|enable <id> [--root <dir>] [--manifest <file>] [--auto] [--force] [--json]';

function runCli(argv, console = global.console) {
  const { cmd, flags, bad, id } = parseArgs(argv);
  if (!['sync', 'remove', 'disable', 'enable'].includes(cmd) || bad) {
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
  let res;
  if (cmd === 'sync') res = syncHooks(opts);
  else if (cmd === 'remove') res = removeHooks(opts);
  else if (cmd === 'disable') res = disableHook(Object.assign(opts, { id }));
  else res = syncHooks(Object.assign(opts, { enable: id }));
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
  resolveGitBash,
  locateGitBash,
  GIT_FOR_WINDOWS_URL,
  renderCommand,
  normaliseCommand,
  loadManifest,
  readSettings,
  planSync,
  planRemove,
  syncHooks,
  disableHook,
  removeHooks,
  formatResult,
  manualCommands,
  autoSync,
  runCli,
};

if (require.main === module) {
  process.exitCode = runCli(process.argv.slice(2));
}
