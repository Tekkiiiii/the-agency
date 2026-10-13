import { expect, mock, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { respawnNotice } from './register'

type On = Parameters<TestBody>[1]

// The kit resolves a path that is not absolute on this (POSIX) host against the plugin folder before a stub sees it;
// a real Windows drive path is absolute there. Stubs strip that prefix back off.
const norm = (p: string): string => p.replace(/^.*?(?=[A-Z]:\\)/, '')
const WIN = { OS: 'Windows_NT', USERPROFILE: 'C:\\Users\\t' }
const HOME = 'C:\\Users\\t/.claude'
const res = (exitCode: number, stdout = '') => ({ value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } })

const MEDIUM_TERM = '## Active Projects\n\n| Project | Path |\n|---|---|\n| proj | x |\n'

// The engine beneath the mod on a machine whose python is described by `works` (launchers that are a real Python 3;
// anything else exits 9009 like the Windows Store stub) and `missing` (launchers that cannot start at all).
function machine(on: On, env: Record<string, string>, works: string[], missing: string[] = []) {
  mock.env(on, env)
  const argvs: string[][] = []
  const reads: string[] = []
  const logs: string[] = []
  let n = 0
  on('fs.read', (_$, e) => {
    reads.push(norm(e.path))
    return { value: e.path.endsWith('/memory/medium-term.md') ? MEDIUM_TERM : 'standard' }
  })
  on('process.run', (_$, e) => {
    const argv = [...e.argv]
    argvs.push(argv)
    const launcher = argv[0] === 'py' ? 'py -3' : String(argv[0])
    if (missing.includes(launcher)) throw new Error(`spawn ${launcher} ENOENT`)
    if (!works.includes(launcher)) return res(9009)
    const rest = argv.slice(launcher === 'py -3' ? 2 : 1)
    if (rest[0] === '-c') return res(0, '3\n')
    if (String(rest[0]).endsWith('/model-pin.py')) return res(0, '{"action":"pass","model":null}')
    return res(0, rest[1] === 'start' ? `sid-${++n}\n` : '')
  })
  on('ui.toast', () => ({ value: undefined }))
  on('ui.log', (_$, e) => (logs.push(e.text), { value: undefined }))
  on('turn.complete', (_$, e) => ({ text: e.answer }))
  return { argvs, reads, logs }
}

const scripts = (argvs: string[][]) =>
  argvs.filter(a => !a.includes('-c')).map(a => (a[0] === 'py' ? a.slice(2) : a.slice(1)).map(String))

async function spawnOnce($: Parameters<TestBody>[0], on: On) {
  let reached = 0
  on('agent.spawn', () => (reached++, { model: 'm', agentId: 'a1' }))
  const out = await $.agent.spawn({ prompt: 'p', description: 'd', subagentType: 'task-executor', tool_use_id: 't1', background: true } as never)
  return { reached, out }
}

