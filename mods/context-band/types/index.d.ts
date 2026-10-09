export type Cache = {
  /** Last main-thread response: uncached input, cache read, cache write, output. */
  input: number
  read: number
  write: number
  output: number
  /** When that response landed, epoch ms. */
  at: number
}

export type Limit = { percentUsed: number; resetsAt: number | null }

export type Category = { name: string; tokens: number }

export type Usage = {
  tokens: number | null
  window: number
  percent: number | null
  model: string
  costUsd: number | null
  cache: Cache | null
  categories: Category[]
  /** Rate-limit windows: % used and reset time (epoch ms). */
  fiveHour: Limit | null
  sevenDay: Limit | null
}

/** Outage flag (`<root>/state/skill-route/jev-down`): `since` as the writer wrote it, null if absent/unparseable. */
export type JevDown = { since: string | null }

/** Today's (local day) Jev router figures from `jev-usage.jsonl`, plus the outage flag. */
export type JevView = {
  calls: number
  inputTokens: number
  usd: number
  /** Haiku-fallback calls and their USD (the writer's `usd`, never re-priced here). */
  fbCalls: number
  fbUsd: number
  down: JevDown | null
}

declare module 'claude-code' {
  interface PluginState {
    'context-band': {
      usage: Usage | null
      now: number
      jev: JevView | null
      /** `since` of the outage already toasted (debounce across hot reloads). */
      jevToasted: string | null
    }
  }
}
