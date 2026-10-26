const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');

module.exports = async function bootstrap({ args, AGENCY_ROOT, console }) {
  const scriptPath = path.resolve(__dirname, '../../scripts/bootstrap-machine.sh');

  if (!fs.existsSync(scriptPath)) {
    console.error(`\nError: bootstrap script not found at:\n  ${scriptPath}`);
    console.error('\nRe-clone or repair the-agency repo to restore it.\n');
    process.exit(1);
  }

  console.log('\nRunning machine bootstrap (3 layers: uv tools, CLI tools, MCP servers)...\n');

  const result = spawnSync('bash', [scriptPath, ...args], { stdio: 'inherit' });

  if (result.error) {
    console.error(`\nFailed to launch bootstrap script: ${result.error.message}\n`);
    process.exit(1);
  }

  if (result.status !== 0) {
    process.exit(result.status);
  }
};
