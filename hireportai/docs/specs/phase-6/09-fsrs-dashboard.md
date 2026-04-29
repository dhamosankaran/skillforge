# Phase 6 — Slice 6.8: User-Self FSRS Dashboard (Read-Only Phase-6 Progress Surface)

## Status: Drafted + §12 amended at `<this-slice>` locking D-1..D-14 from §14 OQ-1..OQ-13 (incl. sub-OQ-5b)

| Field | Value |
|-------|-------|
| **Slice** | 6.8 |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `6ff39b7` (spec-author HEAD pin) |
| **BACKLOG row** | **B-080** 🔴 (filed by this slice) |
| **Depends on** | spec #00 (`docs/specs/phase-6/00-analytics-tables.md` — `quiz_review_events` + `lesson_view_events` tables and append-only invariant; shipped `e7a0044`) ▪ spec #01 (`docs/specs/phase-6/01-foundation-schema.md` — `decks` + `lessons` + `quiz_items` + `quiz_item_progress`; shipped `a989539`) ▪ spec #02 (`docs/specs/phase-6/02-fsrs-quiz-item-binding.md` — `quiz_item_progress` write path + `get_quiz_progress` aggregator; shipped `7b654fb`) ▪ spec #06 (`docs/specs/phase-6/06-read-time-invariants.md` — visibility filter chain + `curriculum_visibility.py` extraction; shipped `930a6a2`) ▪ spec #07 (`docs/specs/phase-6/07-deck-lesson-ranker.md` — persona/tier visibility helpers reused; shipped `5011518`) ▪ existing `gamification_service.get_stats` (Phase-2 streak + XP) ▪ existing `Depends(get_current_user)` chain. |
| **Blocks** | none — this is a leaf surface in the Phase-6 user-facing curriculum loop. The admin-side retention/cohort dashboard (scout slice 6.11 / 6.16 framing) ships separately and is **not** this slice's deliverable. |
| **Cross-refs** | scout `docs/audits/phase-6-scout.md` §6.4 (existing dashboards — `/admin/analytics` only; no user-self FSRS surface), §1 (study engine) for FSRS data shape, slice-by-slice 6.16 framing for retention-source decision (Postgres-only via dual-write tables per locked decision **I1**); curriculum.md §2 (visibility filter chain), §5 (analytics dual-write contract), §8 (ranker contract — re-uses persona/tier helpers); study-engine.md (FSRS state vocab); design-system.md (R12 token-only styling); analytics.md (`useRef` once-per-mount idempotency convention). |

> **Slice numbering note (info-only):** the scout audit at `83dd03b` (2026-04-26) numbered slice 6.8 as the Pro-only daily digest. Phase 6 was re-sequenced after that audit — daily digest is now slice 6.14 per BACKLOG **B-078** 🟦 (cron architecture decision). The FSRS dashboard concept that the scout audit framed under slice 6.11 / 6.16 is what this slice ships, scoped to the **user-self** view only. Admin-side cohort retention is deferred to a still-unnumbered later slice. The `Phase 6 specs on disk` block in `SESSION-STATE.md` is the authoritative slice → spec mapping.

---

## 1. Problem

The Phase-6 curriculum platform now has every load-bearing primitive in
place: a flat 12-deck × N-lesson catalogue (slice 6.1), FSRS state on
`quiz_item_progress` (slice 6.2), the lesson-card UX (slice 6.3),
admin authoring (slice 6.4), reference seed lessons (slice 6.4.5), the
read-time invariant chain (slice 6.5), the Lens-ranked deck ordering
(slice 6.6), and the persona-aware Learn page that surfaces ranked
decks to users (slice 6.7). Slice 6.0 also shipped the dual-write
events tables (`quiz_review_events`, `lesson_view_events`) so that
SQL-aggregatable retention queries do not require HogQL.

What does **not** yet exist is any user-self surface that lets a
person see their own Phase-6 progress. Three concrete gaps:

- **Cards-due visibility**: `/learn/daily` shows the day's queue but
  is action-oriented (the page's job is to drive the user into the
  flip-card review loop). There is no glanceable "you have 12 cards
  due in the next 7 days, mostly in LLM-Internals" surface.
- **Retention curve**: `quiz_review_events` is now populated (slice
  6.0 dual-write), but no surface aggregates it. The user has no
  way to see "your recall rate over the last 30 days has gone from
  62% to 78%".
- **Deck-level mastery**: the on-disk `Profile.tsx` mounts
  `<SkillRadar>` and `<ActivityHeatmap>` but both read the
  legacy Phase-5 `card_progress` + `categories` tables via
  `/api/v1/progress/radar` and `/api/v1/progress/heatmap`. Neither
  consumes `quiz_item_progress` or the new Phase-6 deck/lesson
  schema. After Phase 6 cleanup retires the legacy `cards` /
  `categories` model (scout-listed slice 6.15), those Profile
  surfaces will go dark unless replaced.

The lens-loop framing in the PRD is "scan → study → re-scan → improve".
Slice 6.6 + 6.7 close the **scan → study** half (the user lands on
ranked content). This slice closes the **study → reflect** half: the
user can see what they have studied, what is due, and how their
retention is trending — without leaving the `/learn/*` namespace.

The dashboard is intentionally a **status surface**, not an action
surface. It does not initiate study, mutate FSRS state, or replace
the Daily 5 review loop. Its role in the loop is to answer "how am I
doing?" so the user has a reason to re-enter the `/learn/daily` flow
or click through to a specific deck on `/learn`.

### 1.1 Step 0 audit findings

Audit reads at HEAD `bb3997b` (post-CR full regen `4c4d88f`,
post-slice-6.7 implementation `c6d9274`):

1. **Phase-6 FSRS-state read endpoints today.** Two on disk:
   `GET /api/v1/quiz-items/progress` (`app/api/v1/routes/quiz_items.py:111`)
   returns `QuizProgressResponse` aggregating `quiz_item_progress`
   rows by FSRS state + total reps + total lapses, and
   `GET /api/v1/quiz-items/daily`
   (`app/api/v1/routes/quiz_items.py:28`) returns the day's queue.
   Neither breaks down by deck, neither computes retention from
   `quiz_review_events`, neither surfaces a time-series.

2. **Phase-5 progress read endpoints (still live, legacy).**
   `GET /api/v1/progress/radar` and `GET /api/v1/progress/heatmap`
   (`app/api/v1/routes/progress.py`) read from
   `card_progress` + `categories`. They are the data sources for
   `<SkillRadar>` and `<ActivityHeatmap>` on `Profile.tsx`. The
   new Phase-6 dashboard MUST NOT duplicate or extend these
   endpoints — they belong to the legacy schema slated for
   slice 6.15 cleanup.

3. **`gamification_service.get_stats`**
   (`app/api/v1/routes/gamification.py:50`) returns
   `GamificationStatsResponse {current_streak, longest_streak,
   total_xp, last_active_date, freezes_available, badges}`. The
   dashboard SHOULD reuse this — re-deriving streak / XP would
   duplicate Phase-2 logic and risk drift. The dashboard does NOT
   need its own streak math.

4. **`quiz_review_events` table is on disk and write-active** per
   slice 6.0 spec §4.1 + impl `e7a0044`. Indexes
   `ix_quiz_review_events_user_reviewed_at` (`(user_id,
   reviewed_at DESC)`) and
   `ix_quiz_review_events_deck_reviewed_at` (`(deck_id,
   reviewed_at DESC)`) make the per-user retention curve and
   per-deck mastery queries cheap. The table is **append-only**
   per spec #00 §4.4; no UPDATE / DELETE in the request path.

5. **`lesson_view_events` table is on disk and write-active** per
   slice 6.0 spec §4.2 + impl `e7a0044`. Useful for a "recently
   viewed lessons" section if the OQ-tracked review-history shape
   ends up wanting view-events alongside review-events; otherwise
   not load-bearing for v1.

