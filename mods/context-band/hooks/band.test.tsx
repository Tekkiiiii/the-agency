import { expect, mock, test } from 'claude-code/testing'

import { bar, cacheLine, cacheView, dayStartMs, downText, jevParts, limitParts, line, ctxParts, parseDown, rateFor, short, tally } from './register'

const base = { model: 'claude-opus-5-5[1m]', cache: null, categories: [], fiveHour: null, sevenDay: null }

// ui.toast resolves to void; the test engine reads a bare `undefined` as "no result" and
// reports the hook unimplemented. `{ value: undefined }` is the answer.
const toastSink = (into: string[]) => (_$: unknown, e: { text?: string }) => {
  into.push(String(e.text))
  return { value: undefined } as never
}

test('formats a 1M window line', async () => {
  expect(short(1_000_000)).toBe('1M')
  expect(short(341_200)).toBe('341k')
  expect(line({ ...base, tokens: 341_200, window: 1_000_000, percent: 34, costUsd: 1.5 })).toBe(
    'ctx 34% | 341k/1M | opus-5-5 | $1.50',
  )
})

test('cache math, costs and 5h/7d window timers', async () => {
  const c = { input: 1_000, read: 150_000, write: 10_000, output: 2_000, at: 0 }
  const v = cacheView(c, 'claude-opus-5-5[1m]', 3_600_000, 600_000)
  expect(v.cached).toBe(160_000)
  expect(v.share).toBe(99) // 160k of 161k sent
  expect(v.leftMs).toBe(3_000_000) // 10 min elapsed of 60
  // 1k*4 + 10k*8 + 150k*0.2 + 2k*20 = 4k + 80k + 30k + 40k = 154k micro-$ = $0.154
  expect(v.lastCost?.toFixed(3)).toBe('0.154')
  // warm: 160k*0.2 + 3k*8 = 32k + 24k = $0.056; cold: 163k*8 = $1.304
  expect(v.nextWarm?.toFixed(3)).toBe('0.056')
  expect(v.nextCold?.toFixed(3)).toBe('1.304')
  expect(cacheLine(v)).toBe('cache 160k warm 50:00 ≈$0.056')
  expect(cacheLine({ ...v, leftMs: -1 })).toBe('cache 160k cold ≈$1.30')
  expect(rateFor('some-other-model')).toBe(null)
  const u = { ...base, tokens: 1, window: 1_000_000, percent: 0, costUsd: null,
    fiveHour: { percentUsed: 42, resetsAt: 8_000_000 },
    sevenDay: { percentUsed: 61, resetsAt: 1_000 + (3 * 24 + 4) * 3_600_000 + 59_000 } }
  expect(line(u, 1_000)).toBe('ctx 0% | 1/1M | opus-5-5')
  expect(limitParts(u, 1_000)).toEqual([
    { label: '5h', bar: { text: '███░░░░░', color: '#ff8c00' }, text: '42% ↻ 2:13:19', hot: false },
    { label: '7d', bar: { text: '█████░░░', color: 'red' }, text: '61% ↻ 3d 4h', hot: false },
  ])
  expect(limitParts({ ...u, fiveHour: null, sevenDay: { percentUsed: 95, resetsAt: null } }, 0)).toEqual([
    { label: '7d', bar: { text: '████████', color: '#8b0000' }, text: '95%', hot: true },
  ])
})

