#!/usr/bin/env node
// check-mods-merge.js — regression guard for cli/lib/mods-merge.js, the code
// that wires the repo's mods (mods/<name>/) into a user's settings.json as
// env.CLAUDE_CODE_PLUGIN_DIRS on install, upgrade and `agency mods sync|remove`.
//
// What matters most: the merge must never touch what the user owns (their own
// plugin dirs, their own <root>/mods/<dir>, every other settings/env key), must
// never load one mod twice (dedupe by manifest NAME), and `remove` must take
// out exactly what `sync` put in.
//
// Hermetic: every case runs in mktemp sandboxes and injects platform, env, home
// and claudeVersion through the options, so the real ~/.claude and the real
// `claude` binary are never read.
//
// Cases:
//   1.  merge into an existing value: user entry first, our 3 abs paths after,
//       other env keys untouched, one backup
//   2.  dedupe by NAME: a user entry whose manifest name is "beta" -> beta skipped
//   3.  dedupe via a folder-of-plugins user entry holding "gamma" -> gamma skipped
//   4.  version gate: 2.1.286 / null -> skipped, nothing written, ONE line; 2.1.287 -> changed
//   5.  a pre-existing, not-owned <root>/mods/alpha is never touched (skipped "exists")
//   6.  second sync -> unchanged, no new backup, identical bytes
//   7.  remove -> exactly the original settings back (also when the key was absent)
//   8.  windows: ';' separator, native backslash entries
//   9.  --auto + AGENCY_NO_MODS=1 -> skipped, nothing written
//  10.  hooks-merge interplay: syncHooks / disableHook / removeHooks keep state.mods
//  11.  malformed settings.json -> error, nothing written
//  12.  prune: a mod the repo stopped shipping leaves value and disk
//  13+. extras: ~ expansion, copy filter, content refresh, CLI json, status, autoSyncMods
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const MODS_LIB = path.join(REPO, 'cli', 'lib', 'mods-merge.js');
const HOOKS_LIB = path.join(REPO, 'cli', 'lib', 'hooks-merge.js');

let passes = 0;
let failures = 0;
const cleanup = [];

function ok(name) { passes++; console.log(`ok   ${name}`); }
function fail(name, why) { failures++; console.log(`FAIL ${name}${why ? ` -- ${why}` : ''}`); }
function check(name, cond, why) { cond ? ok(name) : fail(name, why); }
function eq(name, got, want) {
  const a = JSON.stringify(got);
  const b = JSON.stringify(want);
  a === b ? ok(name) : fail(name, `got ${a}, want ${b}`);
}

function tmp(label) {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), `mm-${label}-`));
  cleanup.push(d);
  return fs.realpathSync(d);
}
function write(p, text) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, text);
}
function readJson(p) { return JSON.parse(fs.readFileSync(p, 'utf8')); }
function baks(root) {
  return fs.readdirSync(root).filter(f => f.startsWith('settings.json.bak-'));
}
function statePathOf(root) { return path.join(root, 'hooks', '.agency-hooks-state.json'); }
function readStateFile(root) {
  try { return readJson(statePathOf(root)); } catch (_) { return null; }
}

// A plugin dir: .claude-plugin/plugin.json + something to copy.
function makePlugin(dir, name) {
  write(path.join(dir, '.claude-plugin', 'plugin.json'), JSON.stringify({ name, version: '0.0.1' }));
  write(path.join(dir, 'hooks', 'h.js'), `// ${name}\n`);
}

