// The project registry: ONE file, {root}/memory/medium-term.md.
//
// Every reader (skills/recall, pd-resume, pd-spawn, save-state, the spawn-log hooks
// via hooks/lib/resolve-project.sh) resolves a project slug from the Active Projects
// table in that file, and every writer (`agency new`, project-scaffolder) appends to
// it. Before this module the installer only shipped a stub at
// {root}/core/memory/medium-term.md and `agency new` registered nothing, so /recall
// printed PROJECT NOT FOUND on a fresh install.
//
// ensureRegistry() seeds the file only when it is absent and never rewrites an
// existing one. When it has to create it, it carries over the legacy copy at
// {root}/core/memory/medium-term.md (where project-scaffolder used to write), which
// is also the repo stub on a fresh install. install.sh and install.ps1 do the same
// copy; keep the three in step.

const { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync } = require('fs');
const { join, dirname } = require('path');

const SKELETON = `# Active Projects Registry

The agency's project index: one row per project. /recall, /pd-resume and the spawn
hooks resolve a slug to its memory path from this table.

## Active Projects

| Project | Memory Path | PD | Status |
|---------|-------------|----|--------|
`;

const HEADER_RE = /^\|\s*Project\s*\|\s*Memory Path\s*\|/;

function registryPath(root) { return join(root, 'memory', 'medium-term.md'); }
function legacyPath(root) { return join(root, 'core', 'memory', 'medium-term.md'); }

// Creates {root}/memory/medium-term.md if it does not exist. Returns true if it did.
function ensureRegistry(root) {
  const dest = registryPath(root);
  if (existsSync(dest)) return false;
  mkdirSync(dirname(dest), { recursive: true });
  const legacy = legacyPath(root);
  if (existsSync(legacy)) copyFileSync(legacy, dest);
  else writeFileSync(dest, SKELETON);
  return true;
}

// Appends `| slug | `<projectPath>/memory/` | slug-pd | active |` to the Active Projects
// table. Idempotent: a slug already in the first column of any table row is left alone.
// Returns true if a row was added.
function registerProject(root, slug, projectPath, status = 'active') {
  ensureRegistry(root);
  const file = registryPath(root);
  const text = readFileSync(file, 'utf8');
  const nl = text.includes('\r\n') ? '\r\n' : '\n';
  const lines = text.split(/\r?\n/);

  const exists = lines.some(l => /^\|/.test(l) && l.split('|')[1].trim() === slug);
  if (exists) return false;

  const mem = projectPath.replace(/\\/g, '/').replace(/\/+$/, '') + '/memory/';
  const row = `| ${slug} | \`${mem}\` | ${slug}-pd | ${status} |`;

  const h = lines.findIndex(l => HEADER_RE.test(l));
  if (h === -1) {
    // No recognisable table: add one rather than guess where rows belong.
    const tail = text.endsWith('\n') ? '' : nl;
    writeFileSync(file, text + tail + nl + '## Active Projects' + nl + nl +
      '| Project | Memory Path | PD | Status |' + nl + '|---------|-------------|----|--------|' + nl + row + nl);
    return true;
  }
  let end = h;
  while (end + 1 < lines.length && /^\|/.test(lines[end + 1])) end++;
  lines.splice(end + 1, 0, row);
  writeFileSync(file, lines.join(nl));
  return true;
}

module.exports = { ensureRegistry, registerProject, registryPath, legacyPath, SKELETON };
