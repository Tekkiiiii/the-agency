import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { alertText, levelOf, subAlertText, subLevelOf } from './register'

const usage = (tokens: number, model: string) => ({
  input_tokens: 1_000,
  cache_read_input_tokens: tokens - 1_000,
  cache_creation_input_tokens: 0,
  output_tokens: 10,
  model,
})

async function step($: Parameters<TestBody>[0], agentId: string | undefined, model: string) {
  const stream = $.turn.step({ turnId: 't', index: 0, model, messageCount: 3, agentId } as never)
  for await (const _ of stream) {
    // drain
  }
}

const SUB = (k: number, tag: string) => `CONTEXT_PCT_ALERT: ${k}k tokens (subagent cap 300k) — ${tag}`
const WARN200 = (k: number) => SUB(k, 'WARNING (200k). Complete current task, keep it small.')
const FINISH250 = (k: number) => SUB(k, 'FINISH CURRENT TASK (250k). No new work; wrap up and report.')
const STOP300 = (k: number) =>
  SUB(k, 'STOP (300k). MANDATORY: Coord run /save-state and /coord-respawn-self; Exec write your final report now and stop.')

// A session whose agents each report a fixed context fill (tokens by agentId; main = 'main').
function world(on: Parameters<TestBody>[1], fills: Record<string, number>, agents: unknown[] = [], window = 1_000_000) {
  on('turn.step', async function* (_$, e) {
    const tokens = fills[e.agentId ?? 'main'] ?? 10_000
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'tool_use', usage: usage(tokens, e.model) }
  })
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: 0, window, percent: 0 }, rateLimits: [], cost: null } }) as never)
  on('env.get', (_$, e) => ({ value: e.name === 'HOME' ? '/home/t' : undefined }))
  on('fs.read', () => ({ value: 'standard' }))
  on('agent.list', () => ({ value: agents }) as never)
  on('tool.call', (_$, e) => {
    if (e.tool === 'Agent') return { result: { status: 'async_launched', agentId: 'c1' } } as never
    return { result: 'ok' } as never
  })
}
const bash = ($: Parameters<TestBody>[0], agentId?: string) => $.tool.call({ tool: 'Bash', command: 'ls', agentId } as never)

test('subagent absolute thresholds: 150k silent, 210k warns once, 260k finish-task once', async ($, on) => {
  const fills: Record<string, number> = { s150: 150_000, s210: 210_000, s260: 260_000 }
  world(on, fills)
  for (const id of ['s150', 's210', 's260']) await step($, id, 'claude-sonnet-5-5[1m]')
  expect((await bash($, 's150')).context ?? []).toEqual([])
  expect((await bash($, 's210')).context).toEqual([WARN200(210)])
  expect((await bash($, 's210')).context ?? []).toEqual([]) // once per crossing
  expect((await bash($, 's260')).context).toEqual([FINISH250(260)])
  expect((await bash($, 's260')).context ?? []).toEqual([])
})

test('subagent at >=300k: the stop line rides EVERY tool result', async ($, on) => {
  world(on, { s310: 310_000 })
  await step($, 's310', 'claude-sonnet-5-5[1m]')
  expect((await bash($, 's310')).context).toEqual([STOP300(310)])
  expect((await bash($, 's310')).context).toEqual([STOP300(310)])
  expect((await bash($, 's310')).deny).toBeUndefined()
  expect((await bash($)).context ?? []).toEqual([]) // main unaffected
})

test('subagent window never matters: 200k-window id at 210k tokens warns the same', async ($, on) => {
  world(on, { old: 210_000 })
  await step($, 'old', 'claude-sonnet-5-5')
  expect((await bash($, 'old')).context).toEqual([WARN200(210)])
})

test('main keeps 70/75/80 % of its window: 700k of 1M -> the 70% line, unchanged', async ($, on) => {
  world(on, { main: 700_000 })
  await step($, undefined, 'claude-opus-5-5[1m]')
  expect((await bash($)).context).toEqual(['CONTEXT_PCT_ALERT: 70% — WARNING THRESHOLD (70%). Complete current task. No new L3s.'])
  expect((await bash($)).context ?? []).toEqual([])
})

test('main at 82% gets the mandatory line', async ($, on) => {
  world(on, { main: 820_000 })
  await step($, 'main', 'claude-opus-5-5[1m]')
  expect((await bash($, 'main')).context).toEqual(['CONTEXT_PCT_ALERT: 82% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.'])
})

test('levels: main 70% and 75% warn with their own line; subagent levels are absolute', async () => {
  expect([69, 70, 74, 75, 79, 80].map(levelOf)).toEqual([0, 70, 70, 75, 75, 80])
  expect(alertText(71)).toBe('CONTEXT_PCT_ALERT: 71% — WARNING THRESHOLD (70%). Complete current task. No new L3s.')
  expect([199_999, 200_000, 249_999, 250_000, 299_999, 300_000].map(subLevelOf)).toEqual([0, 200, 200, 250, 250, 300])
  expect(subAlertText(210_000)).toBe(WARN200(210))
})