6. **Persona/tier visibility helpers are extracted.** Slice 6.6
   D-6 moved `_visible_persona_set` /
   `_allowed_tiers_for_user` / `_persona_visible_to` to
   `app/services/curriculum_visibility.py` (impl `5011518`).
   The dashboard's deck-mastery aggregation MUST reuse these
   helpers so retired/archived/persona-invisible decks do not
   leak into the response (slice 6.5 invariant chain).

7. **No FE dashboard route mount today.** `App.tsx` has no
   `/learn/dashboard`, no `/dashboard`, no `/progress` route.
   `<Learn />` (`/learn`) and `<Profile />` (`/profile`) are the
   two glanceable user-facing pages today; neither aggregates
   Phase-6 FSRS state into a single page. Adding a new mount is
   greenfield.

8. **Charting library status.** `package.json` has no
   `recharts` / `victory` / `chart.js` / `nivo` / `d3` /
   `visx` entries. The on-disk `<ActivityHeatmap>`
   (`src/components/progress/ActivityHeatmap.tsx`) is a
   hand-rolled CSS-grid heatmap with no chart library. The on-
   disk `<SkillRadar>` is a hand-rolled SVG `polygon` (no
   library). Adding a charting library would be a new
   dependency surface; staying hand-rolled keeps the bundle lean
   but limits what the retention-curve component can express.
   Locked at **§12 D-4** (hand-rolled SVG).

9. **Existing PostHog events that touch FSRS data.** From
   `analytics.md` + the slice 6.0 / 6.2 / 6.7 specs:
   `quiz_item_reviewed` (BE, dual-written to
   `quiz_review_events`); `quiz_item_progress_initialized` (BE,
   PostHog only); `lesson_viewed` (FE, dual-written to
   `lesson_view_events`); `learn_page_viewed` /
   `learn_mode_rendered` / `learn_deck_clicked` (FE, slice 6.7).
   The dashboard slice does NOT need to extend `quiz_item_*`
   payloads; it is a read-side surface. Per slice 6.6 D-11 zero-
   events default and slice 6.0 D-11 (no new PostHog events on
   read-time hardening), the conservative default is to ship
   only `dashboard_viewed` with the same `useRef` once-per-mount
   discipline as `home_dashboard_viewed` / `learn_page_viewed`.
   Locked at **§12 D-11** (one event `dashboard_viewed`
   once-per-mount via `useRef`).

10. **Cold-start state (a fresh user with zero reviews).**
    `quiz_item_progress` returns zero rows;
    `quiz_review_events` returns zero rows;
    `gamification_stats.current_streak == 0`,
    `last_active_date == NULL`. The dashboard MUST handle this
    branch explicitly — a 500 from a `division by zero` on the
    retention-rate calculation is not acceptable. Per scout
    §2.5's pattern (matched by slice 6.6 D-15), cold-start is a
    response-shape branch (`is_cold_start: true` flag plus
    zeroed-out section payloads), not a 404 or 204.

11. **Free vs Pro tier exposure.** Phase-6 has a foundation/
    premium tier split (`decks.tier`); slice 6.6 D-10 filters
    premium decks out of free users' ranked lists. The
    dashboard's deck-mastery section must respect the same
    visibility filter chain, but the **dashboard surface itself**
    (the page mount, the endpoint) — should it be free-allowed or
    Pro-gated? `Profile.tsx` is universally accessible today.
    Locked at **§12 D-10** (free-allowed page + premium-deck
    mastery rows filtered by visibility helpers).

12. **Profile.tsx coexistence.** `<XPBar>` / `<StreakBadge>` /
    `<SkillRadar>` / `<ActivityHeatmap>` continue to render on
    `/profile`. The new dashboard is additive (different mount,
    different data sources); Profile.tsx is **not** modified by
    this slice. Migration / deprecation of the legacy Profile
    surfaces is a separate concern picked up either by slice 6.15
    (cleanup) or by a follow-up Profile-redesign slice. Surfaced
    at **§12 D-12** (coexist v1 unchanged; follow-up B-### at
    slice 6.15).

### 1.2 Why this matters

- **Closes the lens loop's reflect half.** The user can see their
  retention trend without leaving `/learn/*`. Without it, the
  signal "you got better" is invisible — the only feedback the
  user gets is the `card_reviewed` toast and the streak counter,
  neither of which expresses content-quality progress.
- **Decouples Phase-6 FSRS visibility from the Phase-5 legacy
  surfaces.** Once slice 6.15 retires `card_progress` /
  `categories`, `<SkillRadar>` and `<ActivityHeatmap>` go dark.
  The dashboard ships the Phase-6 replacement primitives so the
  cleanup slice has a destination to point users at.
- **Activates `quiz_review_events`.** Slice 6.0 paid the dual-
  write cost; without a read consumer the table is write-only
  storage. The retention-curve aggregation is the first SQL
  consumer of the new table.
- **Persona-aware reflection** is a follow-up. A career_climber
  user's "how am I doing" framing is streak-and-weekly-progress;
  an interview_prepper's framing is gap-coverage vs target_date.
  Per-persona composition was considered and **rejected for v1
  per §12 D-2** (universal composition for Q1 simplicity); spec
  #34 + spec #61 + slice 6.7 establish the per-persona render-
  mode pattern that a follow-up slice can adopt.

Slice 6.8 ships the user-self FSRS dashboard as a read-only Phase-6
surface that reuses every existing primitive (no new write paths,
no new analytics tables, no new persona logic).

---

## 2. Goals

| # | Goal |
|---|------|
| G-1 | **User-self read-only dashboard at a single mount path.** New `src/pages/Dashboard.tsx` (mount path locked at **§12 D-1** = `/learn/dashboard`) renders the Phase-6 FSRS-progress surfaces in a single page. Read-only — no FSRS mutations, no study-session initiation. |
| G-2 | **Five canonical sections.** Cards-due, retention-curve, deck-mastery, streak-summary, recent-review-history. Each section has a stable Pydantic shape (§5) and a stable React component (§8). Composition is universal across personas per **§12 D-2**. |
| G-3 | **One backend aggregator.** New `app/services/dashboard_service.py::aggregate_user_dashboard(user, db, *, retention_window_days)` returns a single `DashboardResponse` with all five section payloads. Single-envelope endpoint locked at **§12 D-3**; section-level fan-out rejected for v1. |
| G-4 | **Read-only / additive only.** Zero new write paths, zero migrations, zero PostHog payload changes beyond the single `dashboard_viewed` event locked at **§12 D-11**. Reuses existing visibility helpers (`curriculum_visibility.py`) for deck-mastery section so retired/archived/persona-invisible decks never surface. |
| G-5 | **Cold-start safe.** Fresh user (zero reviews, zero progress rows) gets a response with `is_cold_start: true` and zeroed-out section payloads. No 404, no 204, no division-by-zero — section components render their cold-start variant copy. |
| G-6 | **Persona-agnostic BE shape.** The `DashboardResponse` envelope is persona-agnostic regardless of FE composition; **§12 D-2** locks the FE composition as universal for v1 (per-persona render-modes deferred to a follow-up). |
| G-7 | **No Phase-5 endpoint duplication.** The dashboard does NOT call `/api/v1/progress/radar` or `/api/v1/progress/heatmap` — those are legacy `card_progress` / `categories` consumers and will go dark in slice 6.15. The dashboard reads exclusively from Phase-6 tables (+ `gamification_stats` for streak/XP). |

---

## 3. Non-goals (out-of-scope this slice)

- **No FSRS mutations.** The dashboard does not expose review-card
  interactions, "snooze a card", "reset progress", "manually mark a
  card as mastered", or any other FSRS-state-changing action. R4
  (FSRS server-side only) is not relaxed.
