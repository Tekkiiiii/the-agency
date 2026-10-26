#!/usr/bin/env node
// check-hooks-manifest.js — hooks/hooks.json is the single list of hooks every
// install path wires into settings.json (cli/lib/hooks-merge.js). This guard
// keeps it honest:
//   1. the manifest loads (ids unique, every field present) and uses only
//      known Claude Code hook events
//   2. every command runs a script that exists in hooks/, spells the root as
//      `{root}` (never a literal ~/.claude or absolute path), and starts with
//      `bash ` (Windows runs these through Git Bash)
//   3. `retired` entries are well formed and never overlap a current command
//      (an overlap would make sync add and prune the same hook)
//   4. every wired script is documented in docs/HOOKS.md
//   5. the generated table in docs/HOOKS.md (between the hooks-manifest
//      markers) matches the manifest byte for byte
//
//   node .github/scripts/check-hooks-manifest.js           check (CI)
//   node .github/scripts/check-hooks-manifest.js --write   regenerate the table
'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');
const MANIFEST = path.join(REPO, 'hooks', 'hooks.json');
const DOC = path.join(REPO, 'docs', 'HOOKS.md');
const BEGIN = '<!-- hooks-manifest:begin -->';
const END = '<!-- hooks-manifest:end -->';
const EVENTS = new Set([
  'PreToolUse', 'PostToolUse', 'UserPromptSubmit', 'SessionStart', 'SessionEnd',
  'Stop', 'SubagentStop', 'Notification', 'PreCompact',
]);

const { loadManifest } = require(path.join(REPO, 'cli', 'lib', 'hooks-merge.js'));

const errors = [];
let manifest;
try {
  manifest = loadManifest(MANIFEST);
} catch (e) {
  console.log(`FAIL: ${e.message}`);
  process.exit(1);
}

function scriptsOf(command) {
  return [...command.matchAll(/\{root\}\/hooks\/([^\s"';&|<>()]+)/g)].map(m => m[1]);
}

const current = new Set();
for (const h of manifest.hooks) {
  current.add(h.command);
  if (!EVENTS.has(h.event)) errors.push(`${h.id}: unknown event "${h.event}"`);
  if (!/^bash \{root\}\/hooks\//.test(h.command)) errors.push(`${h.id}: command must start with "bash {root}/hooks/" (got ${h.command})`);
  if (/~\/\.claude|\$HOME|\$\{HOME\}|(^|\s)\/(Users|home)\//.test(h.command)) errors.push(`${h.id}: command hardcodes a root; use {root}`);
  const scripts = scriptsOf(h.command);
  if (scripts.length === 0) errors.push(`${h.id}: command references no {root}/hooks/ script`);
  for (const s of scripts) {
    if (!fs.existsSync(path.join(REPO, 'hooks', s))) errors.push(`${h.id}: hooks/${s} does not exist`);
  }
}
const retiredIds = new Set();
for (const r of manifest.retired) {
  if (!r || typeof r.id !== 'string' || typeof r.event !== 'string' || typeof r.command !== 'string') {
    errors.push(`retired entry needs id, event and command: ${JSON.stringify(r)}`);
    continue;
  }
  if (current.has(r.command)) errors.push(`retired ${r.id}: command is also a current manifest command`);
  if (retiredIds.has(r.id)) errors.push(`retired ${r.id}: duplicate id`);
  retiredIds.add(r.id);
}

const doc = fs.readFileSync(DOC, 'utf8');
for (const h of manifest.hooks) {
  for (const s of scriptsOf(h.command)) {
    if (!doc.includes(`### ${s} (`)) errors.push(`${h.id}: docs/HOOKS.md has no "### ${s} (...)" section`);
  }
}

function cell(s) {
  return String(s).replace(/\|/g, '\\|');
}

function table() {
  const lines = [
    BEGIN,
    '<!-- Generated from hooks/hooks.json by `node .github/scripts/check-hooks-manifest.js --write`. Do not edit by hand: CI fails when it drifts. -->',
    '',
    '| ID | Event | Matcher | Command | Purpose |',
    '|----|-------|---------|---------|---------|',
  ];
  for (const h of manifest.hooks) {
    lines.push(`| \`${h.id}\` | ${h.event} | ${h.matcher ? `\`${cell(h.matcher)}\`` : '(all)'} | \`${cell(h.command)}\` | ${cell(h.purpose)} |`);
  }
  lines.push('');
  if (manifest.retired.length === 0) {
    lines.push('Retired (pruned from `settings.json` on the next sync): none.');
  } else {
    lines.push('Retired (pruned from `settings.json` on the next sync):');
    lines.push('');
    for (const r of manifest.retired) lines.push(`- \`${r.id}\` (${r.event}): \`${cell(r.command)}\``);
  }
  lines.push(END);
  return lines.join('\n');
}

const b = doc.indexOf(BEGIN);
const e = doc.indexOf(END);
if (b < 0 || e < 0 || e < b) {
  errors.push(`docs/HOOKS.md is missing the ${BEGIN} ... ${END} markers`);
} else {
  const want = table();
  const have = doc.slice(b, e + END.length);
  if (have !== want) {
    if (process.argv.includes('--write')) {
      fs.writeFileSync(DOC, doc.slice(0, b) + want + doc.slice(e + END.length));
      console.log('wrote: docs/HOOKS.md hooks table regenerated from hooks/hooks.json');
    } else {
      errors.push('docs/HOOKS.md hooks table drifted from hooks/hooks.json; run: node .github/scripts/check-hooks-manifest.js --write');
    }
  }
}

if (errors.length) {
  for (const m of errors) console.log(`  FAIL ${m}`);
  console.log(`FAIL: check-hooks-manifest (${errors.length} problem(s))`);
  process.exit(1);
}
console.log(`OK: hooks/hooks.json (${manifest.hooks.length} hooks, ${manifest.retired.length} retired) matches hooks/ and docs/HOOKS.md`);
