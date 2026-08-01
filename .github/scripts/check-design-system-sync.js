#!/usr/bin/env node
// check-design-system-sync.js — run the design-system sync `agency upgrade`
// uses, end to end, against a throwaway destination.
//
// WHY: Wave 14 shipped the design-system tree onto the deploy list and could
// only verify the upgrade path by READING syncDesignSystem() — an end-to-end
// `agency upgrade` needs a pushed commit to pull, a git remote, and a re-exec,
// none of which belong in a unit check. install.sh's deployment is asserted by
// the workflow already; the UPGRADE path was the untested half.
//
// design-system/ is the quietest tree in the repo: a skill that cannot find its
// brand file does not error, it falls back to a hardcoded hex and ships an
// off-brand deliverable. Silent-failure trees need loud tests.
//
// This calls the exact function upgrade.js calls, with three destination states
// that cover everything sync has to get right:
//   1. absent      -> must be created
//   2. stale       -> must be overwritten (content hash, not mtime/size)
//   3. user-added  -> must be left alone
const { execFileSync } = require('child_process');
const { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync } = require('fs');
const { join } = require('path');
const os = require('os');

const repoDir = join(__dirname, '..', '..');
const { syncDesignSystem } = require(join(repoDir, 'cli', 'commands', 'sync-assets.js'));

const dest = join(os.tmpdir(), 'ds-sync-check-' + process.pid);
rmSync(dest, { recursive: true, force: true });
mkdirSync(join(dest, 'brands'), { recursive: true });

const brandSrc = join(repoDir, 'design-system', 'brands', 'neutral.json');
const brandDest = join(dest, 'brands', 'neutral.json');
const cssDest = join(dest, 'brands', 'neutral.css');
const userFile = join(dest, 'brands', 'my-own-brand.json');

// 2. stale, 3. user-added. (1. absent is everything else, incl. neutral.css.)
// The user file is a VALID brand, not a stub: build.js validates every brand
// JSON in the tree and aborts on a malformed one, so a stub would test the
// validator rather than the sync. It carries a marker name so "preserved" can
// mean "byte-identical to what the user wrote", not merely "still exists".
const userBrand = JSON.parse(readFileSync(brandSrc, 'utf8'));
userBrand.name = 'my-own-brand';
const userBrandText = JSON.stringify(userBrand, null, 2) + '\n';
writeFileSync(brandDest, '{"stale": true}\n');
writeFileSync(userFile, userBrandText);

const quiet = { log() {}, error: console.error };
const result = syncDesignSystem(repoDir, dest, quiet);

const fail = (m) => { console.error('FAIL: ' + m); process.exitCode = 1; };

if (!existsSync(cssDest)) fail('absent file was not created (brands/neutral.css)');
if (readFileSync(brandDest, 'utf8') !== readFileSync(brandSrc, 'utf8')) {
  fail('stale brand SSOT was not overwritten (brands/neutral.json)');
}
if (!existsSync(userFile)) fail('a user-added file was deleted');
else if (readFileSync(userFile, 'utf8') !== userBrandText) fail('a user-added file was overwritten');
if (!existsSync(join(dest, 'build.js'))) fail('build.js was not synced');

// The deployed tree must still be functional, not merely present: regenerate
// the CSS from the synced JSON with the synced build.js and require the result
// to match byte for byte. Catches a truncated copy and a hand-edited .css.
if (existsSync(join(dest, 'build.js')) && existsSync(cssDest)) {
  const before = readFileSync(cssDest, 'utf8');
  try {
    execFileSync(process.execPath, [join(dest, 'build.js')], { stdio: 'pipe' });
  } catch (e) {
    fail('synced build.js did not run: ' + (e.stderr || e.message));
  }
  if (readFileSync(cssDest, 'utf8') !== before) {
    fail('synced brand CSS is not what the synced build.js generates');
  }
}

console.log(
  `design-system sync: ${result.updated} updated, ${result.preserved} preserved` +
  (process.exitCode ? '' : ' — OK')
);
rmSync(dest, { recursive: true, force: true });
