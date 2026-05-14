#!/usr/bin/env node

/**
 * agency CLI — The Agency command center
 * Usage: agency <command> [args]
 */

const { resolve } = require('path');
const os = require('os');

const AGENCY_ROOT = process.env.AGENCY_HOME || resolve(os.homedir(), '.claude');

const COMMANDS = {
  init:    () => require('../commands/init.js'),
  new:     () => require('../commands/new.js'),
  onboard: () => require('../commands/onboard.js'),
  setup:   () => require('../commands/onboard.js'),
  status:  () => require('../commands/status.js'),
  skill:   () => require('../commands/skill.js'),
  tasks:   () => require('../commands/tasks.js'),
  upgrade: () => require('../commands/upgrade.js'),
};

async function main() {
  const [,, cmd, ...args] = process.argv;

  if (!cmd || cmd === 'help' || cmd === '--help') {
    console.log('The Agency CLI');
    console.log('');
    console.log('Commands:');
    console.log('  agency onboard                      Interactive setup wizard (start here)');
    console.log('  agency init                         Initialize the system');
    console.log('  agency new <proj> <desc>            Create a project');
    console.log('  agency status                       Show project states');
    console.log('  agency skill install <n>            Install a skill');
    console.log('  agency skill list                   List installed skills');
    console.log('  agency tasks list [project]         List tasks');
    console.log('  agency tasks add <project> <name>   Add a task');
    console.log('  agency tasks done <task-id>         Mark task completed');
    console.log('  agency tasks status <id> <status>   Update task status');
    console.log('  agency upgrade                      Pull latest updates from git');
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
