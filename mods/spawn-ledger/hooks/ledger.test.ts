import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { isHiggsfieldWork, parseJevGate, parseKnownSlugs, parsePin, respawnNotice, respawnSlug } from './register'
import { seenPosix } from './testpaths'

type Run = { cmd: string; payload: Record<string, unknown> }

const MEDIUM_TERM = `# Medium-Term Memory

## Active Projects

| Project | Memory Path | PD | Flag |
|---------|-------------|-----|------|
| ltv | \`/p/ltv/memory/\` | ltv-pd | active |
| system-improvement | \`/p/si/memory/\` | system-improvement-pd | active |
| acme (alias -> acme-app) | \`/p/acme/memory/\` | acme-app-pd | active |

## Delegation
| contract | not | a | project |
`

// The engine beneath the plugin: HOME, the hook profile, medium-term.md, and ledger.py as a fake.
// mediumTerm = null makes medium-term.md unreadable.
function engine(on: Parameters<TestBody>[1], profile = 'standard', mediumTerm: string | null = MEDIUM_TERM) {
  let prof = profile // setProfile flips the hook profile mid-test
  const media = { present: true } // <agency root>/agents/general-purpose-media.md exists
  const fail = { effortApplied: false } // the ledger.py effort_applied run throws
  const runs: Run[] = []
  const logs: string[] = []
  const toasts: string[] = []
  // The model-pin script (hooks/lib/model-pin.py) as a fake: `reply` is its stdout, 'THROW' makes the run fail.
  const pin = { reply: '{"action":"pass","model":null}', calls: [] as Record<string, unknown>[] }
  // The Jev gate CLI (scripts/jev-spawn-gate.py) as a fake, so no test depends on it existing: default pass. The gate
  // ships disabled with the skill router: `router` is AGENCY_SKILL_ROUTER as the mod reads it (undefined = unset).
  const jev = { reply: '{"action":"pass"}', calls: [] as Record<string, unknown>[], order: [] as string[], router: undefined as string | undefined }
  let n = 0
  on('env.get', (_$, e) => ({ value: e.name === 'HOME' ? '/home/t' : e.name === 'AGENCY_SKILL_ROUTER' ? jev.router : undefined }))
  on('fs.read', (_$, e) => {
    // seenPosix: a real Windows host path.resolve()s '/home/t/x' to 'D:\\home\\t\\x' before the stub sees it.
    if (seenPosix(e.path).endsWith('/agents/general-purpose-media.md')) {
      if (!media.present) throw new Error('ENOENT')
      return { value: '---\nname: general-purpose-media\n---\n' }
    }
    if (!seenPosix(e.path).endsWith('/memory/medium-term.md')) return { value: prof }
    if (mediumTerm === null) throw new Error('ENOENT')
    return { value: mediumTerm }
  })
  on('process.run', (_$, e) => {
    if (String(e.argv[1]).endsWith('/jev-spawn-gate.py')) {
      jev.order.push('jev')
      jev.calls.push(JSON.parse(e.init?.stdin ?? '{}') as Record<string, unknown>)
      if (jev.reply === 'THROW') throw new Error('spawn python3 ENOENT')
      return { value: { exitCode: 0, stdout: jev.reply, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    }
    if (String(e.argv[1]).endsWith('/model-pin.py')) {
      jev.order.push('pin')
      pin.calls.push(JSON.parse(e.init?.stdin ?? '{}') as Record<string, unknown>)
      if (pin.reply === 'THROW') throw new Error('spawn python3 ENOENT')
      return { value: { exitCode: 0, stdout: pin.reply, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    }
    const cmd = String(e.argv[2])
    if (cmd === 'effort_applied' && fail.effortApplied) throw new Error('python gone')
    const payload = JSON.parse(e.init?.stdin ?? '{}') as Record<string, unknown>
    runs.push({ cmd, payload })
    const stdout =
      cmd === 'start' ? `sid-${++n}\n`
        : cmd === 'verify' && String(payload.text).includes('/nope/') ? 'ARTIFACT_MISSING /nope/x.html'
          : cmd === 'end' && payload.agent_type === 'noop' ? 'silent no-op spawn: <5s/0 tools, treat as unverified' : ''
    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('ui.toast', (_$, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.log', (_$, e) => {
    logs.push(e.text)
    return { value: undefined }
  })
  on('turn.complete', (_$, e) => ({ text: e.answer }))
  return { runs, logs, toasts, pin, jev, media, fail, setProfile: (p: string) => void (prof = p) }
}

test('slug parsing', async () => {
  expect(respawnSlug('done.\nRESPAWN_REQUEST system-improvement\n')).toBe('system-improvement')
  expect(respawnSlug('no request here')).toBe(null)
  expect(respawnNotice('ltv', 'PD ltv', '/r')).toContain('/pd-resume ltv')
  expect(respawnNotice('ltv', 'PD ltv', '/r')).toContain('rm /r/state/respawn-queue/ltv')
})

test('slug parsing: only an own, bare line counts', async () => {
  // Quoted inside prose.
  expect(respawnSlug('The RESPAWN_REQUEST contract says to run /pd-resume.')).toBe(null)
  expect(respawnSlug('Fixture phrase: RESPAWN_REQUEST contract applies here')).toBe(null)
  // Code span, quote, bullet, bold, fenced block.
  expect(respawnSlug('see `RESPAWN_REQUEST ltv` above')).toBe(null)
  expect(respawnSlug('> RESPAWN_REQUEST ltv')).toBe(null)
  expect(respawnSlug('- RESPAWN_REQUEST ltv')).toBe(null)
  expect(respawnSlug('**RESPAWN_REQUEST ltv**')).toBe(null)
  expect(respawnSlug('Example:\n```\nRESPAWN_REQUEST ltv\n```\ndone')).toBe(null)
  // Own line, with indent / CRLF / after other lines.
  expect(respawnSlug('done\n  RESPAWN_REQUEST ltv\n')).toBe('ltv')
  expect(respawnSlug('done\r\nRESPAWN_REQUEST ltv\r\n')).toBe('ltv')
  expect(respawnSlug('RESPAWN_REQUEST ltv now')).toBe(null)
  // A fenced example before the real line does not hide the real line.
  expect(respawnSlug('```\nx\n```\nRESPAWN_REQUEST ltv')).toBe('ltv')
})

test('known slugs: first cell of the Active Projects table only', async () => {
  expect([...parseKnownSlugs(MEDIUM_TERM)]).toEqual(['ltv', 'system-improvement', 'acme'])
  expect(parseKnownSlugs('no table').size).toBe(0)
})

async function backgroundReport($: Parameters<TestBody>[0], on: Parameters<TestBody>[1], message: string) {
  on('agent.spawn', () => ({ model: 'm', agentId: 'bg1' }))
  on('tool.call', () => ({ result: 'ok' }) as never)
  await $.agent.spawn({ prompt: 'p', description: 'PD', subagentType: 'ltv-pd', tool_use_id: 't9', background: true } as never)
  await $.tool.call({ tool: 'SubagentHandback', agentId: 'bg1', message } as never)
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't', agentId: 'bg1', reason: 'answer' } as never)
}

test('prose or code span quoting RESPAWN_REQUEST: no toast, no notice', async ($, on) => {
  const { logs, toasts } = engine(on)
  await backgroundReport($, on, 'Tested the RESPAWN_REQUEST contract; also `RESPAWN_REQUEST ltv` quoted.\n> RESPAWN_REQUEST ltv')
  expect(toasts).toHaveLength(0)
  expect(logs).toHaveLength(0)
})

test('own line, known slug: toast + notice', async ($, on) => {
  const { logs, toasts } = engine(on)
  await backgroundReport($, on, 'STATUS: DONE\nRESPAWN_REQUEST ltv\n')
  expect(toasts).toEqual(['RESPAWN_REQUEST ltv: run /pd-resume ltv'])
  expect(logs).toHaveLength(1)
  expect(logs[0]).toContain('/pd-resume ltv')
})

test('own line, unknown slug: no toast, no notice, one ignored log line', async ($, on) => {
  const { logs, toasts } = engine(on)
  await backgroundReport($, on, 'RESPAWN_REQUEST contract')
  expect(toasts).toHaveLength(0)
  expect(logs).toEqual(['ignored RESPAWN_REQUEST contract: not a known project'])
})

test('medium-term.md unreadable: anchored match alone decides, with a warning', async ($, on) => {
  const { logs, toasts } = engine(on, 'standard', null)
  await backgroundReport($, on, 'RESPAWN_REQUEST contract')
  expect(toasts).toEqual(['RESPAWN_REQUEST contract: run /pd-resume contract'])
  expect(logs).toHaveLength(2)
  expect(logs[0]).toContain('unreadable')
  expect(logs[1]).toContain('/pd-resume contract')
})

test('logs start + launched with native lineage: child parent_spawn_id = parent spawn_id', async ($, on) => {
  const { runs } = engine(on)
  let id = 0
  on('agent.spawn', () => ({ model: 'claude-sonnet-5-5', agentId: `a${++id}` }))
  await $.agent.spawn({ prompt: 'p', description: 'pd', subagentType: 'system-improvement-pd', tool_use_id: 't1', background: true } as never)
  await $.agent.spawn({ prompt: 'c', description: 'coord', subagentType: 'coord', tool_use_id: 't2', background: true, parentAgentId: 'a1' } as never)
  expect(runs.map(r => r.cmd)).toEqual(['start', 'launched', 'start', 'launched'])
  expect(runs[0]?.payload).toMatchObject({ tool_use_id: 't1', subagent_type: 'system-improvement-pd', parent_spawn_id: '', parent_agent: 'root' })
  expect(runs[1]?.payload).toEqual({ tool_use_id: 't1', agent_id: 'a1', resolved_model: 'claude-sonnet-5-5' })
  expect(runs[2]?.payload).toMatchObject({ parent_spawn_id: 'sid-1', parent_agent: 'system-improvement-pd' })
})

test('background agent: RESPAWN_REQUEST and missing artifact are toasted and logged', async ($, on) => {
  const { logs, toasts, runs } = engine(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'bg1' }))
  on('tool.call', () => ({ result: 'ok' }) as never)
  await $.agent.spawn({ prompt: 'p', description: 'ltv PD', subagentType: 'ltv-pd', tool_use_id: 't9', background: true } as never)
  // The report arrives through SubagentHandback, the answer text is empty.
  await $.tool.call({ tool: 'SubagentHandback', agentId: 'bg1', message: 'STATUS: DONE /nope/x.html\nRESPAWN_REQUEST ltv' } as never)
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't', agentId: 'bg1', reason: 'answer' } as never)
  expect(runs.find(r => r.cmd === 'verify')?.payload.text).toContain('RESPAWN_REQUEST ltv')
  // The person sees both lines; the same text goes to the parent loop by $.session.append,
  // which this kit does not route to test hooks (verified live, not here).
  expect(logs).toHaveLength(2)
  expect(logs[0]).toContain('ARTIFACT_MISSING')
  expect(logs[1]).toContain('/pd-resume ltv')
  expect(toasts.some(t => t.includes('RESPAWN_REQUEST ltv'))).toBe(true)
})

