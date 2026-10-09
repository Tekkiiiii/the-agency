import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Cache, JevDown, JevView, Limit, Usage } from '../types'

const usage = atom({ plugin: 'context-band', key: 'usage' } as const, null)
const now = atom({ plugin: 'context-band', key: 'now' } as const, 0)
const jev = atom({ plugin: 'context-band', key: 'jev' } as const, null)
// `since` of the outage we already toasted for; survives a hot reload, so one toast per outage.
const jevToasted = atom({ plugin: 'context-band', key: 'jevToasted' } as const, null)
const PANE = 'ctx-detail'

// USD per million tokens, checked against platform.claude.com pricing 2026-10-05.
// ponytail: hand-kept table, re-check when a new model family ships.
type Rate = { in: number; w5m: number; w1h: number; read: number; out: number }
const RATES: Record<string, Rate> = {
  opus: { in: 4, w5m: 5, w1h: 8, read: 0.2, out: 20 },
  sonnet: { in: 2, w5m: 2.5, w1h: 4, read: 0.2, out: 10 },
  haiku: { in: 1, w5m: 1.25, w1h: 2, read: 0.1, out: 5 },
  fable: { in: 10, w5m: 12.5, w1h: 20, read: 1, out: 50 },
}
export const rateFor = (model: string): Rate | null =>
  Object.entries(RATES).find(([family]) => model.includes(family))?.[1] ?? null

// "341k" / "1M" style, exact enough for a glance.
export const short = (n: number): string =>
  n >= 1_000_000
    ? `${+(n / 1_000_000).toFixed(n % 1_000_000 ? 2 : 0)}M`
    : n >= 1_000
      ? `${Math.round(n / 1_000)}k`
      : `${n}`

