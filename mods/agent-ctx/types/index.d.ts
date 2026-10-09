export type Fill = {
  /** Last request's input side over the loop's window, 0-100. */
  pct: number
  /** 0 below 70%, 70, or 80. */
  level: number
  /** Highest level already told to this loop. */
  told: number
}

declare module 'claude-code' {
  interface PluginState {
    'agent-ctx': {
      /** By agentId ("main" for the main loop). */
      fill: StateFamily<Fill>
    }
  }
}
