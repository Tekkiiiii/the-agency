---
name: qa
description: >
  Full QA workflow: browser-based testing, bug report generation, fix
  iteration, and verification. Takes a URL, runs through the pages, finds
  issues, files bugs with screenshots and console logs, fixes bugs, re-tests
  to verify fixes, and produces a health score. Trigger when: "run QA test",
  "QA this page", "test this feature", "QA review", or any time you need
  browser-based verification of a live app. Key capabilities: multi-page
  traversal (follows nav links to cover the app), bug report generation
  with severity scoring, console error detection (Error level only), visual
  evidence (annotated screenshots for every finding), and a fix loop that
  makes changes, re-tests, and verifies the fix worked. Also for: regression
  testing after a fix, smoke testing a deployment, and comparing two versions
  of a page side-by-side. Not for: unit testing (use /test for that) or
  API testing (use a dedicated API testing approach).
---

# /qa — Full QA Test Workflow

Browser-based testing with bug finding, fixing, and verification.

## When to Activate

Trigger `/qa` when:
- User asks to "run QA test" or "QA this page"
- Testing a feature before shipping
- Verifying a deployment is healthy
- Running regression tests after a fix

## Prerequisites

Before running QA, the browse binary must be available. Check:
```bash
which browse 2>/dev/null || ls ~/.claude/skills/gstack/browse/dist/browse 2>/dev/null
```

If not available, tell the user: "gstack browse needs a one-time build (~10 seconds). Run: `cd ~/.claude/skills/gstack && ./setup`"

## Instructions

### Phase 1: Discovery + Baseline

**Step 1: Load the page**
```bash
$B goto {url}
```

**Step 2: Inventory the surface**
```bash
$B links
$B text
$B snapshot -i -a
```

Extract:
- Navigation links (top 10)
- Page text content
- Annotated screenshot

**Step 3: Console errors at baseline**
```bash
$B console --errors
```

Capture console errors before any interaction. Store the error count as `baseline_errors`.

**Step 4: Discover internal pages**
```bash
$B goto {url}/sitemap.xml 2>/dev/null || $B goto {url}/api/pages 2>/dev/null || echo "NO_SITEMAP"
```

Or trace links from the homepage to find the main pages.

Build a page list:
```
PAGES TO TEST:
1. / (homepage)
2. /{nav-link-1}
3. /{nav-link-2}
4. /{nav-link-3}
```

Present the list via AskUserQuestion — confirm which pages to test.

### Phase 2: Page-by-Page Test

For each page in the confirmed list:

**Step 1: Navigate and snapshot**
```bash
$B goto {page_url}
$B snapshot -i -a -o ".qa/screenshots/{page_name}-{timestamp}.png"
$B text
```

**Step 2: Check console errors**
```bash
$B console --errors
```

Flag any Error-level messages. Ignore warnings.

**Step 3: Check performance**
```bash
$B perf
```

Flag any page that takes >5 seconds to load or has very large DOM size.

**Step 4: Check for broken elements**
```bash
$B js "document.querySelectorAll('[class*=\"broken\"], [class*=\"error\"], [data-error]').length"
```

Check for visible error messages in the DOM.

### Phase 3: Bug Report Generation

For every finding from Phase 2, produce a structured bug report:

```
## BUG #{N}: {short title}

**Severity:** P1 (critical) | P2 (high) | P3 (medium) | P4 (low)

**Page:** {URL}

**Finding:**
{what the test found}

**Evidence:**
- Screenshot: {path}
- Console errors: {N} errors
- Load time: {Xs}
- Text snippet: "{text excerpt}"

**Expected:** {what should happen}
**Actual:** {what is happening}

**Severity reasoning:**
- Business impact: {who is affected, how}
- Frequency: {how often does this occur}
```

**Severity scoring:**
- P1: Site down, data loss, auth bypass — ship is blocked
- P2: Broken feature, major UX failure — user cannot complete key task
- P3: Non-critical bug, workaround exists — impacts experience but not function
- P4: Minor cosmetic or edge case — doesn't block anything

### Phase 4: Fix Loop

For each P1 or P2 bug:

**Step 1: Reproduce locally**
Create a minimal reproduction case. Understand the root cause, not just the symptom.

**Step 2: Make the fix**
Edit the relevant code.

**Step 3: Re-test**
```bash
$B goto {page_url}
$B console --errors
$B text
$B snapshot -i
```

**Step 4: Verify**
If the bug is fixed, mark it VERIFIED. If not, iterate.

### Phase 5: Health Score

Calculate the QA health score:

```
QA HEALTH SCORE — {url}
═════════════════════════
Pages tested:      {N}
Total findings:    {N}
  P1:             {N} (blocks ship)
  P2:             {N}
  P3:             {N}
  P4:             {N}
Fixed:            {N} / {N}
Remaining:        {N}

SCORE: {P1×10 + P2×7 + P3×4 + P4×1} / {N pages × 10} = {score}%
STATUS: {PASS | CONDITIONAL PASS | FAIL}

PASS: No P1s, P2s < 2, score > 80%
CONDITIONAL PASS: P1s fixed, P2s < 5, score > 60%
FAIL: P1s present or score < 60%
```

### Phase 6: Report

Output a structured summary:

```
QA REPORT — {url}
═════════════════════
Tested:      {date}
Pages:       {N}
Findings:   {N}
Score:      {score}%
Status:     {PASS|CONDITIONAL|FAIL}

DETAILED FINDINGS:
[all bug reports]

SCREENSHOTS:
.all screenshots in .qa/screenshots/

VERDICT: {READY TO SHIP / NEEDS FIXES / BLOCKED}
```

## Important Rules

- **P1 blocks ship.** If a P1 is found, do not proceed to /ship until fixed.
- **Console errors: Error level only.** Ignore warnings — they are noise.
- **Screenshot everything.** Every finding needs visual evidence.
- **Reproduce before fixing.** Don't guess at the root cause.
- **Fix loop is fast.** Make the change, re-test, verify. Don't overthink.
- **Smoke test a deployment.** /qa can verify a new deploy is healthy in minutes.