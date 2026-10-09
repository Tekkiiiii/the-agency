#!/usr/bin/env node
// check-retired-prune.js — regression guard for cli/lib/retired-prune.js, the
// shared step that deletes files the repo RETIRED (skills/agents/runbooks/core
// paths shipped once, deleted since) from an installed agency root on
// `agency upgrade`, install.sh, install.ps1 and `agency prune`.
//
// What matters most: it only ever touches paths listed in retired-manifest.json,
// never a file the user edited unless they chose delete, never the repo checkout
// itself, and never a git work tree unless forced.
//
// Hermetic: temp dirs, a fake repoDir with its own tiny retired-manifest.json,
// and injected now / env / isTTY / prompt / force. The real home is never read.
//
// Cases:
//   1  unmodified retired skill file removed, its now-empty skill dir removed
//   2  edited retired file archived to archive/agency-retired-<date>/<path>, kept off the live tree
//   3  user-made skill (not in manifest) untouched, also inside a retired skill's dir (dir stays)
//   4  rerun is a no-op ('unchanged')
//   5  CRLF copy of a shipped file counts as unmodified (removed)
//   6  dry-run changes nothing
//   7  root == repoDir refused even with force (also through a symlink)
//   8  git work tree skipped; pruned with force
//   9  retired agents / runbooks / core paths handled the same
//  10  symlink file and symlinked skills/ dir skipped
//  11  missing manifest -> skipped 'no-manifest'
//  12  archive name collision -> .1 suffix
//  13  no TTY defaults to archive and says how to choose
//  14  retired:'delete' deletes edited files
//  15  the "You changed these" note lists every edited item (kind name  path)
//  16  ask + TTY with scripted a / d / c answers
//  17  log file written
//  18  env AGENCY_RETIRED honoured; invalid answer -> archive
//  19  CLI: json, --retired=delete, exit codes
//  20  autoPrune never throws, prints the summary
//  21  manifest paths that escape the four trees are ignored
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const LIB = path.join(REPO, 'cli', 'lib', 'retired-prune.js');

let passed = 0;
let failed = 0;
const ok = (name) => { passed++; console.log(`ok   ${name}`); };
const bad = (name, why) => { failed++; console.log(`FAIL ${name}${why ? ` -- ${why}` : ''}`); };
const check = (name, cond, why) => (cond ? ok(name) : bad(name, why));

let lib = null;
try { lib = require(LIB); } catch (e) { bad('load cli/lib/retired-prune.js', e.message.split('\n')[0]); }

const tmps = [];
const mk = (p) => { const d = fs.mkdtempSync(path.join(os.tmpdir(), `ta-rp-${p}-`)); tmps.push(d); return fs.realpathSync(d); };
const sha = (s) => crypto.createHash('sha256').update(String(s).replace(/\r\n/g, '\n')).digest('hex');
const put = (root, rel, body) => { const f = path.join(root, rel); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, body); return f; };
const exists = (f) => { try { fs.lstatSync(f); return true; } catch { return false; } };
const cons = () => { const out = []; return { out, log: (...a) => out.push(a.join(' ')), error: (...a) => out.push(a.join(' ')) }; };
const NOW = new Date(2026, 9, 9, 12, 0, 0); // local 2026-10-09
const DATE = '2026-10-09';

// manifest: { 'skills/a/SKILL.md': ['v1 text', 'v2 text'] }
function fakeRepo(paths) {
  const dir = mk('repo');
  const m = { version: 1, generated_from: 'x', trees: ['skills/', 'agents/', 'runbooks/', 'core/'], paths: {} };
  for (const [p, vs] of Object.entries(paths)) m.paths[p] = vs.map(sha).sort();
  fs.writeFileSync(path.join(dir, 'retired-manifest.json'), JSON.stringify(m, null, 2));
  return dir;
}
const base = (repoDir, root, extra) => ({ root, repoDir, now: NOW, env: {}, isTTY: false, ...extra });
const run = (opts) => lib.pruneRetired(opts);