// Fake repo with 3 mods: alpha (dir alpha), beta (dir beta-dir), gamma (dir gamma),
// plus a dir without a manifest and a stray file, both of which must be ignored.
function makeRepo() {
  const repo = tmp('repo');
  makePlugin(path.join(repo, 'mods', 'alpha'), 'alpha');
  makePlugin(path.join(repo, 'mods', 'beta-dir'), 'beta');
  makePlugin(path.join(repo, 'mods', 'gamma'), 'gamma');
  write(path.join(repo, 'mods', 'alpha', 'node_modules', 'junk', 'index.js'), 'x');
  write(path.join(repo, 'mods', 'alpha', '__pycache__', 'a.pyc'), 'x');
  write(path.join(repo, 'mods', 'alpha', 'types', 'index.d.ts'), 'export {};\n');
  write(path.join(repo, 'mods', 'nomanifest', 'file.txt'), 'x');
  write(path.join(repo, 'mods', 'README.md'), '# mods\n');
  return repo;
}

function opts(root, repoDir, extra) {
  return Object.assign({
    root, repoDir, env: {}, platform: 'linux', home: path.join(root, '..', 'nohome'),
    claudeVersion: '2.1.293',
  }, extra || {});
}
function modEntry(root, dir) { return path.join(root, 'mods', dir); }

let lib;
try {
  lib = require(MODS_LIB);
} catch (e) {
  fail('load cli/lib/mods-merge.js', e.message);
  console.log(`\n${passes} passed, ${failures} failed`);
  process.exit(1);
}
const hooks = require(HOOKS_LIB);

const OWNED = root => ['alpha', 'beta-dir', 'gamma'].map(d => modEntry(root, d));

// ---------------------------------------------------------------------------
// 1. merge with an existing value
{
  const repo = makeRepo();
  const root = tmp('c1');
  const settings = { model: 'opus', env: { OTHER: 'x', CLAUDE_CODE_PLUGIN_DIRS: '/u/plug-a' }, permissions: { allow: ['Bash'] } };
  write(path.join(root, 'settings.json'), JSON.stringify(settings, null, 2) + '\n');
  const res = lib.syncMods(opts(root, repo));
  const s = readJson(path.join(root, 'settings.json'));
  eq('1 status changed', res.status, 'changed');
  eq('1 value = user entry + 3 owned abs paths', s.env.CLAUDE_CODE_PLUGIN_DIRS, ['/u/plug-a'].concat(OWNED(root)).join(':'));
  eq('1 OTHER env key untouched', s.env.OTHER, 'x');
  eq('1 other top-level keys untouched', [s.model, s.permissions], ['opus', { allow: ['Bash'] }]);
  eq('1 one backup written', baks(root).length, 1);
  check('1 result.backup points at it', res.backup && fs.existsSync(res.backup), String(res.backup));
  eq('1 added names', res.added.slice().sort(), ['alpha', 'beta', 'gamma']);
  const st = readStateFile(root);
  eq('1 state.mods.installed (names)', st && st.mods && st.mods.installed, ['alpha', 'beta', 'gamma']);
  eq('1 state.mods.entries (abs paths)', st && st.mods && st.mods.entries, OWNED(root));
  check('1 mods copied', fs.existsSync(path.join(modEntry(root, 'beta-dir'), '.claude-plugin', 'plugin.json')));
  check('1 node_modules / __pycache__ not copied',
    !fs.existsSync(path.join(modEntry(root, 'alpha'), 'node_modules')) && !fs.existsSync(path.join(modEntry(root, 'alpha'), '__pycache__')));
  check('1 types/ is copied', fs.existsSync(path.join(modEntry(root, 'alpha'), 'types', 'index.d.ts')));
  check('1 dir without a manifest is not a mod', !fs.existsSync(modEntry(root, 'nomanifest')));
}

// 2. dedupe by NAME (user dir name differs from manifest name)
{
  const repo = makeRepo();
  const root = tmp('c2');
  const userDir = path.join(tmp('u2'), 'my-beta');
  makePlugin(userDir, 'beta');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: userDir } }, null, 2) + '\n');
  const res = lib.syncMods(opts(root, repo));
  const s = readJson(path.join(root, 'settings.json'));
  const sk = res.skipped.find(x => x.name === 'beta');
  check('2 beta skipped as provided', sk && sk.reason === 'provided' && sk.entry === userDir, JSON.stringify(res.skipped));
  eq('2 value = user + alpha + gamma only', s.env.CLAUDE_CODE_PLUGIN_DIRS, [userDir, modEntry(root, 'alpha'), modEntry(root, 'gamma')].join(':'));
  check('2 beta not copied', !fs.existsSync(modEntry(root, 'beta-dir')));
}

