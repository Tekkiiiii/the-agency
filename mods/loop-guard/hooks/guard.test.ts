import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

function engine(on: Parameters<TestBody>[1], files: Map<string, string>, env: Record<string, string> = { HOME: '/home/t' }) {
  on('env.get', (_$, e) => ({ value: env[e.name] }))
  on('fs.read', (_$, e) => {
    if (e.path.endsWith('.hook-profile')) return { value: 'standard' }
    const text = files.get(e.path)
    if (text === undefined) throw new Error('ENOENT')
    return { value: text }
  })
  on('fs.write', (_$, e) => {
    files.set(e.path, e.text)
    return { value: undefined }
  })
  on('clock.now', () => ({ value: Date.UTC(2026, 9, 6, 2, 0, 0) }))
  on('tool.call', () => ({ result: 'ok' }) as never)
}

const STATE = '/home/t/.claude/session-state.json'

test('5 identical calls in one loop warn it and write the stall marker', async ($, on) => {
  const files = new Map([[STATE, '{"was_clean": true}']])
  engine(on, files)
  const results = []
  for (let i = 0; i < 5; i++) results.push(await $.tool.call({ tool: 'Bash', command: 'npm test', agentId: 'a1' } as never))
  expect(results.slice(0, 4).every(r => (r.context ?? []).length === 0)).toBe(true)
  expect(results[4]?.context?.[0]).toBe(
    [
      '[loop-detector] STALL DETECTED: 5 identical Bash calls in a row.',
      '[loop-detector] You are likely in an infinite loop. Stop retrying and:',
      '  1. Restate your objective in one sentence',
      '  2. Verify the actual world state (read the file, check git status)',
      '  3. Try a DIFFERENT approach, not the same command again',
      '  4. If still blocked, /save-state and stop.',
    ].join('\n'),
  )
  const state = JSON.parse(files.get(STATE) ?? '{}')
  expect(state).toMatchObject({ was_clean: true, stall_detected: true, stall_tool: 'Bash' })
  expect(typeof state.stall_at).toBe('string')
  // History cleared: one fresh chance.
  const sixth = await $.tool.call({ tool: 'Bash', command: 'npm test', agentId: 'a1' } as never)
  expect(sixth.context ?? []).toEqual([])
})

test('parallel loops keep separate histories', async ($, on) => {
  const files = new Map<string, string>()
  engine(on, files)
  // Interleaved: a1 and a2 each repeat 4 times, main repeats the same command 4 times.
  for (let i = 0; i < 4; i++) {
    for (const agentId of ['a1', 'a2', undefined]) {
      const r = await $.tool.call({ tool: 'Read', file_path: '/same', agentId } as never)
      expect(r.context ?? []).toEqual([])
    }
  }
  expect(files.has(STATE)).toBe(false)
})

test('the stall marker follows AGENCY_HOME, then CLAUDE_CONFIG_DIR, then HOME/.claude', async ($, on) => {
  const files = new Map<string, string>()
  engine(on, files, { AGENCY_HOME: '/opt/agency', CLAUDE_CONFIG_DIR: '/opt/cfg', HOME: '/home/t' })
  for (let i = 0; i < 5; i++) await $.tool.call({ tool: 'Bash', command: 'npm test', agentId: 'a1' } as never)
  expect([...files.keys()]).toEqual(['/opt/agency/session-state.json'])
})
