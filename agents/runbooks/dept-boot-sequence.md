---
name: Dept Boot Sequence
description: Standard startup sequence for all Department Heads. Two-mode: thin discover on spawn, lazy routing on dispatch. Mirrors pd-boot-sequence.md for department operations.
type: runbook
owner: agency-council
lastUpdated: 2026-05-13
---

# Dept Boot Sequence

## Philosophy

- **On spawn**: read as little as possible — dept-state.md is your single briefing doc
- **On dispatch**: load pipeline details only when you need them, not before
- **Check incoming first**: PDs may have left inter-spawn tasks since last session

---

## Mode 1: Spawn (do this every time)

**Target context cost: ~400 tokens max**

**Step 1:** Read dept-state from spawn prompt. `/dept-resume` passes dept-state.md content inline — no file read needed. If spawned manually without a briefing, read:
```
{agency-root}/agents/{dept}/state/dept-state.md
```

**Step 2:** If `active-coords` field is non-empty, read:
```
{agency-root}/agents/{dept}/state/active-coords.md
```
This gives you the current DC names, their D3 tracks, and last-known states. Skip if field is empty.

**Step 3:** Check for incoming inter-spawn tasks from PDs:
```
{agency-root}/agents/{dept}/state/incoming/
```
If files exist, read each one. Prioritize by the `Priority` field. High-priority items become first-session actions before any other department work.

**Step 4:** Check the `open-issues` field in dept-state. Open issues are your first priority after handling any critical incoming tasks.

**Step 5:** Scan `protocols/INDEX.md` for active cross-dept protocols. Know which departments you have bilateral agreements with — you may receive or need to send work through these protocols during the session. Don't read the full protocol files yet; just note which ones exist and who the partners are.

**Step 6:** Proceed with your role.

---

## Mode 2: Route (do this when dispatching work)

**Target context cost: load only what you need**

**Step 1:** Check dept-state for active pipelines that match the work type:
```
active-pipelines: [pipeline-name, ...]
```

**Step 2:** If a matching pipeline exists, read:
```
{agency-root}/agents/{dept}/pipelines/{pipeline-name}.md
```
Only load the pipeline you need. Not all pipelines.

**Step 3:** Determine dispatch tier:

```
Is this a D1 initiative that spans multiple D2 areas?
  YES → Decompose to D3 tracks → spawn Dept-Coords for each D3 (complex)
  NO  → Is this a single D3 track or smaller?
          Single D3 or smaller → dispatch directly to one Dept Member (simple)
          Unclear → decompose first, then decide
```

**Step 4:** Dispatch via Agent tool:
- Complex (multiple D3 tracks) → spawn Dept-Coords per `dept-coord-protocol.md`
- Simple (single D6 atomic) → spawn the relevant Dept Member directly

---

## dept-state.md Format

Path: `{agency-root}/agents/{dept}/state/dept-state.md`

This is the department's equivalent of `next-session.md`. Max 20 lines. Key:value format.

```
dept: {dept-name}
head: {head-agent-name}
last-updated: {YYYY-MM-DD HH:MM}
active-coords: [DC-cc-pipeline-Conductor, DC-cc-review-Lens] | none
active-pipelines: [content-request, blog-review] | none
open-issues: [issue-slug-1, issue-slug-2] | none
blocked-on: [blocker description or "none"]
current-priority: {top D1 initiative or "none"}
incoming-count: {n} | 0
notes: {freeform, max 2 lines}
```

**Rules:**
- Keep it under 20 lines. If you need more, move detail to a linked doc.
- `active-coords` lists DC names currently running — read `active-coords.md` if non-empty.
- `incoming-count` is a hint only — always check the directory.
- Update `last-updated` whenever you write dept-state.

---

## active-coords.md Format

Path: `{agency-root}/agents/{dept}/state/active-coords.md`

Read only when `active-coords` field is non-empty.

```markdown
# Active Dept-Coords — {dept} — {timestamp}

| DC Name | D3 Track | State | Started | Last Update |
|---|---|---|---|---|
| DC-cc-pipeline-Conductor | content-pipeline-v2 | IN_PROGRESS | 2026-05-13 09:00 | 09:45 |
| DC-cc-review-Lens | review-cadence | QA_GATE | 2026-05-13 08:30 | 10:00 |
```

Dept Head updates this table on every DC STATUS_UPDATE received.

---

## Dispatch Priority (reference — don't load on spawn)

```
1. Is there a critical incoming task from a PD in incoming/?
   YES → handle first (or queue if lower priority than open-issues)
   NO  → step 2

2. Are there open-issues in dept-state?
   YES → address before new initiative work
   NO  → step 3

3. Is there an active D1 initiative in current-priority?
   YES → continue or advance it
   NO  → step 4

4. Is there a new initiative to begin?
   YES → decompose D1 → D2 → D3 → dispatch Dept-Coords or Members
   NO  → maintenance mode (protocol review, member check-in)
```

---

## Dept Member Routing (reference — don't load on spawn)

Load only when routing a specific task.

| Task Type | Member to Spawn |
|---|---|
| Protocol writing / revision | Domain specialist in owning dept |
| Pipeline step execution | Domain specialist for that pipeline type |
| Member development / onboarding | Dept Head directly (no DC needed) |
| Quality review of dept output | QA specialist or senior dept member |
| Cross-dept coordination | Dept Head directly — never delegated to DC |
| Incoming PD inter-spawn tasks | Dept Head assesses, then dispatches if needed |

---

## Dept-State Write Convention

Write dept-state after:
- Spawning or receiving completion from a DC
- Processing an incoming task from a PD
- Closing an open issue
- End of session (via `/dept-save-state`)

Never let dept-state go stale across sessions. The `/dept-save-state` skill handles the end-of-session write.

---

## How to Apply to a New Dept Head

1. Create `{agency-root}/agents/{dept}/state/dept-state.md` with the format above.
2. Create `{agency-root}/agents/{dept}/state/incoming/` directory (empty, for PD inter-spawn tasks).
3. Paste Mode 1 (Spawn) + Mode 2 (Route) reference into the Dept Head agent file.
4. Paste Dispatch Priority as a reference block (no file reads on spawn).

Total added to Dept Head agent file: ~50 lines. Single file read on spawn (dept-state.md). Everything else is lazy-loaded.

---

## References

- Dept-Coord lifecycle: `{agency-root}/agents/runbooks/dept-coord-protocol.md`
- Dept lead protocol: `{agency-root}/agents/runbooks/department-lead-protocol.md`
- PD boot sequence (mirror): `{agency-root}/agents/runbooks/pd-boot-sequence.md`
- Protocol registry: `{agency-root}/agents/runbooks/protocol-registry.md`
