# Orchestration Tiers

The Agency supports two orchestration tiers that control how much protocol overhead
runs at each agent handoff. Choose based on your Claude plan.

---

## lite (default)

Optimized for **Claude Pro plan** users. Lower token budget per session.

**What runs:**
- Full L1→L2→L3 decomposition by the PD
- Coord spawn + ACK/NACK lifecycle
- Single-phase QA (Coord-qa-Canary per session)
- DIRECTION framing (team-lead mindset in all agents)

**What is skipped:**
- Approach Gate — Execs do not send an APPROACH plan before file edits
- Mandatory 50% Check-In — no CHECKPOINT mid-task
- Phase B Integration Testing — no IntegrationTester agent spawn
- pd-structure.md structural contracts — optional, not enforced

**Best for:** solo projects, Pro plan users, single-domain tasks, quick iterations.

**PD file:** `core/agents/pd-coordinator-lite.md`

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

**PD file:** `core/agents/pd-coordinator.md`

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
flag only controls which PD coordinator file gets used at spawn time.

---

## Token Budget Comparison

| Feature | lite | standard |
|---------|------|----------|
| PD→Coord protocol rounds per task | 1 (spawn + ACK) | 1-3 (spawn + optional NACK) |
| Exec→Coord protocol rounds | 1 (result) | 2-3 (APPROACH + result + optional CHECKPOINT) |
| Integration testing agent | no | yes (1 Sonnet spawn post-L3) |
| Estimated tokens per medium project | ~40-80k | ~80-160k |

Estimates vary by project size and number of L3 tasks.
