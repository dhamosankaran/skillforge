---
slice: P5-S55 (spec + impl)
base_sha: 7ca2e90
drafted: 2026-04-23
backlog: B-030
---

# SPEC: Re-Analyse Paywall Gate on Analysis Results

## Status: Draft

## Problem

The "Re-analyze" button on `/prep/results` (`src/pages/Results.tsx:154-157`) is a pure client-side `navigate('/prep/analyze')` with no plan check. A free user who has just finished their first analysis can re-run the full JD-match pipeline (token-expensive LLM calls) an unlimited number of times — up to `useUsage().canScan` which allows 3 scans before the `Analyze` page gates.

`Results.tsx` already mounts a `<PaywallModal>` instance with a dead-code `showPaywall` state (line 49, 445-449) — the setter is never called. The scaffolding is in place; only the wiring is missing.

Walkthrough evidence (Enhancements.txt 2026-04-22): the revenue-surface regression on `/prep/results` covers two buttons — Optimize (`/prep/rewrite`) and Re-analyze. This spec covers Re-analyze only. Optimize is a parallel gap tracked separately.

## Solution

Gate the Re-analyze button on plan:

- **Free user** (`useUsage().canUsePro === false`): click opens the existing `PaywallModal` with trigger `scan_limit`. The existing `scan_limit` copy fits ("You've hit your free scan limit" / "You've used all your free ATS scans. Upgrade to Pro for unlimited scans..."). No new trigger type is introduced.
- **Pro user** (`canUsePro === true`): click navigates to `/prep/analyze` as today.

Dead-code `showPaywall` state is wired up. The hardcoded `trigger="skill_gap_study"` on the `PaywallModal` instance is replaced by a state-driven `paywallTrigger` so the same modal instance can serve multiple gating sites within the page (future Optimize-button slice can reuse it).

## Acceptance Criteria

- **AC-1** — Free user click → `PaywallModal` opens with trigger `scan_limit` and does NOT navigate. Verified by a Vitest test that stubs `useUsage` with `canUsePro: false` and `useNavigate`, clicks the Re-analyze button, and asserts the modal headline "You've hit your free scan limit" renders and `navigate` was not called.
- **AC-2** — Pro user click → `navigate('/prep/analyze')` fires and the modal does NOT render. Verified by a Vitest test with `canUsePro: true` that asserts `navigate('/prep/analyze')` was called once and the modal headline is absent.
- **AC-3** — PostHog event `re_analyze_clicked` fires on every Re-analyze click with properties `{plan: 'free' | 'pro'}`, before the gate resolves (so both blocked and allowed clicks are counted). Verified by a Vitest test that stubs `capture` and asserts the exact payload for both plan states.
- **AC-4** — No regression to existing Results tests (240 → 240+N passing after adding the new tests).

## API Contract

None. Uses the existing `/api/v1/payments/checkout` flow via the unchanged `PaywallModal` → `createCheckoutSession` path.

## Data Model Changes

None.

## Plan Detection

Reuses `useUsage().canUsePro` — the same surface that spec #22's `missingSkillsPlan` derivation composes. No new plan-detection mechanism.

## Analytics

- **New frontend event: `re_analyze_clicked`** — properties `{plan: 'free' | 'pro'}`. Fires on every click of the Re-analyze button on `/prep/results`, regardless of gate outcome. Catalogued in `.agent/skills/analytics.md`.
- Existing `paywall_hit` fires from `PaywallModal` on modal open with trigger `scan_limit` (unchanged).

## Out of Scope

- Optimize button (`/prep/rewrite`) paywall gate — same revenue-surface concern, separate slice.
- Backend scan-quota enforcement — already exists in `app/services/usage_service.py` (free-tier scan cap). This spec is UI-only.
- Win-back / dismissal telemetry — E-014 dismissal wiring already extends to any `PaywallModal` instance.

## R14 Classification

Pure bug-fix / revenue-regression closure. The scaffolding (`showPaywall` state, `PaywallModal` mount) already exists in `Results.tsx` but is not wired. No design surface beyond trigger-type selection (reuses existing `scan_limit`). Matches the pattern used for B-015, B-027, B-028, B-029 (R14 exception (b)).
