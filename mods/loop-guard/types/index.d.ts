/** The last 10 call signatures of one loop, oldest first. */
export type History = string[]

declare module 'claude-code' {
  interface PluginState {
    'loop-guard': {
      /** By agentId ("main" for the main loop). */
      history: StateFamily<History>
    }
  }
}
