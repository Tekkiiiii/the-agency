#!/usr/bin/env node
// check-hooks-merge.js — regression guard for cli/lib/hooks-merge.js, the code
// that wires hooks/hooks.json into a user's settings.json on install, upgrade
// and `agency hooks sync|remove`.
//
// The bug it guards: install.sh wired hooks only when settings.json did not
// exist yet, and `agency upgrade` synced hook FILES but never wired them, so
// every existing Claude Code user ran zero agency hooks. The fix merges into a
// live settings.json — which holds the user's own hooks, MCP servers and
// permissions — so the property that matters most is what it must NOT touch.
//
// Everything runs in mktemp sandboxes. HOME and AGENCY_HOME are always set to
// sandbox paths: a run of this script can never read or write the real
// ~/.claude/settings.json.
//
// Cases:
//   1. sync into a settings.json with user hooks (one under {root}/hooks/ that
//      is NOT in the manifest, one composite command that mentions one of our
//      scripts) + other top-level keys -> user hooks and keys intact, ours
//      added once each, one timestamped backup, state file written
//   2. second sync -> byte-identical settings.json and state file, no new backup
//   3. manifest change (one hook retired, one dropped without a retired entry,
//      one matcher changed) -> pruned / pruned via state / moved; user intact
//   4. remove -> only ours gone (current, retired and state-recorded), user
//      hooks + keys intact, state file deleted
//   5. root == $HOME/.claude: an existing `bash ~/.claude/hooks/x.sh` or
//      `$HOME/.claude` form counts as present (no duplicate, not rewritten),
//      and an entry the user put under a different matcher is left there
//   6. malformed settings.json -> exit 1, file untouched, no backup, manual
//      command printed
//   7. AGENCY_NO_HOOKS=1 skips only automatic (--auto) wiring
//   8. the human-readable message: block with purposes + restart line on
//      change, one quiet line when up to date
//   9. pure-function checks: Windows root forms, quoting of a root with spaces,
//      win32 without bash -> skipped
//  10. install.sh end to end: fresh root -> settings.json created with hooks;
//      second install -> no change, no backup (skipped on win32: install.sh
//      there is Git Bash, covered by the install.ps1 job instead)
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const MOD = path.join(REPO, 'cli', 'lib', 'hooks-merge.js');
const MANIFEST = path.join(REPO, 'hooks', 'hooks.json');

