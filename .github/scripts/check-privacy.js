#!/usr/bin/env node
// check-privacy.js - fail the build when a git-tracked file carries private data.
//
//   node .github/scripts/check-privacy.js                       scan the repo this script lives in
//   node .github/scripts/check-privacy.js <dir>                 scan the git repo at <dir>
//   node .github/scripts/check-privacy.js --require-denylist    exit 2 when no denylist is configured
//   node .github/scripts/check-privacy.js --self-test           plant data in a throwaway repo; must be caught
//
// Scans exactly what `git ls-files` lists (so untracked scratch never matters and
// anything that would ship does). Rules:
//
//   notebook  a NotebookLM notebook ID or URL: the word "notebook" followed within
//             40 chars by a UUID (covers "Notebook ID: <uuid>", "Notebook: <uuid>",
//             notebooklm.google.com/notebook/<uuid>)
//   email     an address that is not an obvious placeholder (example.com/.org/.net,
//             *.invalid/*.test/*.localhost, noreply@anthropic.com,
//             users.noreply.github.com, you@/your@ style locals)
//   userpath  /Users/<name> or C:\Users\<name> where <name> is not a placeholder
//   key       pcsk_ / sk-ant- followed by 16+ key characters (the bare prefix in docs
//             or a regex such as sk-ant-[A-Za-z0-9_-]{8,} does not match)
//   term      a private term from the denylist. Case-sensitive and alphanumeric-bounded.
//             The list is never stored in the repo. It comes from, in order:
//               1. env PRIVACY_DENYLIST            newline-separated terms (CI secret)
//               2. env AGENCY_PRIVACY_DENYLIST_FILE  path to a file, one term per line
//             Blank lines and lines starting with # are ignored. With neither set the
//             term rule is skipped (a notice says how to enable it) and the generic
//             rules still run; --require-denylist turns that into exit 2.
//
// Terms and the secret are never printed. Findings show file:line and the rule; a
// term hit shows only the word "term". Other excerpts are truncated.
//
// Justified hits live in .github/scripts/privacy-allowlist.txt:
//   rule | path-glob | line-regex (or -) | one-line justification
// "*" in a path-glob matches within a path segment, "**" across segments; rule "*"
// matches every rule. Exit 0 = clean, 1 = findings, 2 = could not run.
//
// Portable: plain node, runs unchanged on the ubuntu and windows runners.

'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const SCRIPT_DIR = __dirname;
const ALLOWLIST = path.join(SCRIPT_DIR, 'privacy-allowlist.txt');
const MAX_BYTES = 2 * 1024 * 1024;

const UUID = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';

const NOTEBOOK_RE = new RegExp('notebook[^\\n]{0,40}?' + UUID, 'i');
const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}/g;
const EMAIL_OK_DOMAIN = /(^|\.)(example\.(com|org|net)|[a-z0-9-]+\.(invalid|test|localhost)|users\.noreply\.github\.com)$/i;
const EMAIL_OK_LOCAL = /^(you|your|your[-_.][a-z0-9._-]*|you[-_.][a-z0-9._-]*)$/i;

const USER_RE = /(?:\/Users\/|[A-Za-z]:\\Users\\)([^\/\\\s'"`)\]},;:]+)/g;
const USER_OK = /^(you|your|yourname|your-name|username|user|name|me|x|\.\.\.|\u2026|<[^>]*>?|\{[^}]*\}?|\$.*|%.*|\*)$/i;

const KEY_RE = /\b(pcsk_|sk-ant-)([A-Za-z0-9_-]{16,})/g;
const KEY_PLACEHOLDER = /^(x+|X+|\.+|0+|\*+|your|redacted|example|placeholder)/i;

function termRe(t) {
  const esc = t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp('(?<![A-Za-z0-9])' + esc + '(?![A-Za-z0-9])');
}

// Returns { terms, source } where source is 'env', 'file' or null.
function loadDenylist(env) {
  let raw = null, source = null;
  if (env.PRIVACY_DENYLIST && env.PRIVACY_DENYLIST.trim()) {
    raw = env.PRIVACY_DENYLIST; source = 'env';
  } else if (env.AGENCY_PRIVACY_DENYLIST_FILE) {
    try { raw = fs.readFileSync(env.AGENCY_PRIVACY_DENYLIST_FILE, 'utf8'); source = 'file'; }
    catch (e) { throw new Error('cannot read AGENCY_PRIVACY_DENYLIST_FILE'); }
  }
  if (raw === null) return { terms: [], source: null };
  const terms = raw.split(/\r?\n/).map(l => l.trim()).filter(l => l && !l.startsWith('#'));
  return { terms: Array.from(new Set(terms)), source };
}

function globToRe(g) {
  let out = '';
  for (let i = 0; i < g.length; i++) {
    const c = g[i];
    if (c === '*') {
      if (g[i + 1] === '*') { out += '.*'; i++; } else out += '[^/]*';
    } else out += c.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp('^' + out + '$');
}

function loadAllowlist(file) {
  const rules = [];
  if (!fs.existsSync(file)) return rules;
  fs.readFileSync(file, 'utf8').split(/\r?\n/).forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith('#')) return;
    const f = line.split(' | ').map(s => s.trim());
    if (f.length < 4 || !f[3]) {
      throw new Error(`${path.basename(file)}:${i + 1}: need "rule | path-glob | line-regex or - | justification"`);
    }
    rules.push({ rule: f[0], path: globToRe(f[1]), line: f[2] === '-' ? null : new RegExp(f[2]) });
  });
  return rules;
}

