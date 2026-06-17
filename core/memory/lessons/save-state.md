# Save-State Lessons

## Pattern: save-state hang from oversized decisions.md (2026-06-15)

**What happened:** {project}-pd stalled repeatedly across multiple sessions (June 10–15).
Root cause: save-state spawned a general-purpose sonnet subagent that read the full
decisions.md (80KB, 679 lines) in FULL SCAN MODE. The subagent context overloaded and
died silently. No spawn_end was emitted → PD never got "done" → re-issued identical
save-state → re-hanged → session stalled (alive, zero progress).

**Evidence pattern:**
- spawns.jsonl shows repeated spawn_start for save-state with matching prompt_hash but no spawn_end
- Same hash re-spawned 3+ times within 45–60 minutes (15:55, 16:36, 16:40)
- Sessions/ logs from that day show "next-session.md was inaccurate" or repeated same decision loop

**Why:** General-purpose sonnet subagents die past ~200k ctx. An 80KB decisions.md +
heartbeat + mid-flight scan + all lessons = well over the effective context budget.
The subagent loads, starts reading, exhausts context, dies silently with no spawn_end.

**Fixes applied (2026-06-15):**
1. Memory hygiene: keep decisions.md under 15KB. Archive early, archive often.
   Target: ≤ 200 lines active, archive rest to decisions-archive.md.
2. save-state SKILL Step 0 tombstone: write next-session.md FIRST before any heavy reads.
   If subagent dies mid-ritual, the tombstone `Next: SAVE-STATE IN PROGRESS` prevents
   a stale next-session.md from triggering a confused resume loop.
3. save-state SKILL Step 1 memory size guard: if memory/ > 2MB, switch to capped read
   mode (head -n 100 of decisions.md only; skip decisions-archive.md).
4. save-state SKILL Step 6b new auto-prune: prune when decisions.md > 200 lines;
   append to archive (not create-once). Removed the "skip if archive exists" bug.
5. save-state SKILL Step 11b graphify exclusions: exclude brand/, qa/, graphify-out/
   from `graphify memory/` scan to prevent scanning binary/image content.

**Detection heuristic:**
```bash
grep spawn_start spawns.jsonl | grep save-state | sort | uniq -f5 | wc -l
```
If this shows the same hash 2+ times, you have repeated hung save-state spawns.

**Prevention:**
- Run `/recall [slug]` to check heartbeat.md before starting work — if decisions.md line count
  is visible and high (>150 lines), manually archive before the session, not just at the end.
- The session delta (pd-scratch.md ## Session Delta) is the primary weapon: with a valid delta,
  save-state skips the full decisions.md scan entirely. Write the session delta BEFORE triggering
  /save-state.

## Rule: next-session.md must be written FIRST in any save ritual (2026-06-15)

The handoff file is more important than any other artifact the save-state writes.
If the ritual hangs after writing next-session.md, the project can be resumed cleanly.
If it hangs before, the stale next-session.md from the prior session causes the PD to
re-enter whatever state it was in last time — often a blocked decision loop.

**Implementation:** save-state SKILL Step 0 tombstone was added for this reason.
The subagent's first write (before reading anything) is an "in progress" tombstone.
Step 6 overwrites it with the complete, accurate next-session.md — BEFORE the decisions
rewrite (Step 6b/6c), which is the heaviest and most hang-prone part of the ritual.

## Rule: next-session.md must be written BEFORE decisions rewrite, not after (2026-06-15)

The tombstone (Step 0) is the emergency fallback. But a tombstone does not carry phase,
next action, blockers, or mid-flight state — the resume loop still cannot safely proceed.
The FULL next-session.md must be written as early as possible: after we know what was
being done (heartbeat/session log, Steps 4-5) but BEFORE the heavy decisions.md operations.

**Why decisions is the danger zone:** decisions.md grows unboundedly if not pruned. At
80KB (679 lines), reading it in full scan mode plus appending/rewriting consumes
significant subagent context — often enough to push past the 200k crash threshold. If the
subagent dies during decisions rewrite, a tombstone-only next-session.md is insufficient
to resume cleanly. A complete next-session.md (written at Step 6) is.

**Save-state step ordering (correct):**
Step 0 → tombstone (immediate)
Steps 1-5 → read/scan/log/heartbeat (bounded, safe)
Step 6 → FULL next-session.md (uses data already in context — no new heavy reads)
Steps 6b-6c → decisions append + archive prune (heavy; next-session.md already safe)
Steps 7-8 → lessons, STATE.md (lower priority)
Steps 11b-13 → graphify, Pinecone, session graph (background, fire-and-forget)

## Rule: decisions.md auto-prune must not skip when archive already exists (2026-06-15)

The old Step 6b rule said "skip silently if decisions-archive.md already exists."
This meant the prune only ever ran once (when the archive was first created).
After that, decisions.md grew unbounded until the next manual pass.

**Fix:** Step 6b now prunes on every save-state when LINE_COUNT > 200, appending
the excess to the existing archive. The prune is idempotent and incremental.
