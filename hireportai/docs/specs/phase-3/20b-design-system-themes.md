# SPEC: Design System + 3 Themes + ThemePicker

## Status: Implemented — Spec Backfill Pending (P5-S2)

## Code Pointers
- Tokens: `src/styles/design-tokens.ts` (TS source with `applyTheme()` helper) + `src/styles/design-tokens.css` (CSS variable outputs for `:root[data-theme="..."]`).
- Theme state: `src/context/ThemeContext.tsx` (exports `ThemeProvider` + `useTheme()` hook). The playbook-envisioned `src/hooks/useTheme.ts` standalone hook does NOT exist — the hook is exported from the context file.
- Picker UI: `src/components/settings/ThemePicker.tsx`.
- Pre-render theme application: `src/main.tsx` calls `applyInitialTheme()` before React mounts (no FOUC).
- Tailwind integration: `tailwind.config.ts` maps utilities like `bg-bg-surface`, `text-text-primary`, `border-border-accent` to the RGB-triple CSS vars.
- Skill file: `.agent/skills/design-system.md` (already accurate; mirrors this architecture).

## Themes Shipped
| id | Base | Accent |
|----|------|--------|
| `dark` (default) | near-black #0A0A0B | red #DC2626 |
| `light` | white | red #DC2626 |
| `midnight-blue` | deep navy | blue #3B82F6 |

## Problem
*(to be filled in during P5-S2 backfill)*

## Solution
*(to be filled in during P5-S2 backfill)*

## Acceptance Criteria
*(to be filled in during P5-S2 backfill — include contrast/a11y checks)*

## Divergence from Original Spec
- No `src/styles/themes.css` file. Token system is TS-first with CSS output.
- No standalone `src/hooks/useTheme.ts`. Hook exported from `ThemeContext.tsx`.

---
*Placeholder created during P5-S0b on 2026-04-17. Replace with full spec during P5-S2.*
