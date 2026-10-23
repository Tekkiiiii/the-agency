import type { AgentSpawnInput, EngineInterface, Register } from 'claude-code'

import type { Spawn } from '../types'
import { isWindows, joinPath, pickHome, pythonRunner } from './platform'
import type { PyInit } from './platform'

// Replaces hooks/spawn-logger.sh, spawn-completion.sh and artifact-verify.sh.
// This module is the event source; bin/ledger.py does the JSONL writes so the
// records stay byte-compatible with what the shell hooks wrote (see its header).

const SPAWNS = { plugin: 'spawn-ledger', key: 'spawns' } as const
const REPORT = { plugin: 'spawn-ledger', key: 'report' } as const

// The contract (runbooks/respawn-contract.md): a PD emits `RESPAWN_REQUEST {slug}` as its own line.
// Strict on purpose: the line holds nothing else (no bullet, bold, quote or backticks), and a
// fenced code block is skipped, so a report that merely quotes the phrase never fires.
const SLUG = '[a-z0-9][a-z0-9_-]*'
const REQUEST_LINE = new RegExp(`^[ \\t]*RESPAWN_REQUEST[ \\t]+(${SLUG})[ \\t]*$`, 'im')
const FENCED = /^[ \t]*(```|~~~)[\s\S]*?^[ \t]*\1[^\n]*$/gm

export const respawnSlug = (text: string): string | null =>
  REQUEST_LINE.exec(text.replace(FENCED, ''))?.[1]?.toLowerCase() ?? null

// Known project slugs: first cell of each row of the Active Projects table in medium-term.md
// ("acme (alias -> acme-app)" counts as `acme`). Empty set = nothing parsed.
export const parseKnownSlugs = (md: string): Set<string> => {
  const section = /^## Active Projects\s*$([\s\S]*?)(?=^## |(?![\s\S]))/m.exec(md)?.[1] ?? ''
  const slugs = new Set<string>()
  for (const line of section.split('\n')) {
    const cell = /^\s*\|\s*([^|]*?)\s*\|/.exec(line)?.[1] ?? ''
    const slug = new RegExp(`^${SLUG}`, 'i').exec(cell)?.[0]
    if (slug && !/^project$/i.test(cell)) slugs.add(slug.toLowerCase())
  }
  return slugs
}

// `win`: the queue file is removed from PowerShell there (no `rm`).
export const respawnNotice = (slug: string, from: string, root: string, win = false): string => {
  const queue = `${root}/state/respawn-queue/${slug}`
  return (
    `RESPAWN_REQUEST ${slug} from background agent "${from}". Parent contract: run /pd-resume ${slug} now, ` +
    (win
      ? `then delete "${queue.replace(/\//g, '\\')}" (PowerShell Remove-Item; runbooks/respawn-contract.md).`
      : `then rm ${queue} (runbooks/respawn-contract.md).`)
  )
}

// The agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else <home>/.claude (hooks/lib/resolve-root.sh); <home> per OS
// (platform.ts pickHome: USERPROFILE first on Windows, HOME elsewhere).
// bin/ledger.py resolves the same way, so both halves of the mod agree on where the logs live.
// The names are spelled here: the loader wants literal `$.env.get('NAME')`, and follows `$` only inside this file
// (platform.ts holds the pure parts).
async function agencyRoot($: EngineInterface): Promise<string> {
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

// python3 on macOS/Linux; on Windows whichever python is installed (see platform.ts). One runner per register(), so the
// resolved interpreter is remembered for the load and no state is shared between loads.
type Python = ReturnType<typeof pythonRunner>
const runPy = ($: EngineInterface, py: Python, args: string[], init: PyInit) =>
  py.run(args, init, (argv, i) => $.process.run(argv, i), () => $.env.get('CLAUDE_PYTHON'))

type Registry = { slugs?: Set<string> }

// null = registry unreadable: the anchored match alone decides, and the log says so.
async function knownSlugs($: EngineInterface, registry: Registry): Promise<Set<string> | null> {
  if (registry.slugs) return registry.slugs
  const md = await $.fs.read(joinPath(await agencyRoot($), 'memory', 'medium-term.md')).then(String, () => '')
  const slugs = parseKnownSlugs(md)
  if (slugs.size === 0) {
    $.ui.log('spawn-ledger: medium-term.md Active Projects unreadable; RESPAWN_REQUEST slug not checked against known projects')
    return null
  }
  return (registry.slugs = slugs)
}

// <root>/.hook-profile = minimal turns the spawn hooks off, as it did the shell ones.
async function isMinimal($: EngineInterface): Promise<boolean> {
  const profile = await $.fs.read(joinPath(await agencyRoot($), '.hook-profile')).catch(() => '')
  return String(profile).trim() === 'minimal'
}

// Higgsfield fence: bare general-purpose carries disallowedTools mcp__claude_ai_Higgsfield (<agency root>/agents/general-purpose.md).
// Higgsfield work runs as the unfenced file agent general-purpose-media instead. Kill switch: remove agents/general-purpose.md.
const HF_SKILLS = /^[ \t]*Skills?:.*\/higgsfield-(?:functions|stickman-video)\b/im
const HF_MARKER = /^[ \t]*MEDIA-WORK:[ \t]*higgsfield[ \t]*$/im
export const isHiggsfieldWork = (prompt: string): boolean =>
  HF_SKILLS.test(prompt) || prompt.includes('mcp__claude_ai_Higgsfield') || HF_MARKER.test(prompt)

const MEDIA_TYPE = 'general-purpose-media'
// The unfenced variant exists as a file or the rewrite is skipped (fail open: plain, fenced general-purpose).
async function mediaVariantPresent($: EngineInterface): Promise<boolean> {
  try {
    await $.fs.read(joinPath(await agencyRoot($), 'agents', `${MEDIA_TYPE}.md`))
    return true
  } catch {
    return false
  }
}

type Pending = Map<string, { effort: string; category?: string; toolUseId: string }>
const effortKey = (type: string, description: string | undefined) => `${type}\u0000${description ?? ''}`

// The effort the policy wants for a subagent, or undefined (none decided, minimal profile, not ours). Throws on a lookup error.
async function wantedEffort($: EngineInterface, agentId: string, pending: Pending) {
  if (await isMinimal($)) return undefined
  const spawn = (await $.state.get({ ...SPAWNS, id: agentId })).value
  if (spawn) return spawn.effort ? { effort: spawn.effort, category: spawn.effortCategory, toolUseId: spawn.toolUseId } : undefined
  // Not stored yet (the first step beat agent.spawn's $.state.set): the listed row names the pending key.
  const listed = (await $.agent.list()).find(a => a.id === agentId)
  return listed ? pending.get(effortKey(listed.type, listed.description)) : undefined
}

async function ledger($: EngineInterface, py: Python, cmd: string, payload: unknown): Promise<string> {
  const ran = await runPy($, py, [`${$.plugin.root}/bin/ledger.py`, cmd], {
    stdin: JSON.stringify(payload),
    timeoutMs: 20_000,
  })
  return ran.stdout.trim()
}

// Model pin + Exec cap policy: hooks/lib/model-pin.py decides, this only relays. The Agent tool's
// `model` param overrides an agent file's frontmatter model, so a spawner passing "opus" leaks Opus onto
// sonnet-pinned agents; and no PD may have more than 5 Execs running at once across its whole tree (all its coords + direct Execs).
// FAIL OPEN: any error (no python, timeout, non-JSON, unknown action) = the spawn goes through unchanged.
// Kill switch: MODEL_PIN_OFF=1 | state/model-pin.off | .hook-profile=minimal (cap alone: SPAWN_CAP_OFF=1 | state/spawn-cap.off).
// Effort policy (owner ruling 2026-10-15, enforced): the same script also DECIDES an `effort` (+ `effort_category`) for every
// non-deny result. agent.spawn input has no effort field, so it cannot be rewritten there; this module remembers it per
// subagent and the turn.step hook below applies it to every request of that subagent, the way the pin sets `model`.
// Its own kill switches live in the python CLI (EFFORT_POLICY_OFF=1 | state/effort-policy.off | effort.enabled=false): no key, no relay.
type Pin = {
  action: 'pass' | 'rewrite' | 'deny'
  model: string | null
  deny?: string
  reason?: string
  effort?: string
  effort_category?: string
}

const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']

export const parsePin = (stdout: string): Pin | null => {
  const line = stdout.trim().split('\n').filter(Boolean).pop() ?? ''
  const pin = JSON.parse(line) as (Partial<Pin> & { effort?: unknown; effort_category?: unknown }) | null
  if (!pin || typeof pin !== 'object') return null
  if (pin.action === 'deny') return typeof pin.deny === 'string' && pin.deny ? { action: 'deny', model: null, deny: pin.deny } : null
  // A malformed effort is dropped, never an error: the model decision stands.
  const effort = typeof pin.effort === 'string' && EFFORTS.includes(pin.effort) ? pin.effort : undefined
  const category = typeof pin.effort_category === 'string' && pin.effort_category ? pin.effort_category : undefined
  const policy = effort ? { effort, ...(category ? { effort_category: category } : {}) } : {}
  if (pin.action === 'rewrite' && (pin.model === null || (typeof pin.model === 'string' && pin.model))) {
    return { action: 'rewrite', model: pin.model, reason: pin.reason, ...policy }
  }
  return pin.action === 'pass' ? { action: 'pass', model: null, ...policy } : null
}

async function modelPin($: EngineInterface, py: Python, e: AgentSpawnInput, parent: Spawn | undefined): Promise<Pin | null> {
  try {
    const ran = await runPy($, py, [joinPath(await agencyRoot($), 'hooks', 'lib', 'model-pin.py')], {
      stdin: JSON.stringify({
        subagent_type: e.subagentType,
        model: e.model ?? null,
        fork: e.fork === true,
        is_teammate: e.isTeammate === true,
        workflow: e.workflow !== undefined,
        parent_spawn_id: parent?.spawnId ?? '',
        parent_agent: parent?.type ?? 'root',
        tool_use_id: e.tool_use_id,
        description: e.description,
        prompt: e.prompt,
      }),
      timeoutMs: 5_000,
    })
    return parsePin(ran.stdout)
  } catch (err) {
    $.ui.log(`model-pin skipped (fail open): ${err instanceof Error ? err.message : String(err)}`)
    return null
  }
}

// Jev routing gate: scripts/jev-spawn-gate.py decides, this only relays, like modelPin. SHIPS DISABLED, with the skill
// router: the mod calls the gate ONLY when AGENCY_SKILL_ROUTER is exactly "1" (routerOn below); with the router off no
// python process starts and the spawn is untouched. The script itself also passes unchanged when the router is off.
// pass = untouched; rewrite = the full replacement prompt (Jev line / Skills injected); deny = the spawner re-issues
// the same call with its Jev verdict line. `note` rides the Agent result as context.
// FAIL OPEN: any error (no python, timeout, non-JSON, unknown action, rewrite without a prompt, deny without a
// message) = the spawn goes through unchanged; Jev down never blocks. Kill switches live in the python CLI, not here:
// JEV_GATE_OFF=1 | <root>/state/jev-gate.off | .hook-profile=minimal.
type JevGate =
  | { action: 'pass'; note?: string; route_id?: string }
  | { action: 'rewrite'; prompt: string; note?: string; route_id?: string }
  | { action: 'deny'; deny: string; route_id?: string }

export const parseJevGate = (stdout: string): JevGate | null => {
  const line = stdout.trim().split('\n').filter(Boolean).pop() ?? ''
  let gate: Record<string, unknown> | null
  try {
    gate = JSON.parse(line) as Record<string, unknown> | null
  } catch {
    return null
  }
  if (!gate || typeof gate !== 'object') return null
  const text = (v: unknown) => (typeof v === 'string' && v ? v : undefined)
  const note = text(gate.note)
  const route_id = text(gate.route_id)
  if (gate.action === 'deny') {
    const deny = text(gate.deny)
    return deny ? { action: 'deny', deny, route_id } : null
  }
  if (gate.action === 'rewrite') {
    const prompt = text(gate.prompt)
    return prompt ? { action: 'rewrite', prompt, note, route_id } : null
  }
  return gate.action === 'pass' ? { action: 'pass', note, route_id } : null
}

// The skill router opt-in, spelled exactly like skill-route.py and ledger.py read it: only "1" turns it on.
const routerOn = async ($: EngineInterface): Promise<boolean> => (await $.env.get('AGENCY_SKILL_ROUTER')) === '1'

async function jevGate($: EngineInterface, py: Python, e: AgentSpawnInput, parent: Spawn | undefined): Promise<JevGate | null> {
  try {
    if (!(await routerOn($))) return null // router off: no python process, nothing changes
    const ran = await runPy($, py, [joinPath(await agencyRoot($), 'scripts', 'jev-spawn-gate.py')], {
      stdin: JSON.stringify({
        tool_use_id: e.tool_use_id,
        subagent_type: e.subagentType,
        description: e.description,
        prompt: e.prompt,
        parent_agent: parent?.type ?? 'root',
        parent_spawn_id: parent?.spawnId ?? '',
        fork: e.fork === true,
        is_teammate: e.isTeammate === true,
        workflow: e.workflow !== undefined,
      }),
      timeoutMs: 15_000,
    })
    return parseJevGate(ran.stdout)
  } catch (err) {
    $.ui.log(`jev-gate skipped (fail open): ${err instanceof Error ? err.message : String(err)}`)
    return null
  }
}

export const register: Register = on => {
  // Agent calls still running, and warnings waiting to ride their result.
  // ponytail: module variables, so a hot reload mid-call drops one warning; $.state if that ever bites.
  const open = new Set<string>()
  const pending = new Map<string, string>()
  // Project registry, read once per session; a failed read is not cached, so the next request retries.
  const registry: Registry = {}
  const py = pythonRunner()
  // Effort the pin decided for a spawn that has no agentId yet, keyed `${subagentType}\u0000${description}`: the subagent's
  // first turn.step may fire before $.state.set, and $.agent.list() then names the same type + description.
  // ponytail: module variables like `open`/`pending`; a hot reload drops them and the stored record serves later steps.
  const pendingEffort: Pending = new Map()
  // Agents whose first effort-applied step is already in the ledger.
  const effortLogged = new Set<string>()

  on('agent.spawn', async ($, e, next) => {
    if (await isMinimal($)) return next(e)
    const parent = e.parentAgentId ? (await $.state.get({ ...SPAWNS, id: e.parentAgentId })).value : undefined
    // Jev gate before the model pin: a deny must not consume a cap slot, and a rewritten prompt is what the pin and the ledger see.
    // Router off (the default) = jevGate returns null without starting anything.
    const gate = await jevGate($, py, e, parent)
    if (gate?.action === 'deny') return { deny: gate.deny } // no ledger row for a denied spawn
    if (gate?.action === 'rewrite') e = { ...e, prompt: gate.prompt }
    // A workflow agent has no Agent tool call to carry the note; only stash it while one is open.
    if (gate?.note && open.has(e.tool_use_id)) {
      pending.set(e.tool_use_id, [pending.get(e.tool_use_id), gate.note].filter(Boolean).join('\n'))
    }
    const pin = await modelPin($, py, e, parent)
    if (pin?.action === 'deny' && pin.deny) return { deny: pin.deny } // no ledger row for a denied spawn
    if (pin?.action === 'rewrite') {
      const { model: _old, ...rest } = e
      e = pin.model ? { ...rest, model: pin.model } : rest // null = strip the param, frontmatter decides
    }
    const spawnId = await ledger($, py, 'start', {
      tool_use_id: e.tool_use_id,
      subagent_type: e.subagentType,
      description: e.description,
      prompt: e.prompt,
      model: e.model ?? '',
      parent_spawn_id: parent?.spawnId ?? '',
      parent_agent: parent?.type ?? 'root',
    }).catch(() => '')
    // Higgsfield fence: gate, pin, cap and ledger 'start' above all saw the ORIGINAL type; only the spawn itself is swapped.
    const originalType = e.subagentType
    if ((originalType === '' || originalType === 'general-purpose') && isHiggsfieldWork(e.prompt ?? '') && (await mediaVariantPresent($))) {
      e = { ...e, subagentType: MEDIA_TYPE }
    }
    // Remember the effort BEFORE next(e): the agent's first turn.step can run before this hook gets the agentId back.
    // Keyed on the ACTUAL type: turn.step's $.agent.list() fallback shows the type the engine really spawned.
    const key = effortKey(e.subagentType, e.description)
    if (pin?.effort) pendingEffort.set(key, { effort: pin.effort, category: pin.effort_category, toolUseId: e.tool_use_id })
    try {
      const result = await next(e)
      if (result.agentId) {
        const spawn: Spawn = {
          spawnId,
          toolUseId: e.tool_use_id,
          type: originalType,
          ...(e.subagentType !== originalType ? { actualType: e.subagentType } : {}),
          description: e.description || originalType,
          parentAgentId: e.parentAgentId ?? null,
          ...(pin?.effort ? { effort: pin.effort, effortCategory: pin.effort_category } : {}),
        }
        await $.state.set({ ...SPAWNS, id: result.agentId }, spawn)
        await ledger($, py, 'launched', {
          tool_use_id: e.tool_use_id,
          agent_id: result.agentId,
          resolved_model: result.model,
          ...(e.subagentType !== originalType ? { actual_type: e.subagentType } : {}),
        }).catch(() => '')
      }
      return result
    } finally {
      pendingEffort.delete(key)
    }
  })

  // Applies the effort model-pin.py decided to every request of the subagent that spawn made. TurnStepInput.effort is
  // rewritable going down (`next({ ...e, effort })`), AgentSpawnInput's is not. The main loop (no agentId) pays nothing.
  // FAIL OPEN: any lookup error = the step goes through unchanged, one log line.
  on('turn.step', async function* ($, e, next) {
    if (!e.agentId) return yield* next(e)
    // The lookups run in a plain async helper, so a throw from `next` (the model request itself) is never mistaken for a lookup error.
    let desired: Awaited<ReturnType<typeof wantedEffort>>
    try {
      desired = await wantedEffort($, e.agentId, pendingEffort)
    } catch (err) {
      $.ui.log(`effort relay skipped (fail open): ${err instanceof Error ? err.message : String(err)}`)
      return yield* next(e)
    }
    if (!desired) return yield* next(e)
    if (!effortLogged.has(e.agentId)) {
      effortLogged.add(e.agentId)
      await ledger($, py, 'effort_applied', {
        tool_use_id: desired.toolUseId,
        agent_id: e.agentId,
        seen: e.effort ?? null,
        applied: desired.effort,
        category: desired.category ?? '',
      }).catch(() => '')
    }
    return yield* next(e.effort === desired.effort ? e : { ...e, effort: desired.effort as typeof e.effort })
  })

  // spawn_end with real tokens and cost: SubagentStop carries the transcript path.
  on('classic.SubagentStop', async ($, e, next) => {
    const result = await next(e)
    if (await isMinimal($)) return result
    // `end` prints a one-line warning for a silent no-op spawn (<5s, 0 tools). Foreground: it rides the
    // Agent result; background: it goes to the parent like the other warnings.
    const warning = await ledger($, py, 'end', e).catch(() => '')
    const id = (e as { agent_id?: string }).agent_id
    const spawn = warning && id ? (await $.state.get({ ...SPAWNS, id })).value : undefined
    if (!warning || !spawn) return result
    if (open.has(spawn.toolUseId)) {
      pending.set(spawn.toolUseId, [pending.get(spawn.toolUseId), warning].filter(Boolean).join('\n'))
    } else {
      $.ui.log(warning)
      const text = `[spawn-ledger] Background agent "${spawn.description}" (${spawn.type}) finished: ${warning}`
      const message = { type: 'user' as const, content: [{ type: 'text' as const, text }] }
      const toParent = spawn.parentAgentId
        ? await $.session.append({ message, agentId: spawn.parentAgentId }).then(() => true, () => false)
        : false
      if (!toParent) await $.session.append({ message }).catch(() => undefined)
    }
    return result
  })

  on('tool.call', async ($, e, next) => {
    const tool = String(e.tool)
    if (tool === 'SubagentHandback' && e.agentId) {
      const message = (e as { message?: unknown }).message
      if (typeof message === 'string') await $.state.set({ ...REPORT, id: e.agentId }, message)
      return next(e)
    }
    if (tool !== 'Agent' || !e.tool_use_id) return next(e)
    open.add(e.tool_use_id)
    try {
      const ran = await next(e)
      const warning = pending.get(e.tool_use_id)
      pending.delete(e.tool_use_id)
      if (!warning || ran.deny !== undefined) return ran
      return { ...ran, context: [...(ran.context ?? []), warning] }
    } finally {
      open.delete(e.tool_use_id)
    }
  })

  // Every spawned agent ends here, background ones included: the gap PostToolUse left.
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (!e.agentId || (await isMinimal($))) return result
    const spawn = (await $.state.get({ ...SPAWNS, id: e.agentId })).value
    if (!spawn) return result // an engine fork or a workflow agent: not a spawn we logged
    const report = (await $.state.get({ ...REPORT, id: e.agentId })).value || e.answer
    const warning = await ledger($, py, 'verify', { text: report }).catch(() => '')

    // Foreground: the parent's Agent call is still open, so the warning rides its result.
    if (open.has(spawn.toolUseId)) {
      if (warning) pending.set(spawn.toolUseId, warning)
      return result
    }

    // Background: nobody is waiting on a tool result. Tell the parent loop and the person.
    let slug = respawnSlug(report)
    if (slug) {
      const projects = await knownSlugs($, registry)
      if (projects && !projects.has(slug)) {
        $.ui.log(`ignored RESPAWN_REQUEST ${slug}: not a known project`)
        slug = null
      }
    }
    const notes = [warning, slug ? respawnNotice(slug, spawn.description, await agencyRoot($), isWindows(await $.env.get('OS'))) : ''].filter(Boolean)
    if (notes.length === 0) return result
    if (slug) $.ui.toast(`RESPAWN_REQUEST ${slug}: run /pd-resume ${slug}`, { timeoutMs: 10_000 })
    if (warning) $.ui.toast(`Artifact missing in "${spawn.description}" report`, { timeoutMs: 10_000 })
    for (const note of notes) $.ui.log(note)
    const text = `[spawn-ledger] Background agent "${spawn.description}" (${spawn.type}) finished:\n${notes.join('\n')}`
    const message = { type: 'user' as const, content: [{ type: 'text' as const, text }] }
    const toParent = spawn.parentAgentId
      ? await $.session.append({ message, agentId: spawn.parentAgentId }).then(() => true, () => false)
      : false
    if (!toParent) await $.session.append({ message }).catch(() => undefined)
    return result
  })
}
