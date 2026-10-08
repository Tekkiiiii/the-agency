// agency hooks sync|remove — wire (or unwire) the hooks listed in
// hooks/hooks.json into <agency-root>/settings.json.
//
// The merge itself lives in cli/lib/hooks-merge.js, shared with install.sh,
// install.ps1, `agency init` and `agency upgrade`. An explicit `agency hooks
// sync` ignores AGENCY_NO_HOOKS (that variable only opts out of the AUTOMATIC
// wiring done by the installers and upgrade); `--force` wires even on Windows
// when Git Bash is not on PATH.

const path = require('path');
const hooksMerge = require('../lib/hooks-merge.js');

const REPO_DIR = path.resolve(__dirname, '..', '..');

module.exports = async function hooks({ args, AGENCY_ROOT, console }) {
  const [sub, ...rest] = args;
  if (sub !== 'sync' && sub !== 'remove') {
    console.log('Usage:');
    console.log('  agency hooks sync     Wire the agency hooks into settings.json (keeps your own hooks)');
    console.log('  agency hooks remove   Unwire the agency hooks (keeps your own hooks; scripts stay on disk)');
    console.log('  Flags: --json (machine-readable result), --force (sync on Windows without Git Bash)');
    process.exitCode = sub ? 1 : 0;
    return;
  }
  const json = rest.includes('--json');
  const force = rest.includes('--force');
  const unknown = rest.filter(a => a !== '--json' && a !== '--force');
  if (unknown.length) {
    console.error(`Unknown option: ${unknown.join(' ')}`);
    process.exitCode = 1;
    return;
  }
  const opts = { root: AGENCY_ROOT, repoDir: REPO_DIR, force };
  const res = sub === 'sync' ? hooksMerge.syncHooks(opts) : hooksMerge.removeHooks(opts);
  if (json) console.log(JSON.stringify(res, null, 2));
  else for (const line of hooksMerge.formatResult(res)) console.log(line);
  if (res.status === 'error') process.exitCode = 1;
};
