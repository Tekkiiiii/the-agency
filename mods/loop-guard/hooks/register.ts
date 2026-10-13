import { update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import { joinPath, pickHome } from './platform'

// Counterpart of hooks/loop-detector.sh (see mods/README.md for running both). Its one tracker file mixed every loop's calls,
// so parallel subagents tripped (or masked) each other; history is per agentId now.

const HISTORY = { plugin: 'loop-guard', key: 'history' } as const
const RESERVED = new Set(['tool', 'tool_use_id', 'agentId', 'consent'])

// Same key loop-detector.sh hashed: file_path, else command (200 chars), else the args.
export function signature(e: Record<string, unknown>): string {
  const args = Object.fromEntries(Object.entries(e).filter(([k]) => !RESERVED.has(k)))
  const key =
    (typeof args.file_path === 'string' && args.file_path) ||
    (typeof args.command === 'string' && args.command.slice(0, 200)) ||
    JSON.stringify(args).slice(0, 200)
  return `${String(e.tool)}:${key}`
}

export const warning = (tool: string): string =>
  [
    `[loop-detector] STALL DETECTED: 5 identical ${tool} calls in a row.`,
    '[loop-detector] You are likely in an infinite loop. Stop retrying and:',
    '  1. Restate your objective in one sentence',
    '  2. Verify the actual world state (read the file, check git status)',
    '  3. Try a DIFFERENT approach, not the same command again',
    '  4. If still blocked, /save-state and stop.',
  ].join('\n')

// Python's datetime.now().isoformat(): local time, no zone, as check-session-state.sh prints it.
const localIso = (ms: number): string => new Date(ms - new Date(ms).getTimezoneOffset() * 60_000).toISOString().slice(0, -1)

// The agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else <home>/.claude (hooks/lib/resolve-root.sh); <home> per OS
// (platform.ts pickHome: USERPROFILE first on Windows, HOME elsewhere).
async function agencyRoot($: EngineInterface): Promise<string> {
  // The names are spelled here: the loader wants literal `$.env.get('NAME')`, and follows `$` only inside this file.
  const [agency, config, os, home, profile, drive, path] = await Promise.all([
    $.env.get('AGENCY_HOME'),
    $.env.get('CLAUDE_CONFIG_DIR'),
    $.env.get('OS'),
    $.env.get('HOME'),
    $.env.get('USERPROFILE'),
    $.env.get('HOMEDRIVE'),
    $.env.get('HOMEPATH'),
  ])
  return agency || config || joinPath(pickHome([os, home, profile, drive, path]), '.claude')
}

async function markStall($: EngineInterface, root: string, tool: string): Promise<void> {
  const path = joinPath(root, 'session-state.json')
  let state: Record<string, unknown> = {}
  try {
    state = JSON.parse(String(await $.fs.read(path))) as Record<string, unknown>
  } catch {
    // missing or unreadable: start fresh, as loop-detector.sh did
  }
  state.stall_detected = true
  state.stall_tool = tool
  state.stall_at = localIso(await $.clock.now())
  await $.fs.write(path, JSON.stringify(state, null, 2))
}

export const register: Register = on => {
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny !== undefined) return ran
    const root = await agencyRoot($)
    const profile = await $.fs.read(joinPath(root, '.hook-profile')).catch(() => '')
    if (String(profile).trim() === 'minimal') return ran

    const ref = { ...HISTORY, id: e.agentId ?? 'main' }
    const sig = signature(e as unknown as Record<string, unknown>)
    const last = await update($, ref, prev => [...(prev ?? []), sig].slice(-10))
    const tail = last.slice(-5)
    if (tail.length < 5 || tail.some(s => s !== sig)) return ran

    const tool = String(e.tool)
    await markStall($, root, tool).catch(() => undefined)
    await $.state.set(ref, []) // one fresh chance, as the tracker file was removed
    return { ...ran, context: [...(ran.context ?? []), warning(tool)] }
  })
}