const usd = (n: number): string => `$${n < 0.1 ? n.toFixed(3) : n.toFixed(2)}`
const mmss = (ms: number): string => {
  const s = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
const hmmss = (ms: number): string => {
  const s = Math.max(0, Math.round(ms / 1000))
  const h = Math.floor(s / 3600)
  return h ? `${h}:${mmss((s % 3600) * 1000).padStart(5, '0')}` : mmss(ms)
}

// Past a day, "3d 4h"; under it, h:mm:ss.
const until = (ms: number): string => {
  const h = Math.floor(Math.max(0, ms) / 3_600_000)
  return h >= 24 ? `${Math.floor(h / 24)}d ${h % 24}h` : hmmss(ms)
}
const limitText = (label: string, w: Limit | null, at: number): string =>
  w ? `${label} ${w.percentUsed}%${w.resetsAt === null ? '' : ` ↻ ${until(w.resetsAt - at)}`}` : ''

export const windowText = (u: Usage, at: number): string =>
  [limitText('5h', u.fiveHour, at), limitText('7d', u.sevenDay, at)].filter(Boolean).join(' | ')

export type CacheView = {
  cached: number
  share: number
  leftMs: number
  lastCost: number | null
  nextWarm: number | null
  nextCold: number | null
}

export const cacheView = (c: Cache, model: string, ttlMs: number, at: number): CacheView => {
  const cached = c.read + c.write
  const sent = c.input + cached
  const r = rateFor(model)
  const w = r ? (ttlMs > 300_000 ? r.w1h : r.w5m) : 0
  const m = 1_000_000
  return {
    cached,
    share: sent ? Math.round((cached / sent) * 100) : 0,
    leftMs: ttlMs - (at - c.at),
    lastCost: r ? (c.input * r.in + c.write * w + c.read * r.read + c.output * r.out) / m : null,
    // Next request re-sends the cached prefix plus this turn's new tail.
    nextWarm: r ? (cached * r.read + (c.input + c.output) * w) / m : null,
    nextCold: r ? ((cached + c.input + c.output) * w) / m : null,
  }
}

// Band segments: each wraps as a unit on narrow panes, so none splits mid-word.
export const ctxParts = (u: Usage): string[] => {
  const pct = u.percent === null ? '—' : `${u.percent}%`
  const tok = u.tokens === null ? '—' : short(u.tokens)
  return [
    `ctx ${pct}`,
    `${tok}/${short(u.window)}`,
    u.model.replace(/^claude-/, '').replace(/\[1m\]$/, ''),
    ...(u.costUsd === null ? [] : [usd(u.costUsd)]),
  ]
}

export const line = (u: Usage, _at = 0): string => ctxParts(u).join(' | ')

// Fill bar for context %: green under 25, orange under 60, red under 80, dark red from 80.
export const bar = (percent: number | null, width = 10): { text: string; color: string } => {
  const p = Math.min(100, Math.max(0, percent ?? 0))
  const filled = Math.round((p / 100) * width)
  return {
    text: '█'.repeat(filled) + '░'.repeat(width - filled),
    color: p >= 80 ? '#8b0000' : p >= 60 ? 'red' : p >= 25 ? '#ff8c00' : 'green',
  }
}

// Band parts for the 5h/7d windows: label, fill bar, "% ↻ reset" text.
export const limitParts = (u: Usage, at: number) =>
  ([['5h', u.fiveHour], ['7d', u.sevenDay]] as const).flatMap(([label, w]) =>
    w ? [{ label, bar: bar(w.percentUsed, 8), text: limitText('', w, at).trimStart(), hot: w.percentUsed >= 90 }] : [],
  )

// Compact for a split pane; share % and the warm/cold split live in /ctx.
export const cacheLine = (v: CacheView): string => {
  const ttl = v.leftMs > 0 ? `warm ${mmss(v.leftMs)}` : 'cold'
  const next = v.nextWarm === null ? '' : ` ≈${usd(v.leftMs > 0 ? v.nextWarm : v.nextCold ?? 0)}`
  return `cache ${short(v.cached)} ${ttl}${next}`
}

const limit = (all: { kind: string; percentUsed: number; resetsAt?: string }[], kind: string): Limit | null => {
  const w = all.find(r => r.kind === kind)
  if (!w) return null
  const t = w.resetsAt ? Date.parse(w.resetsAt) : NaN
  return { percentUsed: w.percentUsed, resetsAt: Number.isNaN(t) ? null : t }
}

async function refresh($: EngineInterface, measured: boolean): Promise<void> {
  const [{ context, cost, rateLimits }, model, at] = await Promise.all([
    $.session.usage({ breakdown: 'summary' }),
    $.session.model(),
    $.clock.now(),
  ])
  const api = context.breakdown?.apiUsage ?? null
  await update($, usage, prev => ({
    tokens: context.tokens ?? null,
    window: context.window,
    percent: context.percent ?? null,
    model,
    costUsd: cost?.usd ?? null,
    // The TTL clock restarts only when a new response was measured.
    cache: api
      ? {
          input: api.input_tokens,
          read: api.cache_read_input_tokens,
          write: api.cache_creation_input_tokens,
          output: api.output_tokens,
          at: measured || !prev?.cache ? at : prev.cache.at,
        }
      : prev?.cache ?? null,
    fiveHour: limit(rateLimits, 'five_hour') ?? prev?.fiveHour ?? null,
    sevenDay: limit(rateLimits, 'seven_day') ?? prev?.sevenDay ?? null,
    categories: (context.breakdown?.categories ?? [])
      .filter(c => c.kind === 'used' || c.kind === 'deferred')
      .map(c => ({ name: c.name, tokens: c.tokens })),
  }))
}

// --- Jev router line (shadow mode): today's calls from the writer's usage log, and the outage flag. ---
// Both files belong to scripts/jev_client.py; we only read them and never re-price (`usd` is the writer's).
// The row stays hidden when neither file exists (no Jev router set up).
const DAY = 86_400_000
const TAIL_BYTES = 1_048_576 // past this, read only the log's tail: a day is a few hundred lines, ~100 KB
const JEV_POLL_MS = 10_000

type JevTotals = Omit<JevView, 'down'>
const EMPTY_JEV: JevTotals = { calls: 0, inputTokens: 0, usd: 0, fbCalls: 0, fbUsd: 0 }

/** Start of the machine-local calendar day containing `ms`, as epoch ms. */
export const dayStartMs = (ms: number): number => {
  const d = new Date(ms)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

/** Epoch ms from the writer's timestamps: ISO (zone-less means UTC) or epoch seconds/ms; NaN if unusable. */
export const toMs = (ts: unknown): number => {
  if (typeof ts === 'number') return Number.isFinite(ts) ? (ts < 1e11 ? ts * 1000 : ts) : NaN
  if (typeof ts !== 'string') return NaN
  return Date.parse(/^\d{4}-\d\d-\d\dT[\d:.]+$/.test(ts) ? `${ts}Z` : ts)
}

/** Sum one local day's lines [from, to); blank, malformed and foreign lines are skipped. */
export const tally = (text: string, from: number, to: number): JevTotals => {
  const t = { ...EMPTY_JEV }
  const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0)
  for (const raw of text.split('\n')) {
    if (!raw.trim()) continue
    let o: Record<string, unknown>
    try {
      const parsed: unknown = JSON.parse(raw)
      if (parsed === null || typeof parsed !== 'object') continue
      o = parsed as Record<string, unknown>
    } catch {
      continue
    }
    const at = toMs(o.ts)
    if (Number.isNaN(at) || at < from || at >= to) continue
    if (o.router === 'jev') {
      t.calls += 1
      t.inputTokens += num(o.input_tokens)
      t.usd += num(o.usd)
    } else if (o.router === 'haiku') {
      t.fbCalls += 1
      t.fbUsd += num(o.usd)
    }
  }
  return t
}

/** The flag file is JSON {since, ...}; a flag we cannot parse still means "down". */
export const parseDown = (text: string): JevDown => {
  try {
    const o: unknown = JSON.parse(text)
    const since = o !== null && typeof o === 'object' ? (o as { since?: unknown }).since : undefined
    return { since: since === undefined || since === null ? null : String(since) }
  } catch {
    return { since: null }
  }
}

const jevUsd = (n: number): string => `$${n.toFixed(n < 0.01 ? 4 : n < 0.1 ? 3 : 2)}`
// Local wall-clock time, matching the local day the stats are tallied over.
const hhmm = (ms: number): string => {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export const downText = (d: JevDown): string => {
  const at = d.since === null ? NaN : toMs(d.since)
  return `JEV DOWN${Number.isNaN(at) ? '' : ` since ${hhmm(at)}`} → Haiku`
}

/** The band row: `warn` (outage, drawn in the warning color) and `stats` (dim); both null = draw nothing. */
export const jevParts = (j: JevView | null): { warn: string | null; stats: string | null } => {
  if (j === null) return { warn: null, stats: null }
  const fb = j.fbCalls > 0 ? ` | Haiku-fb ${j.fbCalls} · ${jevUsd(j.fbUsd)}` : ''
  return {
    warn: j.down ? downText(j.down) : null,
    stats:
      j.calls + j.fbCalls > 0
        ? `Jev ${j.calls} · ${short(j.inputTokens)} in · ${jevUsd(j.usd)}${fb}`
        : null,
  }
}

// What we last read: skip re-reading the log while its mtime/size and the day are unchanged.
const memo: { key: string; stats: JevTotals } = { key: '', stats: EMPTY_JEV }

// The agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else <HOME or USERPROFILE>/.claude (hooks/lib/resolve-root.sh).
async function agencyRoot($: EngineInterface): Promise<string> {
  const [agency, config, home, winHome] = await Promise.all([
    $.env.get('AGENCY_HOME'),
    $.env.get('CLAUDE_CONFIG_DIR'),
    $.env.get('HOME'),
    $.env.get('USERPROFILE'),
  ])
  return agency || config || `${home || winHome || ''}/.claude`
}

// Where scripts/jev_client.py writes: <root>/memory/metrics/jev-usage.jsonl and <root>/state/skill-route/jev-down
// (JEV_USAGE_LOG / SKILL_ROUTE_STATE_DIR override). Older installs kept <root>/logs/jev-usage.jsonl and
// <root>/state/jev-down; read those only while the primary file is absent.
async function jevPaths($: EngineInterface): Promise<{ log: string; flag: string }> {
  const [root, logEnv, dirEnv] = await Promise.all([
    agencyRoot($),
    $.env.get('JEV_USAGE_LOG'),
    $.env.get('SKILL_ROUTE_STATE_DIR'),
  ])
  const pick = async (primary: string, legacy: string): Promise<string> =>
    (await $.fs.exists(primary)) || !(await $.fs.exists(legacy)) ? primary : legacy
  return {
    log: logEnv ?? (await pick(`${root}/memory/metrics/jev-usage.jsonl`, `${root}/logs/jev-usage.jsonl`)),
    flag:
      dirEnv !== undefined
        ? `${dirEnv}/jev-down`
        : await pick(`${root}/state/skill-route/jev-down`, `${root}/state/jev-down`),
  }
}

async function readDown($: EngineInterface, flag: string): Promise<JevDown | null> {
  if (!(await $.fs.exists(flag))) return null
  return parseDown(await $.fs.read(flag).catch(() => ''))
}

async function readStats($: EngineInterface, log: string, at: number): Promise<JevTotals> {
  if (!(await $.fs.exists(log))) {
    memo.key = ''
    return EMPTY_JEV
  }
  const from = dayStartMs(at)
  const st = await $.fs.stat(log)
  const key = `${from}:${st.mtimeMs}:${st.size}`
  if (key === memo.key) return memo.stats
  const text =
    st.size > TAIL_BYTES
      ? (await $.process.run(['tail', '-c', String(TAIL_BYTES), log])).stdout
      : await $.fs.read(log)
  memo.key = key
  // +26h always lands inside the next local day (a day is 23-25h with DST), so its start is the exclusive end.
  memo.stats = tally(text, from, dayStartMs(from + DAY + 2 * 3_600_000))
  return memo.stats
}

// Never throws: a missing/unreadable file just leaves the band as it was.
async function pollJev($: EngineInterface): Promise<void> {
  try {
    const [{ log, flag }, at] = await Promise.all([jevPaths($), $.clock.now()])
    const [stats, down] = await Promise.all([
      readStats($, log, at).catch(() => memo.stats),
      readDown($, flag).catch(() => null),
    ])
    const next: JevView = { ...stats, down }
    await update($, jev, prev => (JSON.stringify(prev) === JSON.stringify(next) ? prev : next))
    // One toast per outage, keyed on the flag's `since`; the writer owns the osascript alert.
    const id = down === null ? null : down.since ?? 'unknown'
    if ((await read($, jevToasted)) !== id) {
      await update($, jevToasted, () => id)
      if (down !== null) $.ui.toast(`${downText(down)} — Jev router outage`)
    }
  } catch {
    // swallow: this must never reach the band render path
  }
}

export const register: Register = (on, options) => {
  const ttlMs = options?.cacheTtl === '5m' ? 300_000 : 3_600_000
  // Background subagents we saw start; their own turn.complete means done.
  const background = new Map<string, string>()

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    await $.command.register({ name: 'ctx', description: 'Context, cache and cost in detail' })
    $.clock.every(1000, async () => update($, now, () => Date.now()))
    await refresh($, false)
    await pollJev($)
    $.clock.every(JEV_POLL_MS, async () => pollJev($))
    return result
  })

  // Session-start notice: if the Jev outage flag stands now, tell the model once.
  on('classic.SessionStart', async ($, e, next) => {
    const result = await next(e)
    try {
      const { flag } = await jevPaths($)
      const down = await readDown($, flag)
      if (down === null) return result
      const since = down.since === null ? NaN : toMs(down.since)
      const when = Number.isNaN(since) ? '' : ` since ${hhmm(since)}`
      return {
        ...result,
        additionalContext: [
          ...(result.additionalContext ?? []),
          `Jev router is DOWN${when} — routing falls back to Haiku`,
        ],
      }
    } catch {
      return result
    }
  })

  on('command.run', { command: 'ctx' }, async $ => {
    await refresh($, false)
    await $.ui.open({ id: PANE, title: 'Context detail' })
    return { text: 'Context detail pane opened.' }
  })

  on('session.measure', async ($, e, next) => {
    const result = await next(e)
    await refresh($, e.changed?.includes('context') ?? true)
    await pollJev($)
    return result
  })

  on('agent.spawn', async ($, e, next) => {
    const result = await next(e)
    if (e.background && 'agentId' in result && result.agentId) {
      background.set(result.agentId, e.description || e.subagentType)
    }
    return result
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    const label = e.agentId ? background.get(e.agentId) : undefined
    if (label !== undefined && e.agentId) {
      background.delete(e.agentId)
      $.ui.toast(`Background agent done: ${label}${e.isAborted ? ' (aborted)' : ''}`)
    }
    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const u = await read($, usage)
    if (u === null || e.props.hasSurvey) return next(e)
    const { Box, Text } = $.ui.resolve(e)
    const hot = (u.percent ?? 0) >= 80
    const at = (await read($, now)) || u.cache?.at || 0
    const v = u.cache ? cacheView(u.cache, u.model, ttlMs, at) : null
    const b = bar(u.percent, 8)
    const { warn, stats } = jevParts(await read($, jev))
    return (
      <Box key="ctx" flexDirection="column">
        {/* Two rows sized for a ~90-col split pane: this session, then account-wide.
            Segments never shrink; a narrower pane wraps whole segments. */}
        <Box key="ctx-row" flexDirection="row" flexWrap="wrap" columnGap={2}>
          {ctxParts(u).map((part, i) => (
            <Box key={`ctx-${i}`} flexDirection="row" flexShrink={0}>
              {i === 0 ? <Text key="ctx-bar" color={b.color}>{b.text} </Text> : null}
              <Text key="ctx-text" dimColor={!hot} color={hot ? 'red' : undefined}>{part}</Text>
            </Box>
          ))}
          {v && (
            <Box key="ctx-cache" flexShrink={0}>
              <Text dimColor={v.leftMs > 60_000} color={v.leftMs > 60_000 ? undefined : 'yellow'}>{cacheLine(v)}</Text>
            </Box>
          )}
        </Box>
        <Box key="acct-row" flexDirection="row" flexWrap="wrap" columnGap={2}>
          {limitParts(u, at).map(l => (
            <Box key={`lim-${l.label}`} flexDirection="row" flexShrink={0}>
              <Text key="label" dimColor>{`${l.label} `}</Text>
              <Text key="bar" color={l.bar.color}>{l.bar.text}</Text>
              <Text key="text" dimColor={!l.hot} color={l.hot ? 'red' : undefined}>{` ${l.text}`}</Text>
            </Box>
          ))}
          {warn !== null ? <Box key="jev-warn" flexShrink={0}><Text color="yellow">{warn}</Text></Box> : null}
          {stats !== null ? <Box key="jev-stats" flexShrink={0}><Text dimColor>{stats}</Text></Box> : null}
        </Box>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const u = await read($, usage)
    if (u === null) return <Text dimColor>No usage measured yet.</Text>
    const at = (await read($, now)) || u.cache?.at || 0
    const v = u.cache ? cacheView(u.cache, u.model, ttlMs, at) : null
    const pct = (n: number) => `${((n / u.window) * 100).toFixed(1)}%`
    const row = (k: string, label: string, value: string) => (
      <Text key={k}>{label.padEnd(26)}{value}</Text>
    )
    return (
      <Box flexDirection="column">
        <Text key="h1" bold>Context {u.tokens === null ? '—' : short(u.tokens)} / {short(u.window)} ({u.percent ?? '—'}%) | {u.model}</Text>
        {[...u.categories]
          .sort((a, b) => b.tokens - a.tokens)
          .map((c, i) => row(`c${i}`, `  ${c.name}`, `${short(c.tokens).padStart(6)}  ${pct(c.tokens)}`))}
        {u.cache && v && [
          <Text key="h2" bold>Last request</Text>,
          row('in', '  uncached input', short(u.cache.input)),
          row('rd', '  cache read', short(u.cache.read)),
          row('wr', '  cache write', short(u.cache.write)),
          row('out', '  output', short(u.cache.output)),
          row('lc', '  cost (est.)', v.lastCost === null ? 'unknown model' : usd(v.lastCost)),
          <Text key="h3" bold>Cache</Text>,
          row('cs', '  size', `${short(v.cached)} tok`),
          row('cp', '  share of prompt', `${v.share}%`),
          row('ct', '  TTL', `${ttlMs > 300_000 ? '1h' : '5m'} | ${v.leftMs > 0 ? `${mmss(v.leftMs)} left` : 'expired'}`),
          row('nw', '  next request warm', v.nextWarm === null ? '—' : usd(v.nextWarm)),
          row('nc', '  next request cold', v.nextCold === null ? '—' : usd(v.nextCold)),
        ]}
        <Text key="h4" bold>Session cost {u.costUsd === null ? '—' : usd(u.costUsd)}</Text>
        {(u.fiveHour || u.sevenDay) && <Text key="h5" bold>Usage windows {windowText(u, at)}</Text>}
      </Box>
    )
  })
}
