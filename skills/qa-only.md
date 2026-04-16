---
name: qa-only
description: >
  Report-only QA — browser-based testing that finds and documents bugs
  without fixing them. Takes a URL, runs through pages, captures console
  errors and screenshots, and produces a structured bug report. The output
  is a documented list of findings, not fixes. Best for: letting a human
  decide what to fix, prioritizing a backlog, or generating QA reports
  for stakeholders who don't need the fix loop. Use when you want QA
  findings without automated remediation.
---

# /qa-only — Report-Only QA

Browser-based QA that documents findings without fixing them.

## When to Activate

Trigger `/qa-only` when:
- You want a QA report without automatic fixes
- Prioritizing a backlog of known issues
- Generating a report for stakeholders
- A human will decide what to fix

## Prerequisites

Check browse availability:
```bash
which browse 2>/dev/null || ls ~/.claude/skills/gstack/browse/dist/browse 2>/dev/null
```

If not available, tell the user: "gstack browse needs a one-time build (~10 seconds). Run: `cd ~/.claude/skills/gstack && ./setup`"

## Instructions

### Step 1: Discover Pages

**Load the homepage:**
```bash
$B goto {url}
$B links
$B text
```

**Build page list:**
Extract navigation links. Ask the user which pages to test:
```
Pages discovered:
1. {path}
2. {path}
3. {path}

RECOMMENDATION: Choose A — covers the main user flows.
A) Test all discovered pages
B) Test specific pages (user specifies)
C) Homepage only
```

### Step 2: Page-by-Page Scan

For each confirmed page:

```bash
$B goto {url}{path}
$B snapshot -i -a -o ".qa/screenshots/{slug}-{ts}.png"
$B console --errors
$B perf
$B text
```

Record for each page:
- Page title and URL
- Screenshot path
- Console error count and messages (Error level only)
- Load time
- Key text content
- Any visible error states

### Step 3: Collect for Findings

For each page, check for:
- **Console errors**: `Error` level messages only (ignore warnings)
- **Broken UI**: 404s embedded in pages, broken images, placeholder text
- **Performance**: Load time > 5 seconds, very large DOM
- **Visual anomalies**: Misaligned layouts, missing content, wrong fonts

### Step 4: Severity Scoring

Score each finding:
- **P1**: Critical — site broken, data loss possible, auth bypass
- **P2**: High — major feature broken, user cannot complete key task
- **P3**: Medium — non-critical bug, workaround exists
- **P4**: Low — cosmetic, edge case, no user impact

### Step 5: Produce Bug Reports

For every finding, write:

```
## BUG #{N}: {title}

**Severity:** P1 | P2 | P3 | P4
**Page:** {url}
**Found:** {timestamp}

**What was found:**
{detailed description}

**Evidence:**
- Screenshot: `{path}`
- Console: {N} errors — {error messages}
- Load time: {Xs}

**Expected behavior:**
{what should happen}

**Business impact:**
{who is affected, how}
```

### Step 6: QA Health Score

```
QA REPORT — {url}
═════════════════════════
Scanned:       {date}
Pages tested: {N}
Findings:     {N}
  P1:         {N}
  P2:         {N}
  P3:         {N}
  P4:         {N}

SCORE: {calculated score}%
STATUS: REPORT ONLY — no fixes applied

Next step: Run /qa with the same URL to enter the fix loop.
```

### Step 7: Persist Screenshots

```bash
mkdir -p .qa/screenshots
```

All screenshots saved to `.qa/screenshots/` with descriptive names.

## Report Formats

**Short summary (for Slack/teams):**
```
QA: {url}
Pages: {N} | Issues: {N} (P1:{n} P2:{n} P3:{n} P4:{n})
Score: {score}%
Status: REPORT ONLY — fix with /qa
```

**Full report (for stakeholders):**
Includes all bug reports, screenshots, and recommendations.

## Important Rules

- **Report only.** Do not fix anything in this skill. Use `/qa` if fixes are needed.
- **Error level only.** Ignore console warnings — they are noise.
- **Screenshot everything.** Visual evidence is required for every finding.
- **Severity is important.** P1 bugs block shipping. P4 bugs can wait.
- **Score reflects health.** 80%+ = good. Below 60% = significant issues.