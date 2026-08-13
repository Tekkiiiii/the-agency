#!/usr/bin/env node
// check-core-preserve.js — run the core/ sync `agency init` and `agency
// upgrade` use, end to end, against a throwaway destination.
//
// WHY: core/ is deployed by FOUR paths and all four used to do a blind
// recursive overwrite. Some files under core/memory/ ship as empty scaffolds
// that the running system appends rows to at their INSTALLED path — the
// project registry, the delegator route cache. Every reinstall and every
// `agency upgrade` silently destroyed those rows: exit code 0, no warning,
// user data gone. The CLI half of that is what this file covers; the two
// shell installers are asserted directly in .github/workflows/installers.yml.
//
// An `agency upgrade` end to end needs a pushed commit, a git remote and a
// re-exec, none of which belong in a unit check — so this calls the exact
// function upgrade.js calls, the way check-design-system-sync.js does.
//
// Four destination states, covering everything the contract has to get right:
//   1. absent               -> seeded (a fresh install must still get the file)
//   2. stale template       -> overwritten (users keep receiving new content)
//   3. user-modified, preserved -> byte-identical afterwards (the data-loss fix)
//   4. absent, preserved    -> seeded (first-install seeding of a preserved file)
//
// State 2 matters as much as state 3. An assertion that only proved
// preservation would pass just as happily if core syncing were disabled
// wholesale — which would freeze every install on the version it has.
const { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync } = require('fs');
const { join, dirname } = require('path');
const os = require('os');

const repoDir = join(__dirname, '..', '..');
const { syncCore, readCorePreserveList } = require(join(repoDir, 'cli', 'commands', 'sync-assets.js'));

const fail = (m) => { console.error('FAIL: ' + m); process.exitCode = 1; };

// ── 0. The list itself ──────────────────────────────────────────────────────
// A typo'd path in core/.preserve preserves nothing and reports nothing. It is
// the one failure this whole mechanism cannot detect at runtime, so catch it
// here instead.
const preserve = readCorePreserveList(repoDir);
if (preserve.size === 0) fail('core/.preserve is empty or unreadable');
for (const rel of preserve) {
  if (!existsSync(join(repoDir, 'core', rel))) {
    fail(`core/.preserve lists "${rel}", which does not exist under core/ — a typo here silently preserves nothing`);
  }
}

// A preserved path must be a file, not a directory: the parsers in install.sh,
// install.ps1 and sync-assets.js all match whole relative FILE paths.
const PRESERVED = [...preserve];
const REGISTRY = 'memory/medium-term.md';           // must be on the list
const TEMPLATE = 'memory/agency-dispatch.md';       // must NOT be on the list
if (!preserve.has(REGISTRY)) fail(`${REGISTRY} is not preserved — the project registry is the worst-case data loss`);
if (preserve.has(TEMPLATE)) fail(`${TEMPLATE} is preserved — nothing writes it, so users would never receive new agent routes`);

// ── set up the destination ──────────────────────────────────────────────────
const dest = join(os.tmpdir(), 'core-preserve-check-' + process.pid);
rmSync(dest, { recursive: true, force: true });

const write = (rel, text) => {
  const p = join(dest, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, text);
  return p;
};

// 3. user-modified preserved file. Shaped like what the running system
// actually appends — a real Active Projects row — so "preserved" means "byte
// identical to what the user's agents wrote", not merely "still exists".
const userRegistryText =
  readFileSync(join(repoDir, 'core', REGISTRY), 'utf8') +
  '| ci-probe-project | `/tmp/ci-probe/memory/` | ci-probe-pd | Active |\n';
const registryDest = write(REGISTRY, userRegistryText);

// 2. stale template. Content deliberately unlike the repo's so a no-op sync
// is distinguishable from a real refresh.
const templateDest = write(TEMPLATE, 'STALE SENTINEL — must be overwritten\n');

// 4. a preserved file that is ABSENT — first-install seeding.
const seedTargets = PRESERVED.filter(rel => rel !== REGISTRY);
if (seedTargets.length === 0) fail('expected more than one preserved path to test seeding');

const quiet = { log() {}, error: console.error };
const result = syncCore(repoDir, dest, quiet);

// ── assertions ──────────────────────────────────────────────────────────────

// 1. absent -> seeded. core/ORG.md is plain shipped content, on no list.
if (!existsSync(join(dest, 'ORG.md'))) fail('absent file was not created (ORG.md) — is core syncing running at all?');

// 2. stale template -> overwritten.
if (readFileSync(templateDest, 'utf8') !== readFileSync(join(repoDir, 'core', TEMPLATE), 'utf8')) {
  fail(`stale template was not refreshed (${TEMPLATE}) — users would never receive new agent routes`);
}

// 3. user-modified preserved file -> untouched.
if (readFileSync(registryDest, 'utf8') !== userRegistryText) {
  fail(`preserved file was overwritten (${REGISTRY}) — this is the data-loss bug`);
}

// 4. absent preserved file -> seeded from the repo.
for (const rel of seedTargets) {
  const p = join(dest, rel);
  if (!existsSync(p)) fail(`preserved-but-absent file was not seeded (${rel}) — a fresh install would be missing it`);
  else if (readFileSync(p, 'utf8') !== readFileSync(join(repoDir, 'core', rel), 'utf8')) {
    fail(`seeded file does not match the repo copy (${rel})`);
  }
}

// The reported bookkeeping must name the file it actually skipped, so an
// operator reading `Core: N updated, M preserved` can tell why.
if (!result.preserveSkipped.includes(REGISTRY)) {
  fail(`syncCore did not report ${REGISTRY} as preserve-skipped (got: ${JSON.stringify(result.preserveSkipped)})`);
}

// A second sync into the same destination must be idempotent AND must still
// not touch the preserved file — this is the `agency upgrade` case.
const second = syncCore(repoDir, dest, quiet);
if (second.updated !== 0) fail(`a repeat sync copied ${second.updated} file(s) — hash comparison is not working`);
if (readFileSync(registryDest, 'utf8') !== userRegistryText) {
  fail(`preserved file was overwritten by the SECOND sync (${REGISTRY})`);
}

console.log(
  `core sync: ${result.updated} updated, ${result.preserved} preserved ` +
  `(${result.preserveSkipped.length} held by core/.preserve: ${result.preserveSkipped.join(', ')})` +
  (process.exitCode ? '' : ' — OK')
);
rmSync(dest, { recursive: true, force: true });