test('band draws usage and cache rows after a measure', async ($, on) => {
  on('session.usage', () => ({ value: {
    startedAt: 0,
    context: {
      tokens: 412_000, window: 1_000_000, percent: 41,
      breakdown: {
        categories: [{ name: 'Messages', tokens: 300_000, kind: 'used' }],
        apiUsage: { input_tokens: 1_000, cache_read_input_tokens: 400_000, cache_creation_input_tokens: 10_000, output_tokens: 1_000 },
      },
    },
    rateLimits: [],
    cost: { usd: 2.25 },
  } }) as never)
  on('session.model', () => ({ value: 'claude-opus-5-5[1m]' }))
  on('clock.now', () => ({ value: 1_000 }))
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return <Box />
  })
  on('session.measure', () => ({ changed: ['context'] }))
  await $.session.measure({
    context: { tokens: 412_000, window: 1_000_000, percent: 41 },
    rateLimits: [],
    changed: ['context'],
  })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({
      plugin: 'context-band',
      surface,
      component: 'AbovePrompt',
      props: { hasSurvey: false, isWorking: false, maxRows: 10, columns: 100 } as never,
    })
    const drawn = JSON.stringify(await ui.drawn())
    for (const part of ['ctx 41%', '412k/1M', 'opus-5-5', '$2.25']) expect(drawn).toContain(part)
    expect(drawn).toContain('"flexWrap":"wrap"')
    expect(drawn).toContain('cache 410k warm')
  }
})

test('toasts when a background subagent finishes', async ($, on) => {
  const toasts: string[] = []
  on('agent.spawn', () => ({ model: 'sonnet', agentId: 'a1' }))
  on('turn.complete', (_$, e) => ({ text: e.answer }))
  on('ui.toast', toastSink(toasts))
  await $.agent.spawn({ prompt: 'x', description: 'qa sweep', subagentType: 'task-executor', background: true } as never)
  await $.turn.complete({ answer: 'done', durationMs: 5, isAborted: false, turnId: 't', agentId: 'a1', reason: 'answer' } as never)
  expect(toasts).toEqual(['Background agent done: qa sweep'])
})

test('context bar fills and shifts green, orange, red, dark red', async () => {
  expect(bar(20)).toEqual({ text: '██░░░░░░░░', color: 'green' })
  expect(bar(34)).toEqual({ text: '███░░░░░░░', color: '#ff8c00' })
  expect(bar(60).color).toBe('red')
  expect(bar(80).color).toBe('#8b0000')
  expect(bar(null).text).toBe('░░░░░░░░░░')
  expect(bar(130).text).toBe('██████████')
})

// --- Jev line ---------------------------------------------------------------------------------------
// Fixtures are built from machine-local times so the suite passes in any time zone:
// "now" is 2026-10-07 12:00 local, and the local day is [10-07 00:00, 10-08 00:00).
const at = (day: number, h: number, m = 0, s = 0): Date => new Date(2026, 9, day, h, m, s)
const iso = (day: number, h: number, m = 0, s = 0): string => at(day, h, m, s).toISOString()
const NOW = at(7, 12).getTime()
const FROM = dayStartMs(NOW)
const TO = at(8, 0).getTime()
const row = (o: object) => JSON.stringify(o)
const mixed = [
  row({ ts: iso(7, 1), purpose: 'skill-route', router: 'jev', input_tokens: 20_000, output_tokens: 10, usd: 0.00084, ok: true, shadow: true }),
  row({ ts: iso(7, 2).replace('Z', '123'), purpose: 'spawn-plan', router: 'jev', input_tokens: 14_500, output_tokens: 10, usd: 0.000609, ok: true, shadow: true }), // zone-less = UTC
  row({ ts: iso(7, 3), purpose: 'skill-route', router: 'haiku', input_tokens: 900, output_tokens: 50, usd: 0.004, ok: true, shadow: true }),
  row({ ts: iso(6, 23, 59, 59), router: 'jev', input_tokens: 99_999, usd: 9 }), // 23:59:59 yesterday
  row({ ts: iso(7, 0), router: 'jev', input_tokens: 500, usd: 0.0001 }), // 00:00:00 today
  row({ ts: iso(8, 0), router: 'jev', input_tokens: 99_999, usd: 9 }), // tomorrow 00:00
].join('\n')

test('day boundary is the machine-local midnight', async () => {
  expect(FROM).toBe(at(7, 0).getTime())
  expect(dayStartMs(at(7, 23, 59, 59).getTime())).toBe(FROM)
  expect(dayStartMs(at(8, 0).getTime())).toBe(TO)
})

