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
//  10. Windows bash resolver: env > git --exec-path > %ProgramFiles% >
//      %LOCALAPPDATA% > PATH, WSL launcher skipped, none -> skipped with the
//      Git for Windows instruction + `agency hooks sync`, non-standard -> hint
//  11. deleted-hook opt-out: a hook the agency wired and the user then removed
//      is marked disabled in the state file, never re-added, and reported on
//      every sync; `hooks disable|enable <id>`; unknown/retired id -> exit 1;
//      a manifest command change is an update, not a deletion; remove still
//      removes only ours
//  12. install.sh end to end: fresh root -> settings.json created with hooks;
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
section('10. Windows bash resolver (order, WSL skipped, no-bash message, hint)');
{
  const have = (...paths) => { const set = new Set(paths.map(x => x.toLowerCase())); return p => set.has(String(p).toLowerCase()); };
  const ENVP = 'D:\\custom\\bash.exe';
  const EXEC = 'D:\\tools\\Git\\bin\\bash.exe';
  const PF = 'C:\\Program Files\\Git\\bin\\bash.exe';
  const LA = 'C:\\Users\\u\\AppData\\Local\\Programs\\Git\\bin\\bash.exe';
  const PATHB = 'E:\\portable\\bin\\bash.exe';
  const SYS32 = 'C:\\Windows\\System32\\bash.exe';
  const WAPPS = 'C:\\Users\\u\\AppData\\Local\\Microsoft\\WindowsApps\\bash.exe';
  const baseEnv = { CLAUDE_CODE_GIT_BASH_PATH: ENVP, ProgramFiles: 'C:\\Program Files', LOCALAPPDATA: 'C:\\Users\\u\\AppData\\Local', WINDIR: 'C:\\Windows' };
  const deps = (over) => Object.assign({
    env: baseEnv,
    exists: have(ENVP, EXEC, PF, LA, PATHB, SYS32, WAPPS),
    gitExecPath: () => 'D:/tools/Git/mingw64/libexec/git-core',
    pathLookup: () => [SYS32, WAPPS, PATHB],
  }, over || {});
  ok(typeof hm.resolveGitBash === 'function' && typeof hm.locateGitBash === 'function', 'resolveGitBash and locateGitBash are exported');
  if (typeof hm.resolveGitBash === 'function') {
    let r = hm.resolveGitBash(deps());
    ok(r && r.source === 'env' && r.path === ENVP, `1. CLAUDE_CODE_GIT_BASH_PATH wins when the file exists (got ${JSON.stringify(r)})`);
    const noEnv = Object.assign({}, baseEnv); delete noEnv.CLAUDE_CODE_GIT_BASH_PATH;
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have(EXEC, PF, LA, PATHB, SYS32, WAPPS) }));
    ok(r && r.source === 'git-exec-path' && r.path === EXEC, `2. git --exec-path (3 levels up, Git\\bin\\bash.exe) is next (got ${JSON.stringify(r)})`);
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have('D:\\tools\\Git\\mingw64\\bin\\bash.exe', PF), gitExecPath: () => 'D:/tools/Git/mingw64/libexec/git-core' }));
    ok(r && r.source === 'git-exec-path' && r.path === 'D:\\tools\\Git\\mingw64\\bin\\bash.exe', `2b. exec-path 2 levels up is also checked (got ${JSON.stringify(r)})`);
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have('D:\\tools\\bin\\bash.exe'), gitExecPath: () => 'D:/tools/Git/mingw64/libexec/git-core', pathLookup: () => [] }));
    ok(r && r.source === 'git-exec-path' && r.path === 'D:\\tools\\bin\\bash.exe', `2c. exec-path 4 levels up is also checked (got ${JSON.stringify(r)})`);
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have(PF, LA, PATHB), gitExecPath: () => '/mingw64/libexec/git-core' }));
    ok(r && r.source === 'program-files' && r.path === PF, `3. MSYS-style exec-path is skipped, %ProgramFiles%\\Git\\bin\\bash.exe next (got ${JSON.stringify(r)})`);
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have(LA, PATHB), gitExecPath: () => null }));
    ok(r && r.source === 'local-appdata' && r.path === LA, `4. %LOCALAPPDATA%\\Programs\\Git\\bin\\bash.exe next (got ${JSON.stringify(r)})`);
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have(PATHB, SYS32, WAPPS), gitExecPath: () => null }));
    ok(r && r.source === 'path' && r.path === PATHB, `5. PATH lookup is last, skipping System32 and WindowsApps bash (got ${JSON.stringify(r)})`);
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have(SYS32, WAPPS), gitExecPath: () => null, pathLookup: () => [SYS32, WAPPS] }));
    ok(r === null, `6. only the WSL launcher on PATH (System32 + WindowsApps) -> null (got ${JSON.stringify(r)})`);
    r = hm.resolveGitBash(deps({ env: noEnv, exists: have(), gitExecPath: () => null, pathLookup: () => [] }));
    ok(r === null, '7. nothing anywhere -> null');
    const loc = hm.locateGitBash(deps({ env: Object.assign({}, noEnv, { CLAUDE_CODE_GIT_BASH_PATH: 'Z:\\gone\\bash.exe' }), exists: have(PF), gitExecPath: () => null }));
    ok(loc.found && loc.found.source === 'program-files', '8. CLAUDE_CODE_GIT_BASH_PATH pointing at a missing file falls through to the next step');
    ok(loc.notes.some(n => /CLAUDE_CODE_GIT_BASH_PATH/.test(n) && /Z:\\gone/.test(n)), '8b. ... and says so in notes');
    // sync wiring: none found -> skipped with reason + message
    const T11 = sandbox();
    const none = { env: {}, exists: have(), gitExecPath: () => null, pathLookup: () => [] };
    const sk = hm.syncHooks({ root: path.join(T11, 'root'), platform: 'win32', bashDeps: none });
    ok(sk.status === 'skipped' && sk.reason === 'no-bash', `9. none found -> skipped/no-bash (got ${sk.status}/${sk.reason})`);
    ok(!fs.existsSync(path.join(T11, 'root', 'settings.json')), '9b. nothing written when no bash');
    const msg = hm.formatResult(sk).join('\n');
    ok(/https:\/\/git-scm\.com\/downloads\/win/.test(msg) && /then run: agency hooks sync/.test(msg), '9c. message names the Git for Windows download and "then run: agency hooks sync"');
    ok(/Restart Claude Code/.test(msg), '9d. message ends with the restart line');
    // sync wiring: found via PATH (non-standard) -> wired, hint printed
    const T12 = sandbox();
    const viaPath = Object.assign({}, none, { exists: have(PATHB), pathLookup: () => [SYS32, PATHB] });
    const wired = hm.syncHooks({ root: path.join(T12, 'root'), platform: 'win32', bashDeps: viaPath });
    ok(wired.status === 'changed' && wired.bash && wired.bash.source === 'path', `10. found via PATH -> wired (got ${wired.status}, ${JSON.stringify(wired.bash)})`);
    const wmsg = hm.formatResult(wired).join('\n');
    ok(wmsg.includes('CLAUDE_CODE_GIT_BASH_PATH') && wmsg.includes(JSON.stringify(PATHB)), '10b. non-standard location -> one-line CLAUDE_CODE_GIT_BASH_PATH hint with the path');
    ok(!fs.readFileSync(path.join(T12, 'root', 'settings.json'), 'utf8').includes('CLAUDE_CODE_GIT_BASH_PATH'), '10c. the hint is printed, settings.json env is never written');
    const T13 = sandbox();
    const viaPf = Object.assign({}, none, { env: baseEnv, exists: have(PF) });
    const w2 = hm.syncHooks({ root: path.join(T13, 'root'), platform: 'win32', bashDeps: Object.assign({}, viaPf, { env: Object.assign({}, baseEnv, { CLAUDE_CODE_GIT_BASH_PATH: '' }) }) });
    ok(w2.status === 'changed' && w2.bash && w2.bash.source === 'program-files' && !hm.formatResult(w2).join('\n').includes('CLAUDE_CODE_GIT_BASH_PATH'), '10d. standard location -> wired, no hint');
    // overrides still work
    const T14 = sandbox();
    const forced = hm.syncHooks({ root: path.join(T14, 'root'), platform: 'win32', force: true, bashDeps: none });
    ok(forced.status === 'changed', `11. --force wires without bash (got ${forced.status})`);
    const T15 = sandbox();
    const inj = hm.syncHooks({ root: path.join(T15, 'root'), platform: 'win32', bashAvailable: () => true, bashDeps: none });
    ok(inj.status === 'changed', `11b. opts.bashAvailable override still wins (got ${inj.status})`);
  }
}

