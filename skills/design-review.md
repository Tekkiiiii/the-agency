---
name: design-review
description: >
  Visual QA + fix loop — captures the UI state of a URL, reviews it against
  a design reference (Figma, screenshot, or written spec), identifies visual
  gaps, fixes mismatches, and re-verifies the result. Goes beyond functional
  QA to review: spacing, typography, color, alignment, responsiveness, and
  overall polish. Trigger when: "review the design", "check the UI", "design QA",
  "compare to Figma", or after any UI change that needs visual verification.
  Also for: pre-ship polish check, onboarding audit of a new interface, and
  responsive design testing across viewports.
---

# /design-review — Visual Design QA

Verifies that a live UI matches the intended design and fixes any visual gaps.

## When to Activate

Trigger `/design-review` when:
- User asks to "review the design" or "check the UI"
- After any UI change
- Before shipping a feature with a visual component
- Comparing a page against a Figma spec or screenshot

## Prerequisites

**Check browse:**
```bash
ls ~/.claude/skills/gstack/browse/dist/browse 2>/dev/null && echo "READY" || echo "NEEDS_SETUP"
```

If NEEDS_SETUP: tell the user to run `cd ~/.claude/skills/gstack && ./setup`

**Detect design reference:**
- Figma URL provided? → Get design context
- Screenshot provided? → Compare visually
- Written spec provided? → Check against spec
- No reference? → Audit the page for general quality

## Instructions

### Step 1: Load the Page + Capture Baseline

```bash
$B goto {url}
$B snapshot -i -a -o ".qa/design-review/baseline.png"
$B text
$B perf
```

Save to `.qa/design-review/`. Create the directory first.

### Step 2: Apply Design Reference

**If Figma URL provided:**
Call `mcp__plugin_figma_figma__get_design_context` with the fileKey and nodeId.
Extract: colors, typography, spacing, component structure.

**If screenshot provided:**
Read the screenshot file. Compare element-by-element against the live page.

**If written spec provided:**
Parse the spec for: spacing system, color palette, typography scale,
component list, layout rules.

**If no reference:**
Proceed with general quality audit (Step 3).

### Step 3: Visual Gap Analysis

Evaluate the page against the reference (or general best practices):

**Spacing:**
```bash
$B js "
  const els = document.querySelectorAll('[class]');
  const spacings = [...els].map(el => {
    const s = window.getComputedStyle(el);
    return { el: el.className, margin: s.margin, padding: s.padding };
  });
  spacings.slice(0, 20);
"
```

Check for: consistent spacing scale, no orphaned elements, no cramped sections.

**Typography:**
```bash
$B js "
  const textEls = document.querySelectorAll('h1, h2, h3, p, span');
  [...textEls].slice(0, 10).map(el => ({
    tag: el.tagName,
    text: el.textContent.trim().slice(0, 50),
    font: window.getComputedStyle(el).fontFamily,
    size: window.getComputedStyle(el).fontSize,
    weight: window.getComputedStyle(el).fontWeight
  }))
"
```

Check: consistent font scale, correct heading hierarchy, readable line height.

**Color:**
```bash
$B js "
  const styles = [...document.styleSheets].flatMap(sheet => {
    try { return [...sheet.cssRules] } catch { return [] }
  });
  const colors = styles.map(r => r.style?.color).filter(Boolean);
  const bgs = styles.map(r => r.style?.backgroundColor).filter(Boolean);
  [...new Set([...colors, ...bgs])].slice(0, 20);
"
```

Check: consistent palette usage, no jarring color mismatches, sufficient contrast.

**Alignment:**
```bash
$B js "
  const boxes = [...document.querySelectorAll('[class]')].slice(0, 30).map(el => {
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
  });
  boxes;
"
```

Check: elements on the same row have same `y` offset, no obvious misalignment.

### Step 4: Responsive Check

Test at multiple viewport sizes:
```bash
$B resize 375 667   # iPhone SE
$B snapshot -i -o ".qa/design-review/mobile.png"
$B resize 768 1024  # iPad
$B snapshot -i -o ".qa/design-review/tablet.png"
$B resize 1440 900  # Desktop
$B snapshot -i -o ".qa/design-review/desktop.png"
```

For each viewport, check:
- Text reflows correctly (no horizontal scroll on mobile)
- Navigation is usable
- Touch targets are at least 44px
- No content hidden off-screen

### Step 5: Gap Report

Produce a structured gap report:

```
DESIGN REVIEW — {url}
══════════════════════════
Reference: {Figma | screenshot | written spec | general audit}

SPACING:
  Status: PASS | ISSUES FOUND
  Issues:
    - {element}: expected {spacing}, got {spacing}
    - ...

TYPOGRAPHY:
  Status: PASS | ISSUES FOUND
  Issues:
    - {element}: font/size/weight mismatch

COLOR:
  Status: PASS | ISSUES FOUND
  Issues:
    - {element}: color mismatch

ALIGNMENT:
  Status: PASS | ISSUES FOUND
  Issues:
    - {element}: not aligned with siblings

RESPONSIVE:
  Mobile: PASS | ISSUES
  Tablet: PASS | ISSUES
  Desktop: PASS | ISSUES

OVERALL SCORE: {N}%
STATUS: READY | NEEDS FIXES | SIGNIFICANT GAPS
```

### Step 6: Fix Loop (if gaps found)

For each gap:
1. Make the visual fix in the source code
2. Re-test the affected page/viewport
3. Verify the fix

### Step 7: Re-verify and Final Report

After fixes:
```bash
$B goto {url}
$B snapshot -i -a -o ".qa/design-review/verified.png"
```

Compare baseline to verified screenshot.

Final report:
```
DESIGN REVIEW — VERIFIED
══════════════════════════
Original issues: {N}
Fixed:           {N}
Remaining:      {N}

SCREENSHOT: .qa/design-review/verified.png
STATUS: READY TO SHIP | NEEDS MORE WORK
```

## Figma Workflow

When a Figma URL is provided:
1. Call `get_design_context` for the node
2. Extract design tokens: colors, spacing, typography, shadows
3. Compare against live page values
4. Note which tokens are being violated

## Important Rules

- **Visual fixes first.** This is a design QA skill — prioritize visual
  consistency before functional bugs (use /qa for functional issues).
- **Screenshot is evidence.** Every gap needs a before/after screenshot.
- **Responsive is mandatory.** A page that only looks good at 1440px is broken.
- **Reference is the truth.** If Figma says a button should be blue, it
  should be blue. Don't debate the spec — implement it.
- **Small gaps are still gaps.** A 2px misalignment is still a gap. Fix it.
- **Polish is a feature.** Visual quality is part of the product, not a nice-to-have.