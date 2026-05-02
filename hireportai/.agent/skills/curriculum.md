---
description: Phase 6 curriculum platform — deck/lesson/quiz_item domain model, lifecycle filters, substantive-edit cascade, dual-write analytics, seed corpus, ranker contract
---
# Curriculum Skill

## Purpose

How Phase 6 content (decks, lessons, quiz_items) is shaped, filtered,
authored, seeded, ranked, and observed. Read before authoring or
modifying any Phase 6 slice from 6.0 onward, or when a slice touches
deck/lesson/quiz_item read or write paths.

Adjacent skills cover orthogonal layers: `backend.md` (service +
route + error class conventions), `study-engine.md` (FSRS scheduler
internals), `analytics.md` (PostHog event catalog + dual-write
mechanics), `admin-panel.md` (admin auth chain + audit log + admin
write surfaces), `database-schema.md` (column-level contracts),
`db-migration.md` (Alembic). When a Phase 6 detail clearly belongs
in one of those, defer there and link from here.

## 1. Domain model

```
deck (12 locked top-level buckets)
  └── lesson (one card on the Learn page; 4-section render
              concept_md / production_md / examples_md + quiz panel)
        └── quiz_item (atomic FSRS-reviewable recall unit)
              └── quiz_item_progress (per-(user, quiz_item) FSRS state)
```

One deck has many lessons; one lesson has many quiz_items; one user has
0..1 progress row per quiz_item.

**lesson ≠ quiz_item.** Lessons are *content* (Markdown bodies);
quiz_items are *scheduled review units*. **FSRS lives on
`quiz_item_progress`, not on the lesson.** A substantive lesson edit
retires the lesson's quiz_items (§4) but does NOT mutate FSRS state on
existing progress rows — history-preservation invariant is locked at
slice 6.2 §4.6 D-4.

`quiz_item_progress` is byte-identical to legacy `card_progress` modulo
the FK swap (`card_id` → `quiz_item_id`) — same `state` /
`stability` / `difficulty_fsrs` / `due_date` / `reps` / `lapses` columns,
same `Float` types, so the slice 6.2 service code mirrors
`study_service.review_card` line-for-line modulo the FK.

The legacy `cards` / `categories` / `card_progress` / `card_feedback`
tables remain on disk through Phase 6; the **drop** is deferred to
slice 6.15 (cleanup) per spec #01 §2 goal 3.

## 2. Lifecycle states & the visibility filter chain

Every read path that surfaces curriculum content to a user must apply
**the same filter chain** in service-layer code. Spec #06 §4.3 is the
exhaustive contract; this section is the cliff-notes version.

Lifecycle columns (slice 6.1 §4):

- `decks.archived_at` — soft-delete; archived decks vanish from user-
  facing reads, FK references stay intact for audit.
- `decks.persona_visibility` — `'climber' | 'interview_prepper' | 'both'`;
  drives Learn-page filtering.
- `decks.tier` — `'foundation' | 'premium'`; replaces `categories.source`.
  Free-tier accessible iff `'foundation'`.
- `lessons.published_at` — NULL = admin draft (in review queue);
  non-null = user-visible. Replaces "is_published bool" so we can
  measure draft → publish latency.
- `lessons.archived_at` — soft-delete.
- `quiz_items.retired_at` — soft-retire; cascade-set on substantive
  lesson edits (§4) and direct admin retire-and-replace via
  `superseded_by_id` self-ref FK.

The **filter chain** every user-facing read path applies (spec #06
§4.3 row × axis table):

```
Deck.archived_at IS NULL
AND Lesson.archived_at IS NULL
AND Lesson.published_at IS NOT NULL
AND QuizItem.retired_at IS NULL
AND Deck.persona_visibility IN visible_persona_set(user)
AND Deck.tier IN allowed_tiers_for_user(user)
```

Slice 6.5 closed gaps in this chain across the seven user-facing
service-layer reads in `quiz_item_study_service` + `lesson_service`.
Admin-side LIST routes intentionally bypass the chain (admins author
the lifecycle signals — see `admin-panel.md`).

Rejection HTTP-code map per spec #06 §5:

| Reason | Error | HTTP |
|--------|-------|------|
| Deck/lesson archived (lesson_service paths) | `LessonNotFoundError` / `Deck.archived_at IS NULL` filter → empty | 404 |
| Deck/lesson archived (quiz_item paths, post-load) | `QuizItemForbiddenError(reason='archived')` | 403 |
| Quiz_item retired AND no existing progress row | `QuizItemRetiredError` | 409 |
| Persona-mismatch (post-load on quiz_item read) | `QuizItemNotVisibleError` | 404 |
| Premium deck × free user | `QuizItemForbiddenError(reason='premium_deck')` | 403 |