test('foreground agent: the artifact warning rides the Agent result as context', async ($, on) => {
  const { logs } = engine(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'fg1' }))
  on('tool.call', { tool: 'Agent' }, async () => {
    // The subagent finishes inside its parent's still-open Agent call.
    await $.turn.complete({ answer: 'DONE wrote /nope/x.html', durationMs: 1, isAborted: false, turnId: 't', agentId: 'fg1', reason: 'answer' } as never)
    return { result: 'agent text' } as never
  })
  await $.agent.spawn({ prompt: 'p', description: 'exec', subagentType: 'task-executor', tool_use_id: 'tA', background: false } as never)
  const ran = await $.tool.call({ tool: 'Agent', tool_use_id: 'tA', prompt: 'p', description: 'exec', subagent_type: 'task-executor' } as never)
  expect(ran.context).toEqual(['ARTIFACT_MISSING /nope/x.html'])
  expect(logs).toHaveLength(0)
})

test('hook profile minimal: nothing is logged', async ($, on) => {
  const { runs } = engine(on, 'minimal\n')
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn({ prompt: 'p', description: 'x', subagentType: 'coord', tool_use_id: 't1', background: true } as never)
  await $.turn.complete({ answer: 'DONE /nope/x.html', durationMs: 1, isAborted: false, turnId: 't', agentId: 'a1', reason: 'answer' } as never)
  expect(runs).toHaveLength(0)
})