// ---------------------------------------------------------------------------
section('11. deleted-hook opt-out, agency hooks disable|enable');
{
  const T = sandbox();
  const ROOT = path.join(T, 'root');
  const HOME = path.join(T, 'home');
  fs.mkdirSync(path.join(ROOT, 'hooks'), { recursive: true });
  fs.mkdirSync(HOME, { recursive: true });
  const env = { HOME, USERPROFILE: HOME, AGENCY_HOME: ROOT };
  const S = path.join(ROOT, 'settings.json');
  const STATE = path.join(ROOT, 'hooks', '.agency-hooks-state.json');
  const Rf = ROOT.split(path.sep).join('/');
  const userHook = `bash ${Rf}/hooks/my-personal.sh`;
  const userStopHook = 'sh ~/.agent-memory/heartbeat.sh stop';
  fs.writeFileSync(S, JSON.stringify({
    model: 'opus',
    hooks: {
      PreToolUse: [{ matcher: 'Bash', hooks: [{ type: 'command', command: userHook }] }],
      Stop: [{ matcher: '', hooks: [{ type: 'command', command: userStopHook }] }],
    },
  }, null, 2) + '\n');
  const cmdOf = id => hm.renderCommand(manifest.hooks.find(h => h.id === id).command, ROOT);
  const ids = manifest.hooks.map(h => h.id);
  const SKIP = id => `skipped ${id} (you removed it; agency hooks enable ${id} to restore)`;
  // delete every entry of `id` from settings.json, by hand
  const deleteByHand = id => {
    const c = cmdOf(id);
    const s = readJson(S);
    for (const ev of Object.keys(s.hooks)) {
      for (const g of s.hooks[ev]) g.hooks = g.hooks.filter(h => h.command !== c);
      s.hooks[ev] = s.hooks[ev].filter(g => g.hooks.length > 0);
      if (s.hooks[ev].length === 0) delete s.hooks[ev];
    }
    fs.writeFileSync(S, JSON.stringify(s, null, 2) + '\n');
  };
  const userIntact = () => {
    const c = allCommands(readJson(S)).map(x => x.command);
    return c.includes(userHook) && c.includes(userStopHook);
  };

  // a. first-ever install adds everything and records nothing as disabled
  const a = run(['sync', '--root', ROOT], env);
  ok(a.code === 0 && ids.every(id => countCmd(readJson(S), cmdOf(id)) === 1), 'a. first-ever sync (no state) wires every manifest hook');
  ok(!/skipped /.test(a.out) && !('disabled' in readJson(STATE)), 'a. ... and nothing is skipped or recorded as disabled');

  // b. delete by hand -> sync keeps it gone and says so, every time
  deleteByHand('gate-guard');
  const bk0 = backups(ROOT).length;
  const b1 = run(['sync', '--root', ROOT], env);
  ok(b1.code === 0 && countCmd(readJson(S), cmdOf('gate-guard')) === 0, 'b. hook deleted by hand stays gone after sync');
  ok(b1.out.includes(SKIP('gate-guard')), `b. sync prints the skipped line (got ${JSON.stringify(b1.out.slice(0, 160))})`);
  ok(readJson(STATE).disabled && readJson(STATE).disabled['gate-guard'] && !readJson(STATE).hooks['gate-guard'], 'b. state: gate-guard disabled, no longer "wired"');
  const b1j = runJson(['sync', '--root', ROOT], env);
  ok(b1j.json && b1j.json.skipped && b1j.json.skipped.some(x => x.id === 'gate-guard'), 'b. --json lists it under "skipped"');
  ok(backups(ROOT).length === bk0, 'b. marking it disabled changes state only: no settings.json backup');
  const b2 = run(['sync', '--root', ROOT], env);
  ok(countCmd(readJson(S), cmdOf('gate-guard')) === 0 && b2.out.includes(SKIP('gate-guard')), 'b. second sync: still gone, message printed again');
  const b3 = run(['sync', '--root', ROOT, '--auto'], env);
  ok(countCmd(readJson(S), cmdOf('gate-guard')) === 0 && b3.out.includes(SKIP('gate-guard')), 'b. --auto (installer / init / upgrade path) honours it too');
  ok(/Hooks: \d+ wired, up to date/.test(b2.out), 'b. the quiet "up to date" line is kept');
  ok(userIntact(), 'b. user hooks untouched');

  // c. the composite Stop chain is one id too
  deleteByHand('stop-chain');
  const c1 = run(['sync', '--root', ROOT], env);
  ok(countCmd(readJson(S), cmdOf('stop-chain')) === 0 && c1.out.includes(SKIP('stop-chain')), 'c. composite stop-chain deleted by hand stays gone');

  // d. enable brings one back
  const d1 = runJson(['enable', 'gate-guard', '--root', ROOT], env);
  ok(d1.code === 0 && countCmd(readJson(S), cmdOf('gate-guard')) === 1, `d. enable gate-guard wires it now (exit ${d1.code})`);
  ok(!(readJson(STATE).disabled || {})['gate-guard'] && readJson(STATE).hooks['gate-guard'], 'd. state: gate-guard wired again, not disabled');
  ok(countCmd(readJson(S), cmdOf('stop-chain')) === 0, 'd. enabling one hook does not resurrect the other disabled one');
  const d2 = run(['sync', '--root', ROOT], env);
  ok(countCmd(readJson(S), cmdOf('gate-guard')) === 1 && !d2.out.includes(SKIP('gate-guard')) && d2.out.includes(SKIP('stop-chain')), 'd. after enable: sync keeps gate-guard, still skips stop-chain');
  const d3 = run(['enable', 'gate-guard', '--root', ROOT], env);
  ok(d3.code === 0 && /already enabled/.test(d3.out) && countCmd(readJson(S), cmdOf('gate-guard')) === 1, 'd. enable on an enabled id: exit 0, "already enabled", no duplicate');
  const d4 = run(['enable', 'stop-chain', '--root', ROOT], env);
  ok(d4.code === 0 && countCmd(readJson(S), cmdOf('stop-chain')) === 1, 'd. enable stop-chain restores the composite command');

  // e. disable removes our entry, marks it disabled, survives sync
  const e1 = runJson(['disable', 'secret-scanner', '--root', ROOT], env);
  ok(e1.code === 0 && countCmd(readJson(S), cmdOf('secret-scanner')) === 0, `e. disable secret-scanner removes our entry (exit ${e1.code})`);
  ok(readJson(STATE).disabled && readJson(STATE).disabled['secret-scanner'] && !readJson(STATE).hooks['secret-scanner'], 'e. state: secret-scanner disabled');
  const e2 = run(['sync', '--root', ROOT], env);
  ok(countCmd(readJson(S), cmdOf('secret-scanner')) === 0 && e2.out.includes(SKIP('secret-scanner')), 'e. sync after disable: stays gone, message printed');
  const bkE = backups(ROOT).length;
  const e3 = run(['disable', 'secret-scanner', '--root', ROOT], env);
  ok(e3.code === 0 && /already disabled/.test(e3.out) && backups(ROOT).length === bkE, 'e. disable twice: exit 0, "already disabled", no new backup');
  ok(userIntact(), 'e. user hooks untouched by disable');

  // f. unknown / retired id
  const settingsBefore = sha(S);
  const stateBefore = sha(STATE);
  const f1 = run(['disable', 'no-such-hook', '--root', ROOT], env);
  ok(f1.code === 1 && ids.every(id => f1.out.includes(id)) && /no-such-hook/.test(f1.out), `f. disable unknown id: exit 1, names it and lists every valid id (exit ${f1.code})`);
  const f2 = run(['enable', 'no-such-hook', '--root', ROOT], env);
  ok(f2.code === 1 && ids.every(id => f2.out.includes(id)), 'f. enable unknown id: exit 1 + valid ids');
  const mRet = JSON.parse(JSON.stringify(manifest));
  const gone = mRet.hooks.find(h => h.id === 'track-edits');
  mRet.hooks = mRet.hooks.filter(h => h.id !== 'track-edits');
  mRet.retired = (mRet.retired || []).concat([{ id: gone.id, event: gone.event, command: gone.command }]);
  const MRET = path.join(T, 'hooks-retired.json');
  fs.writeFileSync(MRET, JSON.stringify(mRet, null, 2) + '\n');
  const f3 = run(['enable', 'track-edits', '--root', ROOT, '--manifest', MRET], env);
  ok(f3.code === 1 && /retired/.test(f3.out), 'f. enable a retired id: exit 1, says retired');
  const f4 = run(['disable', 'track-edits', '--root', ROOT, '--manifest', MRET], env);
  ok(f4.code === 1 && /retired/.test(f4.out), 'f. disable a retired id: exit 1, says retired');
  const f5 = run(['disable', '--root', ROOT], env);
  ok(f5.code !== 0 && ids.every(id => f5.out.includes(id)), 'f. disable without an id: usage error + valid ids');
  ok(sha(S) === settingsBefore && sha(STATE) === stateBefore, 'f. errors touch neither settings.json nor state');

  // g. a manifest command change is an UPDATE, not a deletion
  const mUpd = JSON.parse(JSON.stringify(manifest));
  const sc = mUpd.hooks.find(h => h.id === 'stop-chain');
  const oldStop = sc.command;
  sc.command = 'bash {root}/hooks/session-end.sh && bash {root}/hooks/batch-check.sh';
  const MUPD = path.join(T, 'hooks-updated.json');
  fs.writeFileSync(MUPD, JSON.stringify(mUpd, null, 2) + '\n');
  ok(countCmd(readJson(S), cmdOf('stop-chain')) === 1, 'g. precondition: old stop-chain command is wired');
  const g1 = runJson(['sync', '--root', ROOT, '--manifest', MUPD], env);
  ok(g1.json && g1.json.updated.some(u => u.id === 'stop-chain'), 'g. changed command is reported as updated');
  ok(countCmd(readJson(S), hm.renderCommand(sc.command, ROOT)) === 1 && countCmd(readJson(S), hm.renderCommand(oldStop, ROOT)) === 0, 'g. old command replaced by the new one');
  ok(!(readJson(STATE).disabled || {})['stop-chain'] && !g1.out.includes('skipped stop-chain'), 'g. ... and stop-chain is NOT marked disabled');
  runJson(['sync', '--root', ROOT], env); // back to the real manifest
  // deleted AND changed in the same release: neither command present -> deleted
  deleteByHand('stop-chain');
  const g2 = run(['sync', '--root', ROOT, '--manifest', MUPD], env);
  ok(g2.out.includes(SKIP('stop-chain')) && countCmd(readJson(S), hm.renderCommand(sc.command, ROOT)) === 0, 'g. deleted by hand, then the manifest changes its command: still opted out');
  run(['enable', 'stop-chain', '--root', ROOT], env);

  // h. wiring it back by hand clears the opt-out
  run(['disable', 'track-edits', '--root', ROOT], env);
  {
    const s = readJson(S);
    s.hooks.PostToolUse.push({ matcher: 'Edit|Write', hooks: [{ type: 'command', command: cmdOf('track-edits') }] });
    fs.writeFileSync(S, JSON.stringify(s, null, 2) + '\n');
  }
  const h1 = run(['sync', '--root', ROOT], env);
  ok(countCmd(readJson(S), cmdOf('track-edits')) === 1 && !h1.out.includes('skipped track-edits') && !(readJson(STATE).disabled || {})['track-edits'], 'h. user re-adds a disabled hook by hand: kept once, no longer disabled');

  // i. a disabled id the manifest no longer ships is dropped from state
  run(['disable', 'startup-sync', '--root', ROOT], env);
  const mDrop = JSON.parse(JSON.stringify(manifest));
  mDrop.hooks = mDrop.hooks.filter(h => h.id !== 'startup-sync');
  const MDROP = path.join(T, 'hooks-dropped.json');
  fs.writeFileSync(MDROP, JSON.stringify(mDrop, null, 2) + '\n');
  run(['sync', '--root', ROOT, '--manifest', MDROP], env);
  ok(!(readJson(STATE).disabled || {})['startup-sync'], 'i. disabled id no longer in the manifest is dropped from state');

  // j. remove still removes only ours, with disabled ids around
  run(['disable', 'spawn-gate', '--root', ROOT], env);
  const j1 = runJson(['remove', '--root', ROOT], env);
  const left = allCommands(readJson(S)).map(c => c.command).sort();
  ok(j1.code === 0 && JSON.stringify(left) === JSON.stringify([userHook, userStopHook].sort()), `j. remove with disabled ids: only user hooks remain (got ${JSON.stringify(left)})`);
  ok(readJson(S).model === 'opus' && !fs.existsSync(STATE), 'j. other keys intact, state file deleted');
  const j2 = run(['sync', '--root', ROOT], env);
  ok(ids.every(id => countCmd(readJson(S), cmdOf(id)) === 1) && !/skipped /.test(j2.out), 'j. sync after remove is a first-ever install again: everything wired');

  // k. installer end to end keeps a deleted hook gone
  if (process.platform !== 'win32') {
    const T2 = sandbox();
    const env2 = Object.assign({}, process.env, { HOME: path.join(T2, 'home'), AGENCY_HOME: path.join(T2, 'root'), AGENCY_NO_HOOKS: '' });
    fs.mkdirSync(env2.HOME, { recursive: true });
    spawnSync('bash', [path.join(REPO, 'install.sh')], { encoding: 'utf8', env: env2, cwd: T2 });
    const S2 = path.join(env2.AGENCY_HOME, 'settings.json');
    const s2 = readJson(S2);
    const c2 = hm.renderCommand(manifest.hooks.find(h => h.id === 'write-evidence').command, env2.AGENCY_HOME);
    for (const ev of Object.keys(s2.hooks)) for (const g of s2.hooks[ev]) g.hooks = g.hooks.filter(h => h.command !== c2);
    fs.writeFileSync(S2, JSON.stringify(s2, null, 2) + '\n');
    const k = spawnSync('bash', [path.join(REPO, 'install.sh')], { encoding: 'utf8', env: env2, cwd: T2 });
    ok(k.status === 0 && countCmd(readJson(S2), c2) === 0, 'k. install.sh run again does not re-add a hook the user deleted');
    ok(k.stdout.includes(SKIP('write-evidence')), 'k. ... and prints the skipped line');
  }

  // l. the CLI entry point and help text
  const agencyJs = path.join(REPO, 'cli', 'bin', 'agency.js');
  const T3 = sandbox();
  const env3 = Object.assign({}, process.env, { HOME: path.join(T3, 'home'), AGENCY_HOME: path.join(T3, 'root'), AGENCY_NO_HOOKS: '' });
  fs.mkdirSync(env3.HOME, { recursive: true });
  const l1 = spawnSync(process.execPath, [agencyJs, 'hooks', 'sync'], { encoding: 'utf8', env: env3 });
  const l2 = spawnSync(process.execPath, [agencyJs, 'hooks', 'disable', 'loop-detector'], { encoding: 'utf8', env: env3 });
  const s3 = readJson(path.join(env3.AGENCY_HOME, 'settings.json'));
  ok(l1.status === 0 && l2.status === 0 && countCmd(s3, hm.renderCommand(manifest.hooks.find(h => h.id === 'loop-detector').command, env3.AGENCY_HOME)) === 0, 'l. agency hooks disable <id> works through the CLI');
  const l3 = spawnSync(process.execPath, [agencyJs, 'hooks', 'enable', 'nope'], { encoding: 'utf8', env: env3 });
  ok(l3.status === 1, 'l. agency hooks enable <unknown>: exit 1');
  const l4 = spawnSync(process.execPath, [agencyJs, 'help'], { encoding: 'utf8', env: env3 });
  ok(/agency hooks disable <id>/.test(l4.stdout) && /agency hooks enable <id>/.test(l4.stdout), 'l. agency help lists hooks disable|enable');
  const l5 = spawnSync(process.execPath, [agencyJs, 'hooks'], { encoding: 'utf8', env: env3 });
  ok(/hooks disable <id>/.test(l5.stdout) && /hooks enable <id>/.test(l5.stdout), 'l. agency hooks (no subcommand) usage lists disable|enable');
}

// ---------------------------------------------------------------------------
section('12. install.sh end to end');
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