test('win32: hook profile and model-pin resolve under USERPROFILE, ledger under the plugin root', async ($, on) => {
  const m = machine(on, WIN, ['python3'])
  await spawnOnce($, on)
  expect(m.reads).toContain(`${HOME}/.hook-profile`)
  const s = scripts(m.argvs)
  expect(s.map(a => a[0]?.replace(/^.*\/\.claude\//, '<home>/'))).toEqual(['<home>/hooks/lib/model-pin.py', expect.stringMatching(/\/bin\/ledger\.py$/), expect.stringMatching(/\/bin\/ledger\.py$/)])
  expect(s[0]?.[0]).toBe(`${HOME}/hooks/lib/model-pin.py`)
})

test('win32: AGENCY_HOME (a drive path) beats USERPROFILE for the profile and model-pin', async ($, on) => {
  const m = machine(on, { ...WIN, AGENCY_HOME: 'D:\\agency' }, ['python3'])
  await spawnOnce($, on)
  expect(m.reads).toContain('D:\\agency/.hook-profile')
  expect(scripts(m.argvs)[0]?.[0]).toBe('D:\\agency/hooks/lib/model-pin.py')
})

test('win32: python3 is the Store stub (exit 9009) -> every script runs through py -3 after one probe', async ($, on) => {
  const m = machine(on, WIN, ['py -3'])
  const { reached } = await spawnOnce($, on)
  expect(reached).toBe(1)
  const real = m.argvs.filter(a => !a.includes('-c'))
  const viaPy = real.filter(a => a[0] === 'py')
  expect(viaPy.length).toBeGreaterThanOrEqual(3) // model-pin retried, then the ledger calls straight through
  for (const a of viaPy) expect(a[1]).toBe('-3')
  expect(real[0]).toEqual(['python3', `${HOME}/hooks/lib/model-pin.py`]) // first try: python3
  expect(real.filter(a => a[0] === 'python3').length).toBe(1) // python3 not retried once py -3 is cached
})

test('win32: no python at all stays fail open, the spawn goes through and nothing throws', async ($, on) => {
  const m = machine(on, WIN, [], ['python3', 'py -3', 'python'])
  const { reached, out } = await spawnOnce($, on)
  expect(reached).toBe(1)
  expect(out.agentId).toBe('a1')
  expect(m.logs.some(l => l.includes('model-pin skipped (fail open)'))).toBe(true)
})

test('win32: CLAUDE_PYTHON is tried first', async ($, on) => {
  const m = machine(on, { ...WIN, CLAUDE_PYTHON: 'C:\\Py\\python.exe' }, ['C:\\Py\\python.exe'])
  await spawnOnce($, on)
  expect(m.argvs.length).toBeGreaterThanOrEqual(3)
  for (const a of m.argvs) expect(a[0]).toBe('C:\\Py\\python.exe')
  expect(m.argvs[0]?.[1]).toBe(`${HOME}/hooks/lib/model-pin.py`)
})

test('mac: one python3 process per script, no probe, no extra argv', async ($, on) => {
  const m = machine(on, { HOME: '/home/t' }, ['python3'])
  await spawnOnce($, on)
  expect(m.argvs.map(a => a[0])).toEqual(['python3', 'python3', 'python3'])
  expect(m.argvs[0]).toEqual(['python3', '/home/t/.claude/hooks/lib/model-pin.py'])
})

const bgRespawn = async ($: Parameters<TestBody>[0], on: On) => {
  on('agent.spawn', () => ({ model: 'm', agentId: 'bg1' }))
  on('tool.call', () => ({ result: 'ok' }) as never)
  await $.agent.spawn({ prompt: 'p', description: 'PD', subagentType: 'proj-pd', tool_use_id: 't9', background: true } as never)
  await $.tool.call({ tool: 'SubagentHandback', agentId: 'bg1', message: 'RESPAWN_REQUEST proj\n' } as never)
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't', agentId: 'bg1', reason: 'answer' } as never)
}

test('respawn hint: the default wording is the POSIX one, byte for byte', () => {
  const posix =
    'RESPAWN_REQUEST proj from background agent "PD proj". Parent contract: run /pd-resume proj now, ' +
    'then rm /home/t/.claude/state/respawn-queue/proj (runbooks/respawn-contract.md).'
  expect(respawnNotice('proj', 'PD proj', '/home/t/.claude')).toBe(posix)
  expect(respawnNotice('proj', 'PD proj', '/home/t/.claude', false)).toBe(posix)
})

test('respawn hint: win32 says PowerShell Remove-Item on the queue file under the agency root', () => {
  expect(respawnNotice('proj', 'PD proj', 'C:\\Users\\t/.claude', true)).toBe(
    'RESPAWN_REQUEST proj from background agent "PD proj". Parent contract: run /pd-resume proj now, ' +
      'then delete "C:\\Users\\t\\.claude\\state\\respawn-queue\\proj" (PowerShell Remove-Item; runbooks/respawn-contract.md).',
  )
})

test('respawn hint: win32 turn.complete hook says Remove-Item and reads the registry under USERPROFILE', async ($, on) => {
  const win = machine(on, WIN, ['python3'])
  await bgRespawn($, on)
  expect(win.reads).toContain(`${HOME}/memory/medium-term.md`)
  expect(win.logs.find(l => l.includes('/pd-resume proj'))).toContain('Remove-Item')
})

test('respawn hint: mac turn.complete hook keeps the rm wording', async ($, on) => {
  const mac = machine(on, { HOME: '/home/t' }, ['python3'])
  await bgRespawn($, on)
  const line = mac.logs.find(l => l.includes('/pd-resume proj'))
  expect(line).toContain('rm /home/t/.claude/state/respawn-queue/proj')
  expect(line).not.toContain('Remove-Item')
})