test('tally sums today only, skips malformed and foreign lines', async () => {
  const t = tally(`${mixed}\n{broken json\n\n"str"\nnull\n${row({ ts: 'nope', router: 'jev', usd: 5 })}\n${row({ ts: iso(7, 4), router: 'other', usd: 5 })}\n${row({ ts: iso(7, 4), router: 'jev', input_tokens: 'x', usd: null })}\n`, FROM, TO)
  expect(t.calls).toBe(4) // 3 good jev lines + the one with unusable numbers (counted as a call, 0 tokens/usd)
  expect(t.inputTokens).toBe(20_000 + 14_500 + 500)
  expect(+t.usd.toFixed(9)).toBe(0.001549)
  expect(t.fbCalls).toBe(1)
  expect(t.fbUsd).toBe(0.004)
  expect(tally('', FROM, TO)).toEqual({ calls: 0, inputTokens: 0, usd: 0, fbCalls: 0, fbUsd: 0 })
})

test('jev text: stats, fallback part only when used, outage in its own part', async () => {
  const j = { calls: 12, inputTokens: 34_500, usd: 0.0015, fbCalls: 2, fbUsd: 0.004, down: null }
  expect(jevParts(j)).toEqual({ warn: null, stats: 'Jev 12 · 35k in · $0.0015 | Haiku-fb 2 · $0.0040' })
  expect(jevParts({ ...j, fbCalls: 0, fbUsd: 0 }).stats).toBe('Jev 12 · 35k in · $0.0015')
  expect(jevParts({ ...j, calls: 0, inputTokens: 0, usd: 0, fbCalls: 0, fbUsd: 0 })).toEqual({ warn: null, stats: null })
  expect(jevParts(null)).toEqual({ warn: null, stats: null })
  const down = { since: iso(7, 14, 5) }
  expect(downText(down)).toBe('JEV DOWN since 14:05 → Haiku')
  expect(downText({ since: null })).toBe('JEV DOWN → Haiku')
  expect(jevParts({ ...j, calls: 0, fbCalls: 0, down })).toEqual({ warn: 'JEV DOWN since 14:05 → Haiku', stats: null })
  expect(parseDown(JSON.stringify({ since: down.since, failures: 3 }))).toEqual(down)
  expect(parseDown('garbage')).toEqual({ since: null })
  expect(parseDown('')).toEqual({ since: null })
})

const LOG = '/tmp/fixture/jev-usage.jsonl'
const FLAG = '/tmp/fixture-state/jev-down'
type Files = Record<string, string>

// Stand in for the file system and environment beneath the mod: the real log is never touched.
type On = Parameters<typeof mock.env>[0]
const world = (on: On, files: Files, sizes: Record<string, number> = {}, env?: Record<string, string>) => {
  mock.env(on, env ?? { JEV_USAGE_LOG: LOG, SKILL_ROUTE_STATE_DIR: '/tmp/fixture-state' })
  mock.clock(on, { now: NOW })
  on('fs.exists', (_$, e) => ({ value: (e as { path: string }).path in files }))
  on('fs.read', (_$, e) => {
    const path = (e as { path: string }).path
    if (sizes[path]) throw new Error('whole-file read of a big log')
    return { value: files[path] ?? '' }
  })
  on('fs.stat', (_$, e) => {
    const path = (e as { path: string }).path
    const size = sizes[path] ?? (files[path] ?? '').length
    return { value: { kind: 'file', size, mtimeMs: size, isLink: false } } as never
  })
  on('session.usage', () => ({ value: {
    startedAt: 0,
    context: { tokens: 100_000, window: 1_000_000, percent: 10, breakdown: { categories: [] } },
    rateLimits: [],
    cost: { usd: 1 },
  } }) as never)
  on('session.model', () => ({ value: 'claude-opus-5-5[1m]' }))
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return <Box />
  })
  on('session.measure', () => ({ changed: ['context'] }))
}

