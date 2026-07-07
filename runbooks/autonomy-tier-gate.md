# Autonomy Tier Gate — Full Protocol (PD/Coord Level)

Moved from `agents/project-management/pd-coordinator.md` and
`agents/project-management/coord.md` (2026-07-07 token-efficiency pass). The
fast-path (auto_ack short list + mechanical verifier) stays in-def in both
files — read this only for ambiguous/known-risky actions not on the fast-path
list.

## Config source of truth

`core/memory/autonomy-tiers.json` — read by PD and Coord before any action
that writes, deploys, sends, or mutates. Safe-by-default: if the file is
absent or an action type isn't listed, treat it as `operator_gated`.

Three tiers:
- `auto_ack` — mechanical verifier only, no human, no critique loop.
- `agent_gated` — critique-loop gate (LLM judges, optional screenshots).
- `operator_gated` — human ACK required (Tekki-gated in the live system).

## Lookup procedure

1. Identify the action's `action_type` key (e.g. `settings_json_edit`,
   `git_push_client_facing`, `public_deploy`, `schema_migration`,
   `external_send`, `dns_change`, `cost_bearing_action`).
2. Look it up in `action_tiers` in `core/memory/autonomy-tiers.json`.
3. Not found → default `operator_gated` (safe-by-default fallback).
4. Run the tier's gate: `auto_ack` → its named verifier; `agent_gated` →
   critique agents must pass; `operator_gated` → wait for explicit human ACK.
5. If a gate's own check fails, fall back to the next-stricter tier
   (`safe_fallback` field on each tier definition) rather than proceeding.

## Standing adversarial-guard list (always operator_gated)

These action types are always `operator_gated` regardless of context —
never promotable, never fast-pathed:
`settings_json_edit`, `git_push_client_facing`, `public_deploy`,
`schema_migration`, `external_send`, `dns_change`, `cost_bearing_action`.

## No-self-promotion rule

Per `_meta.how_to_promote` in the config: promoting a tier from `agent_gated`
to `auto_ack` requires (a) 50+ real logged instances tagged with that
`action_type`, (b) pass_k ≥ 0.95 over those instances, (c) explicit operator
ACK. **No agent may self-promote a tier** — an agent proposing its own
promotion and acting on it before ACK is a violation, report it, don't act on it.

## Mandatory `tier_checked` metric emission (F16)

Every time this gate runs (fast-path or full lookup), emit `tier_checked`
non-blocking via `emit-metric.sh` (see `runbooks/metrics-emit-contracts.md`
Event: tier_checked). Never skip the emission to save time — it's the only
audit trail that proves the gate ran before an action executed.
