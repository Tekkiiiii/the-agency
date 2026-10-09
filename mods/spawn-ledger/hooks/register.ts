import type { AgentSpawnInput, EngineInterface, Register } from 'claude-code'

import type { Spawn } from '../types'

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

export const respawnNotice = (slug: string, from: string, root: string): string =>
  `RESPAWN_REQUEST ${slug} from background agent "${from}". Parent contract: run /pd-resume ${slug} now, ` +
  `then rm ${root}/state/respawn-queue/${slug} (runbooks/respawn-contract.md).`

// The agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else <HOME or USERPROFILE>/.claude (hooks/lib/resolve-root.sh).
// bin/ledger.py resolves the same way, so both halves of the mod agree on where the logs live.
async function agencyRoot($: EngineInterface): Promise<string> {
  const [agency, config, home, winHome] = await Promise.all([
    $.env.get('AGENCY_HOME'),
    $.env.get('CLAUDE_CONFIG_DIR'),
    $.env.get('HOME'),
    $.env.get('USERPROFILE'),
  ])
  return agency || config || `${home || winHome || ''}/.claude`
}

type Registry = { slugs?: Set<string> }

// null = registry unreadable: the anchored match alone decides, and the log says so.
async function knownSlugs($: EngineInterface, registry: Registry): Promise<Set<string> | null> {
  if (registry.slugs) return registry.slugs
  const md = await $.fs.read(`${await agencyRoot($)}/memory/medium-term.md`).then(String, () => '')
  const slugs = parseKnownSlugs(md)
  if (slugs.size === 0) {
    $.ui.log('spawn-ledger: medium-term.md Active Projects unreadable; RESPAWN_REQUEST slug not checked against known projects')
    return null
  }
  return (registry.slugs = slugs)
}

// <root>/.hook-profile = minimal turns the spawn hooks off, as it did the shell ones.
async function isMinimal($: EngineInterface): Promise<boolean> {
  const profile = await $.fs.read(`${await agencyRoot($)}/.hook-profile`).catch(() => '')
  return String(profile).trim() === 'minimal'
}

async function ledger($: EngineInterface, cmd: string, payload: unknown): Promise<string> {
  const ran = await $.process.run(['python3', `${$.plugin.root}/bin/ledger.py`, cmd], {
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
type Pin = { action: 'pass' | 'rewrite' | 'deny'; model: string | null; deny?: string; reason?: string }

export const parsePin = (stdout: string): Pin | null => {
  const line = stdout.trim().split('\n').filter(Boolean).pop() ?? ''
  const pin = JSON.parse(line) as Partial<Pin> | null
  if (!pin || typeof pin !== 'object') return null
  if (pin.action === 'deny') return typeof pin.deny === 'string' && pin.deny ? { action: 'deny', model: null, deny: pin.deny } : null
  if (pin.action === 'rewrite' && (pin.model === null || (typeof pin.model === 'string' && pin.model))) {
    return { action: 'rewrite', model: pin.model, reason: pin.reason }
  }
  return pin.action === 'pass' ? { action: 'pass', model: null } : null
}

async function modelPin($: EngineInterface, e: AgentSpawnInput, parent: Spawn | undefined): Promise<Pin | null> {
  try {
    const root = await agencyRoot($)
    const ran = await $.process.run(['python3', `${root}/hooks/lib/model-pin.py`], {
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

export const register: Register = on => {
  // Agent calls still running, and warnings waiting to ride their result.
  // ponytail: module variables, so a hot reload mid-call drops one warning; $.state if that ever bites.
  const open = new Set<string>()
  const pending = new Map<string, string>()
  // Project registry, read once per session; a failed read is not cached, so the next request retries.
  const registry: Registry = {}

  on('agent.spawn', async ($, e, next) => {
    if (await isMinimal($)) return next(e)
    const parent = e.parentAgentId ? (await $.state.get({ ...SPAWNS, id: e.parentAgentId })).value : undefined
    const pin = await modelPin($, e, parent)
    if (pin?.action === 'deny' && pin.deny) return { deny: pin.deny } // no ledger row for a denied spawn
    if (pin?.action === 'rewrite') {
      const { model: _old, ...rest } = e
      e = pin.model ? { ...rest, model: pin.model } : rest // null = strip the param, frontmatter decides
    }
    const spawnId = await ledger($, 'start', {
      tool_use_id: e.tool_use_id,
      subagent_type: e.subagentType,
      description: e.description,
      prompt: e.prompt,
      model: e.model ?? '',
      parent_spawn_id: parent?.spawnId ?? '',
      parent_agent: parent?.type ?? 'root',
    }).catch(() => '')
    const result = await next(e)
    if (result.agentId) {
      const spawn: Spawn = {
        spawnId,
        toolUseId: e.tool_use_id,
        type: e.subagentType,
        description: e.description || e.subagentType,
        parentAgentId: e.parentAgentId ?? null,
      }
      await $.state.set({ ...SPAWNS, id: result.agentId }, spawn)
      await ledger($, 'launched', {
        tool_use_id: e.tool_use_id,
        agent_id: result.agentId,
        resolved_model: result.model,
      }).catch(() => '')
    }
    return result
  })

  // spawn_end with real tokens and cost: SubagentStop carries the transcript path.
  on('classic.SubagentStop', async ($, e, next) => {
    const result = await next(e)
    if (await isMinimal($)) return result
    // `end` prints a one-line warning for a silent no-op spawn (<5s, 0 tools). Foreground: it rides the
    // Agent result; background: it goes to the parent like the other warnings.
    const warning = await ledger($, 'end', e).catch(() => '')
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
    const warning = await ledger($, 'verify', { text: report }).catch(() => '')

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
    const notes = [warning, slug ? respawnNotice(slug, spawn.description, await agencyRoot($)) : ''].filter(Boolean)
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