// 3. dedupe via a folder-of-plugins user entry
{
  const repo = makeRepo();
  const root = tmp('c3');
  const pack = path.join(tmp('u3'), 'pack');
  makePlugin(path.join(pack, 'some-gamma'), 'gamma');
  makePlugin(path.join(pack, 'other'), 'other');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: pack } }, null, 2) + '\n');
  const res = lib.syncMods(opts(root, repo));
  const sk = res.skipped.find(x => x.name === 'gamma');
  check('3 gamma skipped as provided', sk && sk.reason === 'provided' && sk.entry === pack, JSON.stringify(res.skipped));
  eq('3 value = pack + alpha + beta', readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS,
    [pack, modEntry(root, 'alpha'), modEntry(root, 'beta-dir')].join(':'));
}

// 4. version gate
{
  const repo = makeRepo();
  const root = tmp('c4');
  const raw = JSON.stringify({ model: 'x' }, null, 2) + '\n';
  write(path.join(root, 'settings.json'), raw);
  const old = lib.syncMods(opts(root, repo, { claudeVersion: '2.1.286' }));
  eq('4 2.1.286 -> skipped/version', [old.status, old.reason], ['skipped', 'version']);
  eq('4 2.1.286 settings bytes unchanged', fs.readFileSync(path.join(root, 'settings.json'), 'utf8'), raw);
  check('4 2.1.286 no mods dir, no state, no backup',
    !fs.existsSync(path.join(root, 'mods')) && !fs.existsSync(statePathOf(root)) && baks(root).length === 0);
  eq('4 formatResult is exactly one line', lib.formatResult(old),
    ['Mods: skipped (needs Claude Code 2.1.287+, found 2.1.286). After updating: agency mods sync']);
  const none = lib.syncMods(opts(root, repo, { claudeVersion: null }));
  eq('4 null -> skipped/version', [none.status, none.reason], ['skipped', 'version']);
  const noneLines = lib.formatResult(none);
  check('4 null line says "found none"', noneLines.length === 1 && noneLines[0].includes('found none'), noneLines.join('|'));
  check('4 MIN_VERSION export', lib.MIN_VERSION === '2.1.287', String(lib.MIN_VERSION));
  const exact = lib.syncMods(opts(root, repo, { claudeVersion: '2.1.287' }));
  eq('4 2.1.287 -> changed', exact.status, 'changed');
  const big = lib.syncMods(opts(tmp('c4b'), repo, { claudeVersion: '2.10.0' }));
  eq('4 2.10.0 compares numerically (changed)', big.status, 'changed');
  const viaEnv = lib.syncMods(opts(tmp('c4c'), repo, { claudeVersion: undefined, env: { AGENCY_CLAUDE_VERSION: '2.1.200' } }));
  eq('4 AGENCY_CLAUDE_VERSION env is honoured', [viaEnv.status, viaEnv.reason], ['skipped', 'version']);
}

