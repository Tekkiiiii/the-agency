---
name: ecc-pattern-library
description: Reference patterns from everything-claude-code (ECC) system — hooks, loop safety, council decisions, eval frameworks, cost tracking, model routing. Consult when designing hooks, agents, evals, or decision protocols.
metadata:
  type: reference
  source: github.com/affaan-m/everything-claude-code
  reviewed: 2026-05-17
---

# ECC Pattern Library

Patterns extracted from the everything-claude-code system (60 agents, 230 skills, 9-platform cross-harness). Filtered for relevance to the Tekki system. Source code analyzed, not just documentation.

## Tier 2 — Adopt with Modification

### 1. Hookify — Auto-Generate Rules from Corrections

ECC auto-generates PreToolUse hook rules when the user corrects Claude's behavior. Rules stored as `.claude/hookify.{name}.local.md` with YAML frontmatter (name, enabled, event, pattern regex, action: warn|block).

**Our gap:** Self-improvement loop (`lessons/*.md`) is manual append-only. Hookify closes the loop by creating _code that runs_ rather than _text Claude reads_.

**When to consult:** When a correction surfaces 3+ times in lessons for the same class of mistake.

### 2. Council Quick — 4 Fresh Voices

Four independent agents (Architect, Skeptic, Pragmatist, Critic) receive ONLY the decision question — no shared context, no conversation history. Prevents anchoring bias. Synthesizer must surface strong dissent.

**Our gap:** Agency Council is heavyweight (14 leaders, 2-wave spawn). No mid-weight decision protocol exists.

**When to consult:** Complex architectural decisions or competing approaches. NOT for code review, planning, or factual questions.

### 3. Loop Operator — Safety for Autonomous Loops

Any autonomous loop must have: stall detection (5 identical consecutive tool calls → declare stall), budget cap (max 50 turns), rollback checkpoint (state snapshot before each iteration). Escalate when no progress across 2 checkpoints, repeated identical failures, or context > 70%.

**Our gap:** PDs run in background with no formal loop guard. A stuck PD burns tokens until context exhaustion.

**Action:** Add three rules to `pd-coordinator.md` spawn template: MAX_TURNS 50, STALL_DETECT on 5 identical calls, BUDGET_SIGNAL at context > 70%.

### 4. Strategic Compaction — Active Suggestion

ECC suggests `/compact` at 50 tool calls or at natural task boundaries. Not just a color-coded statusline — an explicit message.

**Our gap:** Statusline changes color at 40%/60% but no active suggestion fires.

**Action:** Add CLAUDE.md rule: "When context exceeds 60%, proactively suggest /compact before starting a new major task."

### 5. Model Routing Matrix

Explicit decision table (not implicit agent frontmatter):

| Task Type | Model | Rationale |
|---|---|---|
| Strategic decisions, architecture | Opus | High-stakes, non-deterministic |
| Code generation, agent execution | Sonnet | Cost-effective, accurate |
| Data extraction, scraping, summarizing | Haiku | Low-stakes, speed |
| PD coordinators | Opus | Long-horizon planning |
| Dept-Coords | Sonnet | Execution-oriented |
| Background PD sessions | Sonnet | Resource-conscious |
| Content pipeline drafts | Sonnet | Draft cheap, review expensive |
| Content pipeline review | Opus | Quality gate |
| Council quick votes | Sonnet x4 | Breadth over depth |

**Our gap:** `modelTier` in agent frontmatter but no documented routing matrix for dynamic decisions.

**Action:** Add to `agency-dispatch.md` as a "Model Routing Matrix" section.

### 6. Eval-Driven Development (EDD)

Define pass/fail criteria BEFORE coding. Metrics: pass@k (any of k attempts succeeds) vs pass^k (all k must succeed). Targets: pass@3 > 90% for capability evals, pass^1 for release-critical. Storage: `.claude/evals/` with cases.jsonl, eval.sh, baseline.json.

**Our gap:** QA dept and gstack eval system exist but no formal eval framework for Tekki-authored skills.

**When to consult:** When authoring a new skill with non-trivial branching logic.

### 7. Context Mode Files

Three overlay files (dev.md, review.md, research.md) loaded dynamically per session mode. Each adds mode-specific instructions without bloating CLAUDE.md permanently.

