# SPEC: Post-ATS Onboarding Flow

**Spec #:** 09
**Phase:** 1
**Status:** Done
**Branch:** `feature/p1-09-onboarding-flow`

---

## Problem

After running an ATS scan a user lands on `/results`, which shows a
dense analysis dashboard (score, keywords, bullets, formatting). The
list of skill gaps is buried in that page and there is no direct path
from "here are your gaps" to "here are the cards that teach them."

Spec #08 built the backend gap→category bridge
(`GET /api/v1/onboarding/recommendations`). There is still no
frontend surface that uses it, so the conversion loop described in
`.agent/skills/ats-card-bridge.md` — **scan → "you're weak in X" →
here are the cards** — remains broken.

---

## Solution

Introduce a dedicated **`/onboarding`** page that is shown immediately
after a successful scan. It is minimal on purpose:

1. Hero: **"Your ATS score: 72"** with letter grade.
2. Headline: **"We found gaps in:"** followed by the gap list.
3. For each gap, a card showing the **recommended category** (icon,
   name, matched card count) with a **"Start studying →"** CTA.
4. **"Skip for now"** link at the bottom that goes to the full
   Study Dashboard.
5. A secondary **"See full analysis"** link that preserves access to
   the existing `/results` page.

Clicking a gap navigates to `/study?category=<id>`, which renders the
existing Study Dashboard filtered to that single category (the grid
shows one tile instead of all categories, plus a "Show all
categories" pill).

---

## Acceptance Criteria

- [ ] **AC-1:** After a successful scan, `useAnalysis.runAnalysis`
  navigates to `/onboarding?scan_id=<client-generated-uuid>` instead
  of `/results`.
- [ ] **AC-2:** `/onboarding` reads the scan result from
  `AnalysisContext`. If no result is present (direct navigation, or
  after a page refresh), it redirects to `/analyze`.
- [ ] **AC-3:** The page shows the numeric ATS score and grade pulled
  from the context result.
- [ ] **AC-4:** On mount the page calls
  `GET /api/v1/onboarding/recommendations` with
  `?scan_id=<uuid>&gaps=<top_gaps[0]>&gaps=<top_gaps[1]>...`.
- [ ] **AC-5:** Each returned gap renders a row with the gap string
  and, if present, up to **one** recommended category
  (`matching_categories[0]`). Rows with `match_type === 'none'` or an
  empty category list render a muted "no study cards yet" state and
  remain visible.
- [ ] **AC-6:** The "Start studying" CTA on a row with a matched
  category navigates to `/study?category=<category_id>` and fires
  `gap_card_clicked` with `{ gap, category_id }`.
- [ ] **AC-7:** "Skip for now" navigates to `/study` and fires
  `onboarding_completed` with `{ gaps_shown, cards_clicked: 0, skipped: true }`.
- [ ] **AC-8:** When the user clicks any gap card, the page also fires
  `onboarding_completed` once with
  `{ gaps_shown, cards_clicked, skipped: false }` before navigating.
- [ ] **AC-9:** On first mount the page fires `onboarding_started`
  with `{ scan_id, gap_count, source: 'ats_scan' }`.
- [ ] **AC-10:** StudyDashboard reads `?category=<id>` on mount. When
  present it filters the category grid to that single category and
  shows a "Show all categories" pill that clears the filter.
- [ ] **AC-11:** Loading state shows a lightweight skeleton while the
  recommendations request is in flight; error state shows an inline
  "Couldn't load recommendations" message with a Retry button and a
  "Skip" escape hatch.

---

## Component Breakdown

### Page: `Onboarding`
**File:** `src/pages/Onboarding.tsx`

- Reads `?scan_id` from `useSearchParams`; generates a fallback UUID
  if absent.
- Reads `result` from `useAnalysisContext`; redirects to `/analyze`
  if null.
- Calls `fetchOnboardingRecommendations(result.top_gaps, scan_id)` via
  React state (no React Query here to keep the page self-contained).
- Tracks `cardsClickedRef` so `onboarding_completed` reflects whether
  the user clicked anything before leaving.

### API Client: `fetchOnboardingRecommendations`
**File:** `src/services/api.ts`

```ts
export async function fetchOnboardingRecommendations(
  gaps: string[],
  scanId?: string,
): Promise<OnboardingRecommendationsResponse>
```

Uses axios `params` with a custom serializer so `gaps` is sent as
repeated query params (`?gaps=a&gaps=b`), matching the FastAPI
`list[str] = Query(...)` contract.

### Types added to `src/types/index.ts`

```ts
export interface RecommendedCategory {
  category_id: string
  name: string
  icon: string
  color: string
  matched_card_count: number
  similarity_score: number | null
}

export interface GapMapping {
  gap: string
  match_type: 'tag' | 'semantic' | 'none'
  matching_categories: RecommendedCategory[]
}

export interface OnboardingRecommendationsResponse {
  scan_id: string | null
  results: GapMapping[]
}
```

### StudyDashboard change
**File:** `src/pages/StudyDashboard.tsx`

- Reads `?category=<id>` via `useSearchParams`.
- When present, filters `categories` to `categories.filter(c => c.id === id)`
  and renders a "Show all categories" pill above the grid that calls
  `setSearchParams({})`.
- All existing behavior (locked modal, daily-review button, PostHog
  events) is preserved.

### Route registration
**File:** `src/App.tsx`

Adds `<Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />`.

### Analysis hook change
**File:** `src/hooks/useAnalysis.ts`

After a successful scan, replaces `navigate('/results')` with
`navigate('/onboarding?scan_id=<uuid>')`. `/results` remains reachable
from the onboarding page via a "See full analysis" link.

---

## PostHog Events

| Event | When | Properties |
|---|---|---|
| `onboarding_started` | Onboarding page mount | `{ scan_id, gap_count, source: 'ats_scan' }` |
| `gap_card_clicked` | User clicks a gap's "Start studying" CTA | `{ gap, category_id, category_name }` |
| `onboarding_completed` | User leaves the page via any CTA | `{ gaps_shown, cards_clicked, skipped }` |

---

## Edge Cases

- **No context result** (refresh, direct nav): redirect to `/analyze`.
- **Empty `top_gaps`:** skip the API call and show an empty-state
  message with a "Go to Study Dashboard" button.
- **API error:** inline error banner with Retry + Skip.
- **All gaps unmatched:** render each row with "no cards yet" copy;
  the "Skip for now" button remains the primary action.
- **User navigates back from `/study`:** `/onboarding` still works on
  re-entry (React state re-initializes; `onboarding_started` fires again).

---

## Test Plan

### Manual verification
1. Start backend + frontend. Sign in.
2. Upload a sample resume + JD, click **Analyze Resume**.
3. After the scan completes, confirm the URL is
   `/onboarding?scan_id=<uuid>`.
4. Confirm the ATS score and grade are shown, followed by the gap list.
5. At least one gap row shows a recommended category and a
   "Start studying →" CTA.
6. Click a gap CTA — lands on `/study?category=<id>`. The dashboard
   shows only that one category plus a "Show all categories" pill.
7. Navigate back to `/onboarding`, click "Skip for now" — lands on
   `/study` with all categories visible.
8. PostHog: `onboarding_started`, `gap_card_clicked`, and
   `onboarding_completed` events should all appear in the PostHog
   live events feed.
9. Click "See full analysis" on the onboarding page → `/results` still
   renders correctly (existing flow intact).

### Regression checks
- `/results` is still reachable via the onboarding page.
- StudyDashboard without a `?category` param behaves as before.
- Direct navigation to `/onboarding` without a scan redirects to
  `/analyze` (no crash).

---

## Dependencies

| Spec | Status | Why |
|---|---|---|
| #08 — ATS gap → card category mapping | Done | Supplies `/api/v1/onboarding/recommendations` |
| #06 — Study Dashboard | Done | Target of the "Start studying" CTA |
| Phase-0 — ATS scanner | Done | Produces `top_gaps` |