// 5. existing, not-owned mod dir is protected
{
  const repo = makeRepo();
  const root = tmp('c5');
  write(path.join(root, 'mods', 'alpha', 'marker.txt'), 'mine');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: '/u/a' } }, null, 2) + '\n');
  const res = lib.syncMods(opts(root, repo));
  const sk = res.skipped.find(x => x.name === 'alpha');
  check('5 alpha skipped as exists', sk && sk.reason === 'exists', JSON.stringify(res.skipped));
  eq('5 marker intact', fs.readFileSync(path.join(root, 'mods', 'alpha', 'marker.txt'), 'utf8'), 'mine');
  check('5 nothing else copied into alpha', !fs.existsSync(path.join(root, 'mods', 'alpha', '.claude-plugin')));
  eq('5 value has no alpha entry', readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS,
    ['/u/a', modEntry(root, 'beta-dir'), modEntry(root, 'gamma')].join(':'));
  // a second sync keeps protecting it, and remove leaves it
  const again = lib.syncMods(opts(root, repo));
  eq('5 second sync unchanged', again.status, 'unchanged');
  lib.removeMods(opts(root, repo));
  eq('5 remove leaves the user dir', fs.readFileSync(path.join(root, 'mods', 'alpha', 'marker.txt'), 'utf8'), 'mine');
  check('5 remove deleted only our dirs', !fs.existsSync(modEntry(root, 'beta-dir')) && !fs.existsSync(modEntry(root, 'gamma')));
}

// 6. idempotent
{
  const repo = makeRepo();
  const root = tmp('c6');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: '/u/a' } }, null, 2) + '\n');
  lib.syncMods(opts(root, repo));
  const bytes = fs.readFileSync(path.join(root, 'settings.json'), 'utf8');
  const stateBytes = fs.readFileSync(statePathOf(root), 'utf8');
  const nb = baks(root).length;
  const res = lib.syncMods(opts(root, repo));
  eq('6 second sync unchanged', res.status, 'unchanged');
  eq('6 settings bytes identical', fs.readFileSync(path.join(root, 'settings.json'), 'utf8'), bytes);
  eq('6 state bytes identical', fs.readFileSync(statePathOf(root), 'utf8'), stateBytes);
  eq('6 no new backup', baks(root).length, nb);
  eq('6 nothing re-copied', res.copied, []);
}

// 7. remove restores the original
{
  const repo = makeRepo();
  const root = tmp('c7');
  const settings = { env: { OTHER: 'x', CLAUDE_CODE_PLUGIN_DIRS: '/u/plug-a:/u/plug-b' }, model: 'opus' };
  const raw = JSON.stringify(settings, null, 2) + '\n';
  write(path.join(root, 'settings.json'), raw);
  write(path.join(root, 'mods', 'mine', 'keep.txt'), 'mine');
  lib.syncMods(opts(root, repo));
  const res = lib.removeMods(opts(root, repo));
  eq('7 remove changed', res.status, 'changed');
  eq('7 value back to the original string', readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS, '/u/plug-a:/u/plug-b');
  eq('7 whole settings equal the original', readJson(path.join(root, 'settings.json')), settings);
  check('7 owned dirs gone', !['alpha', 'beta-dir', 'gamma'].some(d => fs.existsSync(modEntry(root, d))));
  eq('7 user dir intact (so mods/ stays)', fs.readFileSync(path.join(root, 'mods', 'mine', 'keep.txt'), 'utf8'), 'mine');
  const st = readStateFile(root);
  check('7 state.mods gone', !st || st.mods === undefined, JSON.stringify(st));
  const again = lib.removeMods(opts(root, repo));
  eq('7 second remove unchanged', again.status, 'unchanged');
  eq('7 remove works without the version gate', lib.removeMods(opts(root, repo, { claudeVersion: null })).status, 'unchanged');

  // key absent before sync -> absent after remove; mods/ removed when empty
  const root2 = tmp('c7b');
  const s2 = { model: 'opus' };
  write(path.join(root2, 'settings.json'), JSON.stringify(s2, null, 2) + '\n');
  lib.syncMods(opts(root2, repo));
  check('7 sync created the key', readJson(path.join(root2, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS.includes('alpha'));
  lib.removeMods(opts(root2, repo));
  eq('7 key absent -> absent again (env removed too)', readJson(path.join(root2, 'settings.json')), s2);
  check('7 empty <root>/mods removed', !fs.existsSync(path.join(root2, 'mods')));

  // key absent but env has other keys -> env stays, key gone
  const root3 = tmp('c7c');
  write(path.join(root3, 'settings.json'), JSON.stringify({ env: { OTHER: '1' } }, null, 2) + '\n');
  lib.syncMods(opts(root3, repo));
  lib.removeMods(opts(root3, repo));
  eq('7 env with other keys survives', readJson(path.join(root3, 'settings.json')), { env: { OTHER: '1' } });

  // no settings.json at all: sync creates it, remove leaves a clean file
  const root4 = tmp('c7d');
  const r4 = lib.syncMods(opts(root4, repo));
  eq('7 sync with no settings.json creates it', [r4.status, fs.existsSync(path.join(root4, 'settings.json'))], ['changed', true]);
  eq('7 no backup when there was nothing to back up', baks(root4).length, 0);
}

// 8. windows separator and native entries
{
  const repo = makeRepo();
  const root = tmp('c8');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: 'C:\\u\\a' } }, null, 2) + '\n');
  const res = lib.syncMods(opts(root, repo, { platform: 'win32' }));
  const native = d => path.join(root, 'mods', d).replace(/\//g, '\\');
  const v = readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS;
  eq('8 changed', res.status, 'changed');
  eq("8 ';'-joined, native backslash entries", v, ['C:\\u\\a', native('alpha'), native('beta-dir'), native('gamma')].join(';'));
  check('8 owned entries contain no forward slash', v.split(';').slice(1).every(e => !e.includes('/')), v);
  const rm = lib.removeMods(opts(root, repo, { platform: 'win32' }));
  eq('8 remove restores', [rm.status, readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS], ['changed', 'C:\\u\\a']);
}

