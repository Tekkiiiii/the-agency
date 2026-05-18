---
name: tekki-strategic-deck
description: Build a 25-30 slide strategic pitch / audit deck in Tekki's signature style — TekkiSolutions indigo+amber brand gradient on hero slides, cream content slides with a vertical accent bar, navy ink headlines, amber highlights, and a five-act narrative arc (audit - marketing - market - bet - go-to-market). Use whenever the user asks to "build a strategic deck", "audit company X and recommend a bet", "make a pitch deck in my style", "rebuild this deck for [different company]", or any pitch/audit/strategy slide deliverable. Also triggers on "marketing assessment deck", "candidate gift deck", "30-slide deck", and references to the Pay2Pay deck as a stylistic reference.
---

# Strategic Deck — Tekki style

A reusable design system + working template for 25-30 slide strategic decks. Built with `pptxgenjs`. Renders in LibreOffice for QA. Adapted from the Pay2Pay 2026 strategic audit deck. Default palette: TekkiSolutions brand (Deep Indigo + Warm Amber + Off-White).

---

## Quick reference

| Task | Where to look |
|------|---------------|
| Build a new deck | `template.js` — copy, edit `BRIEF` block at top, run with node |
| Change brand colors | Edit the `// ---------- Palette ----------` section in template.js |
| Add a slide pattern | Section comments in template.js — copy a pattern block, swap content |
| Render & QA | `npm install` — `node template.js` — convert to PDF/JPG — visually inspect |
| Brand database | `~/.claude/projects/tekki/memory/brand-database.md` — per-client colors |
| Common pitfalls | See "Pitfalls" section below |

---

## When to use this skill

**Use it when the user wants:**
- A strategic audit deck on a company (the Pay2Pay use case)
- A marketing assessment deck for a TekkiSolutions prospect
- A pitch deck framed as "current state - my bet"
- A multi-act narrative deck (typically 5 sections x 4-6 slides each)
- Anything that should match Tekki's visual language

**Don't use it for:**
- One-off pitch decks under 10 slides — overkill
- Quick content slides — use Marp with `tekkisolutions.css` theme instead
- Decks where the user wants a completely different visual system

---

## Design system

### Palette (TekkiSolutions default)

```
PRIMARY      1B1F3B   Deep Indigo — accents, kickers, card outlines, dark backgrounds
PRIMARY_DEEP 141730   Deeper Indigo — gradient anchor, darkest fills
LAVENDER     3D4266   Mid-Navy — secondary accent, muted text
AMBER        F5A623   Warm Amber — complementary highlight, BET / WIN / RECO callouts
AMBER_DARK   D98D0B   Darker Amber — hover/active states
BG           F8F6F1   Off-White Cream — default content slide background
BG_ALT       EFEADF   Surface Cream — secondary card backgrounds
TEXT         1B1F3B   Deep Indigo — body text (same as PRIMARY)
MUTED        3D4266   Mid-Navy — captions, footnotes
BORDER       E0DBCE   Cream border — card outlines on white bg
SUBTLE       F5F3EE   Very pale cream — table alt rows
```

**To rebrand for a client deck:** check `~/.claude/projects/tekki/memory/brand-database.md` for client-specific colors. Swap PRIMARY, PRIMARY_DEEP, LAVENDER for the target company's colors. The structure doesn't depend on these specifically.

### Typography

- **Headline font:** DM Serif Display (install locally: `~/.claude/projects/tekki/assets/fonts/dm-serif/`)
- **Body font:** Inter (install locally: `~/.claude/projects/tekki/assets/fonts/inter/`)
- **Fallback:** Calibri (universal, Vietnamese-friendly)
- **Title sizes:** 56pt (cover), 40-54pt (section dividers), 26-28pt (content slide titles)
- **Body sizes:** 14pt (intro paragraphs), 11-12pt (cards), 10-10.5pt (table cells)
- **Kicker / eyebrow text:** 10-11pt bold uppercase with `charSpacing: 4-8`

### Visual motifs (use consistently)

1. **Vertical accent bar** to the left of every content-slide title — `0.07" wide`, indigo, height matches title block.
2. **Radial gradient** on hero/divider slides — subtle lighter center fading to deep navy at edges (NOT flat navy, NOT white center).
3. **Decorative ovals** on hero/divider slides — amber + lavender + white-with-transparency, partially off-slide so they bleed.
4. **Cards with left accent** — content cards have a thin colored vertical strip on the left edge (indigo for default, amber for "win/bet").
5. **No accent lines under titles** — never. They're the AI-deck giveaway.
6. **Footer** on every content slide: "[Deck name] . [page] / [total]" in muted slate.

### Layout grid (16:9, 10" x 5.625")

- Slide margins: 0.4"-0.6" left/right, 0.3"-0.5" top/bottom
- Title block: x=0.6, y=0.4-1.0, w=9
- Content area: x=0.6, y=1.25-4.95, w=8.85
- Footer: y=5.30
- Card gutters: 0.15" between cards in a row

---

## Gradient specification (TekkiSolutions)

The hero/divider/closing slides use a radial gradient, NOT flat navy. Generated as SVG -> PNG via sharp.

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
  <defs>
    <linearGradient id="base" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%"   stop-color="#141730"/>
      <stop offset="55%"  stop-color="#1B1F3B"/>
      <stop offset="100%" stop-color="#242848"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="45%">
      <stop offset="0%"   stop-color="#242848" stop-opacity="1"/>
      <stop offset="100%" stop-color="#1B1F3B" stop-opacity="1"/>
    </radialGradient>
  </defs>
  <rect width="1600" height="900" fill="url(#base)"/>
  <rect width="1600" height="900" fill="url(#glow)"/>
