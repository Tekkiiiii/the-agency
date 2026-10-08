#!/usr/bin/env node
// check-privacy.js - fail the build when a git-tracked file carries private data.
//
//   node .github/scripts/check-privacy.js              scan the repo this script lives in
//   node .github/scripts/check-privacy.js <dir>        scan the git repo at <dir>
//   node .github/scripts/check-privacy.js --self-test  plant data in a throwaway repo; must be caught
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
//   term      a personal term from the C4 rule in the sync brief (the operator's
//             name, employer, client and personal project slugs). Case-sensitive and
//             alphanumeric-bounded, so the GitHub org name does not match the first name.
//
// Justified hits live in .github/scripts/privacy-allowlist.txt:
//   rule | path-glob | line-regex (or -) | one-line justification
// "*" in a path-glob matches within a path segment, "**" across segments; rule "*"
// matches every rule. Findings print file:line and a truncated excerpt, never the
// whole secret. Exit 0 = clean, 1 = findings, 2 = could not run.
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

// C4 personal terms. Add a term here only if its hits in the tree are not generic
// English; a term that is also a normal word belongs behind an allowlist line, not
// in a looser regex. Pervasive generic names (system-improvement, ai-engineer,
// agent-memory, ltv, website-pitch, Obsidian) are deliberately NOT here.
const TERMS = [
  'Tekki', 'TekkiSolutions', 'tekkisolutions', 'SeaBank', 'SeABank', 'HTI Group',
  'Indochina', 'AgencyFlow', 'agencyflow', 'amani', 'frigate', 'maximus', 'pipedeck',
  'inlay', 'marketsense', 'cv-bach-dat', 'tekki-sticks', 'morpheus',
  'ai-tool-directory', 'content-agent', 'the-agency-pd', 'datbgt1', 'Buzz',
];

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
const TERM_RES = TERMS.map(t => ({ t, re: termRe(t) }));

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

function scanLine(text) {
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
  for (const { t, re } of TERM_RES) {
    if (re.test(text)) hits.push(['term', t]);
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

function scan(dir, allow) {
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
      for (const [rule, match] of scanLine(text)) {
        if (allowed(allow, rule, f, text)) continue;
        findings.push({ file: f, line: i + 1, rule, excerpt: match.length > 14 ? match.slice(0, 14) + '...' : match });
      }
    });
  }
  return { scanned, findings };
}

function report(res) {
  for (const x of res.findings) console.log(`PRIVACY ${x.file}:${x.line}: ${x.rule}: ${x.excerpt}`);
  return res.findings.length;
}

function selfTest() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'privacy-selftest-'));
  const id = ['aaaaaaaa', 'bbbb', 'cccc', 'dddd', 'eeeeeeeeeeee'].join('-');
  try {
    git(tmp, ['init', '-q']);
    const plant = (name, body) => { fs.writeFileSync(path.join(tmp, name), body); git(tmp, ['add', '--', name]); };

    plant('clean.md', 'See you@example.com or noreply@anthropic.com, /Users/you/x, C:\\Users\\<name>\\x, sk-ant-[A-Za-z0-9]{8,}\n');
    const clean = scan(tmp, []);
    if (clean.findings.length) { report(clean); console.log('SELF-TEST FAIL: placeholders were flagged'); return 1; }

    const cases = [
      ['notebook', 'line one\n**Notebook ID:** ' + id + '\n'],
      ['notebook', 'https://notebooklm.google.com/notebook/' + id + '\n'],
      ['email', 'mail jane.doe@gmail.com\n'],
      ['userpath', 'cd /Users/janedoe/work\n'],
      ['key', 'KEY=pcsk_' + 'A1b2C3d4E5f6G7h8I9j0' + '\n'],
      ['term', 'ask ' + TERMS[0] + ' first\n'],
    ];
    let bad = 0;
    cases.forEach(([rule, body], n) => {
      const name = `plant-${n}.md`;
      plant(name, body);
      const r = scan(tmp, []);
      const hit = r.findings.find(x => x.file === name && x.rule === rule);
      if (!hit) { console.log(`SELF-TEST FAIL: rule "${rule}" missed ${name}`); bad++; }
      else console.log(`self-test ok: ${rule} caught at ${hit.file}:${hit.line}`);
      git(tmp, ['rm', '-q', '-f', '--', name]);
    });
    plant('allow.md', 'ask ' + TERMS[0] + ' first\n');
    const rules = [{ rule: 'term', path: globToRe('allow.md'), line: null }];
    if (scan(tmp, rules).findings.length) { console.log('SELF-TEST FAIL: allowlist did not suppress'); bad++; }
    else console.log('self-test ok: allowlist suppresses a justified hit');
    return bad ? 1 : 0;
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

function main() {
  const arg = process.argv[2];
  try {
    if (arg === '--self-test') {
      const rc = selfTest();
      console.log(rc ? 'check-privacy self-test: FAIL' : 'check-privacy self-test: PASS');
      process.exit(rc);
    }
    const dir = arg ? path.resolve(arg) : path.resolve(SCRIPT_DIR, '..', '..');
    const allow = loadAllowlist(ALLOWLIST);
    const res = scan(dir, allow);
    const n = report(res);
    if (n) {
      console.log(`check-privacy: FAIL - ${n} finding(s) in ${res.scanned} tracked text files. Remove the data, or add a justified line to .github/scripts/privacy-allowlist.txt.`);
      process.exit(1);
    }
    console.log(`check-privacy: PASS - ${res.scanned} tracked text files, ${allow.length} allowlist entries`);
  } catch (e) {
    console.error('check-privacy: ERROR - ' + e.message);
    process.exit(2);
  }
}

main();