// 9. opt-out
{
  const repo = makeRepo();
  const root = tmp('c9');
  const res = lib.syncMods(opts(root, repo, { auto: true, env: { AGENCY_NO_MODS: '1' } }));
  eq('9 auto + AGENCY_NO_MODS=1 -> skipped/opt-out', [res.status, res.reason], ['skipped', 'opt-out']);
  check('9 nothing written', fs.readdirSync(root).length === 0, fs.readdirSync(root).join(','));
  const explicit = lib.syncMods(opts(root, repo, { env: { AGENCY_NO_MODS: '1' } }));
  eq('9 explicit sync ignores AGENCY_NO_MODS', explicit.status, 'changed');
  const zero = lib.syncMods(opts(tmp('c9b'), repo, { auto: true, env: { AGENCY_NO_MODS: '0' } }));
  eq('9 AGENCY_NO_MODS=0 is not an opt-out', zero.status, 'changed');
}

// 10. hooks-merge interplay
{
  const repo = makeRepo();
  const root = tmp('c10');
  const manifest = path.join(tmp('m10'), 'hooks.json');
  write(manifest, JSON.stringify({
    hooks: [{ id: 'stop-x', event: 'Stop', matcher: '', command: 'bash {root}/hooks/x.sh', purpose: 'test' }],
  }));
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: '/u/a' } }, null, 2) + '\n');
  lib.syncMods(opts(root, repo));
  const mods = readStateFile(root).mods;
  const hopts = { root, repoDir: repo, manifestPath: manifest, env: {}, home: path.join(root, '..', 'nohome') };
  const h = hooks.syncHooks(hopts);
  eq('10 syncHooks changed', h.status, 'changed');
  const st = readStateFile(root);
  eq('10 syncHooks keeps state.mods', st.mods, mods);
  check('10 syncHooks wrote its own state', st.hooks['stop-x'] !== undefined);
  const d = hooks.disableHook(Object.assign({ id: 'stop-x' }, hopts));
  eq('10 disableHook ok', d.status, 'changed');
  eq('10 disableHook keeps state.mods', readStateFile(root).mods, mods);
  hooks.syncHooks(Object.assign({ enable: 'stop-x' }, hopts));
  const r = hooks.removeHooks(hopts);
  eq('10 removeHooks ok', r.status, 'changed');
  check('10 state file still exists after removeHooks', fs.existsSync(statePathOf(root)));
  const st2 = readStateFile(root);
  eq('10 removeHooks keeps state.mods, hooks empty', [st2.version, st2.hooks, st2.mods], [1, {}, mods]);
  const rm = lib.removeMods(opts(root, repo));
  eq('10 removeMods still works after removeHooks', [rm.status, readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS], ['changed', '/u/a']);

  // removeHooks with no mods still deletes the state file (unchanged behaviour)
  const root2 = tmp('c10b');
  hooks.syncHooks(Object.assign({}, hopts, { root: root2 }));
  check('10 hooks-only: state exists', fs.existsSync(statePathOf(root2)));
  hooks.removeHooks(Object.assign({}, hopts, { root: root2 }));
  check('10 hooks-only: removeHooks deletes the state file', !fs.existsSync(statePathOf(root2)));

  // mods sync keeps hooks state
  const root3 = tmp('c10c');
  hooks.syncHooks(Object.assign({}, hopts, { root: root3 }));
  const before = readStateFile(root3).hooks;
  lib.syncMods(opts(root3, repo));
  eq('10 syncMods keeps state.hooks', readStateFile(root3).hooks, before);
  lib.removeMods(opts(root3, repo));
  eq('10 removeMods keeps state.hooks', readStateFile(root3).hooks, before);
}

