---
name: frontend
description: >
  Frontend design system and implementation — applies a consistent design
  language to web projects using React + Tailwind conventions. Covers
  typography scale, color tokens, spacing system, component patterns, and
  responsive breakpoints. Trigger when: building a new UI from scratch,
  implementing a design system, or refactoring frontend code to match
  existing patterns. Key capability: design token system that's consistent
  with gstack conventions. Also for: auditing existing frontend code for
  design system compliance, and scaffolding new components.
---

# /frontend — Frontend Design System

Consistent frontend design language using React + Tailwind.

## When to Activate

Trigger `/frontend` when:
- Building UI from scratch
- Implementing a design system
- Refactoring frontend code
- Auditing frontend for design system compliance
- Scaffolding new components

## Design Token Conventions

### Color Palette

```
COLORS — {project}
════════════════════════════════

Brand:
  --color-primary:       #3B82F6  (blue-500)
  --color-primary-dark:  #1D4ED8  (blue-700)
  --color-primary-light: #93C5FD  (blue-300)

Neutral:
  --color-bg:            #FFFFFF
  --color-surface:       #F9FAFB  (gray-50)
  --color-border:        #E5E7EB  (gray-200)
  --color-text:          #111827  (gray-900)
  --color-text-muted:    #6B7280  (gray-500)

Semantic:
  --color-success:       #10B981  (emerald-500)
  --color-warning:       #F59E0B  (amber-500)
  --color-error:         #EF4444  (red-500)
  --color-info:          #3B82F6  (blue-500)
```

### Typography Scale

```
TYPOGRAPHY — {project}
════════════════════════════════

Font family:
  Sans:   Inter, system-ui, sans-serif
  Mono:   JetBrains Mono, Menlo, monospace
  Display: Inter (weight 700+)

Scale (rem):
  xs:   0.75rem   / 1rem       (12px)
  sm:   0.875rem  / 1.25rem    (14px)
  base: 1rem      / 1.5rem      (16px)
  lg:   1.125rem  / 1.75rem    (18px)
  xl:   1.25rem   / 1.75rem    (20px)
  2xl:  1.5rem    / 2rem        (24px)
  3xl:  1.875rem  / 2.25rem    (30px)
  4xl:  2.25rem   / 2.5rem      (36px)

Weights: 400 (normal), 500 (medium), 600 (semibold), 700 (bold)
```

### Spacing System

```
SPACING — {project}
════════════════════════════════

Base unit: 4px (Tailwind default)

Scale:
  0:    0px
  1:    4px     (0.25rem)
  2:    8px     (0.5rem)
  3:    12px    (0.75rem)
  4:    16px    (1rem)
  5:    20px    (1.25rem)
  6:    24px    (1.5rem)
  8:    32px    (2rem)
  10:   40px    (2.5rem)
  12:   48px    (3rem)
  16:   64px    (4rem)
  20:   80px    (5rem)
  24:   96px    (6rem)
```

### Breakpoints

```
BREAKPOINTS — {project}
════════════════════════════════

Mobile:   < 640px   (sm)
Tablet:   640-768px (md)
Laptop:   768-1024px (lg)
Desktop:  1024-1280px (xl)
Wide:     1280px+   (2xl)

Tailwind prefixes:  sm:, md:, lg:, xl:, 2xl:
```

## Component Patterns

### Button

```tsx
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost' | 'danger';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}

// Variants:
// primary:   bg-blue-600 text-white hover:bg-blue-700
// secondary: bg-gray-100 text-gray-900 hover:bg-gray-200
// ghost:     bg-transparent text-gray-700 hover:bg-gray-100
// danger:    bg-red-600 text-white hover:bg-red-700

// Sizes:
// sm: px-3 py-1.5 text-sm
// md: px-4 py-2 text-base
// lg: px-6 py-3 text-lg
```

### Input

```tsx
interface InputProps {
  label?: string;
  error?: string;
  helper?: string;
  type?: 'text' | 'email' | 'password' | 'number';
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

// Structure:
// label (block text-sm font-medium text-gray-700)
// input (block w-full rounded-md border border-gray-300 px-3 py-2)
// error (mt-1 text-sm text-red-600)
// helper (mt-1 text-sm text-gray-500)
```

### Card

```tsx
// Container
<div className="bg-white rounded-lg border border-gray-200 shadow-sm">
  // Header (optional)
  <div className="px-6 py-4 border-b border-gray-200">
    <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
  </div>
  // Body
  <div className="px-6 py-4">
    {children}
  </div>
</div>
```

## Accessibility (WCAG 2.1 AA)

```
ACCESSIBILITY CHECKLIST — {project}
════════════════════════════════

Color contrast:
  □ Text on background: minimum 4.5:1
  □ Large text (18pt+): minimum 3:1
  □ UI components: minimum 3:1

Keyboard navigation:
  □ All interactive elements focusable
  □ Focus order is logical
  □ Focus is visible (not just outline:none)

Screen readers:
  □ Images have alt text
  □ Forms have labels
  □ Buttons have accessible names
  □ Dynamic content has aria-live regions

Touch targets:
  □ Minimum 44x44px touch target
  □ Adequate spacing between targets
```

## Important Rules

- **Use design tokens, not magic values.** `bg-primary` not `#3B82F6`.
- **Consistent spacing only.** Use the 4px scale — no arbitrary values.
- **Mobile first.** Write styles for mobile, add breakpoints for larger screens.
- **Accessibility is not optional.** WCAG AA compliance is the minimum.
- **Components do one thing.** A Button component is just a button — not a button + icon + loading state combo.
