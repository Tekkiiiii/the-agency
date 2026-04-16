const { mkdirSync, existsSync, writeFileSync } = require('fs');

module.exports = async function newProject({ args, AGENCY_ROOT, console }) {
  const [slug, ...descParts] = args;
  if (!slug) {
    console.error('Usage: agency new <project-slug> "<description>"');
    process.exit(1);
  }

  const projectPath = `${AGENCY_ROOT}/projects/${slug}`;
  if (existsSync(projectPath)) {
    console.error(`Project "${slug}" already exists.`);
    process.exit(1);
  }

  const description = descParts.join(' ') || 'New project';
  const today = new Date().toISOString().split('T')[0];

  mkdirSync(projectPath, { recursive: true });
  mkdirSync(`${AGENCY_ROOT}/sessions/${slug}`, { recursive: true });

  const state = `# ${slug} — STATE

**Last updated**: ${today}
**Phase**: init
**Status**: active

## Current work
${description}

## Blockers
None

## Next session
1. Define project scope and goals
2. Set up project structure
`;

  writeFileSync(`${projectPath}/STATE.md`, state);
  console.log(`\n✅ Project "${slug}" created at ${projectPath}\n`);
  console.log('Next: cd to your project and start working\n');
};