**Our gap:** On-demand context files exist (trigger table in CLAUDE.md) but no mode-switching system.

**When to consult:** When designing session-type-specific behavior.

---

## Tier 3 — Knowledge Only

### 8. Cross-Harness Adapter

Common interface defined before adapters. Stdin passthrough pattern: read → transform → delegate → write original to stdout. Exit code 2 = block. Profile system via env var (`ECC_HOOK_PROFILE`). 9 platforms supported.

### 9. GAN-Style Harness

Planner→Generator→Evaluator pipeline. 14-22x cost, 2-3x quality. Evaluator grades output and can reject, forcing regeneration. Reviewers never review code they authored.

### 10. Santa Loop

Two different AI models (e.g., Claude + GPT), no shared system prompt. Both must approve before code ships. Max 3 fix cycles. Disagreements surface blind spots a single model misses.

### 11. Instinct-Based Learning v2.1

Project-scoped via SHA1 of git remote URL. Confidence 0.3-0.9. Auto-prune < 0.3, auto-promote > 0.9 to global. Stored outside `~/.claude` at `${XDG_DATA_HOME}/ecc-homunculus/` to avoid sensitivity restrictions.

### 12. PRP Methodology

8 exploration categories before any plan: Context, Stakeholders, Constraints, Risks, Alternatives, Dependencies, Success Metrics, Open Questions. Use as a checklist when running `plan-ceo-review`.

### 13. CLI-over-MCP Strategy

Each MCP tool schema costs ~500 tokens. A 30-tool MCP server costs more context than all skills combined. For large-output operations, prefer CLI via Bash over MCP tool calls.

### 14. Chief-of-Staff Pattern

PostToolUse hooks for follow-through tasks (calendar updates, relationship logging). Key insight: "Hooks over prompts for reliability — LLM memory forgets instructions ~20% of the time; hooks physically cannot skip."

### 15. Confidence-Gated Review

Only report findings with >80% confidence. Four pre-reporting questions: exact file/line, concrete failure scenario, surrounding context reviewed, severity defensible. A clean review is valid — don't manufacture findings.

### 16. De-Sloppify Pattern

Cleanup agent in a SEPARATE context window after implementation. Never combine implementation and cleanup in one pass. "Two focused agents outperform one constrained agent."

### 17. Context Budget Audit

Agent descriptions loaded always — even if the agent is never invoked. Token estimation: words x 1.3 for prose, chars / 4 for code. Keep agent descriptions under 30 words in frontmatter.

### 18. Session Bridge Files

`SHARED_TASK_NOTES.md` bridges independent `claude -p` context windows. Filesystem state as coordination mechanism between agents that cannot message each other.

### 19. Cost Tracking Implementation

JSONL at `~/.claude/metrics/costs.jsonl`. Each row: timestamp, session_id, model, input/output/cache tokens, estimated_cost_usd. Fires at every Stop (cumulative). Last row per session_id = total. Rate table: Haiku $0.80/$4.00, Sonnet $3.00/$15.00, Opus $15.00/$75.00 per 1M tokens.

### 20. Config Protection

30+ linter/formatter config filenames blocked from modification. Uses `lstatSync` (not `existsSync`) to catch permission errors. First-time creation allowed (ENOENT). Fail-closed on truncated input.

---

## Skill-Level Patterns (from 230 ECC skills analyzed)

### 21. Agent Architecture Audit — 12-Layer Diagnostic

Formalized diagnostic stack for agent systems. When an agent misbehaves, check these layers in order:

| # | Layer | What Goes Wrong |
|---|-------|----------------|
| 1 | System prompt | Conflicting instructions, instruction bloat |
| 2 | Session history | Stale context from previous turns |
| 3 | Long-term memory | Pollution across sessions |
| 4 | Distillation | Compressed artifacts re-entering as pseudo-facts |
| 5 | Active recall | Redundant re-summary wasting context |
| 6 | Tool selection | Wrong tool routing |
| 7 | Tool execution | Hallucinated execution — claims to call but doesn't |
| 8 | Tool interpretation | Misread or ignored tool output |
| 9 | Answer shaping | Format corruption in final response |
| 10 | Platform rendering | Transport-layer mutation |
| 11 | Hidden repair loops | Silent fallback/retry agents running second pass |
| 12 | Persistence | Expired state reused as live evidence |

