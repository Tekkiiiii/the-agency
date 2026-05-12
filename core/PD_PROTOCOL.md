# PD Standard Protocol

> The authoritative PD protocol is embedded in the PD Coordinator agent definition at `core/agents/pd-coordinator.md`. This file provides a summary for quick reference.

---

## The Four Rules

### Rule 1 — Decompose First

Break every task into the smallest possible independent sub-tasks before starting any work. If a sub-task can run without waiting for another's output, split them.

### Rule 2 — Parallel by Default

Deploy one subagent per sub-task in a single message using the `Agent` tool. All subagents launch simultaneously — never sequentially.

### Rule 3 — Gate Before Ship

QA gate is mandatory before marking any task done. Health score >= 70 with no CRITICAL issues required to pass. Failed gates get NACK with fix list, not ignored.

### Rule 4 — Escalate Explicitly

Blocked tasks get explicit ESCALATE messages with reason, scope, and needed action. Never silently stop or retry without reporting.

---

## Tiered Architecture

```
PD (L1-L3)  →  Coord (L3-L6)  →  Mini-Coord (L6+)  →  Exec (atomic)
```

Each agent stops at its termination level. PD decomposes to L3, Coord to L6, Mini-Coord to atomic units, Exec implements.

## Full Protocol

See `core/agents/pd-coordinator.md` for the complete lifecycle, spawn templates, ACK/NACK protocol, QA gates, and status reporting format.
