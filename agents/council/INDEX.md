# Council — independent opinion seats

The council gives a caller (a PD, a Coord or the parent AI) several independent, read-only opinions on one decision brief. It replaces the retired department-lead council (department layer sunset 2026-10-08). The caller synthesises the answers; the Opus seat is the tie-break.

## Members

| Agent | Tier | Role |
|---|---|---|
| council-fable | Fable | One independent opinion on a brief, read-only |
| council-opus | Opus | One independent opinion on a brief, read-only; also the tie-break seat |
| council-sonnet | Sonnet | One independent opinion on a brief, read-only |
| council-haiku | Haiku | One independent opinion on a brief, read-only |

Optional fifth seat: Codex, run through the `codex` CLI in read-only mode (no agent file; the caller runs it alongside the four seats when Codex is installed).

Protocol (one wave, fixed output format, synthesis rules): `{agency-root}/core/memory/agency-council.md`. Seats are not Execs: they never edit, write, spawn or run commands.

## Parent Directory

[<- Agency Directory](../INDEX.md)
