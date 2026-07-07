# pd-structure — {project}
Last updated: YYYY-MM-DD by PD-{slug}

## Architecture Decisions
- {key decision}: {one-line rationale}

## No-Touch Zones
- {file or module}: {reason it must not be modified without PD approval}

## Integration Contracts
- {interface or API surface}: {what Coords must preserve}

## Active L3 Boundaries
- Coord-{name}: owns {scope — files, modules, directories}

## Known Cross-L3 Dependencies
- {L3-A} → {L3-B}: {what L3-A produces that L3-B consumes}

---

## PD Responsibilities

The PD owns `pd-structure.md` for the life of the project:
- **Create on first spawn.** If the file doesn't exist when a PD is spawned
  for a project, create it from this template before decomposing L1 → L2 → L3.
- **Read on every spawn.** Load it as part of the BOOT-READ batch (see
  pd-coordinator.md's Lifecycle step 1.5) — never skip it, it's how a fresh
  PD instance (post-respawn) recovers architecture decisions and no-touch
  zones without re-deriving them from scratch.
- **Update after any architecture-affecting decision.** New no-touch zone,
  new integration contract, new L3 boundary, new cross-L3 dependency — append
  immediately, don't batch it for end-of-session.
- **Pass to every Coord spawn prompt.** Coords need No-Touch Zones and
  Integration Contracts to avoid silently breaking another Coord's L3 — never
  spawn a Coord without this file's current content inlined or referenced.

## Coord Read/Update Contract

- Coords **read** pd-structure.md at spawn time (passed inline by the PD) —
  they do not re-fetch it themselves.
- Coords **do not edit** pd-structure.md directly — it's PD-owned. If a Coord's
  work implies a new no-touch zone, integration contract, or cross-L3
  dependency, it reports the finding back to the PD (via STATUS_UPDATE or the
  final digest), and the PD is the one who appends it.
- If a Coord's read copy conflicts with what it observes in the actual
  codebase (stale no-touch zone, contract no longer honored), it flags the
  conflict to the PD rather than silently overriding either the file or the
  code.
