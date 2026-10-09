import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { parseKnownSlugs, respawnNotice, respawnSlug } from './register'

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
  const runs: Run[] = []
  const logs: string[] = []
  const toasts: string[] = []
  // The model-pin script (hooks/lib/model-pin.py) as a fake: `reply` is its stdout, 'THROW' makes the run fail.
  const pin = { reply: '{"action":"pass","model":null}', calls: [] as Record<string, unknown>[] }
  let n = 0
  on('env.get', (_$, e) => ({ value: e.name === 'HOME' ? '/home/t' : undefined }))
  on('fs.read', (_$, e) => {
    if (!e.path.endsWith('/memory/medium-term.md')) return { value: profile }
    if (mediumTerm === null) throw new Error('ENOENT')
    return { value: mediumTerm }
  })
  on('process.run', (_$, e) => {
    if (String(e.argv[1]).endsWith('/model-pin.py')) {
      pin.calls.push(JSON.parse(e.init?.stdin ?? '{}') as Record<string, unknown>)
      if (pin.reply === 'THROW') throw new Error('spawn python3 ENOENT')
      return { value: { exitCode: 0, stdout: pin.reply, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    }
    const cmd = String(e.argv[2])
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
  return { runs, logs, toasts, pin }
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
