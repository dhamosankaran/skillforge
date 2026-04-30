# Phase 6 — Slice 6.11: Content-Quality Retention Dashboard (Admin Observability + `quality_score` Layer-3 Writeback)

## Status: 🔴 Drafted, §12 amended — D-1..D-16 locked at `d9bfcfc` from §14 OQ-A..OQ-P (mirrors slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 §12 amendment pattern at `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` / `0c21223` / `ab07168` / `be7d59a`); B-084 🔴 unchanged (impl not shipped).

| Field | Value |
|-------|-------|
| **Slice** | 6.11 (Track D — first content-quality observability slice; first non-NULL `quality_score` emitter) |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `7d7c6e8` (spec-author commit) |
| **BACKLOG row** | **B-084** 🔴 (filed by this slice) |
| **Depends on** | spec #00 (`docs/specs/phase-6/00-analytics-tables.md` — `quiz_review_events` + `lesson_view_events` source tables; shipped `e7a0044`) ▪ spec #01 (`docs/specs/phase-6/01-foundation-schema.md` — `lessons.quality_score` Numeric(3,2) NULLABLE column already on disk; shipped `a989539`) ▪ spec #07 (`docs/specs/phase-6/07-deck-lesson-ranker.md` — slice 6.6 D-2 `_avg_quality_score` null-coercion-to-0.5 contract this slice resolves; shipped `5011518`) ▪ spec #09 (`docs/specs/phase-6/09-fsrs-dashboard.md` — slice 6.8 D-5 rating semantics for recall/lapse + D-11 admin-internal event convention; shipped `0968a13`) ▪ spec #10 (`docs/specs/phase-6/10-ai-ingestion-pipeline.md` — slice 6.10 admin auth chain + `internal: true` admin-event convention + drafts pipeline writes `quality_score=NULL`; shipped `8735373`) ▪ existing `Depends(require_admin)` + `audit_admin_request` chain (`app/core/deps.py`) ▪ existing `slowapi` rate limiter (`app/core/rate_limit.py`). |
| **Blocks** | Slice 6.13.5 (`card_quality_signals` table per LD J2 — finer-grained per-(lesson, quiz_item, signal_source, dimension) layer-1 + layer-3 unified storage). Slice 6.13 (whatever ships between today and 6.13.5; cross-ref at amendment time). |
| **Cross-refs** | scout `docs/audits/phase-6-scout.md` slice 6.11 framing (caveat: scout numbering may pre-date Phase 6 re-sequencing; on-disk progression is authoritative — see §1.1 finding #1 below); `curriculum.md` §7 three-layer quality skeleton (this slice = layer 3 writeback) + §8 ranker contract D-2 (`_avg_quality_score` null-coercion this slice starts populating); `analytics.md` (catalog discipline + `internal: true` admin-event convention + Postgres event tables §I1); `study-engine.md` (FSRS Rating semantics 1-4 for pass/fail derivation); SESSION-STATE Phase 6 LDs **I1** (dual-write Postgres events — this slice consumes), **J2** (`card_quality_signals` — slice 6.13.5 supersedes this slice's writeback shape). |

> **Slice numbering note (info-only):** scout audit `docs/audits/phase-6-scout.md` slice-by-slice block was annotated at `7036968` for slices 6.8 / 6.14 numbering drift. Slice 6.11's scout framing line may not match current on-disk topic mapping; the SESSION-STATE Phase 6 specs block + on-disk filename progression are authoritative per AGENTS.md tier-1. See §1.1 finding #1.

---

## 1. Problem

The Phase-6 curriculum platform now has every load-bearing primitive
in place to *produce* and *serve* content: schema (slice 6.1), FSRS
scheduler (slice 6.2), lesson-card UX (slice 6.3), admin authoring
shell + services (slice 6.4 / 6.4b), reference seed corpus (slice
6.4.5), read-time invariant chain (slice 6.5), Lens-ranked deck
ordering (slice 6.6), persona-aware Learn page (slice 6.7), user-self
FSRS dashboard (slice 6.8), AI ingestion pipeline (slice 6.10
B-083a + B-083b). Two distinct event streams write to Postgres
alongside PostHog (slice 6.0 dual-write per LD I1):
`quiz_review_events` and `lesson_view_events`.

What does **not** yet exist is any *content-side* observability —
*which* lessons are users failing, *which* quiz_items have low pass
rates, *which* decks have high abandonment? The user-self dashboard
(slice 6.8) answers "how is *this user* doing?"; this slice answers
the orthogonal question: "how is *this content* doing across all
users?".

Three concrete gaps motivate this slice:

- **`lessons.quality_score` stays NULL on every lesson.** The column
  exists since slice 6.1 (`Numeric(3,2) NULLABLE`); the ranker
  null-coerces to 0.5 per slice 6.6 D-2 (`_avg_quality_score`
  fallback). No code path ever sets a non-NULL value today —
  hand-authored content stays NULL by definition (slice 6.4b admin
  routes don't touch the column), seed corpus stays NULL (slice
  6.4.5 loader doesn't set it), AI-ingested drafts stay NULL (slice
  6.10 worker doesn't set it on draft creation per §1.1 finding
  #7). The ranker's `0.10 * avg_quality_score` weight is therefore
  a constant 0.05 contribution today — the signal is dormant.
- **Admin has no visibility into per-content retention.** Admins
  who edit the seed corpus or publish AI drafts have no on-disk
  surface that says "lesson X has 80 reviews and a 35% recall rate
  — your edit didn't land". The slice 6.4b editor pages
  (`pages/admin/AdminLessonEditor.tsx`, `AdminQuizItems.tsx`) are
  authoring views, not retention views. The slice 6.8 dashboard is
  user-self, not admin-cohort.
- **`/admin/analytics` is org-level, not content-level.**
  `admin_analytics_service.py` (468 lines, `get_metrics_summary` +
  `get_performance_summary`) covers PRD §1.4 OKRs (registered
  users, paying Pro, DAU/MAU, avg streak, ATS-to-Pro conversion,
  monthly churn) + LLM spend + Stripe webhook success. It does
  not touch `lessons` / `quiz_items` / `decks` rows at all (audit
  finding #5). The content-quality surface is greenfield.

Slice 6.11 closes all three by introducing:

1. **A new admin-only aggregator service** that computes per-deck
   + per-lesson + per-quiz_item recall/lapse stats from
   `quiz_review_events` over a 30-day window (audit finding #4
   confirms the four indexes exist; no migration needed).
2. **A first non-NULL `quality_score` writeback path** to
   `lessons.quality_score` derived from a **Bayesian-smoothed
   pass_rate** (curriculum.md §7 layer-3 — *user signal aggregate*).
   The ranker (slice 6.6) reads it transparently when non-NULL;
   null-coercion stays as the fallback for cold-start lessons.
3. **A new admin-only single-envelope dashboard** at
   `/admin/content-quality` mirroring slice 6.8's
   `DashboardResponse` envelope precedent so the FE renders one
   page from one fetch.

This slice is the **first user of `quiz_review_events` for a
content-side rollup** (slice 6.8 reads them user-scoped). It is
the **first emitter** of any non-NULL `quality_score` row in the
codebase. It is **read-only over user data** (no writes to
`quiz_item_progress`, `quiz_review_events`, `lesson_view_events`,
or any user-owned table); the only writes are to
`lessons.quality_score` per G-3.

The dashboard is **admin-only in v1** (G-1) — no user-facing
surface. The product loop is "admin opens
`/admin/content-quality` → sees ranked list of lowest-quality
lessons + per-deck rollup → clicks through to existing slice 6.4b
authoring pages to revise". User-facing quality signals (e.g.
"this lesson is rated 4.8/5") are explicitly out of scope and not
implied to come later — slice 6.13.5 (layer-1 unified table) is
the long-term home for finer-grained signals.

### 1.1 Step 0 audit findings

Audit reads at HEAD `057ff93` (post-watermark, post-slice-6.10b
SHA-backfill):

1. **Scout slice 6.11 framing vs current on-disk numbering:
   verified non-blocking.** Scout audit `docs/audits/phase-6-scout.md`
   was annotated at `7036968` for slices 6.8 / 6.14 numbering drift
   (post-resequencing). Slice 6.11's scout framing line at `:881-1022`
   may number this topic differently than the current on-disk
   progression. The authoritative slice → spec mapping is the
   SESSION-STATE Phase 6 specs block + on-disk filename progression;
   per AGENTS.md tier-1, on-disk wins. This spec uses the on-disk
   slot (next-free filename `11-content-quality-retention.md` after
   `10-ai-ingestion-pipeline.md`). Information-only — no §12 lock
   needed.

2. **`lessons.quality_score: Numeric(3,2) NULLABLE` confirmed on
   disk** at `app/models/lesson.py:63` (slice 6.1 `a989539`). The
   column has `Mapped[Decimal | None]` with no server default and
   no value written by any path on disk today. Slice 6.6 ranker
   null-coerces to 0.5 in `_avg_quality_score` per D-2
   (`app/services/curriculum_visibility.py` / `deck_ranker_service.py`).
   This slice's writeback is the first non-NULL emitter. Contract:
   **non-NULL value must lie in [0.00, 1.00]** so the ranker's
   weighted-sum formula stays bounded (D-2 contract is implicit
   bound; this slice locks it explicitly via §6 service docstring +
   Pydantic constraint).

3. **`quiz_items.quality_score` does NOT exist on disk** at
   `app/models/quiz_item.py:32-93`. No corresponding column, no
   index, no migration. This is the **single largest scope decision
   of the slice** — see §6 + §7 + §12 D-5 + §12 D-9. Three valid v1
   shapes: (a) **lesson-level only** writeback (zero migrations),
   (b) **add `quiz_items.quality_score: Numeric(3,2) NULLABLE`** in
   §7 and write per-quiz_item too, (c) **defer all non-lesson
   surfaces to slice 6.13.5** when LD J2's `card_quality_signals`
   table lands. Default proposal at §12 amendment time: (a)
   lesson-level only — minimum spec surface, zero migration risk,
   matches the ranker's slice 6.6 D-2 read-side contract which
   only reads `lessons.quality_score`. Per-quiz_item rollups are
   surfaced *in the dashboard payload* (admin can see them) but
   **not written back to disk** in v1; slice 6.13.5's
   `card_quality_signals` table is the proper home.

4. **`card_quality_signals` table absent on disk** — confirmed by
   `find hirelens-backend/app -name '*.py' | xargs grep -l
   "card_quality_signals\|CardQualitySignal"` returning no hits.
   Greenfield as expected per LD J2 ("Built in slice 6.13.5"). No
   drift to flag. v1 of this slice does NOT introduce the table —
   the writeback path uses the existing `lessons.quality_score`
   column only.

5. **`quiz_review_events` indexes exhaustive — no new index
   needed.** All four lookup keys exist at
   `app/models/analytics_event.py:83-103`:
   - `ix_quiz_review_events_user_reviewed_at (user_id, reviewed_at)`
   - `ix_quiz_review_events_quiz_item_reviewed_at (quiz_item_id, reviewed_at)`
   - `ix_quiz_review_events_lesson_reviewed_at (lesson_id, reviewed_at)`
   - `ix_quiz_review_events_deck_reviewed_at (deck_id, reviewed_at)`

   The aggregation reads (per-deck rollup, per-lesson rollup,
   per-quiz_item rollup, all over a 30-day reviewed_at window) all
   hit a leftmost-prefix-supported index. No migration required.

6. **`lesson_view_events` indexes also exhaustive** for view-volume
   denominator. Three indexes at `app/models/analytics_event.py:142-158`:
   - `ix_lesson_view_events_user_viewed_at (user_id, viewed_at)`
   - `ix_lesson_view_events_lesson_viewed_at (lesson_id, viewed_at)`
   - `ix_lesson_view_events_deck_viewed_at (deck_id, viewed_at)`

   Available if §6.1 needs a "views vs reviews" denominator for
   "how many users opened this lesson but never finished a quiz?"
   — see §12 D-14.

7. **Slice 6.10 worker does NOT write `quality_score` on draft
   creation.** Confirmed by `grep -n "quality_score"
   hirelens-backend/app/jobs/ingestion_worker.py
   hirelens-backend/app/services/ingestion_service.py` returning no
   hits. AI-ingested lessons land with `published_at IS NULL` and
   `quality_score IS NULL`. Slice 6.11's writeback is therefore
   safe — there is no critique-derived initial score to overwrite.
   When slice 6.13.5's layer-1 unified table ships, it can write
   to `card_quality_signals` instead and this slice's path migrates
   to read the unified table. **No coordination flag needed today.**

8. **`admin_analytics_service.py` exists but does NOT touch
   curriculum content** — confirmed by `grep -n "Lesson|QuizItem|
   published_at|retired_at|tier|persona_visibility"` returning only
   tier-mapping hits in `_FEATURE_TIER` (LLM spend attribution),
   not curriculum reads. Slice 6.11 stands up a **new service**
   (`app/services/admin_content_quality_service.py`) — extending
   `admin_analytics_service.py` would mix orthogonal concerns
   (org-level OKRs vs content-quality rollups), the file would
   double in size (~468 → ~700+ lines), and the test surface would
   re-stratify. New-service decision is tactical (per Q1 simplicity);
   the long-term unification opportunity is filed as a §13
   forward-link.

9. **Admin route mount precedent confirmed.** Five admin routers
   in `app/main.py:25-28, 141-151`:
   `admin_analytics` / `admin_decks` / `admin_ingest` / `admin_lessons`
   / `admin_quiz_items` (plus legacy `admin.py`). Each uses
   `APIRouter(dependencies=[Depends(audit_admin_request)])` +
   per-route `Depends(require_admin)`. Slice 6.11's
   `admin_content_quality.py` follows verbatim — alphabetical
   mount ordering places it between `admin_analytics` and
   `admin_decks` in `app/main.py`.

10. **FE admin shell mount confirmed** at `App.tsx:113-115`:
    `<ProtectedRoute><AdminGate><AdminLayout /></AdminGate></ProtectedRoute>`.
    Existing admin pages under `pages/admin/` (slice 6.4a / 6.4b
    convention): `AdminCards.tsx` / `AdminDecks.tsx` /
    `AdminDeckDetail.tsx` / `AdminLessons.tsx` /
    `AdminLessonEditor.tsx` / `AdminQuizItems.tsx`. Plus older
    convention at top level: `AdminAnalytics.tsx` (Phase 5 spec
    #38 surface). Slice 6.11 lands under `pages/admin/`
    (`AdminContentQuality.tsx`) per current convention; mounted
    inside the `AdminLayout` outlet.

11. **PostHog event surface for retention dashboard, enumerated.**
    BE-emitted: `quiz_item_reviewed` (dual-writes to
    `quiz_review_events` per slice 6.0 I1 contract). FE-emitted:
    `lesson_viewed` (dual-writes to `lesson_view_events` via the
    BE `POST /api/v1/lessons/:id/view-event` route +
    `recordLessonView` helper at `services/api.ts:401`),
    `lesson_section_expanded` (FE-only, NOT dual-written per
    analytics.md §I1). Plus admin-side precedent:
    `admin_analytics_segment_changed` (FE) +
    `admin_analytics_viewed` (BE side-fire from
    `audit_admin_request`). Slice 6.11's new event surface =
    one event `admin_content_quality_viewed` with
    `internal: true` mirroring slice 6.8 D-11
    (`dashboard_viewed` once-per-mount) + slice 6.10 D-13
    (admin-internal `internal: true` convention).

12. **`quiz_review_events` rating semantics carry from slice 6.8
    D-5.** py-fsrs Rating { Again=1, Hard=2, Good=3, Easy=4 };
    slice 6.8 D-5 locked recall = (3, 4); lapse = (1); Hard=2
    excluded from both. Slice 6.11 should mirror this convention
    so admin-side and user-self dashboards stay coherent — a
    "lesson is failing for users" signal computed off ratings
    1+2+3+4 vs 3+4 would not match the user dashboard's "you
    recalled 78% of cards" copy. **Default proposal: mirror D-5.**
    Locked at §12 D-13.

13. **Existing seed corpus is the v1 content universe.** Slice
    6.4.5 (B-071, `ac5b905`) shipped 12 decks × 2 lessons per deck
    = 24 lessons + ~72 quiz_items (3 per lesson average). The
    full-table scan for "compute pass_rate for every lesson" is
    cheap at this volume — no pagination needed in v1, no
    caching needed (mirrors slice 6.6 D-12 ranker decision; the
    universe is bounded). When the catalogue grows past ~500
    lessons or the dashboard request latency exceeds ~500ms,
    revisit (see §13).

14. **Slice 6.10 ingestion writes drafts with
    `quality_score=NULL`** (cross-ref finding #7). The writeback
    path in this slice MUST be **idempotent** — re-aggregating
    the same window must produce the same `quality_score` value,
    and re-running the writeback must overwrite cleanly without
    creating drift. Implementation: `UPDATE lessons SET
    quality_score = X WHERE id = Y AND (quality_score IS DISTINCT
    FROM X)` semantics (Postgres `IS DISTINCT FROM` handles
    NULL → value transition cleanly). One write per lesson per
    invocation max — cap is bounded by the lesson universe.

### 1.2 Why this matters

The ranker's `0.10 * avg_quality_score` term (slice 6.6 D-1) is
a **dormant signal** today. Every lesson contributes 0.5 (the
null-coercion fallback). Once this slice ships, lessons with
genuinely low pass rates start ranking lower — the Lens-ranked
Learn page (slice 6.7) starts demoting weak content automatically.
This is the **first feedback loop** in the Phase-6 quality model:
real review behaviour starts shaping what users see next.

For admins, the dashboard is the **first surface that says
"your work matters"**. The slice 6.4b editor pages produce
content; this slice produces evidence. Without it, the AI
ingestion pipeline (slice 6.10) is a one-way street — drafts
land, admins publish, no signal flows back. With it, admins can
ship a draft, watch its quality_score evolve over a week, and
either (a) leave it published if recall holds, (b) edit it via
slice 6.4b's substantive-edit cascade if recall craters and the
quiz_items need replacement, or (c) archive it via
`admin_lesson_archived` if it's irrecoverable.

The slice is also **load-bearing for slice 6.13.5**. LD J2's
`card_quality_signals` table is keyed on
`(id, lesson_id, quiz_item_id NULLABLE, signal_source,
dimension)`. Slice 6.11's lesson-level writeback is *the
prototype* — it answers "what shape does a layer-3 user-signal
aggregate look like in practice?" before slice 6.13.5 commits
the table schema. If slice 6.11's Bayesian-smoothed pass_rate
turns out to be the wrong shape (e.g., admins want
recall-trend-direction instead of point-in-time recall), slice
6.13.5 absorbs the lesson and ships the right thing.

---

## 2. Goals

- **G-1** **Admin-only access.** Mount under `/api/v1/admin/*`
  using the existing `Depends(require_admin)` +
  `audit_admin_request` chain (mirror slice 6.10 G-4). Non-admin
  authed → 403; unauthed → 401. No tier-based access control —
  admin status is binary.

- **G-2** **Read-only over user data.** Zero writes to
  `quiz_item_progress`, `quiz_review_events`, `lesson_view_events`,
  `users`, `subscriptions`, or any user-owned table. The only
  writes are to `lessons.quality_score` per G-3 below.

- **G-3** **First emitter of layer-3 `quality_score` v1.** Derive
  a non-NULL value for `lessons.quality_score` from a
  Bayesian-smoothed pass_rate over `quiz_review_events` (rating
  semantics per audit finding #12 + §12 D-13 lock). Lessons below the
  minimum-review threshold (§12 D-4) stay NULL → ranker keeps the
  0.5 fallback per slice 6.6 D-2 — no behavioural delta for
  cold-start lessons. Idempotent UPDATEs (audit finding #14).

- **G-4** **Surface problem content for admin authoring action.**
  The dashboard ranks content by *worst-first* signals — low
  pass rate, high lapse rate, low review volume below threshold,
  high view-vs-review-volume ratio (audit finding #6) — so admins
  can prioritize their next edit cycle. Each row links back to
  the slice 6.4b editor pages.

- **G-5** **Reuses existing analytics tables.** Zero new event
  tables. Reads from `quiz_review_events` (slice 6.0) and
  optionally `lesson_view_events` (per §12 D-14 lock); both indexed
  exhaustively per audit findings #5 + #6.

- **G-6** **Reuses slice 6.10 admin auth chain.** No new admin
  infra (no new RQ workers, no new R2 buckets, no new auth
  primitives). The dashboard is a synchronous read against
  Postgres + a single UPDATE per lesson per request (G-3). No
  background jobs.

- **G-7** **Single envelope dashboard surface.** One
  `GET /api/v1/admin/content-quality` returns
  `AdminContentQualityResponse` with all sections (per-deck
  rollup, per-lesson worst-first list, per-quiz_item worst-first
  list) — mirrors slice 6.8 `DashboardResponse` precedent so the
  FE renders one page from one fetch (no waterfall, no per-section
  endpoints). Optional query params for windowing (§12 D-3 lock) +
  archived-toggle (§12 D-8 lock).

---

## 3. Non-goals (out-of-scope this slice)

- **User-facing quality surfaces.** No "this lesson is rated
  4.8/5" badges anywhere user-visible; no per-quiz_item stars on
  Learn.tsx; no quality-based filtering in the FSRS daily review
  queue. Quality drives ranker scores transparently (G-3) but is
  never directly user-visible. Future user-facing layer (if
  needed) is a distinct spec.

- **Per-quiz_item `quality_score` writeback.** Per audit finding
  #3, `quiz_items.quality_score` does not exist on disk. v1
  default proposal: surface per-quiz_item rollups *in the
  dashboard payload* (admins see them), but do NOT add the
  column or write back to disk. Slice 6.13.5's
  `card_quality_signals` table is the long-term home for
  per-quiz_item signals — adding the column now would create
  drift that slice 6.13.5 would have to migrate around.

- **Layer-1 critique scores.** Slice 6.10's AI ingestion pipeline
  produces a `CritiqueSchema` payload with per-dimension scores
  (clarity, accuracy, etc.) that becomes layer-1 quality data.
  Slice 6.11 does NOT consume the critique payload — it sits at
  layer 3 (user signals) only. Layer-1 storage and reads are
  slice 6.13.5 territory.

- **`card_quality_signals` table.** LD J2 explicitly assigns the
  table to slice 6.13.5; this slice does not introduce it. The
  writeback path uses the existing `lessons.quality_score`
  column only.

- **User-thumbs feedback ingestion.** Slice 6.13.5's third
  signal source (user thumbs up/down per
  `analytics.md` §gamification or per a future feedback widget)
  is layer-3 user-signal too, but the *trigger* is explicit
  thumb-press, not implicit review behaviour. Slice 6.11 derives
  signal from FSRS reviews only.

- **Real-time / SSE updates.** The dashboard is a snapshot
  refreshed on page load (mirror slice 6.8 D-12). No
  WebSocket / SSE / polling endpoints. Admin reload triggers
  recompute.

- **Cron-driven recomputation.** No background job recomputes
  quality_score on a schedule. v1 writeback fires synchronously
  on every dashboard load (§12 D-1) — bounded by
  the per-admin slowapi rate limit (G-6 implicit). Background
  recomputation is a slice 6.14 / future-cron territory.

- **Cross-deck normalization.** v1 reports raw pass_rates +
  Bayesian-smoothed scores per lesson; it does NOT normalize
  across decks (e.g., "lesson X is in the bottom 10% within its
  deck"). Cross-deck comparisons are an admin's mental task in
  v1; ranking-within-deck is a future-spec consideration.

- **Export / CSV / PDF.** No data export from the dashboard.
  Admin reads on screen. Export is a future-spec consideration if
  the volume of content + signals grows past visual-scan capacity.

- **Comparison / time-series / "did my edit help?" diffs.** v1
  is point-in-time only — pass_rate over the last 30 days. No
  "before-edit vs after-edit" delta surface. Slice 6.4b's
  `lessons.version` + `version_type` columns + `admin_lesson_*`
  events have the data shape to support this in a future slice;
  v1 leaves the surface unbuilt to keep scope bounded.

---

## 4. Architecture

### 4.1 Component graph (new files)

```
hirelens-backend/
  app/
    services/
      admin_content_quality_service.py   ← NEW (~250-350 lines)
        ↓ reads
        QuizReviewEvent (slice 6.0 I1 dual-write source)
        LessonViewEvent (slice 6.0 I1 dual-write source; per §12 D-14)
        Lesson, QuizItem, Deck (slice 6.1 ORM)
        ↓ writes
        Lesson.quality_score (idempotent UPDATE per finding #14)
    schemas/
      admin_content_quality.py           ← NEW (~120-180 lines)
        AdminContentQualityResponse       ← top-level envelope
        DeckQualityRow                    ← per-deck rollup
        LessonQualityRow                  ← per-lesson worst-first row
        QuizItemQualityRow                ← per-quiz_item worst-first row
    api/v1/routes/
      admin_content_quality.py           ← NEW (~50-80 lines)
        GET  /api/v1/admin/content-quality

hirelens-frontend/
  src/
    pages/admin/
      AdminContentQuality.tsx            ← NEW (~200-300 lines)
    hooks/
      useAdminContentQuality.ts          ← NEW (~50-80 lines)
    components/admin/
      content-quality/
        DeckRollupTable.tsx              ← NEW (~80-120 lines)
        WorstLessonsTable.tsx            ← NEW (~80-120 lines)
        WorstQuizItemsTable.tsx          ← NEW (~80-120 lines)
    services/
      api.ts                              ← MODIFIED (+1 helper)
    types/
      index.ts                            ← MODIFIED (+4 types)
    App.tsx                               ← MODIFIED (+1 route)
```

### 4.2 Data flow

```
admin opens /admin/content-quality
   │
   ▼
useAdminContentQuality() → GET /api/v1/admin/content-quality?window_days=30&include_archived=false
   │
   ▼
require_admin + audit_admin_request side-fire admin_analytics_viewed event
   │
   ▼
admin_content_quality_service.aggregate_dashboard(db, *, window_days=30, include_archived=False)
   │
   ├─→ scan visible lessons (Lesson + Deck join, archived filter per request flag)
   │   ↓
   ├─→ scan quiz_review_events for window (per-lesson + per-quiz_item rollup)
   │   ↓
   ├─→ scan lesson_view_events for window (per-lesson view-volume, per §12 D-14)
   │   ↓
   ├─→ compute pass_rate + Bayesian-smoothed pass_rate + lapse_rate + review_count
   │   per lesson and per quiz_item
   │   ↓
   ├─→ if review_count >= MIN_REVIEW_THRESHOLD (§12 D-4), UPDATE lessons.quality_score
   │   (idempotent IS DISTINCT FROM gate per finding #14)
   │   ↓
   ├─→ aggregate per-deck rollup (sum review_count, weighted-avg pass_rate)
   │   ↓
   └─→ build AdminContentQualityResponse envelope
   │
   ▼
FE renders 3 sections (deck rollup, worst lessons, worst quiz_items)
   │
   ▼
admin clicks lesson row → navigates to /admin/lessons/:id/edit (slice 6.4b editor)
```

Single-pass aggregation (one Postgres round-trip per source
table). No fanout to RQ. Total wall-clock ≤ 500ms target at 24
lessons + ~72 quiz_items + 30-day window. Performance envelope
locked at §6.4.

### 4.3 Failure modes + recovery

- **Empty `quiz_review_events` table** (cold-start, fresh DB):
  every lesson reports `review_count=0`, `pass_rate=None`,
  `quality_score=None` (writeback skipped). Dashboard renders an
  empty-state banner; no rows.
- **Lesson with N reviews where N < MIN_REVIEW_THRESHOLD (§12 D-4):**
  rolls up `pass_rate` for display (admin can see early signal)
  but writeback is **skipped** — `quality_score` stays NULL on
  disk; ranker keeps 0.5 fallback. Dashboard tags the row with
  `low_volume: true` so admin knows the score is provisional.
- **One UPDATE failure (e.g., a row got archived between SELECT
  and UPDATE):** logged at WARNING; the rest of the batch
  continues. Mirrors slice 6.6 D-16 partial-failure-skip
  pattern.
- **Aggregation query timeout:** the service catches
  `SQLAlchemyError` at the top level and returns a
  structured 500 with `detail='content_quality_aggregation_failed'`.
  Admin retries on next page-load. No background recovery.
- **Dashboard request from non-admin:** 403 from
  `Depends(require_admin)` before the service runs (G-1).
- **Concurrent dashboard loads from two admins within seconds:**
  both writebacks run; the `IS DISTINCT FROM` gate makes the
  second one a no-op for unchanged rows. No locking, no race.

### 4.4 Cross-cutting composition rules

- **R11 LLM router:** zero LLM calls in this slice. Quality
  computation is pure SQL aggregation + Python arithmetic. Not
  load-bearing on `llm_router.py`.
- **R12 design tokens:** every FE color / spacing / shadow uses
  tokens via Tailwind utilities (`bg-bg-surface`,
  `text-text-primary`, `border-border-accent`). No hardcoded
  hex (mirror slice 6.8 + slice 6.7 precedent).
- **R13 integration tests:** zero integration-marked tests in
  this slice. All tests run under default `-m "not integration"`.
- **R15(c) closure:** B-084 forward-files at status 🔴 in this
  spec-author slice; closure happens in the impl commit.
- **R16 audit at impl Step 1:** any new shared BE types
  (`AdminContentQualityResponse` / `DeckQualityRow` /
  `LessonQualityRow` / `QuizItemQualityRow`) need consumer-graph
  audited. Predicted consumers:
  `admin_content_quality_service`, `admin_content_quality.py`
  route, plus their test files. Predicted FE consumers:
  `useAdminContentQuality`, `AdminContentQuality.tsx`, the three
  table components. No external consumer (e.g. cards / study /
  mission) predicted.

---

## 5. Schemas

### 5.1 `AdminContentQualityResponse` (top-level envelope)

New file `app/schemas/admin_content_quality.py`. Mirrors slice
6.8's `DashboardResponse` envelope shape — single response with
N section payloads.

```python
class AdminContentQualityResponse(BaseModel):
    """Single-envelope admin content-quality dashboard response.

    G-7: one fetch renders the whole page. All sections present
    on every response (including cold-start with empty section
    payloads).
    """
    window_days: int                              # echo of request param
    include_archived: bool                        # echo of request param
    generated_at: datetime
    is_cold_start: bool                           # true iff zero reviews in window
    decks: list[DeckQualityRow]
    worst_lessons: list[LessonQualityRow]         # bottom-N by quality_score
    worst_quiz_items: list[QuizItemQualityRow]    # bottom-N by pass_rate
    writebacks_applied: int                       # how many lessons.quality_score were UPDATEd this request
```

### 5.2 `DeckQualityRow` (per-deck rollup)

```python
class DeckQualityRow(BaseModel):
    deck_id: str
    deck_slug: str
    deck_title: str
    tier: Literal["foundation", "premium"]
    persona_visibility: Literal["climber", "interview_prepper", "both"]
    archived: bool                                # echo of deck.archived_at IS NOT NULL
    lesson_count: int                             # active visible lessons in deck
    review_count_window: int                      # sum of reviews in window across deck's lessons
    weighted_pass_rate: float | None              # review-count-weighted mean of per-lesson pass_rates
    avg_quality_score: float | None               # mean of non-NULL lessons.quality_score values
```

### 5.3 `LessonQualityRow` (per-lesson worst-first)

```python
class LessonQualityRow(BaseModel):
    lesson_id: str
    lesson_slug: str
    lesson_title: str
    deck_id: str
    deck_slug: str
    review_count_window: int
    view_count_window: int                        # from lesson_view_events per §12 D-14
    pass_rate: float | None                       # raw pass_rate; None if review_count_window == 0
    smoothed_quality_score: float | None          # Bayesian-smoothed; None if low-volume below MIN threshold
    persisted_quality_score: float | None         # current lessons.quality_score on disk (post-writeback)
    low_volume: bool                              # true iff review_count_window < MIN_REVIEW_THRESHOLD
    archived: bool
    published_at: datetime | None
```

### 5.4 `QuizItemQualityRow` (per-quiz_item worst-first)

```python
class QuizItemQualityRow(BaseModel):
    quiz_item_id: str
    lesson_id: str
    deck_id: str
    question_preview: str                         # first 80 chars of question (no full question — visual scan only)
    review_count_window: int
    pass_rate: float | None                       # raw; None if review_count_window == 0
    lapse_rate: float | None                      # rating==1 / total_reviews
    low_volume: bool
    retired: bool                                 # echo of quiz_item.retired_at IS NOT NULL
```

### 5.5 Request shape

`GET /api/v1/admin/content-quality` accepts query params:

- `window_days: int = 30` (clamp [7, 90] per §12 D-3 lock)
- `include_archived: bool = False` (per §12 D-8 lock)

No request body. No POST today (the only writeback is
synchronous as a side-effect of the GET — see G-6 + §12 D-1).

---

## 6. Backend

### 6.1 New service — `app/services/admin_content_quality_service.py`

Public API (single entry point):

```python
async def aggregate_dashboard(
    db: AsyncSession,
    *,
    window_days: int = 30,
    include_archived: bool = False,
) -> AdminContentQualityResponse:
    """Aggregate content-quality dashboard + writeback quality_score.

    Returns a populated AdminContentQualityResponse envelope.
    Side-effect: idempotent UPDATEs to lessons.quality_score for
    every lesson where review_count_window >= MIN_REVIEW_THRESHOLD
    AND the smoothed score differs from the persisted value.

    Read-only over all user-owned tables (G-2). Reads:
      - Lesson + Deck join (archived filter per param)
      - QuizReviewEvent (per-lesson + per-quiz_item aggregation)
      - LessonViewEvent (view-volume denominator; §12 D-14)
    Writes:
      - Lesson.quality_score (idempotent IS DISTINCT FROM gate)
    """
```

Module constants (locked at §12 D-2 + D-3 + D-4):

```python
DEFAULT_WINDOW_DAYS = 30                   # §12 D-3
MIN_WINDOW_DAYS = 7                        # §12 D-3 lower clamp
MAX_WINDOW_DAYS = 90                       # §12 D-3 upper clamp
MIN_REVIEW_THRESHOLD = 10                  # §12 D-4
WORST_LESSONS_CAP = 25                     # number of rows in worst_lessons
WORST_QUIZ_ITEMS_CAP = 50                  # number of rows in worst_quiz_items
QUESTION_PREVIEW_CHARS = 80                # for QuizItemQualityRow.question_preview

# Bayesian smoothing prior: 0.5 (neutral) with prior weight = MIN_REVIEW_THRESHOLD
SMOOTHING_PRIOR_PASS_RATE = 0.5
SMOOTHING_PRIOR_WEIGHT = 10                # equals MIN_REVIEW_THRESHOLD by symmetry

# Rating semantics from slice 6.8 D-5 (audit finding #12)
_RECALL_RATINGS = (3, 4)                   # Good + Easy
_LAPSE_RATING = 1                          # Again
# Hard (rating=2) excluded from both per slice 6.8 D-5
```

Bayesian smoothing formula (locked at §12 D-2):

```python
smoothed = (passes + SMOOTHING_PRIOR_PASS_RATE * SMOOTHING_PRIOR_WEIGHT) / \
           (review_count + SMOOTHING_PRIOR_WEIGHT)
```

Where `passes = count(rating in (3,4))` per slice 6.8 D-5. The
prior pulls low-volume lessons toward 0.5 — a lesson with 5
reviews and 3 passes (raw 0.6) smooths to
`(3 + 0.5*10) / (5 + 10) = 8/15 = 0.533`. A lesson with 100
reviews and 60 passes (raw 0.6) smooths to
`(60 + 5) / (100 + 10) = 65/110 = 0.591`. The prior dampens
small-sample volatility without dominating the signal at scale.

Writeback gate (per audit finding #14):

```python
if review_count_window >= MIN_REVIEW_THRESHOLD:
    new_score = round(smoothed, 2)        # Numeric(3,2) precision
    # IS DISTINCT FROM handles NULL → value cleanly + skips no-ops
    await db.execute(
        update(Lesson)
        .where(Lesson.id == lesson_id)
        .where(Lesson.quality_score.is_distinct_from(new_score))
        .values(quality_score=new_score)
    )
    writebacks_applied += 1
```

Note `is_distinct_from` is the SQLAlchemy 2.0 way to express
Postgres `IS DISTINCT FROM` semantics; for pre-2.0 SQLAlchemy
fall back to `or_(Lesson.quality_score != new_score,
Lesson.quality_score.is_(None))`. (Pin the canonical expression
at impl per §6 helper signatures.)

Reuses curriculum visibility helpers from
`app/services/curriculum_visibility.py` (slice 6.6 D-6 extraction)
to apply the visibility filter chain when `include_archived=False`
— specifically `archived_at IS NULL` on Deck + Lesson; persona
filter is **not** applied (admin views all personas — G-1).

### 6.2 New route — `app/api/v1/routes/admin_content_quality.py`

```python
router = APIRouter(
    prefix="/admin",
    tags=["admin-content-quality"],
    dependencies=[Depends(audit_admin_request)],
)


@router.get("/content-quality", response_model=AdminContentQualityResponse)
async def get_content_quality(
    window_days: int = Query(30, ge=7, le=90),
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> AdminContentQualityResponse:
    return await aggregate_dashboard(
        db,
        window_days=window_days,
        include_archived=include_archived,
    )
```

Route mounts in `app/main.py` between `admin_analytics` and
`admin_decks` per audit finding #9 alphabetical convention.

### 6.3 Performance envelope

- **24 lessons + 72 quiz_items (current corpus, audit finding
  #13) + 30-day window:** target ≤ 500ms wall-clock per request,
  including writeback. Three indexed reads
  (`quiz_review_events` by lesson, by quiz_item, by deck) + one
  batched `UPDATE` for writebacks. No pagination, no caching.
- **Scaling beyond ~500 lessons / 5000 quiz_items:** revisit per
  §13 forward-link. Likely additions: pagination on worst_lessons
  / worst_quiz_items; per-deck filter param; Redis-cached
  aggregation with 5-minute TTL mirroring
  `admin_analytics_service` precedent.

### 6.4 Reuse of existing services

- **`app/services/curriculum_visibility.py`** — `archived_at`
  filter helpers; persona filter intentionally not applied
  (admin sees all personas).
- **`Depends(require_admin)` + `audit_admin_request`** — auth
  chain unchanged from slice 6.10 G-4.
- **Pydantic v2 `BaseModel`** — schemas follow established
  conventions; no special config needed beyond `from_attributes=True`
  if the service returns ORM rows.
- **`slowapi` rate limiter** — admin routes already inherit the
  global default (100/min); a per-admin per-route limiter is NOT
  needed for v1 (the page is admin-only and synchronous; abuse
  risk is bounded by admin status).

---

## 7. Migrations

**Zero migrations.** The default proposal at §12 amendment time
(§12 D-5 + D-9 lock "lesson-level only") requires no schema
change — `lessons.quality_score` already exists on disk per
audit finding #2.

(D-5 alternative — not the locked path:) if a future amendment flips D-5 to "add `quiz_items.quality_score`
column", §7 would gain one Alembic migration adding the
`Numeric(3,2) NULLABLE` column to `quiz_items` mirroring the
shape of `lessons.quality_score`. Default proposal: do not add
the column; defer per-quiz_item writeback to slice 6.13.5 +
LD J2's `card_quality_signals` table.

If amendment changes default, the migration shape would be:

```python
# alembic/versions/<hash>_phase6_quiz_items_quality_score.py
def upgrade() -> None:
    op.add_column(
        "quiz_items",
        sa.Column("quality_score", sa.Numeric(3, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_items", "quality_score")
```

No data backfill. Existing rows stay NULL until a future
recompute pass writes to them.

---

## 8. Frontend

### 8.1 New page — `src/pages/admin/AdminContentQuality.tsx`

Mounts at `/admin/content-quality` inside the existing
`<AdminLayout />` outlet (audit finding #10 — slice 6.4a admin
shell pattern). Data fetched via `useAdminContentQuality()`
hook (§8.2). Sections rendered in order:

1. Header with `WindowSelector` (7d / 30d / 60d / 90d toggle,
   clamped per §6.1 module constants) + `IncludeArchivedToggle`.
2. `<DeckRollupTable>` — sortable table of `decks: DeckQualityRow[]`,
   default sort by `review_count_window DESC` (most-reviewed
   first). Click row → navigate to
   `/admin/decks/:deck_id` (existing slice 6.4b).
3. `<WorstLessonsTable>` — `worst_lessons: LessonQualityRow[]`,
   sorted by `smoothed_quality_score ASC NULLS LAST` (worst non-NULL
   first; NULL tail). Click row → navigate to
   `/admin/lessons/:lesson_id/edit` (existing slice 6.4b).
4. `<WorstQuizItemsTable>` — `worst_quiz_items: QuizItemQualityRow[]`,
   sorted by `pass_rate ASC NULLS LAST`. Click row → navigate to
   `/admin/lessons/:lesson_id/quiz-items` (existing slice 6.4b).
5. Footer with `writebacks_applied: N` indicator + last-generated
   timestamp.

Empty-state banner if `is_cold_start: true`: "No reviews in
window — quality scores not yet computable. Re-check once users
have reviewed cards."

Fires `admin_content_quality_viewed` PostHog event once per
mount via `useRef` idempotency guard (mirror
slice 6.8 D-11 `dashboard_viewed` once-per-mount precedent).

### 8.2 New hook — `src/hooks/useAdminContentQuality.ts`

```typescript
export function useAdminContentQuality(opts: {
  windowDays?: number  // default 30
  includeArchived?: boolean  // default false
}) {
  // useQuery wrapper; depends on opts via queryKey
  // ['adminContentQuality', windowDays, includeArchived]
}
```

### 8.3 New section components — `src/components/admin/content-quality/`

- `DeckRollupTable.tsx` (~80-120 lines)
- `WorstLessonsTable.tsx` (~80-120 lines)
- `WorstQuizItemsTable.tsx` (~80-120 lines)

All three use existing table primitives from
`src/components/ui/` (`Table`, `TableHeader`, `TableRow` etc.).
No new chart library (audit finding + §12 D-10 = match
slice 6.8 zero-deps precedent).

### 8.4 Modified files

- `src/services/api.ts` — `+1` helper:
  `fetchAdminContentQuality(windowDays, includeArchived)`.
- `src/types/index.ts` — `+4` types mirroring §5 schemas:
  `AdminContentQualityResponse` / `DeckQualityRow` /
  `LessonQualityRow` / `QuizItemQualityRow`.
- `src/App.tsx` — `+1` route:
  `<Route path="content-quality" element={<AdminContentQuality />} />`
  inside the `/admin` outlet block.

### 8.5 Existing pages explicitly NOT touched

- `pages/admin/AdminLessonEditor.tsx` — no quality_score badge
  added (kept as authoring view only; quality observability lives
  on the dedicated dashboard).
- `pages/admin/AdminDeckDetail.tsx` — no per-deck mini-rollup
  added (use the dashboard's `DeckRollupTable`).
- `pages/AdminAnalytics.tsx` — no cross-link from PRD-OKR
  surface to content-quality surface (orthogonal concerns —
  audit finding #8). A future "admin home" hub could surface
  both; that's a different spec.
- `pages/Dashboard.tsx` (slice 6.8 user-self) — untouched.

---

## 9. Analytics

### 9.1 New events (one)

| Event | Source | Properties |
|-------|--------|-----------|
| `admin_content_quality_viewed` | `pages/admin/AdminContentQuality.tsx` (FE, useRef once-per-mount) | `{admin_id, window_days, include_archived, internal: true}` |

`internal: true` keeps the event out of user-facing PostHog
dashboards (matches slice 6.8 D-11 + slice 6.10 D-13 +
slice 6.4b admin-event convention).

### 9.2 BE side-fire

`audit_admin_request` already fires
`admin_analytics_viewed` for `/api/v1/admin/analytics/*`
paths (audit finding #11). The path predicate is
prefix-string-startswith. Slice 6.11 does NOT extend it to
`/admin/content-quality` — the BE side-fire would be redundant
with the FE event (which carries window/archived params the BE
side-fire does not). Locked at §12 D-11.

### 9.3 Existing events touched

None. `quiz_item_reviewed` + `lesson_viewed` shapes unchanged.
No FE consumer for the new event needs migration.

### 9.4 Catalog discipline

`.agent/skills/analytics.md` — append one row in the FE event
catalog after the existing `admin_analytics_segment_changed`
row. Lock-step update in the impl commit per slice 6.10 D-13
precedent.

---

## 10. Test plan

Test envelope locked at impl. Estimates below.

### 10.1 BE unit — `tests/services/test_admin_content_quality_service.py` (~10-14 tests)

- happy path: 3 lessons with mixed review counts → response
  populates DeckQualityRow + LessonQualityRow + QuizItemQualityRow
  correctly.
- empty `quiz_review_events` table → `is_cold_start: true` +
  zero rows in worst_lessons / worst_quiz_items + no writebacks.
- writeback fires when `review_count >= MIN_REVIEW_THRESHOLD` and
  `quality_score` differs from current value (assert
  `lessons.quality_score` flips NULL → value).
- writeback skipped when `review_count < MIN_REVIEW_THRESHOLD`
  (assert NULL stays NULL).
- writeback no-op when smoothed_score equals persisted value
  (assert `writebacks_applied: 0`).
- `include_archived=False` filter excludes archived decks /
  archived lessons (assert deck/lesson with `archived_at IS NOT
  NULL` not in payload).
- `include_archived=True` includes them (assert presence + flag
  set on row).
- Bayesian smoothing math correctness (parametrize a few cases:
  raw 0.6 with N=5 → smoothed 0.533; raw 0.6 with N=100 →
  smoothed 0.591).
- worst_lessons cap (WORST_LESSONS_CAP=25) honoured when 30
  lessons all have low quality.
- worst_quiz_items cap (WORST_QUIZ_ITEMS_CAP=50) honoured.
- rating semantics: rating=2 (Hard) excluded from both pass and
  lapse counts per slice 6.8 D-5.
- partial-failure: one lesson UPDATE raises → logged WARNING +
  rest of batch continues + writebacks_applied count = N-1.

### 10.2 BE route — `tests/test_admin_content_quality_routes.py` (~5-7 tests)

- unauthed GET → 401.
- non-admin authed GET → 403.
- admin GET happy path → 200 + AdminContentQualityResponse + 1
  audit_admin_request log row.
- query param clamping: `window_days=200` → 422 (Query
  validator); `window_days=3` → 422 (below min).
- `include_archived=true` boolean passes through.
- response envelope matches Pydantic schema.

### 10.3 FE — `tests/pages/admin/AdminContentQuality.test.tsx` (~5-8 tests)

- renders all 3 sections from a mocked
  `AdminContentQualityResponse`.
- empty-state banner shown when `is_cold_start: true`.
- window selector change triggers refetch (queryKey changes).
- archived toggle change triggers refetch.
- click on lesson row navigates to
  `/admin/lessons/:id/edit`.
- click on quiz_item row navigates to
  `/admin/lessons/:lesson_id/quiz-items`.
- click on deck row navigates to `/admin/decks/:deck_id`.
- `admin_content_quality_viewed` event fires once per mount
  (useRef guard).

### 10.4 FE — `tests/components/admin/content-quality/*.test.tsx` (~3-6 tests)

- `DeckRollupTable` sorts by review_count desc by default.
- `WorstLessonsTable` sorts by smoothed_quality_score asc
  NULLS-LAST.
- `WorstQuizItemsTable` sorts by pass_rate asc NULLS-LAST.

### 10.5 Test envelope (estimates, locked at impl)

- BE: **692 → ~707..720** (+15..+28 across `_service` + `_routes`).
- FE: **414 → ~422..428** (+8..+14 across page + 3 component
  tests).
- Integration: **0** (no `@pytest.mark.integration` markers
  this slice).

---

## 11. Acceptance criteria

- **AC-1** GET `/api/v1/admin/content-quality` unauthed → 401.
- **AC-2** GET as authed non-admin → 403.
- **AC-3** GET as admin returns 200 +
  `AdminContentQualityResponse` envelope with all 3 section
  arrays present (even when empty).
- **AC-4** With zero `quiz_review_events` rows in window,
  response has `is_cold_start: true` + zero worst_lessons +
  zero worst_quiz_items + zero writebacks_applied.
- **AC-5** With ≥10 reviews on a lesson, that lesson's
  `lessons.quality_score` is UPDATEd to the
  Bayesian-smoothed value (assert the row in DB after request
  completes).
- **AC-6** With <10 reviews on a lesson, that lesson's
  `lessons.quality_score` stays NULL (assert no UPDATE fires
  for that row; `writebacks_applied` does not include it).
- **AC-7** Re-running the same request produces the same
  response shape and `writebacks_applied: 0` on the second
  call (idempotency per finding #14).
- **AC-8** `include_archived=False` excludes decks with
  `archived_at IS NOT NULL` and lessons with `archived_at IS
  NOT NULL`.
- **AC-9** `include_archived=True` includes them with
  `archived: true` flag on rows.
- **AC-10** `window_days` query param clamps to [7, 90] —
  values outside range return 422.
- **AC-11** worst_lessons sorted by `smoothed_quality_score
  ASC NULLS LAST` (lowest non-NULL first; NULL tail).
- **AC-12** worst_quiz_items sorted by `pass_rate ASC NULLS
  LAST`.
- **AC-13** worst_lessons capped at WORST_LESSONS_CAP=25 even
  when more lessons match.
- **AC-14** worst_quiz_items capped at
  WORST_QUIZ_ITEMS_CAP=50.
- **AC-15** Bayesian-smoothed pass_rate matches the formula in
  §6.1 (parametrized test).
- **AC-16** `admin_audit_log` row written per request (one
  audit row per GET — same shape as slice 6.10 AC-17).
- **AC-17** FE renders 3 section tables + empty-state banner +
  fires `admin_content_quality_viewed` once per mount.
- **AC-18** Rating=2 (Hard) excluded from both pass_rate and
  lapse_rate denominators (per slice 6.8 D-5).

---

## 12. Decisions

> Locked at `d9bfcfc` (2026-04-29). D-1..D-16 resolve §14
> OQ-A..OQ-P 1:1 (verbatim author-hint dispositions, all 16
> confirmed by Dhamo). Mirrors slice 6.0 / 6.4.5 / 6.5 / 6.6 /
> 6.7 / 6.8 / 6.10 §12 amendment pattern at `e8eecdd` /
> `df58eaf` / `acba7ed` / `fb92396` / `0c21223` / `ab07168` /
> `be7d59a`.

- **D-1** (resolves OQ-A) — **Writeback cadence: synchronous
  on-read.** `lessons.quality_score` writeback fires
  synchronously as a side-effect of the admin dashboard GET; no
  background job in v1. Per G-6 — no new infra, bounded by the
  per-admin slowapi default rate-limit, idempotent so concurrent
  admins are safe (audit finding #14 IS DISTINCT FROM gate).
  Background recompute deferred per §13 (likely bundled with
  slice 6.14 daily Pro digest infra extension).

- **D-2** (resolves OQ-B) — **`quality_score` formula v1 =
  Bayesian-smoothed pass_rate.** Formula:
  `(pass_count + 0.5 × 10) / (review_count + 10)`. Prior =
  0.5 (neutral, matches slice 6.6 D-2 ranker null-coercion
  convention); prior weight = 10 (matches the smoothing-prior
  weight by symmetry with D-4 — at N=10, raw and smoothed
  contribute equally). Dampens small-sample volatility without
  dominating the signal at scale. See §6.1 module constants
  `SMOOTHING_PRIOR_PASS_RATE = 0.5`,
  `SMOOTHING_PRIOR_WEIGHT = 10`.

- **D-3** (resolves OQ-C) — **Aggregation window: configurable,
  default 30 days, clamp [7, 90].** Default mirrors slice 6.8
  D-7 (`DEFAULT_RETENTION_WINDOW_DAYS = 30`) so admin and
  user-self dashboards stay coherent. Admin-toggleable via
  `?window_days=N` query param; values outside [7, 90] return
  422 (Pydantic Query validator). Module constants
  `DEFAULT_WINDOW_DAYS = 30`, `MIN_WINDOW_DAYS = 7`,
  `MAX_WINDOW_DAYS = 90`.

- **D-4** (resolves OQ-D) — **Minimum review threshold for
  non-NULL emission = 10 reviews.** A lesson's
  `quality_score` stays NULL until it accumulates ≥10 reviews
  in the configured window. Below threshold, the ranker (slice
  6.6 D-2) keeps the 0.5 default — no behavioural delta for
  cold-start lessons. Threshold matches the Bayesian smoothing
  prior weight (D-2) by symmetry. Module constant
  `MIN_REVIEW_THRESHOLD = 10`.

- **D-5** (resolves OQ-E) — **Writeback target =
  `lessons.quality_score` only; `quiz_items.quality_score`
  column NOT added this slice.** Audit finding #3 confirmed the
  column does not exist on `quiz_items`. Per-quiz_item
  writeback defers to slice 6.13.5 + LD J2 `card_quality_signals`
  table (the proper home for finer-grained per-(lesson,
  quiz_item, signal_source, dimension) signals). Per-quiz_item
  rollups STILL surface in the dashboard payload
  (`QuizItemQualityRow[]`) as read-time aggregations — admin
  can see them — but no column-add and no writeback to disk.
  Zero migrations result.

- **D-6** (resolves OQ-F) — **Admin route shape: single envelope.**
  `GET /api/v1/admin/content-quality?window_days=N&include_archived=bool`
  returns one `AdminContentQualityResponse` envelope with all
  three section arrays (per-deck rollup, worst-lessons,
  worst-quiz_items) populated in the same response. Mirrors
  slice 6.8 D-3 dashboard precedent — FE renders the page from
  one fetch, no waterfall, no per-section endpoints.

- **D-7** (resolves OQ-G) — **Tier filtering: merged but
  tagged.** Free + premium content appear in the same ranked
  lists; each row carries `DeckQualityRow.tier ∈ {'foundation',
  'premium'}` for client-side filtering / colour-coding. The
  dashboard does NOT apply tier-based filtering server-side
  (admin sees the universe; tier is a presentation hint only).

- **D-8** (resolves OQ-H) — **Archived/retired content
  visibility: hidden by default, opt-in toggle.**
  `?include_archived=false` (default) excludes decks with
  `archived_at IS NOT NULL` AND lessons with `archived_at IS
  NOT NULL` from all three sections. `?include_archived=true`
  surfaces them with `archived: true` flag on the row. Retired
  quiz_items (`retired_at IS NOT NULL`) are ALWAYS hidden in
  v1 — admin doesn't edit retired rows; the dashboard's question
  is "what should I author next?", and retired rows are
  historical, not actionable. Slice 6.13.5 may revisit if the
  layer-1 critique signal warrants surfacing them.

- **D-9** (resolves OQ-I) — **Writeback granularity: lesson-
  level only.** Consistent with D-5. Per-quiz_item dashboard
  rows are read-time aggregations from `quiz_review_events` —
  no writeback path. The `worst_quiz_items: QuizItemQualityRow[]`
  array carries `pass_rate` + `lapse_rate` + `review_count_window`
  + `low_volume` (per D-15) but no persisted score.

- **D-10** (resolves OQ-J) — **FE charts hand-rolled SVG /
  CSS-grid; zero new deps.** Mirrors slice 6.8's
  `RetentionCurve.tsx` SVG precedent (D-4 in spec #09). The v1
  dashboard is tabular not chart-heavy — three sortable tables
  rendered via existing `src/components/ui/Table` primitives
  cover the surface. Recharts/Visx introduction deferred until
  a future spec actually needs continuous-data visualisation
  beyond what hand-rolled SVG provides cleanly.

- **D-11** (resolves OQ-K) — **One PostHog event:
  `admin_content_quality_viewed`** fired client-side from
  `pages/admin/AdminContentQuality.tsx` on mount via `useRef`
  once-per-mount idempotency guard. Properties:
  `{admin_id, window_days, include_archived, internal: true}`.
  Mirrors slice 6.8 D-11 (`dashboard_viewed` once-per-mount
  pattern). NO BE side-fire extension to `audit_admin_request`
  — the FE event already carries the window/archived params the
  BE side-fire would not have access to. Single-event minimum
  matches slice 6.8 read-only-surface convention (slice 6.10's
  three-event minimum was specific to its async-job pipeline
  with start/end states; a synchronous read surface needs only
  one event).

- **D-12** (resolves OQ-L) — **Access control: plain
  `Depends(require_admin)`.** No sub-permission introduced
  (e.g., no `admin.content.review` role). Sub-permission
  infrastructure deferred until two admin surfaces actually
  need to differentiate access — today every admin can do every
  admin thing, and the cost of building a permission system for
  one consumer is unjustified.

- **D-13** (resolves OQ-M) — **Rating semantics: mirror slice
  6.8 D-5.** "Pass" = Rating ∈ {3, 4} (Good + Easy); "lapse"
  = Rating ∈ {1} (Again); Hard (Rating=2) is excluded from
  both numerators (pass and lapse). Module constants
  `_RECALL_RATINGS = (3, 4)` and `_LAPSE_RATING = 1` mirror
  `dashboard_service.py`'s constants verbatim (slice 6.8 D-5
  audit finding #12 — coherence with user-self dashboard so
  admin and user "this lesson is X% recall" copy match).

- **D-14** (resolves OQ-N) — **Include `lesson_view_events`
  view-volume denominator on `LessonQualityRow`.** Read
  `lesson_view_events` indexed per-lesson over the same
  configured window (audit finding #6 confirms
  `ix_lesson_view_events_lesson_viewed_at` supports this
  efficiently). Expose as `view_count_window: int` on
  `LessonQualityRow` so the dashboard surfaces "this lesson is
  opened 100x but reviewed only 10x" abandonment signal — the
  ratio is a meaningful authoring signal that pure
  review-volume doesn't capture. One extra indexed query per
  request; performance envelope per §6.3 unchanged (target
  ≤500ms holds).

- **D-15** (resolves OQ-O) — **Low-volume surfacing: tagged,
  not hidden.** Lessons / quiz_items below the D-4 threshold
  (10 reviews) appear in `worst_lessons` / `worst_quiz_items`
  with `low_volume: true` flag and `quality_score: null` on
  the lesson side (D-4 — no writeback). Sort order
  `smoothed_quality_score ASC NULLS LAST` puts non-NULL
  worst-first; NULL low-volume rows tail. No separate hiding
  threshold — every lesson with at least 1 review in window
  appears, and admins can visually filter via the
  `low_volume` tag. `LessonQualityRow.low_volume` and
  `QuizItemQualityRow.low_volume` fields locked.

- **D-16** (resolves OQ-P) — **Slice 6.13.5 docstring
  breadcrumb in `admin_content_quality_service.py`.** The
  service's module-level docstring carries a one-line note:
  `# layer-3 user-signal v1; merges with layer-1 critique
  signal in slice 6.13.5 via card_quality_signals table per
  LD J2`. Ensures continuity for the future slice 6.13.5
  Step 1 audit — the migration target (this writeback path)
  is grep-discoverable without curriculum.md spelunking.

---

## 13. Out of scope (deferred to other slices)

- **Per-quiz_item `quality_score` writeback to disk** — defer
  to slice 6.13.5 + LD J2's `card_quality_signals` table.
  Per-quiz_item rollups are surfaced *in the dashboard payload*
  in v1, but no column add + no writeback to disk.
- **Layer-1 critique-score consumption** — slice 6.10's
  `CritiqueSchema` payload (per-dimension scores) is layer 1;
  this slice is layer 3 only. Slice 6.13.5 unifies both layers
  via `card_quality_signals`.
- **`card_quality_signals` table** — LD J2 / slice 6.13.5.
- **User-thumbs feedback ingestion** — third source for layer
  3; slice 6.13.5 consolidates.
- **Cron-driven recomputation** — v1 fires synchronously on
  every dashboard load. Background recompute = future slice
  (likely bundled with slice 6.14 daily Pro digest infra
  extension).
- **Cross-deck normalization** — v1 reports raw + smoothed
  per-lesson; "lesson X is bottom-decile in its deck" is a
  future surface.
- **Export / CSV / PDF** — v1 read-on-screen only.
- **Time-series / before-after-edit diffs** — v1 point-in-time
  only.
- **Real-time / SSE updates** — page reload triggers recompute.
- **Per-route slowapi rate limit** — global default
  (100/min) covers v1; per-admin per-route limiter is unneeded
  for an admin-only synchronous read surface.
- **Pagination on worst_lessons / worst_quiz_items** — v1
  caps at 25 / 50 respectively. Pagination is future-spec
  when corpus grows past visual-scan capacity.
- **Unifying `admin_analytics_service` + `admin_content_quality_service`**
  — orthogonal concerns today (audit finding #8). Future "admin
  observability hub" could merge or compose.

---

## 14. Open questions

> All 16 OQs RESOLVED at §12 amendment slice (`d9bfcfc`)
> per author-hint dispositions. Headings + first-sentence
> questions preserved for historical reference; option bodies
> + author hints removed (locked dispositions live in §12 D-N).

- **OQ-A — Writeback cadence.** Synchronous on-read vs admin-
  triggered batch vs background job?
  **RESOLVED:** locked at §12 D-1 (`d9bfcfc`).

- **OQ-B — quality_score formula v1.** Raw pass_rate vs
  pass_rate × volume_factor vs Bayesian-smoothed?
  **RESOLVED:** locked at §12 D-2 (`d9bfcfc`).

- **OQ-C — Aggregation window.** 30 days vs N reviews vs
  lifetime vs configurable?
  **RESOLVED:** locked at §12 D-3 (`d9bfcfc`).

- **OQ-D — Minimum review threshold for non-NULL emission.**
  How many reviews before we trust the signal enough to write
  to disk?
  **RESOLVED:** locked at §12 D-4 (`d9bfcfc`).

- **OQ-E — `quiz_items.quality_score` column status.** Add the
  column this slice (so per-quiz_item writeback works) or stay
  lesson-level only and defer per-item writeback to slice
  6.13.5?
  **RESOLVED:** locked at §12 D-5 (`d9bfcfc`).

- **OQ-F — Admin route shape.** Single envelope vs split
  per-deck/lesson/quiz_item endpoints?
  **RESOLVED:** locked at §12 D-6 (`d9bfcfc`).

- **OQ-G — Tier filtering.** Free vs premium content shown
  separately or merged?
  **RESOLVED:** locked at §12 D-7 (`d9bfcfc`).

- **OQ-H — Archived/retired content visibility.** Surface
  archived decks / archived lessons / retired quiz_items by
  default?
  **RESOLVED:** locked at §12 D-8 (`d9bfcfc`).

- **OQ-I — Writeback granularity.** Per-quiz_item, per-lesson,
  both?
  **RESOLVED:** locked at §12 D-9 (`d9bfcfc`).

- **OQ-J — FE chart library.** Match slice 6.8's hand-rolled
  zero-deps pattern or first introduction of recharts?
  **RESOLVED:** locked at §12 D-10 (`d9bfcfc`).

- **OQ-K — Analytics events.** Mirror slice 6.10's three-event
  minimum (`_enqueued`, `_completed`, `_failed`) or single
  `_viewed` event?
  **RESOLVED:** locked at §12 D-11 (`d9bfcfc`).

- **OQ-L — Access control sub-permission.** Plain
  `require_admin` for v1 or sub-permission like
  `admin.content.review`?
  **RESOLVED:** locked at §12 D-12 (`d9bfcfc`).

- **OQ-M — Rating semantics.** Mirror slice 6.8 D-5 (recall =
  3+4; lapse = 1; Hard=2 excluded) or include Hard as pass?
  **RESOLVED:** locked at §12 D-13 (`d9bfcfc`).

- **OQ-N — View-volume denominator.** Surface
  `lesson_view_events` view counts alongside review counts (so
  admins see "this lesson is opened 100x but reviewed only
  10x" abandonment signal)?
  **RESOLVED:** locked at §12 D-14 (`d9bfcfc`).

- **OQ-O — Low-volume threshold for surfacing problem
  content.** Separate from OQ-D's non-NULL emission threshold:
  should a lesson with 3 reviews and 33% pass_rate appear in
  worst_lessons (provisional signal) or be hidden (insufficient
  data)?
  **RESOLVED:** locked at §12 D-15 (`d9bfcfc`).

- **OQ-P — Idempotency vs slice 6.13.5 future migration.**
  When slice 6.13.5 ships `card_quality_signals`, this slice's
  writeback path migrates to write the unified table instead.
  Should v1 leave any breadcrumbs (e.g., a comment in the
  service docstring) or just rely on slice 6.13.5's Step 1
  audit to find the callsite?
  **RESOLVED:** locked at §12 D-16 (`d9bfcfc`).

---

## 15. Implementation slice forward-link

Implementation row: **B-084** 🔴 (filed by this slice; closure
happens in the impl commit per R15(c)).

Forward dependencies before impl can start:

1. **§12 amendment slice** ✅ shipped at `d9bfcfc` —
   locked D-1..D-16 from §14 OQ-A..OQ-P (now §12 D-1..D-16)
   mirroring slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10
   §12 amendment pattern at `e8eecdd` / `df58eaf` / `acba7ed`
   / `fb92396` / `0c21223` / `ab07168` / `be7d59a`.
2. No BE primitive prerequisite — every existing data source is
   on disk:
   - `lessons.quality_score Numeric(3,2) NULLABLE` (slice 6.1,
     `a989539`).
   - `quiz_review_events` + indexes (slice 6.0, `e7a0044`).
   - `lesson_view_events` + indexes (slice 6.0, `e7a0044`).
   - `Depends(require_admin)` + `audit_admin_request`
     (pre-Phase-6).
   - `slowapi` rate-limiter (`app/core/rate_limit.py`).

Impl slice expected scope (from §4.1 component graph + §6
backend + §7 migrations + §8 frontend):

- New file `app/services/admin_content_quality_service.py`
  (~250-350 lines).
- New file `app/schemas/admin_content_quality.py` (~120-180
  lines).
- New file `app/api/v1/routes/admin_content_quality.py` (~50-80
  lines).
- Modify `app/main.py` — mount admin_content_quality router
  alphabetical between admin_analytics + admin_decks (~3-5
  lines).
- New file `src/pages/admin/AdminContentQuality.tsx` (~200-300
  lines).
- New file `src/hooks/useAdminContentQuality.ts` (~50-80
  lines).
- New files
  `src/components/admin/content-quality/DeckRollupTable.tsx`
  + `WorstLessonsTable.tsx` + `WorstQuizItemsTable.tsx`
  (~80-120 lines each).
- Modify `src/services/api.ts` — `+1` helper (~5-10 lines).
- Modify `src/types/index.ts` — `+4` types mirroring §5
  (~30-50 lines).
- Modify `src/App.tsx` — `+1` route under `/admin` outlet
  (~3-5 lines).
- 4 new BE/FE test files per §10.1-§10.4 (~25-35 unit tests
  total).
- 0 integration tests (R13).
- 0 new deps.
- 0 migrations (per §12 D-5 lock to lesson-only).
- `.agent/skills/analytics.md` update: 1 new event row per §9
  (`admin_content_quality_viewed`).
- `.agent/skills/curriculum.md` — minor §7 layer-3 update
  referencing slice 6.11 by SHA (this slice is the first
  layer-3 emitter).
- BACKLOG B-084 closure with impl SHA (R15(c)).
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new service +
  schema + route + page + 3 components + hook + types +
  api helper + skill catalog updates).

Impl test envelope (estimates, locked at impl):
- BE: **692 → ~707..720** (+15..+28).
- BE integration: **0**.
- FE: **414 → ~422..428** (+8..+14).

R16 consumer-graph audit at impl Step 1: any new shared BE
types (`AdminContentQualityResponse` /
`{Deck,Lesson,QuizItem}QualityRow`) need consumer-graph
audited. Predicted consumers:
`admin_content_quality_service`, route, page, hook, three
table components — leaf surface, no external consumers.

R11 + LLM-strategy compliance: zero LLM calls this slice.
Pure SQL aggregation + arithmetic. R11 not load-bearing.

R12 design-tokens compliance: every FE color / spacing /
shadow uses tokens. Pre-impl audit must grep
`hardcoded color values` in the new components — convention
already established by slice 6.4b admin pages + slice 6.7
Learn.tsx + slice 6.8 Dashboard.tsx.

Out-of-scope at impl (cross-ref §13): user-facing quality
surfaces, per-quiz_item disk writeback, layer-1 critique-score
consumption, `card_quality_signals` table, user-thumbs ingest,
cron recompute, cross-deck normalization, export/CSV/PDF,
time-series diffs, real-time updates, per-route rate limit,
pagination, admin-service unification.

Skill-author work potentially surfaced post-impl (NOT this
slice's scope): none new. Existing four skills
(`curriculum.md` §7-§8, `analytics.md`, `study-engine.md`,
`backend.md`) cover the surface. The
`background-jobs.md` candidate (slice 6.10a / 6.10b carry-
forward at flag #1) is unaffected — slice 6.11 introduces no
RQ work.

---

*Spec authored at `7d7c6e8` against HEAD `057ff93`. All
on-disk citations verified at audit time per SOP-5; phantom
citations zero. Forward-filed B-084 at status 🔴 per R15(c).
§12 amendment locked D-1..D-16 from §14 OQ-A..OQ-P at
`d9bfcfc` (2026-04-29); B-084 stays 🔴 pending impl
pickup.*
