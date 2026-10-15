#!/usr/bin/env node
// check-scripts-tests-excluded.js - regression guard: scripts/tests is repo + CI only and must never be deployed.
//
// scripts/ is deployed (install.sh, install.ps1, `agency init`, `agency upgrade`), but its unit tests are not
// (~1 MB the user never runs). 26e4f72 shipped them by accident for one day. This check covers the CLI sync path:
//   1. syncScripts() into a fresh dir copies scripts/ (spot files) but creates NO scripts/tests
//   2. `agency init` into a fresh AGENCY_HOME does the same end to end
//   3. a pre-existing {root}/scripts/tests (an earlier install's, or the user's own) is left exactly as it is:
//      not deleted, not refreshed, nothing added beside it. That is the "no automatic cleanup" decision in
//      docs/INSTALL-LAYOUT.md: the directory carries no ownership marker, so the installers only stop copying it.
//   4. only the top level is skipped: a nested directory named tests elsewhere under scripts/ still ships
//      (checked with a throwaway repo fixture)
//
// REPO=<dir> checks another checkout (e.g. a worktree of an older revision, to see the check go red).
// Usage: node .github/scripts/check-scripts-tests-excluded.js   Exit 0 = PASS, 1 = FAIL.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const REPO = path.resolve(process.env.REPO || path.join(__dirname, '..', '..'));
const { syncScripts } = require(path.join(REPO, 'cli', 'commands', 'sync-assets.js'));
const quiet = { log() {}, warn() {}, error() {} };

let fails = 0;
function check(ok, label) {
  console.log((ok ? '  ok   ' : '  FAIL ') + label);
  if (!ok) fails++;
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'scripts-tests-excluded-'));
const exists = (p) => fs.existsSync(p);

try {
  console.log('check-scripts-tests-excluded: repo = ' + REPO);
  check(exists(path.join(REPO, 'scripts', 'tests')), 'the repo has scripts/tests (so the exclusion is not vacuous)');
  const spot = ['jev-spawn-gate.py', 'skill-route.py', path.join('skill-route', 'overlay.json')];

  // 1. syncScripts, fresh destination
  const d1 = path.join(tmp, 'sync', 'scripts');
  syncScripts(REPO, d1, quiet);
  check(spot.every((f) => exists(path.join(d1, f))), 'syncScripts deployed scripts/ (' + spot.join(', ') + ')');
  check(!exists(path.join(d1, 'tests')), 'syncScripts did not create scripts/tests');
  syncScripts(REPO, d1, quiet);
  check(!exists(path.join(d1, 'tests')), 'a second syncScripts (the upgrade case) still did not create it');

  // 2. agency init, end to end
  const home = path.join(tmp, 'init-home');
  const r = spawnSync(process.execPath, [path.join(REPO, 'cli', 'bin', 'agency.js'), 'init'], {
    env: Object.assign({}, process.env, { AGENCY_HOME: home, HOME: path.join(tmp, 'h'), USERPROFILE: path.join(tmp, 'h'),
      AGENCY_NO_MODS: '1', AGENCY_NO_HOOKS: '1' }),
    cwd: tmp, encoding: 'utf8', input: '', timeout: 180000,
  });
  check(r.status === 0, 'agency init exit 0 (got ' + r.status + ')' + (r.status === 0 ? '' : '\n' + (r.stdout + r.stderr).slice(-600)));
  check(exists(path.join(home, 'scripts', 'jev-spawn-gate.py')), 'agency init deployed scripts/jev-spawn-gate.py');
  check(!exists(path.join(home, 'scripts', 'tests')), 'agency init did not create scripts/tests');

  // 3. an existing scripts/tests is left alone
  const d3 = path.join(tmp, 'existing', 'scripts');
  fs.mkdirSync(path.join(d3, 'tests'), { recursive: true });
  fs.writeFileSync(path.join(d3, 'tests', 'keep-me.py'), 'user test\n');
  syncScripts(REPO, d3, quiet);
  check(fs.readFileSync(path.join(d3, 'tests', 'keep-me.py'), 'utf8') === 'user test\n', 'an existing scripts/tests/keep-me.py survives untouched');
  check(fs.readdirSync(path.join(d3, 'tests')).join() === 'keep-me.py', 'nothing was copied beside it');

  // 4. only the top-level tests is skipped
  const fx = path.join(tmp, 'fx-repo');
  fs.mkdirSync(path.join(fx, 'scripts', 'tests'), { recursive: true });
  fs.mkdirSync(path.join(fx, 'scripts', 'lib', 'tests'), { recursive: true });
  fs.writeFileSync(path.join(fx, 'scripts', 'tests', 'a.py'), 'a\n');
  fs.writeFileSync(path.join(fx, 'scripts', 'lib', 'tests', 'b.py'), 'b\n');
  fs.writeFileSync(path.join(fx, 'scripts', 'run.py'), 'r\n');
  const d4 = path.join(tmp, 'fx-dest');
  syncScripts(fx, d4, quiet);
  check(exists(path.join(d4, 'run.py')) && exists(path.join(d4, 'lib', 'tests', 'b.py')), 'a nested scripts/lib/tests still ships');
  check(!exists(path.join(d4, 'tests')), 'the top-level scripts/tests of the fixture was skipped');
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
console.log(fails === 0 ? 'PASS: check-scripts-tests-excluded' : 'FAIL: check-scripts-tests-excluded - ' + fails + ' check(s) failed');
process.exit(fails === 0 ? 0 : 1);
