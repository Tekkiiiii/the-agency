#!/usr/bin/env node
// check-quickstart-registry.js - the first-run path works end to end:
//   install -> `agency new demo` -> the project is findable by /recall and /pd-resume.
//
//   node .github/scripts/check-quickstart-registry.js [--installer sh|ps1]
//
// There is ONE project registry: {root}/memory/medium-term.md. Every reader
// (skills/recall, pd-resume, pd-spawn, the spawn-log hooks) reads that path, so the
// installer must seed it and `agency new` must write to it. Before this check the
// installer shipped a stub at {root}/core/memory/medium-term.md only, `agency new`
// registered nothing, and /recall printed "PROJECT NOT FOUND" on a fresh install.
//
// recall and pd-resume are prose skills, so the lookups below are the ones they
// document, run as written:
//   recall    "find the slug in the Active Projects table -> get project path":
//             column 2 of the row whose column 1 is the slug, backticks stripped,
//             then read {project-path}/memory/next-session.md.
//   pd-resume the awk one-liner in skills/pd-resume/SKILL.md Step 2 (verbatim).
//   hooks     hooks/lib/resolve-project.sh (sourced, as the spawn-logger does).
//
// AGENCY_HOME may be preset (the windows job does); otherwise a fresh temp root is used.

'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const installer = process.argv[2] === '--installer' ? process.argv[3] : 'sh';
const ROOT = process.env.AGENCY_HOME || path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'quickstart-')), 'h');
const REG = path.join(ROOT, 'memory', 'medium-term.md');
const LEGACY = path.join(ROOT, 'core', 'memory', 'medium-term.md');
// AGENCY_NO_MODS=1: this check is about the project registry; the installer's mods step
// depends on whether the machine has a claude CLI, so keep it out of the result.
const env = Object.assign({}, process.env, { AGENCY_HOME: ROOT, AGENCY_NO_MODS: '1' });
delete env.CLAUDE_CONFIG_DIR;

let failures = 0;
function ok(cond, msg) {
  console.log((cond ? 'ok   ' : 'FAIL ') + msg);
  if (!cond) failures++;
  return cond;
}
function run(cmd, args, opts) {
  return spawnSync(cmd, args, Object.assign({ env, cwd: REPO, encoding: 'utf8' }, opts || {}));
}
function install() {
  const r = installer === 'ps1'
    ? run('pwsh', ['-NoProfile', '-File', path.join(REPO, 'install.ps1')])
    : run('bash', [path.join(REPO, 'install.sh')]);
  if (r.status !== 0) console.log((r.stdout || '') + (r.stderr || ''));
  return r.status === 0;
}
const read = f => (fs.existsSync(f) ? fs.readFileSync(f, 'utf8') : null);
const rows = txt => (txt || '').split(/\r?\n/).filter(l => /^\|/.test(l));
// recall's documented parse: Active Projects table, column 1 = slug, column 2 = path.
function recallLookup(txt, slug) {
  const row = rows(txt).map(l => l.split('|').map(s => s.trim())).find(c => c[1] === slug);
  return row ? row[2].replace(/`/g, '') : null;
}

console.log(`root=${ROOT} installer=${installer}`);
ok(install(), 'install exits 0');

// 1. The installer seeds the registry the readers use.
const seeded = read(REG);
ok(seeded !== null, 'installer seeds {root}/memory/medium-term.md');
ok(/\|\s*Project\s*\|\s*Memory Path\s*\|\s*PD\s*\|\s*Status\s*\|/.test(seeded || ''), 'registry carries the Active Projects header project-scaffolder expects');

// 2. `agency new demo` registers the project in that same file.
const n = run('node', [path.join(REPO, 'cli', 'bin', 'agency.js'), 'new', 'demo', 'Demo project']);
ok(n.status === 0, '`agency new demo` exits 0' + (n.status === 0 ? '' : '\n' + n.stdout + n.stderr));
const after = read(REG);
const memPath = recallLookup(after, 'demo');
ok(memPath !== null, 'registry has a row for demo');

// 3. recall resolves it to a real project.
if (memPath) {
  const projectPath = memPath.replace(/[\\/]+$/, '').replace(/[\\/]memory$/, '');
  ok(fs.existsSync(path.join(projectPath, 'STATE.md')), `recall path resolves to the created project (${projectPath})`);
  ok(fs.existsSync(path.join(projectPath, 'memory')), 'project has a memory/ dir for next-session.md');

  // 4. pd-resume's documented awk lookup, verbatim.
  const awk = run('awk', ['-F|', '-v', 's=demo', '$2 ~ "^ *"s" *$" {gsub(/ /,"",$4); print $4}', REG]);
  ok(awk.status === 0 && awk.stdout.trim() === 'demo-pd', `pd-resume awk lookup returns the PD name (got "${(awk.stdout || '').trim()}")`);

  // 5. the spawn-log hooks resolve the project from the same file (POSIX only: the
  //    hook greps the cwd against the registry path as a literal prefix).
  if (process.platform !== 'win32') {
    const hook = run('bash', ['-c', `. "${path.join(ROOT, 'hooks', 'lib', 'resolve-project.sh')}"; resolve_project_path; printf %s "$SPAWN_LOG_FILE"`],
      { env: Object.assign({}, env, { CLAUDE_PROJECT_DIR: projectPath }) });
    ok(hook.stdout.trim() === path.join(projectPath, 'memory', 'spawns.jsonl'), `resolve-project.sh finds the project from the registry (got "${hook.stdout.trim()}")`);
  }
}

// 6. Registering is idempotent: a second `new` refuses, and never adds a second row.
const again = run('node', [path.join(REPO, 'cli', 'bin', 'agency.js'), 'new', 'demo']);
ok(again.status !== 0, 'second `agency new demo` is refused');
ok(rows(read(REG)).filter(l => l.split('|')[1].trim() === 'demo').length === 1, 'registry still has exactly one demo row');

// 7. `agency new` rebuilds a missing registry rather than failing.
if (fs.existsSync(REG)) fs.unlinkSync(REG);
const n2 = run('node', [path.join(REPO, 'cli', 'bin', 'agency.js'), 'new', 'demo2', 'Second']);
ok(n2.status === 0 && recallLookup(read(REG), 'demo2') !== null, '`agency new` recreates a missing registry and registers into it');

// 8. A second install never touches an existing registry (byte-identical).
const custom = (read(REG) || '') + '| user-proj | `/somewhere/user-proj/memory/` | user-proj-pd | Active |\n\nUser prose, kept.\n';
fs.writeFileSync(REG, custom);
ok(install(), 'second install exits 0');
ok(read(REG) === custom, 'second install leaves an existing registry byte-identical');

// 9. Upgrade path: a registry that only exists in the old location (core/memory,
//    where project-scaffolder used to write) is carried over, not lost.
fs.unlinkSync(REG);
fs.mkdirSync(path.dirname(LEGACY), { recursive: true });
fs.writeFileSync(LEGACY, (read(LEGACY) || '') + '| legacy-proj | `/old/legacy-proj/memory/` | legacy-proj-pd | Active |\n');
ok(install(), 'install after removing the registry exits 0');
ok(recallLookup(read(REG), 'legacy-proj') !== null, 'rows accumulated in the legacy core/memory registry are carried into {root}/memory');

console.log(failures ? `check-quickstart-registry: FAIL (${failures})` : 'check-quickstart-registry: PASS');
process.exit(failures ? 1 : 0);
