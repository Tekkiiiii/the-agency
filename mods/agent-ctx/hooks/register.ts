import { update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Fill } from '../types'

// Each loop's own context %, measured from the model requests this session makes. Replaces the one
// global state/context-pct.txt (hooks/lib/context-pct-publish.sh) that every subagent read, and so
// saw the MAIN session's figure. Reads no statusline output and no file except the optional
// .hook-profile: with nothing else installed it just works, and with no usage data it does nothing.
// Thresholds and wording are the Self-Respawn Protocol's (runbooks/respawn-contract.md).

const FILL = { plugin: 'agent-ctx', key: 'fill' } as const

// 70: coordinator warn line; 75: PD warn line (respawn-contract.md); 80: mandatory respawn.
export const levelOf = (pct: number): number => (pct >= 80 ? 80 : pct >= 75 ? 75 : pct >= 70 ? 70 : 0)

// ponytail: no per-agent window API; [1m] in the model id (or a prompt already past
// 200k) means 1M, else 200k. Add a lookup if a model ships with another window.
export const windowFor = (model: string, tokens: number): number =>
  /\[1m\]/i.test(model) || tokens > 200_000 ? 1_000_000 : 200_000

export const alertText = (pct: number): string =>
  pct >= 80
    ? `CONTEXT_PCT_ALERT: ${pct}% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.`
    : `CONTEXT_PCT_ALERT: ${pct}% — WARNING THRESHOLD (${levelOf(pct)}%). Complete current task. No new L3s.`

// The agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else <HOME or USERPROFILE>/.claude (hooks/lib/resolve-root.sh).
async function agencyRoot($: EngineInterface): Promise<string> {
  const [agency, config, home, winHome] = await Promise.all([
    $.env.get('AGENCY_HOME'),
    $.env.get('CLAUDE_CONFIG_DIR'),
    $.env.get('HOME'),
    $.env.get('USERPROFILE'),
  ])
  return agency || config || `${home || winHome || ''}/.claude`
}

// <root>/.hook-profile = minimal turns the alert off. A missing file means standard.
async function isMinimal($: EngineInterface): Promise<boolean> {
  const profile = await $.fs.read(`${await agencyRoot($)}/.hook-profile`).catch(() => '')
  return String(profile).trim() === 'minimal'
}

export const register: Register = on => {
  // One model request of any loop: its input side is that loop's context fill.
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    const u = result.usage
    if (!u) return result
    const tokens = u.input_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens
    const window = e.agentId ? windowFor(e.model, tokens) : (await $.session.usage()).context.window
    const pct = Math.floor((tokens * 100) / window)
    const level = levelOf(pct)
    // A drop (compaction) lowers `told`, so a later crossing is told again.
    await update($, { ...FILL, id: e.agentId ?? 'main' }, (prev): Fill => ({
      pct,
      level,
      told: Math.min(prev?.told ?? 0, level),
    }))
    return result
  })

  // The loop's next tool result carries the alert once per crossing; no file to read.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny !== undefined) return ran
    const ref = { ...FILL, id: e.agentId ?? 'main' }
    const fill = (await $.state.get(ref)).value
    if (!fill || fill.level <= fill.told || (await isMinimal($))) return ran
    await $.state.set(ref, { ...fill, told: fill.level })
    return { ...ran, context: [...(ran.context ?? []), alertText(fill.pct)] }
  })
}