// 11. malformed settings
{
  const repo = makeRepo();
  const root = tmp('c11');
  const bad = '{ "env": { oops';
  write(path.join(root, 'settings.json'), bad);
  const res = lib.syncMods(opts(root, repo));
  eq('11 sync -> error/malformed', [res.status, res.reason], ['error', 'malformed']);
  eq('11 bytes untouched', fs.readFileSync(path.join(root, 'settings.json'), 'utf8'), bad);
  check('11 no mods dir, no state, no backup',
    !fs.existsSync(path.join(root, 'mods')) && !fs.existsSync(statePathOf(root)) && baks(root).length === 0);
  const rm = lib.removeMods(opts(root, repo));
  eq('11 remove -> error/malformed', [rm.status, rm.reason], ['error', 'malformed']);
  const nonString = tmp('c11b');
  write(path.join(nonString, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: 5 } }));
  const ns = lib.syncMods(opts(nonString, repo));
  eq('11 non-string value -> error/malformed, untouched', [ns.status, ns.reason, baks(nonString).length], ['error', 'malformed', 0]);
}

// 12. prune
{
  const repo = makeRepo();
  const root = tmp('c12');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: '/u/a' } }, null, 2) + '\n');
  lib.syncMods(opts(root, repo));
  fs.rmSync(path.join(repo, 'mods', 'beta-dir'), { recursive: true });
  const res = lib.syncMods(opts(root, repo));
  eq('12 changed', res.status, 'changed');
  eq('12 pruned names', res.pruned, ['beta']);
  eq('12 value lost the retired mod', readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS,
    ['/u/a', modEntry(root, 'alpha'), modEntry(root, 'gamma')].join(':'));
  check('12 its dir is gone', !fs.existsSync(modEntry(root, 'beta-dir')));
  const st = readStateFile(root);
  eq('12 state follows', [st.mods.installed, st.mods.entries], [['alpha', 'gamma'], [modEntry(root, 'alpha'), modEntry(root, 'gamma')]]);

  // the user adds their own copy of an owned mod: ours is pruned, theirs wins
  const userGamma = path.join(tmp('u12'), 'gamma-mine');
  makePlugin(userGamma, 'gamma');
  const s = readJson(path.join(root, 'settings.json'));
  s.env.CLAUDE_CODE_PLUGIN_DIRS += ':' + userGamma;
  write(path.join(root, 'settings.json'), JSON.stringify(s, null, 2) + '\n');
  const res2 = lib.syncMods(opts(root, repo));
  eq('12 user now provides gamma -> ours pruned', res2.pruned, ['gamma']);
  eq('12 value = user entries + remaining owned', readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS,
    ['/u/a', userGamma, modEntry(root, 'alpha')].join(':'));
  check('12 our gamma dir gone', !fs.existsSync(modEntry(root, 'gamma')));
}

