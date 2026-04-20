---
slice: P5-S21a (spec) + P5-S21b (impl)
base_sha: b0a7c0e
drafted: 2026-04-19
---

# SPEC: Analysis Results — Keyword Color Fix + Education Layer

## Status: Draft

## Problem

Two user problems on `/prep/results` (the Analysis Results page after an ATS scan):

1. **Keyword color legend doesn't match what users see.** The "Keyword Frequency Analysis" legend claims three colors (Matched / Missing / In resume), but the bars on the chart render with different colors — most obviously, the "In resume" bars render as hardcoded violet (`#7c3aed`) that is never the value of `--accent-secondary` in any of the three themes. This is a trust-breaker: the first data-viz a user sees after paying attention to our product disagrees with its own legend.

2. **No education layer.** Users land on a dense results page with many numeric signals (ATS score, score breakdown, skill overlap radar, bullet analysis, formatting issues, improvement suggestions) and no guidance on what each means, how to act on it, or why it matters. Four sections have tooltips today; five don't. The tooltip that exists is also not fully accessible (no keyboard dismiss, no click-outside, no `role="tooltip"`, no `aria-describedby`).

## Solution

1. **Fix the keyword color mismatch** by replacing the hardcoded violet in `KeywordChart.tsx` with the `--color-accent-secondary` design-token value, and align the legend swatch opacities to the chart cell opacities (or vice-versa — fix in one direction). Root cause documented in "Bug Analysis" below.

2. **Add info tooltips on every major section header** using the existing `PanelSection` tooltip primitive, hardened for accessibility (Escape-dismiss, click-outside, keyboard-reachable, `role="tooltip"`, `aria-describedby`). Each tooltip shows three-line what-this-means / how-to-act / why-it-matters copy drafted in §Education Layer Design below.

## Bug Analysis (Keyword Color Mismatch)

**Classification: CAUSE-2 — className / token-string mismatch (theme-aware variant).**

**Legend** (`hirelens-frontend/src/pages/Results.tsx:292-302`):

```tsx
<span className="w-2 h-2 rounded-sm bg-success/70" />Matched
<span className="w-2 h-2 rounded-sm bg-danger/40" />Missing
<span className="w-2 h-2 rounded-sm bg-accent-secondary/50" />In resume
```

**Chart rendering** (`hirelens-frontend/src/components/dashboard/KeywordChart.tsx:73-83`):

```tsx
<Bar dataKey="jd_count" name="In JD" ...>
  {chartData.map((entry, i) => (
    <Cell
      fill={entry.matched ? success : `${danger}40`}       // success CSS var / danger + hex-alpha 0x40
      stroke={entry.matched ? `${success}80` : `${danger}60`}
    />
  ))}
</Bar>
<Bar dataKey="resume_count" name="In Resume" fill="rgba(124,58,237,0.5)" />  // ← hardcoded violet
```

**Trace table:**

| class / value | Legend claims | Actually applied when | Correct? |
|---|---|---|---|
| `bg-success/70` | "Matched" | Bar 1 cell fill `success` (full opacity) when `entry.matched === true` | ⚠️ Opacity mismatch (legend 70%, chart 100%) |
| `bg-danger/40` | "Missing" | Bar 1 cell fill `${danger}40` (hex-alpha 0x40 ≈ 25%) when `entry.matched === false` | ⚠️ Opacity mismatch (legend 40% Tailwind-alpha, chart ~25% hex-alpha) |
| `bg-accent-secondary/50` | "In resume" | Bar 2 (`resume_count`) fill hardcoded `rgba(124,58,237,0.5)` (violet `#7c3aed`) | ❌ Hue mismatch — violates CLAUDE.md R12; `--accent-secondary` is `#EF4444` (Dark, Light) or `#60A5FA` (Midnight Blue), never violet |

**Why it ships broken:** the legend and the chart were written to different style sources (Tailwind token classes vs. inline hex). The "In resume" bar's hardcoded hex was never corrected to the design token, so it diverged silently from the legend across all three themes. CLAUDE.md R12 ("Never hardcode a hex value") would have caught this at review time.

## Proposed Fix (Keyword Colors)

Two coordinated edits in `hirelens-frontend/src/components/dashboard/KeywordChart.tsx`:

