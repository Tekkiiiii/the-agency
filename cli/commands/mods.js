// agency mods sync|remove|status — wire (or unwire) the mods shipped in mods/
// into <agency-root>/settings.json as env.CLAUDE_CODE_PLUGIN_DIRS.
//
// The merge itself lives in cli/lib/mods-merge.js, shared with install.sh,
// install.ps1, `agency init` and `agency upgrade`. An explicit `agency mods
// sync` ignores AGENCY_NO_MODS (that variable only opts out of the AUTOMATIC
// wiring done by the installers and upgrade). Mods need Claude Code 2.1.287+;
// on an older version sync says so and writes nothing.

const path = require('path');
const modsMerge = require('../lib/mods-merge.js');

const REPO_DIR = path.resolve(__dirname, '..', '..');

module.exports = async function mods({ args, AGENCY_ROOT, console }) {
  const [sub, ...rest] = args;
  const known = ['sync', 'remove', 'status'];
  if (!known.includes(sub)) {
    console.log('Usage:');
    console.log('  agency mods sync              Wire the agency mods into settings.json (keeps your own plugin dirs)');
    console.log('  agency mods remove            Unwire the agency mods and delete the copies we made');
    console.log('  agency mods status            Show what is wired, what would change, what is skipped');
    console.log('  Flags: --json (machine-readable result), --root <dir> (use another agency root)');
    process.exitCode = sub ? 1 : 0;
    return;
  }
  let json = false;
  let root = AGENCY_ROOT;
  const unknown = [];
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (a === '--json') json = true;
    else if (a === '--root' && rest[i + 1]) root = rest[++i];
    else if (/^--root=./.test(a)) root = a.slice(7);
    else unknown.push(a);
  }
  if (unknown.length) {
    console.error(`Unknown option: ${unknown.join(' ')}`);
    process.exitCode = 1;
    return;
  }
  const opts = { root, repoDir: REPO_DIR };
  let res;
  if (sub === 'sync') res = modsMerge.syncMods(opts);
  else if (sub === 'remove') res = modsMerge.removeMods(opts);
  else res = modsMerge.statusMods(opts);
  if (json) console.log(JSON.stringify(res, null, 2));
  else for (const line of modsMerge.formatResult(res)) console.log(line);
  if (res.status === 'error') process.exitCode = 1;
};
