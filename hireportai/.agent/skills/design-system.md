---
description: Theme tokens, multi-theme switching, Tailwind integration, no-flash init
---
# Design System Skill

## Overview
All styling in `hirelens-frontend` is driven by **design tokens** that
emit CSS variables to `:root`. Tailwind reads those variables through
a small helper so utility classes stay theme-aware. Three themes ship
out of the box and the user can switch at runtime from the settings
page; their choice is persisted in `localStorage` and re-applied
**before** React mounts so there is no flash of wrong theme.

## Key Files
- `src/styles/design-tokens.ts` — token definitions + `applyTheme()`
- `src/context/ThemeContext.tsx` — `ThemeProvider`, `useTheme()` hook
- `src/components/settings/ThemePicker.tsx` — UI picker
- `tailwind.config.ts` — rgb() helper mapping utilities to vars
- `src/main.tsx` — calls `applyInitialTheme()` pre-render

## Themes
Exactly three themes, each exports a `vars` object keyed by CSS var:

| Theme | id | Base | Accent |
|-------|----|------|--------|
| Dark (default) | `dark` | near-black (#0A0A0B) | red #DC2626 |
| Light | `light` | white | red #DC2626 |
| Midnight Blue | `midnight-blue` | deep navy | blue #3B82F6 |

`DEFAULT_THEME_ID = 'dark'`.

## Token Categories
Every theme sets the same keys. Shared (non-theme) tokens live in a
separate constant and are merged in by `applyTheme()`.

- **Colors** (dual-emission: hex + space-separated RGB triple so
  Tailwind can do `bg-accent-primary/50`):
  `--bg-base`, `--bg-surface`, `--bg-elevated`, `--bg-overlay`,
  `--accent-primary`, `--accent-secondary`, `--accent-glow`,
  `--text-primary`, `--text-secondary`, `--text-muted`,
  `--success`, `--warning`, `--danger`,
  `--border`, `--border-accent`,
  `--color-score-high|mid|low`
- **Typography:** scale `xs` 12 → `4xl` 36; display/body/mono
  font-family vars under `--sf-font-*`.
- **Spacing:** 4 px increments `[4, 8, 12, 16, 20, 24, 32, 40, 48, 64]`
  exposed as `--sf-space-xs`…`--sf-space-4xl`.
- **Border radius:** `sm` 4 / `md` 8 / `lg` 12 / `xl` 16 / `full` 9999.
- **Shadows:** `sm`, `md`, `lg`, plus app-specific `card`, `card-hover`,
  `modal`, `depth`, `depth-hover`, `glow`, `glow-lg`, `glow-xl`.
- **Transitions:** `--sf-duration-fast` 150 ms, `normal` 250 ms,
  `slow` 350 ms; easing `--sf-ease-out`, `--sf-ease-spring`.

## `useTheme()` Hook
```tsx
import { useTheme } from '@/context/ThemeContext'

const { theme, setTheme, themes } = useTheme()
setTheme('midnight-blue')
```
- Persists to `localStorage` under key **`sf-theme`**.
- Fires PostHog event `theme_changed` with `{from_theme, to_theme}`.

## No-Flash Initialization
`src/main.tsx` calls `applyInitialTheme()` **before** ReactDOM renders.
That function:
1. Reads `localStorage['sf-theme']` synchronously.
2. Falls back to `DEFAULT_THEME_ID` on any error (quota, unavailable).
3. Calls `applyTheme(id)` which sets all CSS variables on `:root`.
Result: the first paint already has the correct colors.

## Tailwind Integration
`tailwind.config.ts` wires CSS variables into Tailwind's color system
through a helper:

```ts
function rgb(varName: string) {
  return `rgb(var(--color-${varName}) / <alpha-value>)`
}
// example usage in config
colors: {
  'bg-base':        rgb('bg-base'),
  'accent-primary': rgb('accent-primary'),
  // ...
}
```

That means every utility class — `bg-bg-base`, `text-text-secondary`,
`border-border-accent` — automatically reflects the current theme,
**and** opacity modifiers like `bg-accent-primary/40` work because
the variable holds an RGB triple, not a hex.

## ThemePicker Component
`src/components/settings/ThemePicker.tsx` renders a 3-card grid:
theme name + five color swatches (base / surface / accent-primary /
accent-secondary / text-primary). Clicking a card calls `setTheme()`
and highlights the active card with a check. Mobile: 1 col; desktop: 3.

## Rules
- **Never hardcode hex values** in components or Tailwind classes.
  Use semantic utilities backed by tokens
  (`bg-bg-surface`, `text-text-primary`, `border-border-accent`).
- If you need a new color, add it to **all three themes** in
  `design-tokens.ts` and wire it through the Tailwind config.
- New shared tokens (spacing, radius, shadow) go in the shared
  constant, not per-theme.
- Animations/motion should consume `--sf-duration-*` and
  `--sf-ease-*` vars so they stay consistent across themes.