1. **"In resume" bar — use the design token.** Replace line 83's `fill="rgba(124,58,237,0.5)"` with a value derived from `--color-accent-secondary` (space-separated RGB already emitted by `design-tokens.ts`). Read it at render time alongside the existing `success` / `danger` / `textMuted` reads at lines 38-41:

    ```tsx
    const accentSecondary = s.getPropertyValue('--color-accent-secondary').trim()
    // …
    <Bar dataKey="resume_count" name="In Resume"
         fill={`rgba(${accentSecondary.replaceAll(' ', ',')}, 0.5)`} ... />
    ```

    (Pattern: `--color-accent-secondary` is `"239 68 68"` / `"96 165 250"` depending on theme; splitting → `rgb()` form + 0.5 alpha matches the legend's `bg-accent-secondary/50` Tailwind rendering.)

2. **Match opacities on matched/missing.** Either:
    - **Option A (adopt chart's opacities in the legend):** change legend to `bg-success` (no `/70`) and `bg-danger/25` to mirror the chart cells' actual opacity.
    - **Option B (adopt legend's opacities in the chart):** change Bar 1 cell fills to `rgba(<success-rgb>, 0.7)` / `rgba(<danger-rgb>, 0.4)` to mirror the legend swatches.

    **Preferred: Option A.** The legend is a visual reference; aligning it to the chart means we don't visually dim the bars on the chart (which are the primary signal). Option A is also a one-file edit in `Results.tsx` and doesn't require rewriting the `KeywordChart.tsx` cell logic.

3. **Extract legend into a constant** so the legend text and the chart coloring reference the same source of truth (a single `KEYWORD_LEGEND` constant in `KeywordChart.tsx`, exported and imported by `Results.tsx`). Prevents future drift.

**Verification:** new Vitest case `test_keyword_legend_colors_match_chart_cells` renders a fixture with one matched + one missing + one resume-only keyword, queries the three legend swatches and the three Cell fills, and asserts string equality on the computed `fill` values. Run across all three themes via `applyTheme()` before render.

## Education Layer Design

Tooltip copy — three-line structure per section. Each cell ≤ 12 words. Draft copy; the review of this spec is the copy review.

| Section header | What this means | How to act on it | Why it matters |
|----------------|-----------------|------------------|----------------|
| ATS Score | Estimated resume-to-JD match strength, 0–100. | Aim for 75+ before applying; under 60 needs rewrite. | Filters auto-reject below a recruiter-set cutoff, often 70. |
| Score Breakdown | Which dimensions (keywords, skills, format) drove your score. | Target the lowest bar first; biggest score gain per edit. | Shows *why* your score is what it is, not just the number. |
| Job Fit Explanation | AI summary of how your experience maps to the role. | Read the gaps list; reframe bullets to cover them. | Recruiters skim this exact framing in their first 10 seconds. |
| Keyword Frequency Analysis | Which JD keywords appear in your resume vs. don't. | Add missing keywords where the evidence supports it. | ATS keyword-match drives the biggest single score component. |
| Skills Coverage Radar | Visual overlap between your skills and JD requirements. | Close gaps on axes where JD demand is high. | Spots category-level holes that bullet-level edits miss. |
| Bullet Point Analysis | Which bullets are weak (no metrics, weak verbs). | Rewrite flagged bullets with numbers and outcome verbs. | Strong bullets are the #1 driver of human screener yes/no. |
| Missing Skills | JD skills not found in your resume. | Either add if you have them, or study via flashcards. | Unaddressed gaps are the fastest reason to skip an application. |
| ATS Formatting Issues | Structural problems (tables, images, headers). | Fix before re-scanning; some ATSes drop formatted content entirely. | One table can cost you the whole scan, not just a section. |
| Improvement Suggestions | Prioritized concrete edits to lift your score. | Work top-to-bottom; highest-leverage first. | Saves you guessing what to fix next. |

Section IDs (for `results_tooltip_opened` enum + DOM anchor):
- `ats_score`, `score_breakdown`, `job_fit`, `keywords`, `skills_radar`, `bullets`, `missing_skills`, `formatting`, `improvements`

`job-fit`, `keywords`, `skills`, `bullets` already exist as DOM `id=` anchors for the left-sidebar quick-nav (`NAV_ITEMS` in `Results.tsx:69-74`). Analytics event IDs normalize these to `job_fit`, `keywords`, `skills_radar`, `bullets` to keep underscore-style naming consistent with other PostHog enums.

## Tooltip Component

**Reuse and harden the existing `PanelSection` tooltip primitive** (`Results.tsx:37-66`). A second component is not warranted — the API already fits, and the primitive is used on 4 of 9 sections on this page today.

**Existing API (kept):**
- `tooltip?: string` prop on `PanelSection` — when present, renders an info icon after the title.
- Info icon: Lucide `Info` 12px, `text-text-muted hover:text-text-secondary`.
- Activation today: click toggles, hover opens.

**Required hardening (this spec):**
- **Keyboard:** trigger button must be focusable (default for `<button>`, keep it); `Enter` and `Space` toggle the tooltip (native button behavior already does this). Add `type="button"` to prevent form submission.
- **Escape to dismiss:** when the tooltip is open, pressing `Escape` closes it and returns focus to the trigger.
- **Click-outside dismissal:** when the tooltip is open, any `mousedown` / `touchstart` outside the tooltip content + trigger closes the tooltip. Implement with a shared `useClickOutside` hook (create `hirelens-frontend/src/hooks/useClickOutside.ts` if absent — grep first).
- **ARIA:** trigger gets `aria-label={`Info: ${title}`}` (already present), `aria-expanded={showTooltip}`, `aria-describedby={tooltipId}` when open. Tooltip content gets `role="tooltip"` and `id={tooltipId}` (generate with `useId()`).
- **Mobile:** tap toggles (existing `onClick` already handles); hover is optional and does not fire on touch devices — acceptable. Tap-outside closes via the click-outside handler above.
- **Touch target:** wrap the icon in a 24×24 hit area (padding on the button) to exceed the 20×20 minimum recommended for on-body icons without blowing up the visual layout; the WCAG 44×44 target is not required for inline informational icons adjacent to a clear label (WCAG 2.5.5 Level AAA, exception for inline text glyphs).

**Five sections need `tooltip` prop added** (already use `PanelSection`):
- Skills Coverage Radar (`Results.tsx:309`)
- Bullet Point Analysis (`Results.tsx:316`)
- ATS Formatting Issues (`Results.tsx:341`)
- Improvement Suggestions (`Results.tsx:346`)

**One section needs refactoring to use `PanelSection`** (currently bypasses it):
- Score Breakdown (`Results.tsx:201-209`) — presently renders `AnimatedCard` + manual header. Convert to `<PanelSection title="Score Breakdown" icon={BarChart3} tooltip="...">`.

**One section needs a section ID** for the nav + analytics event (`results_tooltip_opened`):
- Add `id="score-breakdown"` / `id="missing-skills"` / `id="formatting"` / `id="improvements"` on the wrapper `<div>` for consistency with the existing `id="job-fit"` / `id="keywords"` / `id="skills"` / `id="bullets"`.

## Acceptance Criteria

- **AC-1**: The "In resume" bar's fill is derived from `--color-accent-secondary` at render time. No hardcoded hex color remains in `KeywordChart.tsx`. Verified by a Vitest assertion that `rgba(124,58,237` does not appear in the component source after the change.
- **AC-2**: A single `KEYWORD_LEGEND` constant (exported from `KeywordChart.tsx`) is the source of truth for both the legend swatches in `Results.tsx` and the chart cell colors. The three legend swatches and the three rendered bar-fill values match 1:1 by `rgba(r, g, b, a)` string equality on a test fixture with known matched / missing / resume-only distribution — verified under all three themes (`dark`, `light`, `midnight-blue`).
- **AC-3**: Every one of the nine major section headers (ATS Score, Score Breakdown, Job Fit Explanation, Keyword Frequency Analysis, Skills Coverage Radar, Bullet Point Analysis, Missing Skills, ATS Formatting Issues, Improvement Suggestions) renders a visible, focusable `Info` icon immediately after its title.
- **AC-4**: Activating any info icon (click or keyboard Enter/Space) shows the three-line what-this-means / how-to-act / why-it-matters copy from §Education Layer Design.
- **AC-5**: Tooltip accessibility:
  - Trigger is keyboard-reachable via Tab.
  - Trigger carries `aria-label="Info: <title>"` and `aria-expanded` reflecting open state.
  - Tooltip content carries `role="tooltip"` and is linked to the trigger via `aria-describedby` when open.
  - Escape closes the tooltip and returns focus to the trigger.
- **AC-6**: Mobile/touch:
  - Tap on the trigger opens the tooltip.
  - Tap anywhere outside the tooltip closes it.
  - No behavior requires hover (hover is an enhancement, not a gate).
- **AC-7**: PostHog event `results_tooltip_opened` fires with `{ section: <section-id> }` on each open event. It does **not** fire on close. Section values drawn from the enum: `ats_score | score_breakdown | job_fit | keywords | skills_radar | bullets | missing_skills | formatting | improvements`.

## API Contract

**No backend API changes.** Bug root cause is entirely frontend (CAUSE-2). The existing `/api/v1/analyze` response shape (`KeywordChartData[]` with `{ keyword, jd_count, resume_count, matched }`) is preserved.

## Data Model Changes

None.

## Analytics Events

**New:**

| Event | Source file | Properties |
|-------|-------------|-----------|
| `results_tooltip_opened` | `pages/Results.tsx` (via `PanelSection`) | `{ section: 'ats_score' \| 'score_breakdown' \| 'job_fit' \| 'keywords' \| 'skills_radar' \| 'bullets' \| 'missing_skills' \| 'formatting' \| 'improvements' }` — fires on each tooltip open; does not fire on close (open count is sufficient signal for curriculum iteration). |

To be added to `.agent/skills/analytics.md` in the P5-S21b implementation commit.

No close event. No hover-preview event. No per-dwell-time event. Keep the schema flat.

## UI/UX

- **Info icon:** Lucide `Info` icon, 12px (existing), `text-text-muted` default, `hover:text-text-secondary` (existing).
- **Placement:** inline, trailing the section heading, separated by `gap-2` (existing `PanelSection` layout).
- **Tooltip content:** `w-64 p-2.5 rounded-lg bg-bg-overlay border border-contrast/10 shadow-lg text-xs text-text-secondary leading-relaxed` (existing styling — do not restyle in this slice).
- **Tooltip copy format:** three short lines separated by line breaks — `<strong>What this means:</strong> …` then `<strong>How to act:</strong> …` then `<strong>Why it matters:</strong> …`. Labels in `font-semibold text-text-primary`, values in `text-text-secondary`. Implement via a structured prop `tooltip?: { what: string; how: string; why: string }` rather than a raw string, so the labels are consistent and not baked into each caller.
- **Mobile:** icon wrapped in a 24×24 hit area. Tooltip content max-width 256px (`w-64`), wraps on narrow viewports, never truncates.
- **Desktop:** hover shows tooltip; click pins it open; click-outside dismisses; Escape dismisses.
- **Color tokens:** all colors come from the theme via Tailwind utilities (CLAUDE.md R12).

## Edge Cases

- **No keywords returned from backend:** `KeywordChart` already renders "No keyword data available" (existing `data.length === 0` branch). Hide the legend when no data — nothing to color-match. Add a `data.length === 0` guard in `Results.tsx` around the legend swatch row.
- **Single-color scenario** (all matched, or all missing, or no resume-only hits): legend still shows all three swatches for reference. Chart renders what it has. No change.
- **Long tooltip content on narrow mobile viewport:** Tailwind `w-64` + `leading-relaxed` wraps naturally. Do not truncate.
- **Tooltip open when user navigates via Tab away from the trigger:** onBlur does NOT close the tooltip (it would fight with click-to-pin). Escape or click-outside closes.
- **Multiple tooltips simultaneously open:** allowed. Each `PanelSection` manages its own `showTooltip` state. Escape only closes the tooltip whose trigger last had focus.

## Dependencies

- **P5-S20 ordering:** P5-S20 ("Move Job Fit Explanation above the fold", BACKLOG E-009) is in the same Phase-5E chunk as this spec. If P5-S20 ships first, this spec must verify the Job Fit section ID remains `job-fit` (analytics event value `job_fit`). If this spec ships first, P5-S20 must preserve the section IDs referenced by `results_tooltip_opened` — callout in P5-S20's spec when it's authored.
- **BACKLOG:**
  - **B-004** — "Keyword Frequency Analysis colors don't match the legend" (P1 🔴, P5-S21 part). Closed by P5-S21b implementation commit.
  - **E-010** — "Add education layer (info icons + first-visit guided tour)" (P1 🔴, P5-S21 part). Closed by P5-S21b implementation commit. Note: the "first-visit guided tour" part of E-010 is **deferred** to a follow-up slice; see §Out of Scope / Follow-ups. P5-S21b closes the info-icon half only, and the Notes column on E-010 will be updated to reflect partial close (✅ info-icons layer / 🟡 guided tour deferred) before implementation commit.
- **CODE-REALITY.md:** Session header records CODE-REALITY at `f09be80`; HEAD is `b0a7c0e`. CODE-REALITY is stale but this slice is spec-only — no live-state change that requires regeneration. P5-S21b's audit (per CLAUDE.md R16) must regenerate CODE-REALITY before drafting its audit since P5-S21b will touch frontend types (new structured `tooltip` prop shape) and component graph (adding `useClickOutside` hook).

## Test Plan

**Vitest (new tests in `hirelens-frontend/tests/`):**

- `tests/components/dashboard/KeywordChart.colors.test.tsx`:
  - `test_keyword_matched_bar_uses_token_success` — render fixture with `matched: true` keyword, read Cell fill, assert equals computed-style of `--success`.
  - `test_keyword_missing_bar_uses_token_danger_at_alpha_40` — fixture with `matched: false`, assert Cell fill equals `${danger}40`.
  - `test_keyword_resume_bar_uses_token_accent_secondary` — fixture with `resume_count > 0`, assert resume-bar fill is `rgba(<color-accent-secondary-rgb>, 0.5)`. No `124,58,237` substring anywhere in the rendered DOM.
  - `test_keyword_legend_swatches_match_chart_cells_across_themes` — loop `applyTheme('dark')`, `applyTheme('light')`, `applyTheme('midnight-blue')`; for each theme, render `Results` with a mixed fixture; parse legend swatch computed `background-color` + chart Cell fills; assert equality for matched / missing / resume.
  - `test_legend_hidden_when_no_keyword_data` — empty `keyword_chart_data`, assert the three-swatch legend row is not in the DOM.

- `tests/components/dashboard/PanelSection.tooltip.test.tsx`:
  - `test_info_icon_renders_when_tooltip_prop_present`.
  - `test_info_icon_absent_when_tooltip_prop_absent`.
  - `test_tooltip_opens_on_click_and_shows_copy` — click trigger, assert the three copy lines render under `role="tooltip"`.
  - `test_tooltip_opens_on_enter_and_space_keys`.
  - `test_tooltip_closes_on_escape_and_returns_focus_to_trigger`.
  - `test_tooltip_closes_on_outside_click`.
  - `test_trigger_has_aria_expanded_reflecting_state`.
  - `test_trigger_aria_describedby_matches_tooltip_id_when_open`.
  - `test_tooltip_fires_results_tooltip_opened_with_section_id` — mock `capture`, open tooltip, assert called with `('results_tooltip_opened', { section: <expected-id> })`; close → not called again.
  - `test_tooltip_does_not_fire_close_event` — open, close, assert capture called exactly once.

- `tests/pages/Results.tooltips.test.tsx`:
  - `test_every_major_section_renders_info_icon` — assert exactly nine `Info` icons on a canonical result fixture, one per section header.

**Manual verification (post-P5-S21b deploy smoke):**

1. Load `/prep/results` with a live scan result in each theme (Dark, Light, Midnight Blue) via the theme toggle — legend swatch colors visually match the bars.
2. On mobile (iOS Safari + Android Chrome), tap each info icon — tooltip opens; tap elsewhere — tooltip closes. No double-tap required.
3. Keyboard-only: Tab through the page, press Enter on an info icon, confirm tooltip opens and `role="tooltip"` is announced by VoiceOver/NVDA. Press Escape, confirm tooltip closes and focus returns to the trigger.
4. Open PostHog live events, click two info icons on the page, confirm two `results_tooltip_opened` events with distinct `section` values and no `results_tooltip_closed` events.

## Out of Scope / Follow-ups

- **P5-S20** — "Move Job Fit Explanation above the fold" (BACKLOG E-009). Separate slice; coordination noted in §Dependencies.
- **First-visit guided tour** — the "guided tour" half of E-010 (sequential tooltip walkthrough on first visit to `/prep/results`). Deferred. Info-icon tooltips deliver the education layer; a walkthrough is a separate UX primitive (full-page overlay with next/prev controls). Open as a new follow-up slice after P5-S21b ships and tooltip open-rates are measurable.
- **A/B test on tooltip copy phrasing** — deferred. Ship the drafted copy, measure open rate in PostHog for two weeks, iterate in a dedicated content slice.
- **Internationalization of tooltip copy** — deferred. Product is English-only today; follow when i18n infrastructure lands (post-Phase 6).
- **Tooltip copy stored in a separate content module** — not worth the abstraction at 9 sections. Keep copy inline with each `<PanelSection>` callsite in `Results.tsx`; revisit if the page grows past ~20 sections or copy review becomes a separate workflow.
- **Rebuilding the tooltip on top of a shadcn `Popover`** — not in scope. The existing `PanelSection` primitive is adequate once hardened; adding a new dependency layer for one page is not warranted.