test('SubagentStop hands its whole payload to ledger.py end (transcript path for cost)', async ($, on) => {
  const { runs } = engine(on)
  on('classic.SubagentStop', () => ({}))
  await $.classic.SubagentStop({ agent_id: 'a1', agent_type: 'coord', agent_transcript_path: '/t/a1.jsonl', stop_hook_active: false } as never)
  expect(runs.map(r => r.cmd)).toEqual(['end'])
  expect(runs[0]?.payload).toMatchObject({ hook_event_name: 'SubagentStop', agent_id: 'a1', agent_transcript_path: '/t/a1.jsonl' })
})

test('silent no-op spawn: the ledger warning rides the foreground Agent result as context', async ($, on) => {
  engine(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'fg2' }))
  on('classic.SubagentStop', () => ({}))
  on('tool.call', { tool: 'Agent' }, async () => {
    await $.classic.SubagentStop({ agent_id: 'fg2', agent_type: 'noop', agent_transcript_path: '/t/fg2.jsonl', stop_hook_active: false } as never)
    return { result: 'agent text' } as never
  })
  await $.agent.spawn({ prompt: 'p', description: 'exec', subagentType: 'noop', tool_use_id: 'tB', background: false } as never)
  const ran = await $.tool.call({ tool: 'Agent', tool_use_id: 'tB', prompt: 'p', description: 'exec', subagent_type: 'noop' } as never)
  expect(ran.context).toEqual(['silent no-op spawn: <5s/0 tools, treat as unverified'])
})

// ---- model pin / Exec cap policy: glue around hooks/lib/model-pin.py, which has its own tests

const spawnCall = (extra: Record<string, unknown> = {}) =>
  ({ prompt: 'do it', description: 'exec', subagentType: 'general-purpose', model: 'opus', tool_use_id: 'tP', background: true, ...extra }) as never