`get_quiz_progress` is a deliberate exception — it aggregates over
`QuizItemProgress` rows without filtering retired/archived rows so
analytics retention surfaces stay queryable (spec #06 §3 + D-9).

## 3. Helper extraction status

Slice 6.5 duplicated three private helpers across `lesson_service.py`
and `quiz_item_study_service.py` per its D-5 (rule-of-three not yet
tripped):

- `_visible_persona_set(user) -> set[str]`
- `_allowed_tiers_for_user(user) -> set[str]`
- `_persona_visible_to(deck_persona, user_persona) -> bool`

**Slice 6.6 trips the rule-of-three.** Spec #07 §12 D-6 locks the
extraction: in the slice 6.6 impl commit, move the three helpers to
`app/services/curriculum_visibility.py` and rewire both existing
services + the new `deck_ranker_service` to import from there.
Additive change, no behavioural delta.

When threading a fourth consumer through, import from
`curriculum_visibility.py` directly. Don't re-duplicate.

## 4. Substantive-edit cascade

Spec #04 §7 + D-17 lock the rule. The classifier lives in
`app/services/lesson_admin_service._is_substantive_change` with
`SUBSTANTIVE_EDIT_THRESHOLD = 0.15` exposed from
`app/services/admin_errors.py`.

A lesson edit is **substantive** iff any of the three Markdown fields
(`concept_md` / `production_md` / `examples_md`) differ by more than
**15% character-delta** from the on-disk row. (The exact distance
metric — `Levenshtein` vs `difflib.SequenceMatcher.ratio()` — is
documented at spec #04 §7.2; pick one and pin it via test.)

On a substantive `update_lesson`:

1. Service runs the cascade in the **same DB transaction** as the
   PATCH — `quiz_items.retired_at` set on every active quiz_item under
   the lesson, `lessons.version += 1`, `lessons.version_type =
   'substantive_edit'`. Synchronous — no RQ enqueue (G2 punted to
   slice 6.10).
2. FSRS state on existing `quiz_item_progress` rows stays untouched
   (slice 6.2 §4.6 D-4 history-preservation).
3. Response shape is `LessonResponse` extended additively with
   `quiz_items_retired_count` + `quiz_items_retired_ids` (spec #04 §6).

The FE mirrors classification client-side via
`src/utils/lessonEdit.ts::classifyEdit(before, after) -> 'minor' |
'substantive'` so the editor can render a confirm-cascade modal
*before* the PATCH. **The BE re-validates and is authoritative** —
admin claim vs §7 rule disagreement raises
`EditClassificationConflictError` → HTTP 409 so the FE re-prompts
with the corrected classification.

Quiz-item-level substantive edits route through
`retire_quiz_item` + replacement-create with `superseded_by_id`
back-link (spec #04 §7.4); they do NOT cascade upward to the
parent lesson.

## 5. Analytics dual-write contract

Phase 6 events dual-write to PostHog (funnels, retention) AND
to dedicated Postgres tables (SQL-queryable content-quality and
retention dashboards). Spec #38 banned HogQL inside `/admin/analytics`
— that's why the Postgres path exists. Per locked decision **I1**:

- `quiz_item_reviewed` (BE-emitted; existing PostHog event from slice
  6.2) → **dual-writes** to `quiz_review_events` table (slice 6.0).
- `quiz_item_progress_initialized` (BE; sister event) → no Postgres
  dual-write today.
- `lesson_viewed` (originally FE-only PostHog) → BE `POST
  /api/v1/lessons/:id/view-event` route + FE `recordLessonView`
  helper writes to `lesson_view_events` table.
- `lesson_section_expanded` (FE-only) — explicitly NOT dual-written.

Both Postgres event tables are **append-only**; no UPDATE / DELETE
except via a future retention slice. FK `ON DELETE SET NULL` on
`user_id` (anonymize the link if account is deleted) and `CASCADE`
on `quiz_item_id` / `lesson_id` / `deck_id` (if the content goes,
analytical value goes too).

Emission discipline lives in `backend.md` §1 (Analytics emission):
post-flush, separate `try/except` around each emission so a `track()`
failure cannot corrupt the user-facing response. The Postgres
dual-write call is the second `try/except` — see canonical site at
`quiz_item_study_service.review_quiz_item:553-575`.

PostHog payloads are unchanged from their pre-Phase-6 shapes; the
Postgres rows mirror those payloads field-for-field. Don't add
new PostHog events when a Phase 6 slice ships read-time hardening
(spec #06 D-8 — slice 6.7 owns paywall telemetry).

## 6. Seed corpus conventions (slice 6.4.5)

Locked decision **H1** picks filesystem markdown + a one-shot loader
over `scripts/seed_phase6_decks.py`. The corpus lives at:

```
hirelens-backend/app/data/decks/seed_lessons/
  <deck_slug>/
    _meta.md              # YAML frontmatter for the deck row
    <lesson_slug>.md      # YAML frontmatter + body H2 sections per lesson
```

Body H2 sections in each lesson file map to the three Markdown columns
(`Concept` → `concept_md`, `Production` → `production_md`, `Examples`
→ `examples_md`). Frontmatter carries the structured fields
(`difficulty`, `version_type`, quiz_items list, etc.).

Loader API: `app.services.seed_lessons_service.load_seed_corpus(db) ->
SeedLoadReport` (idempotent UPSERTs). CLI:
`python -m app.scripts.seed_phase6 [--dry-run] [--seed-root PATH]`.

**Natural keys** for UPSERT (spec #05 §6.1 + D-10):

- `decks` keyed on `slug`
- `lessons` keyed on `(deck_id, slug)`
- `quiz_items` keyed on `(lesson_id, sha256(question)[:16])`

**Idempotency floor**: re-running on a populated DB is a no-op — no
UPDATEs, no version bumps. Editing one lesson's `concept_md` on disk
and re-running causes exactly that lesson to bump version + flip
`version_type` to `'minor_edit'`.

**Admin-action survival** (D-5): rows with `archived_at IS NOT NULL`
or `retired_at IS NOT NULL` are treated as immutable signals — the
loader does NOT resurrect them. This is the read-time mirror of
slice 6.5's filter chain.

Partial-failure tolerance: `seed_lessons_service` wraps each row INSERT
in `db.begin_nested()` (savepoint pattern from `backend.md` §1) so a
single bad row aborts only its savepoint, not the whole load.

## 7. Three-layer quality model (skeleton)

Phase 6 commits to a layered quality pipeline; details get filled in
across slices 6.10 / 6.11 / 6.12 / 6.13 / 6.13.5 (see scout audit
`docs/audits/phase-6-scout.md` §3 for the canonical sketch). Today
the layers are:

1. **Generation** — Gemini-assisted lesson + quiz_item authoring
   (slice 6.10 / 6.11). Writes through admin authoring routes (§4
   classifier still applies).
2. **Critique — layer 2 (active, slice 6.13.5a).** The cross-model
   `CritiqueSchema` payload from slice 6.10 (Anthropic critique stage)
   now persists as `signal_source='critique'` rows on
   `card_quality_signals` (LD J2). One row per
   (`lesson_id`, `dimension`) tuple where `dimension ∈ {'accuracy',
   'clarity', 'completeness', 'cohesion'}` and `score = raw / 5.0`.
   Write-time hook fires from `app/jobs/ingestion_worker.py` Stage 2.5
   (`critique_signal_consumer.persist_critique_signals`) after Stage 3
   persist succeeds, so the consumer always has stable `lesson_id`s.
   The R2 critique.json blob remains the audit trail (slice 6.10
   forever-retention) — `card_quality_signals` is the queryable
   denormalisation. Admin content-quality dashboard exposes the
   per-dimension scores via `LessonQualityRow.critique_scores`.
3. **User signal — layer 3 (active, slice 6.11 + slice 6.13.5a).**
   Two homes: **(a)** Lesson-level Bayesian-smoothed pass_rate writes
   to `lessons.quality_score` from `admin_content_quality_service`
   when `review_count >= 10` (slice 6.11 D-1 / D-4). Below threshold
   the column stays NULL so the ranker (§8) keeps the 0.5 fallback.
   **(b)** Per-quiz_item Bayesian-smoothed pass_rate now writes to
   `card_quality_signals` (`signal_source='user_review'`,
   `dimension='pass_rate'`, `quiz_item_id IS NOT NULL`,
   `recorded_by_user_id IS NULL`) — same threshold + smoothing
   formula, IS DISTINCT FROM-gated for idempotency (slice 6.13.5a /
   §6.5). User-thumbs feedback (the third layer-3 source) lands as
   `signal_source='user_thumbs'` rows in slice 6.13.5b (per-user
   distinct via the 5-tuple UNIQUE; aggregate at read-time).

When `lessons.quality_score IS NULL` the ranker (§8) coerces it to
0.5 (neutral) per spec #07 §12 D-2 so unscored lessons aren't ranked
worst-by-default.

## 8. Ranker contract (slice 6.6)

Spec #07 D-1..D-16 lock the contract. BE-only; FE consumer is slice
6.7. Cliff-notes:

**Inputs** (per spec #07 §4.1):
- `users.persona` + `users.subscription.plan` (delegated visibility filter)
- `tracker_applications_v2.analysis_payload` JSONB → recent skill_gaps
  (`undefer(...)` required per spec #59 §6)
- `quiz_item_progress` joined to `quiz_items → lessons → decks`
- `decks.display_order` (tie-break)
- `lessons.quality_score` (averaged per deck)

**Score formula** (D-1, locked):
```
score(deck) = 0.55 * gap_match_score
            + 0.25 * fsrs_due_score
            + 0.10 * avg_quality_score
            + 0.10 * (1 / display_order_rank)
```

- `gap_match_score` (D-7): case-insensitive substring of each gap's
  `skill` against `deck.slug.replace('-', ' ') + deck.title`,
  weighted by importance (`critical=1.0, recommended=0.5,
  nice-to-have=0.25`), normalised by considered-gap count. **No**
  lesson-title matching in v1 (D-8).
- `fsrs_due_score` (D-3): linear `min(due_count, total_quiz_items) /
  total_quiz_items`; empty-deck floor 0.
- `avg_quality_score` (D-2): mean across published, non-archived
  lessons; null-coerced to 0.5.
- `display_order_rank`: rank within persona+tier-visible set,
  reciprocal pulls curator-favoured decks up as tie-break.

**Output**: `RankedDecksResponse { user_id, persona, cold_start: bool,
lookback_days, recent_gap_count, ranked_at, decks: list[RankedDeck] }`
sorted by `score DESC` then `display_order ASC`. **Decks-only in v1**
(D-5) — `lessons` field is forward-compat shape, always None.

**Route**: `GET /api/v1/learn/ranked-decks` (D-9). Auth required.
Optional `?lookback_days=N&max_scans=M` query params (defaults 30 / 5
per D-14).

**Visibility**: persona-agnostic — applies to all three personas
(D-4). Premium decks **filtered out** for free users at the visibility
helper layer (D-10) — they don't surface in the response, so there's
no upsell-via-rank surface here. (Slice 6.7 FE is where paywall
nudges live.)

**Cold-start** (D-15): when no recent scan has `analysis_payload`
populated, return `cold_start: true`, score by `display_order` only,
no copy hint embedded in the response. Slice 6.7 picks the CTA copy.

**No caching** (D-12) — recomputes on every request. The 12-deck
universe is cheap.

**No analytics events** (D-11) — pure read.

**No migration** (D-13) — `get_recent_skill_gaps` reads
`tracker_applications_v2.analysis_payload` JSONB live. The
materialised `user_skill_gap` table alternative is locked out of v1.

**Partial-failure** (D-16): a single deck whose sub-score query
errors gets skipped + logged at WARNING; the rest of the response
still ships. No 5xx for one bad row.

## 9. What this skill is NOT

- **Slice-specific FE component shapes** — read the slice spec
  (`docs/specs/phase-6/NN-*.md`) for the consuming page layout.
- **Slice-specific Pydantic schema field names** — read the slice
  spec; this skill names the shapes (`RankedDecksResponse`,
  `LessonWithQuizzesResponse`) but not exhaustive field lists.
- **Test file layout** — see `testing.md` for the flat `tests/test_*.py`
  convention; slice specs name the new test files.
- **Phase 5 Lens / Forge / legacy-card schema** — covered by other
  skills (`ats-scanner.md`, `study-engine.md`, `card-extraction.md`,
  `database-schema.md`).
- **FSRS scheduler internals** — see `study-engine.md`. This skill
  only covers where FSRS state attaches in the Phase 6 schema.
- **Admin auth mechanics** — see `admin-panel.md`. The substantive-edit
  cascade lives here because the rule is curriculum-shaped, but the
  audit-log + `require_admin` chain is admin-shaped.

## 10. Cross-references

| Topic | Spec | Skill |
|---|---|---|
| Foundation schema (decks/lessons/quiz_items/progress) | `docs/specs/phase-6/01-foundation-schema.md` | `database-schema.md` |
| FSRS-on-quiz_item service contract | `docs/specs/phase-6/02-fsrs-quiz-item-binding.md` | `study-engine.md` |
| Lesson UX (4-section render) | `docs/specs/phase-6/03-lesson-ux.md` | — |
| Admin authoring CRUD + substantive-edit cascade | `docs/specs/phase-6/04-admin-authoring.md` | `admin-panel.md` |
| Reference seed corpus + loader | `docs/specs/phase-6/05-seed-lessons.md` | — |
| Read-time invariants | `docs/specs/phase-6/06-read-time-invariants.md` | `backend.md` (helper rule-of-three) |
| Lens-ranked deck/lesson ordering | `docs/specs/phase-6/07-deck-lesson-ranker.md` | — |
| Dual-write events tables | `docs/specs/phase-6/00-analytics-tables.md` | `analytics.md` |
| Foundation audit (Phase 6 origin) | `docs/audits/phase-6-scout.md` | — |
