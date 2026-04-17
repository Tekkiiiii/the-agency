# The Agency v2 — QA Gates, ACK/NACK Protocol, and the 4-Tier Chain Are Live

*Posted in General*

---

We've shipped the biggest update to The Agency since launch. Here's what's new and why it matters.

## What's changed

### 4-Tier Autonomous Chain

The PD → Coord → Executor chain now has a fourth layer. Projects decompose across four levels:

```
PD  (L1→L3 — orchestration)
 └── Coord  (L3→L6 — parallel spawn)
      └── Mini-Coord  (L6→L7+ — for complex tasks)
           └── Task-Executor  (atomic unit)
```

Mini-Coords handle deep decomposition autonomously. Complex features split into L7/L8/L9 without bouncing back to PD for escalation. The chain scales with problem complexity.

### Mandatory QA Gates

Every task now passes a quality gate before any handoff is approved. Executors run `/qa-only` on completion. Coordinators review the health score before ACK fires. No work gets approved without evidence.

**The gate: health score ≥ 70 + zero CRITICAL issues.**

A `Coord-qa-Canary` runs pre-aggregate QA across all L3 outputs before PD reports to root. Full traceability, built into the protocol.

### Explicit ACK/NACK Protocol

Every agent-to-agent handoff is now explicit:

- **ACK**: "looks good, die quietly" → agent stops
- **NACK**: "fix: [list of issues]" → agent fixes → re-QA → re-reports

Rejected work loops back through the QA gate until it passes. You always know exactly why something was rejected and what needs to change.

## A 3-step example

```
1. Executor finishes a feature, runs /qa-only
   → Health score: 82. Issues: 1 MED (mobile layout), 0 CRITICAL.

2. Coord reviews the QA report
   → ACK (health ≥ 70, no CRITICALs)
   → Exec stops quietly.

3. Coord pre-aggregate: all Executors done
   → Coord-qa-Canary runs across combined output
   → Health score: 91. No CRITICALs.
   → Coord reports L3 complete to PD.
```

No guessing. No mystery handoffs. Evidence at every step.

## What's in the repo

- `core/agents/pd-coordinator.md` — PD template with ACK/NACK, Coord-qa-Canary, pre-aggregate QA
- `core/agents/coord.md` — Coord template with Executor QA review, pre-PD gate, Mini-Coord spawn
- `core/agents/mini-coord.md` — new: L6→L7+ decomposition for complex tasks
- `core/agents/task-executor.md` — Executor with mandatory QA gate, ACK/NACK wait
- `docs/ARCHITECTURE.md` — full protocol documentation
- `docs/DEVELOPER.md` — updated with tiered chain overview + onboarding

## Try it

```bash
git clone https://github.com/Tekkiiiii/the-agency.git
cd the-agency
npx agency init
agency new my-project "Build something"
```

Then in Claude Code: `/recall my-project` — the PD loads and picks up from wherever you left off.

If you hit issues or want to contribute: open an issue, PR, or discussion. This is v2 — there's a lot more coming.

**Star the repo** | **Try it** | **Contribute**