test('model pin: rewrite with a model replaces the param the spawn runs with', async ($, on) => {
  const { runs, pin } = engine(on)
  pin.reply = '{"action":"rewrite","model":"sonnet","old":"opus","new":"sonnet","reason":"gp_category_map"}'
  const seen: Array<string | undefined> = []
  on('agent.spawn', (_$, e) => (seen.push(e.model), { model: 'claude-sonnet-5-5', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  expect(seen).toEqual(['sonnet'])
  expect(runs[0]?.payload).toMatchObject({ model: 'sonnet' })
})

test('model pin: rewrite with model null strips the param (frontmatter decides)', async ($, on) => {
  const { runs, pin } = engine(on)
  pin.reply = '{"action":"rewrite","model":null,"old":"opus","new":"sonnet[1m]","reason":"named_frontmatter_wins"}'
  const seen: Array<string | undefined> = []
  on('agent.spawn', (_$, e) => (seen.push(e.model), { model: 'claude-sonnet-5-5', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ subagentType: 'task-executor' }))
  expect(seen).toEqual([undefined])
  expect(runs[0]?.payload).toMatchObject({ model: '' })
})

test('model pin: deny refuses the spawn and writes no ledger row', async ($, on) => {
  const { runs, pin } = engine(on)
  pin.reply = '{"action":"deny","model":null,"reason":"spawn_cap","deny":"[spawn-cap] 5 Execs already running"}'
  let started = 0
  on('agent.spawn', () => (started++, { model: 'm', agentId: 'a1' }))
  const res = await $.agent.spawn(spawnCall())
  expect(res.deny).toBe('[spawn-cap] 5 Execs already running')
  expect(started).toBe(0)
  expect(runs).toHaveLength(0)
})

test('model pin: sends the spawn facts, parent lineage included', async ($, on) => {
  const { pin } = engine(on)
  let id = 0
  on('agent.spawn', () => ({ model: 'm', agentId: `a${++id}` }))
  await $.agent.spawn(spawnCall({ subagentType: 'coord', model: undefined, tool_use_id: 't1' }))
  await $.agent.spawn(spawnCall({ tool_use_id: 't2', parentAgentId: 'a1', prompt: 'MODEL-CATEGORY: lookup' }))
  expect(pin.calls[0]).toMatchObject({ subagent_type: 'coord', model: null, fork: false, is_teammate: false, workflow: false, parent_spawn_id: '', parent_agent: 'root', tool_use_id: 't1' })
  expect(pin.calls[1]).toMatchObject({ subagent_type: 'general-purpose', model: 'opus', parent_spawn_id: 'sid-1', parent_agent: 'coord', prompt: 'MODEL-CATEGORY: lookup' })
})

test('model pin: any failure fails open, the spawn goes through unchanged', async ($, on) => {
  const { runs, pin, logs } = engine(on)
  const seen: Array<string | undefined> = []
  on('agent.spawn', (_$, e) => (seen.push(e.model), { model: 'm', agentId: 'a1' }))
  for (const reply of ['THROW', 'not json', '', '{"action":"weird"}', '{"action":"deny"}', 'null']) {
    pin.reply = reply
    await $.agent.spawn(spawnCall())
  }
  expect(seen).toEqual(Array(6).fill('opus'))
  expect(runs.filter(r => r.cmd === 'start')).toHaveLength(6)
  expect(logs.length).toBeGreaterThan(0)
})

test('model pin: hook profile minimal never runs it', async ($, on) => {
  const { pin } = engine(on, 'minimal\n')
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  expect(pin.calls).toHaveLength(0)
})

// ---- Jev routing gate: glue around scripts/jev-spawn-gate.py, faked here (the CLI has its own tests).
// Ships DISABLED with the skill router: the mod calls the gate only when AGENCY_SKILL_ROUTER is exactly "1".

test('parseJevGate: pass, rewrite and deny parse; the last stdout line wins', () => {
  expect(parseJevGate('{"action":"pass"}')).toEqual({ action: 'pass', note: undefined, route_id: undefined })
  expect(parseJevGate('warming up\n{"action":"pass","note":"n","route_id":"3fa9c1d2"}\n')).toEqual({ action: 'pass', note: 'n', route_id: '3fa9c1d2' })
  expect(parseJevGate('{"action":"rewrite","prompt":"Skills: /a\\ndo it","note":"injected","route_id":"3fa9c1d2"}')).toEqual({
    action: 'rewrite',
    prompt: 'Skills: /a\ndo it',
    note: 'injected',
    route_id: '3fa9c1d2',
  })
  expect(parseJevGate('{"action":"deny","deny":"[jev-gate] add a Jev line","route_id":"3fa9c1d2"}')).toEqual({
    action: 'deny',
    deny: '[jev-gate] add a Jev line',
    route_id: '3fa9c1d2',
  })
})

test('parseJevGate: anything malformed is null (fail open)', () => {
  for (const bad of ['', 'not json', 'null', '[]', '"pass"', '{}', '{"action":"weird"}', '{"action":"Pass"}']) {
    expect(parseJevGate(bad)).toBeNull()
  }
})

test('parseJevGate: rewrite without a prompt and deny without a message are null', () => {
  for (const bad of ['{"action":"rewrite"}', '{"action":"rewrite","prompt":""}', '{"action":"rewrite","prompt":5}', '{"action":"deny"}', '{"action":"deny","deny":""}', '{"action":"deny","deny":7}']) {
    expect(parseJevGate(bad)).toBeNull()
  }
})

test('jev gate, router OFF (unset): no python process starts and the spawn is untouched even if the gate would deny', async ($, on) => {
  const { runs, jev } = engine(on)
  jev.reply = '{"action":"deny","deny":"[jev-gate] must never be seen"}'
  const seen: string[] = []
  on('agent.spawn', (_$, e) => (seen.push(e.prompt), { model: 'm', agentId: 'a1' }))
  const res = await $.agent.spawn(spawnCall())
  expect(res.deny).toBeUndefined()
  expect(seen).toEqual(['do it'])
  expect(jev.calls).toHaveLength(0)
  expect(jev.order).toEqual(['pin']) // only the model pin ran: the gate script was never started
  expect(runs.filter(r => r.cmd === 'start')).toHaveLength(1)
})

test('jev gate, router not exactly "1": off for "", "0", "true", "yes"', async ($, on) => {
  const { jev } = engine(on)
  jev.reply = '{"action":"deny","deny":"[jev-gate] must never be seen"}'
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  for (const value of ['', '0', 'true', 'yes', ' 1']) {
    jev.router = value
    const res = await $.agent.spawn(spawnCall())
    expect(res.deny).toBeUndefined()
  }
  expect(jev.calls).toHaveLength(0)
})

test('jev gate, router ON: sends the spawn facts, parent lineage included', async ($, on) => {
  const { jev } = engine(on)
  jev.router = '1'
  let id = 0
  on('agent.spawn', () => ({ model: 'm', agentId: `a${++id}` }))
  await $.agent.spawn(spawnCall({ subagentType: 'coord', model: undefined, tool_use_id: 't1', description: 'd1' }))
  await $.agent.spawn(spawnCall({ tool_use_id: 't2', parentAgentId: 'a1', prompt: 'Skills: /x' }))
  expect(jev.calls[0]).toEqual({ tool_use_id: 't1', subagent_type: 'coord', description: 'd1', prompt: 'do it', parent_agent: 'root', parent_spawn_id: '', fork: false, is_teammate: false, workflow: false })
  expect(jev.calls[1]).toMatchObject({ tool_use_id: 't2', subagent_type: 'general-purpose', prompt: 'Skills: /x', parent_agent: 'coord', parent_spawn_id: 'sid-1' })
})

test('jev gate, router ON: deny refuses the spawn, writes no ledger row and never reaches the model pin', async ($, on) => {
  const { runs, jev } = engine(on)
  jev.router = '1'
  jev.reply = '{"action":"deny","deny":"[jev-gate] Jev[r=3fa9c1d2]: accept|modify|reject — <reason>","route_id":"3fa9c1d2"}'
  let started = 0
  on('agent.spawn', () => (started++, { model: 'm', agentId: 'a1' }))
  const res = await $.agent.spawn(spawnCall())
  expect(res.deny).toContain('[jev-gate]')
  expect(started).toBe(0)
  expect(runs).toHaveLength(0)
  expect(jev.order).toEqual(['jev']) // the pin (and its cap slot) was never consulted
})

test('jev gate, router ON: rewrite replaces the prompt the pin, the ledger and the subagent see', async ($, on) => {
  const { runs, jev } = engine(on)
  jev.router = '1'
  jev.reply = '{"action":"rewrite","prompt":"Jev[r=3fa9c1d2]: accept — auto: Jev default (gate pass)\\nSkills: /a\\ndo it"}'
  const seen: string[] = []
  on('agent.spawn', (_$, e) => (seen.push(e.prompt), { model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  const rewritten = 'Jev[r=3fa9c1d2]: accept — auto: Jev default (gate pass)\nSkills: /a\ndo it'
  expect(seen).toEqual([rewritten])
  expect(runs[0]?.payload).toMatchObject({ prompt: rewritten })
  expect(jev.order).toEqual(['jev', 'pin']) // gate first
})

test('jev gate, router ON: pass leaves the spawn untouched', async ($, on) => {
  const { runs, jev } = engine(on)
  jev.router = '1'
  const seen: string[] = []
  on('agent.spawn', (_$, e) => (seen.push(e.prompt), { model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  expect(seen).toEqual(['do it'])
  expect(jev.calls).toHaveLength(1)
  expect(runs.filter(r => r.cmd === 'start')).toHaveLength(1)
})

test('jev gate, router ON: Jev down or any failure never blocks; the spawn goes through unchanged and the reason is logged', async ($, on) => {
  const { runs, jev, logs } = engine(on)
  jev.router = '1'
  const seen: string[] = []
  on('agent.spawn', (_$, e) => (seen.push(e.prompt), { model: 'm', agentId: 'a1' }))
  for (const reply of ['THROW', 'not json', '', '{"action":"weird"}', '{"action":"deny"}', '{"action":"rewrite"}', 'null']) {
    jev.reply = reply
    await $.agent.spawn(spawnCall())
  }
  expect(seen).toEqual(Array(7).fill('do it'))
  expect(runs.filter(r => r.cmd === 'start')).toHaveLength(7)
  expect(logs.some(l => l.startsWith('jev-gate skipped (fail open)'))).toBe(true)
})

test('jev gate, router ON: note rides the Agent result as context', async ($, on) => {
  const { jev } = engine(on)
  jev.router = '1'
  jev.reply = '{"action":"pass","note":"[jev-gate] Jev unavailable, spawn recorded as unreviewed"}'
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  // As in the engine, the spawn happens inside the still-open Agent tool call.
  on('tool.call', { tool: 'Agent' }, async () => {
    await $.agent.spawn(spawnCall({ tool_use_id: 'tN' }))
    return { result: 'agent text' } as never
  })
  const ran = await $.tool.call({ tool: 'Agent', tool_use_id: 'tN', prompt: 'p', description: 'exec', subagent_type: 'general-purpose' } as never)
  expect(ran.context).toEqual(['[jev-gate] Jev unavailable, spawn recorded as unreviewed'])
})

test('jev gate, router ON: hook profile minimal never runs it', async ($, on) => {
  const { jev } = engine(on, 'minimal\n')
  jev.router = '1'
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  expect(jev.calls).toHaveLength(0)
})

test('jev gate, router ON: a note with no open Agent call (a workflow agent) is dropped, never leaked to a later call', async ($, on) => {
  const { jev } = engine(on)
  jev.router = '1'
  jev.reply = '{"action":"pass","note":"stray"}'
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  on('tool.call', { tool: 'Agent' }, () => ({ result: 'agent text' }) as never)
  await $.agent.spawn(spawnCall({ tool_use_id: 'tW' }))
  const later = await $.tool.call({ tool: 'Agent', tool_use_id: 'tW', prompt: 'p', description: 'exec', subagent_type: 'general-purpose' } as never)
  expect(later.context ?? []).toEqual([])
})

// ---- effort relay: model-pin.py DECIDES an effort at agent.spawn (AgentSpawnInput has no effort field), this remembers it
// per subagent and APPLIES it on that subagent's turn.step, the way the pin sets `model`. The fake pin stands in for the script.

test('parsePin: effort and effort_category ride pass and rewrite; malformed effort is dropped, not an error', () => {
  expect(parsePin('{"action":"pass","model":null,"effort":"medium","effort_category":"pd"}')).toEqual({
    action: 'pass', model: null, effort: 'medium', effort_category: 'pd',
  })
  expect(parsePin('{"action":"rewrite","model":"sonnet","reason":"r","effort":"xhigh","effort_category":"content_vi"}')).toEqual({
    action: 'rewrite', model: 'sonnet', reason: 'r', effort: 'xhigh', effort_category: 'content_vi',
  })
  for (const effort of ['low', 'medium', 'high', 'xhigh', 'max']) {
    expect(parsePin(`{"action":"pass","effort":"${effort}"}`)?.effort).toBe(effort)
  }
  for (const bad of ['"turbo"', '"HIGH"', '""', '5', 'null', 'true', '["high"]']) {
    const pin = parsePin(`{"action":"pass","effort":${bad},"effort_category":"x"}`)
    expect(pin?.action).toBe('pass') // still a usable pin
    expect(pin?.effort).toBeUndefined()
  }
  expect(parsePin('{"action":"pass","effort_category":7}')?.effort_category).toBeUndefined()
  expect(parsePin('{"action":"pass"}')?.effort).toBeUndefined()
  // deny carries no effort
  expect(parsePin('{"action":"deny","deny":"cap","effort":"high"}')).toEqual({ action: 'deny', model: null, deny: 'cap' })
})

type Seen = Array<{ agentId?: string; effort?: unknown }>

// The bottom of the turn.step chain: records what the engine would send.
function bottomStep(on: Parameters<TestBody>[1]): Seen {
  const seen: Seen = []
  on('turn.step', async function* (_$, e) {
    seen.push({ agentId: e.agentId, effort: e.effort })
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn' } as never
  })
  return seen
}

async function step($: Parameters<TestBody>[0], agentId: string | undefined, effort?: string) {
  const stream = $.turn.step({ turnId: 't', index: 0, model: 'claude-sonnet-5-5', messageCount: 3, agentId, effort } as never)
  for await (const _ of stream) {
    // drain
  }
}

const PD_PIN = '{"action":"pass","model":null,"effort":"medium","effort_category":"pd"}'

test('effort relay: the spawned agent\'s turn.step reaches the bottom with the pin effort, whatever the caller sent', async ($, on) => {
  const { pin } = engine(on)
  pin.reply = '{"action":"pass","model":null,"effort":"high","effort_category":"coding_complex"}'
  const seen = bottomStep(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  await step($, 'a1', 'low') // the caller's effort differs from the policy
  expect(seen).toEqual([{ agentId: 'a1', effort: 'high' }])
  await step($, 'a1') // no effort at all (model without one set): the policy still applies
  expect(seen[1]).toEqual({ agentId: 'a1', effort: 'high' })
})

test('effort relay: another agent, no agentId and an equal effort are untouched', async ($, on) => {
  const { pin, runs } = engine(on)
  pin.reply = PD_PIN
  const seen = bottomStep(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  on('agent.list', () => ({ value: [] }) as never)
  await $.agent.spawn(spawnCall({ subagentType: 'ltv-pd' }))
  await step($, 'other', 'low') // not a spawn we pinned
  await step($, undefined, 'low') // the main loop pays nothing
  await step($, 'a1', 'medium') // already the policy value
  expect(seen).toEqual([
    { agentId: 'other', effort: 'low' },
    { agentId: undefined, effort: 'low' },
    { agentId: 'a1', effort: 'medium' },
  ])
  // the main loop and a stranger never reach the ledger; the equal step logs seen == applied
  expect(runs.filter(r => r.cmd === 'effort_applied').map(r => r.payload.agent_id)).toEqual(['a1'])
})

test('effort relay: a fork (the pin returns no effort) is untouched, and so is a pin that predates the key', async ($, on) => {
  const { pin, runs } = engine(on)
  const seen = bottomStep(on)
  let id = 0
  on('agent.spawn', () => ({ model: 'm', agentId: `a${++id}` }))
  on('agent.list', () => ({ value: [] }) as never)
  pin.reply = '{"action":"pass","model":null,"effort":null,"effort_category":null}'
  await $.agent.spawn(spawnCall({ subagentType: 'fork', tool_use_id: 'tF', fork: true }))
  pin.reply = '{"action":"pass","model":null}'
  await $.agent.spawn(spawnCall({ tool_use_id: 'tG' }))
  await step($, 'a1', 'low')
  await step($, 'a2', 'xhigh')
  expect(seen).toEqual([{ agentId: 'a1', effort: 'low' }, { agentId: 'a2', effort: 'xhigh' }])
  expect(runs.filter(r => r.cmd === 'effort_applied')).toHaveLength(0)
})

test('effort relay: a deny pin starts no agent and leaves nothing behind', async ($, on) => {
  const { pin } = engine(on)
  pin.reply = '{"action":"deny","model":null,"deny":"cap","effort":"high"}'
  const seen = bottomStep(on)
  on('agent.list', () => ({ value: [] }) as never)
  await $.agent.spawn(spawnCall())
  await step($, 'a1', 'low')
  expect(seen).toEqual([{ agentId: 'a1', effort: 'low' }])
})

test('effort relay: the first step may beat $.state.set, the agent.list row finds the pending effort', async ($, on) => {
  const { pin } = engine(on)
  pin.reply = '{"action":"pass","model":null,"effort":"xhigh","effort_category":"content_vi"}'
  const seen = bottomStep(on)
  on('agent.list', () => ({ value: [{ id: 'a1', type: 'general-purpose', description: 'exec', status: 'running' }] }) as never)
  on('agent.spawn', async () => {
    await step($, 'a1', 'low') // inside the spawn: the record is not stored yet
    return { model: 'm', agentId: 'a1' }
  })
  await $.agent.spawn(spawnCall())
  expect(seen).toEqual([{ agentId: 'a1', effort: 'xhigh' }])
  // the pending key is gone after the spawn; the stored record now serves later steps
  await step($, 'a1', 'low')
  expect(seen[1]).toEqual({ agentId: 'a1', effort: 'xhigh' })
})

test('effort relay: a pending effort never leaks to a later agent with the same type and description', async ($, on) => {
  const { pin } = engine(on)
  const seen = bottomStep(on)
  on('agent.list', () => ({ value: [{ id: 'ghost', type: 'general-purpose', description: 'exec', status: 'running' }] }) as never)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  pin.reply = '{"action":"pass","model":null,"effort":"high","effort_category":"visual"}'
  await $.agent.spawn(spawnCall())
  await step($, 'ghost', 'low') // listed, but no record and no pending effort left
  expect(seen).toEqual([{ agentId: 'ghost', effort: 'low' }])
})

test('effort relay: the first step per agent writes one effort_applied row with what it saw and applied', async ($, on) => {
  const { pin, runs } = engine(on)
  pin.reply = '{"action":"pass","model":null,"effort":"high","effort_category":"coding_complex"}'
  bottomStep(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ tool_use_id: 'tE' }))
  await step($, 'a1', 'low')
  await step($, 'a1', 'low')
  await step($, 'a1', 'low')
  const rows = runs.filter(r => r.cmd === 'effort_applied')
  expect(rows).toHaveLength(1)
  expect(rows[0]?.payload).toEqual({ tool_use_id: 'tE', agent_id: 'a1', seen: 'low', applied: 'high', category: 'coding_complex' })
})

test('effort relay: seen is null when the request carried no effort', async ($, on) => {
  const { pin, runs } = engine(on)
  pin.reply = '{"action":"pass","model":null,"effort":"low","effort_category":"lookup"}'
  bottomStep(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ tool_use_id: 'tN' }))
  await step($, 'a1')
  expect(runs.find(r => r.cmd === 'effort_applied')?.payload).toEqual({ tool_use_id: 'tN', agent_id: 'a1', seen: null, applied: 'low', category: 'lookup' })
})

test('effort relay: fail open, a throwing lookup sends the step unchanged and logs one line', async ($, on) => {
  const { pin, logs } = engine(on)
  pin.reply = PD_PIN
  const seen = bottomStep(on)
  on('agent.list', () => {
    throw new Error('list down')
  })
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  const before = logs.length
  await step($, 'unknown', 'low') // no record: the fallback lookup throws
  expect(seen).toEqual([{ agentId: 'unknown', effort: 'low' }])
  const added = logs.slice(before)
  expect(added).toHaveLength(1)
  expect(added[0]).toContain('effort relay skipped (fail open)')
})

test('effort relay: a failing effort_applied ledger call never blocks the step or changes its effort', async ($, on) => {
  const { pin, fail } = engine(on)
  pin.reply = '{"action":"pass","model":null,"effort":"high","effort_category":"visual"}'
  fail.effortApplied = true
  const seen = bottomStep(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  await step($, 'a1', 'low')
  expect(seen).toEqual([{ agentId: 'a1', effort: 'high' }])
})

test('effort relay: hook profile minimal leaves every step untouched', async ($, on) => {
  const { pin, runs, setProfile } = engine(on)
  pin.reply = PD_PIN
  const seen = bottomStep(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ subagentType: 'ltv-pd' }))
  setProfile('minimal\n') // recorded under standard, applied under minimal: still off
  await step($, 'a1', 'low')
  expect(seen).toEqual([{ agentId: 'a1', effort: 'low' }])
  expect(runs.filter(r => r.cmd === 'effort_applied')).toHaveLength(0)
})

test('effort relay: minimal at spawn never runs the pin, so no step is touched', async ($, on) => {
  const { pin } = engine(on, 'minimal\n')
  pin.reply = PD_PIN
  const seen = bottomStep(on)
  on('agent.spawn', () => ({ model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall())
  await step($, 'a1', 'low')
  expect(pin.calls).toHaveLength(0)
  expect(seen).toEqual([{ agentId: 'a1', effort: 'low' }])
})

// ---- Higgsfield fence: a bare general-purpose spawn is fenced (agents/general-purpose.md); Higgsfield work is
// rewritten to the unfenced agents/general-purpose-media.md AFTER the Jev gate, the pin and the ledger 'start' saw the original type.

test('isHiggsfieldWork: Skills line, tool name or MEDIA-WORK marker; plain prompts are not', () => {
  expect(isHiggsfieldWork('Skills: /higgsfield-functions, /x')).toBe(true)
  expect(isHiggsfieldWork('task\nSkills: /plugin-authoring, /higgsfield-stickman-video\nmore')).toBe(true)
  expect(isHiggsfieldWork('call mcp__claude_ai_Higgsfield__generate_image now')).toBe(true)
  expect(isHiggsfieldWork('hello\nMEDIA-WORK: higgsfield\n')).toBe(true)
  expect(isHiggsfieldWork('Skills: /frontend, /backend')).toBe(false)
  expect(isHiggsfieldWork('discuss higgsfield pricing')).toBe(false)
  expect(isHiggsfieldWork('')).toBe(false)
})

test('higgsfield fence: Higgsfield work on general-purpose is rewritten to general-purpose-media; pin and ledger saw the original', async ($, on) => {
  const { runs, pin } = engine(on)
  const seen: Array<string | undefined> = []
  on('agent.spawn', (_$, e) => (seen.push(e.subagentType), { model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ prompt: 'Skills: /higgsfield-functions' }))
  expect(seen).toEqual(['general-purpose-media'])
  expect(pin.calls[0]).toMatchObject({ subagent_type: 'general-purpose' })
  expect(runs[0]).toMatchObject({ cmd: 'start', payload: { subagent_type: 'general-purpose' } })
  expect(runs[1]).toMatchObject({ cmd: 'launched', payload: { actual_type: 'general-purpose-media' } })
})

test('higgsfield fence: an empty type is rewritten too', async ($, on) => {
  engine(on)
  const seen: Array<string | undefined> = []
  on('agent.spawn', (_$, e) => (seen.push(e.subagentType), { model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ subagentType: '', prompt: 'MEDIA-WORK: higgsfield' }))
  expect(seen).toEqual(['general-purpose-media'])
})

test('higgsfield fence: no rewrite for plain prompts, other types, or an absent media file (fail open)', async ($, on) => {
  const { media } = engine(on)
  const seen: Array<string | undefined> = []
  on('agent.spawn', (_$, e) => (seen.push(e.subagentType), { model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ prompt: 'Skills: /frontend' }))
  await $.agent.spawn(spawnCall({ subagentType: 'coord', prompt: 'Skills: /higgsfield-functions' }))
  await $.agent.spawn(spawnCall({ subagentType: 'claude', prompt: 'Skills: /higgsfield-functions' }))
  media.present = false
  await $.agent.spawn(spawnCall({ prompt: 'Skills: /higgsfield-functions' }))
  expect(seen).toEqual(['general-purpose', 'coord', 'claude', 'general-purpose'])
})

test('higgsfield fence: hook profile minimal never rewrites', async ($, on) => {
  const { setProfile } = engine(on)
  setProfile('minimal')
  const seen: Array<string | undefined> = []
  on('agent.spawn', (_$, e) => (seen.push(e.subagentType), { model: 'm', agentId: 'a1' }))
  await $.agent.spawn(spawnCall({ prompt: 'Skills: /higgsfield-functions' }))
  expect(seen).toEqual(['general-purpose'])
})

test('higgsfield fence: the pending effort key uses the ACTUAL type (turn.step fallback lists the actual type)', async ($, on) => {
  const { pin } = engine(on)
  pin.reply = '{"action":"pass","model":null,"effort":"high","effort_category":"coding_complex"}'
  const seen = bottomStep(on)
  on('agent.list', () => ({ value: [{ id: 'a1', type: 'general-purpose-media', description: 'd' }] }) as never)
  on('agent.spawn', async () => {
    await step($, 'a1', 'low') // inside the spawn: the record is not stored yet, only the pending map can answer
    return { model: 'm', agentId: 'a1' }
  })
  await $.agent.spawn(spawnCall({ prompt: 'Skills: /higgsfield-functions', description: 'd' }))
  expect(seen).toEqual([{ agentId: 'a1', effort: 'high' }])
})