test('CHILD_CTX rides the Agent result and the SendMessage reply', async ($, on) => {
  world(on, { c1: 180_000 }, [{ id: 'c1', name: 'exec-one', type: 'general-purpose', description: 'd', status: 'running' }])
  await step($, 'c1', 'claude-sonnet-5-5[1m]')
  const spawned = await $.tool.call({ tool: 'Agent', prompt: 'x', description: 'd', subagent_type: 'general-purpose' } as never)
  expect(spawned.context).toEqual(['CHILD_CTX: exec-one 180k/300k (60%)'])
  const byName = await $.tool.call({ tool: 'SendMessage', to: 'exec-one', message: 'hi' } as never)
  expect(byName.context).toEqual(['CHILD_CTX: exec-one 180k/300k (60%)'])
  const byId = await $.tool.call({ tool: 'SendMessage', to: 'c1', message: 'hi' } as never)
  expect(byId.context).toEqual(['CHILD_CTX: exec-one 180k/300k (60%)'])
  const other = await $.tool.call({ tool: 'SendMessage', to: 'nobody', message: 'hi' } as never)
  expect(other.context ?? []).toEqual([])
})

const ALERT = (who: string, k: number, tail: string) => `CHILD_CTX_ALERT: ${who} ${k}k/300k — ${tail}`
const T250 = 'finish current task'
const T300 = 'must stop, request report now'
const kid = (id: string, extra: object = {}) => ({ id, type: 'general-purpose', description: 'd', status: 'running', ...extra })
const S = 'claude-sonnet-5-5[1m]'

test('CHILD_CTX_ALERT: 251k -> the 250k line exactly once, 301k -> the 300k line once; re-arms after a drop', async ($, on) => {
  const fills: Record<string, number> = { c1: 100_000 }
  world(on, fills, [kid('c1', { name: 'exec-one' })])
  await step($, 'c1', S)
  expect((await bash($)).context ?? []).toEqual([])
  fills.c1 = 251_000
  await step($, 'c1', S)
  expect((await bash($)).context).toEqual([ALERT('exec-one', 251, T250)])
  expect((await bash($)).context ?? []).toEqual([])
  fills.c1 = 301_000
  await step($, 'c1', S)
  expect((await bash($)).context).toEqual([ALERT('exec-one', 301, T300)])
  expect((await bash($)).context ?? []).toEqual([])
  fills.c1 = 90_000 // child compacted
  await step($, 'c1', S)
  fills.c1 = 255_000
  await step($, 'c1', S)
  expect((await bash($)).context).toEqual([ALERT('exec-one', 255, T250)])
  expect((await bash($, 'other')).context ?? []).toEqual([]) // another parent does not see this child
})

test('CHILD_CTX_ALERT: two children, only the crossing one is named', async ($, on) => {
  world(on, { a: 120_000, b: 260_000 }, [kid('a', { name: 'quiet' }), kid('b', { name: 'loud' })])
  await step($, 'a', S)
  await step($, 'b', S)
  expect((await bash($)).context).toEqual([ALERT('loud', 260, T250)])
})

test('child label: name, else the spawn description (bracket tag dropped), else agentId', async ($, on) => {
  world(on, { a: 260_000, b: 260_000, c: 260_000 }, [
    kid('a', { name: 'named', description: 'Exec-x [task:t]' }),
    kid('b', { description: 'Exec-ctxfix-NaNny [task:ctx-cap-fix]' }),
    kid('c', { description: '' }),
  ])
  for (const id of ['a', 'b', 'c']) await step($, id, S)
  expect((await bash($)).context).toEqual([ALERT('named', 260, T250), ALERT('Exec-ctxfix-NaNny', 260, T250), ALERT('c', 260, T250)])
})

test('CHILD_CTX_ALERT: a child the agent list does not know -> no line', async ($, on) => {
  world(on, { ghost: 310_000 }, [])
  await step($, 'ghost', S)
  expect((await bash($)).context ?? []).toEqual([])
})

test('turn.step stores numeric tokens in the fill record on every step', async ($, on) => {
  world(on, { c1: 123_456 }, [kid('c1')])
  const written: unknown[] = []
  on('state.set', async (_$, e, next) => {
    written.push(e)
    return next(e)
  })
  await step($, 'c1', S)
  expect(JSON.stringify(written)).toContain('"tokens":123456')
})

test('legacy fill record {pct, level, told} (no tokens): no NaN, no CHILD_CTX, no alert, no self-alert', async ($, on) => {
  // Persist c1's record in the legacy shape, as an older build of this mod left it in $.state.
  on('state.set', (_$, e, next) => {
    const { pct, level, told } = (e as { value: { pct: number; level: number; told: number } }).value
    return next((e as { id?: string }).id === 'c1' ? ({ ...e, value: { pct, level, told } } as never) : e)
  })
  world(on, { c1: 310_000 }, [kid('c1', { name: 'exec-one' })])
  await step($, 'c1', S)
  const r0 = await bash($)
  expect(r0.context ?? []).toEqual([])
  const spawned = await $.tool.call({ tool: 'Agent', prompt: 'x', description: 'd', subagent_type: 'general-purpose' } as never)
  expect(spawned.context ?? []).toEqual([])
  const msg = await $.tool.call({ tool: 'SendMessage', to: 'exec-one', message: 'hi' } as never)
  expect(msg.context ?? []).toEqual([])
  // the legacy child itself running a tool: no NaN self-alert
  expect(((await bash($, 'c1')).context ?? []).join('\n')).not.toContain('NaN')
  expect((await bash($, 'c1')).context ?? []).toEqual([])
})