**Quick diagnostic (7 questions):**
1. Can the model skip a required tool and still answer? → Tool not code-gated
2. Does old conversation content appear in new turns? → Memory contamination
3. Is the same info in system prompt AND memory AND history? → Context duplication
4. Does the platform run a second LLM pass before delivery? → Hidden repair loop
5. Does output differ between internal generation and user delivery? → Rendering corruption
6. Are "must use tool X" rules only in prompt text? → Tool discipline failure
7. Can the agent's own monologue become persistent memory? → Memory poisoning

### 22. Agent Self-Debugging — Recovery Heuristics

When an agent is stuck, follow this ordered recovery:
1. Restate the real objective in one sentence
2. Verify the world state instead of trusting memory
3. Shrink the failing scope to one file/test/command
4. Run one discriminating check (not a full re-run)
5. Only then retry

**Output standard:** Never end with "I fixed it" alone. Always provide: failure pattern, root-cause hypothesis, recovery action, evidence of improvement or continued block.

### 23. Autonomous Loop Patterns

**De-Sloppify:** Add a dedicated cleanup agent in a SEPARATE context window after implementation. Never combine implementation and cleanup. "Two focused agents outperform one constrained agent."

**SHARED_TASK_NOTES.md:** Bridges independent context windows. Agent reads at iteration start, updates at end. The standard solution for fresh context per `claude -p` call.

**Completion signal:** Agent outputs a magic phrase N consecutive times → loop stops. Prevents wasted runs on finished work.

**Separate context per pipeline stage:** Reviewer never wrote the code it reviews. Author bias eliminated by architectural separation.

### 24. Knowledge Operations — 6-Layer Architecture

| Layer | What | When |
|-------|------|------|
| 1 | GitHub/Linear | Active execution truth — roadmaps, releases, issues |
| 2 | Memory files | Quick-access markdown with frontmatter |
| 3 | MCP memory / knowledge graph | Semantic search and relationships |
| 4 | Knowledge base repo | Curated durable documents |
| 5 | External data store | Large documents (Supabase/PostgreSQL) |
| 6 | Local archive | Human-facing notes |

**Key rule:** If something affects an active engineering plan, put it in GitHub/Linear FIRST, not a local note.

### 25. Workspace Surface Audit — Gap Classification

When auditing system capabilities, classify each gap into the right ECC shape:

| Gap Type | Preferred Shape |
|----------|----------------|
| Repeatable operator workflow | Skill |
| Automatic enforcement or side-effect | Hook |
| Specialized delegated role | Agent |
| External tool bridge | MCP server |
| Install/bootstrap guidance | Setup skill |

---

## Cross-Cutting Insights

1. **"Hooks fire 100%, skills fire 50-80%"** — All observation/enforcement should live in hooks, not skill instructions
2. **"Two focused agents > one constrained agent"** — Cleanup pass beats negative instructions
3. **Anti-anchoring:** Decision subagents get ONLY the question, never conversation history
4. **Cold-start briefs:** Each plan step should be self-contained for a fresh agent with zero prior context
5. **"The investigation itself creates context that changes the output"** — GateGuard's core insight

---

## Usage Guide for Agents

- Designing a new hook → read sections 1 (Hookify), 14 (Chief-of-Staff), 20 (Config Protection)
- Making architectural decisions → read sections 2 (Council), 5 (Model Routing)
- Authoring a new skill → read sections 6 (EDD), 7 (Context Modes)
- Reviewing code or plans → read section 15 (Confidence-Gated Review)
- Running autonomous loops → read sections 3 (Loop Operator), 23 (Loop Patterns)
- Optimizing costs → read sections 13 (CLI-over-MCP), 17 (Context Budget), 19 (Cost Tracking)
- Debugging agent failures → read sections 21 (12-Layer Audit), 22 (Self-Debugging)
- Classifying system gaps → read section 25 (Workspace Surface Audit)
- Knowledge storage decisions → read section 24 (6-Layer Architecture)

See also: [[video_use_skill]], [[feedback_agent_fix_before_fallback]]