- **No replacement of `/learn/daily`.** The Daily 5 surface
  (`pages/DailyReview.tsx`) remains the canonical study-session
  entry point. Cards-due section on the dashboard links to
  `/learn/daily` when the user wants to act on what they see, but
  does NOT mount the review UI inline.
- **No replacement of `Profile.tsx`.** Existing Profile mounts of
  `<XPBar>` / `<StreakBadge>` / `<SkillRadar>` / `<ActivityHeatmap>`
  remain unchanged this slice. Profile-redesign or Profile-
  retirement is a separate concern (locked at **§12 D-12** =
  coexist v1 unchanged; follow-up B-### at slice 6.15).
- **No admin-side cohort retention.** The scout audit's slice 6.11 /
  6.16 framing covers admin-aggregated retention curves across all
  users, deck-quality leaderboards, etc. That surface ships in its
  own slice using its own admin-gated routes; this slice is
  user-self only.
- **No social / leaderboard / comparison surfaces.** The dashboard
  shows the user's own data. No "you're in the top 30% of
  Career-Climbers", no friend-graph, no team comparisons (Team-Lead
  B2B is its own surface per slice 6.7 §3 + PRD §1.5 P3).
- **No CSV / PDF export.** Read surface only; no download buttons.
- **No email digest of dashboard stats.** Slice 6.14 owns the
  Pro-daily-digest surface; this slice does not extend Resend or
  `email_preferences`.
- **No HogQL / PostHog Query API integration.** Spec #38 ban
  unchanged. All aggregation is Postgres SQL via SQLAlchemy 2.0.
- **No new PostHog events beyond `dashboard_viewed`** per
  **§12 D-11** (single event once-per-mount). The dashboard is a
  glanceable read; per-section view events would proliferate
  without a clear consumer.
