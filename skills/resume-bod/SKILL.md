---
name: resume-bod
description: "Use on /resume-bod, /bod-resume, \"resume the board\", \"continue council workflow\", \"pick up where BOD left off\". Restores BOD/Agency Council context from memory and reassembles the 5-seat council (Fable, Opus, Sonnet, Haiku + Codex on gpt-6-astra) in one wave and synthesises the answers."
---

# Resume BOD — Continue Council Workflow in New Session

Use this skill to restore context and continue The Agency council workflow without re-deriving state manually.

---

## When Invoked

Trigger on:
- `/resume-bod`
- `/bod-resume`
- "resume the board"
- "continue council workflow"
- "pick up where BOD left off"

---

## Step 1: Load Session Context

1. Read `~/.claude/memory/medium-term.md`
2. Identify the active project and confirm whether `agency-agents` is the target
3. Read the target project's `PROJECT.md`
4. Read latest session log at `{project}/memory/sessions/YYYY-MM-DD.md` (most recent)

If project is ambiguous, ask the user to choose from active projects before proceeding.

---

## Step 2: Summarize Prior BOD State

Summarize in 5 bullets max:
- Last completed phase / milestone
- Current status and blockers
- Last known council/team state
- Key constraints (Tier rules, approvals)
- Next recommended action

Do not re-explore the codebase unless PROJECT.md is stale or missing critical state.

---

## Step 3: Offer Council Assembly

After context summary, offer explicit next actions:

- **Assemble full council now** (`BOD`, `assemble`, `the board`, `the council`)
- **Assemble a sub-council** (pick 3-4 of the 5 seats; quorum rule still 3)
- **Skip assembly** and continue solo planning

If user confirms assembly, proceed immediately.

---

## Step 4: Assemble the 5-Seat Council (one wave)

Protocol source of truth: `{agency-root}/core/memory/agency-council.md`. Read it first; do not restate it here.

1. Write the brief once (Step 5 template). Same text to every seat.
2. In ONE message: four Agent calls (`council-fable`, `council-opus`, `council-sonnet`, `council-haiku`; background; no `name`, no `model`) plus one Bash call for Codex (`codex exec -m gpt-6-astra -s read-only ...`, exact command in agency-council.md C3). Codex runs via the `codex` binary on PATH; if `codex` is absent, skip that seat and name it as missing.
3. No TeamCreate, no waves. Seats are read-only opinion agents, pinned by their agent files, and do not count toward the 5-Exec cap.
4. Proceed once 3 of 5 have answered; name any missing seat.

---

## Step 5: Kickoff Brief Template

Use this message format:

```
TYPE: council-brief
PURPOSE: project-resume
PROJECT: [project name]
SCOPE: [brief]
TIMELINE: [urgency]
---
[What was completed previously]
[What remains]
[Decision needed now]
ANSWER FORMAT: VERDICT / REASONS (top 3) / RISKS / CONFIDENCE 0-100 / DISSENT, max 300 words. Answer alone.
```

---

## Step 6: Resume Execution Loop

After the seats reply:
1. The CALLER synthesises (no extra seat): table of seat/verdict/confidence, agreement, disagreement, recommended decision, risks. Cheap-agent caller: council-opus is the tie-break.
2. Weigh reasons, not vote count
3. Hand the decision to the project PD for work packages
4. Report concise checkpoint summary to user with the five raw verdicts

---

## Key Rules

- Read memory first, spawn second
- Treat PROJECT.md as source of truth unless user says otherwise
- Use the single-wave 5-seat assembly every time
- Keep kickoff summaries concise and decision-focused
- Seats are stateless one-shot subagents: re-run the whole assembly, do not reuse a team
