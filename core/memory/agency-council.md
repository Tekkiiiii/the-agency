---
name: Agency Council — On-Demand Reference
type: note
description: Council/BOD protocol -- trigger phrases, 5 independent seats (Fable/Opus/Sonnet/Haiku + Codex on gpt-6-astra) in ONE wave, caller synthesises
created: 2026-04-13
links: []
review-by: 2027-01-08
---
# Agency Council — On-Demand Reference

Redefined 2026-10-08: the 8-lead council is retired. The council is now 5 independent seats, one wave, caller synthesises. Load this file only when a trigger fires.

## Triggers
"BOD", "assemble", "assemble the board", "the board", "the council", "the agency council", "convene the council", "call the board to order". `/resume-bod` restores context first, then runs this protocol.

## Seats (C1)
| Seat | subagent_type | Model (pinned in agent file) |
|---|---|---|
| 1 | council-fable | claude-fable-5-1 |
| 2 | council-opus | claude-opus-5-5 |
| 3 | council-sonnet | claude-sonnet-5-5 |
| 4 | council-haiku | claude-haiku-5-5 |
| 5 | Codex CLI (Bash, not an Agent) | gpt-6-astra, if your Codex account offers it; otherwise its default model |

Files: `{agency-root}/agents/council/council-{fable,opus,sonnet,haiku}.md`. Tools: Read, Grep, Glob, WebFetch, WebSearch only. Seats give opinions; they never edit, write or spawn.

## Assembly (C2) — ONE wave
1. Write the brief once (question, context, constraints, what decision is needed). Identical text to all 5 seats. No seat sees another's answer.
2. In ONE message: 4 Agent calls (`subagent_type` = seat name, `run_in_background: true`, pass the brief as prompt; omit `name`; do NOT pass `model`, the pinned model in the agent file wins) + 1 Bash call for Codex.
3. No TeamCreate, no waves, no team config: seats are plain subagents.
4. A seat that fails or times out: proceed with the rest, name the missing seat in the synthesis. 3 of 5 is a quorum.

## Codex seat (C3)
```bash
mkdir -p /tmp/council && printf '%s\n' "$BRIEF" > /tmp/council/brief.md
codex exec -m gpt-6-astra -s read-only --skip-git-repo-check --ephemeral -C /tmp/council \
  -c 'model_reasoning_effort="medium"' -o /tmp/council/codex-out.txt - < /tmp/council/brief.md
```
- Requires `codex` on PATH. If `command -v codex` finds nothing, skip seat 5 and name it missing in the synthesis (4 of 5 is still a quorum).
- `-m gpt-6-astra` pins the model. If your Codex account does not offer it, drop `-m` and use the account default. The run header prints the model used; check it.
- `-s read-only` = sandboxed.
- Append the seat output format (C4) to the brief so Codex answers the same shape. Timeout 300s.

## Seat output format (C4) — every seat
`VERDICT / REASONS (top 3) / RISKS / CONFIDENCE 0-100 / DISSENT`, max 300 words.

## Synthesis (C5) — the CALLER synthesises. No extra synthesis seat.
1. Caller = the agent that ran the assembly (normally the main session, already Opus).
2. Output: one table (seat, verdict, confidence), points of agreement, points of disagreement with each side's best reason, recommended decision, residual risks.
3. Weigh by reasons, not by vote count and not by tier.
4. Caller is a cheap agent (sonnet/haiku): the council-opus answer is the tie-break; state this and report the dissenting seats verbatim.
5. Give the operator the synthesis plus the five raw verdicts (one line each).

## Cap (C6)
Council seats are opinion agents, not Execs, so they never take an Exec slot in the PD-tree cap.

## Gotchas
- Agent types are registered when a Claude Code session starts. Seats added or renamed mid-session are "not found" until a new session.
- Seat model IDs are full IDs (docs: frontmatter `model` accepts aliases and full IDs). A full ID is deterministic on old CLIs that map alias `haiku` to Haiku 4.5.

See also: [[agency-dispatch]]
