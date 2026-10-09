import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { alertText, levelOf } from './register'

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

test('red-green: subagent at 75% gets the notice, main at 10% does not', async ($, on) => {
  // Main: 100k of a 1M window = 10%. Subagent: 150k of a 200k window = 75%.
  on('turn.step', async function* (_$, e) {
    const tokens = e.agentId === 'sub1' ? 150_000 : 100_000
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'tool_use', usage: usage(tokens, e.model) }
  })
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: 100_000, window: 1_000_000, percent: 10 }, rateLimits: [], cost: null } }) as never)
  on('env.get', (_$, e) => ({ value: e.name === 'HOME' ? '/home/t' : undefined }))
  on('fs.read', () => ({ value: 'standard' }))
  on('tool.call', () => ({ result: 'ok' }) as never)

  await step($, undefined, 'claude-opus-5-5[1m]')
  await step($, 'sub1', 'claude-sonnet-5-5')

  const sub = await $.tool.call({ tool: 'Bash', command: 'ls', agentId: 'sub1' } as never)
  const main = await $.tool.call({ tool: 'Bash', command: 'ls' } as never)
  expect(sub.context).toEqual(['CONTEXT_PCT_ALERT: 75% — WARNING THRESHOLD (75%). Complete current task. No new L3s.'])
  expect(main.context ?? []).toEqual([])

  // Once per crossing: the next call carries nothing.
  const again = await $.tool.call({ tool: 'Bash', command: 'pwd', agentId: 'sub1' } as never)
  expect(again.context ?? []).toEqual([])
})

test('levels: 70% and 75% warn with their own line', async () => {
  expect([69, 70, 74, 75, 79, 80].map(levelOf)).toEqual([0, 70, 70, 75, 75, 80])
  expect(alertText(71)).toBe('CONTEXT_PCT_ALERT: 71% — WARNING THRESHOLD (70%). Complete current task. No new L3s.')
})

test('80% is the mandatory line; a 1M subagent at 150k stays quiet', async ($, on) => {
  on('turn.step', async function* (_$, e) {
    const tokens = e.agentId === 'big' ? 150_000 : 165_000
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'tool_use', usage: usage(tokens, e.model) }
  })
  on('env.get', (_$, e) => ({ value: e.name === 'HOME' ? '/home/t' : undefined }))
  on('fs.read', () => ({ value: 'standard' }))
  on('tool.call', () => ({ result: 'ok' }) as never)
  await step($, 'small', 'claude-sonnet-5-5')
  await step($, 'big', 'claude-sonnet-5-5[1m]')
  const small = await $.tool.call({ tool: 'Read', file_path: '/x', agentId: 'small' } as never)
  const big = await $.tool.call({ tool: 'Read', file_path: '/x', agentId: 'big' } as never)
  expect(small.context).toEqual(['CONTEXT_PCT_ALERT: 82% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.'])
  expect(big.context ?? []).toEqual([])
})
