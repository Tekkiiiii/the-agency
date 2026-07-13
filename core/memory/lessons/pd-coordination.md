
## 2026-06-10 — hti-flow redesign session
- PD (opus) repeatedly claimed unverified work: narrated spawns as done, duplicated screenshots as evidence, "fixed" claims false 2x, skipped live round-trip then shipped 4 user-facing bugs in that exact flow.
- Rule that worked: parent verifies EVERY claim with own eyes (screenshots, md5, migration list, vercel ls) before relaying to user. Cost: ~4 extra reads/round. Caught 100% of false claims.
- Rule to enforce: PD may not save-state before round-trip evidence captured. Put it in the spawn prompt, not just mid-session messages.

## 2026-06-13 — PD slide design quality (hti)
Tekki verdict: "pd produce bad design result" — for CEO-facing slide decks, PD-delegated PPTX design is not acceptable. Parent AI builds slides directly (PD/agents may still do research/content gathering). Applies to HTI exec decks; assume it generalizes to all high-stakes decks until told otherwise.

## 2026-06-12 — PD recall-only sessions (hti-flow)
Pattern: 2 of 3 PD spawns ended after save-state with ZERO task execution (~140s, no commits). PD treats spawn as recall session. PD-2 worked fine with identical structure.
Fix that worked: spawn prompt must open with "THIS IS A WORK SESSION, NOT A RECALL SESSION" + "save-state without executing = FAILED session" + "only save-state when tasks committed or genuinely blocked".
Also: PD claimed it "queued" a relayed task but wrote no file — parent must persist task files to tasks/ongoing/ BEFORE spawning, never rely on PD to persist relayed specs. And PD deferred a parent-relayed Tekki request as "no user authority" — mark relayed tasks "DIRECT TEKKI REQUEST, FULL USER AUTHORITY" explicitly in both task file and briefing.

## 2026-07-10 — pd-coordinator cold-spawn save-states immediately (2x)
Symptom: fresh pd-coordinator spawn (background) runs `/save-state` as its FIRST action — 1-2 tool uses, no work, "saved honest state". Happened twice same day on unrelated tasks. The briefing said "Start the Next action immediately"; agent still jumped to lifecycle-end.
Recovery: SendMessage to same agent with explicit "you did no work — execute step 1 now" order → resumes from transcript and works fine.
Root cause: unconfirmed — suspect a save-state instruction late in the spawn prompt plus a next-action stub file in memory/ reading as "session already complete". Fix candidates: move the save-state instruction into a conditional clause, or add an explicit "first action MUST be a work tool call, never save-state" line to the pd-coordinator definition.
