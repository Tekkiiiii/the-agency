const { readFileSync, existsSync, readdirSync } = require('fs');
const { join } = require('path');

module.exports = async function status({ AGENCY_ROOT, console }) {
  const projectsPath = `${AGENCY_ROOT}/projects`;

  if (!existsSync(projectsPath)) {
    console.log('No projects found. Run: agency init');
    return;
  }

  const projects = readdirSync(projectsPath).filter(p =>
    existsSync(`${projectsPath}/${p}/STATE.md`)
  );

  if (projects.length === 0) {
    console.log('No projects found. Run: agency init && agency new <name> "<desc>"');
    return;
  }

  console.log('The Agency — Projects\n');
  for (const slug of projects) {
    const statePath = `${projectsPath}/${slug}/STATE.md`;
    try {
      const content = readFileSync(statePath, 'utf-8');
      const lines = content.split('\n');
      const phase = lines.find(l => l.startsWith('**Phase**:'))?.replace('**Phase**:', '').trim() || '?';
      const status = lines.find(l => l.startsWith('**Status**:'))?.replace('**Status**:', '').trim() || '?';
      const updated = lines.find(l => l.startsWith('**Last updated**:'))?.replace('**Last updated**:', '').trim() || '?';
      console.log(`  ${slug.padEnd(20)} ${status.padEnd(10)} phase:${phase.padEnd(12)} updated:${updated}`);
    } catch {
      console.log(`  ${slug} (error reading state)`);
    }
  }
  console.log('');
};
