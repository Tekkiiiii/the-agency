export type Spawn = {
  /** spawn_id written by ledger.py start to the spawn's project log <project>/memory/spawns.jsonl (the agency root logs/spawns.jsonl only when unhinted). */
  spawnId: string
  /** The Agent call that started it. */
  toolUseId: string
  /** The type the caller asked for (what the pin, the cap and the ledger row key on). */
  type: string
  /** The type actually spawned when the Higgsfield fence swapped it (general-purpose-media); absent otherwise. */
  actualType?: string
  description: string
  /** The loop that spawned it; null for the main loop. */
  parentAgentId: string | null
  /** The effort hooks/lib/model-pin.py decided at spawn (low|medium|high|xhigh|max); the turn.step relay applies it. Absent: no policy (fork, named_unlisted, kill switch). */
  effort?: string
  /** The policy category behind `effort` (pd, coding_complex, ...). */
  effortCategory?: string
}

declare module 'claude-code' {
  interface PluginState {
    'spawn-ledger': {
      /** By agentId: what agent.spawn recorded. */
      spawns: StateFamily<Spawn>
      /** By agentId: the message its SubagentHandback call carried. */
      report: StateFamily<string>
    }
  }
}