async function main() {
  if (!lib) return;

  // 1
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped v1', 'shipped v2'], 'skills/old-skill/notes.md': ['n1'] });
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'shipped v2');
    put(root, 'skills/old-skill/notes.md', 'n1');
    put(root, 'skills/keep/SKILL.md', 'mine');
    const c = cons();
    const r = await run(base(repo, root, { console: c }));
    check('1 unmodified retired files removed', r.status === 'changed' && r.removed.length === 2 && !exists(path.join(root, 'skills/old-skill/SKILL.md')), JSON.stringify(r));
    check('1 now-empty skill dir removed, skills/ root kept', !exists(path.join(root, 'skills/old-skill')) && exists(path.join(root, 'skills')) && r.dirsRemoved.length >= 1);
    check('1 unrelated skill intact', exists(path.join(root, 'skills/keep/SKILL.md')));
    check('1 summary line', lib.formatResult(r).some((l) => l === 'Retired files: 2 removed, 0 archived (modified)'), lib.formatResult(r).join(' | '));
  }
  // 2 + 13 + 15
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'], 'agents/specialized/gone-agent.md': ['a1'], 'runbooks/old.md': ['r1'], 'core/ORG-old.md': ['c1'] });
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'shipped\nplus my edit');
    put(root, 'agents/specialized/gone-agent.md', 'a1 edited');
    put(root, 'runbooks/old.md', 'r1 edited');
    put(root, 'core/ORG-old.md', 'c1 edited');
    const c = cons();
    const r = await run(base(repo, root, { console: c }));
    const dest = path.join(root, 'archive', `agency-retired-${DATE}`, 'skills/old-skill/SKILL.md');
    check('2 edited file archived under archive/agency-retired-<date>/<path>', r.archived.length === 4 && exists(dest) && fs.readFileSync(dest, 'utf8').includes('my edit'), JSON.stringify(r.archived));
    check('2 edited file not left in place', !exists(path.join(root, 'skills/old-skill/SKILL.md')) && r.removed.length === 0);
    check('2 archiveDir reported', r.archiveDir === path.join(root, 'archive', `agency-retired-${DATE}`), String(r.archiveDir));
    const text = c.out.join('\n');
    check('2 notice names the file and its archive path', /Retired file kept \(you edited it\): skills\/old-skill\/SKILL\.md -> archive\/agency-retired-\d{4}-\d\d-\d\d\/skills\/old-skill\/SKILL\.md/.test(lib.formatResult(r).join('\n')), lib.formatResult(r).join('\n'));
    check('13 no TTY defaults to archive and says how to choose', /Not asked \(no terminal\)\. Archived\. To choose: agency prune --retired=delete\|ask/.test(text), text);
    check('15 note heading and body', /^You changed these$/m.test(text) && text.includes('Upstream retired these files; your copy has local edits:'), text);
    check('15 note lists every edited item as "<kind> <name>  <path>"',
      text.includes('skill old-skill  skills/old-skill/SKILL.md') && text.includes('agent gone-agent  agents/specialized/gone-agent.md') &&
      text.includes('runbook old  runbooks/old.md') && text.includes('core ORG-old.md  core/ORG-old.md'), text);
    check('2 summary counts', lib.formatResult(r)[0] === 'Retired files: 0 removed, 4 archived (modified)', lib.formatResult(r)[0]);
    // 17 log
    const log = path.join(root, 'logs', 'agency-retired.log');
    const lt = exists(log) ? fs.readFileSync(log, 'utf8') : '';
    check('17 log written with note + a decision per item', /2026-10-09/.test(lt) && lt.includes('You changed these') && lt.includes('skills/old-skill/SKILL.md') && /archive/i.test(lt) && lt.split('\n').filter((l) => /->|archive/i.test(l)).length >= 4, lt);
  }
  // 3
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'] });
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'shipped');
    put(root, 'skills/old-skill/my-notes.md', 'user file in a retired skill dir');
    put(root, 'skills/my-skill/SKILL.md', 'user made');
    const r = await run(base(repo, root, {}));
    check('3 retired file removed', r.removed.length === 1 && !exists(path.join(root, 'skills/old-skill/SKILL.md')));
    check('3 user file inside retired skill dir untouched, dir kept', exists(path.join(root, 'skills/old-skill/my-notes.md')) && r.dirsRemoved.length === 0);
    check('3 user-made skill untouched', fs.readFileSync(path.join(root, 'skills/my-skill/SKILL.md'), 'utf8') === 'user made');
    // 4
    const r2 = await run(base(repo, root, {}));
    check('4 rerun is a no-op', r2.status === 'unchanged' && r2.removed.length === 0 && r2.archived.length === 0, JSON.stringify(r2));
    check('4 formatResult says none to remove', lib.formatResult(r2)[0] === 'Retired files: none to remove', lib.formatResult(r2)[0]);
  }
  // 5
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['line1\nline2\n'] });
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'line1\r\nline2\r\n');
    const r = await run(base(repo, root, {}));
    check('5 CRLF copy counts as unmodified', r.removed.length === 1 && r.archived.length === 0 && !exists(path.join(root, 'skills/old-skill')), JSON.stringify(r));
  }
  // 6
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'], 'skills/ed/SKILL.md': ['v'] });
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'shipped');
    put(root, 'skills/ed/SKILL.md', 'edited');
    const c = cons();
    const r = await run(base(repo, root, { dryRun: true, console: c, retired: 'delete' }));
    check('6 dry-run changes nothing on disk', exists(path.join(root, 'skills/old-skill/SKILL.md')) && exists(path.join(root, 'skills/ed/SKILL.md')) && !exists(path.join(root, 'archive')) && !exists(path.join(root, 'logs')));
    check('6 dry-run still reports what it would do', r.dryRun === true && r.removed.length >= 1, JSON.stringify(r));
  }
  // 7
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'] });
    put(repo, 'skills/old-skill/SKILL.md', 'shipped');
    const r = await run(base(repo, repo, { force: true }));
    check('7 root == repoDir refused even with force', r.status === 'skipped' && r.reason === 'repo-root' && exists(path.join(repo, 'skills/old-skill/SKILL.md')), JSON.stringify(r));
    const link = path.join(mk('lnk'), 'root');
    fs.symlinkSync(repo, link);
    const r2 = await run(base(repo, link, { force: true }));
    check('7 same through a symlink to repoDir', r2.status === 'skipped' && r2.reason === 'repo-root' && exists(path.join(repo, 'skills/old-skill/SKILL.md')), JSON.stringify(r2));
  }
  // 8
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'] });
    const root = mk('root');
    fs.mkdirSync(path.join(root, '.git'));
    put(root, 'skills/old-skill/SKILL.md', 'shipped');
    const c = cons();
    const r = await run(base(repo, root, { console: c }));
    const line = lib.formatResult(r).join('\n');
    check('8 git work tree skipped', r.status === 'skipped' && r.reason === 'git-root' && exists(path.join(root, 'skills/old-skill/SKILL.md')), JSON.stringify(r));
    check('8 skip line names the root and the force command', line === `Retired files: skipped (${root} is a git work tree; run: agency prune --force)`, line);
    const r2 = await run(base(repo, root, { force: true }));
    check('8 force prunes the git work tree', r2.status === 'changed' && !exists(path.join(root, 'skills/old-skill/SKILL.md')), JSON.stringify(r2));
    // a root nested inside a real work tree (rev-parse path, no .git in root itself)
    const outer = mk('outer');
    const g = spawnSync('git', ['init', '-q', outer]);
    if (g.status === 0) {
      const inner = path.join(outer, 'sub');
      put(inner, 'skills/old-skill/SKILL.md', 'shipped');
      const r3 = await run(base(repo, inner, {}));
      check('8 root inside a work tree skipped via rev-parse', r3.reason === 'git-root' && exists(path.join(inner, 'skills/old-skill/SKILL.md')), JSON.stringify(r3));
    } else ok('8 (git unavailable: nested-work-tree check skipped)');
  }
  // 9
  {
    const repo = fakeRepo({
      'agents/specialized/task-executor.md': ['ag1'], 'agents/engineering/engineering-lead.md': ['ag2'],
      'runbooks/protocol-registry.md': ['rb1'], 'core/runbooks/protocol-registry.md': ['co1'],
    });
    const root = mk('root');
    put(root, 'agents/specialized/task-executor.md', 'ag1');
    put(root, 'agents/engineering/engineering-lead.md', 'ag2');
    put(root, 'agents/engineering/mine.md', 'user agent');
    put(root, 'runbooks/protocol-registry.md', 'rb1');
    put(root, 'core/runbooks/protocol-registry.md', 'co1');
    put(root, 'core/memory/medium-term.md', 'user registry');
    const r = await run(base(repo, root, {}));
    check('9 agents/runbooks/core retired paths removed', r.removed.length === 4, JSON.stringify(r.removed));
    check('9 emptied dirs removed (agents/specialized, agents/engineering stays: has mine.md)', !exists(path.join(root, 'agents/specialized')) && exists(path.join(root, 'agents/engineering/mine.md')) && !exists(path.join(root, 'runbooks/protocol-registry.md')));
    check('9 core/runbooks dir removed, core/ and core/memory kept', !exists(path.join(root, 'core/runbooks')) && exists(path.join(root, 'core/memory/medium-term.md')));
    check('9 tree roots never removed', ['skills', 'agents', 'runbooks', 'core'].every((t) => exists(path.join(root, t)) || t === 'skills' || t === 'runbooks'));
  }
  // 10
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'], 'skills/linked/SKILL.md': ['shipped'] });
    const root = mk('root');
    const elsewhere = mk('elsewhere');
    put(elsewhere, 'target.md', 'shipped');
    fs.mkdirSync(path.join(root, 'skills/old-skill'), { recursive: true });
    fs.symlinkSync(path.join(elsewhere, 'target.md'), path.join(root, 'skills/old-skill/SKILL.md'));
    const r = await run(base(repo, root, {}));
    check('10 symlinked file skipped, target untouched', r.skipped.some((s) => s.path === 'skills/old-skill/SKILL.md' && s.reason === 'symlink') && exists(path.join(elsewhere, 'target.md')) && r.removed.length === 0, JSON.stringify(r));
    // symlinked skills/ directory: never delete through it
    const root2 = mk('root');
    const realSkills = mk('realskills');
    put(realSkills, 'linked/SKILL.md', 'shipped');
    fs.symlinkSync(realSkills, path.join(root2, 'skills'));
    const r2 = await run(base(repo, root2, {}));
    check('10 symlinked skills/ dir not pruned through', exists(path.join(realSkills, 'linked/SKILL.md')) && r2.removed.length === 0 && r2.skipped.some((s) => s.reason === 'symlink'), JSON.stringify(r2));
  }
  // 11
  {
    const emptyRepo = mk('norepo');
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'shipped');
    const r = await run(base(emptyRepo, root, {}));
    check('11 missing manifest -> skipped no-manifest', r.status === 'skipped' && r.reason === 'no-manifest' && exists(path.join(root, 'skills/old-skill/SKILL.md')), JSON.stringify(r));
  }
  // 12
  {
    const repo = fakeRepo({ 'skills/ed/SKILL.md': ['v'] });
    const root = mk('root');
    put(root, `archive/agency-retired-${DATE}/skills/ed/SKILL.md`, 'older archive');
    put(root, 'skills/ed/SKILL.md', 'edited A');
    const r1 = await run(base(repo, root, {}));
    put(root, 'skills/ed/SKILL.md', 'edited B');
    const r2 = await run(base(repo, root, {}));
    const d = path.join(root, 'archive', `agency-retired-${DATE}`, 'skills/ed');
    check('12 collision -> .1 then .2, nothing overwritten',
      fs.readFileSync(path.join(d, 'SKILL.md'), 'utf8') === 'older archive' && fs.readFileSync(path.join(d, 'SKILL.md.1'), 'utf8') === 'edited A' && fs.readFileSync(path.join(d, 'SKILL.md.2'), 'utf8') === 'edited B' && /SKILL\.md\.1$/.test(r1.archived[0].to) && /SKILL\.md\.2$/.test(r2.archived[0].to), JSON.stringify([r1.archived, r2.archived]));
  }
  // 14
  {
    const repo = fakeRepo({ 'skills/ed/SKILL.md': ['v'] });
    const root = mk('root');
    put(root, 'skills/ed/SKILL.md', 'edited');
    const r = await run(base(repo, root, { retired: 'delete' }));
    check('14 retired:delete deletes the edited file, no archive', r.removed.length === 1 && r.archived.length === 0 && !exists(path.join(root, 'skills/ed')) && !exists(path.join(root, 'archive')), JSON.stringify(r));
    check('14 deleted-by-choice counted in the summary', lib.formatResult(r)[0] === 'Retired files: 1 removed, 0 archived (modified)', lib.formatResult(r)[0]);
  }
  // 16
  {
    const mkTwo = () => {
      const repo = fakeRepo({ 'skills/e1/SKILL.md': ['v'], 'skills/e2/SKILL.md': ['v'], 'skills/clean/SKILL.md': ['v'] });
      const root = mk('root');
      put(root, 'skills/e1/SKILL.md', 'edit1');
      put(root, 'skills/e2/SKILL.md', 'edit2');
      put(root, 'skills/clean/SKILL.md', 'v');
      return { repo, root };
    };
    const script = (answers) => { const asked = []; return { asked, prompt: async (q) => { asked.push(q); return answers.shift(); } }; };
    let s = script(['a']); let { repo, root } = mkTwo();
    let r = await run(base(repo, root, { isTTY: true, prompt: s.prompt }));
    check('16 ask+TTY "a": archive all, ONE prompt, clean file silently deleted', s.asked.length === 1 && /\[a\]rchive all \/ \[d\]elete all \/ \[c\]hoose per item/.test(s.asked[0]) && r.archived.length === 2 && r.removed.length === 1, JSON.stringify([s.asked, r]));
    s = script(['d']); ({ repo, root } = mkTwo());
    r = await run(base(repo, root, { isTTY: true, prompt: s.prompt }));
    check('16 ask+TTY "d": delete all', s.asked.length === 1 && r.removed.length === 3 && r.archived.length === 0 && !exists(path.join(root, 'archive')), JSON.stringify(r));
    s = script(['c', 'd', 'a']); ({ repo, root } = mkTwo());
    r = await run(base(repo, root, { isTTY: true, prompt: s.prompt }));
    check('16 ask+TTY "c": one prompt, then per item (e1 deleted, e2 archived)', s.asked.length === 3 && r.removed.length === 2 && r.archived.length === 1 && r.archived[0].path === 'skills/e2/SKILL.md' && !exists(path.join(root, 'skills/e1/SKILL.md')), JSON.stringify([s.asked, r]));
    const lt = fs.readFileSync(path.join(root, 'logs', 'agency-retired.log'), 'utf8');
    check('17 log records each per-item decision', /deleted: skills\/e1\/SKILL\.md/.test(lt) && /archived: skills\/e2\/SKILL\.md/.test(lt), lt);
    s = script(['zzz']); ({ repo, root } = mkTwo());
    r = await run(base(repo, root, { isTTY: true, prompt: s.prompt }));
    check('18 invalid answer -> archive', r.archived.length === 2 && r.removed.length === 1);
    s = script(['']); ({ repo, root } = mkTwo());
    r = await run(base(repo, root, { isTTY: true, prompt: s.prompt }));
    check('18 empty answer -> archive', r.archived.length === 2);
    s = script(['d']); ({ repo, root } = mkTwo());
    r = await run(base(repo, root, { isTTY: true, retired: 'archive', prompt: s.prompt }));
    check('16 explicit retired:archive never prompts', s.asked.length === 0 && r.archived.length === 2);
    s = script(['d']); ({ repo, root } = mkTwo());
    r = await run(base(repo, root, { isTTY: false, retired: 'ask', prompt: s.prompt }));
    check('16 ask without TTY never prompts, archives', s.asked.length === 0 && r.archived.length === 2 && r.removed.length === 1);
  }
  // 18 env
  {
    const repo = fakeRepo({ 'skills/ed/SKILL.md': ['v'] });
    let root = mk('root'); put(root, 'skills/ed/SKILL.md', 'edited');
    let r = await run(base(repo, root, { env: { AGENCY_RETIRED: 'delete' } }));
    check('18 env AGENCY_RETIRED=delete honoured', r.removed.length === 1 && r.archived.length === 0, JSON.stringify(r));
    root = mk('root'); put(root, 'skills/ed/SKILL.md', 'edited');
    r = await run(base(repo, root, { env: { AGENCY_RETIRED: 'delete' }, retired: 'archive' }));
    check('18 explicit option beats env', r.archived.length === 1 && r.removed.length === 0);
  }
  // 19 CLI
  {
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'], 'skills/ed/SKILL.md': ['v'] });
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'shipped');
    put(root, 'skills/ed/SKILL.md', 'edited');
    const cli = (args) => spawnSync(process.execPath, [LIB, ...args], { encoding: 'utf8', env: { ...process.env, AGENCY_RETIRED: '' }, input: '' });
    const st = cli(['status', '--root', root, '--repo', repo, '--json']);
    let j = null; try { j = JSON.parse(st.stdout); } catch { /* reported below */ }
    check('19 status --json is dry-run, valid JSON, exit 0', st.status === 0 && j && j.dryRun === true && exists(path.join(root, 'skills/old-skill/SKILL.md')), st.stdout + st.stderr);
    const pr = cli(['prune', '--root', root, '--repo', repo, '--retired=delete']);
    check('19 prune --retired=delete deletes both, summary on stdout, exit 0', pr.status === 0 && /Retired files: 2 removed, 0 archived \(modified\)/.test(pr.stdout) && !exists(path.join(root, 'skills/ed')), pr.stdout + pr.stderr);
    const nm = cli(['prune', '--root', mk('root'), '--repo', mk('norepo')]);
    check('19 skipped is not an error (exit 0)', nm.status === 0 && /skipped/.test(nm.stdout), nm.stdout + nm.stderr);
    const badRepo = mk('badrepo'); fs.writeFileSync(path.join(badRepo, 'retired-manifest.json'), '{nope');
    const er = cli(['prune', '--root', mk('root'), '--repo', badRepo]);
    check('19 unreadable manifest -> exit 1', er.status === 1, er.stdout + er.stderr);
    const bf = cli(['prune', '--bogus']);
    check('19 unknown option -> exit 1', bf.status === 1);
  }
  // 20
  {
    const badRepo = mk('badrepo'); fs.writeFileSync(path.join(badRepo, 'retired-manifest.json'), '{nope');
    const c = cons();
    let threw = false; let r = null;
    try { r = await lib.autoPrune({ root: mk('root'), repoDir: badRepo, console: c, indent: '  ' }); } catch { threw = true; }
    check('20 autoPrune never throws (bad manifest)', !threw && r && r.status === 'error' && c.out.length >= 1, JSON.stringify(r));
    const repo = fakeRepo({ 'skills/old-skill/SKILL.md': ['shipped'], 'skills/ed/SKILL.md': ['v'] });
    const root = mk('root');
    put(root, 'skills/old-skill/SKILL.md', 'shipped'); put(root, 'skills/ed/SKILL.md', 'edited');
    const c2 = cons();
    const t0 = Date.now();
    const r2 = await lib.autoPrune({ root, repoDir: repo, console: c2, indent: '  ' });
    check('20 autoPrune non-blocking without a TTY, indented summary', Date.now() - t0 < 3000 && r2.status === 'changed' && c2.out.some((l) => l.startsWith('  Retired files: 1 removed, 1 archived (modified)')), c2.out.join('\n'));
  }
  // 21
  {
    const repo = fakeRepo({ 'skills/ok/SKILL.md': ['v'] });
    const mp = path.join(repo, 'retired-manifest.json');
    const m = JSON.parse(fs.readFileSync(mp, 'utf8'));
    m.paths['../outside.txt'] = [sha('x')];
    m.paths['hooks/live-hook.sh'] = [sha('x')];
    m.paths['/etc/passwd'] = [sha('x')];
    fs.writeFileSync(mp, JSON.stringify(m));
    const root = mk('root');
    put(root, 'skills/ok/SKILL.md', 'v');
    put(path.dirname(root), 'outside.txt', 'x');
    put(root, 'hooks/live-hook.sh', 'x');
    const r = await run(base(repo, root, {}));
    check('21 only the four trees are ever touched', r.removed.length === 1 && exists(path.join(path.dirname(root), 'outside.txt')) && exists(path.join(root, 'hooks/live-hook.sh')), JSON.stringify(r));
    fs.rmSync(path.join(path.dirname(root), 'outside.txt'), { force: true });
  }
}

main().catch((e) => { bad('unexpected exception', e.stack || e.message); }).finally(() => {
  for (const d of tmps) { try { fs.rmSync(d, { recursive: true, force: true }); } catch { /* best effort */ } }
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
});
