---
name: dept-resume
description: >
  Resume department head sessions with minimal context overhead. Reads dept-state.md
  directly (no subagents), spawns dept heads with lean briefings. Invoke as
  /dept-resume all or /dept-resume [dept-slug]. Optimized for context window
  efficiency: no recall subagents, no temp files.
---

# /dept-resume

Fully autonomous. Reads dept state directly, spawns dept heads with pre-digested briefings.

**Context budget principle:** dept-save-state does the synthesis at write-time so
dept-resume pays near-zero at read-time. Every token in the dept head spawn prompt
must earn its place. Target: ~400 tokens per spawn.

## Department Registry

| Slug | Path | Lead Agent | Agent Definition |
|------|------|-----------|-----------------|
| career | {agency-root}/agents/career | Pipeline Strategist (acting) | career-lead.md |
| content-creation | {agency-root}/agents/content-creation | Chief Content Officer | content-creation-lead.md |
| design | {agency-root}/agents/design | Brand Guardian | design-brand-guardian.md |
| engineering | {agency-root}/agents/engineering | Backend Architect | engineering-lead.md |
| game-development | {agency-root}/agents/game-development | Game Designer | game-development-lead.md |
| marketing | {agency-root}/agents/marketing | Growth Hacker | marketing-lead.md |
| operations | {agency-root}/agents/operations | Infrastructure Maintainer | operations-lead.md |
| paid-media | {agency-root}/agents/paid-media | PPC Campaign Strategist | paid-media-lead.md |
| product | {agency-root}/agents/product | Sprint Prioritizer | product-lead.md |
| project-management | {agency-root}/agents/project-management | Studio Producer | project-management-lead.md |
| sales | {agency-root}/agents/sales | Sales Coach | sales-lead.md |
| spatial-computing | {agency-root}/agents/spatial-computing | XR Interface Architect | spatial-computing-lead.md |
| specialized | {agency-root}/agents/specialized | Agents Orchestrator | specialized-lead.md |
| testing | {agency-root}/agents/testing | Reality Checker | testing-lead.md |

Replace `{agency-root}` with `~/.claude` after installation.

## Argument Resolution

| Argument | Action |
|---|---|
| `all` | Resume all departments in parallel |
| `[dept-slug]` | Resume one department |
| comma-separated | Resume listed departments |
| no arg | Fail: "Pass a dept slug, comma-separated slugs, or 'all'" |

## Step 1 — Read Briefings Directly

For each target department, read `{dept-path}/state/dept-state.md` using the
Read tool. **Do NOT spawn subagents.** Issue all reads in parallel.

dept-state.md is self-contained — dept-save-state writes active pipelines, protocols,
coords, issues, and next-focus into it. No other files need to be read at startup.

If dept-state.md doesn't exist or is empty, use fallback:
```
dept: {slug}
lead: {lead from registry}
updated: unknown
next-focus: initialize department state and pipelines
blockers: none
```

## Step 2 — Spawn Dept Heads

Spawn one dept head agent per target. **All in a single message** (parallel).

**Spawn config:**
- `subagent_type`: the dept lead agent name (from registry)
- `model`: opus
- `run_in_background`: true (dept heads work autonomously)

**Spawn prompt — LEAN FORMAT (do not add to this):**

```
You are the {lead-name}, resuming the {department} department.
Department dir: {dept-path}
Dept-Coord protocol: {agency-root}/agents/runbooks/dept-coord-protocol.md
Boot sequence: {agency-root}/agents/runbooks/dept-boot-sequence.md

--- STATE ---
{verbatim content of dept-state.md}
---

Follow the boot sequence. Check state/incoming/ for inter-spawn tasks from PDs.
Start the next-focus action immediately. When done or blocked, /dept-save-state {slug} and stop.
```

**What is NOT in the spawn prompt (already in the dept lead agent definition):**
- Department member roster
- Approval tiers
- Skills list
- Communication protocol
- Curator pattern

## Step 3 — Output Summary

After all spawns:

```
DEPT-RESUME: Spawned {n} department head(s)
{for each: {slug} — {lead-name} — next-focus: {value}}
All running in background. Use /dept-status [slug] to check progress.
```
