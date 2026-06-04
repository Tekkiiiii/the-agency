# Orchestration Tiers

The Agency supports two orchestration tiers that control how much protocol overhead
runs at each agent handoff. Choose based on your Claude plan.

---

## lite (default)

Optimized for **Claude Pro plan** users. ~30-40% token footprint of standard.

**Architecture:** PD → Coord → Task-Executor (3 layers)

**Coord role in LITE:** Pure task-giver. Coord decomposes L3 → smallest independent
sub-tasks, dispatches Task-Executors, reviews ACK/NACK reports. No hands-on work.
No Director-era Approach Gate or 50% Check-In patterns.

**What runs:**
- Full L1→L2→L3 decomposition by the PD
- L3→L6 decomposition by Coord (task-giver only)
- Coord spawn + ACK/NACK lifecycle
- Phase A QA gate (Coord-qa-Canary per session)

**What is skipped:**
- Approach Gate — Execs do not send an APPROACH plan before file edits
- Mandatory 50% Check-In — no CHECKPOINT mid-task
- Phase B Integration Testing — no IntegrationTester agent spawn
- pd-structure.md structural contracts — optional, not enforced

**Best for:** solo projects, Pro plan users, single-domain tasks, quick iterations.

**Agent trio:**
- `core/agents/pd-coordinator-lite.md` — PD (source: commit 9607f2d)
- `core/agents/coord-lite.md` — Coord task-giver (source: commit 9607f2d)
- `core/agents/task-executor-lite.md` — Exec (source: commit 9607f2d)

---

## standard (recommended for Max 5x / Max 20x)

Full quality gates for complex multi-domain projects.

**What runs (everything in lite, plus):**
- **Approach Gate** — before any file edits, Executor sends a plan to Coord for approval.
  Coord approves (ACK_APPROACH) or redirects (REVISE_APPROACH, max 2 rounds).
- **Mandatory 50% Check-In** — at ~50% effort, Executor sends a CHECKPOINT.
  Coord replies ACK_CONTINUE or COURSE_CORRECT.
- **Phase B Integration Testing** — after all per-L3 Coord QA gates pass, the PD spawns
  an IntegrationTester agent that verifies cross-L3 contracts and dependencies.
  Produces INTEGRATION_PASS / WARN / FAIL verdict.
- **pd-structure.md** — structural contract file maintained by the PD. Defines no-touch
  zones, integration contracts, and active L3 boundaries.

**Best for:** complex multi-domain builds, Max 5x / Max 20x users, team deployments.

**Agent trio:**
- `core/agents/pd-coordinator.md` — PD
- `core/agents/coord.md` — Coord (Director-era: team-lead mindset, Approach Gate, Check-In)
- `core/agents/task-executor.md` — Exec

---

## full

Alias for `standard`. Identical behavior.

---

## Selecting a Tier

**At install time:**
```bash
agency init                   # defaults to lite
agency init --tier=standard   # opt in to full quality gates
```

**After install:**
```bash
agency tier set lite          # switch to Pro-plan mode
agency tier set standard      # switch to full quality gates
agency tier get               # show current tier
```

**In `~/.agency/config.json`:**
```json
{ "tier": "lite" }
```

---

## Migration

**Existing users** (installed before tiers were added): your behavior is unchanged.
`~/.agency/config.json` will be created on next `agency init` with `"tier": "lite"`.
If you were using the full quality-gate architecture, run `agency tier set standard`
to explicitly lock that in.

**New installs** default to `lite` (safest assumption for Pro plan).

**Upgrade path:** `agency tier set standard` — no file migration needed. The tier
flag controls which full agent trio (PD + Coord + Exec) gets used at spawn time.
Use `require('./cli/commands/tier').agentTrio(tier)` to resolve the trio programmatically.

---

## Token Budget Comparison

| Feature | lite | standard |
|---------|------|----------|
| Coord role | task-giver (pure dispatch) | team-lead (hands-on oversight) |
| PD→Coord protocol rounds per task | 1 (spawn + ACK) | 1-3 (spawn + optional NACK) |
| Exec→Coord protocol rounds | 1 (result + QA) | 2-3 (APPROACH + result + optional CHECKPOINT) |
| Phase A QA gate (Coord-qa-Canary) | yes | yes |
| Phase B Integration Testing agent | no | yes (1 Sonnet spawn post-L3) |
| Approach Gate | no | yes |
| 50% Check-In | no | yes |
| Estimated tokens per medium project | ~40-80k | ~80-160k |

Estimates vary by project size and number of L3 tasks.
