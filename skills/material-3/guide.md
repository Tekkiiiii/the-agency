# Material 3 — Fit Criteria Guide

Use this guide to decide whether M3 is the right design system for a given project.

## Fit Criteria — Use M3

### Strong Fit (all conditions ideal for M3)

| Scenario | Why M3 fits |
|----------|------------|
| Android native app (Jetpack Compose) | M3 is the native design system for Android |
| Flutter app | Flutter Material library is M3-based |
| Google Workspace add-on or plugin | Inherits Google's Material aesthetic |
| Firebase console UI extension | Same Material codebase as Firebase console |
| Cross-platform app targeting Android + Web | M3 tokens map cleanly to both |
| App requiring WCAG 2.1 AA compliance | M3 color system is accessibility-first |
| App using `@material/web` web components | M3 is the source design system |
| Design file is a Material Figma Kit | Tokens are already M3-native |

### Moderate Fit (M3 as token source only)

| Scenario | How to use M3 |
|----------|--------------|
| React + shadcn/ui project | Use M3 color roles → shadcn CSS variables. See mappings/m3-to-shadcn.md |
| Tailwind CSS project | Use M3 color roles → Tailwind config. See mappings/m3-to-tailwind.md |
| Design-system-agnostic greenfield app | M3 tokens as semantic naming baseline |
| App where "clean/modern" is the brief | M3 shape + elevation + motion provides good defaults |

## Anti-Fit Criteria — Do NOT Use M3

| Project type | Why not |
|-------------|---------|
| Locked-brand project (e.g., has brand-guidelines.md) | Has its own brand-guidelines.md — never override |
| HTML plans or report files | html-plan-style skill provides locked palette — M3 overrides are forbidden |
| Projects with existing non-Material UI kits | Replacing Ant Design / Chakra / Spectrum mid-project causes churn |
| Clients who explicitly rejected Google aesthetic | Respect client brand decisions |
| Pure content/editorial sites | M3 is app-oriented — overkill for blogs/landing pages |

## Decision Checklist

Before applying M3 to a project, confirm:

- [ ] No locked brand guidelines that conflict with M3
- [ ] Not an html-plan-style document
- [ ] Target platform benefits from M3 (Android, cross-platform, Google-adjacent)
- [ ] Stack can use M3 as token source (even if not using Material web components)
- [ ] Design files are M3 Figma Kit OR will be rebuilt with M3 tokens

If any checkbox is unchecked, use M3 only as reference or skip entirely.

## Stack Compatibility Quick Reference

| Stack | M3 Mode |
|-------|---------|
| Jetpack Compose | Full M3 — use MaterialTheme directly |
| Flutter | Full M3 — use ThemeData.useMaterial3 |
| React Native + Material | Full M3 via react-native-paper |
| React + shadcn | Token source only — see mappings/m3-to-shadcn.md |
| React + Tailwind | Token source only — see mappings/m3-to-tailwind.md |
| React + @material/web | Full M3 web components — read anti-patterns.md first |
| Vue / Angular + @material/web | Full M3 web components — read anti-patterns.md first |
| Vanilla CSS | Use CSS custom properties — see mappings/m3-to-css-vars.md |
| Figma design file | Use Figma variables — see mappings/m3-to-figma.md |
