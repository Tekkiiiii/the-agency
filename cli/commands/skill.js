const { existsSync, readdirSync, copyFileSync, mkdirSync } = require('fs');
const { join } = require('path');

module.exports = async function skill({ args, AGENCY_ROOT, console }) {
  const [subcmd, ...rest] = args;
  const skillsSrc = join(__dirname, '../../skills');
  const skillsDest = join(AGENCY_ROOT, 'skills');

  if (subcmd === 'list') {
    if (!existsSync(skillsDest)) {
      console.log('No skills installed. Run: agency init');
      return;
    }
    const entries = readdirSync(skillsDest, { withFileTypes: true });
    const skills = entries
      .filter(e => e.isDirectory() && existsSync(join(skillsDest, e.name, 'SKILL.md')))
      .map(e => e.name)
      .sort();

    if (skills.length === 0) {
      console.log('No skills installed. Run: agency init');
      return;
    }
    console.log(`Installed skills (${skills.length}):\n`);
    for (const s of skills) {
      console.log(`  ${s}`);
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

    const srcFile = join(skillsSrc, `${name}.md`);
    const destDir = join(skillsDest, name);
    const destFile = join(destDir, 'SKILL.md');

    if (!existsSync(skillsSrc)) {
      console.error(`Skill source not found: ${skillsSrc}`);
      process.exit(1);
    }

    if (!existsSync(srcFile)) {
      if (existsSync(destFile)) {
        console.log(`Skill "${name}" already installed.`);
        return;
      }
      console.error(`Skill "${name}" not found in source library.`);
      process.exit(1);
    }

    mkdirSync(destDir, { recursive: true });
    copyFileSync(srcFile, destFile);
    console.log(`\n✅ Skill "${name}" installed.\n`);
    console.log(`  Source: ${srcFile}`);
    console.log(`  Dest:   ${destFile}\n`);
    return;
  }

  console.error('Usage: agency skill list | agency skill install <name>');
  process.exit(1);
};