const measureAndDraw = async ($: any) => {
  await $.session.measure({ context: { tokens: 100_000, window: 1_000_000, percent: 10 }, rateLimits: [], changed: ['context'] })
  const ui = await $.ui.mount({
    plugin: 'context-band',
    surface: 'terminal',
    component: 'AbovePrompt',
    props: { hasSurvey: false, isWorking: false, maxRows: 10, columns: 100 } as never,
  })
  return JSON.stringify(await ui.drawn())
}

test('band: no usage log, no flag draws no Jev row', async ($, on) => {
  world(on, {})
  const drawn = await measureAndDraw($)
  expect(drawn).toContain('ctx 10%')
  expect(drawn).not.toContain('Jev')
  expect(drawn).not.toContain('JEV')
})

test('band: today mixed jev/haiku lines, yesterday and malformed excluded', async ($, on) => {
  world(on, { [LOG]: `${mixed}\n{oops\n` })
  const drawn = await measureAndDraw($)
  // 3 jev calls today (20000 + 14500 + 500 = 35000 in), $0.001549; 1 haiku fallback $0.004
  expect(drawn).toContain('Jev 3 · 35k in · $0.0015 | Haiku-fb 1 · $0.0040')
  expect(drawn).not.toContain('JEV DOWN')
  expect(drawn).not.toContain('99k')
})

test('band: outage flag shows warning text and toasts once per outage', async ($, on) => {
  const files: Files = { [FLAG]: JSON.stringify({ since: iso(7, 14, 5), last_failure: iso(7, 14, 6), reason: 'timeout', failures: 2 }) }
  world(on, files)
  const toasts: string[] = []
  on('ui.toast', toastSink(toasts))
  const first = await measureAndDraw($)
  expect(first).toContain('JEV DOWN since 14:05 → Haiku')
  expect(first).toContain('yellow')
  await measureAndDraw($)
  await measureAndDraw($)
  expect(toasts.length).toBe(1) // same `since`: no repeat
  expect(toasts[0]).toContain('JEV DOWN since 14:05')
  // recovery, then a new outage with a new `since` toasts again
  delete files[FLAG]
  expect(await measureAndDraw($)).not.toContain('JEV DOWN')
  files[FLAG] = JSON.stringify({ since: iso(7, 16, 30) })
  expect(await measureAndDraw($)).toContain('JEV DOWN since 16:30 → Haiku')
  expect(toasts.length).toBe(2)
})

// No JEV_* overrides: the paths come from the agency root (AGENCY_HOME here), repo layout first.
const ROOT = '/tmp/ctx-band-root'
const ROOT_ENV = { AGENCY_HOME: ROOT }

test('band: default paths follow scripts/jev_client.py under the agency root', async ($, on) => {
  const files: Files = {
    [`${ROOT}/memory/metrics/jev-usage.jsonl`]: mixed,
    [`${ROOT}/state/skill-route/jev-down`]: JSON.stringify({ since: iso(7, 14, 5) }),
    [`${ROOT}/logs/jev-usage.jsonl`]: row({ ts: iso(7, 5), router: 'jev', input_tokens: 77_000, usd: 1 }), // legacy: ignored while primary exists
  }
  world(on, files, {}, ROOT_ENV)
  const drawn = await measureAndDraw($)
  expect(drawn).toContain('Jev 3 · 35k in · $0.0015 | Haiku-fb 1 · $0.0040')
  expect(drawn).toContain('JEV DOWN since 14:05 → Haiku')
})

test('band: legacy logs/ and state/ paths are read only when the repo paths are absent', async ($, on) => {
  world(on, { [`${ROOT}/logs/jev-usage.jsonl`]: mixed, [`${ROOT}/state/jev-down`]: JSON.stringify({ since: iso(7, 14, 5) }) }, {}, ROOT_ENV)
  const drawn = await measureAndDraw($)
  expect(drawn).toContain('Jev 3 · 35k in')
  expect(drawn).toContain('JEV DOWN since 14:05 → Haiku')
})