function allowed(allow, rule, file, text) {
  return allow.some(a => (a.rule === '*' || a.rule === rule) && a.path.test(file) && (!a.line || a.line.test(text)));
}

function scanLine(text, termRes) {
  const hits = [];
  const nb = text.match(NOTEBOOK_RE);
  if (nb) hits.push(['notebook', nb[0]]);
  for (const m of text.matchAll(EMAIL_RE)) {
    const at = m[0].lastIndexOf('@');
    const local = m[0].slice(0, at);
    const domain = m[0].slice(at + 1);
    if (m[0].toLowerCase() === 'noreply@anthropic.com') continue;
    if (EMAIL_OK_DOMAIN.test(domain) || EMAIL_OK_LOCAL.test(local)) continue;
    hits.push(['email', m[0]]);
  }
  for (const m of text.matchAll(USER_RE)) {
    if (!USER_OK.test(m[1])) hits.push(['userpath', m[0]]);
  }
  for (const m of text.matchAll(KEY_RE)) {
    if (!KEY_PLACEHOLDER.test(m[2])) hits.push(['key', m[1] + m[2]]);
  }
  for (const re of termRes) {
    if (re.test(text)) hits.push(['term', 'term']);
  }
  return hits;
}

function git(dir, args) {
  const r = spawnSync('git', args, { cwd: dir, encoding: 'buffer', maxBuffer: 256 * 1024 * 1024 });
  if (r.error || r.status !== 0) {
    throw new Error(`git ${args.join(' ')} failed in ${dir}: ${r.error ? r.error.message : String(r.stderr)}`);
  }
  return r.stdout;
}

function scan(dir, allow, termRes) {
  const files = git(dir, ['ls-files', '-z']).toString('utf8').split('\0').filter(Boolean);
  const findings = [];
  let scanned = 0;
  for (const f of files) {
    const p = path.join(dir, f);
    let buf;
    try {
      const st = fs.statSync(p);
      if (!st.isFile() || st.size > MAX_BYTES) continue;
      buf = fs.readFileSync(p);
    } catch (e) { continue; }            // tracked but deleted in the worktree
    if (buf.indexOf(0) !== -1) continue; // binary
    scanned++;
    buf.toString('utf8').split(/\r?\n/).forEach((text, i) => {
      if (text.length > 20000) text = text.slice(0, 20000);
      for (const [rule, match] of scanLine(text, termRes)) {
        if (allowed(allow, rule, f, text)) continue;
        findings.push({ file: f, line: i + 1, rule, excerpt: rule === 'term' ? '' : (match.length > 14 ? match.slice(0, 14) + '...' : match) });
      }
    });
  }
  return { scanned, findings };
}

function report(res) {
  for (const x of res.findings) console.log(`PRIVACY ${x.file}:${x.line}: ${x.rule}${x.excerpt ? ': ' + x.excerpt : ''}`);
  return res.findings.length;
}

