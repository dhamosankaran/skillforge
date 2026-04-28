# Phase 6 — Slice 6.5: Read-Time Service-Layer Invariants (FSRS-progress writes + lesson/quiz_item lifecycle filters)

## Status: Shipped — §12 amended at `acba7ed` locking D-1..D-9 from §14 OQ-1..OQ-9; + D-10 inline-amended at impl commit `930a6a2`; closes B-072 ✅

| Field | Value |
|-------|-------|
| Phase | 6 (Curriculum Platform) |
| Slice | 6.5 — read-time service-layer invariants |
| Mode | 4 (spec-author) |
| Author HEAD | `688d178` (post-slice-6.4.5 implementation SHA backfill) |
| Spec authored | 2026-04-28 (§12 amendment 2026-04-28 at `acba7ed`) |
| Implementation slice | TBD (one-step follow-up to this spec). Will file `B-072` close-line. |
| BACKLOG row | `B-072` filed at status 🔴 by this spec slice for the future implementation slice (per R15(c) + R17). |
| Audit dependency | `docs/audits/phase-6-scout.md` slice-by-slice 6.5 entry + cross-cutting #3 (slice 6.1 dependency) — anchored to the on-disk service shape at the time of the Step 0 audit (slice 6.2 `quiz_item_study_service` shipped, slice 6.4b-1 `lesson_service` body-swap shipped, slice 6.4b-1 `quiz_item_admin_service` shipped, slice 6.4 D-19 persona-narrowing punt). |
| Spec dependencies | `docs/specs/phase-6/01-foundation-schema.md` (slice 6.1, shipped at `a989539` / `f621248`) — `decks.archived_at` + `decks.persona_visibility` + `decks.tier` + `lessons.archived_at` + `lessons.published_at` + `quiz_items.retired_at` + `quiz_items.superseded_by_id` columns + their semantics (§4.1 / §4.2 / §4.3). `docs/specs/phase-6/02-fsrs-quiz-item-binding.md` (slice 6.2, shipped at `7b654fb` / `a02639c`) — service contract for `get_daily_quiz_items` + `review_quiz_item` + `get_quiz_progress` + the three slice-6.2 service errors (`QuizItemNotFoundError` / `QuizItemForbiddenError` / `QuizItemRetiredError`) + their HTTP mapping (404 / 403 / 409). `docs/specs/phase-6/04-admin-authoring.md` §7 (substantive-edit cascade) + §12 D-15 (selectinload strategy on user-facing read path) + §12 D-18 (retire-and-replace shape) + §12 D-19 (persona-narrowing punt: "narrowing does not retire in-flight quiz_item_progress rows for users now in excluded personas — orphan cleanup deferred to slice 6.7 / 6.8"). `docs/specs/phase-6/05-seed-lessons.md` §6.1.2 + D-5 (loader's read-time mirror — "loader respects archived/retired"; this slice's invariant is the read-side counterpart). |
| Slice dependencies | **Upstream:** slice 6.1 (foundation schema, shipped); slice 6.2 (FSRS quiz-item binding, shipped); slice 6.4b-1 (BE admin authoring + `lesson_service` DB-backed body swap, shipped at `d6bda3b`); slice 6.4.5 (seed corpus, shipped at `ac5b905`) — all required, all shipped. **Downstream:** unblocks slice 6.7 / 6.12 (persona-aware Learn-page composition — needs the persona-visibility read-time guarantee this slice ships); slice 6.13.5 (`card_quality_signals` user-thumbs dimension — observes review outcomes and assumes the read-side is filter-clean). |

### Phase 6 locked decisions referenced by this spec

> Recorded in front-matter so spec readers see the relevant locks
> without chasing SESSION-STATE. Rationale lives in §12 (Decisions) below.

| ID | Decision |
|----|----------|
| **G2** | Background jobs: RQ on Redis for ingestion (slice 6.10); Railway cron for daily Pro digest (slice 6.14). **Not consumed by this slice** — read-time filters run synchronously in the request session; no async fan-out, no RQ enqueue. |
| **H1** | Object storage: Cloudflare R2 for ingestion artifacts (slice 6.10); `hirelens-backend/app/data/decks/seed_lessons/*.md` for the 12 locked-deck seeds (slice 6.4.5). **Not consumed by this slice** — no file I/O. |
| **I1** | Events: dual-write (PostHog + Postgres `quiz_review_events` + `lesson_view_events`). **Untouched by this slice** — slice 6.5 adds zero new events; existing `quiz_item_reviewed` + `lesson_viewed` payloads carry forward unchanged. |
| **J2** | Quality signals: `card_quality_signals` keyed `(id, lesson_id, quiz_item_id NULLABLE, signal_source, dimension)`; built in slice 6.13.5. **Not consumed by this slice** — read-time invariants are upstream of the quality-signal write path. |

---

## 1. Problem

Phase 6 has shipped, in order: slice 6.1 (foundation schema —
`decks.archived_at` + `decks.persona_visibility` + `decks.tier` +
`lessons.archived_at` + `lessons.published_at` + `quiz_items.retired_at`
columns + their semantics); slice 6.2 (FSRS quiz-item binding —
`quiz_item_study_service.get_daily_quiz_items` + `.review_quiz_item` +
`.get_quiz_progress`, with archive-guards + retired-quiz_item-guard);
slice 6.3 (lesson-card UX backed by fixture data); slice 6.4 (admin
authoring CRUD + `lesson_service.py` DB-backed body swap; persona-
narrowing punt at D-19; "no new progress rows against retired
quiz_items / archived lessons / archived decks" enforcement explicitly
delegated to `quiz_item_study_service` per `quiz_item_admin_service`
docstring); slice 6.4.5 (reference seed corpus + idempotent loader,
with `archived_at IS NOT NULL` / `retired_at IS NOT NULL` skip
semantics on re-load per loader D-5).

The result: **invariant coverage on the read paths is implicit and
partially distributed across four services with no formal contract
between them.** The Step 0 audit at this spec's HEAD (`688d178`)
maps the on-disk filter coverage as follows:

- **`quiz_item_study_service.get_daily_quiz_items`** (slice 6.2) —
  filters `QuizItem.retired_at IS NULL` + `Lesson.archived_at IS NULL`
  + `Deck.archived_at IS NULL` on **both** the overdue pass and the
  fresh-fill pass. Persona-visibility + tier filters are absent.
- **`quiz_item_study_service.review_quiz_item`** (slice 6.2) —
  archive-guard (raises `QuizItemForbiddenError` / 403 if lesson or
  deck is archived) + retired-guard (raises `QuizItemRetiredError`
  / 409 if quiz_item retired AND no existing progress row). No
  persona-visibility check; no tier check.
- **`quiz_item_study_service.get_quiz_progress`** (slice 6.2) — pure
  aggregation of `QuizItemProgress` rows by `state`. No archive/
  retired/persona/tier filtering. (See §3 non-goals — this is
  intentional analytics behavior; orphan progress rows stay queryable
  for retention metrics.)
- **`lesson_service.get_lesson_with_quizzes`** (slice 6.4b-1 body-
  swap) — filters `Lesson.archived_at IS NULL` + `Lesson.published_at
  IS NOT NULL`; post-load checks `Deck.archived_at IS NOT NULL` →
  returns `None` (route maps to 404); `selectinload` of quiz_items is
  conditioned on `QuizItem.retired_at IS NULL`. Persona-visibility +
  tier filters are absent.
- **`lesson_service.get_deck_with_meta`** (slice 6.4b-1) — filters
  `Deck.archived_at IS NULL`. Persona-visibility + tier filters are
  absent.
- **`lesson_service.list_lessons_in_deck`** (slice 6.4b-1) — filters
  `Lesson.archived_at IS NULL` + `Lesson.published_at IS NOT NULL`.
  **Does NOT filter `Deck.archived_at IS NULL`.** Currently safe in
  practice because the only caller (`get_deck_lessons_bundle`) fronts
  it with `get_deck_with_meta`, but a direct-call path (e.g. a future
  ranker in slice 6.6, or a misuse from a yet-unwritten admin-side
  endpoint) would leak lessons from archived decks.
- **`lesson_service.get_deck_lessons_bundle`** (slice 6.4b-1) —
  composes `get_deck_with_meta` (filters archived deck) +
  `list_lessons_in_deck` (filters archived/unpublished lessons) →
  safe.

The audit also confirms a missing filter axis across **every** read
path: **persona-visibility**. Slice 6.4 D-19 explicitly punted
"narrowing does not retire in-flight quiz_item_progress rows for users
now in excluded personas — orphan cleanup deferred to slice 6.7 /
6.8". Slice 6.5 owns the **read-side** treatment of those orphans:
the orphan rows stay queryable (per slice 6.4 D-19's preservation
invariant), but a user in a now-excluded persona must not be SERVED
content (daily-queue items, lesson detail, deck detail) from a deck
they can no longer see.

