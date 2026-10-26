// COPY of mods/_shared/platform.ts, edit there and re-copy; mods cannot import outside their plugin folder

// Where the mods differ between macOS/Linux and Windows: the home directory, path joining and which python
// launches the helper scripts.
//
// Pure functions only, none takes `$`: the module loader follows `$` into functions of the SAME file, never across
// an import, and wants every `$.env.get('NAME')` / `$.process.run(...)` spelled in the hooks module with a literal
// name. So each register file reads its own env vars and hands the values (or a `$.process.run` closure) in here.
// The mod API has no home/platform/path noun; Windows itself sets OS=Windows_NT for every process.

/** True on Windows (the value of `$.env.get('OS')`). */
export const isWindows = (os: string | undefined): boolean => os === 'Windows_NT'

const TRAILING_SEPS = /[\\/]+$/

/** `$.env.get` of OS, HOME, USERPROFILE, HOMEDRIVE, HOMEPATH, in that order. */
export type HomeEnv = readonly [os?: string, home?: string, profile?: string, drive?: string, path?: string]

/**
 * The user's home directory without a trailing separator; '' when nothing is set (callers tolerate it).
 * Windows prefers USERPROFILE (HOME exists only under Git Bash/MSYS and may be a POSIX-style path), then HOME,
 * then HOMEDRIVE+HOMEPATH; elsewhere HOME, then USERPROFILE.
 */
export function pickHome([os, home, profile, drive, path]: HomeEnv): string {
  const win = isWindows(os)
  const found = (win ? profile || home : home || profile) || (win && drive && path ? `${drive}${path}` : '')
  return found.replace(TRAILING_SEPS, '')
}

/**
 * Join with '/': Windows Node and Python accept mixed separators. Separators between parts are collapsed;
 * the first part keeps its leading drive/UNC prefix. An empty first part gives a '/'-rooted path, as `${home}/x` did.
 */
export function joinPath(...parts: string[]): string {
  const [head = '', ...rest] = parts
  return [head.replace(TRAILING_SEPS, ''), ...rest.map(p => p.replace(/^[\\/]+|[\\/]+$/g, '')).filter(Boolean)].join('/')
}

export type PyRun = { exitCode: number; stdout: string; stderr: string }
export type PyInit = { stdin?: string; timeoutMs?: number; cwd?: string; env?: Record<string, string> }
/** The caller's `(argv, init) => $.process.run(argv, init)`. */
export type PyExec = (argv: string[], init: PyInit) => Promise<PyRun>

// Windows Python defaults to the ANSI code page for pipes; the scripts read and write UTF-8.
const PY_ENV = { PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' }
const PROBE = ['-c', 'import sys;print(sys.version_info[0])']

/**
 * Runs a python script with whichever python this machine has. macOS happy path: exactly one `python3 ...`
 * process. When that rejects or exits non-zero (no python3, or the Windows Store `python3` stub), probe
 * CLAUDE_PYTHON, python3, `py -3`, python for a real Python 3, cache the winner and retry once. Nothing found: the
 * original result (or rejection) comes back, so callers fail open as before.
 * A factory, one runner per register() call: the cache lives and dies with the load, no module-level state.
 */
export function pythonRunner(): {
  run: (args: string[], init: PyInit, exec: PyExec, claudePython: () => Promise<string | undefined>) => Promise<PyRun>
} {
  let cached: string[] | undefined
  // ponytail: CLAUDE_PYTHON is ONE executable path (no arguments); a launcher with flags would need splitting.
  // ponytail: a cached interpreter is never re-probed; a python removed mid-session fails open until the mod reloads.
  const isPython3 = async (exec: PyExec, cmd: string[]): Promise<boolean> => {
    try {
      const ran = await exec([...cmd, ...PROBE], { env: PY_ENV, timeoutMs: 5_000 })
      return ran.exitCode === 0 && ran.stdout.trim() === '3'
    } catch {
      return false
    }
  }
  return {
    async run(args, init, exec, claudePython) {
      const override = cached ? undefined : await claudePython()
      const first = cached ?? (override ? [override] : ['python3'])
      let original: PyRun | undefined
      let failure: unknown
      try {
        original = await exec([...first, ...args], { ...init, env: PY_ENV })
        if (original.exitCode === 0) {
          cached = first
          return original
        }
      } catch (err) {
        failure = err
      }
      const giveUp = (): PyRun => {
        if (original) return original
        throw failure
      }
      if (cached) return giveUp() // a known-good python failed on its own account: nothing to re-probe
      for (const cmd of [...(override ? [[override]] : []), ['python3'], ['py', '-3'], ['python']]) {
        if (!(await isPython3(exec, cmd))) continue
        cached = cmd
        return cmd.join('\0') === first.join('\0') ? giveUp() : exec([...cmd, ...args], { ...init, env: PY_ENV })
      }
      return giveUp()
    },
  }
}
