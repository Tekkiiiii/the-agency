// agency prune [status] [--dry-run] [--force] [--json] [--root <dir>] [--retired=archive|delete|ask]
//
// Removes files the repo retired (skills/agents/runbooks/core paths it shipped
// once and deleted since) from the agency root. The engine lives in
// cli/lib/retired-prune.js, shared with install.sh, install.ps1,
// `agency init` and `agency upgrade`. Skips a root that is a git work tree
// unless --force, and always refuses the repo checkout itself.

const path = require('path');
const retiredPrune = require('../lib/retired-prune.js');

const REPO_DIR = path.resolve(__dirname, '..', '..');

module.exports = async function prune({ args, AGENCY_ROOT, console }) {
  const code = await retiredPrune.runCli(args, console, { root: AGENCY_ROOT, repoDir: REPO_DIR });
  if (code) process.exitCode = code;
};