The tier-vs-paywall axis (`Deck.tier='premium'` AND user plan free
→ 403 / paywall surface) is the seam between slice 6.5 (server-side
guarantee) and slice 6.7 (visible UX paywall composition); locked
at §12 **D-2**.

Without slice 6.5, the invariants live in code comments, individual
slice-spec footnotes, and the `quiz_item_admin_service` module
docstring. There is no single source of truth that says "these are
the read-time invariants; here's how each path satisfies (or fails to
satisfy) them; here are the regression tests that lock the contract."
This slice ships that source of truth.

## 2. Goals

1. **Lock the Read-Time Invariant Table** (§4) — one row per
   (read path × invariant axis) cell; columns enumerate the current
   on-disk shape, the gap (if any), the target shape, and the
   error-class / HTTP-code mapping. The table IS the contract.
2. **Audit + close gaps** in the existing slice 6.2 / 6.4b-1 filter
   coverage. Step 0 identifies three gap categories: (a)
   `list_lessons_in_deck` lacks `Deck.archived_at IS NULL` (defense-
   in-depth gap); (b) every read path lacks persona-visibility
   filtering (closes slice 6.4 D-19 read-side punt); (c) tier-vs-
   plan filtering is missing across the lesson_service surface
   (slice 6.7 vs 6.5 ownership — locked at §12 **D-2**: slice 6.5
   owns the server-side guarantee). Goals (a), (b), and (c) are
   all in scope unconditionally per D-2 disposition.
3. **Regression tests for every §4 row** — one (positive, negative)
   pair per invariant cell; estimated +15 to +25 BE tests per §10.
4. **Zero new domain errors / zero new HTTP status codes.** Reuse
   slice 6.2's `QuizItemNotFoundError` (404) / `QuizItemForbiddenError`
   (403) / `QuizItemRetiredError` (409) and slice 6.4b-1's
   `LessonNotFoundError` (404) / `LessonArchivedError` (409). New
   filter-violation paths surface via existing error classes.
5. **Zero new endpoints, zero schema changes, zero migrations.**
   Service-layer hardening only; route surface is unchanged. (This
   slice adds a private query helper to `lesson_service` per
   §12 **D-5**; that is a service-internal refactor, not a route or
   schema addition.)

## 3. Non-goals

- **Orphan progress-row cleanup.** Slice 6.4 D-19 punted "no
  cleanup of in-flight `quiz_item_progress` rows for users now in
  excluded personas / archived lessons / retired quiz_items"
  to slice 6.7 / 6.8. Slice 6.5 enforces only the **read-side**
  treatment of those orphan rows: they stay in the table for
  analytics retention metrics (slice 6.13.5 / 6.16), but the user-
  facing read paths must not surface content from rows the user can
  no longer access. Cleanup itself is out of scope.
- **`get_quiz_progress` filtering.** The aggregate-stats endpoint
  is intentionally counter-of-rows (per §1 audit). Rows whose
  `quiz_item.retired_at IS NOT NULL` or whose `lesson.archived_at IS
  NOT NULL` are still counted in the user's `total_reps` / `lapses`
  — preserving the per-user FSRS-history retention surface. Locked
  as a positive invariant at §12 **D-9** with one anti-regression
  test per §10.2.
- **Tier-paywall UX surface.** Slice 6.7 owns the paywall modal
  copy + "upgrade to access" composition on the Learn page. Slice
  6.5 owns the **server-side** 403 (free-user-on-premium-deck →
  read service layer raises) per §12 **D-2**.
- **FSRS-history backfill on cascade-retired quiz_items.** Cascade-
  retired (slice 6.4 §7.3) and direct-retired (slice 6.4b-1
  `retire_quiz_item`) quiz_items both end up with `retired_at IS
  NOT NULL`; slice 6.5 enforces "FSRS state preserved on retired
  rows" but does NOT backfill historical reviews onto cascade
  victims. (Per §12 **D-6**, both retirement paths get identical
  read-time treatment.)
- **Admin audit log of read-time invariant violations.** A free
  user who hits a 403 on a premium deck does not generate a row in
  `admin_audit_log`. Standard request logs (`logger.info`) are the
  surface; PostHog tracking of paywall-blocked-at-read is a slice
  6.7 concern (locked at §12 **D-8**).
- **Cross-deck invariants** ("user can't have progress on quiz_items
  from decks they've never been able to see"). Out of scope; this
  slice enforces per-request, per-path read-time invariants only.
- **DB schema changes.** Slice 6.1 already shipped all the columns
  this slice's filters touch (`decks.archived_at`,
  `decks.persona_visibility`, `decks.tier`, `lessons.archived_at`,
  `lessons.published_at`, `quiz_items.retired_at`). N7 STOP if a
  schema gap surfaces.
- **New routes / new schemas.** Service-layer hardening only.
- **Admin-side read paths** (`/api/v1/admin/decks`,
  `/api/v1/admin/lessons/{id}`, `/api/v1/admin/lessons/{id}/quiz-
  items`). Admin LIST routes intentionally surface drafts +
  archived rows + retired quiz_items (with status-filter query
  param per slice 6.4 §5); admins are NOT subject to the §4 read-
  time invariants (they are the ones authoring the lifecycle
  signals). Slice 6.4 §3 already enumerates this carve-out;
  this slice respects it.
