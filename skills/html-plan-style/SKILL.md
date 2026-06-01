---
name: html-plan-style
description: >
  Use when generating any HTML plan, report, or deliverable document. Apply this
  skill whenever the task involves "create a plan", "write a plan", "make an HTML
  plan", "/pipeline-*" that produces plans, output convention plan files, or any
  structured HTML document for review. Provides a locked color
  palette, typography, and layout system so all plan HTML files look consistent
  and professional. Includes the 22px body font rule, rem-based child sizing,
  CSS variable architecture, print stylesheet, and a full component vocabulary
  (headings, callouts, tables, checklists, code blocks, status badges).
  Self-contained. Use plan-template.html as the base skeleton and
  style.css (or the embedded style block) as the single CSS source of truth.
  Also for: session digests, agent reports, architecture decision records, sprint
  summaries, onboarding docs, and any structured HTML deliverable that will be
  opened in a browser or exported to PDF. This skill is for plans/documents, not slide decks.
scope: global
dept:
  - all
team: "-"
priority: foundation
triggers:
  - create a plan
  - write a plan
  - make an html plan
  - write an html plan
  - generate a plan
  - plan.html
  - output convention
  - pipeline-feature
  - pipeline-bugfix
  - pipeline-content
  - pipeline-audit
  - pipeline-deploy
  - pipeline-seo
  - html report
  - html deliverable
  - architecture decision record
  - session digest
aliases:
  - plan-style
  - html-plan
  - plan-template
last_updated: "2026-05-22"
trust_level: human-authored
author: agency
provenance: manual
quality_gate_passed: true
---

# html-plan-style

Locked style system for all HTML plan and report files. Apply whenever producing a plan.html.

## Quick Start

1. Copy `plan-template.html` from this skill directory as your starting file
2. Replace the placeholder content with your actual plan content
3. Do NOT change the CSS variables in `:root` -- palette changes happen in one place
4. Serve or open in browser to verify; export to PDF via browser print if needed

## Palette Reference (CSS Variables)

| Variable | Value | Use |
|---|---|---|
| `--color-bg` | `#f0f5f3` | Page background (forest-50) |
| `--color-surface` | `#ffffff` | Cards, panels |
| `--color-surface-alt` | `#fdf6f3` | Alternate section bg (terracotta-50) |
| `--color-border` | `#d4e9e2` | Card borders (forest-100) |
| `--color-border-subtle` | `#e7e5e4` | Subtle dividers (stone-200) |
| `--color-primary` | `#1E3A2F` | Forest-800 -- primary headings, CTAs |
| `--color-primary-dark` | `#1a3028` | Forest-900 -- hero bg, dark sections |
| `--color-primary-light` | `#3d7a62` | Forest-500 -- links, accents |
| `--color-accent` | `#D4A853` | Gold-500 -- highlights, badges |
| `--color-accent-dark` | `#b8922e` | Gold-600 -- hover states |
| `--color-secondary` | `#C4785A` | Terracotta-500 -- warnings, secondary |
| `--color-secondary-light` | `#f5d5c8` | Terracotta-200 -- warning backgrounds |
| `--color-text` | `#292524` | Stone-800 -- body text |
| `--color-text-muted` | `#78716c` | Stone-500 -- captions, metadata |
| `--color-text-on-primary` | `#ffffff` | Text on dark/forest bg |
| `--color-success` | `#3d7a62` | Forest-500 -- success states |
| `--color-success-bg` | `#f0f5f3` | Forest-50 -- success bg |

## Typography

- Body: `Plus Jakarta Sans`, `DM Sans`, `system-ui`, sans-serif
- Display/headings: `Playfair Display`, `Georgia`, serif
- Mono: `JetBrains Mono`, `ui-monospace`, monospace
- Base size: **22px** (per CLAUDE.md rule) -- all children in `rem`
- H1: 2.5rem | H2: 1.8rem | H3: 1.3rem | H4: 1.1rem

## Component Vocabulary

### Section Label (gold, uppercase)
```html
<span class="section-label">Phase 1</span>
```

### Callout Types
```html
<div class="callout callout-info">Informational note</div>
<div class="callout callout-warning">Warning or blocker</div>
<div class="callout callout-success">Completed or approved</div>
<div class="callout callout-decision">Decision locked</div>
```

### Status Badge
```html
<span class="badge badge-done">Done</span>
<span class="badge badge-in-progress">In Progress</span>
<span class="badge badge-blocked">Blocked</span>
<span class="badge badge-pending">Pending</span>
```

### Checklist
```html
<ul class="checklist">
  <li class="done">Completed item</li>
  <li class="in-progress">Active item</li>
  <li>Pending item</li>
</ul>
```

### Card
```html
<div class="card">
  <h3>Card Title</h3>
  <p>Card content</p>
</div>
```

### Table
Use standard `<table>` -- the stylesheet handles striping and borders automatically.

### Code Block
Use standard `<pre><code>` -- styled with mono font and forest-50 background.

### Hero / Title Block
```html
<header class="plan-header">
  <span class="section-label">Project Name</span>
  <h1>Plan Title</h1>
  <p class="subtitle">One-line description of this plan</p>
  <div class="header-meta">
    <span>Date: 2026-05-22</span>
    <span>Author: System-Improvement PD</span>
    <span class="badge badge-in-progress">In Progress</span>
  </div>
</header>
```

## Invocation Rules

- Always load `plan-template.html` as the base (or copy its `<style>` block inline)
- Never override CSS variables outside `:root`
- Never use inline `color:` or `background:` -- use CSS variable references only
- Body font stays 22px; child elements use rem (e.g. `1rem` = 22px, `0.9rem` = ~20px)
- Print stylesheet is included -- do not remove the `@media print` block
- No emojis in plan content unless the plan content specifically calls for them

## Files in This Skill

- `SKILL.md` -- this file (invocation guide + component vocabulary)
- `plan-template.html` -- full skeleton ready to fill in
- `style.css` -- standalone CSS (same as the embedded style in plan-template.html)
