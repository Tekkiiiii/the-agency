---
name: project-expansion-scout
description: "Use to set up, configure or run the expansion scout: scans active projects for growth opportunities, gets BOD feasibility approval (default >80%), and adds approved phases to PROJECT.md. For stalled projects, cross-project synergies, or quarterly roadmapping; schedule is daily/weekly/biweekly cron."
---

# Project Expansion Scout

An autonomous strategic growth agent that runs on a configurable schedule, finds expansion opportunities across all active projects, gets BOD approval, and updates `PROJECT.md` accordingly.

---

## Setup

### Files

| File | Purpose |
|------|---------|
| `{agency-root}/agents-archive/generalist-2026-10-06/specialized/project-expansion-scout.md` | Archived role definition (read as the scout's role file) |
| `~/.claude/memory/expansion-scouts/` | Storage for drafts and voting state |
| `~/.claude/memory/expansion-scouts/voting-state.json` | Configuration + per-project voting state |

### Configure the Scout

Edit `voting-state.json` to set:

```json
{
  "scan_interval": "weekly",
  "approval_threshold": 0.80,
  "max_revision_cycles": 5,
  "projects": {}
}
```

| Field | Values | Default | Notes |
|-------|--------|---------|-------|
| `scan_interval` | `"daily"` / `"weekly"` / `"biweekly"` | `"weekly"` | Affects cron schedule |
| `approval_threshold` | `0.0` – `1.0` | `0.80` | Fraction of BOD votes needed |
| `max_revision_cycles` | `1` – `10` | `5` | Max revise iterations before archiving |

### Set Up Cron Schedule

**Note:** Cron jobs are session-only and auto-expire after 7 days. You must re-establish the cron at the start of each session. The `cron_job_id` is stored in `voting-state.json` for reference.

Use `/cron-list` and `/cron-delete` to manage. Default schedule:

- **Weekly**: Every Monday at 8:00 AM local — `0 8 * * 1`
- **Biweekly**: Every other Monday at 8:00 AM — `0 8 * * 1 */2`
- **Daily**: Every day at 8:00 AM — `0 8 * * *`

Cron fires, wakes the scout (general-purpose + /project-expansion-scout), which runs its full scan → BOD consult → vote → execute cycle.

---

## Invoking the Scout

### Manual Trigger (One-Shot)

Run the scout inline, or spawn `general-purpose` with `/project-expansion-scout` and let it run its full cycle:

```
Skills: /project-expansion-scout
Role: read {agency-root}/agents-archive/generalist-2026-10-06/specialized/project-expansion-scout.md first.

Run one complete expansion scan cycle:
1. Read medium-term.md for active projects
2. Scan each PROJECT.md + source code for expansion signals
3. Write drafts to ~/.claude/memory/expansion-scouts/{project}/current-draft.md
4. If drafts exist → assemble BOD, present drafts, collect votes
5. Tally votes against threshold
6. Execute approved expansions → update PROJECT.md + decisions.md
7. Archive or re-vote based on outcome
```

### Cron-Triggered (Recurring)

The cron job fires the same prompt. The agent checks `voting-state.json` on wake:
- If `projects` has an active draft → continue BOD consultation (resume mid-vote)
- If no active draft → run new scan

---

## What Gets Scanned

Per project:

1. **`PROJECT.md`** — `focus` list (stale items, scope underruns), `blockers`, open questions
2. **Source code** — `TODO`, `FIXME`, `XXX` comments; deprecated/unimplemented
3. **README / docs** — known limitations, planned-but-not-done features
4. **Cross-project** — compare PROJECT.md across all active projects for synergy opportunities

---

## Expansion Draft Lifecycle

```
[Draft Written] → [BOD Vote #1] → [Revised] → [BOD Vote #2] → ...
                          ↓              ↓
                    [APPROVED]      [Cycle 5 Hit]
                          ↓              ↓
                   [PROJECT.md     [Archived]
                    Updated]
```

| State | File | What Happens |
|-------|------|-------------|
| Draft exists | `current-draft.md` | Awaiting BOD vote |
| In revision | `current-draft.md` (updated) | Incorporating revision notes |
| Approved | `history/phase-N-date.md` | Appended to PROJECT.md |
| Rejected | `history/phase-N-date-rejected.md` | Logged with rejection reason |
| Skipped (no opportunity) | No file | Nothing to do this cycle |

---

## BOD Vote Tracking

Votes stored in `voting-state.json`:

```json
{
  "projects": {
    "{project}": {
      "phase": 1,
      "revision_cycle": 2,
      "draft_date": "2026-03-25",
      "votes": {
        "council-fable": "approve",
        "council-opus": "revise",
        "council-sonnet": "approve",
        "council-haiku": "approve",
        "codex": "approve",
        ...
      },
      "revision_notes": {
        "council-opus": "Split into two phases: MVP first, polish later"
      }
    }
  }
}
```

On session resume, the agent reads this state and continues from where it left off.

---

## Integration with Project Memory

Approved expansion phases are written to:
- **`{project}/PROJECT.md`** — appended under `## Expansion Phases`
- **`{project}/memory/decisions.md`** — decision log entry

---

## Disabling / Pausing

To pause the scout:
1. Delete the cron job (`/cron-delete`)
2. Or set `scan_interval` to `null` / remove it

To disable for a specific project: add it to `voting-state.json` under a `disabled_projects` array.

---

## Key Files Reference

| File | Read/Write | Purpose |
|------|-----------|---------|
| `~/.claude/memory/medium-term.md` | Read | Active project list |
| `~/.claude/memory/expansion-scouts/voting-state.json` | Read/Write | Config + voting state |
| `~/.claude/memory/expansion-scouts/{project}/current-draft.md` | Read/Write | Active draft |
| `~/.claude/memory/expansion-scouts/{project}/history/*.md` | Write | Archive |
| `{project}/PROJECT.md` | Read/Write | Project source + append expansion |
| `{project}/memory/decisions.md` | Append | Decision log |
