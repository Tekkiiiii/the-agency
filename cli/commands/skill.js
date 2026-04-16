const { existsSync, readdirSync, copyFileSync } = require('fs');
const { join, basename } = require('path');

module.exports = async function skill({ args, AGENCY_ROOT, console }) {
  const [subcmd, ...rest] = args;
  const skillsSrc = join(__dirname, '../../skills');
  const skillsDest = `${AGENCY_ROOT}/skills`;

  if (subcmd === 'list') {
    if (!existsSync(skillsDest)) {
      console.log('No skills installed.');
      return;
    }
    const files = readdirSync(skillsDest).filter(f => f.endsWith('.md'));
    if (files.length === 0) {
      console.log('No skills installed. Run: agency skill install <name>');
      return;
    }
    console.log('Installed skills:\n');
    for (const f of files.sort()) {
      const name = f.replace('.md', '');
      console.log(`  ${name}`);
    }
    console.log('');
    return;
  }

  if (subcmd === 'install') {
    const [name] = rest;
    if (!name) {
      console.error('Usage: agency skill install <name>');
      process.exit(1);
    }

    const srcFile = `${skillsSrc}/${name}.md`;
    const destFile = `${skillsDest}/${name}.md`;

    if (!existsSync(skillsSrc)) {
      console.error(`Skill source not found: ${skillsSrc}`);
      process.exit(1);
    }

    if (!existsSync(srcFile)) {
      // Check if it's already installed
      if (existsSync(destFile)) {
        console.log(`Skill "${name}" already installed.`);
        return;
      }
      console.error(`Skill "${name}" not found in source library.`);
      process.exit(1);
    }

    if (!existsSync(skillsDest)) {
      require('fs').mkdirSync(skillsDest, { recursive: true });
    }

    copyFileSync(srcFile, destFile);
    console.log(`\n✅ Skill "${name}" installed.\n`);
    console.log(`  Source: ${srcFile}`);
    console.log(`  Dest:   ${destFile}\n`);
    return;
  }

  console.error('Usage: agency skill list | agency skill install <name>');
  process.exit(1);
};
