#!/usr/bin/env node
// check-never-distribute.js - fail the build when a git-tracked path or file
// carries something on .github/scripts/never-distribute.txt (third-party
// skills that are not licensed for distribution).
//
//   node .github/scripts/check-never-distribute.js            scan the repo this script lives in
//   node .github/scripts/check-never-distribute.js <dir>      scan the git repo at <dir>
//   node .github/scripts/check-never-distribute.js --self-test  plant a skill dir + an id in a throwaway repo; must be caught
//
// Exit 0 = clean, 1 = findings, 2 = could not run. Plain node, ubuntu + windows.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const sha = t => crypto.createHash('sha256').update(t).digest('hex');

const LIST = path.join(__dirname, 'never-distribute.txt');
const CONTENT_EXEMPT = new Set(['.github/scripts/never-distribute.txt']);
const MAX_BYTES = 2 * 1024 * 1024;

function git(dir, args) {
  const r = spawnSync('git', args, { cwd: dir, encoding: 'buffer', maxBuffer: 256 * 1024 * 1024 });
  if (r.error || r.status !== 0) throw new Error(`git ${args.join(' ')} failed in ${dir}: ${r.error ? r.error.message : String(r.stderr)}`);
  return r.stdout;
}

function loadList() {
  const dirs = new Set(), ids = [], hashes = new Set();
  for (const raw of fs.readFileSync(LIST, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const m = /^(dir|id|idhash)\s*\|\s*(.+)$/.exec(line);
    if (!m) throw new Error(`bad line in never-distribute.txt: ${line}`);
    if (m[1] === 'dir') dirs.add(m[2].trim());
    else if (m[1] === 'idhash') hashes.add(m[2].trim().toLowerCase());
    else ids.push(m[2].trim().toLowerCase());
  }
  if (!dirs.size || !(ids.length || hashes.size)) throw new Error('never-distribute.txt has no entries');
  return { dirs, ids, hashes };
}

function scan(dir, list) {
  const out = [];
  const files = git(dir, ['ls-files', '-z']).toString('utf8').split('\0').filter(Boolean);
  for (const f of files) {
    const parts = f.split('/').slice(0, -1);
    const at = parts.indexOf('skills');
    const segs = at < 0 ? [] : parts.slice(at + 1); // dir rule: anything below a skills/ segment
    for (const s of segs) if (list.dirs.has(s)) { out.push(`${f}: path has blocked directory "${s}"`); break; }
    if (CONTENT_EXEMPT.has(f)) continue;
    const abs = path.join(dir, f);
    let st; try { st = fs.statSync(abs); } catch (e) { continue; }
    if (!st.isFile() || st.size > MAX_BYTES) continue;
    const buf = fs.readFileSync(abs);
    if (buf.includes(0)) continue;
    const lines = buf.toString('utf8').toLowerCase().split('\n');
    for (let i = 0; i < lines.length; i++) {
      const id = list.ids.find(x => lines[i].includes(x));
      if (id) { out.push(`${f}:${i + 1}: contains blocked identifier "${id}"`); break; }
      if (list.hashes.size && lines[i].split(/[^a-z0-9]+/).some(t => t && list.hashes.has(sha(t)))) {
        out.push(`${f}:${i + 1}: contains a blocked identifier (hashed entry)`); break;
      }
    }
  }
  return out;
}

function selfTest() {
  const list = { dirs: new Set(['blocked-dir']), ids: ['zxq-plain-id'], hashes: new Set([sha('zxqhashed')]) };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'never-dist-'));
  try {
    git(tmp, ['init', '-q']);
    fs.mkdirSync(path.join(tmp, 'skills', 'blocked-dir'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'skills', 'blocked-dir', 'SKILL.md'), 'x\n');
    fs.writeFileSync(path.join(tmp, 'a.md'), 'credit: ZXQ-plain-id\n');
    fs.writeFileSync(path.join(tmp, 'b.md'), 'credit: example.org/ZXQhashed/x\n');
    git(tmp, ['add', '-A']);
    const hits = scan(tmp, list);
    const ok = hits.some(h => h.includes('blocked directory')) && hits.some(h => h.startsWith('a.md') && h.includes('blocked identifier'))
      && hits.some(h => h.startsWith('b.md') && h.includes('hashed'));
    if (!ok) { console.error('self-test FAILED: planted leaks not caught:\n' + hits.join('\n')); return 1; }
    console.log(`self-test ok: ${hits.length} planted hit(s) caught`);
    return 0;
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}

try {
  const list = loadList();
  const arg = process.argv[2];
  if (arg === '--self-test') process.exit(selfTest());
  const dir = arg ? path.resolve(arg) : path.resolve(__dirname, '..', '..');
  const hits = scan(dir, list);
  if (hits.length) {
    console.error('never-distribute: blocked third-party content is tracked:\n  ' + hits.join('\n  '));
    console.error('See .github/scripts/never-distribute.txt. Delete the files; do not allowlist.');
    process.exit(1);
  }
  console.log('never-distribute: clean');
} catch (e) { console.error('never-distribute: could not run: ' + e.message); process.exit(2); }
