export type Fill = {
  /** Last request's input side over the loop's window (main) or over the 300k subagent cap (subagents), whole percent. */
  pct: number
  /** Last request's input side in tokens. */
  tokens: number
  /** Main: 0, 70, 75 or 80 (% of window). Subagent: 0, 200, 250 or 300 (absolute k tokens). */
  level: number
  /** Highest level already told to this loop. */
  told: number
  /** Highest level already flagged to its parent (CHILD_CTX_ALERT). */
  parentTold: number
}

declare module 'claude-code' {
  interface PluginState {
    'agent-ctx': {
      /** By agentId ("main" for the main loop). */
      fill: StateFamily<Fill>
    }
  }
}