function selfTest() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'privacy-selftest-'));
  const id = ['aaaaaaaa', 'bbbb', 'cccc', 'dddd', 'eeeeeeeeeeee'].join('-');
  const synthetic = 'ZXQ-test-term';
  const denyFile = path.join(tmp, 'denylist.txt');
  const gitDir = path.join(tmp, 'repo');
  try {
    fs.mkdirSync(gitDir);
    fs.writeFileSync(denyFile, '# synthetic denylist\n\n' + synthetic + '\n');
    const dl = loadDenylist({ AGENCY_PRIVACY_DENYLIST_FILE: denyFile });
    if (dl.source !== 'file' || dl.terms.length !== 1) { console.log('SELF-TEST FAIL: denylist file not loaded'); return 1; }
    const viaEnv = loadDenylist({ PRIVACY_DENYLIST: '#c\n' + synthetic + '\n\n' });
    if (viaEnv.source !== 'env' || viaEnv.terms.length !== 1) { console.log('SELF-TEST FAIL: env denylist not loaded'); return 1; }
    const termRes = dl.terms.map(termRe);

    git(gitDir, ['init', '-q']);
    const plant = (name, body) => { fs.writeFileSync(path.join(gitDir, name), body); git(gitDir, ['add', '--', name]); };

    plant('clean.md', 'See you@example.com or noreply@anthropic.com, /Users/you/x, C:\\Users\\<name>\\x, sk-ant-[A-Za-z0-9]{8,}, ' + synthetic + 'x\n');
    const clean = scan(gitDir, [], termRes);
    if (clean.findings.length) { report(clean); console.log('SELF-TEST FAIL: placeholders were flagged'); return 1; }

    const cases = [
      ['notebook', 'line one\n**Notebook ID:** ' + id + '\n'],
      ['notebook', 'https://notebooklm.google.com/notebook/' + id + '\n'],
      ['email', 'mail alex' + '@' + 'mail-host.org\n'],
      ['userpath', 'cd ' + '/Users/' + 'alexdoe' + '/work\n'],
      ['key', 'KEY=pcsk_' + 'A1b2C3d4E5f6G7h8I9j0' + '\n'],
      ['term', 'ask ' + synthetic + ' first\n'],
    ];
    let bad = 0;
    cases.forEach(([rule, body], n) => {
      const name = `plant-${n}.md`;
      plant(name, body);
      const r = scan(gitDir, [], termRes);
      const hit = r.findings.find(x => x.file === name && x.rule === rule);
      if (!hit) { console.log(`SELF-TEST FAIL: rule "${rule}" missed ${name}`); bad++; }
      else {
        console.log(`self-test ok: ${rule} caught at ${hit.file}:${hit.line}`);
        if (rule === 'term' && hit.excerpt) { console.log('SELF-TEST FAIL: term hit leaked its value'); bad++; }
      }
      git(gitDir, ['rm', '-q', '-f', '--', name]);
    });
    plant('plain.md', 'ask ' + synthetic + ' first\n');
    if (scan(gitDir, [], []).findings.length) { console.log('SELF-TEST FAIL: term flagged with no denylist'); bad++; }
    else console.log('self-test ok: no denylist, no term hits');
    const rules = [{ rule: 'term', path: globToRe('plain.md'), line: null }];
    if (scan(gitDir, rules, termRes).findings.length) { console.log('SELF-TEST FAIL: allowlist did not suppress'); bad++; }
    else console.log('self-test ok: allowlist suppresses a justified hit');
    return bad ? 1 : 0;
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

function main() {
  const args = process.argv.slice(2);
  const flags = args.filter(a => a.startsWith('--'));
  const pos = args.filter(a => !a.startsWith('--'));
  try {
    if (flags.includes('--self-test')) {
      const rc = selfTest();
      console.log(rc ? 'check-privacy self-test: FAIL' : 'check-privacy self-test: PASS');
      process.exit(rc);
    }
    const dir = pos[0] ? path.resolve(pos[0]) : path.resolve(SCRIPT_DIR, '..', '..');
    const dl = loadDenylist(process.env);
    if (!dl.source) {
      console.log('check-privacy: NOTICE - no private denylist configured; the term rule is skipped.');
      console.log('  Set PRIVACY_DENYLIST (newline-separated terms, e.g. a CI secret) or');
      console.log('  AGENCY_PRIVACY_DENYLIST_FILE=<path to a file with one term per line>.');
      if (flags.includes('--require-denylist')) {
        console.error('check-privacy: ERROR - --require-denylist given but no denylist is set');
        process.exit(2);
      }
    } else {
      console.log(`check-privacy: denylist loaded from ${dl.source}: ${dl.terms.length} term(s)`);
    }
    const allow = loadAllowlist(ALLOWLIST);
    const res = scan(dir, allow, dl.terms.map(termRe));
    const n = report(res);
    if (n) {
      console.log(`check-privacy: FAIL - ${n} finding(s) in ${res.scanned} tracked text files. Remove the data, or add a justified line to .github/scripts/privacy-allowlist.txt.`);
      process.exit(1);
    }
    console.log(`check-privacy: PASS - ${res.scanned} tracked text files, ${allow.length} allowlist entries, ${dl.terms.length} denylist terms`);
  } catch (e) {
    console.error('check-privacy: ERROR - ' + e.message);
    process.exit(2);
  }
}

main();