- **FE consumer surface.** Zero FE deliverables. Existing route
  shapes are byte-identical; new 403 / 404 paths are reachable via
  existing error-handling patterns on the FE (the same patterns
  that handle today's archived-lesson 404).
- **Telemetry on filter-violation rejection paths.** A `logger.info`
  on each rejection is acceptable and recommended for ops
  observability, but no new PostHog events. (Locked at §12 **D-8**
  — NO new event this slice; slice 6.7 owns paywall telemetry.)

## 4. Read-Time Invariant Table

> **The contract.** Every cell describes one (read path × invariant
> axis) pair. The implementation slice's regression tests (§10) lock
> the table row-by-row. A future read-path addition (e.g. slice 6.6
> ranker, slice 6.7 Learn-page composition) extends the table by
> adding rows for the new path; same `(filter, error, HTTP code)`
> column shape.

### 4.1 Read paths in scope

Seven user-facing service-layer functions across two services:

| # | Read path | Service | Slice of origin |
|---|-----------|---------|-----------------|
| R-1 | `get_daily_quiz_items(user_id, db, *, user)` | `quiz_item_study_service` | 6.2 |
| R-2 | `review_quiz_item(user_id, quiz_item_id, rating, db, …)` | `quiz_item_study_service` | 6.2 |
| R-3 | `get_quiz_progress(user_id, db)` | `quiz_item_study_service` | 6.2 |
| R-4 | `get_lesson_with_quizzes(lesson_id, db)` | `lesson_service` | 6.4b-1 |
| R-5 | `get_deck_with_meta(deck_id, db)` | `lesson_service` | 6.4b-1 |
| R-6 | `list_lessons_in_deck(deck_id, db)` | `lesson_service` | 6.4b-1 |
| R-7 | `get_deck_lessons_bundle(deck_id, db)` | `lesson_service` | 6.4b-1 |

### 4.2 Invariant axes

Seven binary axes; each cell evaluates to "filter applies" / "filter
does not apply" / "vacuously not applicable" for a given read path:

| Axis | Predicate | Target outcome on violation |
|------|-----------|------------------------------|
| **A-1 deck archived** | `Deck.archived_at IS NOT NULL` | 404 (treat as nonexistent — locked at §12 **D-1** for lesson_service paths; review path R-2 retains 403 per slice 6.2 §AC-5 — accepted asymmetry) |
| **A-2 lesson archived** | `Lesson.archived_at IS NOT NULL` | 404 |
| **A-3 lesson draft** | `Lesson.published_at IS NULL` | 404 (non-admin reader paths only; admin paths excluded per §3) |
| **A-4 quiz_item retired (no existing progress)** | `QuizItem.retired_at IS NOT NULL AND no row in quiz_item_progress for (user, quiz_item)` | 409 (`QuizItemRetiredError` per slice 6.2 contract) |
| **A-5 quiz_item retired (existing progress)** | `QuizItem.retired_at IS NOT NULL AND quiz_item_progress row exists for (user, quiz_item)` | **PERMITTED** — FSRS history preservation per slice 6.2 §4.6 D-4 |
| **A-6 persona-visibility mismatch** | `Deck.persona_visibility ∉ user's persona expansion set` (mirrors `deck_admin_service._persona_set` semantics — `'both'` ⊇ `{'climber', 'interview_prepper'}`) | 404 — closes slice 6.4 D-19 read-side punt; locked at §12 **D-3** + **D-7** |
| **A-7 tier-vs-plan** | `Deck.tier == 'premium' AND user plan == 'free'` | 403 (server-side guarantee) — locked at §12 **D-2** |

> **A-1 vs A-6 status-code rationale.** Both surface as 404 (not 403)
> on the rationale that information leakage about deck existence is
> the correct conservative default. A user in an excluded persona
> should be indistinguishable from a user pointing at a nonexistent
> deck ID. Locked at §12 **D-1** + **D-7**.
>
> **A-7 status-code rationale.** Tier mismatch is fundamentally
> different — the deck exists, the user *can* access it post-upgrade,
> and the FE Learn-page composition (slice 6.7) needs to surface a
> paywall, not a 404. 403 with a `detail` enum tagging the trigger
> is the seam.

### 4.3 The table — current shape vs target shape

> **Legend.** `✓` = filter currently applies on disk (slice 6.2 /
> 6.4b-1 already ships it); `✗` = filter is missing on disk and
> slice 6.5 adds it; `n/a` = axis vacuously not applicable to this
> read path. (`OQ-2`-conditional cells from the spec-author draft
> are now unconditional `✗ → ADD` per §12 **D-2** lock; the table
> below reflects the locked state.)

| Path | A-1 deck archived | A-2 lesson archived | A-3 lesson draft | A-4 retired (no progress) | A-5 retired (with progress) | A-6 persona-visibility | A-7 tier-vs-plan |
|------|-------------------|---------------------|------------------|----------------------------|------------------------------|--------------------------|------------------|
| R-1 `get_daily_quiz_items` | ✓ (both passes) | ✓ (both passes) | n/a (queue-fill ignores `published_at`) ¹ | ✓ (excluded from fresh-fill) | n/a (queue does not surface progress rows the user owns at retired quiz_items — they are non-`new`-state and pass-1 filters retired) | ✗ → ADD | ✗ → ADD (per D-2) |
| R-2 `review_quiz_item` | ✓ (raises 403 — D-1 asymmetry) | ✓ (raises 403 — D-1 asymmetry) | n/a (review path operates on a `quiz_item_id` regardless of lesson `published_at`) ² | ✓ (raises 409) | ✓ (PERMITTED — preserves FSRS history) | ✗ → ADD (raises 404 via new `QuizItemNotVisibleError` per D-7) | ✗ → ADD (raises 403 per D-2) |
| R-3 `get_quiz_progress` | n/a (per §3 non-goal — analytics aggregate; locked filter-free per D-9) | n/a (idem per D-9) | n/a | n/a | n/a (preserved for retention) | n/a (idem per D-9) | n/a |
| R-4 `get_lesson_with_quizzes` | ✓ (post-load via `lesson.deck.archived_at`) | ✓ | ✓ (filters `published_at IS NOT NULL`) | n/a (selectinload filters retired quiz_items so they don't appear in the bundle's `quiz_items` list) | n/a (idem; the user's progress row is irrelevant to the read shape) | ✗ → ADD | ✗ → ADD (per D-2) |
| R-5 `get_deck_with_meta` | ✓ | n/a (deck-only) | n/a (deck-only) | n/a (deck-only) | n/a (deck-only) | ✗ → ADD | ✗ → ADD (per D-2) |
| R-6 `list_lessons_in_deck` | ✗ → ADD ³ | ✓ | ✓ | n/a (lessons-only) | n/a (lessons-only) | ✗ → ADD ⁴ | ✗ → ADD (per D-2) |
| R-7 `get_deck_lessons_bundle` | ✓ (via `get_deck_with_meta`) | ✓ (via `list_lessons_in_deck`) | ✓ (via `list_lessons_in_deck`) | n/a | n/a | ✗ → ADD (via R-5 + R-6) | ✗ → ADD (via R-5 + R-6 per D-2) |

**Notes.**

- **¹** R-1 ignores `published_at` because slice 6.2 D-2 mirrors
  `study_service.get_daily_review`, which has no draft-vs-published
  concept on the legacy `cards` table. This is **intentional** for
  the queue path — the queue only surfaces published quiz_items
  *because* `quiz_items.lesson_id` only points at lessons whose
  admin authoring path went through the slice-6.4b
  `publish_lesson` route (which sets `lessons.published_at`). The
  invariant is implicit through admin-write-side enforcement, not
  read-side filtering. Slice 6.5 may codify A-3 on R-1 if the impl
  prompt finds a path where a draft lesson's quiz_item could leak
  (e.g. a developer-only seed direct-INSERT) — surfaced as §14
  the still-OPEN OQ-1c (deferred from this amendment — not in the
  prompt's lock list).
- **²** R-2 ignores `published_at` for the same reason as R-1.
  Locked by slice 6.2's review-path contract — the review service
  trusts `quiz_item_id` ownership and the admin-write-side has
  already gated on `published_at`. Slice 6.5 does NOT change this.
- **³** R-6 lacks a `Deck.archived_at IS NULL` filter on disk. In
  the current call graph it is safe (only `get_deck_lessons_bundle`
  calls it, and that caller fronts with `get_deck_with_meta`), but
  **defense-in-depth requires** R-6 to filter independently — slice
  6.5 adds it. Without the additive filter, a slice-6.6 ranker that
  imports `list_lessons_in_deck` directly would silently leak
  archived-deck lessons.
- **⁴** R-6's persona-visibility filter joins `Deck` (currently it
  doesn't join the deck table at all — it filters by `Lesson.deck_id
  == :deck_id`). The implementation slice adds the join + the
  persona filter; alternative is to short-circuit by reading the
  deck's `persona_visibility` once via a sub-query and gating in-
  process. The simpler path is the explicit join — see §6.3 for
  the recommended shape.

### 4.4 Filter implementation strategy

The persona-visibility filter (A-6) is the only one that requires a
shared helper — it appears on five of seven read paths and the
predicate is non-trivial (the `_persona_set` expansion). The
implementation slice adds:

```python
# app/services/lesson_service.py (or new app/services/curriculum_visibility.py per §12 D-5 escape hatch)
def _persona_visible_to(deck_persona: str, user_persona: Optional[str]) -> bool:
    """True iff a user with `user_persona` may see a deck with
    `persona_visibility == deck_persona`. Mirrors deck_admin_service
    semantics: `'both'` is visible to everyone; the named persona is
    visible only to a user with that persona.
    """
    if deck_persona == "both":
        return True
    if user_persona is None:
        return False  # persona-null users cannot see persona-narrowed decks
    return deck_persona == user_persona
```

The function is consulted at the SQL layer where possible (filter
clauses use the join + `Deck.persona_visibility.in_(visible_set)`
form per the helper, computed once at request time from the bound
user). Where a join is structurally awkward (R-2 review path which
is keyed by `quiz_item_id`, not `deck_id`), the filter is a post-
load check on the `lesson.deck.persona_visibility` already loaded
for the archive-guard. See §6 for the per-path recipe.

### 4.5 What this slice does NOT change in the existing filters

- The slice-6.2 `archived_at IS NULL` and `retired_at IS NULL`
  predicates already on R-1 and R-2 are LOCKED by slice 6.2 §AC-4
  + §AC-5; slice 6.5 does NOT rewrite them.
- The slice-6.4b-1 `Lesson.published_at IS NOT NULL` and
  `Lesson.archived_at IS NULL` predicates on R-4 / R-6 / R-7 are
  LOCKED; slice 6.5 does NOT rewrite them.
- The R-1 `selectinload`-conditioned `QuizItem.retired_at IS NULL`
  filter on R-4 is LOCKED.
- Status code mappings on existing exception types (`QuizItem*Error`,
  `Lesson*Error`) are LOCKED; slice 6.5 reuses them and does NOT
  introduce a new exception.

## 5. Pydantic / domain-error contracts

This slice ships **zero new Pydantic schemas** and **zero new domain
errors**. The (filter-violation → exception → HTTP) mapping reuses
existing classes:

| Filter violation | Exception class | HTTP code | Source slice |
|------------------|-----------------|-----------|--------------|
| Deck archived (read paths) | mapping returns `None` from service → route maps to 404 | 404 | slice 6.4b-1 (existing) |
| Lesson archived (R-4) | mapping returns `None` from service → 404 | 404 | slice 6.4b-1 (existing) |
| Lesson draft (`published_at IS NULL`, R-4 / R-6 / R-7) | mapping returns `None` / empty list → 404 / 200 empty | 404 / 200 | slice 6.4b-1 (existing) |
| Quiz_item retired without progress (R-2) | `QuizItemRetiredError` | 409 | slice 6.2 (existing) |
| Quiz_item retired with progress (R-2) | NOT raised — review proceeds | 200 | slice 6.2 (existing — preserved) |
| Lesson or deck archived (R-2) | `QuizItemForbiddenError` | 403 | slice 6.2 (existing) |
| Persona-visibility mismatch (R-1, R-2, R-4, R-5, R-6, R-7) | mapping returns `None` from lesson_service / new `QuizItemNotVisibleError` from quiz_item_study_service review path | 404 across the board (per §12 **D-7**) — symmetric for information-leakage minimization | new `QuizItemNotVisibleError` class added per D-7 |
| Tier-vs-plan mismatch (locked at §12 **D-2**) | reuse `QuizItemForbiddenError` (403 with `detail.trigger='premium_deck'`) — slice 6.5 owns server-side guarantee | 403 | reuse existing |

> **Persona-visibility mapping subtlety (locked at §12 D-7).**
> lesson_service returns `None` (route → 404) on
> archive/draft/persona-mismatch — consistent across all four
> invariant axes that surface via lesson_service. The review path
> R-2 introduces a new `QuizItemNotVisibleError` (route → 404) for
> the persona-mismatch case only; existing `QuizItemForbiddenError`
> (403) is retained for archived-lesson / archived-deck per slice
> 6.2 §AC-5 (D-1 asymmetry). The 1:1 exception/HTTP-code map stays
> clean: each exception maps to exactly one HTTP code, with no
> route-layer detail-discrimination. Violates §2 G-4 ("zero new
> domain errors") by exactly one class — accepted at D-7 to keep
> the persona-mismatch axis 404-symmetric across all read paths.

The internal helper introduced by this slice (§4.4
`_persona_visible_to`) is **not** a Pydantic schema; it is a pure-
function predicate. No `app/schemas/*` files are touched.

## 6. BE service & route surface

### 6.1 `app/services/quiz_item_study_service.py` — additive filters

**File modified, signatures unchanged.** All four public functions
(`get_daily_quiz_items`, `review_quiz_item`, `get_quiz_progress`,
plus the `_compute_daily_quiz_status` helper) keep their existing
parameter lists.

#### 6.1.1 `get_daily_quiz_items` — add A-6 persona filter (both passes)

The existing `select(QuizItemProgress, QuizItem, Lesson, Deck)` join
chain on the overdue pass already loads `Deck`; add a
`Deck.persona_visibility.in_([...])` filter (or — equivalent — a
two-element OR for `'both'` + the user's persona). Same for the
fresh-fill pass.

```python
visible_personas = _visible_persona_set(user)  # {'both', user.persona}
overdue_stmt = (
    select(QuizItemProgress, QuizItem, Lesson, Deck)
    .join(QuizItem, QuizItem.id == QuizItemProgress.quiz_item_id)
    .join(Lesson, Lesson.id == QuizItem.lesson_id)
    .join(Deck, Deck.id == Lesson.deck_id)
    .where(QuizItemProgress.user_id == user_id)
    .where(QuizItemProgress.state != "new")
    .where(QuizItemProgress.due_date <= now)
    .where(QuizItem.retired_at.is_(None))
    .where(Lesson.archived_at.is_(None))
    .where(Deck.archived_at.is_(None))
    .where(Deck.persona_visibility.in_(visible_personas))   # ← new
    .order_by(QuizItemProgress.due_date.asc())
    .limit(_DAILY_GOAL)
)
```

If `user is None` (no User loaded), `visible_personas` collapses to
`{'both'}` — persona-null callers see only the cross-persona decks,
matching the slice 6.4 D-19 read-side guarantee. Note: the
`get_daily_quiz_items` route already loads the User via
`Depends(get_current_user)`, so `user is None` arises only in
service-layer test paths that bypass the route — defensive default.

Per §12 **D-2** lock (slice 6.5 owns server-side tier guarantee),
add `Deck.tier.in_(allowed_tiers_for_user(user))` alongside the
persona-visibility filter — both passes of the daily queue exclude
premium decks for free users.

#### 6.1.2 `review_quiz_item` — add A-6 persona filter (post-load)

The existing service already loads `(QuizItem, Lesson, Deck)` to
run the archive-guard (`if lesson.archived_at is not None or
deck.archived_at is not None: raise QuizItemForbiddenError`). Add
the persona check on the same loaded objects:

```python
qi_row = (
    await db.execute(
        select(QuizItem, Lesson, Deck)
        .join(Lesson, Lesson.id == QuizItem.lesson_id)
        .join(Deck, Deck.id == Lesson.deck_id)
        .where(QuizItem.id == quiz_item_id)
    )
).first()

if qi_row is None:
    raise QuizItemNotFoundError(quiz_item_id)

qi, lesson, deck = qi_row.QuizItem, qi_row.Lesson, qi_row.Deck

if lesson.archived_at is not None or deck.archived_at is not None:
    raise QuizItemForbiddenError(quiz_item_id)

# ← new: persona-visibility check
if not _persona_visible_to(deck.persona_visibility, user.persona if user else None):
    raise QuizItemNotVisibleError(quiz_item_id)   # new exception class per §12 D-7

# (existing retired-quiz / progress-row / FSRS path follows)
```

Per §12 **D-7** lock, raise a new `QuizItemNotVisibleError` (404)
to keep the route map's 1:1 exception/code shape clean. The
alternative (reuse `QuizItemForbiddenError` with detail
discrimination) is rejected.

Per §12 **D-2** lock (slice 6.5 owns server-side tier guarantee),
add a tier check after the persona check — raises 403 (the only
axis that legitimately *should* be 403, not 404; the deck exists
and the user can access it post-upgrade).

#### 6.1.3 `get_quiz_progress` — UNCHANGED

Per §3 non-goal. The aggregate-stats endpoint preserves the
slice-6.2 contract: count rows by `state`, no archive/retired/
persona/tier filtering. Locked filter-free at §12 **D-9** with
one anti-regression test per §10.2.

### 6.2 `app/services/lesson_service.py` — additive filters

**File modified, signatures unchanged.** All four public functions
keep their existing parameter lists. Persona-null users see only
`'both'`-visibility decks; persona-set users see `'both'` plus
their named persona.

The implementation slice introduces ONE shared helper (§4.4
`_persona_visible_to` and the `_visible_persona_set(user)` set
expansion), private to `lesson_service.py` per §12 **D-5**. The
helper is duplicated into `quiz_item_study_service.py`; if the
impl prompt judges the third on-disk consumer
(`deck_admin_service._PERSONA_EXPANSION` lines 28-33) tips past
the rule-of-three threshold, **D-5 escape hatch** lifts both
helpers to a new shared `app/services/curriculum_visibility.py`
public module.

#### 6.2.1 `get_lesson_with_quizzes(lesson_id, db, *, user)` — signature change ⚠

This is the **only signature change** in slice 6.5. The existing
function takes `(lesson_id, db)`; it cannot apply A-6 without
knowing the requesting user. The implementation slice extends the
signature to `(lesson_id, db, *, user: Optional[User] = None)` —
keyword-only so existing callers that pass two positional args do
not break (verified at impl by `git grep get_lesson_with_quizzes` —
the route layer is the sole caller and it has User-in-hand from
`Depends(get_current_user)`).

The route handler at `app/api/v1/routes/lessons.py` is updated to
pass `user=current_user` through. R3 — every existing route under
`/api/v1/lessons` already uses `Depends(get_current_user)` (verified
at slice 6.4b-1 audit time); no auth-gate addition required.

Add the persona filter as a SQL clause on `Deck.persona_visibility`
joined via `selectinload(Lesson.deck)` (already loaded for the
archive-guard):

```python
visible_personas = _visible_persona_set(user)
stmt = (
    select(Lesson)
    .options(
        selectinload(Lesson.quiz_items.and_(QuizItem.retired_at.is_(None))),
        selectinload(Lesson.deck),
    )
    .join(Deck, Deck.id == Lesson.deck_id)
    .where(Lesson.id == lesson_id)
    .where(Lesson.archived_at.is_(None))
    .where(Lesson.published_at.is_not(None))
    .where(Deck.persona_visibility.in_(visible_personas))   # ← new
)
# (existing post-load deck.archived_at check + return path follows)
```

The post-load `if deck is None or deck.archived_at is not None:
return None` check stays; the new SQL filter just narrows the
result set further.

#### 6.2.2 `get_deck_with_meta(deck_id, db, *, user)` — signature change ⚠

Same shape: keyword-only `user` param added; SQL filter
extended.

```python
visible_personas = _visible_persona_set(user)
stmt = (
    select(Deck)
    .where(Deck.id == deck_id)
    .where(Deck.archived_at.is_(None))
    .where(Deck.persona_visibility.in_(visible_personas))   # ← new
)
```

#### 6.2.3 `list_lessons_in_deck(deck_id, db, *, user)` — signature change ⚠

Same shape. Plus the table-row-³ defense-in-depth gap from §4.3 —
add the join + `Deck.archived_at.is_(None)` filter so a direct
caller can't leak archived-deck lessons:

```python
visible_personas = _visible_persona_set(user)
stmt = (
    select(Lesson)
    .join(Deck, Deck.id == Lesson.deck_id)                  # ← new (was implicit only via caller)
    .where(Lesson.deck_id == deck_id)
    .where(Lesson.archived_at.is_(None))
    .where(Lesson.published_at.is_not(None))
    .where(Deck.archived_at.is_(None))                       # ← new (defense-in-depth)
    .where(Deck.persona_visibility.in_(visible_personas))    # ← new
    .order_by(Lesson.display_order.asc(), Lesson.created_at.asc())
)
```

#### 6.2.4 `get_deck_lessons_bundle(deck_id, db, *, user)` — signature pass-through

```python
async def get_deck_lessons_bundle(deck_id, db, *, user=None):
    deck = await get_deck_with_meta(deck_id, db, user=user)
    if deck is None:
        return None
    lessons = await list_lessons_in_deck(deck_id, db, user=user)
    return DeckLessonsResponse(deck=deck, lessons=lessons)
```

The composition shape is unchanged; the `user` kwarg is threaded
through.

### 6.3 Helper extraction — `_persona_visible_to` + `_visible_persona_set`

Per §12 **D-5** lock — keep both private to `lesson_service.py`;
copy `_persona_visible_to` + `_visible_persona_set` into
`quiz_item_study_service.py` (small enough to duplicate; ~5 LOC).
**Escape hatch:** if the impl slice judges the third on-disk
consumer (`deck_admin_service._PERSONA_EXPANSION` lines 28-33)
tips past the rule-of-three threshold, promote to a new
`app/services/curriculum_visibility.py` module with two public
helpers and one shared `_PERSONA_EXPANSION` dict. Document the
choice in the impl slice's final-report JC line.

### 6.4 Route layer — exception-to-HTTP mapping

Existing routes at `app/api/v1/routes/lessons.py`,
`app/api/v1/routes/quiz_items.py` already map slice-6.2 / slice-6.4b-1
exceptions to HTTP codes via `HTTPException(status_code=…,
detail=str(exc))`. Slice 6.5 ADDS exactly one mapping per §12
**D-7**: the new `QuizItemNotVisibleError` → route maps to 404.
The alternative (reuse `QuizItemForbiddenError` with detail
discrimination) is rejected by D-7.

Per §12 **D-2** lock: existing `QuizItemForbiddenError` (or a new
`QuizItemTierError` per impl-slice judgment) is mapped to 403 with
`detail.trigger='premium_deck'` for free-user-on-premium-deck reads.
Implementation-slice JC: pick between exception-class reuse vs new
`QuizItemTierError` for the tier rejection path.

### 6.5 No new HTTP routes, no new admin surface, no new schemas

Service-layer hardening only. All existing route handler files
(`lessons.py`, `quiz_items.py`, `decks.py`) require either no
change (if no new exception is added) or a single mapping line
(`QuizItemNotVisibleError` lands per §12 **D-7**).

## 7. Migration

**No Alembic migration this slice.** Slice 6.1 schema columns
(`decks.archived_at`, `decks.persona_visibility`, `decks.tier`,
`lessons.archived_at`, `lessons.published_at`, `quiz_items.retired_at`)
are sufficient; the read-time invariants are filter additions on
existing tables.

## 8. FE component graph

**No FE deliverable this slice.**

The seven service-layer reads surface through routes consumed by:

- `pages/Lesson.tsx` (slice 6.3) — consumes
  `GET /api/v1/lessons/{id}` backed by `get_lesson_with_quizzes`.
- `services/api.ts` `recordLessonView` (slice 6.0 / 6.3) — same
  route shape; not affected by read-time invariants except via the
  same 404 path.
- Future slice 6.7 / 6.12 Learn-page — consumes
  `GET /api/v1/decks` (`list_admin_decks` admin-side OR a new user-
  side route slice 6.7 will spec) backed by `lesson_service.*`.
- `pages/DailyReview.tsx` (slice 6.3 future-state) — consumes
  `GET /api/v1/quiz-items/daily` backed by `get_daily_quiz_items`.

After slice 6.5 ships, these consumers see **the same response
shapes** as today; the only behavioral change is that some 200
responses become 404 (persona/archive mismatch) or 403 (tier
mismatch per §12 **D-2**). Existing FE error-handling
patterns (which already handle `archived_lesson` 404 from slice
6.4b-1 paths) absorb the new 404 paths transparently. The FE does
NOT need a new error-class branch.

The implementation slice records "FE consumer graph" as **N/A —
service-layer hardening; existing 404 / 403 paths reused** in its
final report. R16 component-graph audit is satisfied vacuously.

## 9. Analytics events declared by this slice

**Zero new PostHog events.** Existing slice 6.2 events
(`quiz_item_progress_initialized`, `quiz_item_reviewed`) and slice
6.0 events (`lesson_viewed`) carry forward unchanged.

The implementation slice MAY add stdlib `logger.info` lines on
filter-violation rejection paths for ops observability — e.g.:

```python
logger.info(
    "read_invariant_rejected",
    extra={
        "path": "review_quiz_item",
        "user_id": user_id,
        "quiz_item_id": quiz_item_id,
        "reason": "persona_visibility_mismatch",
    },
)
```

These are NOT PostHog events. Per §12 **D-8** lock, the
paywall-blocked-at-read PostHog event (if any) belongs to slice 6.7
when the FE Learn-page composition surfaces the paywall.

`.agent/skills/analytics.md` requires no edits this slice.

## 10. Test plan (implementation slice)

> This spec lists tests the implementation slice will add. No test
> code is written in this spec slice. Test count delta target: **+15
> to +25 BE, +0 FE** (FE has zero surface).

Per §12 **D-4** lock, tests split per service across two files:

### 10.1 Backend — `tests/test_quiz_item_study_service_invariants.py` (~6-10 tests)

For each (R-1, R-2) × (A-1, A-2, A-4, A-5, A-6) cell where the
filter applies, one test for the rejection path and one test for
the permitted path (where a permitted path exists — A-5 has only a
permitted path; A-1/A-2/A-4 have only rejection paths from the
review-route view since archived/retired-no-progress is the
violation).

- `test_get_daily_quiz_items_excludes_persona_narrowed_decks` —
  user with `persona='climber'`; deck visibility `'interview_prepper'`;
  pre-seeded with one due quiz_item from that deck. Assert the
  daily queue does not include it.
- `test_get_daily_quiz_items_includes_both_visibility_decks` —
  same user; deck visibility `'both'`; assert included.
- `test_get_daily_quiz_items_persona_null_user_sees_only_both` —
  `user.persona is None`; only `'both'` decks surface.
- `test_review_quiz_item_persona_mismatch_raises_404` —
  user `persona='climber'`; quiz_item is in a deck with
  `persona_visibility='interview_prepper'`. Assert raises the new
  `QuizItemNotVisibleError` (per §12 **D-7** lock — route maps to
  404).
- `test_review_quiz_item_persona_match_succeeds` — same shape but
  matching persona; 200.
- `test_review_quiz_item_archived_deck_still_403` — regression on
  slice 6.2 §AC-5; archived deck still raises
  `QuizItemForbiddenError` (existing code path); ensures slice 6.5
  filter additions did not change the archived-deck behavior.
- `test_review_quiz_item_retired_with_progress_still_succeeds` —
  regression on slice 6.2 §AC-4 + §4.6 D-4; retired-with-existing-
  progress still permitted.
- (Per §12 **D-2** lock) `test_review_quiz_item_premium_deck_free_user_403` —
  `Deck.tier='premium'`, user plan free; raises 403. Unconditional
  per D-2.

### 10.2 Backend — `tests/test_lesson_service_invariants.py` (~9-15 tests)

For each (R-4, R-5, R-6, R-7) × (A-1, A-2, A-3, A-6) cell where
the filter applies, one rejection-path + one permitted-path test.
Note R-6's `Deck.archived_at` defense-in-depth gap gets an
explicit test even though it's not user-reachable today (slice
6.6 will reach it).

- `test_get_lesson_with_quizzes_persona_narrowed_returns_none` —
  user `persona='climber'`; lesson belongs to a deck with
  `persona_visibility='interview_prepper'`; assert `None`.
- `test_get_lesson_with_quizzes_persona_null_user_sees_only_both` —
  `user is None`; only `'both'` decks surface.
- `test_get_lesson_with_quizzes_archived_deck_still_returns_none` —
  regression on slice 6.4b-1 deck-archive semantic.
- `test_get_lesson_with_quizzes_unpublished_still_returns_none` —
  regression on `published_at IS NULL` filter.
- `test_get_lesson_with_quizzes_retired_quiz_items_excluded` —
  regression on selectinload retired-quiz_item filter.
- `test_get_deck_with_meta_persona_narrowed_returns_none`.
- `test_list_lessons_in_deck_archived_deck_returns_empty_list` —
  the §4.3 note ³ defense-in-depth gap; pre-seeds an archived
  deck with active published lessons; assert empty list.
- `test_list_lessons_in_deck_persona_narrowed_returns_empty_list`.
- `test_get_deck_lessons_bundle_persona_narrowed_returns_none` —
  composes via `get_deck_with_meta` rejection.
- `test_get_deck_lessons_bundle_archived_deck_returns_none` —
  regression on slice 6.4b-1 deck-archive semantic via R-7.
- (Per §12 **D-2** lock) `test_get_lesson_with_quizzes_premium_deck_free_user_returns_none_or_403` —
  free user on a premium-tier deck; impl slice picks 403 raise vs
  `None` → 404 per D-2 lesson_service surface judgment (default
  leans toward 403 since tier is fundamentally distinguishable
  from non-existence).
- (Per §12 **D-9** lock — `get_quiz_progress` filter-free positive invariant)
  `test_get_quiz_progress_counts_progress_on_archived_lessons` —
  pre-seeds a user with progress on a now-archived lesson; assert
  the row IS counted (per §3 non-goal). Anti-regression test for
  the analytics-by-design behavior.

### 10.3 Backend — regression suite stays green

Slice 6.2 + slice 6.4b-1 existing tests run unmodified. AC-13.

### 10.4 No FE tests

Zero FE surface this slice; no new FE tests are added.

## 11. Acceptance criteria

The implementation slice (one-step follow-up) must pass:

- **AC-1** — Every cell in §4.3 marked `✗ → ADD` is satisfied on
  disk: the corresponding service function applies the
  corresponding SQL filter (or post-load check) per §6.
- **AC-2** — `_persona_visible_to(deck_persona, user_persona)`
  returns `True` iff (a) `deck_persona == 'both'` OR (b)
  `user_persona is not None AND deck_persona == user_persona`.
  Verified by a unit test on the helper.
- **AC-3** — `_visible_persona_set(user)` returns `{'both',
  user.persona}` for a persona-set user; `{'both'}` for a
  persona-null user. Verified by a unit test.
- **AC-4** — `quiz_item_study_service.get_daily_quiz_items` excludes
  quiz_items in persona-narrowed decks for the requesting user
  on BOTH the overdue pass and the fresh-fill pass (test 10.1
  case 1).
- **AC-5** — `quiz_item_study_service.review_quiz_item` raises
  the new `QuizItemNotVisibleError` (per §12 **D-7**) on persona
  mismatch BEFORE touching any FSRS state or progress row (no
  side-effect on rejection path).
- **AC-6** — `lesson_service.get_lesson_with_quizzes` returns
  `None` (route → 404) on persona mismatch.
- **AC-7** — `lesson_service.get_deck_with_meta` returns `None`
  on persona mismatch.
- **AC-8** — `lesson_service.list_lessons_in_deck` returns `[]`
  on archived deck (§4.3 note ³ defense-in-depth gap closed) AND
  on persona mismatch.
- **AC-9** — `lesson_service.get_deck_lessons_bundle` returns
  `None` on persona mismatch (composes via `get_deck_with_meta`).
- **AC-10** — Slice 6.2 §AC-4 (retired-with-progress permitted) +
  §AC-5 (archived-deck 403) hold unchanged. Verified by the
  10.1 regression tests.
- **AC-11** — Slice 6.4b-1 read-path tests stay green (no
  modification needed; new filters narrow but do not contradict
  existing rejections).
- **AC-12** — Slice 6.0 `analytics_event_service` dual-write hook
  in `review_quiz_item` is unaffected (the rejection paths short-
  circuit BEFORE the analytics call; permitted paths preserve the
  existing dual-write).
- **AC-13** — Test suite stays green (BE 577 → 577 + N where N is
  the §10 delta). New tests run under default `not integration`
  selector (no LLM keys required).
- **AC-14** — Per §12 **D-2** + **D-10** lock (slice 6.5 owns server-
  side tier guarantee): a free user calling a premium-deck read path
  on `quiz_item_study_service` (R-1 / R-2) receives 403; on
  `lesson_service` (R-4 / R-5 / R-6 / R-7) receives 403 unconditionally
  per the **D-10** lock (the impl-slice judgment between 403 vs
  `None` → 404 was resolved at impl time in favor of 403, since tier
  mismatch is fundamentally different from archive/persona-mismatch
  — the deck exists and the user can access it post-upgrade).

## 12. Decisions

> §14 OQ-1..OQ-9 all RESOLVED at spec amendment `acba7ed` —
> locked into §12 as D-1..D-9 below, mirroring slice 6.0 §12
> amendment (`e8eecdd`) + slice 6.4.5 §12 amendment (`df58eaf`)
> precedent. Locks honor the §14 author hints verbatim where on-
> disk and prompt-side phrasings agree; divergences resolved in
> favor of the on-disk hint per R3 (the spec body authored the
> hints, prompt is codifying them).
>
> Phase-level decisions (G2, H1, I1, J2) carry forward from slice
> 6.1; cross-ref §front-matter table for each.
>
> §14 OQ-1c (implicit-via-admin-write A-3 invariant on R-1 / R-2)
> is **NOT locked at this amendment** — the prompt that drafted this
> amendment listed only OQ-1..OQ-9; OQ-1c remains open at author hint
> "(a) leave implicit." A future spec amendment may lock it as
> D-10 if the impl slice surfaces a need; otherwise OQ-1c stays as
> a documented design note.

### Phase-level decision rationale

Phase-level locks (G2, H1, I1, J2) cited in front-matter; rationale
inherits from slice 6.1 §11 + slice 6.0 §12 amendment. Slice 6.5
consumes none of them at runtime — the read-time invariants are pure
filter additions on existing tables, with no async fan-out (G2),
no file I/O (H1), no events table writes (I1 carries forward
unchanged), and no quality-signal coupling (J2).

### Slice-local decisions

- **D-1 (resolves OQ-1) — Status code asymmetry on archived-deck
  violations: ACCEPT.** lesson_service paths (R-4 / R-5 / R-6 /
  R-7) return `None` → route maps to **404** (treat as nonexistent
  — minimizes information leakage); the review path R-2
  (`review_quiz_item`) retains the **403** (`QuizItemForbiddenError`)
  contract from slice 6.2 §AC-5. Rationale: a user on the review
  path already holds a `quiz_item_id`, so existence is not
  concealable; 403 "you can no longer act on this" is the right
  semantic. lesson_service callers don't yet have a handle, so
  404 minimizes leakage. Slice 6.2 §AC-5 is **NOT amended**; the
  asymmetry is a deliberate contract. On-disk OQ-1 hint (a) [404 on
  lesson_service] + JC resolution (b) [accept asymmetry; review
  path retains 403] both honored. Cross-ref §4.3 R-2 row, §6.1
  (review path), §6.2 (lesson_service paths).

- **D-2 (resolves OQ-2) — Tier paywall ownership: SPLIT.** Slice
  6.5 owns the **server-side guarantee** — read service layer
  raises 403 (`QuizItemForbiddenError` reused, OR a future
  `QuizItemTierError` per impl-slice judgment) when a free user
  attempts to read a `Deck.tier == 'premium'` deck or its
  lessons/quiz_items. Slice 6.7 owns the **user-facing paywall UX**
  — Learn-page composition, paywall modal copy, upsell composition.
  The two layers ship in series: 6.5 ensures the API never returns
  premium content to free users; 6.7 makes the rejection user-
  friendly. lesson_service surface for premium-deck-on-free-user
  returns 403 / `None` → route maps appropriately (per impl-slice
  judgment between 403 vs 404 for the lesson_service surface; the
  prompt-side condensation chose 403, the on-disk hint left both
  options open — escape-hatch is the impl prompt). Cross-ref §4.3
  A-7 column (now `✗ → ADD` across R-1, R-2, R-4, R-5, R-6, R-7),
  §11 AC-14 (now unconditional), §13 Out of scope (UX surface
  deferred to slice 6.7).

- **D-3 (resolves OQ-3) — persona_visibility filter scope: ALL
  SIX READ PATHS.** A-6 applies to all four `lesson_service` reads
  (R-4 / R-5 / R-6 / R-7) AND both `quiz_item_study_service`
  user-facing reads (R-1 / R-2). A user in a now-excluded persona
  who has a bookmarked `/learn/decks/{id}` URL OR a stored
  `quiz_item_id` from a prior session must receive 404 (not just
  the LIST surface). Filter applies at the SERVICE layer; routes
  inherit. Information-leakage-minimization rationale per §4.2
  A-1 vs A-6 note. Cross-ref §4.3 A-6 column, §6.1 + §6.2 filter
  additions.

- **D-4 (resolves OQ-4) — Test-file structure: SPLIT PER
  SERVICE.** Two new test files at impl: `tests/test_quiz_item_study_service_invariants.py`
  (covers §4 rows R-1 / R-2 / R-3 — quiz-item paths) +
  `tests/test_lesson_service_invariants.py` (covers §4 rows
  R-4 / R-5 / R-6 / R-7 — lesson/deck paths). Co-located with
  existing per-service test files; easier to find regressions;
  matches slice 6.2 / 6.4b-1 test-file naming convention. Rejected
  alternative: single `tests/test_phase6_read_time_invariants.py`
  spanning both services — would force per-service regression
  triage to grep across one file instead of opening the right one.
  Cross-ref §10.

- **D-5 (resolves OQ-5) — Helper extraction strategy: PRIVATE
  DUPLICATE WITH ESCAPE HATCH.** `_persona_visible_to(deck_persona,
  user_persona) -> bool` + `_visible_persona_set(user) -> set[str]`
  ship as **private** helpers in `lesson_service.py`, duplicated
  (~5 LOC) into `quiz_item_study_service.py`. Rationale: small
  enough not to be a maintenance burden; slice 6.15 cleanup
  (which retires `study_service.py`) is the natural moment to
  consolidate visibility helpers. **Escape hatch:** if the impl
  prompt judges the third on-disk consumer
  (`deck_admin_service._PERSONA_EXPANSION` lines 28-33) raises
  the duplicate count past the rule-of-three threshold, the
  helpers MAY lift to a new shared `app/services/curriculum_visibility.py`
  module (public, no leading underscore — the original on-disk
  hint option (b) phrasing); document the decision in the impl
  slice's final-report JC line. Both options are acceptable;
  defer to impl-time judgment. Cross-ref §6.3.

- **D-6 (resolves OQ-6) — Cascade-retired vs direct-retired
  read-time treatment: IDENTICAL.** Both retirement paths set
  `quiz_items.retired_at IS NOT NULL`; the `superseded_by_id`
  discriminator is for admin authoring contexts (slice 6.4b retire-
  and-replace audit trail + future FSRS-history forward-link
  queries), NOT for read paths. Read service layer treats both
  equivalently: the `QuizItem.retired_at.is_(None)` filter applies
  uniformly; existing `quiz_item_progress` for the retired
  quiz_item permits continued review per slice 6.2 §AC-4
  (history preservation); no `quiz_item_progress` permits 409
  per slice 6.2 §AC-4 (retired-no-progress block). Cross-ref §4.3
  A-4 / A-5 columns, §6.1 review-path retired guard.

- **D-7 (resolves OQ-7) — Persona-mismatch HTTP code + new
  exception class: 404 + `QuizItemNotVisibleError`.** All read-
  path persona-visibility violations surface as 404 (information-
  leakage minimization — a user in a now-excluded persona is
  indistinguishable from a user pointing at a nonexistent
  resource). lesson_service paths (R-4 / R-5 / R-6 / R-7) return
  `None` → route maps to 404 (existing convention). The review
  path R-2 (`review_quiz_item`) introduces a **new exception class**
  `QuizItemNotVisibleError` (route maps to 404) so the 1:1
  exception/HTTP-code map stays clean and the persona-mismatch
  axis is symmetric across all read paths. Slightly violates §2
  G-4 ("zero new domain errors") — accepted: one new exception
  class is judged worth it to keep the contract symmetric vs the
  alternative of reusing `QuizItemForbiddenError` (403) with a
  `detail.reason='persona_visibility'` discriminator (asymmetric
  HTTP codes for the same logical violation). Existing
  `quiz_item_progress` rows for orphaned-persona users stay
  queryable for analytics per slice 6.4 D-19 (cleanup explicitly
  deferred to slice 6.7 / 6.8). Cross-ref §4.3 A-6 column, §5
  exception/HTTP map, §6.1.2 review path, §6.4 route mapping.

- **D-8 (resolves OQ-8) — Paywall-blocked-at-read PostHog
  telemetry: NONE this slice.** Zero new PostHog events in slice
  6.5. Slice 6.7 owns paywall telemetry — will likely add
  `paywall_shown` / `paywall_dismissed` / `paywall_upgrade_clicked`
  per slice 6.7's persona Learn-page surface; adding a slice-6.5
  event would create a duplicate that forces a deprecation when
  6.7 lands. Filter-violation rejection paths emit stdlib
  `logger.info("read_time_invariant_violation", extra={"axis":
  "...", "user_id": "...", "deck_id": "..."})` for ops
  observability only. `.agent/skills/analytics.md` requires no
  edits. Cross-ref §9 (zero events confirmed), §13 Out of scope.

- **D-9 (resolves OQ-9) — `get_quiz_progress` aggregation
  invariants: CODIFY AS POSITIVE INVARIANT.** R-3
  (`get_quiz_progress`) is **filter-free by design** — it
  aggregates `quiz_item_progress` rows by `state` regardless of
  whether the underlying quiz_item is retired, the lesson is
  archived, or the deck is persona-narrowed away. This is locked
  as a positive invariant ("aggregation is filter-free for
  retention metrics"), not just a §3 non-goal. The impl slice
  ships **one anti-regression test** asserting that orphan
  progress rows (on archived lessons / retired quiz_items /
  persona-narrowed decks) ARE counted in `total_reps` /
  `total_lapses` / `by_state`. Rationale: a future slice (e.g.
  slice 6.16 retention dashboard) may inadvertently add a filter
  to `get_quiz_progress` and silently break the slice 6.5 design
  intent; one test locks the contract. Cross-ref §3 non-goal,
  §10.2 conditional case (now unconditional). **DIVERGENCE
  FLAG:** the prompt that drafted this §12 amendment proposed a
  different D-9 (table-format inline-vs-separate-file question);
  that question was never authored as an on-disk OQ. Per R3,
  on-disk OQ-9 (`get_quiz_progress` aggregation) is canonical and
  D-9 locks it; the prompt-side table-format question is moot
  (the on-disk spec already chose inline §4 format). Logged as
  JC in the amendment's final report.

- **D-10 (extends D-2) — `lesson_service` tier-mismatch surface
  = `QuizItemForbiddenError` (reason='premium_deck') → 403.**
  Inline-amended at the slice 6.5 implementation commit (R14(b)
  pure codification of the impl-slice judgment foreshadowed in
  §6.4 + §11 AC-14). The four `lesson_service` public reads
  (R-4 / R-5 / R-6 / R-7) raise `QuizItemForbiddenError` (with
  the new keyword-only `reason='premium_deck'` constructor field)
  on free-user-on-premium-deck access, mirroring the
  `quiz_item_study_service` shape locked at D-2. Routes
  (`lessons.py`, `decks.py`) catch the exception and return 403,
  identical to the existing `quiz_items.py` review-route
  mapping. **Rationale:** tier mismatch is fundamentally
  distinguishable from non-existence (the deck exists and the
  user can access it post-upgrade); 404 would lose this
  distinction and would block slice 6.7 from composing a
  "deck exists, you need Pro" upsell surface. Reuse of the
  existing `QuizItemForbiddenError` class — extended with the
  `reason` kwarg (defaulting to `'archived'` so slice 6.2
  call sites are unchanged) — is preferred over introducing a
  new `DeckTierError` / `PremiumDeckRequiresUpgradeError` per the
  impl-slice "ONE new error class is the locked exception (the
  D-7 `QuizItemNotVisibleError`); do not introduce others"
  constraint. The class name is mildly awkward when raised by
  `lesson_service` (no `quiz_item_id` in scope; the constructor's
  first positional arg carries `lesson_id` / `deck_id` for those
  call sites) — accepted as the cost of holding §2 G-4 to ONE
  net-new exception. Cross-ref D-2, §4.3 A-7 column, §5
  exception-to-HTTP map (now reads "reuse `QuizItemForbiddenError`
  with `reason='premium_deck'`"), §6.4 route-mapping note (the
  "or new `QuizItemTierError` per impl-slice judgment"
  alternative is rejected by D-10), §11 AC-14 (now unconditional
  per D-10).

## 13. Out of scope (deferred to other Phase-6 slices)

Explicit list:

- **Orphan progress-row cleanup on persona narrowing / lesson
  archiving / quiz_item retirement.** Slice 6.4 D-19 punted to
  slice 6.7 / 6.8. Slice 6.5 owns READ-time treatment only.
- **Tier-paywall UX surface.** Slice 6.7 — Learn-page composition
  with paywall modal. Slice 6.5 may own at most the server-side
  403 per §14 OQ-2 disposition.
- **FSRS-history backfill on cascade-retired quiz_items.** Slice
  6.5 enforces "FSRS state preserved on retired rows" but does
  NOT backfill historical reviews onto cascade victims.
- **Admin audit log of read-time invariant violations.** A free
  user who hits a 403 on a premium deck does not generate a row
  in `admin_audit_log`. Standard `logger.info` is the surface.
- **PostHog telemetry on read-time rejection paths.** Slice 6.7
  owns paywall telemetry; slice 6.5 logs via `logger.info` only.
- **Cross-deck invariants** ("user can't have progress on
  quiz_items from decks they've never been able to see"). Out
  of scope; per-request, per-path read-time invariants only.
- **`get_quiz_progress` filtering.** Per §3 non-goal — analytics-
  by-design behavior; orphan progress rows preserved for
  retention metrics.
- **Admin-side read paths.** Admin LIST routes intentionally
  surface drafts + archived rows + retired quiz_items per slice
  6.4 §5; admins are NOT subject to the §4 read-time invariants.
- **DB schema changes.** Slice 6.1 already shipped all the
  columns this slice's filters touch. N7 STOP if a gap surfaces.
- **New routes / new schemas.** Service-layer hardening only.
- **FE consumer surface.** Zero FE deliverables; new 404 / 403
  paths absorbed by existing FE error-handling.

## 14. Open questions

> **OQ-1..OQ-9 all RESOLVED at spec amendment `acba7ed`** —
> locked into §12 as D-1..D-9 respectively. OQ headings + question
> text retained verbatim below for forward-readability; the
> resolution line cites the §12 D-N decision that closes each one.
> Mirrors slice 6.0 §14 OQ-1..OQ-4 + slice 6.4.5 §14 OQ-1..OQ-10
> post-amendment shape (`e8eecdd` / `df58eaf`).
>
> OQ-1c remains OPEN — the amendment prompt did not include it in
> the OQ-1..OQ-9 lock list; revisited if the impl slice surfaces a
> need.

### OQ-1 — `Deck.archived_at` violation status code

A-1 surfaces as 404 (treat as nonexistent) or 403 (signaling
existence-but-forbidden) on the lesson_service paths? Today's
lesson_service surface returns `None` (route → 404), so 404 is
already on disk; the question is whether the formal contract pins
404 or leaves room for a future 403 escalation. JC sub-question:
slice 6.2 §AC-5 ships 403 on the review path for archived-deck —
amend or accept the asymmetry?

**RESOLVED** — see §12 **D-1** (`acba7ed`): accept the
asymmetry. lesson_service paths return 404; review path R-2
retains 403 per slice 6.2 §AC-5 (privileged: caller already
holds `quiz_item_id`). On-disk hint (a) [404 lesson_service] +
JC resolution (b) [accept asymmetry] both honored.

### OQ-1c — Implicit-via-admin-write A-3 invariant on R-1 / R-2

§4.3 footnotes ¹ + ² note that R-1 and R-2 do NOT filter
`Lesson.published_at IS NOT NULL`; the invariant is implicit because
admin write-paths only assign `quiz_items.lesson_id` to lessons that
have been published. Should slice 6.5 codify A-3 explicitly on R-1
and R-2 (defense in depth) or leave the invariant implicit?

**Author hint:** (a) leave implicit. Adding the filter on R-1's two
passes would force a `Lesson.published_at IS NOT NULL` clause on a
hot daily-queue path that today does not need it. The implicit
invariant has held since slice 6.2 ship (`7b654fb`); no production
incident has surfaced. If a future slice introduces a
`quiz_items.lesson_id` write path that bypasses `publish_lesson`
(e.g. an ingestion pipeline in slice 6.10), THAT slice owns the
re-codification. **OQ-1c stays OPEN at this amendment** — not in
the OQ-1..OQ-9 lock list per the amendment prompt's scope; the
author hint stands as the working disposition until a future
amendment locks it (likely as D-10 if/when a write-path bypass
materializes).

### OQ-2 — Tier paywall enforcement ownership: slice 6.5 vs slice 6.7

A-7 (free-user-on-premium-deck) is the only invariant axis that's
in genuine tension between Phase-6 slices. Slice 6.7 is "persona
Learn-page composition" per scout Track C; tier gating is naturally
visible there (paywall modal copy on the Learn page). But slice
6.5's invariant table is structurally incomplete without A-7.

**RESOLVED** — see §12 **D-2** (`acba7ed`): split. Slice 6.5
owns the server-side guarantee (read service layer raises 403 for
free-user-on-premium-deck reads); slice 6.7 owns the user-facing
paywall UX (Learn-page composition, paywall modal copy). §4.3 A-7
column is `✗ → ADD` on R-1 / R-2 / R-4 / R-5 / R-6 / R-7; AC-14
is unconditional.

### OQ-3 — Persona-visibility filter scope: deck-LIST only OR deck-LIST + deck-DETAIL

A-6 needs to apply to all four lesson_service read paths PLUS
the two quiz_item_study_service paths, OR only to the LIST paths?

**RESOLVED** — see §12 **D-3** (`acba7ed`): all six paths
(R-1, R-2, R-4, R-5, R-6, R-7). Bookmarked `/learn/decks/{id}`
URLs and stored `quiz_item_id`s must also receive 404, not just
the LIST surface. Author hint (a) selected.

### OQ-4 — Test-file structure: single file vs split per service

Single `tests/test_phase6_read_time_invariants.py` covering all
seven read paths, OR split per service (`test_quiz_item_study_service_invariants.py`
+ `test_lesson_service_invariants.py`)?

**RESOLVED** — see §12 **D-4** (`acba7ed`): split per service.
Co-located with existing per-service test files; easier per-service
regression triage. Author hint (b) selected.

### OQ-5 — Helper extraction location: private to lesson_service vs new module

`_persona_visible_to` + `_visible_persona_set` are needed in BOTH
`quiz_item_study_service` and `lesson_service`. Options were (a)
private duplicate, (b) new shared `app/services/curriculum_visibility.py`,
(c) defensive shim. Complication: `deck_admin_service.py` already
has a private `_PERSONA_EXPANSION` dict (lines 28-33) — possible
third on-disk consumer.

**RESOLVED** — see §12 **D-5** (`acba7ed`): private duplicate
in `lesson_service.py` + duplicated into `quiz_item_study_service.py`,
with an **escape hatch** for the impl prompt to lift to a shared
`app/services/curriculum_visibility.py` if the third on-disk
consumer (`deck_admin_service._PERSONA_EXPANSION`) tips past the
rule-of-three threshold. Author hint (a) selected as default;
(b) reserved as escape hatch.

### OQ-6 — Cascade-retired vs direct-retired quiz_items: identical read-time treatment?

Slice 6.4 §7.3 ships the substantive-edit cascade (lesson PATCH
retires all active quiz_items in the lesson). Slice 6.4b-1
`quiz_item_admin_service.update_quiz_item` ships the per-quiz_item
retire-and-replace. Both paths set `retired_at IS NOT NULL` + may
set `superseded_by_id`. Does slice 6.5 read-time treatment depend
on which retire path produced the row?

**RESOLVED** — see §12 **D-6** (`acba7ed`): identical. Both
paths set `retired_at`; `superseded_by_id` is admin-authoring
metadata, not a read-path discriminator. The
`QuizItem.retired_at.is_(None)` filter applies uniformly. Author
hint (a) selected.

### OQ-7 — Persona mismatch HTTP code: 404 vs 403 — and the new exception class question

Per §5 mapping subtlety. Options were (a) reuse
`QuizItemForbiddenError` (403) with a `detail.reason='persona_visibility'`
discriminator (asymmetric across read paths), or (b) introduce a
new `QuizItemNotVisibleError` (404) for the review path
specifically (symmetric: 404 across all read paths).

**RESOLVED** — see §12 **D-7** (`acba7ed`): 404 across all
read paths via a new `QuizItemNotVisibleError` exception class on
the review path; lesson_service paths continue returning `None` →
404. Author hint (b) selected. Slightly violates §2 G-4 ("zero
new domain errors") — accepted to keep the contract symmetric.

### OQ-8 — PostHog telemetry on filter-violation rejection paths

Should slice 6.5 emit a `paywall_blocked_at_read` (or similar)
event when a free user hits a premium deck read, or when a
persona-narrowed user hits a now-excluded deck?

**RESOLVED** — see §12 **D-8** (`acba7ed`): NO new PostHog
event this slice. Slice 6.7 owns paywall telemetry; rejection
paths emit stdlib `logger.info("read_time_invariant_violation",
…)` for ops observability only. Author hint (b) selected.

### OQ-9 — `get_quiz_progress` aggregation invariants

§3 non-goal: orphan progress rows (on archived lessons / retired
quiz_items / persona-narrowed decks) are intentionally counted in
the aggregate. Should slice 6.5 codify this as a positive
invariant ("aggregation is filter-free") with a regression test,
or leave it as a §3 non-goal only?

**RESOLVED** — see §12 **D-9** (`acba7ed`): codify as a
positive invariant. The impl slice ships one anti-regression test
asserting orphan progress rows ARE counted in `total_reps` /
`total_lapses` / `by_state`. Future slice 6.16 retention dashboard
must NOT silently add a filter to `get_quiz_progress`. Author hint
(a) selected.

### OQ-10+ (placeholder)

If chat-Claude or impl-time CC surfaces additional product OQs at
spec-amendment time, file them as OQ-10 / OQ-11 / etc. below.
OQ-1c remains a candidate for OQ-10 / D-10 if the impl slice
surfaces a write-path bypass that breaks the implicit A-3
invariant.

---

*End of slice 6.5 spec. Authored 2026-04-28 at HEAD `688d178`.
§12 amended 2026-04-28 at `acba7ed` locking D-1..D-9 from
§14 OQ-1..OQ-9. Audit basis: live `app/services/{quiz_item_study_service,
lesson_service,quiz_item_admin_service,deck_admin_service,
lesson_admin_service}.py` shapes at HEAD; spec basis
`docs/specs/phase-6/01-foundation-schema.md` §4.1/§4.2/§4.3 +
`02-fsrs-quiz-item-binding.md` §4.5/§4.6 + `04-admin-authoring.md`
§7 + §12 D-15/D-18/D-19 + `05-seed-lessons.md` §6.1.2 + D-5.
Next step: Mode 1 implementation slice executes against this spec
— files B-072 close-line at execution time per R17.*
