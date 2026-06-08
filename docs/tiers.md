# Orchestration Tiers

The Agency ships two tiers. The tier controls how much protocol overhead runs at each agent handoff. Choose based on your Claude plan.

| | lite | standard |
|--|--|--|
| **Claude plan** | Pro | Max 5x / Max 20x |
| **Best for** | Solo projects, quick iterations | Complex multi-domain builds |
| **Token use** | ~30-40% of standard | Full |
| **Agent trio** | pd-coordinator-lite + coord-lite + task-executor-lite | pd-coordinator + coord + task-executor |

---

## lite — default for Claude Pro

**~30-40% of standard token cost.**

Coord acts as a team-lead task-giver: decomposes work to the smallest independent sub-tasks, dispatches Executors, reviews ACK/NACK reports with judgment. No hands-on oversight gates.

**What runs:**
- Full PD decomposition (L1 → L2 → L3)
- Coord task decomposition (L3 → L6) and dispatch
- ACK/NACK lifecycle on every Exec → Coord handoff
- Phase A QA gate (Coord-qa-Canary) per session

**What is skipped to save tokens:**
- Approach Gate (Exec pre-approval before file edits)
- Mandatory 50% Check-In
- Phase B Integration Testing (post-L3 IntegrationTester agent)
- pd-structure.md structural contracts

**Agent trio:**
- `core/agents/pd-coordinator-lite.md`
- `core/agents/coord-lite.md`
- `core/agents/task-executor-lite.md`

---

## standard — recommended for Max 5x / Max 20x

Full quality gates. Coord acts as a team lead with hands-on oversight at every step.

**Everything in lite, plus:**

- **Approach Gate** — Executor sends a plan to Coord before any file edits. Coord approves (`ACK_APPROACH`) or redirects (`REVISE_APPROACH`, max 2 rounds). Catches wrong approaches before they waste tokens.
- **Mandatory 50% Check-In** — at ~50% effort, Executor sends a CHECKPOINT. Coord replies `ACK_CONTINUE` or `COURSE_CORRECT`. Catches drift early.
- **Phase B Integration Testing** — after all L3 Coord QA gates pass, PD spawns an IntegrationTester that verifies cross-L3 contracts. Produces `INTEGRATION_PASS` / `WARN` / `FAIL`.
- **pd-structure.md** — PD-maintained structural contract file. Defines no-touch zones, integration contracts, and active L3 boundaries.

**Agent trio:**
- `core/agents/pd-coordinator.md`
- `core/agents/coord.md`
- `core/agents/task-executor.md`

---

## full

Alias for `standard`. Identical behavior.

---

## Selecting a Tier

**At install time:**
```bash
agency init                   # defaults to lite (Claude Pro)
agency init --tier=standard   # full quality gates (Max 5x / Max 20x)
```

**Switch after install:**
```bash
agency tier set lite          # switch to lite
agency tier set standard      # switch to standard
agency tier get               # show current tier
```

**In `~/.agency/config.json`:**
```json
{ "tier": "lite" }
```

Not sure which to use? Start with `lite`. If you're on Max and hitting issues with complex multi-domain builds, switch to `standard`.

---

## Migration

**Existing users** (installed before tiers shipped): your behavior is unchanged. `~/.agency/config.json` will be created on next `agency init` with `"tier": "lite"`. If you were running the full quality-gate architecture, run `agency tier set standard` to lock that in explicitly.

**New installs** default to `lite` (safe for Pro plan; Max users can upgrade immediately).

---

## Token Budget Detail

| Feature | lite | standard |
|---------|------|----------|
| Coord role | team-lead task-giver (no hands-on gates) | team-lead (hands-on oversight, Approach+Checkpoint gates) |
| PD→Coord protocol rounds per task | 1 (spawn + ACK) | 1-3 (spawn + optional NACK) |
| Exec→Coord protocol rounds | 1 (result + QA) | 2-3 (APPROACH + result + optional CHECKPOINT) |
| Phase A QA gate (Coord-qa-Canary) | yes | yes |
| Phase B Integration Testing | no | yes (1 Sonnet spawn post-L3) |
| Approach Gate | no | yes |
| 50% Check-In | no | yes |
| Estimated tokens per medium project | ~40-80k | ~80-160k |

Estimates vary by project size and number of L3 tasks.
