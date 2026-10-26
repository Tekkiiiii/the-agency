#!/usr/bin/env node
// check-ps1-ascii.js - every PowerShell / cmd source file must be ASCII-only.
//
// Why: Windows PowerShell 5.1 reads a script that has no UTF-8 BOM as ANSI
// (cp1252). The three UTF-8 bytes of an em dash (E2 80 94) become the three
// characters U+00E2 U+20AC U+201D, and U+201D / U+201C (what 0x94 / 0x93 map
// to) are string terminators to the PowerShell parser. A single dash inside a
// quoted string ends the string early and the whole script fails to parse,
// before a single line runs. This is how install.ps1 broke on a real
// Windows PowerShell 5.1 machine while the CI job (PowerShell 7, UTF-8 by
// default) stayed green.
//
// Usage:
//   node .github/scripts/check-ps1-ascii.js            scan every tracked
//        *.ps1 *.psm1 *.psd1 *.cmd *.bat (git ls-files)
//   node .github/scripts/check-ps1-ascii.js <file>...  scan these files instead
//        (used by the negative test)
//
// Prints file:line:col and the hex byte for every non-ASCII byte. Exit 1 if any.
// No dependencies.
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const EXT = /\.(ps1|psm1|psd1|cmd|bat)$/i;

function trackedFiles() {
  const out = execFileSync('git', ['ls-files', '-z'], { cwd: REPO, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  return out.split('\0').filter(f => f && EXT.test(f)).map(f => path.join(REPO, f));
}

// Returns [{line, col, byte}] for every byte > 0x7F. col is the 1-based BYTE
// column, which is what the hex dump of the offending line shows.
function scanBuffer(buf) {
  const hits = [];
  let line = 1;
  let lineStart = 0;
  for (let i = 0; i < buf.length; i++) {
    const b = buf[i];
    if (b === 0x0a) { line++; lineStart = i + 1; continue; }
    if (b > 0x7f) hits.push({ line, col: i - lineStart + 1, byte: b });
  }
  return hits;
}

function main(argv) {
  const explicit = argv.length > 0;
  const files = explicit ? argv.map(f => path.resolve(f)) : trackedFiles();
  if (files.length === 0) {
    console.log('FAIL: check-ps1-ascii: no *.ps1/*.psm1/*.psd1/*.cmd/*.bat files found (is this a git checkout?)');
    return 1;
  }
  let bad = 0;
  let badFiles = 0;
  for (const f of files) {
    let buf;
    try { buf = fs.readFileSync(f); } catch (e) { console.log(`FAIL: cannot read ${f}: ${e.message}`); return 1; }
    const rel = path.relative(process.cwd(), f) || f;
    const hits = scanBuffer(buf);
    if (hits.length) badFiles++;
    for (const h of hits) {
      console.log(`${rel}:${h.line}:${h.col}: non-ASCII byte 0x${h.byte.toString(16).toUpperCase().padStart(2, '0')}`);
    }
    bad += hits.length;
  }
  if (bad) {
    console.log(`\nFAIL: check-ps1-ascii: ${bad} non-ASCII byte(s) in ${badFiles} file(s). Windows PowerShell 5.1 reads BOM-less scripts as cp1252; keep these files ASCII-only.`);
    return 1;
  }
  console.log(`OK: check-ps1-ascii: ${files.length} file(s), all ASCII`);
  return 0;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));

module.exports = { scanBuffer, main };
