import { expect, mock, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

type On = Parameters<TestBody>[1]

// The kit resolves a path that is not absolute on this (POSIX) host against the plugin folder before a stub sees it;
// a real Windows drive path is absolute there. Stubs strip that prefix back off.
const norm = (p: string): string => p.replace(/^.*?(?=[A-Z]:\\)/, '')
const WIN = { OS: 'Windows_NT', USERPROFILE: 'C:\\Users\\t' }

// `profile` is what ONLY the expected hook-profile path holds; any other path reads as 'standard'.
function engine(on: On, env: Record<string, string>, profile: string, files: Map<string, string>, reads: string[], profilePath = 'C:\\Users\\t/.claude/.hook-profile') {
  mock.env(on, env)
  on('fs.read', (_$, e) => {
    const path = norm(e.path)
    reads.push(path)
    if (path.endsWith('.hook-profile')) return { value: path === profilePath ? profile : 'standard' }
    const text = files.get(path)
    if (text === undefined) throw new Error('ENOENT')
    return { value: text }
  })
  on('fs.write', (_$, e) => {
    files.set(norm(e.path), e.text)
    return { value: undefined }
  })
  on('clock.now', () => ({ value: Date.UTC(2026, 9, 6, 2, 0, 0) }))
  on('tool.call', () => ({ result: 'ok' }) as never)
}

async function five($: Parameters<TestBody>[0]) {
  let last
  for (let i = 0; i < 5; i++) last = await $.tool.call({ tool: 'Bash', command: 'npm test', agentId: 'a1' } as never)
  return last
}

test('win32: profile and stall marker live under USERPROFILE/.claude', async ($, on) => {
  const files = new Map<string, string>()
  const reads: string[] = []
  engine(on, WIN, 'standard', files, reads)
  const fifth = await five($)
  expect(reads).toContain('C:\\Users\\t/.claude/.hook-profile')
  expect(fifth?.context?.[0]).toContain('STALL DETECTED')
  expect(JSON.parse(files.get('C:\\Users\\t/.claude/session-state.json') ?? '{}')).toMatchObject({ stall_detected: true, stall_tool: 'Bash' })
  expect([...files.keys()]).toEqual(['C:\\Users\\t/.claude/session-state.json'])
})

test('win32: hook profile minimal under USERPROFILE turns the guard off', async ($, on) => {
  const files = new Map<string, string>()
  engine(on, WIN, 'minimal', files, [])
  const fifth = await five($)
  expect(fifth?.context ?? []).toEqual([])
  expect(files.size).toBe(0)
})

test('mac: paths stay under HOME', async ($, on) => {
  const files = new Map<string, string>()
  const reads: string[] = []
  engine(on, { HOME: '/home/t' }, 'standard', files, reads, '/home/t/.claude/.hook-profile')
  await five($)
  expect(reads).toContain('/home/t/.claude/.hook-profile')
  expect([...files.keys()]).toEqual(['/home/t/.claude/session-state.json'])
})
