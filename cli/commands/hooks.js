// agency hooks sync|remove|disable|enable — wire (or unwire) the hooks listed in
// hooks/hooks.json into <agency-root>/settings.json.
//
// The merge itself lives in cli/lib/hooks-merge.js, shared with install.sh,
// install.ps1, `agency init` and `agency upgrade`. An explicit `agency hooks
// sync` ignores AGENCY_NO_HOOKS (that variable only opts out of the AUTOMATIC
// wiring done by the installers and upgrade); `--force` wires even on Windows
// when Git Bash cannot be found.
//
// disable/enable are the per-hook opt-out: `disable <id>` removes our entry and
// remembers the choice (sync, upgrade and the installers then leave it out);
// `enable <id>` forgets the choice and wires the hook now. A hook you delete
// from settings.json by hand is treated the same way as `disable`.

const path = require('path');
const hooksMerge = require('../lib/hooks-merge.js');

const REPO_DIR = path.resolve(__dirname, '..', '..');

function validIds() {
  try {
    return hooksMerge.loadManifest(hooksMerge.DEFAULT_MANIFEST).hooks.map(h => h.id);
  } catch (_) {
    return [];
  }
}

module.exports = async function hooks({ args, AGENCY_ROOT, console }) {
  const [sub, ...rest] = args;
  const known = ['sync', 'remove', 'disable', 'enable'];
  if (!known.includes(sub)) {
    console.log('Usage:');
    console.log('  agency hooks sync             Wire the agency hooks into settings.json (keeps your own hooks)');
    console.log('  agency hooks remove           Unwire the agency hooks (keeps your own hooks; scripts stay on disk)');
    console.log('  agency hooks disable <id>     Unwire one hook and keep it off across sync, upgrade and install');
    console.log('  agency hooks enable <id>      Wire a disabled (or deleted) hook again, now');
    console.log('  Flags: --json (machine-readable result), --force (sync on Windows without Git Bash)');
    process.exitCode = sub ? 1 : 0;
    return;
  }
  const json = rest.includes('--json');
  const force = rest.includes('--force');
  const positional = rest.filter(a => !a.startsWith('--'));
  const unknown = rest.filter(a => a.startsWith('--') && a !== '--json' && a !== '--force');
  const needsId = sub === 'disable' || sub === 'enable';
  const extra = needsId ? positional.slice(1) : positional;
  if (unknown.length || extra.length) {
    console.error(`Unknown option: ${unknown.concat(extra).join(' ')}`);
    process.exitCode = 1;
    return;
  }
  if (needsId && positional.length === 0) {
    console.error(`Usage: agency hooks ${sub} <id>`);
    console.error(`Valid ids: ${validIds().join(', ')}`);
    process.exitCode = 1;
    return;
  }
  const opts = { root: AGENCY_ROOT, repoDir: REPO_DIR, force };
  let res;
  if (sub === 'sync') res = hooksMerge.syncHooks(opts);
  else if (sub === 'remove') res = hooksMerge.removeHooks(opts);
  else if (sub === 'disable') res = hooksMerge.disableHook(Object.assign(opts, { id: positional[0] }));
  else res = hooksMerge.syncHooks(Object.assign(opts, { enable: positional[0] }));
  if (json) console.log(JSON.stringify(res, null, 2));
  else for (const line of hooksMerge.formatResult(res)) console.log(line);
  if (res.status === 'error') process.exitCode = 1;
};
