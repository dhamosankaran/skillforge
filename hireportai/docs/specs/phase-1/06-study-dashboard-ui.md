# SPEC: Study Dashboard UI

**Spec #:** 06  
**Phase:** 1  
**Status:** Done
**Branch:** `feature/p1-06-study-dashboard-ui`

---

## Problem

Cards and FSRS scheduling exist in the backend (specs #04 and #05), but there
is no screen that gives users an overview of all card categories, their per-
category progress, or a clear entry point into the Daily 5 review loop.
Without this page, users have no way to understand what they have studied,
what is locked behind a plan upgrade, or how to start a review session.

---

## Solution

A `/study` route renders a full-page **Study Dashboard** showing all card
categories as a responsive grid. Each category tile displays: the category
icon, name, total card count, and a progress bar derived from how many cards
in that category the user has reviewed at least once (`reps > 0` in
`card_progress`). Free-plan users see premium categories rendered in a locked
state rather than being hidden — the locked tiles act as upgrade prompts.
A persistent "Start Daily Review" CTA at the top of the page drives users
into the existing Daily 5 flow.

---

## Acceptance Criteria

- [ ] **AC-1:** The dashboard loads and renders all categories in a grid. Pro
  users see every category as an unlocked tile. Free users see `source =
  "foundation"` tiles as unlocked and all other tiles as locked.

- [ ] **AC-2:** Each tile shows the category `icon`, `name`, `card_count`, and
  a progress bar where fill = `studied_count / card_count`. `studied_count` is
  the number of cards in that category the authenticated user has reviewed at
  least once (`reps > 0`).

- [ ] **AC-3:** Clicking an unlocked tile navigates to
  `/study/category/:categoryId` (the Card Viewer, spec #07).

- [ ] **AC-4:** Clicking a locked tile opens an upgrade prompt modal — it does
  **not** navigate away. The modal contains a "Upgrade to Pro" CTA that links
  to `/pricing`.

- [ ] **AC-5:** A "Start Daily Review" button at the top of the page is always
  visible. Clicking it navigates to `/study/daily`. If no cards are due
  (empty queue), the button is still enabled; the daily review page handles
  the empty state.

- [ ] **AC-6:** On mobile (< 640 px), tiles render in a single column. On
  tablet (640–1023 px), two columns. On desktop (≥ 1024 px), three or four
  columns.

- [ ] **AC-7:** While data is loading, each tile renders a skeleton placeholder
  matching the tile dimensions. No layout shift on data arrival.

- [ ] **AC-8:** If the categories API call fails, an inline error state is
  shown within the grid area with a "Retry" button.

- [ ] **AC-9:** The page fires a PostHog event `study_dashboard_viewed` on
  mount with `{ category_count, locked_count, plan }`.

- [ ] **AC-10:** Clicking an unlocked tile fires PostHog event
  `category_tile_clicked` with `{ category_id, category_name, studied_count,
  card_count }`. Clicking a locked tile fires `locked_tile_clicked` with
  `{ category_id, category_name }`.

---

## Page Layout

### Desktop (≥ 1024 px)

```
┌─────────────────────────────────────────────────────────────────┐
│  Study Dashboard                           [Start Daily Review] │
│  ─────────────────────────────────────────────────────────────  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  🏗️          │  │  💻          │  │  🔒 Locked   │             │
│  │ System      │  │ Coding      │  │ Behavioral  │             │
│  │ Design      │  │ Patterns    │  │             │             │
│  │ ─────────── │  │ ─────────── │  │ ─────────── │             │
│  │ 42 cards    │  │ 38 cards    │  │ 55 cards    │             │
│  │ [████░░░░░] │  │ [██░░░░░░░] │  │ [─────────] │             │
│  │ 18 / 42     │  │ 8 / 38      │  │ Pro only    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  ...         │  │  ...         │  │  ...         │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile (< 640 px)

```
┌──────────────────────────┐
│  Study Dashboard         │
│  [Start Daily Review]    │
│  ──────────────────────  │
│  ┌────────────────────┐  │
│  │  🏗️  System Design  │  │
│  │  ────────────────  │  │
│  │  42 cards          │  │
│  │  [████░░░░░░░░░░░] │  │
│  │  18 / 42 studied   │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │  💻  Coding Patterns│  │
│  │  ────────────────  │  │
│  │  38 cards          │  │
│  │  [██░░░░░░░░░░░░░] │  │
│  │  8 / 38 studied    │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │  🔒  Behavioral     │  │
│  │  ────────────────  │  │
│  │  55 cards          │  │
│  │  Pro only          │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

---

## Component Breakdown

### Page: `StudyDashboardPage`

**File:** `src/pages/StudyDashboardPage.tsx`

Top-level route component. Owns data fetching and orchestrates layout.

Responsibilities:
- Calls `useStudyDashboard()` hook to fetch categories + progress.
- Renders `DashboardHeader` (title + CTA).
- Renders `CategoryGrid` (tile grid).
- Renders `UpgradeModal` (shown/hidden via local state).
- Fires `study_dashboard_viewed` PostHog event on mount.

---

### Component: `DashboardHeader`

**File:** `src/components/study/DashboardHeader.tsx`

| Prop | Type | Description |
|------|------|-------------|
| `dueCount` | `number` | Cards currently due (from `GET /study/daily` total_due) |

Renders:
- Page title "Study Dashboard".
- "Start Daily Review" button — navigates to `/study/daily`.
- Optional badge on the button showing `dueCount` if > 0 (e.g. "5 due").

---

### Component: `CategoryGrid`

**File:** `src/components/study/CategoryGrid.tsx`

| Prop | Type | Description |
|------|------|-------------|
| `categories` | `CategoryTileData[]` | Merged category + progress data |
| `isLoading` | `boolean` | Shows skeletons when true |
| `error` | `Error \| null` | Renders error state when set |
| `onRetry` | `() => void` | Called when user clicks Retry |
| `onLockedClick` | `(category: CategoryTileData) => void` | Called when locked tile is clicked |

Renders a CSS grid:
- `grid-cols-1` on mobile
- `sm:grid-cols-2` on tablet
- `lg:grid-cols-3 xl:grid-cols-4` on desktop

When `isLoading` is true: renders `N` `CategoryTileSkeleton` components (N = last known count or 6 as default).

When `error` is set: renders `ErrorState` inline.

---

### Component: `CategoryTile`

**File:** `src/components/study/CategoryTile.tsx`

| Prop | Type | Description |
|------|------|-------------|
| `category` | `CategoryTileData` | Category metadata + progress |
| `locked` | `boolean` | Renders locked state when true |
| `onClick` | `() => void` | Called on tile click |

**Unlocked tile structure:**
```
┌──────────────────────────┐
│  <icon>  <name>          │
│  ─────────────────────   │
│  <card_count> cards      │
│  [progress bar]          │
│  <studied> / <total>     │
└──────────────────────────┘
```

**Locked tile structure:**
```
┌──────────────────────────┐
│  🔒  <name>              │  ← icon overlaid with lock
│  ─────────────────────   │
│  <card_count> cards      │
│  [greyed progress bar]   │
│  Pro only                │
└──────────────────────────┘
```

Locked tile styling: reduced opacity (`opacity-60`), lock icon overlay, cursor
`cursor-pointer` (still clickable for the upgrade modal), no hover highlight.

---

### Component: `CategoryProgressBar`

**File:** `src/components/study/CategoryProgressBar.tsx`

| Prop | Type | Description |
|------|------|-------------|
| `studied` | `number` | Cards with `reps > 0` for the user in this category |
| `total` | `number` | Total cards in the category |
| `locked` | `boolean` | Renders an inert greyed bar when true |

Renders a `<div>` track with an inner `<div>` fill. Fill width = `(studied / total) * 100`%, clamped to [0, 100]. Animates width with Framer Motion `initial={{ width: 0 }}` → `animate={{ width: fillPercent }}` on mount.

When `total === 0`: renders a full-width greyed bar (no division by zero).

---

### Component: `CategoryTileSkeleton`

**File:** `src/components/study/CategoryTileSkeleton.tsx`

No props. Matches tile dimensions with pulsing placeholder blocks for icon,
name, card count, and progress bar. Uses Tailwind `animate-pulse`.

---

### Component: `UpgradeModal`

**File:** `src/components/study/UpgradeModal.tsx`

| Prop | Type | Description |
|------|------|-------------|
| `category` | `CategoryTileData \| null` | Locked category that triggered the modal |
| `onClose` | `() => void` | Dismisses the modal |

Shown when `category` is non-null. Displays:
- Category name and icon.
- "Unlock [category name] and X more with Pro" copy.
- "Upgrade to Pro" button → navigates to `/pricing`.
- "Maybe later" link → calls `onClose`.

Animated with Framer Motion `AnimatePresence` + scale/fade.

---

### Hook: `useStudyDashboard`

**File:** `src/hooks/useStudyDashboard.ts`

Wraps two `useQuery` calls:

1. `GET /api/v1/study/dashboard` — returns all categories with `studied_count`
   per category for the authenticated user (see API section below).
2. `GET /api/v1/study/daily` — used only to read `total_due` for the CTA badge.

Returns:
```typescript
{
  categories: CategoryTileData[];
  dueCount: number;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}
```

---

### Type: `CategoryTileData`

**File:** `src/types/study.ts`

```typescript
interface CategoryTileData {
  id: string;
  name: string;
  icon: string;           // emoji or icon identifier
  color: string;          // Tailwind gradient class, e.g. "from-purple-500 to-indigo-600"
  cardCount: number;
  studiedCount: number;   // cards where reps > 0 for this user
  source: "foundation" | "premium";
  locked: boolean;        // true for free users on non-foundation categories
}
```

---

## API Calls

### 1. `GET /api/v1/study/dashboard`

New endpoint required by this spec. Returns all categories (not plan-filtered)
with per-user progress counts so the UI can render locked tiles rather than
hiding premium categories entirely.

**Request**

| Parameter | In | Type | Required |
|-----------|----|------|----------|
| — | header | string | yes | `Authorization: Bearer <token>` |

**Response 200**

```json
{
  "categories": [
    {
      "id":            "<UUID>",
      "name":          "System Design",
      "icon":          "🏗️",
      "color":         "from-purple-500 to-indigo-600",
      "display_order": 1,
      "source":        "foundation",
      "card_count":    42,
      "studied_count": 18,
      "locked":        false
    },
    {
      "id":            "<UUID>",
      "name":          "Behavioral",
      "icon":          "🧠",
      "color":         "from-orange-500 to-red-600",
      "display_order": 4,
      "source":        "premium",
      "card_count":    55,
      "studied_count": 0,
      "locked":        true
    }
  ]
}
```

`locked` is `true` when the caller is on the free plan AND `source != "foundation"`.
`studied_count` is always 0 for locked categories (the user has no access, so
no progress exists).

Categories are ordered by `display_order ASC`. Free users receive all categories
with appropriate `locked` flags — none are filtered out.

**Error codes**

| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |

**PostHog:** no server-side event; the page fires `study_dashboard_viewed`
client-side on mount.

---

### 2. `GET /api/v1/study/daily`

Already specified in spec #05. Called here only to read `total_due` for the
"Start Daily Review" button badge. Uses the same `useQuery` instance cached
by the daily review page (no extra network round-trip if already cached).

---

## Responsive Layout Breakpoints

| Breakpoint | Columns | Tile width |
|------------|---------|------------|
| < 640 px (mobile) | 1 | Full width minus padding |
| 640–1023 px (tablet) | 2 | ~50% minus gap |
| 1024–1279 px (desktop) | 3 | ~33% minus gap |
| ≥ 1280 px (wide) | 4 | ~25% minus gap |

Tile min-height: 160 px. Gap between tiles: 16 px (`gap-4`). Grid padding:
16 px on mobile, 24 px on desktop.

---

## Edge Cases

- **Zero-card category:** progress bar shows empty (0 / 0). Label shows
  "0 cards". No division-by-zero; the bar renders as full-width grey.
- **All cards studied:** progress bar is fully filled. Label shows e.g.
  "42 / 42". Tile still navigates to the category viewer on click.
- **Free user with no subscription row:** treat as free plan. Same lock logic
  applies.
- **`studied_count > card_count`:** clamp progress bar to 100%. Can occur
  if cards were deleted after being reviewed. Label still shows raw numbers.
- **Empty categories list (API returns `[]`):** render a "No categories found"
  empty state with a support link, not a blank grid.
- **Network error on dashboard load:** show per-category skeleton until
  error is confirmed, then replace with inline error + Retry button.
- **Upgrade modal open, user navigates back:** modal closes because parent
  state is reset on remount. No stale modal state.
- **Touch devices:** locked tiles respond to tap, not hover. Unlocked tiles
  have active state (scale down slightly) on tap via Framer Motion `whileTap`.

---

## Dependencies

| Spec | Status |
|------|--------|
| #00 — PostgreSQL + pgvector | Done |
| #02 — Auth unification (`get_current_user`) | Done |
| #03-card-extraction — Card + Category models, seeded data | Done |
| #04 — Cards API (category list, plan gate) | Must be done first |
| #05 — FSRS Daily Review (`GET /study/daily` for due count) | Must be done first |
| New backend route: `GET /api/v1/study/dashboard` | Part of this spec |

---

## Test Plan

### Frontend unit tests (`src/components/study/`)

- **`CategoryTile` — unlocked:** renders icon, name, card count, progress bar;
  clicking fires `onClick`.
- **`CategoryTile` — locked:** renders lock overlay, "Pro only" label, reduced
  opacity; clicking fires `onClick` (not navigate).
- **`CategoryProgressBar`:** fill width = `(studied / total) * 100`%; clamps
  to 100% when studied > total; renders grey bar when `locked = true`.
- **`CategoryGrid` — loading:** renders 6 skeleton tiles when `isLoading = true`.
- **`CategoryGrid` — error:** renders error message and Retry button when
  `error` is set; Retry calls `onRetry`.
- **`UpgradeModal`:** renders category name in copy; "Upgrade to Pro" navigates
  to `/pricing`; "Maybe later" calls `onClose`.
- **`useStudyDashboard`:** mock API responses; assert `categories` are shaped
  correctly, `dueCount` is extracted from daily response.

### Integration / page tests

- **`StudyDashboardPage` — pro user:** all category tiles unlocked; clicking a
  tile navigates to `/study/category/:id`.
- **`StudyDashboardPage` — free user:** foundation tiles unlocked, premium
  tiles locked; clicking locked tile opens `UpgradeModal`, does not navigate.
- **`StudyDashboardPage` — PostHog events:** `study_dashboard_viewed` fired on
  mount; `category_tile_clicked` fired on unlocked click; `locked_tile_clicked`
  fired on locked click.

### Manual verification

1. Log in as a free-plan user; confirm premium tiles appear locked with "Pro
   only" label and clicking them opens the upgrade modal.
2. Log in as a pro-plan user; confirm all tiles are unlocked and clickable.
3. Review 5 cards in one category; revisit the dashboard and confirm that
   category's progress bar has advanced.
4. Resize browser to 375 px width; confirm tiles render single-column.
5. Confirm "Start Daily Review" button badge shows correct due count from
   `/study/daily`.
6. Kill the API server; confirm the dashboard shows the error state with a
   Retry button, not a blank page.
