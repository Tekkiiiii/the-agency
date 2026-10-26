import { expect, mock, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { respawnNotice } from './register'
import { seenWin } from './testpaths'

type On = Parameters<TestBody>[1]

// The kit path.resolve()s every path on the HOST before a stub sees it (see testpaths.ts); stubs and expectations
// speak the canonical spelling: 'C:/Users/x/.claude/x' for a Windows path, '/home/t/.claude/x' for a POSIX one.
const WIN = { OS: 'Windows_NT', USERPROFILE: 'C:\\Users\\x' }
const HOME = 'C:\\Users\\x/.claude' // as the hook builds it: what process.run argv carry (argv are never path-resolved)
const HOME_SEEN = 'C:/Users/x/.claude' // as a stub sees an fs path
const res = (exitCode: number, stdout = '') => ({ value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } })

const MEDIUM_TERM = '## Active Projects\n\n| Project | Path |\n|---|---|\n| proj | x |\n'

// The engine beneath the mod on a machine whose python is described by `works` (launchers that are a real Python 3;
// anything else exits 9009 like the Windows Store stub) and `missing` (launchers that cannot start at all).
function machine(on: On, env: Record<string, string>, works: string[], missing: string[] = []) {
  mock.env(on, env)
  const argvs: string[][] = []
  const inits: Array<{ stdin?: string; env?: Record<string, string> } | undefined> = []
  const reads: string[] = []
  const logs: string[] = []
  let n = 0
  on('fs.read', (_$, e) => {
    const path = seenWin(e.path)
    reads.push(path)
    return { value: path.endsWith('/memory/medium-term.md') ? MEDIUM_TERM : 'standard' }
  })
  on('process.run', (_$, e) => {
    const argv = [...e.argv]
    argvs.push(argv)
    inits.push(e.init)
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
  return { argvs, inits, reads, logs }
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
  expect(m.reads).toContain(`${HOME_SEEN}/.hook-profile`)
  const s = scripts(m.argvs)
  expect(s.map(a => a[0]?.replace(/^.*\/\.claude\//, '<home>/'))).toEqual(['<home>/hooks/lib/model-pin.py', expect.stringMatching(/\/bin\/ledger\.py$/), expect.stringMatching(/\/bin\/ledger\.py$/)])
  expect(s[0]?.[0]).toBe(`${HOME}/hooks/lib/model-pin.py`)
})

test('win32: AGENCY_HOME (a drive path) beats USERPROFILE for the profile and model-pin', async ($, on) => {
  const m = machine(on, { ...WIN, AGENCY_HOME: 'D:\\agency' }, ['python3'])
  await spawnOnce($, on)
  expect(m.reads).toContain('D:/agency/.hook-profile')
  expect(scripts(m.argvs)[0]?.[0]).toBe('D:\\agency/hooks/lib/model-pin.py')
})

test('win32: router ON: the Jev gate resolves under USERPROFILE and runs before the model pin', async ($, on) => {
  const m = machine(on, { ...WIN, AGENCY_SKILL_ROUTER: '1' }, ['python3'])
  await spawnOnce($, on)
  const s = scripts(m.argvs)
  expect(s.map(a => a[0]?.replace(/^.*\/\.claude\//, '<home>/'))).toEqual(['<home>/scripts/jev-spawn-gate.py', '<home>/hooks/lib/model-pin.py', expect.stringMatching(/\/bin\/ledger\.py$/), expect.stringMatching(/\/bin\/ledger\.py$/)])
  expect(s[0]?.[0]).toBe(`${HOME}/scripts/jev-spawn-gate.py`)
})

test('win32: router ON: AGENCY_HOME (a drive path) beats USERPROFILE for the Jev gate too', async ($, on) => {
  const m = machine(on, { ...WIN, AGENCY_HOME: 'D:\\agency', AGENCY_SKILL_ROUTER: '1' }, ['python3'])
  await spawnOnce($, on)
  expect(scripts(m.argvs)[0]?.[0]).toBe('D:\\agency/scripts/jev-spawn-gate.py')
})

test('win32: router OFF: the Jev gate script is never started', async ($, on) => {
  const m = machine(on, { ...WIN, AGENCY_SKILL_ROUTER: '0' }, ['python3'])
  await spawnOnce($, on)
  expect(scripts(m.argvs).some(a => String(a[0]).endsWith('jev-spawn-gate.py'))).toBe(false)
})

test('win32: Vietnamese text and an em dash reach the ledger as UTF-8 JSON, python runs with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8', async ($, on) => {
  const m = machine(on, WIN, ['python3'])
  const prompt = 'Kiểm tra — tiếng Việt'
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn({ prompt, description: 'Mô tả — Hà Nội', subagentType: 'task-executor', tool_use_id: 't1', background: true } as never)
  const i = m.argvs.findIndex(a => a.some(x => String(x).endsWith('/bin/ledger.py')) && a.includes('start'))
  expect(i).toBeGreaterThanOrEqual(0)
  const stdin = m.inits[i]?.stdin ?? ''
  expect(stdin).not.toMatch(/\\u[0-9a-f]{4}/i) // JSON.stringify keeps non-ASCII raw: python must decode it as UTF-8
  const sent = JSON.parse(stdin) as Record<string, string>
  expect(sent.prompt).toBe(prompt)
  expect(sent.description).toBe('Mô tả — Hà Nội')
  for (const init of m.inits.filter((_, k) => !m.argvs[k]?.includes('-c'))) {
    expect(init?.env).toEqual({ PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' })
  }
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
  expect(respawnNotice('proj', 'PD proj', 'C:\\Users\\x/.claude', true)).toBe(
    'RESPAWN_REQUEST proj from background agent "PD proj". Parent contract: run /pd-resume proj now, ' +
      'then delete "C:\\Users\\x\\.claude\\state\\respawn-queue\\proj" (PowerShell Remove-Item; runbooks/respawn-contract.md).',
  )
})

test('respawn hint: win32 turn.complete hook says Remove-Item and reads the registry under USERPROFILE', async ($, on) => {
  const win = machine(on, WIN, ['python3'])
  await bgRespawn($, on)
  expect(win.reads).toContain(`${HOME_SEEN}/memory/medium-term.md`)
  expect(win.logs.find(l => l.includes('/pd-resume proj'))).toContain('Remove-Item')
})

test('respawn hint: mac turn.complete hook keeps the rm wording', async ($, on) => {
  const mac = machine(on, { HOME: '/home/t' }, ['python3'])
  await bgRespawn($, on)
  const line = mac.logs.find(l => l.includes('/pd-resume proj'))
  expect(line).toContain('rm /home/t/.claude/state/respawn-queue/proj')
  expect(line).not.toContain('Remove-Item')
})
