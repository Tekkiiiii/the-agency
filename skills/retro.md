---
name: retro
description: >
  Structured retrospective analysis for engineering teams. Triggers at end of
  sprint or after a milestone. Analyzes git history and session logs to identify:
  patterns (recurring themes across time), wins (what worked well), losses
  (what didn't), velocity data (commits per day, PR cycle time), and a
  prioritized action items list for next sprint. Two modes: sprint retro
  (standard) and global cross-project mode (patterns across multiple repos).
  Trigger when: sprint ends, milestone ships, or "run a retro". Also for:
  onboarding a new team member (understanding what the team has been doing),
  identifying systemic issues that slow down delivery, and tracking team
  health over time.
---

# /retro — Engineering Retrospective

Structured retrospective that learns from history.

## When to Activate

Trigger `/retro` when:
- Sprint or iteration ends
- Major milestone ships
- Team asks "what did we learn from that?"
- Tracking team health over time

## Two Modes

| Mode | Trigger | Scope |
|------|---------|-------|
| **Sprint retro** | Standard retro | Single project |
| **Global mode** | `/retro --global` | Cross-project patterns |

## Sprint Retro Mode

### Step 1: Set Time Range

Ask or detect:
```
RECOMMENDATION: Choose A — auto-detect from git log is fastest.
A) Auto-detect (last sprint — scan git log for sprint boundaries)
B) Specify range: YYYY-MM-DD..YYYY-MM-DD
C) Last N weeks
```

### Step 2: Git History Analysis

```bash
git log --since="{start_date}" --until="{end_date}" --oneline
git log --since="{start_date}" --until="{end_date}" --format="%H %ae %ad %s" --date=iso
git log --since="{start_date}" --until="{end_date}" --stat --summary
```

Extract:
- **Commits**: count, by author, by day
- **PRs merged**: count, cycle time (open → merged)
- **Files changed**: count, by category (feat/fix/docs/refactor)
- **Lines changed**: added/removed per commit

### Step 3: Velocity Metrics

Calculate:
- **Commit velocity**: commits per day
- **PR cycle time**: average time from open to merge
- **Code churn**: lines added + removed per week
- **Focus ratio**: feat/fix commits vs total

```
VELOCITY METRICS — {date range}
════════════════════════════
Commits:        {N} ({avg}/day)
PRs merged:     {N} (avg cycle: {X} days)
Lines changed:  +{added} / -{removed}
Focus ratio:    {feat+fix}% of commits
Top authors:   {name} ({N} commits), {name} ({N} commits)
```

### Step 4: Pattern Detection

Analyze the git log for patterns:

**Recurring themes:**
- Same type of bug fixed repeatedly? → systemic issue
- Same file changed many times? → likely a complexity hotspot
- Long gaps in activity? → blockers or PTO

```bash
git log --since="{start_date}" --grep="fix:" --oneline  # recurring fixes
git log --since="{start_date}" --grep="refactor:" --oneline  # refactor churn
```

**What worked (wins):**
- Look for: new features that shipped cleanly, well-tested PRs, clear commit structure
- Identify PRs with minimal back-and-forth (1-2 review rounds)

**What didn't (losses):**
- Look for: reverted commits, repeated fixes, long-lived branches
- Identify PRs with many rounds of review

### Step 5: Session Logs (if available)

If session logs exist in `{project}/memory/sessions/`:
```bash
cat {project}/memory/sessions/*.md | grep -A 5 "## What happened" | head -50
```

Extract themes from past sessions.

### Step 6: Win/Loss Summary

**Wins:**
```
WINS:
1. {win 1} — evidenced by: {git log excerpt}
2. {win 2} — evidenced by: {git log excerpt}
```

**Losses:**
```
LOSSES:
1. {loss 1} — evidenced by: {git log excerpt}
2. {loss 2} — evidenced by: {git log excerpt}
```

### Step 7: Action Items

For each loss, propose an action item:
```
ACTION ITEM: {description}
ROOT CAUSE: {why this happened}
OWNER: {who is responsible}
PRIORITY: P1 | P2 | P3
```

### Step 8: Full Retro Report

```
RETROSPECTIVE — {date range}
══════════════════════════════

VELOCITY:
{velocity metrics table}

WINS:
{win list}

LOSSES:
{loss list}

ACTION ITEMS:
{action items list}

VERDICT: {healthy|struggling|declining} — {one-line summary}
```

## Global Cross-Project Mode

Run `/retro --global` to analyze patterns across multiple projects.

### Step 1: Discover Projects

```bash
grep -A 100 "Active Projects" ~/.claude/memory/medium-term.md | grep "^| " | head -20
```

### Step 2: Per-Project Velocity

For each active project, run the sprint retro analysis (Steps 1-4).

### Step 3: Cross-Project Pattern Report

```
GLOBAL RETRO — {date range}
══════════════════════════════

CROSS-PROJECT METRICS:
{project}: {N} commits, {N} PRs, velocity: {X}/day
{project}: {N} commits, {N} PRs, velocity: {X}/day

PATTERNS:
- {pattern across multiple projects}

PORTFOLIO HEALTH:
{overall assessment}

RECOMMENDATIONS:
1. {cross-project recommendation}
```

## Tracking Over Time

After the retro, persist the results:
```bash
mkdir -p .gstack/retro-reports
cat > .gstack/retro-reports/{date}.md << 'EOF'
---
retro: {date range}
velocity: {metrics}
status: {healthy|struggling|declining}
EOF
```

This creates a history for trend analysis in future retros.

## Important Rules

- **Evidence-based.** Every finding needs a git log excerpt or session log cite.
- **Root cause over symptoms.** Don't just report the problem — identify why it happened.
- **Actionable items only.** If you can't turn a loss into an action item, skip it.
- **Wins are not optional.** Teams that only discuss what went wrong miss the chance to scale what works.
- **Global mode is for pattern recognition.** Individual project retros are more detailed.