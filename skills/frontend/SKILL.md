---
name: frontend
description: "Use when building frontend UIs: \"build a landing page\", \"make a dashboard\", \"write a React component\", \"make it responsive\", \"fix accessibility\", \"add animations\". Design-first, production-grade, WCAG 2.1 AA baseline. Not for restyling or critique passes (use /impeccable)."
---

## Relationship with `ui-ux-pro-max`

When both `ui-ux-pro-max` and `frontend` could apply:
- `ui-ux-pro-max` **leads** on visual/interface decisions, design systems, color, typography, layout
- `frontend` **handles** component-level code quality, React patterns, state management, performance, accessibility implementation

Do not duplicate design decisions — implement what ui-ux-pro-max specifies.

# Frontend Design Skill

## Core Principles
- **Design-first thinking**: Consider visual hierarchy, spacing, and typography before writing code
- **Component architecture**: Build reusable, composable components
- **Performance**: Lazy load, minimize bundle size, optimize images
- **Accessibility**: WCAG 2.1 AA as baseline — semantic HTML, ARIA labels, keyboard navigation

## Stack Defaults (adjust to user's context)
- React + TypeScript
- Tailwind CSS for utility-first styling
- Framer Motion for animations
- Lucide React for icons

## Design System Checklist
- Consistent spacing scale (4px base unit)
- Limited color palette (primary, secondary, neutral, semantic)
- Typography scale (display, heading, body, caption)
- Interactive states for all clickable elements (hover, active, focus, disabled)

## Component Patterns

### Layout
```jsx
// Always use semantic HTML
<main>, <section>, <article>, <nav>, <aside>, <header>, <footer>
// Grid for 2D layouts, Flexbox for 1D
```

### Forms
- Label every input
- Show validation inline, immediately after interaction
- Clear error states with helpful messages

### Loading & Empty States
- Skeleton screens over spinners for content
- Always design the empty state — don't leave blank white space

## Code Quality
- Extract magic numbers to named constants
- Keep components under 200 lines — split if larger
- Co-locate styles with components
- Write self-documenting prop names

## Responsive Design
- Mobile-first: start with smallest viewport
- Breakpoints: sm (640), md (768), lg (1024), xl (1280)
- Test at 375px (iPhone SE) and 1440px (desktop)