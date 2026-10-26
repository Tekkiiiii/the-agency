#!/usr/bin/env node

/**
 * agency CLI — The Agency (Claude Code, fixed for everyone)
 * Usage: agency <command> [args]
 */

const { resolve } = require('path');
const os = require('os');

// Root precedence must match hooks/lib/resolve-root.sh exactly — otherwise the
// CLI writes to one directory and the deployed scripts read from another.
const AGENCY_ROOT = process.env.AGENCY_HOME
  || process.env.CLAUDE_CONFIG_DIR
  || resolve(os.homedir(), '.claude');

const COMMANDS = {
  init:      () => require('../commands/init.js'),
  new:       () => require('../commands/new.js'),
  onboard:   () => require('../commands/onboard.js'),
  setup:     () => require('../commands/onboard.js'),
  status:    () => require('../commands/status.js'),
  skill:     () => require('../commands/skill.js'),
  tasks:     () => require('../commands/tasks.js'),
  upgrade:   () => require('../commands/upgrade.js'),
  hooks:     () => require('../commands/hooks.js'),
  mods:      () => require('../commands/mods.js'),
  prune:     () => require('../commands/prune.js'),
  initiate:  () => require('../commands/bootstrap.js'),
  bootstrap: () => require('../commands/bootstrap.js'),
};

async function main() {
  const [,, cmd, ...args] = process.argv;

  if (!cmd || cmd === 'help' || cmd === '--help') {
    console.log('The Agency CLI');
    console.log('');
    console.log('Commands:');
    console.log('  agency init [--retired=MODE]        Install skills, agents, core docs, task store, and CLI link');
    console.log('  agency initiate                     Install tool deps + register MCP servers + auth checklist (run after init)');
    console.log('                                        Flags: --upgrade (force reinstall), --dry-run (preview only)');
    console.log('  agency onboard                      Guided introduction — creates first project + agent (run after init)');
    console.log('  agency new <proj> <desc>            Create a project');
    console.log('  agency status                       Show project states');
    console.log('  agency skill install <n>            Install a single skill by name');
    console.log('  agency skill list                   List installed skills');
    console.log('  agency tasks list [project]         List tasks');
    console.log('  agency tasks add <project> <name>   Add a task');
    console.log('  agency tasks done <task-id>         Mark task completed');
    console.log('  agency tasks status <id> <status>   Update task status');
    console.log('  agency upgrade [--retired=MODE]     Pull latest updates from git (also re-wires hooks, removes retired files)');
    console.log('                                        MODE (init/upgrade/prune): archive | delete | ask. What happens to a retired file you EDITED.');
    console.log('                                        Default: ask on a terminal, archive without one. Env AGENCY_RETIRED sets it too.');
    console.log('  agency hooks sync                   Wire the agency hooks into settings.json (keeps your own hooks)');
    console.log('  agency hooks remove                 Unwire the agency hooks (keeps your own hooks)');
    console.log('  agency hooks disable <id>           Unwire one hook and keep it off (also what deleting it by hand means)');
    console.log('  agency hooks enable <id>            Wire a disabled hook again');
    console.log('  agency mods sync                    Wire the agency mods into settings.json (Claude Code 2.1.287+; keeps your own plugin dirs)');
    console.log('  agency mods remove                  Unwire the agency mods and delete the copies we made');
    console.log('  agency mods status                  Show which mods are wired and which were skipped');
    console.log('  agency prune [--dry-run] [--force]  Remove files the repo retired from your root (edited ones are archived; --retired=archive|delete|ask)');
    process.exit(0);
  }

  const loader = COMMANDS[cmd];
  if (!loader) {
    console.error(`Unknown command: ${cmd}`);
    process.exit(1);
  }

  await loader()({ args, AGENCY_ROOT, console });
}

main().catch(err => {
  console.error(err.message);
  process.exit(1);
});
