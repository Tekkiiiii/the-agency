---
name: pd-showcase
description: >
  Toggle PD showcase mode on/off for live demos. When ON, /pd-spawn and /pd-resume
  spawn PDs in the foreground with verbose narration so the audience sees every
  tool call, reasoning step, and decision in real-time. When OFF (default), PDs
  run silently in the background as usual. Invoke as /pd-showcase on, off, or
  status. State is a single marker file at {agency-root}/state/pd-showcase.flag —
  read by pd-spawn and pd-resume at spawn-time.
---

# /pd-showcase — Demo Visibility Toggle

A single marker file flips PD-spawning skills between two modes:

- **OFF (default)** — PDs spawn with `run_in_background: true`, silent until done.
- **ON (showcase)** — PDs spawn with `run_in_background: false` and a narration
  directive injected into their briefing. Every tool call and decision is
  visible in the main session. Trade-off: one PD at a time, main session blocks.

## SSOT

Flag file: `{agency-root}/state/pd-showcase.flag`
- Exists → showcase ON
- Absent → showcase OFF

The file's contents are advisory (timestamp + reason) but only its existence
matters. `pd-spawn` and `pd-resume` test for presence via `test -f`.

## Argument Parsing

Accept one of:
- `on` | `enable` | `start` — turn showcase on
- `off` | `disable` | `stop` — turn showcase off
- `status` | (no argument) — report current state
- `toggle` — flip whatever the current state is

## Step 1 — Determine Action

From the slash-command argument, pick one of: `on`, `off`, `status`, `toggle`.

If the argument is missing or unrecognized, default to `status` (read-only).

## Step 2 — Read Current State

Check whether `{agency-root}/state/pd-showcase.flag` exists. Record the result
as `currently_on = true | false`.

## Step 3 — Apply Action

**`on` (or `enable`, `start`):**
1. If `currently_on` → output "Showcase already ON — no change." and stop.
2. Otherwise, write `{agency-root}/state/pd-showcase.flag` with body:
   ```
   enabled_at: {ISO timestamp}
   note: PD showcase mode — foreground spawns + narration injected
   ```
3. Output the "ENABLED" confirmation (see Step 4).

**`off` (or `disable`, `stop`):**
1. If not `currently_on` → output "Showcase already OFF — no change." and stop.
2. Otherwise, delete `{agency-root}/state/pd-showcase.flag`.
3. Output the "DISABLED" confirmation (see Step 4).

**`toggle`:**
- If `currently_on` → run the `off` branch.
- Else → run the `on` branch.

**`status` (or no argument):**
- Read the flag file body if present; show timestamp and note.
- Output the "STATUS" report (see Step 4).

## Step 4 — Output Format

**ENABLED:**
```
PD SHOWCASE: ON
  Flag: {agency-root}/state/pd-showcase.flag
  Effect: Next /pd-spawn and /pd-resume run PDs in the foreground with verbose narration.
  Trade-off: One PD at a time. Main session blocks until each PD finishes.

To turn off: /pd-showcase off
```

**DISABLED:**
```
PD SHOWCASE: OFF
  Flag removed.
  Effect: Next /pd-spawn and /pd-resume return to silent background spawning.
```

**STATUS (when ON):**
```
PD SHOWCASE: ON (since {enabled_at})
  Note: {note from flag body}
  Flip with /pd-showcase off or /pd-showcase toggle.
```

**STATUS (when OFF):**
```
PD SHOWCASE: OFF (default)
  Flip with /pd-showcase on or /pd-showcase toggle.
```

## How pd-spawn and pd-resume Honor the Flag

Both skills include a "Step — Check Showcase Mode" gate before the Agent call:

1. Test for `{agency-root}/state/pd-showcase.flag`.
2. If present:
   - Spawn config: set `run_in_background: false`.
   - Briefing prompt: append the **Showcase Narration Directive** (below).
3. If absent: use default (background + lean briefing).

## Showcase Narration Directive (injected into PD briefing when flag is ON)

```
--- SHOWCASE MODE ---
A live audience is watching this session. Optimize for comprehension over speed:

1. Before each tool call, write ONE short sentence explaining what you're
   about to do and why.
2. After each tool result, write ONE short sentence summarizing what you
   learned before choosing the next step.
3. When deciding between approaches, narrate the trade-off out loud
   ("I could either X or Y — going with X because...").
4. When you finish a phase (research, planning, implementation, verification),
   call it out explicitly so the audience knows where you are.

Keep narration tight — one sentence each, no lectures. The audience reads
your tool calls; you just connect the dots.
--- END SHOWCASE MODE ---
```

## Notes

- The flag is session-agnostic — it persists until explicitly turned off. Always
  flip it back to `off` after a demo, or future PD spawns will keep blocking
  the main session.
- This toggle does NOT affect Curator, Delegator, codebase-search, or any
  non-PD agent. Only `/pd-spawn` and `/pd-resume` honor it.
- If you forget the flag is on and the next PD spawn blocks the main session,
  the running PD will still complete normally — interrupt it via the Agent
  tool's stop, or just let it finish, then flip the flag off.
