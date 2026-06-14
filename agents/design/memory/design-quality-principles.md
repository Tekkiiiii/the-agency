# Design Quality Principles — Agency Reference

**Source:** Research synthesis (IxDF, NNG, Material Design, conversion optimization research + internal synthesis)
**Audience:** critique-design, critique-brand, design agents, ad copywriters, social content creators

---

## 1. Visual Hierarchy

**Core rule:** If the eye leaves the page before reaching the CTA, the design has failed regardless of how beautiful it is.

### Three Dominance Tiers
- **Tier 1 — Dominant (60-70% visual weight):** The single most important element. Usually the headline or hero image. Must win every visual competition on the page.
- **Tier 2 — Sub-dominant (20-30% visual weight):** Supporting elements (subheadline, social proof, product image). Reinforces Tier 1 without competing.
- **Tier 3 — Subordinate (10% visual weight):** Body copy, captions, fine print. Legible but never draws the eye from Tier 1 or 2.

### Five Hierarchy Tools
- **Size:** Headline must be largest. 3:1 ratio minimum — header to body text.
- **Contrast:** Dark on light OR light on dark. Never mid-tones against mid-tones.
- **White space:** Space around an element increases perceived importance. CTA: minimum 16px padding, 24px preferred.
- **Proximity:** Related elements cluster. Unrelated elements separate. Gestalt proximity = brain-readable grouping.
- **Position:** Top-left starts the eye journey (LTR cultures). Critical elements belong above the fold.
- **Directional cues:** Arrows, faces looking at CTA, flow lines guide the eye to the conversion point.

### 3-Second Rule
A viewer decides in 3 seconds whether to engage. The dominant element must communicate the core value proposition within that window.

---

## 2. Color Theory

### 60-30-10 Rule — Non-negotiable for all marketing assets
- **60% — Dominant brand color:** Backgrounds, large surfaces.
- **30% — Secondary color:** Sections, cards, supporting areas.
- **10% — Accent color:** CTAs, highlights, key data points ONLY.

### Hard Contrast Rules
| Rule | Standard | Why it matters |
|------|----------|----------------|
| Minimum contrast ratio | 4.5:1 (WCAG AA) | Legal compliance + readability |
| Avoid pure black on pure white | Use #1a1a1a on #F8F8F8 | Pure #000 on #FFF causes eye strain |
| Text over images | Always add overlay or shadow | Background images behind text almost always fail contrast checks |
| Brand color drift | Always use exact hex codes | Eyeballing colors erodes brand equity |

---

## 3. Typography

**Max 2 typefaces per asset.** A display/serif for headlines and a sans-serif for body.

### Scale and Sizing
| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Ad headline / Hero title | 36-48px+ | Bold (700) | Must win the hierarchy. 3:1 ratio to body. |
| Section headline (web) | 24-36px | Bold (700) | Display or serif preferred |
| Subheadline | 18-22px | Semi-bold (600) | Sans-serif |
| Body copy | 16-18px | Regular (400) | **Never below 16px for screen-read content** |
| Labels / captions / badges | 12-14px | Bold (700) | All-caps acceptable at this size only (max 4 words) |
| Fine print / legal | 10-12px | Regular | Never below 10px |

### Readability Rules
- **Line height:** Body copy 1.5x font size minimum. Headlines 1.1-1.25x.
- **Line length:** Desktop 60-80 characters per line. Mobile 30-40 characters.
- **All-caps rule:** All-caps only for labels/badges of 4 words or fewer.

---

## 4. Layout Principles

### Scan Patterns
- **F-Pattern — Long-form / Web pages:** Users make two horizontal sweeps across the top, then a vertical drop down the left edge.
- **Z-Pattern — Ads and sparse layouts:** Top-left → top-right → diagonal → bottom-left → bottom-right.

### 8-Point Grid System — Mandatory for all agency assets
All padding, margins, and spacing values must be multiples of 8px (8, 16, 24, 32, 48, 64, 96px).

### Rule of Thirds
Divide canvas into 3x3 grid. Place key elements at intersection points — not dead center.

---

## 5. Conversion-Oriented Design