// ---------------------------------------------------------------------------
// extras
{
  // ~ expansion in a user entry counts for dedupe
  const repo = makeRepo();
  const root = tmp('x1');
  const home = tmp('home1');
  makePlugin(path.join(home, 'plugs', 'alpha-user'), 'alpha');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: '~/plugs/alpha-user' } }, null, 2) + '\n');
  const res = lib.syncMods(opts(root, repo, { home }));
  const sk = res.skipped.find(x => x.name === 'alpha');
  check('x1 "~/..." user entry provides alpha', sk && sk.reason === 'provided', JSON.stringify(res.skipped));
  eq('x1 user string kept verbatim', readJson(path.join(root, 'settings.json')).env.CLAUDE_CODE_PLUGIN_DIRS.split(':')[0], '~/plugs/alpha-user');
}
{
  // a repo update refreshes our copy; an entry with no manifest provides its basename
  const repo = makeRepo();
  const root = tmp('x2');
  lib.syncMods(opts(root, repo));
  write(path.join(repo, 'mods', 'gamma', 'hooks', 'h.js'), '// gamma v2\n');
  const res = lib.syncMods(opts(root, repo));
  eq('x2 content change -> changed + copied', [res.status, res.copied], ['changed', ['gamma']]);
  eq('x2 copy refreshed', fs.readFileSync(path.join(modEntry(root, 'gamma'), 'hooks', 'h.js'), 'utf8'), '// gamma v2\n');
  write(path.join(repo, 'mods', 'gamma', 'obsolete-in-v2.txt'), 'x');
  lib.syncMods(opts(root, repo));
  fs.rmSync(path.join(repo, 'mods', 'gamma', 'obsolete-in-v2.txt'));
  lib.syncMods(opts(root, repo));
  check('x2 replaced fully (a file the repo dropped is gone)', !fs.existsSync(path.join(modEntry(root, 'gamma'), 'obsolete-in-v2.txt')));

  const root2 = tmp('x2b');
  const bare = path.join(tmp('u-bare'), 'beta');
  fs.mkdirSync(bare, { recursive: true });
  write(path.join(root2, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: bare } }) + '\n');
  const r2 = lib.syncMods(opts(root2, repo));
  check('x2 manifest-less dir provides its basename', r2.skipped.some(x => x.name === 'beta' && x.reason === 'provided'), JSON.stringify(r2.skipped));
}
{
  // relative user entries are skipped by Claude Code, so they provide nothing
  const repo = makeRepo();
  const root = tmp('x3');
  write(path.join(root, 'settings.json'), JSON.stringify({ env: { CLAUDE_CODE_PLUGIN_DIRS: ' rel/alpha ; ' } }) + '\n');
  const res = lib.syncMods(opts(root, repo));
  check('x3 relative entry provides nothing', !res.skipped.some(x => x.name === 'alpha'), JSON.stringify(res.skipped));
}
{
  // status is read-only
  const repo = makeRepo();
  const root = tmp('x4');
  const s0 = lib.statusMods(opts(root, repo));
  check('x4 status before sync: nothing written', fs.readdirSync(root).length === 0);
  check('x4 status before sync reports a result', s0 && typeof s0.status === 'string', JSON.stringify(s0 && s0.status));
  lib.syncMods(opts(root, repo));
  const bytes = fs.readFileSync(path.join(root, 'settings.json'), 'utf8');
  const s1 = lib.statusMods(opts(root, repo));
  eq('x4 status after sync: kept', s1.kept.slice().sort(), ['alpha', 'beta', 'gamma']);
  eq('x4 status did not write', fs.readFileSync(path.join(root, 'settings.json'), 'utf8'), bytes);
  check('x4 status lines are non-empty', lib.formatResult(s1).length > 0);
}
{
  // autoSyncMods never throws and prints formatResult lines
  const repo = makeRepo();
  const root = tmp('x5');
  const lines = [];
  const fake = { log: l => lines.push(l), error: l => lines.push(l) };
  const prev = process.env.AGENCY_CLAUDE_VERSION;
  process.env.AGENCY_CLAUDE_VERSION = '2.1.293';
  let res;
  try {
    res = lib.autoSyncMods({ root, repoDir: repo, console: fake, indent: '  ' });
  } finally {
    if (prev === undefined) delete process.env.AGENCY_CLAUDE_VERSION; else process.env.AGENCY_CLAUDE_VERSION = prev;
  }
  eq('x5 autoSyncMods returns the result', res && res.status, 'changed');
  check('x5 lines printed with the indent', lines.length > 0 && lines.every(l => l.startsWith('  ')), JSON.stringify(lines));
  const badRoot = tmp('x5b');
  write(path.join(badRoot, 'settings.json'), '{ nope');
  let threw = false;
  try { lib.autoSyncMods({ root: badRoot, repoDir: repo, console: fake }); } catch (_) { threw = true; }
  check('x5 autoSyncMods never throws', !threw);
  let threw2 = false;
  try { lib.autoSyncMods({ root: badRoot, repoDir: path.join(badRoot, 'no-such-repo'), console: fake }); } catch (_) { threw2 = true; }
  check('x5 autoSyncMods never throws (missing repo)', !threw2);
}
{
  // CLI form
  const repo = makeRepo();
  const root = tmp('x6');
  const env = Object.assign({}, process.env, { AGENCY_CLAUDE_VERSION: '2.1.293' });
  delete env.AGENCY_NO_MODS;
  const run = args => spawnSync(process.execPath, [MODS_LIB].concat(args), { encoding: 'utf8', env });
  const r = run(['sync', '--root', root, '--repo', repo, '--json']);
  let j = null;
  try { j = JSON.parse(r.stdout); } catch (_) {}
  eq('x6 CLI sync --json: exit 0, changed', [r.status, j && j.status], [0, 'changed']);
  const st = run(['status', '--root', root, '--repo', repo]);
  eq('x6 CLI status exit 0', st.status, 0);
  const rm = run(['remove', '--root', root, '--repo', repo]);
  eq('x6 CLI remove exit 0', rm.status, 0);
  const bad = tmp('x6b');
  write(path.join(bad, 'settings.json'), '{ nope');
  eq('x6 CLI exit 1 only on error status', run(['sync', '--root', bad, '--repo', repo]).status, 1);
  const old = spawnSync(process.execPath, [MODS_LIB, 'sync', '--root', tmp('x6c'), '--repo', repo], { encoding: 'utf8', env: Object.assign({}, env, { AGENCY_CLAUDE_VERSION: '2.1.100' }) });
  eq('x6 CLI version-skip exits 0', old.status, 0);
  eq('x6 bad usage exits non-zero', run(['bogus']).status !== 0, true);
  const oo = spawnSync(process.execPath, [MODS_LIB, 'sync', '--auto', '--root', tmp('x6d'), '--repo', repo], { encoding: 'utf8', env: Object.assign({}, env, { AGENCY_NO_MODS: '1' }) });
  check('x6 CLI --auto honours AGENCY_NO_MODS', oo.status === 0 && !/changed/.test(oo.stdout));
}

for (const d of cleanup) {
  try { fs.rmSync(d, { recursive: true, force: true }); } catch (_) {}
}
console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures ? 1 : 0);
