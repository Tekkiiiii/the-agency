import type { Register } from 'claude-code'

// Startup token diet. The caveman and ponytail plugins inject their full rule
// text (~300 and ~1000 tokens) as hook context at every session and subagent
// start. This hook rewrites each such text block to a compact version that
// keeps the ACTIVE level and points at the skill for the full rules. Anything
// that does not match passes through untouched; a row is never dropped.

type Voice = 'CAVEMAN' | 'PONYTAIL'

// Marker as both plugins emit it: "<NAME> MODE ACTIVE — level: <level>".
const MARKER = /(CAVEMAN|PONYTAIL) MODE ACTIVE — level: ([a-z][a-z0-9-]*)/g
// The context may arrive inside a short wrapper (a hook-success line, a tag).
const MAX_WRAPPER = 200
const WRAPPER_END = '</system-reminder>'

const COMPACT: Record<Voice, (level: string, row: string) => string> = {
  CAVEMAN: (level, row) =>
    `CAVEMAN MODE ACTIVE — level: ${level} (compact; full rules: /caveman)\n\n` +
    'Respond terse like smart caveman. All technical substance stay. Only fluff die.\n' +
    'Active every response, no drift. Off only: "stop caveman" / "normal mode". Switch: /caveman lite|full|ultra.\n' +
    'Drop: articles, filler (just/really/basically), pleasantries, hedging. Fragments OK. Short synonyms. ' +
    'Technical terms exact. Code blocks unchanged. Errors quoted exact.\n' +
    'Pattern: [thing] [action] [reason]. [next step].\n' +
    'Auto-clarity: drop caveman for security warnings, irreversible-action confirmations, risky multi-step order, ' +
    'or when user asks to clarify. Resume after. Code/commits/PRs: write normal.' +
    row,
  PONYTAIL: (level, row) =>
    `PONYTAIL MODE ACTIVE — level: ${level} (compact; full rules: /ponytail)\n\n` +
    'Lazy senior dev: efficient, not careless. Best code is code never written. ' +
    'Active every response; off only "stop ponytail" / "normal mode". Switch: /ponytail lite|full|ultra.\n' +
    'Ladder, stop at first rung that holds: needed at all (YAGNI)? > already in codebase, reuse > stdlib > native platform ' +
    '> installed dep > one line > minimum code. Read the code first. Bug fix = root cause: grep callers, fix once.\n' +
    'No unrequested abstractions or scaffolding; delete over add; fewest files; mark shortcuts `ponytail:`. ' +
    'Output: code, then max 3 short lines (skipped X, add when Y).\n' +
    'Never skip: input validation, data-loss handling, security, accessibility, anything requested.' +
    row,
}

// The active level's row of the original's intensity table, if it carries one,
// so a non-default level keeps its meaning.
function levelRow(segment: string, level: string): string {
  const m = new RegExp(`^\\|\\s*\\*\\*${level}\\*\\*\\s*\\|(.*)\\|\\s*$`, 'm').exec(segment)
  const body = m?.[1]?.trim()
  return body ? `\nLevel ${level}: ${body.slice(0, 120)}` : ''
}

// Rewrites every matching injection inside one text block; returns the same
// string (identical reference) when nothing matched, so callers can tell.
export function compactText(text: string): string {
  const hits = [...text.matchAll(MARKER)]
  const first = hits[0]
  if (!first || first.index > MAX_WRAPPER) return text

  let out = ''
  let cursor = 0
  let changed = false
  hits.forEach((m, i) => {
    const start = m.index
    const next = hits[i + 1]?.index ?? text.length
    const wrapperEnd = text.indexOf(WRAPPER_END, start)
    const end = wrapperEnd === -1 ? next : Math.min(next, wrapperEnd)
    const segment = text.slice(start, end).trimEnd()
    const compact = COMPACT[m[1] as Voice](m[2] as string, levelRow(segment, m[2] as string))
    // Already compact, or an injection shorter than the compact form (e.g. the
    // one-line "level: commit" notice): leave as is.
    if (segment.includes('full rules: /') || segment.length <= compact.length) return
    out += text.slice(cursor, start) + compact
    cursor = start + segment.length
    changed = true
  })
  return changed ? out + text.slice(cursor) : text
}

export const register: Register = (on) => {
  on('session.append', { door: 'hook-context' }, ($, e, next) => {
    let changed = false
    const content = e.message.content.map(block => {
      const original: unknown = block.type === 'text' ? (block as { text?: unknown }).text : undefined
      if (typeof original !== 'string') return block
      const text = compactText(original)
      if (text === original) return block
      changed = true
      return { ...block, text }
    })
    if (!changed) return next(e)
    return next({ ...e, message: { ...e.message, content } })
  })
}
