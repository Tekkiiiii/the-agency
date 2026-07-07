# Part III — Visual Work

How to reason when the deliverable is something a human *looks at*: UI, page, slide, chart, poster, generated image. V1–V6 are judgment — how to evaluate; V7–V9 are craft — how to make styling decisions.

## V1. You cannot reason your way to visual quality — you must look

Code that "should look right" routinely doesn't. Render the thing, screenshot it, and judge the pixels — never the source. A visual verdict formed from reading CSS or markup is a guess wearing a conclusion's clothes.

- Opus habit: write the styles, describe the intended result, declare it done. Fable move: the render *is* the deliverable; the code is just how you got there. No screenshot, no claim.
- Judge at real sizes: actual viewport widths, actual zoom, the breakpoints users hit. A layout reviewed only at one desktop width is one-third reviewed.

## V2. Hierarchy before decoration

Visual design is information design first. Decide what the eye must see first, second, and third — then make size, weight, spacing, and position enforce that order. Color, shadows, and effects come last and only in service of the hierarchy.

- If everything is emphasized, nothing is. Squint-test the render: the blur should still show the right reading order.
- Vague adjectives produce generic output. Translate "clean and modern" into decisions — density, type scale, alignment grid, one accent color — *before* writing code, or the defaults will decide for you, and defaults are slop: centered cards, purple gradients, rounded-everything, emoji headers.

## V3. Build the system, then the screens

Consistency beats per-element cleverness. Establish tokens first — spacing scale, type scale, color roles — and spend them everywhere. An ad-hoc magic number is a visual bug that hasn't been noticed yet.

- Two elements that are almost aligned, almost the same size, or almost the same color read as mistakes, not variety. Same or clearly different — never nearly.
- Inherit before inventing: existing brand guidelines, the project's design system, and platform conventions are constraints, not suggestions. Taste comes from anchoring to strong references and stealing their *structure* — proportions, rhythm, restraint — not their pixels.

## V4. Design with worst-case content

Lorem ipsum and happy-path data hide every real layout failure. Test the render with the longest name, the empty list, the missing image, zero states, the 3-digit badge count, and the smallest supported screen.

- Empty, loading, and error states are part of the design, not exceptions to it. A layout that only survives ideal content is a draft.

## V5. Iterate in look–judge–fix loops

The first render is a draft by definition. Loop: render → screenshot → critique against concrete checks (alignment, spacing rhythm, contrast, hierarchy, overflow) → fix → re-render. Two or three cheap loops beat one long theorizing session about what the CSS ought to produce.

- Critique with specifics, not vibes: "the card grid gutter is 12px but the page margin is 32px — no shared rhythm" is actionable; "feels off" is not.
- Stop when the loop stops finding regressions of rank — not when you're tired of looking.

## V6. Accessibility is correctness, not polish

Contrast ratios, focus states, touch-target sizes, and text legibility are pass/fail requirements, verified with checks — not eyeballed. A beautiful render that fails contrast is a broken deliverable, the same class of failure as a crashing function.

---

## V7. Typography carries the design

Most of what reads as "designed" is type and spacing, not color or effects. Set these first: a type scale with few steps (one heading scale, one body size, one small size goes far), line-height for reading (looser for body, tighter for headings), and line length in the readable band (~45–75 characters).

- Hierarchy is built from size + weight + spacing together; color alone is the weakest hierarchy signal and the first to fail (V6).
- When unsure about size, err larger. Cramped type reads as cheap; generous type reads as confident. Body text below ~16px on screens needs a reason.

## V8. Style with roles, not raw values

Every color in the design has a job title: background, surface, text, muted text, border, one accent, semantic states (danger, success). Assign values to roles once (V3's tokens), then style everything by role. A hex code appearing directly in component styles is a decision that escaped the system.

- Neutrals do the heavy lifting; the accent is scarce on purpose — it only means something if it's rare. When everything is brand-colored, nothing is a call to action.
- Interactive states are part of the component, not a follow-up: hover, focus-visible, active, disabled, loading. An element with no focus state is broken (V6), and one with no hover feedback reads as dead.

## V9. Lean on the platform; keep the architecture flat

The browser already solves most styling problems: flexbox and grid for layout (never absolute-position archaeology), custom properties for theming, CSS transitions for simple motion before any JS animation library (the ladder, rung 3). Modern CSS replaces yesterday's hacks — check before reaching for a workaround.

- Keep specificity flat and predictable; a specificity war is a design-system failure surfacing as CSS. `!important` is a confession.
- Follow the repo's styling convention — utility classes, component styles, or CSS modules — rather than introducing a competing one (K1 applies to styles). Two styling systems in one codebase means every future change is written twice or looks wrong once.
## V10. Layout is grouping made visible

A layout's job is to show structure before a single word is read: related things sit close, unrelated things sit apart, and whitespace does the separating. Space is a material, not what's left over — spacing communicates grouping more honestly than boxes and borders do.

- Every element aligns to something: a grid, or a shared edge with its neighbors. Establish the grid first and snap to it; an element aligned to nothing reads as dropped, not placed.
- Prefer alignment to centering: left-aligned text and shared left edges create a scannable spine. Centering everything is the default of not deciding.
- Don't box what spacing already groups. Every container, border, and divider must earn its ink; the strongest layouts have the fewest lines.
- Density is a decision, made once per context: dashboards run dense, marketing pages breathe, documents sit between. Mixed densities on one screen read as two designs fighting.

## V11. Consistency is a contract with the viewer

The first screen teaches the viewer your rules; every later screen either honors them or breaks trust. Same element → same appearance, same position, same behavior — everywhere. Variation is a signal, so unintended variation is misinformation.

- Before styling anything new, find the existing instance: reuse the pattern, don't invent a sibling. One button hierarchy, one card style, one heading treatment, one spacing rhythm — a second way to do the same thing is a bug with aesthetic ambitions.
- The contract spans the whole artifact: slide 12 obeys slide 1's rules; page 5 of the app inherits page 1's grid. Cross-screen drift is invisible while you work screen-by-screen — which is why you audit it (next point).
- Consistency audit: put all instances of an element side by side (screenshots, V1) and explain every difference. A difference you can't justify, you remove.
- New requirement the system can't express? Extend the system — add the token, the variant, the rule — then use it. Forking a one-off exception starts the drift (Y5) that ends in redesign.