- **No new BACKLOG B-### IDs filed for sub-OQs** beyond B-080
  itself. If a §12 D-N lock surfaces work that warrants its own
  slice (e.g., "extract retention-curve component into a shared
  chart primitive"), the impl slice is the place to file the
  follow-up row.
- **No real-time / SSE / WebSocket.** The dashboard refetches on
  navigation to the page; no live stream, no polling timer.
- **No deep-link drill-down on individual cards.** Clicking a row
  in the recent-review-history section navigates to
  `/learn/lesson/<lesson_id>` (existing slice 6.3 surface), NOT
  to a new "review detail" page.
- **No tier-gating widening.** Slice 6.5 / 6.6 tier rules unchanged.
  Pro-gating of the dashboard surface itself locked at **§12 D-10**
  (free-allowed page + premium-deck mastery rows filtered by
  visibility helpers).

---

## 4. Architecture

### 4.1 Component graph (new files)

```
src/pages/Dashboard.tsx                              -- new (page mount)
src/hooks/useFsrsDashboard.ts                        -- new (fetcher + state machine)
src/components/dashboard/CardsDueSection.tsx         -- new
src/components/dashboard/RetentionCurveSection.tsx   -- new
src/components/dashboard/DeckMasterySection.tsx      -- new
src/components/dashboard/StreakSummarySection.tsx    -- new
src/components/dashboard/ReviewHistorySection.tsx    -- new
src/services/api.ts::fetchFsrsDashboard()            -- new helper (additive)
src/types/index.ts::DashboardResponse + section types -- new (additive)

hirelens-backend/app/services/dashboard_service.py   -- new (aggregator)
hirelens-backend/app/schemas/dashboard.py            -- new (response shapes)
hirelens-backend/app/api/v1/routes/dashboard.py      -- new (route handler)
hirelens-backend/app/main.py                         -- modified (route mount line)
```

### 4.2 Data flow

```
GET /api/v1/learn/dashboard?retention_window_days=30
  ↓ Depends(get_current_user)
  ↓ dashboard_service.aggregate_user_dashboard(user, db, retention_window_days=30)
      ├── _aggregate_cards_due(user.id, db)           reads quiz_item_progress
      ├── _aggregate_retention_curve(user.id, db, window_days)
      │                                                reads quiz_review_events
      ├── _aggregate_deck_mastery(user, db)           reads quiz_item_progress
      │                                                JOIN quiz_items → lessons → decks
      │                                                applies curriculum_visibility filter
      ├── _aggregate_streak(user.id, db)              reuses gamification_service.get_stats
      └── _aggregate_review_history(user.id, db, window_days)
                                                       reads quiz_review_events
  ← DashboardResponse (single envelope)

useFsrsDashboard() fetches once on mount via Learn-page-equivalent
  cancellable-effect pattern (matches src/hooks/useRankedDecks.ts)
  ↓
<Dashboard /> mounts <CardsDueSection> + <RetentionCurveSection> +
              <DeckMasterySection> + <StreakSummarySection> +
              <ReviewHistorySection> per §12 D-2 universal composition
```

### 4.3 Persona composition (composition rules)

The `DashboardResponse` shape is **persona-agnostic** — backend
returns the same envelope for every persona. Per-persona section
visibility decisions are FE-only. **§12 D-2 locks (a) universal**
— every persona sees every section in the same order (mirrors the
current `Profile.tsx` universal layout). The per-persona option
(three render modes mirroring `LearnInterviewMode` /
`LearnHabitMode` / `LearnTeamMode` from slice 6.7) is a follow-up
if D-11 telemetry shows persona-specific disengagement.

### 4.4 Cross-cutting composition rules

Computed at the parent `Dashboard.tsx` level (mirroring the
`useStudyPromptEligibility` pattern at
`src/pages/HomeDashboard.tsx:96-159` and the parent-owned param
contract at `src/pages/Learn.tsx`):

- The `useFsrsDashboard` fetch fires once per mount with the
  default `retention_window_days` value (locked at §12 D-7 = 30
  days). Window-selection toggle (7d / 30d / 90d) was considered
  and **deferred per §12 D-7** — v1 ships fixed at 30 days; the
  toggle ships in a follow-up if D-11 telemetry surfaces user
  demand.
- Cold-start (`response.is_cold_start === true`) is the parent's
  responsibility to detect and pass to each section as a
  `coldStart` prop. Each section component renders its own
  cold-start variant.
- Section ordering rendered top-to-bottom is universal per
  §12 D-2 (cards-due → streak → retention → deck-mastery →
  review-history per §8.1 default).

---

## 5. Schemas

All shapes Pydantic v2 in `hirelens-backend/app/schemas/dashboard.py`.
Field-for-field mirror in `src/types/index.ts` per the curriculum.md
§9 convention (FE types are literal mirrors of BE schemas; no
re-derivation, no `any`).

### 5.1 `DashboardResponse` (top-level envelope)

```python
class DashboardResponse(BaseModel):
    user_id: str
    persona: Optional[str]               # snake_case enum or null
    plan: Optional[str]                  # 'free' | 'pro' | 'enterprise' | null
    is_cold_start: bool                  # true iff user has zero reviews + zero progress rows
    retention_window_days: int           # actual window used
    generated_at: datetime               # server-side ranked_at-equivalent

    cards_due: CardsDueSection
    retention: RetentionSection
    deck_mastery: DeckMasterySection
    streak: StreakSection
    review_history: ReviewHistorySection
```

### 5.2 `CardsDueSection`

```python
class CardsDueSection(BaseModel):
    due_today: int
    due_next_7_days: int
    due_breakdown_by_state: CardsDueByState  # nested {new, learning, review, relearning}
    total_quiz_items_in_progress: int        # rows in quiz_item_progress for this user

class CardsDueByState(BaseModel):
    new: int          # state == 'new'
    learning: int     # state == 'learning'
    review: int       # state == 'review'
    relearning: int   # state == 'relearning'
```

Source: `quiz_item_progress` for the user, joined to `quiz_items` →
`lessons` → `decks` so the visibility filter chain applies (no
counts from retired quiz_items, archived lessons, archived decks,
persona-invisible decks, premium decks for free users).

`due_today` = rows where `due_date <= now()` AND state ∈
{learning, review, relearning} (state='new' rows have no due_date
per spec #02 §6.1 — they appear in the daily queue as fresh-fill
but aren't "due"). `due_next_7_days` = same predicate with
`due_date <= now() + interval '7 days'`. The semantics of "due"
match slice 6.2's daily-queue selector behavior.

### 5.3 `RetentionSection`

```python
class RetentionSection(BaseModel):
    sample_size: int                     # number of reviews in window
    overall_recall_rate: float           # [0, 1]; ratings 3+4 / total in window
    overall_lapse_rate: float            # [0, 1]; ratings 1 / total in window
    daily_retention: list[DailyRetentionPoint]  # newest-last; gaps filled with zero-sample entries

class DailyRetentionPoint(BaseModel):
    date: date                           # user-local date per §12 D-6
    sample_size: int                     # reviews on that day
    recall_rate: Optional[float]         # null if sample_size == 0
```

Source: `quiz_review_events` for the user, `reviewed_at >= now() -
interval 'N days'`. Recall is `rating IN (3, 4)` (Good + Easy);
lapse is `rating == 1` (Again). `rating == 2` (Hard) counts toward
recall by py-fsrs convention but excluded per §12 D-5
(`overall_recall_rate` counts Good + Easy only;
`overall_lapse_rate` counts Again only).

The series is **continuous** — every date in the window appears,
sample-zero days carry `sample_size: 0, recall_rate: None`. This
keeps the FE chart code free of gap-fill logic.

### 5.4 `DeckMasterySection`

```python
class DeckMasterySection(BaseModel):
    decks: list[DeckMastery]             # sorted by mastery_pct DESC, then deck.display_order ASC

class DeckMastery(BaseModel):
    deck_id: str
    deck_slug: str
    deck_title: str
    total_quiz_items_visible: int        # count of visible quiz_items in this deck
    quiz_items_with_progress: int        # rows in quiz_item_progress for these quiz_items
    quiz_items_mastered: int             # state == 'review' AND reps >= MASTERY_REPS_THRESHOLD
    mastery_pct: float                   # quiz_items_mastered / total_quiz_items_visible; [0, 1]
```

The "mastery threshold" — what counts as a mastered quiz_item — is
a tunable. **§12 D-8 locks `state == 'review' AND reps >= 3`** (vs
`state == 'review'` AND `stability >= some_value` vs `state == 'review'`
alone). The visibility filter chain (curriculum_visibility helpers
+ slice 6.6 D-6) is reused so retired / archived / persona-invisible
/ premium-for-free decks do not surface.

### 5.5 `StreakSection`

```python
class StreakSection(BaseModel):
    current_streak: int
    longest_streak: int
    last_active_date: Optional[date]
    freezes_available: int
    total_xp: int
```

Source: `gamification_service.get_stats(user_id, db)` (Phase-2
service, untouched). The dashboard does NOT compute streak
locally — re-deriving Phase-2 logic risks drift. `total_xp` is
included so the section can render a single "you've earned N XP"
line without a second fetch.

### 5.6 `ReviewHistorySection`

```python
class ReviewHistorySection(BaseModel):
    window_days: int                     # actual lookback used
    total_in_window: int
    recent_reviews: list[RecentReview]   # newest-first; capped at MAX_RECENT_REVIEWS

class RecentReview(BaseModel):
    quiz_item_id: str
    lesson_id: str
    lesson_title: str
    deck_slug: str
    rating: int                          # 1..4
    fsrs_state_after: str                # 'new' | 'learning' | 'review' | 'relearning'
    reviewed_at: datetime
```

Source: `quiz_review_events` JOIN `lessons` (for `lesson_title`)
JOIN `decks` (for `deck_slug`) for the user, ordered
`reviewed_at DESC`, LIMIT `MAX_RECENT_REVIEWS`. The cap value is
locked at §12 D-9 (= 20 — enough to scroll, small
enough to not drag the response payload).

The `fsrs_state_after` field gives the FE row a "state badge" hint
without needing to re-derive from the rating (a Hard rating in a
review-state card has different meaning from a Hard in a new-state
card; the state-after is the truth).

---

## 6. Backend

### 6.1 New service — `app/services/dashboard_service.py`

Single public function:

```python
async def aggregate_user_dashboard(
    user: User,
    db: AsyncSession,
    *,
    retention_window_days: int = DEFAULT_RETENTION_WINDOW_DAYS,
    review_history_window_days: int = DEFAULT_REVIEW_HISTORY_WINDOW_DAYS,
    max_recent_reviews: int = DEFAULT_MAX_RECENT_REVIEWS,
) -> DashboardResponse:
    ...
```

Internal structure mirrors `deck_ranker_service.rank_decks_for_user`:
five private async aggregators, each returning a typed section
payload, composed at the end into the envelope. Each aggregator
applies the curriculum_visibility filter chain via the shared
helpers — no aggregator opens its own visibility lookup.

`is_cold_start = (cards_due.total_quiz_items_in_progress == 0 AND
retention.sample_size == 0)` — both signals must be zero. A user
with a single review has a populated `retention.sample_size` and
thus is not cold-start even if their `quiz_item_progress` row count
is zero (impossible in practice — review writes a progress row —
but the boolean is a defensive AND for clarity).

Aggregator-internal partial-failure tolerance follows slice 6.6
D-16 — a single deck whose mastery query errors gets skipped + WARNING-
logged with the `deck_id`; the rest of the response still ships. No
5xx for one bad row. (Section-level partial failure — e.g., the
streak fetch raises — is bubbled up; if a whole section is
load-bearing the response fails fast rather than silently dropping
the section.)

Constants live at module scope:

```python
DEFAULT_RETENTION_WINDOW_DAYS = 30        # locked at §12 D-7
DEFAULT_REVIEW_HISTORY_WINDOW_DAYS = 30   # locked at §12 D-9 (same as retention)
DEFAULT_MAX_RECENT_REVIEWS = 20           # locked at §12 D-9
MASTERY_REPS_THRESHOLD = 3                # locked at §12 D-8
```

### 6.2 New route — `app/api/v1/routes/dashboard.py`

```python
@router.get(
    "/learn/dashboard",
    response_model=DashboardResponse,
    summary="User-self FSRS dashboard (Phase-6 progress aggregator)",
)
async def get_fsrs_dashboard(
    retention_window_days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    ...
```

Auth required. Free-tier visibility locked at **§12 D-10** =
free-allowed page + premium-deck mastery rows filtered by
`curriculum_visibility` helpers (no PaywallTrigger; no new union
member). Single-envelope endpoint shape locked at **§12 D-3**.

Mounted in `app/main.py` next to the existing `app.include_router`
calls for `quiz_items`, `progress`, `gamification` — alphabetical
proximity, no router-prefix change to the `/api/v1` namespace.

### 6.3 Reuse of existing services

- `gamification_service.get_stats(user_id, db)` — streak section.
  Imported, not re-implemented.
- `app.services.curriculum_visibility._visible_persona_set` /
  `_allowed_tiers_for_user` — deck-mastery section. Imported, not
  duplicated.
- `quiz_item_study_service.get_quiz_progress` — NOT reused;
  `CardsDueSection` aggregates the same source table differently
  (per-state breakdown + due-window arithmetic). Two separate
  aggregators against the same table are simpler than threading
  optional kwargs through one shared helper.
- `lesson_service` reads — NOT reused; deck-mastery is a counts
  query, not a content fetch. Avoiding `selectinload` paths keeps
  the dashboard query cheap.

### 6.4 Performance envelope

For a typical user (~100 progress rows, ~500 events in 30-day
window, ~12 decks visible) the five aggregators are each indexed
single-pass queries totalling ~200ms — within the 500ms admin-
analytics envelope spec #38 sets as a soft ceiling. **No caching**
(mirrors slice 6.6 D-12 — invalidation on every review submission
costs more than recompute).

---

## 7. Migrations

**Zero.** Every data source the dashboard consumes is already on
disk:

- `quiz_item_progress` shipped at slice 6.1 (`a989539`).
- `quiz_review_events` shipped at slice 6.0 (`e7a0044`).
- `lesson_view_events` shipped at slice 6.0 (`e7a0044`) — not used
  by v1 sections, listed for completeness.
- `gamification_stats` + `badges` shipped pre-Phase-6 (Phase 2).
- The visibility-helper module shipped at slice 6.6 (`5011518`).

§12 D-9 locks review-history reads from `quiz_review_events`
only; `lesson_view_events` is unused by v1 sections. A future
amendment that wants view-events alongside reviews can join
the existing `lesson_view_events` table — still no migration.

The only additive write paths Phase-6 has produced are slice 6.0's
two events tables; this slice is a pure consumer of those write
paths.

---

## 8. Frontend

### 8.1 New page — `src/pages/Dashboard.tsx`

Mounts at `/learn/dashboard` per **§12 D-1** — same `/learn/*`
namespace as `/learn` (Learn page), `/learn/daily` (Daily Review),
`/learn/lesson/:id` (Lesson reader), `/learn/mission` (Mission
Mode).

Page structure:

```tsx
function Dashboard() {
  const { user } = useAuth()
  const { data, isLoading, error, isColdStart } = useFsrsDashboard()
  const persona = user?.persona
  ...
  return (
    <PageContainer>
      <DashboardHeader persona={persona} isColdStart={isColdStart} />
      {/* universal composition per §12 D-2 */}
      <CardsDueSection data={data?.cards_due} coldStart={isColdStart} />
      <StreakSummarySection data={data?.streak} coldStart={isColdStart} />
      <RetentionCurveSection data={data?.retention} coldStart={isColdStart} />
      <DeckMasterySection data={data?.deck_mastery} coldStart={isColdStart} />
      <ReviewHistorySection data={data?.review_history} coldStart={isColdStart} />
    </PageContainer>
  )
}
```

Universal composition per **§12 D-2** — no inline persona-mode
functions. A future per-persona refactor (mirroring slice 6.7's
inline-mode pattern) is a separate slice if D-11 telemetry
surfaces persona-specific disengagement.

### 8.2 New hook — `src/hooks/useFsrsDashboard.ts`

Mirrors `src/hooks/useRankedDecks.ts`:

```ts
export function useFsrsDashboard(opts?: {retentionWindowDays?: number}) {
  // useEffect-backed cancellable fetch; matches existing convention
  // returns {data, isLoading, error, isColdStart}
}
```

`isColdStart` is derived from `data?.is_cold_start`. The hook does
not duplicate cold-start logic.

### 8.3 New section components — `src/components/dashboard/`

Five components, one per section. All:

- Receive their slice of the `DashboardResponse` as a typed prop
  (`CardsDueSectionProps { data: CardsDueSection | undefined,
  coldStart: boolean }`).
- Render a skeleton / cold-start variant when `data === undefined`
  or `coldStart`.
- Use design-token classes only (R12) — no hardcoded hexes.
- Receive zero context dependencies (the parent `Dashboard.tsx`
  owns `useAuth` + `useFsrsDashboard`; sections are pure).

Charting locked at **§12 D-4** = hand-rolled SVG (~80 LoC for the
curve chart; mirrors on-disk `<SkillRadar>` / `<ActivityHeatmap>`
precedent; no new dep).

### 8.4 Modified files

- `src/App.tsx` — one route added (`/learn/dashboard` →
  `<Dashboard />` wrapped in `<ProtectedRoute>` per the
  established pattern). Dashboard is **not** lazy-loaded in v1
  (matches `<Learn />`'s eager mount); not surfaced as an OQ —
  Q1 simplicity.
- `src/services/api.ts` — `fetchFsrsDashboard(opts?: {
  retentionWindowDays?: number })` helper added (additive).
- `src/types/index.ts` — `DashboardResponse` + section types
  added (additive). Field-for-field mirror of `app/schemas/
  dashboard.py` per curriculum.md §9.

### 8.5 Existing pages explicitly NOT touched

- `src/pages/Profile.tsx` — `<XPBar>` / `<StreakBadge>` /
  `<SkillRadar>` / `<ActivityHeatmap>` continue to render
  unchanged. Coexistence locked at **§12 D-12** (coexist v1;
  follow-up retirement B-### at slice 6.15).
- `src/pages/Learn.tsx` (slice 6.7) — composition rules unchanged.
  No "click here for your stats" CTA wired in v1; the dashboard
  is reachable via direct URL + the navigation chrome (whether
  TopNav adds a "Dashboard" link locked at §12 D-1 sub-decision = wait
  until D-11 telemetry proves the surface).
- `src/pages/HomeDashboard.tsx` (Phase-5 spec #34 + #61) —
  unchanged; composition rules untouched.

---

## 9. Analytics

### 9.1 Default proposal — at most one new event

Per **§12 D-11** = single event:

| Event | Source | Properties | Fires |
|-------|--------|------------|-------|
| `dashboard_viewed` | `src/pages/Dashboard.tsx` | `{persona, plan, is_cold_start, retention_window_days}` | Once per Dashboard mount via `useRef` (matches `home_dashboard_viewed` / `learn_page_viewed` convention). Fires AFTER the `useFsrsDashboard` fetch resolves (so payload includes the cold-start flag). |

Per-section view events (`dashboard_section_viewed`) and per-row
click events (`dashboard_review_history_row_clicked`) were
considered and **rejected for v1 per §12 D-11** — single event
mirrors the slice 6.6 D-11 / 6.0 D-11 read-side conservatism while
keeping enough signal that the page is being visited.

### 9.2 Existing events touched

None. The dashboard is a pure read consumer of `quiz_review_events`
and `quiz_item_progress`; no existing emission site changes.

### 9.3 Catalog discipline

`.agent/skills/analytics.md` gets one new row at impl time
(`dashboard_viewed`). No deprecations; no renames; no changes to
existing rows.

---

## 10. Test plan

Estimated **~+10 BE + ~+15 FE** test cases. Final count locked at
impl per the slice 6.7 / 6.6 envelope-with-tolerance pattern.

### 10.1 BE — `tests/test_dashboard_service.py` — aggregator tests

Estimated **~6-8 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `aggregate_user_dashboard returns is_cold_start=true for fresh user` | G-5 cold-start AC. |
| 2 | `aggregate_user_dashboard returns populated cards_due for user with progress rows` | Happy-path cards-due. |
| 3 | `aggregate_user_dashboard retention curve sample-zero days fill with null recall` | §5.3 continuous-series invariant. |
| 4 | `aggregate_user_dashboard deck_mastery filters retired quiz_items + archived lessons + archived decks` | G-7 + slice 6.5 invariant chain. |
| 5 | `aggregate_user_dashboard deck_mastery filters premium decks for free user` | Slice 6.5 D-2 + slice 6.6 D-10 tier. |
| 6 | `aggregate_user_dashboard deck_mastery filters persona-invisible decks` | Persona visibility (per `_visible_persona_set`). |
| 7 | `aggregate_user_dashboard streak section matches gamification_service.get_stats output` | §6.3 reuse contract — assert no drift. |
| 8 | `aggregate_user_dashboard partial-failure on one deck mastery query logs WARNING and skips deck` | §6.1 D-16-mirror partial-failure semantics. |

### 10.2 BE — `tests/test_dashboard_routes.py` — route-layer tests

Estimated **~4-5 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `GET /api/v1/learn/dashboard returns 401 for unauthed request` | R3 auth gate. |
| 2 | `GET /api/v1/learn/dashboard returns 200 + DashboardResponse for authed user` | Happy path. |
| 3 | `GET /api/v1/learn/dashboard?retention_window_days=7 honors window override` | Query-param plumbing. |
| 4 | `GET /api/v1/learn/dashboard?retention_window_days=999 returns 422` | Pydantic Query validator (`le=365`). |
| 5 | `GET /api/v1/learn/dashboard does NOT fire any PostHog event from BE` | §9 zero-BE-events invariant. |

### 10.3 FE — `tests/pages/Dashboard.test.tsx` — page-level

Estimated **~6-8 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `renders all five section components when data resolves` | Composition AC. |
| 2 | `mounts cold-start variants when is_cold_start === true` | G-5 cold-start AC. |
| 3 | `shows skeleton state during fetch` | Loading UX. |
| 4 | `surfaces fetch error inline (no toast — read surface)` | Error UX. |
| 5 | `dashboard_viewed fires once via useRef even on Strict-Mode double-render` | §9 idempotency. |
| 6 | `dashboard_viewed payload includes persona + plan + is_cold_start + retention_window_days` | §9 payload regression. |
| 7 | `null persona redirects to /onboarding/persona via PersonaGate` | PersonaGate compatibility regression (matches slice 6.7 AC-4). |
| 8 | `universal composition renders all sections in the §8.1 order across all three personas` | §12 D-2 lock observable. |

### 10.4 FE — `tests/components/dashboard/*.test.tsx` — section components

Estimated **~5-7 tests across 5 files** (one or two tests per
section component). Section-level coverage:

| Section | Key test |
|---------|----------|
| `CardsDueSection` | Renders due_today + due_next_7_days + per-state breakdown; cold-start renders "Nothing due — start a session" CTA copy. |
| `RetentionCurveSection` | Renders chart for ≥1 sample-day; cold-start renders "Review some cards to see your retention curve" copy; sample-zero days are visually distinct (per §5.3 null `recall_rate`). |
| `DeckMasterySection` | Renders one row per deck sorted by mastery_pct DESC; cold-start renders "No mastery data yet" copy. |
| `StreakSummarySection` | Renders current_streak + longest_streak + freezes_available + total_xp; cold-start renders "Start a streak today" copy. |
| `ReviewHistorySection` | Renders newest-first review rows; row click navigates to `/learn/lesson/<lesson_id>`; cold-start renders "Your recent reviews will show up here" copy. |

### 10.5 Regression set must stay green

- `tests/pages/Profile.test.tsx` — Profile composition unchanged
  (G-7 + §1.1 finding #12 + §3 non-goal).
- `tests/pages/Learn.test.tsx` (slice 6.7) — Learn page unchanged.
- `tests/App.redirects.test.tsx` — `/study → /learn` redirects
  unaffected (this slice adds `/learn/dashboard`, doesn't change
  existing routes).
- All slice-6.5 invariant tests
  (`tests/test_lesson_service_invariants.py`,
  `tests/test_quiz_item_study_service_invariants.py`) — visibility
  helpers reused, no behavioral change.

### 10.6 Integration tests

None. The dashboard is a pure SQL aggregation — no LLM call, no
external service, no integration marker.

---

## 11. Acceptance criteria

| AC | Surface | Trigger | Expected behavior | Test harness |
|----|---------|---------|-------------------|--------------|
| **AC-1** | `GET /api/v1/learn/dashboard` | unauthed | 401 | pytest `httpx_client` |
| **AC-2** | `GET /api/v1/learn/dashboard` | authed, fresh user (zero progress, zero events) | 200 + `is_cold_start: true` + zeroed sections | pytest |
| **AC-3** | `GET /api/v1/learn/dashboard` | authed, populated user | 200 + `is_cold_start: false` + non-zero `cards_due.total_quiz_items_in_progress` | pytest |
| **AC-4** | `_aggregate_deck_mastery` | user with retired quiz_items in seed deck | retired quiz_items excluded from `total_quiz_items_visible` | pytest service-layer |
| **AC-5** | `_aggregate_deck_mastery` | free user with premium decks in seed | premium decks not present in `decks` array | pytest |
| **AC-6** | `_aggregate_retention_curve` | user with 0 reviews on a date in window | day appears in `daily_retention` with `sample_size: 0, recall_rate: null` | pytest |
| **AC-7** | `_aggregate_streak` | user with `gamification_stats.current_streak == 7` | `streak.current_streak == 7` | pytest |
| **AC-8** | `Dashboard.tsx` | persona=null user mount | PersonaGate redirect to `/onboarding/persona` | Vitest `MemoryRouter` |
| **AC-9** | `Dashboard.tsx` | authed populated user mount | Renders all five section components in DOM order locked at §12 D-2 (universal composition; cards-due → streak → retention → deck-mastery → review-history per §8.1) | Vitest `getByTestId` ordering |
| **AC-10** | `Dashboard.tsx` | mount with `is_cold_start: true` | Each section's cold-start variant renders | Vitest |
| **AC-11** | `dashboard_viewed` | mount completes after fetch resolves | event fires exactly once even under React Strict Mode double-render | Vitest `vi.spyOn(captureMock)` |
| **AC-12** | `tsc --noEmit` | post-impl baseline | type-check passes; new types in `src/types/index.ts` mirror `app/schemas/dashboard.py` field-for-field | `npm run typecheck` |
| **AC-13** | All existing FE + BE tests | post-impl baseline | 636 BE + 397 FE baseline still passes; net new tests per §10 | `pytest -m "not integration"` + `npx vitest run` |

---

## 12. Decisions

> Locked at §12 amendment `<this-slice>` (2026-04-29) from §14
> OQ-1..OQ-13 + sub-OQ-5b (mirrors slice 6.0 `e8eecdd` / slice
> 6.4.5 `df58eaf` / slice 6.5 `acba7ed` / slice 6.6 `fb92396` /
> slice 6.7 `0c21223` precedent). Each D-N below resolves a §14
> OQ; §14 retains the question + RESOLVED pointer back here for
> traceability. OQ→D mapping: OQ-1→D-1, OQ-2→D-2, OQ-3→D-3,
> OQ-4→D-4, OQ-5→D-5, OQ-5b→D-6, OQ-6→D-7, OQ-7→D-8, OQ-8→D-9,
> OQ-9→D-10, OQ-10→D-11, OQ-11→D-12, OQ-12→D-13, OQ-13→D-14.

**D-1 (resolves OQ-1) — mount path = `/learn/dashboard`** per
author hint (a). Keeps the surface inside the `/learn/*` namespace
alongside Learn / Daily Review / Lesson / Mission — same namespace
as the rest of slice 6.7 / 6.6 / 6.3 collateral. Sub-decision:
TopNav `Dashboard` link is NOT added this slice (wait until the
surface is proven via direct-URL traffic + telemetry from D-11).

**D-2 (resolves OQ-2) — persona scope = universal composition**
per author hint (a). Every persona sees every section in the same
order (matches `Profile.tsx` precedent). Q1 simplicity for v1;
per-persona render-mode (option (b) mirroring slice 6.7) is a
follow-up if telemetry from D-11 surfaces persona-specific
disengagement. The `DashboardResponse` shape stays persona-
agnostic (§5.1) regardless — the lock affects FE composition only.

**D-3 (resolves OQ-3) — endpoint surface = single envelope** per
author hint (a). One `GET /api/v1/learn/dashboard` returns the full
`DashboardResponse`. The 200ms total budget (§6.4) gives no latency
case for splitting; future split is non-breaking (split routes can
re-call the aggregator with a section selector).

**D-4 (resolves OQ-4) — charting library = hand-rolled SVG** per
author hint (a). No new dep; ~80 LoC for the retention-curve chart;
mirrors on-disk `<SkillRadar>` / `<ActivityHeatmap>` precedent.
Replaceable with `recharts` (option (b)) when the admin retention
dashboard slice ships and forces the chart-lib decision.

**D-5 (resolves OQ-5) — recall-rate definition = `rating IN (3, 4)`
(Good + Easy) only** per author hint (a). User-facing dashboards
report confident recall; Hard sits in the middle and is arguably a
near-lapse. The §5.3 `overall_recall_rate` field takes a single
definition; py-fsrs's "remembered" semantics (option (b)) are
exposed as a separate `overall_lapse_rate` (`rating == 1`) on the
same shape, so a future amendment can switch the recall framing
without schema change.

**D-6 (resolves OQ-5b) — date bucketing = user-local date via
`email_preferences.timezone`** per author hint (b). Gamification's
streak math already uses user-local timezone (per `/gamification/
stats` lazy-reset on UTC day rollover); mismatch between dashboard
date-bucketing and streak day-rollover would read as a bug. One
extra `email_preferences` lookup per request (cheap; the row is
small and joinable in the same query).

**D-7 (resolves OQ-6) — default `retention_window_days = 30`, no
toggle in v1** per author hint (a). 30 days is enough samples to
be statistically informative and short enough that a casual user
sees recent behavior. The 7d / 30d / 90d toggle UI (option (c))
defers to a follow-up if telemetry from D-11 surfaces user demand.
Constant lives in `dashboard_service.py` per §6.1; query param
(`?retention_window_days=N`) per D-14 lets ad-hoc tuning happen
without redeploy.

**D-8 (resolves OQ-7) — mastery threshold = `state == 'review' AND
reps >= 3`** per author hint (a). Most legible to the user
("you've reviewed this 3+ times and consistently got it right");
FSRS-stability-based (option (c)) is faithful but requires
explaining `stability` in copy; `state == 'review'` alone (option
(b)) is too lenient (a single Good rating in learning + first
review = 2 reps). Constant `MASTERY_REPS_THRESHOLD = 3` lives at
module scope per §6.1.

**D-9 (resolves OQ-8) — review-history = `MAX_RECENT_REVIEWS = 20`,
same window as retention** per author hint (a). 20 rows scroll
comfortably without dragging the response payload; same window as
the retention curve above keeps the section semantically aligned.
Sub-decision: row click navigates to `/learn/lesson/<lesson_id>`
(existing slice 6.3 surface); no inline drawer in v1. Section's own
window (option (c)) deferred — coupling to retention window is a
v1 simplicity win, splittable in a follow-up if user feedback
asks.

**D-10 (resolves OQ-9) — tier-gating = (a) free-allowed page +
(c) premium-deck mastery rows hidden from free users** per author
hint (compound). The page itself has no PaywallTrigger — read-only
data, no quota cost, blocking foundation users from their own
progress is anti-engagement. Premium-deck mastery rows are already
filtered out by the `curriculum_visibility` helper chain (slice
6.6 D-10 / slice 6.5 D-2) so no extra FE branch is needed; the
filter happens in `_aggregate_deck_mastery` (§6.1).

**D-11 (resolves OQ-10) — analytics = one event `dashboard_viewed`
once-per-mount via `useRef`** per author hint (a). Single event
with rich payload (`{persona, plan, is_cold_start,
retention_window_days}`) is enough to funnel-analyze. Per-section
view events / row click events (option (b)) over-instrument before
there is a consumer dashboard; zero events (option (c)) loses signal
that the page is being visited at all. Matches `home_dashboard_viewed`
/ `learn_page_viewed` cadence convention.

**D-12 (resolves OQ-11) — Profile.tsx = coexist v1 unchanged** per
author hint (a). Q2 surgical-changes prevails; Profile is a working
surface and the legacy `card_progress` data isn't going dark until
slice 6.15. A follow-up B-### to retire `<SkillRadar>` /
`<ActivityHeatmap>` from Profile (option (b)) is the right ledger
entry once slice 6.15 (cleanup) ships — file at that point, not
this slice. Inline deprecation (option (c)) is rejected — would mix
slice scopes and risk breaking the Phase-5 surfaces before their
data source is retired.

**D-13 (resolves OQ-12) — cold-start CTA copy = per-section
variants** per author hint (a). Each section's cold-start variant
tells the user what that section will do once they have data
(e.g., "Nothing due — start a session" on cards-due; "Review some
cards to see your retention curve" on retention). A page-level
banner alone (option (b)) is a wall; banner + per-section (option
(c)) over-communicates. Five variants are locked per-section in
the §10.4 component-test table.

**D-14 (resolves OQ-13) — query param shape = `?retention_window_days=N`
only** per author hint (a). One param is the right minimum;
`MAX_RECENT_REVIEWS` and `DEFAULT_REVIEW_HISTORY_WINDOW_DAYS` stay
hardcoded constants in `dashboard_service.py` (§6.1). Exposing every
constant (option (b)) over-parameterises the surface before there
is a caller demanding the knobs; zero query params (option (c))
loses ad-hoc tuning for QA / debug. Route signature locks at
`get_fsrs_dashboard(retention_window_days: int = Query(default=30,
ge=1, le=365), ...)` per §6.2.

---

## 13. Out of scope (deferred to other slices)

- **Admin-side cohort retention dashboard.** Scout slice 6.11 /
  6.16 framing covers per-deck recall-curve, deck-quality
  leaderboards, lapse-rate by content-type, etc., aggregated
  across all users. That ships in its own admin-gated slice with
  its own routes under `/api/v1/admin/analytics/*`. This slice is
  user-self only.
- **Email digest of dashboard stats.** Slice 6.14 (daily Pro
  digest) owns the recurring email surface; this slice does not
  extend Resend or `email_preferences`.
- **Dashboard CSV / PDF export.** Read-only on-screen surface
  only; no download buttons.
- **Profile.tsx redesign or retirement.** `<XPBar>` /
  `<StreakBadge>` / `<SkillRadar>` / `<ActivityHeatmap>` continue
  to render on `/profile` unchanged. Migration / deprecation is
  picked up by either slice 6.15 (cleanup) or a follow-up
  Profile-redesign slice.
- **HomeDashboard widget addition** (e.g. a tiny "you have N due"
  tile on `/home`). Spec #34 + spec #61 composition is unchanged
  this slice. A future slice can add a thin pointer-widget if
  product wants the dashboard discoverable from `/home`.
- **TopNav "Dashboard" navigation entry.** Whether the chrome adds
  a Dashboard link locked at §12 D-1 sub-decision = wait until
  D-11 telemetry proves the surface; the `/learn/dashboard` mount
  is reachable via direct URL in v1.
- **Real-time / SSE / WebSocket.** Static fetch on page mount; no
  live stream.
- **Comparison surfaces** (peer comparison, "you're in the top
  N%", leaderboards). Out of scope; no social features in
  Phase-6.
- **Gamification expansions** (new badges keyed off dashboard
  events, unlock-a-trophy-for-mastering-a-deck, etc.). The
  dashboard reads `gamification_stats`; it does NOT extend the
  badges catalog.
- **Charting library adoption beyond §12 D-4 lock.** v1 ships
  hand-rolled SVG; library swap to `recharts` (option (b)) is a
  follow-up if the admin retention dashboard slice forces a
  different choice.
- **Window-toggle UI.** §12 D-7 locks 30 days fixed for v1; the
  7d / 30d / 90d toggle ships in a follow-up if D-11 telemetry
  surfaces user demand.
- **Accessibility audits beyond R12 token compliance.** Standard
  alt-text on charts and ARIA roles on tables apply (per AGENTS.md
  baseline) — no extra WCAG sweep this slice.
- **i18n.** Copy is English-only; no translation infra extended.
- **A/B variants of cold-start copy.** Spec locks per-section
  variants per §12 D-13; no rollout-tooling scope.

---

## 14. Open questions

> All OQs locked at §12 amendment `<this-slice>` (mirrors slice 6.0
> `e8eecdd` / 6.4.5 `df58eaf` / 6.5 `acba7ed` / 6.6 `fb92396` /
> 6.7 `0c21223` precedent). Each OQ retains its question text +
> RESOLVED pointer to §12 D-N for traceability; option bodies +
> author hints have been replaced.

**OQ-1 — Mount path for the dashboard.** Where does the new page
mount inside the `/learn/*` namespace, at top level, or under
Profile?
RESOLVED — see §12 **D-1** (`<this-slice>`): `/learn/dashboard`;
no TopNav link this slice (wait until proven via D-11 telemetry).

**OQ-2 — Persona scope and per-persona composition.** Universal
section composition or three render modes mirroring slice 6.7?
RESOLVED — see §12 **D-2** (`<this-slice>`): universal
composition; BE response stays persona-agnostic regardless.

**OQ-3 — Endpoint surface (single envelope vs split per-section).**
One `/learn/dashboard` returning the full envelope vs five
section endpoints?
RESOLVED — see §12 **D-3** (`<this-slice>`): single envelope
per §6.4 perf budget; future split is non-breaking.

**OQ-4 — Charting library for `RetentionCurveSection`.**
Hand-rolled SVG, `recharts`, or numeric-only tile?
RESOLVED — see §12 **D-4** (`<this-slice>`): hand-rolled SVG;
no new dep; replaceable with `recharts` when the admin retention
dashboard slice forces the lib decision.

**OQ-5 — Recall-rate definition.** Which py-fsrs ratings count as
recall in `overall_recall_rate`?
RESOLVED — see §12 **D-5** (`<this-slice>`): `rating IN (3, 4)`
(Good + Easy) only; `overall_lapse_rate` covers `rating == 1`
on the same shape.

**OQ-5b — Date bucketing for the daily-retention curve.** UTC
date or user-local via `email_preferences.timezone`?
RESOLVED — see §12 **D-6** (`<this-slice>`): user-local date;
matches gamification streak day-rollover semantics.

**OQ-6 — Default `retention_window_days` and toggle-in-v1.** 30d
no toggle / 7d no toggle / 30d with 7d-30d-90d toggle UI?
RESOLVED — see §12 **D-7** (`<this-slice>`): 30 days, no toggle
in v1; toggle defers unless D-11 telemetry surfaces demand.

**OQ-7 — Mastery threshold definition.** `state == 'review' AND
reps >= 3` / `state == 'review'` alone / FSRS stability-based?
RESOLVED — see §12 **D-8** (`<this-slice>`): `state == 'review'
AND reps >= 3`; `MASTERY_REPS_THRESHOLD = 3` lives at module
scope per §6.1.

**OQ-8 — Review-history shape and cap.** Cap value + window
coupling?
RESOLVED — see §12 **D-9** (`<this-slice>`): `MAX_RECENT_REVIEWS
= 20`, same window as retention; row click navigates to
`/learn/lesson/<lesson_id>`; no inline drawer in v1.

**OQ-9 — Tier-gating of the dashboard surface.** Free-allowed /
Pro-gated / free-allowed-with-premium-row-hidden?
RESOLVED — see §12 **D-10** (`<this-slice>`): page free-allowed
(no PaywallTrigger) + premium-deck mastery rows already filtered
by `curriculum_visibility` helpers (compound (a)+(c)).

**OQ-10 — Analytics events.** Single `dashboard_viewed`, two
events incl. `dashboard_section_clicked`, or zero events?
RESOLVED — see §12 **D-11** (`<this-slice>`): one event
`dashboard_viewed` once-per-mount via `useRef`; payload
`{persona, plan, is_cold_start, retention_window_days}`.

**OQ-11 — Profile.tsx coexistence vs migration.** Coexist v1
unchanged / coexist + file follow-up retirement B-### / inline
deprecation now?
RESOLVED — see §12 **D-12** (`<this-slice>`): coexist v1
unchanged. Follow-up B-### filed at slice 6.15 (cleanup) when
Phase-5 data sources retire.

**OQ-12 — Cold-start CTA copy variants.** Per-section / page-level
banner / both?
RESOLVED — see §12 **D-13** (`<this-slice>`): per-section copy
locked per the §10.4 component-test table; no page-level banner.

**OQ-13 — Session/window query param shape.** Single window
param / every constant exposed / no params at all?
RESOLVED — see §12 **D-14** (`<this-slice>`): `?retention_window_days=N`
only; `MAX_RECENT_REVIEWS` + `DEFAULT_REVIEW_HISTORY_WINDOW_DAYS`
stay hardcoded constants per §6.1.

---

## 15. Implementation slice forward-link

Implementation row: **B-080** 🔴 (filed by this slice).

Forward dependencies before impl can start:

1. **§12 amendment slice** locked D-1..D-14 from §14 OQ-1..OQ-13
   (incl. sub-OQ-5b) at `<this-slice>` (mirrors slice 6.0 / 6.4.5
   / 6.5 / 6.6 / 6.7 §12 amendment pattern at `e8eecdd` /
   `df58eaf` / `acba7ed` / `fb92396` / `0c21223`). ✅ shipped.
2. No BE primitive prerequisite — every data source is on disk:
   - `quiz_item_progress` (slice 6.1, `a989539`).
   - `quiz_review_events` + `lesson_view_events` (slice 6.0,
     `e7a0044`).
   - `gamification_stats` + `badges` (Phase 2, pre-Phase-6).
   - `curriculum_visibility` helpers (slice 6.6, `5011518`).

Impl slice expected scope:

- New file `app/services/dashboard_service.py` (~250-300 lines).
- New file `app/schemas/dashboard.py` (~80-120 lines).
- New file `app/api/v1/routes/dashboard.py` (~50-70 lines).
- `app/main.py` route mount addition (1 line + 1 import).
- Two new BE test files per §10.1 + §10.2 (~10-13 tests).
- New file `src/pages/Dashboard.tsx` (~200-300 lines per
  §12 D-2 universal composition).
- New file `src/hooks/useFsrsDashboard.ts` (~30-50 lines).
- Five new section components under `src/components/dashboard/`
  (~80-150 lines each; ~500-750 lines total).
- `src/services/api.ts` modification: `fetchFsrsDashboard` helper
  + `DashboardResponse` types (~40-60 lines added).
- `src/App.tsx` modification: `/learn/dashboard` route mount (1
  line + 1 import).
- `src/types/index.ts` additions: `DashboardResponse` + section
  type literals mirroring `app/schemas/dashboard.py`
  field-for-field (~50-80 lines).
- Six new FE test files per §10.3 + §10.4 (~11-15 tests).
- `.agent/skills/analytics.md` update: at most one new event row
  per §12 D-11 (one new event row).
- BACKLOG B-080 closure with impl SHA.
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new page + components +
  hook + types delta + new BE service + schema + route + main.py
  mount).

Impl test envelope (estimates, locked at impl):
- BE: **636 → ~646..649** (+10..+13).
- FE: **397 → ~408..412** (+11..+15).

R16 consumer-graph audit at impl Step 1: any new shared FE types
in `src/types/index.ts` (`DashboardResponse` + section types) need
their consumer graph audited. Predicted consumers: `services/api.ts`
(the `fetchFsrsDashboard` helper), `hooks/useFsrsDashboard.ts`,
`pages/Dashboard.tsx`, the five section components, plus their
test files. No external (e.g. admin or analytics) consumer
predicted, but verify against the live graph at impl time.

Out-of-scope at impl (cross-ref §13): admin-side cohort retention,
Profile.tsx migration, charting-library swap, window-toggle UI,
TopNav navigation entry, real-time updates, comparison surfaces.
