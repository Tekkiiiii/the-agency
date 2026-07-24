#!/usr/bin/env node
/**
 * Guard against the flat-skill layout regressing.
 *
 * Canonical skill layout is directory-only: skills/<name>/SKILL.md. A flat
 * skills/<name>.md file is invisible to cli/commands/sync-assets.js and
 * silently never ships to installs — see
 * ~/.claude/projects/the-agency/memory/tasks/completed/skill-sync-structural-fix/
 * for the incident this script exists to prevent from recurring.
 *
 * Exit 0 = clean. Exit 1 = flat skill file(s) found, printed to stderr.
 * Run via: node scripts/check-flat-skills.js
 * Wired into: cli/package.json "test" script.
 */

const { readdirSync } = require('fs');
const { join, resolve } = require('path');

const repoRoot = resolve(__dirname, '..');
const skillsDir = join(repoRoot, 'skills');
const ALLOWED = new Set(['INDEX.md', 'README.md']);

const entries = readdirSync(skillsDir, { withFileTypes: true });
const flatFiles = entries
  .filter(e => e.isFile() && e.name.endsWith('.md') && !ALLOWED.has(e.name))
  .map(e => e.name);

if (flatFiles.length > 0) {
  console.error('✗ Flat skill files found in skills/ — canonical layout is directory-only.');
  console.error('  Each must move to skills/<name>/SKILL.md:');
  for (const f of flatFiles) {
    console.error(`    skills/${f}`);
  }
  console.error('');
  console.error('  Flat files are invisible to syncSkills() and never reach installs.');
  process.exit(1);
}

console.log(`✓ No flat skill files — ${entries.filter(e => e.isDirectory()).length} skills all directory-layout.`);
process.exit(0);
