export type Spawn = {
  /** spawn_id written by ledger.py start to the spawn's project log <project>/memory/spawns.jsonl (the agency root logs/spawns.jsonl only when unhinted). */
  spawnId: string
  /** The Agent call that started it. */
  toolUseId: string
  type: string
  description: string
  /** The loop that spawned it; null for the main loop. */
  parentAgentId: string | null
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
