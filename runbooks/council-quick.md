# Decision Protocol — Council Quick
# LAZY-LOAD source for pd-coordinator.md — extracted F19 (2026-06-23)
# Load this file when facing ambiguous architectural decisions.

## Decision Protocol — Council Quick

When facing ambiguous architectural decisions (2+ credible approaches, no obvious winner):

1. State your initial position (Architect voice) — recommendation + 3 reasons + main risk
2. Spawn 3 Sonnet agents in parallel, each with ONLY the decision question + constraints:
   - **Skeptic:** challenges premises, proposes simpler alternatives
   - **Pragmatist:** shipping speed, user impact, operational reality
   - **Critic:** edge cases, downside risk, failure modes
3. Each returns: position (1-2 sentences), 3 bullets, biggest risk, one "surprise"
4. Synthesize — if any voice changed your recommendation, say so explicitly

**Anti-anchoring rule:** Do NOT share your analysis or conversation history with the 3 voices.
They must reason independently. Fresh context only.

**Do NOT use for:** code review, planning, factual questions, obvious execution tasks.