let failures = 0;
let passes = 0;
function ok(cond, msg) {
  if (cond) { passes++; console.log('  ok   ' + msg); }
  else { failures++; console.log('  FAIL ' + msg); }
}
function section(name) { console.log('\n# ' + name); }
function sha(p) { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'); }
function readJson(p) { return JSON.parse(fs.readFileSync(p, 'utf8')); }
function backups(dir) { return fs.readdirSync(dir).filter(n => /^settings\.json\.bak-\d{8}-\d{6}(-\d+)?$/.test(n)); }
function allCommands(settings) {
  const out = [];
  for (const [event, groups] of Object.entries(settings.hooks || {})) {
    for (const g of groups) for (const h of g.hooks || []) out.push({ event, matcher: g.matcher, command: h.command });
  }
  return out;
}
function countCmd(settings, cmd) { return allCommands(settings).filter(c => c.command === cmd).length; }
function sandbox() { return fs.mkdtempSync(path.join(os.tmpdir(), 'hooks-merge-')); }

function run(args, env, opts) {
  const res = spawnSync(process.execPath, [MOD, ...args], {
    encoding: 'utf8',
    env: Object.assign({}, process.env, { AGENCY_NO_HOOKS: '' }, env || {}),
    ...(opts || {}),
  });
  return { code: res.status, out: (res.stdout || '') + (res.stderr || ''), stdout: res.stdout || '' };
}
function runJson(args, env) {
  const r = run(args.concat('--json'), env);
  let json = null;
  try { json = JSON.parse(r.stdout); } catch (_) {}
  return Object.assign(r, { json });
}

if (!fs.existsSync(MOD)) {
  console.log(`FAIL: ${path.relative(REPO, MOD)} does not exist`);
  process.exit(1);
}
if (!fs.existsSync(MANIFEST)) {
  console.log(`FAIL: ${path.relative(REPO, MANIFEST)} does not exist`);
  process.exit(1);
}

const manifest = readJson(MANIFEST);
const hm = require(MOD);

// ---------------------------------------------------------------------------
section('1. sync into settings.json with user hooks and other keys');
const T1 = sandbox();
const HOME1 = path.join(T1, 'home');
const ROOT1 = path.join(T1, 'root');
fs.mkdirSync(path.join(ROOT1, 'hooks'), { recursive: true });
fs.mkdirSync(HOME1, { recursive: true });
const env1 = { HOME: HOME1, USERPROFILE: HOME1, AGENCY_HOME: ROOT1 };
const R = ROOT1.split(path.sep).join('/');
const userPersonal = `bash ${R}/hooks/my-personal.sh`;            // under {root}/hooks, NOT in manifest
const userComposite = `echo pre && bash ${R}/hooks/gate-guard.sh`;  // composite: user-owned
const userStop = 'sh ~/.agent-memory/heartbeat.sh stop';
const original = {
  model: 'opus',
  env: { FOO: '1' },
  permissions: { allow: ['Bash(ls:*)'] },
  hooks: {
    PreToolUse: [
      { matcher: 'Bash', hooks: [{ type: 'command', command: userPersonal }] },
      { matcher: 'Edit|Write', hooks: [{ type: 'command', command: userComposite }] },
    ],
    Stop: [{ matcher: '', hooks: [{ type: 'command', command: userStop }] }],
  },
  statusLine: { type: 'command', command: 'echo status' },
};
const S1 = path.join(ROOT1, 'settings.json');
fs.writeFileSync(S1, JSON.stringify(original, null, 2) + '\n');

const r1 = runJson(['sync', '--root', ROOT1], env1);
ok(r1.code === 0, `sync exit 0 (got ${r1.code})`);
ok(r1.json && r1.json.status === 'changed', `status changed (got ${r1.json && r1.json.status})`);
const s1 = readJson(S1);
for (const k of ['model', 'env', 'permissions', 'statusLine']) {
  ok(JSON.stringify(s1[k]) === JSON.stringify(original[k]), `top-level key "${k}" untouched`);
}
ok(JSON.stringify(Object.keys(s1)) === JSON.stringify(Object.keys(original)), 'top-level key order preserved');
ok(JSON.stringify(s1.hooks.PreToolUse[0]) === JSON.stringify(original.hooks.PreToolUse[0]), 'user hook under {root}/hooks (not in manifest) intact, same position');
ok(JSON.stringify(s1.hooks.PreToolUse[1]) === JSON.stringify(original.hooks.PreToolUse[1]), 'user composite command group intact, same position');
ok(JSON.stringify(s1.hooks.Stop[0]) === JSON.stringify(original.hooks.Stop[0]), 'user Stop hook intact, same position');
for (const h of manifest.hooks) {
  const cmd = hm.renderCommand(h.command, ROOT1);
  ok(countCmd(s1, cmd) === 1, `manifest hook ${h.id} wired exactly once`);
}
ok(backups(ROOT1).length === 1, `one backup created (got ${backups(ROOT1).length})`);
const bk = backups(ROOT1)[0];
ok(bk && fs.readFileSync(path.join(ROOT1, bk), 'utf8') === JSON.stringify(original, null, 2) + '\n', 'backup holds the pre-sync bytes');
const STATE1 = path.join(ROOT1, 'hooks', '.agency-hooks-state.json');
ok(fs.existsSync(STATE1), 'state file written under {root}/hooks/');
ok(fs.readFileSync(S1, 'utf8').endsWith('}\n'), 'trailing newline kept');
ok(/^\{\n  "model"/.test(fs.readFileSync(S1, 'utf8')), '2-space indent kept');
ok(!fs.readdirSync(ROOT1).some(n => n.includes('tmp')), 'no temp file left behind');

// ---------------------------------------------------------------------------
section('2. second sync is a no-op on disk');
const shaA = sha(S1);
const stateShaA = sha(STATE1);
const r2 = runJson(['sync', '--root', ROOT1], env1);
ok(r2.code === 0, 'second sync exit 0');
ok(r2.json && r2.json.status === 'unchanged', `status unchanged (got ${r2.json && r2.json.status})`);
ok(sha(S1) === shaA, `settings.json byte-identical (${shaA.slice(0, 12)})`);
ok(sha(STATE1) === stateShaA, 'state file byte-identical');
ok(backups(ROOT1).length === 1, `no new backup (count ${backups(ROOT1).length})`);

// ---------------------------------------------------------------------------
section('3. manifest change: retire, drop, move');
const m2 = JSON.parse(JSON.stringify(manifest));
const retireId = 'secret-scanner';
const dropId = 'config-protection';
const moveId = 'spawn-gate';
const retired = m2.hooks.find(h => h.id === retireId);
const dropped = m2.hooks.find(h => h.id === dropId);
ok(!!retired && !!dropped && !!m2.hooks.find(h => h.id === moveId), 'fixture ids exist in the real manifest');
m2.hooks = m2.hooks.filter(h => h.id !== retireId && h.id !== dropId);
m2.retired = (m2.retired || []).concat([{ id: retired.id, event: retired.event, command: retired.command }]);
m2.hooks.find(h => h.id === moveId).matcher = 'Agent|Task';
const M2 = path.join(T1, 'hooks-v2.json');
fs.writeFileSync(M2, JSON.stringify(m2, null, 2) + '\n');
const r3 = runJson(['sync', '--root', ROOT1, '--manifest', M2], env1);
ok(r3.code === 0, 'sync with changed manifest exit 0');
const s3 = readJson(S1);
ok(countCmd(s3, hm.renderCommand(retired.command, ROOT1)) === 0, 'retired hook pruned');
ok(countCmd(s3, hm.renderCommand(dropped.command, ROOT1)) === 0, 'hook dropped without a retired entry pruned (via state)');
const moved = allCommands(s3).filter(c => c.command === hm.renderCommand(m2.hooks.find(h => h.id === moveId).command, ROOT1));
ok(moved.length === 1 && moved[0].matcher === 'Agent|Task', `changed-matcher hook moved once to Agent|Task (got ${JSON.stringify(moved)})`);
ok(r3.json && r3.json.removed.map(x => x.id).sort().join(',') === [dropId, retireId].sort().join(','), 'report lists both removals');
ok(r3.json && r3.json.updated.map(x => x.id).join(',') === moveId, 'report lists the matcher update');
ok(JSON.stringify(s3.hooks.PreToolUse[0]) === JSON.stringify(original.hooks.PreToolUse[0]), 'user hook still intact');
ok(JSON.stringify(s3.hooks.PreToolUse[1]) === JSON.stringify(original.hooks.PreToolUse[1]), 'user composite still intact');
ok(Object.values(s3.hooks).every(gs => gs.length > 0 && gs.every(g => (g.hooks || []).length > 0)), 'no empty groups or events left behind');
ok(backups(ROOT1).length === 2, `second backup for the second real change (count ${backups(ROOT1).length})`);
const r3b = runJson(['sync', '--root', ROOT1, '--manifest', M2], env1);
ok(r3b.json && r3b.json.status === 'unchanged', 're-sync with the changed manifest is a no-op');

// ---------------------------------------------------------------------------
section('4. remove: only ours go');
// Re-insert the retired hook by hand (as an old install would still have it):
// remove must recognise it through the manifest's retired list.
{
  const s = readJson(S1);
  s.hooks.PreToolUse.push({ matcher: 'Bash', hooks: [{ type: 'command', command: hm.renderCommand(retired.command, ROOT1) }] });
  fs.writeFileSync(S1, JSON.stringify(s, null, 2) + '\n');
}
const r4 = runJson(['remove', '--root', ROOT1, '--manifest', M2], env1);
ok(r4.code === 0, 'remove exit 0');
const s4 = readJson(S1);
const remaining = allCommands(s4).map(c => c.command).sort();
ok(JSON.stringify(remaining) === JSON.stringify([userPersonal, userComposite, userStop].sort()), `only user hooks remain (got ${JSON.stringify(remaining)})`);
for (const k of ['model', 'env', 'permissions', 'statusLine']) {
  ok(JSON.stringify(s4[k]) === JSON.stringify(original[k]), `top-level key "${k}" untouched by remove`);
}
ok(!fs.existsSync(STATE1), 'state file deleted by remove');
ok(backups(ROOT1).length === 3, `backup before remove (count ${backups(ROOT1).length})`);
const r4b = runJson(['remove', '--root', ROOT1, '--manifest', M2], env1);
ok(r4b.json && r4b.json.status === 'unchanged' && backups(ROOT1).length === 3, 'second remove is a no-op');

// ---------------------------------------------------------------------------
section('5. root == $HOME/.claude: ~ and $HOME forms count as present');
const T5 = sandbox();
const HOME5 = path.join(T5, 'home');
const ROOT5 = path.join(HOME5, '.claude');
fs.mkdirSync(path.join(ROOT5, 'hooks'), { recursive: true });
const env5 = { HOME: HOME5, USERPROFILE: HOME5, AGENCY_HOME: '', CLAUDE_CONFIG_DIR: '' };
const tilde = 'bash ~/.claude/hooks/gate-guard.sh';
const dollar = 'bash $HOME/.claude/hooks/secret-scanner.sh';
const braced = 'bash ${HOME}/.claude/hooks/track-edits.sh';
const weUser = 'bash ~/.claude/hooks/write-evidence.sh';
const S5 = path.join(ROOT5, 'settings.json');
fs.writeFileSync(S5, JSON.stringify({
  hooks: {
    PreToolUse: [
      { matcher: 'Edit|Write', hooks: [{ type: 'command', command: tilde }] },
      { matcher: 'Bash', hooks: [{ type: 'command', command: dollar }] },
    ],
    PostToolUse: [
      { matcher: 'Edit|Write', hooks: [{ type: 'command', command: braced }] },
      { matcher: 'Write|Edit', hooks: [{ type: 'command', command: weUser }] },
    ],
  },
}, null, 2) + '\n');
const r5 = runJson(['sync', '--root', ROOT5], env5);
ok(r5.code === 0, 'sync exit 0');
const s5 = readJson(S5);
ok(countCmd(s5, tilde) === 1 && countCmd(s5, hm.renderCommand('bash {root}/hooks/gate-guard.sh', ROOT5)) === 0, '~/.claude gate-guard kept as-is, no absolute duplicate');
ok(countCmd(s5, dollar) === 1 && countCmd(s5, hm.renderCommand('bash {root}/hooks/secret-scanner.sh', ROOT5)) === 0, '$HOME/.claude form recognised');
ok(countCmd(s5, braced) === 1 && countCmd(s5, hm.renderCommand('bash {root}/hooks/track-edits.sh', ROOT5)) === 0, '${HOME}/.claude form recognised');
const we = allCommands(s5).filter(c => /write-evidence\.sh/.test(c.command));
ok(we.length === 1 && we[0].matcher === 'Write|Edit' && we[0].command === weUser, 'user-placed write-evidence left under its own matcher, not duplicated');
ok(r5.json && !r5.json.added.some(a => ['gate-guard', 'secret-scanner', 'track-edits', 'write-evidence'].includes(a.id)), 'present hooks not reported as added');
const r5b = runJson(['remove', '--root', ROOT5], env5);
ok(r5b.code === 0 && allCommands(readJson(S5)).length === 0, 'remove recognises ~ / $HOME forms as ours');

// ---------------------------------------------------------------------------
section('6. malformed settings.json is never written');
const T6 = sandbox();
const ROOT6 = path.join(T6, 'root');
fs.mkdirSync(ROOT6, { recursive: true });
const S6 = path.join(ROOT6, 'settings.json');
fs.writeFileSync(S6, '{ "model": "opus", ');
const sha6 = sha(S6);
const r6 = run(['sync', '--root', ROOT6], { HOME: T6, USERPROFILE: T6 });
ok(r6.code === 1, `exit 1 on malformed JSON (got ${r6.code})`);
ok(sha(S6) === sha6, 'malformed file untouched');
ok(backups(ROOT6).length === 0, 'no backup for a refused write');
ok(/agency hooks sync/.test(r6.out) && /hooks-merge\.js" sync --root/.test(r6.out), 'manual commands printed');

// ---------------------------------------------------------------------------
section('7. AGENCY_NO_HOOKS=1 skips automatic wiring only');
const T7 = sandbox();
const ROOT7 = path.join(T7, 'root');
fs.mkdirSync(ROOT7, { recursive: true });
const S7 = path.join(ROOT7, 'settings.json');
const r7 = run(['sync', '--root', ROOT7, '--auto'], { HOME: T7, USERPROFILE: T7, AGENCY_NO_HOOKS: '1' });
ok(r7.code === 0 && !fs.existsSync(S7), 'auto sync with AGENCY_NO_HOOKS=1 writes nothing');
ok(/AGENCY_NO_HOOKS/.test(r7.out) && /agency hooks sync/.test(r7.out), 'skip message names the opt-out and the manual command');
const r7b = run(['sync', '--root', ROOT7], { HOME: T7, USERPROFILE: T7, AGENCY_NO_HOOKS: '1' });
ok(r7b.code === 0 && fs.existsSync(S7), 'explicit sync still works with AGENCY_NO_HOOKS=1');

// ---------------------------------------------------------------------------
section('8. message');
const T8 = sandbox();
const ROOT8 = path.join(T8, 'root');
fs.mkdirSync(ROOT8, { recursive: true });
const r8 = run(['sync', '--root', ROOT8], { HOME: T8, USERPROFILE: T8 });
ok(/Restart Claude Code to activate the hooks\./.test(r8.out), 'change block ends with the restart line');
ok(manifest.hooks.every(h => r8.out.includes(h.id) && r8.out.includes(h.purpose)), 'every added hook printed with its purpose');
const r8b = run(['sync', '--root', ROOT8], { HOME: T8, USERPROFILE: T8 });
ok(r8b.out.trim() === `Hooks: ${manifest.hooks.length} wired, up to date`, `quiet line when nothing changed (got "${r8b.out.trim()}")`);

// ---------------------------------------------------------------------------
section('9. pure functions: Windows forms, quoting, no bash');
const winRoot = 'C:\\Users\\x\\.claude';
ok(hm.renderCommand('bash {root}/hooks/gate-guard.sh', winRoot) === 'bash C:/Users/x/.claude/hooks/gate-guard.sh', 'Windows root rendered with forward slashes');
for (const form of ['bash C:/Users/x/.claude/hooks/gate-guard.sh', 'bash C:\\Users\\x\\.claude\\hooks\\gate-guard.sh', 'bash c:/users/x/.claude/hooks/gate-guard.sh', 'bash /c/Users/x/.claude/hooks/gate-guard.sh']) {
  ok(hm.normaliseCommand(form, { root: winRoot, home: 'C:\\Users\\x', platform: 'win32' }) === 'bash {root}/hooks/gate-guard.sh', `win32 form recognised: ${form}`);
}
ok(hm.normaliseCommand('bash ~/.claude/hooks/gate-guard.sh', { root: winRoot, home: 'C:\\Users\\x', platform: 'win32' }) === 'bash {root}/hooks/gate-guard.sh', 'win32 ~/.claude form recognised for the default root');
ok(hm.normaliseCommand('bash ~/.claude/hooks/gate-guard.sh', { root: '/opt/custom', home: '/home/u', platform: 'linux' }) !== 'bash {root}/hooks/gate-guard.sh', '~/.claude NOT ours when root is a custom path');
const spaced = '/tmp/a b/.claude';
const q = hm.renderCommand('bash {root}/hooks/session-end.sh && bash {root}/hooks/batch-check.sh', spaced);
ok(q === 'bash "/tmp/a b/.claude/hooks/session-end.sh" && bash "/tmp/a b/.claude/hooks/batch-check.sh"', `root with a space is quoted per path (got ${q})`);
ok(hm.normaliseCommand(q, { root: spaced, home: '/home/u', platform: 'linux' }) === 'bash {root}/hooks/session-end.sh && bash {root}/hooks/batch-check.sh', 'quoted form normalises back');
const T9 = sandbox();
const res9 = hm.syncHooks({ root: path.join(T9, 'root'), platform: 'win32', bashAvailable: () => false });
ok(res9.status === 'skipped' && res9.reason === 'no-bash', `win32 without bash -> skipped/no-bash (got ${res9.status}/${res9.reason})`);
ok(!fs.existsSync(path.join(T9, 'root', 'settings.json')), 'nothing written when bash is missing');

// ---------------------------------------------------------------------------
section('10. install.sh end to end');
if (process.platform === 'win32') {
  console.log('  skip install.sh e2e on win32 (covered by the install.ps1 job)');
} else {
  const T10 = sandbox();
  const env10 = Object.assign({}, process.env, { HOME: path.join(T10, 'home'), AGENCY_HOME: path.join(T10, 'root'), AGENCY_NO_HOOKS: '' });
  fs.mkdirSync(env10.HOME, { recursive: true });
  const i1 = spawnSync('bash', [path.join(REPO, 'install.sh')], { encoding: 'utf8', env: env10, cwd: T10 });
  const S10 = path.join(env10.AGENCY_HOME, 'settings.json');
  ok(i1.status === 0, `install.sh exit 0 (got ${i1.status})`);
  ok(fs.existsSync(S10), 'fresh install created settings.json');
  if (fs.existsSync(S10)) {
    const s10 = readJson(S10);
    ok(manifest.hooks.every(h => countCmd(s10, hm.renderCommand(h.command, env10.AGENCY_HOME)) === 1), 'every manifest hook wired once by install.sh');
  }
  ok(/Restart Claude Code to activate the hooks\./.test(i1.stdout), 'install.sh printed the hooks block');
  const sha10 = fs.existsSync(S10) ? sha(S10) : '';
  const i2 = spawnSync('bash', [path.join(REPO, 'install.sh')], { encoding: 'utf8', env: env10, cwd: T10 });
  ok(i2.status === 0, 'second install.sh exit 0');
  ok(fs.existsSync(S10) && sha(S10) === sha10, 'second install leaves settings.json byte-identical');
  ok(backups(env10.AGENCY_HOME).length === 0, 'no backup on a no-op install');
  ok(new RegExp(`Hooks: ${manifest.hooks.length} wired, up to date`).test(i2.stdout), 'second install printed the quiet line');
  const i3 = spawnSync('bash', [path.join(REPO, 'install.sh')], { encoding: 'utf8', env: Object.assign({}, env10, { AGENCY_NO_HOOKS: '1' }), cwd: T10 });
  ok(i3.status === 0 && /agency hooks sync/.test(i3.stdout), 'install.sh with AGENCY_NO_HOOKS=1 prints the manual command');
}

console.log(`\n${passes} passed, ${failures} failed`);
if (failures) { console.log('FAIL: check-hooks-merge'); process.exit(1); }
console.log('OK: check-hooks-merge');
