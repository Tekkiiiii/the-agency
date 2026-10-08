// Which rung of the agency-root ladder resolved the sync root, and a loud
// warning when the answer is "the default, by accident".
//
// The ladder is DEFINED in hooks/lib/resolve-root.sh and mirrored verbatim in
// cli/bin/agency.js, install.sh and install.ps1:
//   AGENCY_HOME || CLAUDE_CONFIG_DIR || <home>/.claude
// rootSource() walks the same rungs with the same `||` truthiness (an empty
// string falls through, exactly like `${AGENCY_HOME:-...}` in the shell twins).
// Keep the four in lockstep.
//
// Real case behind the warning: a Windows user whose Claude Code config lived on
// D: ran the installer with neither variable set; everything synced into
// C:\Users\<them>\.claude, which Claude Code never read, and nothing said so.

const { existsSync } = require('fs');
const { join } = require('path');

function rootSource(env) {
  if (env.AGENCY_HOME) return 'AGENCY_HOME';
  if (env.CLAUDE_CONFIG_DIR) return 'CLAUDE_CONFIG_DIR';
  return 'default';
}

// Prints "Sync root: <root> (from <source>)". When neither variable is set AND
// the default root has no settings.json yet, the user's real config may live
// somewhere else — say so. Call this BEFORE anything could create settings.json.
// Returns true when the warning fired, so callers can repeat it at the end.
function printSyncRoot(root, env, console) {
  const source = rootSource(env);
  console.log(`Sync root: ${root} (from ${source === 'default' ? 'default — neither AGENCY_HOME nor CLAUDE_CONFIG_DIR is set' : source})`);
  if (source !== 'default' || existsSync(join(root, 'settings.json'))) return false;
  printNoSettingsWarning(root, console);
  return true;
}

function printNoSettingsWarning(root, console) {
  console.log(`  ⚠ No settings.json at ${root}.`);
  console.log('    If your Claude Code config lives elsewhere (e.g. D:\\claude or a custom folder),');
  console.log('    set CLAUDE_CONFIG_DIR or AGENCY_HOME to that folder and re-run.');
}

module.exports = { rootSource, printSyncRoot, printNoSettingsWarning };