### Above-the-Fold Requirements
- Benefit-led headline (what the user gets, not what you do)
- Subheadline that answers "how" in one sentence
- Visual proof (product image, result screenshot, or social proof number)
- Primary CTA button — visible, high-contrast, action verb + outcome

### CTA Design Rules
- Minimum touch target: 44px x 44px (mobile accessibility)
- Minimum padding: 16px horizontal, 12px vertical
- CTA breathing room: 24px whitespace on all sides
- Maximum 2 CTAs per page
- Use brand's accent color exclusively for primary CTA

**CTA copy:**
- Action verb + outcome: "Start Free Trial" beats "Submit"
- First person: "Get My Report" outperforms "Get Your Report" in most tests
- Avoid generic verbs: Submit, Click Here, Go, Enter

---

## 6. Social Media and Carousel Design

### Format Specifications
| Format | Dimensions | Notes |
|--------|------------|-------|
| Instagram/LinkedIn carousel (square) | 1080 x 1080px | Default carousel format |
| Instagram/LinkedIn carousel (portrait) | 1080 x 1350px (4:5) | More screen real estate |
| Instagram/TikTok Stories/Reels | 1080 x 1920px (9:16) | Vertical video |
| Facebook feed post | 1200 x 630px | Link preview standard |
| LinkedIn single image | 1200 x 627px | Feed display standard |

### Text Coverage Rule
Maximum 20% of slide area covered by text.

### Social-Specific Rules
- Design for mobile-first
- Safe zones: keep critical text 80px from all edges
- Font minimum 40px on social graphics
- Test designs at thumbnail size (150px) before finalizing

---

## 7. Brand Consistency

### Brand Consistency Failures — The 6 Common Failures
| Failure mode | Fix |
|---|---|
| **Color drift** | Store hex codes in brand file; never eyeball |
| **Font substitution** | Embed fonts or maintain a font kit; verify on export |
| **Logo distortion** | Always constrain proportions |
| **Rogue gradients** | Follow brand guidelines; when in doubt, stay flat |
| **Spacing inconsistency** | Enforce 8-point grid across all templates |
| **Off-brand photography** | Maintain curated approved image library |

---

## 8. Common Design Mistakes (The Amateur Mark List)

These patterns signal inexperience and actively reduce conversion rates. Design QA must catch all of these before delivery.

1. **Inconsistent spacing** — Fix: 8-point grid, no exceptions.
2. **Competing visual weights** — Dominant element must win at 60-70%.
3. **Low contrast text** — Text below 4.5:1 contrast fails WCAG AA.
4. **Wall of text (F-pattern trap)** — Break up with subheadings, bullets, and bold phrases.
5. **Weak CTA copy** — CTAs need action verbs and outcome language.
6. **Too many CTAs** — Maximum 2 CTAs per page.
7. **Overcrowded layouts** — One message per ad. One value point per carousel slide.
8. **Ad "look"** — Native-feeling content gets more attention.

---

## 9. Design QA Checklist (Pass/Fail)

Use before any marketing asset is approved for delivery. Any unchecked item is a HIGH blocker.

### Visual Hierarchy
- [ ] Dominant element holds 60-70% visual weight
- [ ] Headline is the largest text element
- [ ] CTA is visually distinct from all other elements
- [ ] Eye journey leads to CTA without escape

### Color
- [ ] Brand hex codes used (not approximations)
- [ ] 60-30-10 ratio maintained
- [ ] All text passes 4.5:1 contrast minimum
- [ ] CTA uses accent color exclusively

### Typography
- [ ] Maximum 2 typefaces used
- [ ] Body text minimum 16px
- [ ] Line height minimum 1.5x for body
- [ ] All-caps only for labels, 4 words max

### Layout
- [ ] 8-point grid applied to all spacing
- [ ] Critical content above the fold
- [ ] CTA has 24px breathing room on all sides

### Social Media
- [ ] Correct dimensions for target platform
- [ ] Text covers less than 20% of slide area
- [ ] Fonts minimum 40px at design size
- [ ] Verified at thumbnail size (150px)

### Brand Consistency
- [ ] Logo at correct aspect ratio (no distortion)
- [ ] Hex codes verified against brand guidelines
- [ ] Photography matches brand image style

---

**Delivery standard:** An asset that fails any item in Visual Hierarchy, Color, or Typography must be revised before delivery.
