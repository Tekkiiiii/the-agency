---
name: plan-design-review
description: >
  Report-only design audit — reviews a plan or URL for UI/UX gaps without
  fixing them. Captures screenshots, annotates gaps, scores 10 dimensions
  (hierarchy, layout, typography, color, spacing, responsiveness, consistency,
  visual polish, UX patterns, accessibility), and produces a structured
  scorecard. Triggers when: "design review", "UX review", "UI audit", "check
  this design", or when reviewing a plan with significant UI work. Key
  capability: consistent scoring rubric so teams can track design quality over
  time. Also for: scoring a redesign, comparing two design approaches, and
  baseline auditing before a major UI overhaul. Not for: interactive fixing
  (use /design-review for that).
---

# /plan-design-review — Report-Only Design Audit

Structured design audit with scoring across 10 dimensions.

## When to Activate

Trigger `/plan-design-review` when:
- Reviewing a plan with significant UI work
- Auditing a live URL for design quality
- Scoring a redesign effort
- Baseline audit before a major UI overhaul

## Instructions

### Step 1: Load the Subject

**If a URL is provided:**
```bash
$B goto {url}
$B snapshot -i -a
$B text
```

**If a plan is provided:**
Read the plan and extract any UI descriptions, screenshots, or design references.

**If Figma URL is provided:**
Call `get_design_context` to extract design tokens.

### Step 2: Evaluate 10 Dimensions

For each dimension, score 1-10 and provide evidence.

#### 1. Visual Hierarchy
Does the page guide the eye to what matters first?
- 10: Clear primary/secondary/tertiary structure, eye flows naturally
- 5: Some hierarchy but mixed signals
- 1: No clear hierarchy, everything competes for attention

#### 2. Layout & Structure
Is the overall layout logical and balanced?
- 10: Clean, balanced, appropriate density
- 5: Functional but unbalanced or cluttered
- 1: Chaotic, confusing structure

#### 3. Typography
Are fonts consistent, readable, and appropriately sized?
- 10: Consistent scale, readable at all sizes, appropriate weights
- 5: Mostly consistent with minor inconsistencies
- 1: Inconsistent sizes, poor contrast, wrong fonts

#### 4. Color & Palette
Does the color usage feel intentional and accessible?
- 10: Consistent palette, good contrast, intentional accents
- 5: Palette exists but not always applied consistently
- 1: Random colors, poor contrast, no palette

#### 5. Spacing & Rhythm
Is there consistent spacing between and within elements?
- 10: Consistent spacing scale, good rhythm
- 5: Mostly consistent with some outliers
- 1: Random spacing, cramped or sparse sections

#### 6. Responsiveness
Does the design work at all viewport sizes?
- 10: Perfect at all sizes, fluid layout
- 5: Functional at main sizes, minor breaks elsewhere
- 1: Desktop-only or significantly broken at mobile/tablet

#### 7. Visual Consistency
Are components used consistently throughout?
- 10: All buttons look the same, forms consistent, patterns repeated
- 5: Mostly consistent with exceptions
- 1: Every instance looks different

#### 8. Polish & Refinement
Does the design feel finished or rough?
- 10: Refined, smooth edges, considered micro-interactions
- 5: Functional but feels like a first draft
- 1: Rough, unfinished, placeholder elements visible

#### 9. UX Patterns
Are standard patterns used correctly?
- 10: Buttons look like buttons, links look like links, forms behave predictably
- 5: Mostly correct with some deviations
- 1: Non-standard patterns that confuse users

#### 10. Accessibility
Is the design accessible?
- 10: WCAG AA compliant, keyboard navigable, screen reader friendly
- 5: Basic accessibility but gaps
- 1: Major accessibility failures (contrast, missing labels, no keyboard nav)

### Step 3: Annotated Screenshots

For each dimension scoring below 7, capture a screenshot with annotation:
```bash
$B snapshot -i -a -o ".qa/design-reviews/{slug}-dim{N}-{timestamp}.png"
```

### Step 4: Scorecard

```
DESIGN REVIEW SCORECARD — {url or plan name}
══════════════════════════════════════════

Visual Hierarchy:      {N}/10  {evidence}
Layout & Structure:   {N}/10  {evidence}
Typography:          {N}/10  {evidence}
Color & Palette:     {N}/10  {evidence}
Spacing & Rhythm:   {N}/10  {evidence}
Responsiveness:      {N}/10  {evidence}
Visual Consistency:  {N}/10  {evidence}
Polish & Refinement: {N}/10  {evidence}
UX Patterns:         {N}/10  {evidence}
Accessibility:       {N}/10  {evidence}

OVERALL SCORE:        {avg}/10
GRADE:                A | B | C | D | F

A: 9-10   Strong design — ship it
B: 7-8    Good design — minor fixes before ship
C: 5-6    Needs work — significant improvements needed
D: 3-4    Poor design — major overhaul recommended
F: 1-2    Broken design — redesign from scratch
```

### Step 5: Findings

For each dimension below 7:

```
FINDING: {dimension} — Score {N}/10
Issue:    {what's wrong}
Evidence: {screenshot reference, specific elements}
Impact:   {how this affects the user}
Fix:      {what would improve the score}
```

### Step 6: Recommendations

**Must fix (below 5):**
- {dimension}: {specific fix}

**Should fix (5-6):**
- {dimension}: {specific fix}

**Nice to have (7-8):**
- {dimension}: {specific fix}

## Important Rules

- **Score the evidence, not the taste.** Score based on functional criteria, not personal aesthetic preference.
- **Below 7 means "needs work".** Below 5 means "blocks ship".
- **Annotate every low score.** Screenshots with circle annotations are worth more than words.
- **Consistency trumps perfection.** A consistent B-grade design is better than an A in one area and F in another.
- **Accessibility is functional.** WCAG compliance is not optional.
