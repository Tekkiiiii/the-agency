import { update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Fill } from '../types'
import { joinPath, pickHome } from './platform'

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

// Subagents: ABSOLUTE tokens, whatever their window (cap decision 2026-10-19): 200k warn, 250k finish, 300k stop.
export const SUB_CAP = 300_000
export const subLevelOf = (tokens: number): number => (tokens >= 300_000 ? 300 : tokens >= 250_000 ? 250 : tokens >= 200_000 ? 200 : 0)

export const subAlertText = (tokens: number): string => {
  const head = `CONTEXT_PCT_ALERT: ${Math.floor(tokens / 1000)}k tokens (subagent cap 300k) — `
  return tokens >= 300_000
    ? `${head}STOP (300k). MANDATORY: Coord run /save-state and /coord-respawn-self; Exec write your final report now and stop.`
    : tokens >= 250_000
      ? `${head}FINISH CURRENT TASK (250k). No new work; wrap up and report.`
      : `${head}WARNING (200k). Complete current task, keep it small.`
}

const isSub = (id: string | undefined): boolean => !!id && id !== 'main'
const k = (tokens: number): number => Math.floor(tokens / 1000)
const subPct = (tokens: number): number => Math.floor((tokens * 100) / SUB_CAP)
// A record from an older build ({pct, level, told}) has no tokens: nothing to report, never NaN.
const hasTokens = (f: { tokens?: unknown } | undefined): f is { tokens: number } => typeof f?.tokens === 'number' && Number.isFinite(f.tokens)


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

// <root>/.hook-profile = minimal turns the alert off. A missing file means standard.
async function isMinimal($: EngineInterface): Promise<boolean> {
  const profile = await $.fs.read(joinPath(await agencyRoot($), '.hook-profile')).catch(() => '')
  return String(profile).trim() === 'minimal'
}

export const register: Register = on => {
  // One model request of any loop: its input side is that loop's context fill.
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    const u = result.usage
    if (!u) return result
    const tokens = u.input_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens
    const sub = isSub(e.agentId)
    const window = e.agentId && !sub ? windowFor(e.model, tokens) : sub ? SUB_CAP : (await $.session.usage()).context.window
    const pct = Math.floor((tokens * 100) / window)
    const level = sub ? subLevelOf(tokens) : levelOf(pct)
    // A drop (compaction) lowers `told`, so a later crossing is told again.
    await update($, { ...FILL, id: e.agentId ?? 'main' }, (prev): Fill => ({
      pct,
      tokens,
      level,
      told: Math.min(prev?.told ?? 0, level),
      parentTold: Math.min(prev?.parentTold ?? 0, level),
    }))
    return result
  })

  // The loop's next tool result carries the alert once per crossing; no file to read.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny !== undefined || (await isMinimal($))) return ran
    const lines: string[] = []
    const ref = { ...FILL, id: e.agentId ?? 'main' }
    const fill = (await $.state.get(ref)).value
    if (fill && (!isSub(e.agentId) || hasTokens(fill))) {
      if (isSub(e.agentId) && fill.level >= 300) {
        lines.push(subAlertText(fill.tokens)) // every tool result until the agent ends; never a deny
      } else if (fill.level > fill.told) {
        await $.state.set(ref, { ...fill, told: fill.level })
        lines.push(isSub(e.agentId) ? subAlertText(fill.tokens) : alertText(fill.pct))
      }
    }
    lines.push(...(await childLines($, e, ran)))
    return lines.length ? { ...ran, context: [...(ran.context ?? []), ...lines] } : ran
  })
}

type Agents = Awaited<ReturnType<EngineInterface['agent']['list']>>

// What a controller sees of its children: CHILD_CTX after Agent/SendMessage, CHILD_CTX_ALERT at 250k/300k.
async function childLines($: EngineInterface, e: { tool: unknown; agentId?: string; to?: unknown }, ran: { result?: unknown }): Promise<string[]> {
  const agents: Agents = await $.agent.list().catch(() => [])
  // The child's name (what SendMessage addresses), else its spawn description minus a trailing "[task:...]" tag, else its id.
  const label = (id: string) => {
    const a = agents.find(x => x.id === id)
    return a?.name || a?.description?.replace(/\s*\[[^\]]*\]\s*$/, '').trim() || id
  }
  const lines: string[] = []
  const tool = String(e.tool)
  let childId: string | undefined
  if (tool === 'Agent') childId = (ran.result as { agentId?: unknown } | undefined)?.agentId as string | undefined
  else if (tool === 'SendMessage') {
    const to = String(e.to ?? '')
    childId = agents.find(a => a.id === to)?.id ?? agents.find(a => a.name === to)?.id
  }
  if (childId) {
    const f = (await $.state.get({ ...FILL, id: childId }).catch(() => ({ value: undefined }))).value
    if (hasTokens(f)) lines.push(`CHILD_CTX: ${label(childId)} ${k(f.tokens)}k/300k (${subPct(f.tokens)}%)`)
  }
  for (const a of agents) {
    if ((a.parentId ?? 'main') !== (e.agentId ?? 'main') || a.status !== 'running') continue
    const ref = { ...FILL, id: a.id }
    const f = (await $.state.get(ref)).value
    if (!hasTokens(f) || f.level < 250 || f.level <= (f.parentTold ?? 0)) continue
    await $.state.set(ref, { ...f, parentTold: f.level })
    const tail = f.level >= 300 ? 'must stop, request report now' : 'finish current task'
    lines.push(`CHILD_CTX_ALERT: ${label(a.id)} ${k(f.tokens)}k/300k — ${tail}`)
  }
  return lines
}
