import { expect, mock, test } from 'claude-code/testing'

import { seenPosix, seenWin } from './testpaths'

type On = Parameters<typeof mock.env>[0]

// Fixtures are machine-local times (the band's day is the local day), so the suite passes in any time zone.
const at = (day: number, h: number, m = 0): Date => new Date(2026, 9, day, h, m)
const NOW = at(7, 12).getTime()
const ROWS = [
  JSON.stringify({ ts: at(7, 1).toISOString(), purpose: 'skill-route', router: 'jev', input_tokens: 20_000, usd: 0.00084 }),
  JSON.stringify({ ts: at(7, 3).toISOString(), purpose: 'skill-route', router: 'haiku', input_tokens: 900, usd: 0.004 }),
].join('\n')
const WIN_LOG_ARG = 'C:\\Users\\x/.claude/memory/metrics/jev-usage.jsonl' // as the hook builds it: what the tail/python argv carry (never path-resolved)
// The kit path.resolve()s every fs path on the HOST before a stub sees it (see testpaths.ts); fixtures are keyed by the
// canonical spelling: 'C:/Users/x/.claude/x' for a Windows path, '/home/t/.claude/x' for a POSIX one.
const WIN_LOG = 'C:/Users/x/.claude/memory/metrics/jev-usage.jsonl'
const WIN = { OS: 'Windows_NT', USERPROFILE: 'C:\\Users\\x' }

// The file system beneath the mod: only `files` exist; `sizes` makes a file big enough to need its tail.
function world(on: On, env: Record<string, string>, files: Record<string, string>, sizes: Record<string, number> = {}, norm = seenWin) {
  mock.env(on, env)
  mock.clock(on, { now: NOW })
  const reads: string[] = []
  on('fs.exists', (_$, e) => ({ value: norm((e as { path: string }).path) in files }))
  on('fs.read', (_$, e) => {
    const path = norm((e as { path: string }).path)
    reads.push(path)
    if (sizes[path]) throw new Error('whole-file read of a big log')
    return { value: files[path] ?? '' }
  })
  on('fs.stat', (_$, e) => {
    const path = norm((e as { path: string }).path)
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
  return reads
}

const draw = async ($: any) => {
  await $.session.measure({ context: { tokens: 100_000, window: 1_000_000, percent: 10 }, rateLimits: [], changed: ['context'] })
  const ui = await $.ui.mount({
    plugin: 'context-band',
    surface: 'terminal',
    component: 'AbovePrompt',
    props: { hasSurvey: false, isWorking: false, maxRows: 10, columns: 100 } as never,
  })
  return JSON.stringify(await ui.drawn())
}

const runResult = (exitCode: number, stdout: string) => ({ value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never

test('win32: the Jev log is found under USERPROFILE when JEV_USAGE_LOG is unset', async ($, on) => {
  world(on, WIN, { [WIN_LOG]: ROWS })
  expect(await draw($)).toContain('Jev 1 · 20k in · $0.0008 | Haiku-fb 1 · $0.0040')
})

test('win32: the outage flag is found under USERPROFILE/.claude/state/skill-route', async ($, on) => {
  world(on, WIN, { 'C:/Users/x/.claude/state/skill-route/jev-down': JSON.stringify({ since: at(7, 14, 5).toISOString() }) })
  expect(await draw($)).toContain('JEV DOWN since 14:05 → Haiku')
})

test('mac: the Jev log is still found under HOME', async ($, on) => {
  world(on, { HOME: '/home/t' }, { '/home/t/.claude/memory/metrics/jev-usage.jsonl': ROWS }, {}, seenPosix)
  expect(await draw($)).toContain('Jev 1 · 20k in · $0.0008')
})

// Distinct sizes below: the mod remembers the last log it read by mtime/size, across tests.
const BIG = { [WIN_LOG]: ROWS }

test('win32: tail cannot start -> the python one-liner reads the log tail', async ($, on) => {
  world(on, WIN, BIG, { [WIN_LOG]: 5_000_011 })
  const argvs: string[][] = []
  on('process.run', (_$, e) => {
    const argv = [...(e as { argv: readonly string[] }).argv]
    argvs.push(argv)
    if (argv[0] === 'tail') throw new Error('spawn tail ENOENT')
    return runResult(0, `partial-first-line\n${ROWS}\n`)
  })
  expect(await draw($)).toContain('Jev 1 · 20k in · $0.0008 | Haiku-fb 1 · $0.0040')
  expect(argvs[0]).toEqual(['tail', '-c', '1048576', WIN_LOG_ARG])
  expect(argvs[1]?.slice(0, 2)).toEqual(['python3', '-c'])
  expect(argvs[1]?.[2]).toContain('f.seek(max(0,n-int(sys.argv[2])))')
  expect(argvs[1]?.slice(3)).toEqual([WIN_LOG_ARG, '1048576'])
})

test('tail exits non-zero -> the python one-liner takes over', async ($, on) => {
  world(on, WIN, BIG, { [WIN_LOG]: 5_000_022 })
  const first: string[] = []
  on('process.run', (_$, e) => {
    const argv = [...(e as { argv: readonly string[] }).argv]
    first.push(String(argv[0]))
    return argv[0] === 'tail' ? runResult(1, '') : runResult(0, `partial\n${ROWS}\n`)
  })
  expect(await draw($)).toContain('Jev 1 · 20k in')
  expect(first).toEqual(['tail', 'python3'])
})

test('tail works -> python is never started', async ($, on) => {
  world(on, WIN, BIG, { [WIN_LOG]: 5_000_033 })
  const first: string[] = []
  on('process.run', (_$, e) => {
    first.push(String((e as { argv: readonly string[] }).argv[0]))
    return runResult(0, `partial\n${ROWS}\n`)
  })
  expect(await draw($)).toContain('Jev 1 · 20k in')
  expect(first).toEqual(['tail'])
})
