import { expect, mock, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { isWindows, joinPath, pickHome, pythonRunner } from './platform'
import type { PyExec, PyInit, PyRun } from './platform'
import { seenPosix, seenWin } from './testpaths'

type On = Parameters<TestBody>[1]

// The kit path.resolve()s every path on the HOST before a stub sees it (see testpaths.ts); stubs and expectations
// speak the canonical spelling: 'C:/Users/x/.claude/x' for a Windows path, '/home/t/.claude/x' for a POSIX one.
const WIN = { OS: 'Windows_NT', USERPROFILE: 'C:\\Users\\x' }
// The helpers are pure (no `$`: the loader follows `$` only inside one file), so they are tested directly.
// The mods' glue and the file paths they build are covered through the hooks below and in the other mods' win32 tests.
const res = (exitCode: number, stdout = ''): PyRun => ({ exitCode, stdout, stderr: '' })

// A process.run log plus the `exec` / `claudePython` closures a register file would pass in.
function fake(process: (argv: string[]) => PyRun, claudePython?: string) {
  const seen: string[][] = []
  const inits: PyInit[] = []
  const exec: PyExec = async (argv, init) => {
    seen.push(argv)
    inits.push(init)
    return process(argv)
  }
  return { seen, inits, exec, claudePython: async () => claudePython }
}
const go = (f: ReturnType<typeof fake>, py: ReturnType<typeof pythonRunner>, args: string[], init: PyInit = {}) =>
  py.run(args, init, f.exec, f.claudePython)

// A machine whose python is described by `works` (launchers that are a real Python 3: 'python3', 'py -3', 'python',
// a path); any other launcher exits 9009 like the Windows Store stub, or rejects when `missing` has it.
const machine = (works: string[], missing: string[] = []) => (argv: string[]): PyRun => {
  const launcher = argv[0] === 'py' ? 'py -3' : String(argv[0])
  if (missing.includes(launcher)) throw new Error(`spawn ${launcher} ENOENT`)
  if (!works.includes(launcher)) return res(9009)
  const rest = argv.slice(launcher === 'py -3' ? 2 : 1)
  return rest[0] === '-c' && String(rest[1]).includes('version_info') ? res(0, '3\n') : res(0, 'out')
}

test('isWindows: OS=Windows_NT only', () => {
  expect(isWindows('Windows_NT')).toBe(true)
  expect(isWindows(undefined)).toBe(false)
  expect(isWindows('Darwin')).toBe(false)
})

test('pickHome: Windows prefers USERPROFILE, then HOME, then HOMEDRIVE+HOMEPATH', () => {
  expect(pickHome(['Windows_NT', '/c/home/t', 'C:\\Users\\x'])).toBe('C:\\Users\\x')
  expect(pickHome(['Windows_NT', '/c/home/t'])).toBe('/c/home/t')
  expect(pickHome(['Windows_NT', undefined, undefined, 'D:', '\\Users\\x'])).toBe('D:\\Users\\x')
  expect(pickHome(['Windows_NT', undefined, undefined, 'D:'])).toBe('')
})

test('pickHome: elsewhere HOME first, then USERPROFILE; nothing set is empty; no trailing separator', () => {
  expect(pickHome([undefined, '/home/t', 'C:\\x'])).toBe('/home/t')
  expect(pickHome([undefined, undefined, 'C:\\x'])).toBe('C:\\x')
  expect(pickHome([])).toBe('')
  expect(pickHome([undefined, '', undefined, 'D:', '\\Users'])).toBe('') // HOMEDRIVE+HOMEPATH is a Windows-only fallback
  expect(pickHome([undefined, '/home/t/'])).toBe('/home/t')
  expect(pickHome(['Windows_NT', undefined, 'C:\\Users\\x\\'])).toBe('C:\\Users\\x')
})

test('joinPath: joins with /, collapses separators between parts, leaves the leading prefix alone', () => {
  expect(joinPath('/home/t', '.claude', 'x.json')).toBe('/home/t/.claude/x.json')
  expect(joinPath('C:\\Users\\x\\', '.claude', 'hooks/lib\\', 'm.py')).toBe('C:\\Users\\x/.claude/hooks/lib/m.py')
  expect(joinPath('/h/', '/.claude/', '/a')).toBe('/h/.claude/a')
  expect(joinPath('\\\\srv\\share', '.claude')).toBe('\\\\srv\\share/.claude')
  expect(joinPath('', '.claude', 'a')).toBe('/.claude/a') // no home: rooted, as `${home}/.claude/a` always was
  expect(joinPath('/')).toBe('')
})

const PROBE = ['-c', 'import sys;print(sys.version_info[0])']

test('pythonRunner: mac happy path is exactly one python3 process, with UTF-8 env and the caller init', async () => {
  const f = fake(machine(['python3']))
  const py = pythonRunner()
  expect((await go(f, py, ['s.py', 'a'], { stdin: 'in', timeoutMs: 20_000 })).stdout).toBe('out')
  expect(f.seen).toEqual([['python3', 's.py', 'a']])
  expect(f.inits[0]).toEqual({ stdin: 'in', timeoutMs: 20_000, env: { PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' } })
  await go(f, py, ['s.py'])
  expect(f.seen.map(a => a[0])).toEqual(['python3', 'python3']) // cached: still one process per call
})

test('pythonRunner: python3 is a Windows Store stub -> probes py -3, retries once, caches it', async () => {
  const f = fake(machine(['py -3']))
  const py = pythonRunner()
  expect((await go(f, py, ['s.py'])).stdout).toBe('out')
  expect(f.seen).toEqual([['python3', 's.py'], ['python3', ...PROBE], ['py', '-3', ...PROBE], ['py', '-3', 's.py']])
  f.seen.length = 0
  await go(f, py, ['t.py'])
  expect(f.seen).toEqual([['py', '-3', 't.py']])
})

test('pythonRunner: probe order is CLAUDE_PYTHON, python3, py -3, python; launchers that cannot start are skipped', async () => {
  const f = fake(machine(['python'], ['python3', 'py -3', 'C:\\Py\\python.exe']), 'C:\\Py\\python.exe')
  expect((await go(f, pythonRunner(), ['s.py'])).stdout).toBe('out')
  expect(f.seen.map(a => (a[0] === 'py' ? 'py -3' : a[0]))).toEqual([
    'C:\\Py\\python.exe', // CLAUDE_PYTHON first, cannot start
    'C:\\Py\\python.exe', 'python3', 'py -3', 'python', // probes in order
    'python', // retry
  ])
})

test('pythonRunner: CLAUDE_PYTHON is tried first and, when it works, is the only process', async () => {
  const f = fake(machine(['C:\\Py\\python.exe', 'python3']), 'C:\\Py\\python.exe')
  await go(f, pythonRunner(), ['s.py'])
  expect(f.seen).toEqual([['C:\\Py\\python.exe', 's.py']])
})

test('pythonRunner: CLAUDE_PYTHON is read only until a python is cached', async () => {
  const f = fake(machine(['python3']))
  let reads = 0
  const py = pythonRunner()
  const run = () => py.run(['s.py'], {}, f.exec, async () => (reads++, undefined))
  await run()
  await run()
  expect(reads).toBe(1)
})

test('pythonRunner: no python anywhere fails open as before (original result) and is not cached', async () => {
  const f = fake(machine([]))
  const py = pythonRunner()
  expect((await go(f, py, ['s.py'])).exitCode).toBe(9009)
  expect(f.seen.length).toBe(1 + 3) // the call, then the python3, py -3, python probes
  await go(f, py, ['s.py'])
  expect(f.seen.length).toBe(2 * (1 + 3)) // failures are never cached: probed again
})

test('pythonRunner: no python that can even start rethrows the original rejection', async () => {
  const f = fake(machine([], ['python3', 'py -3', 'python']))
  await expect(go(f, pythonRunner(), ['s.py'])).rejects.toThrow('spawn python3 ENOENT')
  expect(f.seen.length).toBe(1 + 3)
})

test('pythonRunner: a real python3 whose script fails returns that result, caches python3, and a failing call later does not probe', async () => {
  let script = 1
  const f = fake(argv => (argv[1] === '-c' ? res(0, '3\n') : res(script, 'boom')))
  const py = pythonRunner()
  expect((await go(f, py, ['s.py'])).exitCode).toBe(1)
  expect(f.seen.map(a => a[1])).toEqual(['s.py', '-c']) // one probe: python3 is the candidate that was tried
  f.seen.length = 0
  expect((await go(f, py, ['s.py'])).exitCode).toBe(1)
  expect(f.seen).toEqual([['python3', 's.py']])
  script = 0
  expect((await go(f, py, ['s.py'])).exitCode).toBe(0)
})

// --- agent-ctx integration: the hook profile path on Windows ---

const usage = (tokens: number) => ({ input_tokens: 1_000, cache_read_input_tokens: tokens - 1_000, cache_creation_input_tokens: 0, output_tokens: 10 })

async function warnedSubagent($: Parameters<TestBody>[0], on: On, env: Record<string, string>, profilePath: string, seen = seenWin) {
  mock.env(on, env)
  const reads: string[] = []
  on('turn.step', async function* (_$, e) {
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'tool_use', usage: { ...usage(150_000), model: e.model } }
  })
  on('fs.read', (_$, e) => (reads.push(seen(e.path)), { value: seen(e.path) === profilePath ? 'minimal' : 'standard' }))
  on('tool.call', () => ({ result: 'ok' }) as never)
  for await (const _ of $.turn.step({ turnId: 't', index: 0, model: 'claude-sonnet-5-5', messageCount: 3, agentId: 'sub1' } as never)) {
    // drain
  }
  const ran = await $.tool.call({ tool: 'Bash', command: 'ls', agentId: 'sub1' } as never)
  return { reads, context: ran.context ?? [] }
}

test('win32: the hook profile is read under USERPROFILE (minimal there silences the alert)', async ($, on) => {
  const { reads, context } = await warnedSubagent($, on, WIN, 'C:/Users/x/.claude/.hook-profile')
  expect(reads).toEqual(['C:/Users/x/.claude/.hook-profile'])
  expect(context).toEqual([])
})

test('win32: a POSIX-style HOME (Git Bash) does not beat USERPROFILE; HOMEDRIVE+HOMEPATH is the last resort', async ($, on) => {
  const a = await warnedSubagent($, on, { ...WIN, HOME: '/c/home/t' }, 'C:/Users/x/.claude/.hook-profile')
  expect(a.reads).toEqual(['C:/Users/x/.claude/.hook-profile'])
})

test('win32: HOMEDRIVE+HOMEPATH when neither HOME nor USERPROFILE is set', async ($, on) => {
  const a = await warnedSubagent($, on, { OS: 'Windows_NT', HOMEDRIVE: 'D:', HOMEPATH: '\\Users\\x' }, 'D:/Users/x/.claude/.hook-profile')
  expect(a.reads).toEqual(['D:/Users/x/.claude/.hook-profile'])
})

test('mac: the hook profile is read under HOME, alert unchanged', async ($, on) => {
  const { reads, context } = await warnedSubagent($, on, { HOME: '/home/t' }, '/nowhere', seenPosix)
  expect(reads).toEqual(['/home/t/.claude/.hook-profile'])
  expect(context).toEqual(['CONTEXT_PCT_ALERT: 75% — WARNING THRESHOLD (75%). Complete current task. No new L3s.'])
})
