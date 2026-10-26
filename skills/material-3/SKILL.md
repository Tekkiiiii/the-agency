# Material 3 Skill

Resource skill: Material Design 3 (M3) design system tokens and integration rules.
Source: https://m3.material.io
License: Apache 2.0

## Trigger Phrases

Invoke this skill when the task contains any of:
- "use M3"
- "Material Design"
- "Material 3"
- "M3 tokens"
- "M3 colors" / "M3 typography" / "M3 elevation" / "M3 shape"
- "md3" (case-insensitive)
- Building Android UI
- Building cross-platform UI with Material Design compliance
- "shadcn with Material" / "Tailwind Material tokens"

## When to Use

Use this skill as a TOKEN SOURCE when:
- Building Android native UI (Jetpack Compose, XML)
- Building cross-platform apps where M3 is the design system (Flutter, Ionic with Material)
- Building web apps adjacent to Google products (Google Workspace add-ons, Firebase console UIs)
- Implementing Material Web Components (`@material/web`)
- Mapping design tokens from Figma Material Kit to code
- Configuring shadcn/ui theme variables to M3 roles
- Configuring Tailwind CSS with M3 color tokens

## When NOT to Use

Do NOT apply M3 when:
- The project has a locked brand (e.g. a project with a locked brand identity)
- The project uses html-plan-style (plans/reports use a locked CSS palette — never override)
- The stack is already committed to a non-Material design system (Ant Design, Chakra, Spectrum)
- The brief explicitly says to avoid Google/Material aesthetic
- The component library (shadcn, etc.) is already themed with custom tokens that conflict

When in doubt: use M3 as a reference only, not as direct implementation.

## What This Skill Provides

Paths under `{agency-root}/skills/material-3/`:

```
tokens/
  color-tokens.md        — 29 color role tokens with naming conventions
  type-scale-tokens.md   — 15 type scale tokens (5 roles × 3 sizes)
  elevation-tokens.md    — 6 elevation levels + surface tint + motion
  shape-tokens.md        — 7 shape scale tokens

mappings/
  m3-to-tailwind.md      — M3 color roles → Tailwind CSS config
  m3-to-shadcn.md        — M3 roles → shadcn CSS variables
  m3-to-css-vars.md      — M3 → raw CSS custom properties
  m3-to-figma.md         — M3 → Figma variable structure

guide.md                 — Fit/anti-fit criteria
anti-patterns.md         — What NOT to do
SKILL.md                 — This file
```

## Usage Protocol

1. Read `guide.md` to confirm M3 is the right fit for the project
2. Read the relevant `tokens/*.md` for the token categories you need
3. Read the relevant `mappings/*.md` for your stack
4. Apply tokens — never hardcode values; always reference token names
5. For React/shadcn projects: use M3 as token source only, NOT component library

## References

- Material Design 3: https://m3.material.io
- Material Theme Builder: https://m3.material.io/theme-builder
- Material Web Components: https://github.com/material-components/material-web
- Figma Material Kit: https://www.figma.com/community/file/1035203688168086460