test('band: with neither file under the root the Jev row stays hidden', async ($, on) => {
  world(on, {}, {}, ROOT_ENV)
  const drawn = await measureAndDraw($)
  expect(drawn).not.toContain('Jev')
  expect(drawn).not.toContain('JEV')
})

test('band: flag and stats together share one row; unreadable flag still reads as down', async ($, on) => {
  world(on, { [LOG]: mixed, [FLAG]: 'not json' })
  const drawn = await measureAndDraw($)
  expect(drawn).toContain('JEV DOWN → Haiku')
  expect(drawn).toContain('Jev 3 · 35k in')
})

test('session start notice when the outage flag stands', async ($, on) => {
  world(on, { [FLAG]: JSON.stringify({ since: iso(7, 14, 5) }) })
  on('classic.SessionStart', () => ({ additionalContext: ['other hook'] }))
  const withFlag = await $.classic.SessionStart({ source: 'startup' } as never)
  expect(withFlag.additionalContext).toEqual([
    'other hook',
    'Jev router is DOWN since 14:05 — routing falls back to Haiku',
  ])
})

test('no session start notice without the flag', async ($, on) => {
  world(on, {})
  on('classic.SessionStart', () => ({}))
  const r = await $.classic.SessionStart({ source: 'startup' } as never)
  expect(r.additionalContext).toBeUndefined()
})

test('band: a log past 1 MiB is read through its tail, not whole', async ($, on) => {
  world(on, { [LOG]: 'x' }, { [LOG]: 5_000_000 })
  let argv: readonly string[] = []
  on('process.run', (_$, e) => {
    argv = (e as { argv: readonly string[] }).argv
    return { value: { exitCode: 0, stdout: `partial-first-line\n${mixed}\n`, stderr: '' } } as never
  })
  const drawn = await measureAndDraw($)
  expect(argv).toEqual(['tail', '-c', '1048576', LOG])
  expect(drawn).toContain('Jev 3 · 35k in · $0.0015 | Haiku-fb 1 · $0.0040')
})

test('band segments split so a narrow pane wraps whole segments', async () => {
  expect(ctxParts({ ...base, tokens: 64_000, window: 1_000_000, percent: 6, costUsd: 1.07 })).toEqual([
    'ctx 6%', '64k/1M', 'opus-5-5', '$1.07',
  ])
  expect(ctxParts({ ...base, tokens: null, window: 200_000, percent: null, costUsd: null })).toEqual([
    'ctx —', '—/200k', 'opus-5-5',
  ])
})

test('split pane: worst-case rows fit 88 columns', async () => {
  const u = { ...base, model: 'claude-sonnet-5-5[1m]', tokens: 999_000, window: 1_000_000, percent: 100, costUsd: 123.45,
    fiveHour: { percentUsed: 100, resetsAt: 5 * 3_600_000 }, sevenDay: { percentUsed: 100, resetsAt: 6 * 86_400_000 + 23 * 3_600_000 } }
  const v = cacheView({ input: 1_000, read: 999_000, write: 0, output: 1_000, at: 0 }, u.model, 3_600_000, 0)
  const gap = '  '
  const row1 = `${bar(100, 8).text} ${ctxParts(u).join(gap)}${gap}${cacheLine(v)}`
  const jev = jevParts({ calls: 999, inputTokens: 9_990_000, usd: 99.99, fbCalls: 0, fbUsd: 0, down: null }).stats
  const row2 = [...limitParts(u, 0).map(l => `${l.label} ${l.bar.text} ${l.text}`), jev].join(gap)
  expect(row1.length).toBeLessThanOrEqual(88)
  expect(row2.length).toBeLessThanOrEqual(88)
})
