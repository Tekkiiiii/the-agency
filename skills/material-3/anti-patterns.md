# Material 3 — Anti-Patterns

What NOT to do when integrating M3.

---

## 1. Mixing @material/web Web Components Inside React/shadcn Projects

**Anti-pattern:**
```jsx
// DON'T do this in a React/shadcn project
import '@material/web/button/filled-button.js';
<md-filled-button>Submit</md-filled-button>
```

**Why it's wrong:**
- `@material/web` is a Web Components library — it does not integrate cleanly with React's virtual DOM
- Event handling, ref forwarding, and TypeScript types all require workarounds
- You get two component systems competing: shadcn's Radix primitives AND Material web components
- Bundle size doubles without proportional benefit

**Correct approach for React/shadcn:**
- Use M3 as a **token source only** — import color, typography, elevation, shape tokens
- Map M3 tokens to shadcn CSS variables (see `mappings/m3-to-shadcn.md`)
- Keep all components as shadcn/Radix components — just themed with M3 values

---

## 2. Overriding M3 Elevation with Custom Shadows

**Anti-pattern:**
```css
/* DON'T override M3 elevation with arbitrary custom shadows */
.my-card {
  box-shadow: 0 2px 8px rgba(0,0,0,0.3); /* custom value, not M3 */
}
```

**Why it's wrong:**
- Breaks the semantic elevation system — elevation level 2 cards and "2px shadow" cards are visually inconsistent
- Custom shadows don't adapt to dark mode (M3 elevation uses surface tint on dark, not just shadow)
- Design tokens lose their meaning when bypassed

**Correct approach:**
```css
/* Use the elevation token */
.my-card {
  box-shadow: var(--md-sys-elevation-level2-shadow); /* or however you've mapped it */
  /* AND add surface tint for dark mode */
  background-color: color-mix(in srgb, var(--md-sys-color-surface), var(--md-sys-color-primary) 8%);
}
```

---

## 3. Using @material/web as a Component Library in Non-Material Apps

**Anti-pattern:**
Importing `@material/web` buttons, text fields, chips into an app that already uses a different component library (Ant Design, Mantine, Chakra, Spectrum).

**Why it's wrong:**
- Two component libraries = doubled CSS specificity conflicts
- Accessibility roles may conflict (two aria implementations for the same element)
- Maintenance nightmare — breaking changes in either library affect everything

**Correct approach:**
- Pick one component library. Use M3 only for its design tokens, not its components.
- If the brief requires Material components: commit to `@material/web` or a Material-native framework (Flutter, Jetpack Compose). Don't mix.

---

## 4. Treating M3 as a Complete Drop-In for Existing Token Systems

**Anti-pattern:**
Replacing an existing token system (e.g., a client's brand tokens) wholesale with M3.

**Why it's wrong:**
- The client's brand tokens encode business decisions and accessibility requirements specific to their brand
- M3 color roles don't map 1:1 to most brand token systems
- M3's "primary" is not necessarily the client's "brand-primary"

**Correct approach:**
- Map the client's brand tokens TO M3 roles (e.g., brand-primary → M3 primary)
- Keep the client's token names as the public API; use M3 roles as semantic aliases internally

---

## 5. Hardcoding M3 Values Instead of Using Token References

**Anti-pattern:**
```css
/* DON'T hardcode M3 token values */
.headline {
  font-size: 32px;  /* hard-coded, from headline-large */
  font-weight: 400;
}
```

**Why it's wrong:**
- Loses the ability to update the design system globally
- Breaks theme switching (light/dark, dynamic color)
- Reviewer can't tell this is an M3 token without documentation

**Correct approach:**
```css
/* Reference the token */
.headline {
  font-size: var(--md-sys-typescale-headline-large-size);
  font-weight: var(--md-sys-typescale-headline-large-weight);
}
```

---

## 6. Applying M3 to html-plan-style Documents

**Anti-pattern:**
Adding M3 color tokens or typography to HTML plan files that use the html-plan-style skill.

**Why it's wrong:**
- html-plan-style has a locked palette and typography system
- M3 overrides would break consistency across all plan documents
- Plans are internal artifacts, not product UIs

**Rule:** html-plan-style is explicitly excluded from M3 scope. Never mix.

---

## 7. Applying M3 to Locked-Brand Projects (e.g., a locked-brand project)

**Anti-pattern:**
Using M3 color roles or type scale on any project that has a `memory/brand-guidelines.md`.

**Why it's wrong:**
- Brand guidelines encode deliberate decisions (brand identity, market positioning)
- M3's "primary" color is not your brand color
- Overrides brand consistency across all deliverables

**Rule:** If a project has `memory/brand-guidelines.md`, read it and follow it. M3 is reference only — never applied.
