// One line for the installers: is the optional skill router on or off?
//
// The router (scripts/skill-route.py) ships DISABLED. It is enabled by exactly one
// switch, AGENCY_SKILL_ROUTER=1 (the exact string "1"), which can come from either:
//   - the process environment, or
//   - the "env" block of <root>/settings.json (Claude Code's documented place for
//     env vars; an installer run from a terminal does not inherit it).
// This file only READS settings.json. Any error means "not set". It never creates
// or touches the Jev key file and installs nothing.
//
// install.sh, `agency init` and `agency upgrade` call this; install.ps1 does the same
// read natively in PowerShell. Keep the wording identical in all four.

const { readFileSync } = require('fs');
const { join, resolve } = require('path');

const SWITCH = 'AGENCY_SKILL_ROUTER';

function routerEnabled(root, env) {
  if (env && env[SWITCH] === '1') return true;
  try {
    const s = JSON.parse(readFileSync(join(resolve(root), 'settings.json'), 'utf8'));
    return !!(s && s.env && s.env[SWITCH] === '1');
  } catch (_) {
    return false;
  }
}

function routerLine(root, env) {
  if (routerEnabled(root, env)) return 'Skill router: enabled (AGENCY_SKILL_ROUTER=1)';
  return `Skill router: disabled (see ${join(resolve(root), 'scripts', 'skill-route', 'README.md')} to enable)`;
}

module.exports = { routerEnabled, routerLine };

// node cli/lib/skill-router.js line <root>   (used by install.sh)
if (require.main === module) {
  const root = process.argv[3] || '';
  if (process.argv[2] !== 'line' || !root) {
    process.stderr.write('usage: skill-router.js line <root>\n');
    process.exit(2);
  }
  console.log(routerLine(root, process.env));
}