</svg>
```

This produces a subtle lighter-center gradient that adds depth without washing out text. The center is slightly lighter navy (#242848), edges are deep indigo (#141730). No white, no visible spotlight — just warmth.

---

## Slide patterns (the building blocks)

The template includes one canonical example of each. Reuse / repeat / vary as needed.

### 1. Cover (gradient background)
### 2. Section divider (gradient bg + decorative ovals)
### 3. Standard content slide (cream bg, kicker + title + body)
### 4. Three-card row (icon + title + body)
### 5. Six-card grid (2x3)
### 6. Comparison columns (3 cards horizontally)
### 7. Bordered table (header row + alt-fill rows)
### 8. KPI tile grid (2x3)
### 9. Two-column with chart on left
### 10. Findings/risks list (5+ stacked cards)
### 11. Recommendation hero (gradient bg + 3 dark cards)
### 12. Closing prose (gradient bg + paragraphs + sign-off)

---

## Standard 30-slide structure

```
1.  Cover (gradient)
2.  About this deck (3 cards explaining what this is)
3.  Executive summary (4-5 stacked findings)
4.  PART 1 - divider
5-8.   Part 1 content (company snapshot, products, posture, content audit)
9.  PART 2 - divider
10-13. Part 2 content (channel inventory, SEO gap, brand risk, dev gap)
14. PART 3 - divider
15-17. Part 3 content (competitive map, positioning matrix, options)
18. PART 4 - divider (the pivot to "the bet")
19-24. Part 4 content (global wave, local gap, primitive deep-dive, audience, recommendation, blueprint)
25. PART 5 - divider
26-29. Part 5 content (channels, 90-day plan, KPIs, risks)
30. Closing (gradient + personal note)
```

### Marketing Assessment variant (for TekkiSolutions prospects)

```
1.  Cover (gradient) — "Danh Gia Marketing" / "Marketing Assessment Report"
2.  About this report
3.  Executive scorecard
4.  PART 1 - Current State divider
5-9.   Current state (website, facebook, instagram, google, brand consistency)
10. PART 2 - Process Assessment divider
11-14. Process (customer mgmt, lead gen, decision making, maturity level)
15. PART 3 - Problem Diagnosis divider
16-18. Diagnosis (owner perception, data shows, hidden cost, gap)
19. PART 4 - Recommendations divider
20-24. Recommendations (roadmap, quick wins, foundation, growth, ROI)
25. PART 5 - AI Solutions divider
26-28. AI (mapped to their gaps, examples, SIGNAL method)
29-30. Next steps + closing
```

---

## How to brief a new deck

```yaml
subject:           # Who/what is the deck about?
audience:          # Prospect / investors / internal team
intent:            # "marketing assessment" / pitch / audit / sales
length:            # 20 / 25-30 / 40 slides
arc:               # What's the 5-act narrative? Default: audit - marketing - market - bet - GTM
the_bet:           # If applicable: what's the headline recommendation?
brand_colors:      # "tekkisolutions" (default) or client-specific from brand-database.md
language:          # English / Vietnamese / mixed
sources_visible:   # Should source footnotes appear on slides? (default: yes)
risk_tone:         # Constructive ("assessment") / pointed ("paid audit") / neutral
```

---

## Setup

```bash
npm init -y
npm install pptxgenjs react react-dom react-icons sharp
cp ~/.claude/skills/skill-tekki-strategic-deck/template.js ./
# Edit BRIEF block, then:
node template.js
```

---

## Rendering & QA workflow

```bash
soffice --headless --convert-to pdf deck.pptx
pdftoppm -jpeg -r 110 deck.pdf slide
ls slide-*.jpg
```

**Visual QA checklist:**
- Title kicker doesn't collide with title text on two-line titles
- Card content doesn't overflow card boundaries
- Footer text and page number have >=0.2" gap
- Decorative ovals don't sit on top of body text
- Gradient is subtle (no white spotlight in center)
- Typography: DM Serif Display for headlines, Inter for body
- Currency: use "VND" string, NOT the dong symbol

---

## Pitfalls (learned the hard way)

1. **Never use "₫" symbol** — LibreOffice renders it wrong. Use "VND".
2. **Never use "#" prefix on hex colors** — corrupts the .pptx file.
3. **Never use 8-char hex with alpha** — corrupts. Use `opacity` property.
4. **Don't reuse `shadow` or `option` objects** — pptxgenjs mutates them in place.
5. **Don't pair `ROUNDED_RECTANGLE` with rectangular accent overlays**.
6. **Don't run a single Edit tool against very long template files** — use sed.
7. **Brand gradient = SVG -> PNG**, not pptxgenjs-native.
8. **Bullets must use `bullet: true`** — never unicode.

---

## Customisation cookbook

**Change to original purple (Pay2Pay-style):**
- PRIMARY: `1B1F3B` -> `6343F0`
- PRIMARY_DEEP: `141730` -> `5427D4`
- LAVENDER: `3D4266` -> `859EFF`
- AMBER stays `F5A623`

**Change to green (9Pay-style):**
- PRIMARY: `1B1F3B` -> `00A562`
- PRIMARY_DEEP: `141730` -> `008049`
- LAVENDER: `3D4266` -> `7FCFB0`

---

## File map

```
skill-tekki-strategic-deck/
├── SKILL.md              — this file
├── template.js           — working pptxgenjs template
└── README.md             — installation instructions
```
