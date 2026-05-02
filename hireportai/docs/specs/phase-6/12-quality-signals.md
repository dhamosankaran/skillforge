# Phase 6 — Slice 6.13.5: Quality Signals (`card_quality_signals` Table + Critique-Score Consumption + Per-Quiz_Item Writeback + User-Thumbs Ingestion)

## Status: 🔴 Drafted — §12 LOCKED DECISIONS empty placeholder; §14 Open Questions carry author hints for the §12 amendment slice; B-094 forward-filed at status 🔴 for the impl slice.

| Field | Value |
|-------|-------|
| **Slice** | 6.13.5 (Track D — quality-signal foundation; LD J2 home; closes the four §13 deferrals from slice 6.11) |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `<spec-author-sha>` (this slice) |
| **BACKLOG row (spec-author)** | **B-093** ✅ (filed + closed in this slice per single-slice spec-author lifecycle; mirrors slice 6.10 / 6.11 / 6.13 spec-author rows) |
| **BACKLOG row (impl, forward-filed)** | **B-094** 🔴 (filed at status 🔴 by this slice for the future implementation slice per R15(c)) |
| **Depends on** | spec #00 (`docs/specs/phase-6/00-analytics-tables.md` — `quiz_review_events` + `lesson_view_events` source tables; shipped `e7a0044`) ▪ spec #01 (`docs/specs/phase-6/01-foundation-schema.md` — `decks` / `lessons` / `quiz_items` FK targets, `lessons.quality_score Numeric(3,2) NULLABLE`; shipped `a989539`) ▪ spec #04 (`docs/specs/phase-6/04-admin-authoring.md` — admin auth chain, `audit_admin_request`; shipped `d6bda3b` BE + `634f633` FE) ▪ spec #10 (`docs/specs/phase-6/10-ai-ingestion-pipeline.md` — `CritiqueSchema` per-dimension layer-2 payload + R2 `critique.json` artifact + `ingestion_jobs.critique_r2_key` column; shipped `8735373`) ▪ spec #11 (`docs/specs/phase-6/11-content-quality-retention.md` — first non-NULL `lessons.quality_score` emitter at `admin_content_quality_service.py`; D-16 breadcrumb at line 19 names this slice as the migration target; shipped `95104d2`) ▪ existing `Depends(require_admin)` + `audit_admin_request` chain (`app/core/deps.py`) ▪ existing `Depends(get_current_user)` for user-side thumbs route ▪ existing `slowapi` rate limiter (`app/core/rate_limit.py`). |
| **Blocks** | Re-evaluation of LD G2 cron decision via B-078 🟦 (per `CODE-REALITY.md:848` — "G2 cron decision is also tracked at B-078 🟦 awaiting re-evaluation when 6.13.5 closes"). Future "user-facing quality badges" surface (no spec yet; not in scope here). |
| **Cross-refs** | scout `docs/audits/phase-6-scout.md` §3 quality-pipeline sketch + Q1 `card_quality_signals` keying question (spec body around `:957` and `:1117`); `curriculum.md` §7 three-layer quality model (this slice activates the layered table); `analytics.md` (catalog discipline + `internal: true` admin-event convention + Postgres event-table conventions); SESSION-STATE Phase 6 LDs **I1** (dual-write Postgres events — this slice introduces the third Postgres event-adjacent table after `quiz_review_events` + `lesson_view_events`), **J2** (`card_quality_signals` keyed `(id, lesson_id, quiz_item_id NULLABLE, signal_source, dimension)` — this slice ships the table). Drift `D-016` (resolved — `response_schema` plumbed at `9bd9397`; consumed by spec #10 critique stage; not load-bearing here but cross-ref'd because critique-payload validation matters). |

> **Slice numbering note (info-only):** the slice number is **6.13.5** (per SESSION-STATE Phase 6 specs block + LD J2). The on-disk filename is `12-quality-signals.md` because slot 12 is the next-free numeric prefix after `11-content-quality-retention.md` (slice 6.11) and before `13-pro-digest-opt-out.md` (slice 6.13). On-disk filename progression and slice-number progression have been decoupled since the Phase-6 re-sequencing — see slice 6.11 §1.1 finding #1 for prior precedent of this same drift. Information-only — no §12 lock needed.

---

## 1. Problem

The Phase-6 curriculum platform now produces and serves content
end-to-end: schema (slice 6.1), FSRS scheduler (slice 6.2),
lesson-card UX (slice 6.3), admin authoring shell + services
(slice 6.4 / 6.4b), reference seed corpus (slice 6.4.5), read-time
invariant chain (slice 6.5), Lens-ranked deck ordering (slice 6.6),
persona-aware Learn page (slice 6.7), user-self FSRS dashboard
(slice 6.8), AI ingestion pipeline (slice 6.10), and content-quality
retention dashboard with the first non-NULL `lessons.quality_score`
emitter (slice 6.11). What does **not** yet exist is a unified
storage shape for the per-(lesson, quiz_item, signal_source,
dimension) quality signals that LD J2 names — and four distinct
quality-signal sources are either unused, stub-only, or inferred
read-time when they could be persisted.

Four concrete gaps motivate this slice:

- **`card_quality_signals` table is greenfield.** LD J2 names the
  table and its key shape `(id, lesson_id, quiz_item_id NULLABLE,
  signal_source, dimension)` but no migration exists, no ORM model
  exists, no service exists. The breadcrumb at
  `app/services/admin_content_quality_service.py:19` (slice 6.11
  D-16 lock) explicitly points the future slice 6.13.5 audit at the
  migration target — "merges with layer-1 critique signal in slice
  6.13.5 via card_quality_signals table per LD J2". On-disk
  references to the table appear only in spec / audit / SESSION-STATE
  prose, not in any `.py` file.

- **Slice 6.10 critique-score per-dimension data is stuck in R2 blob
  form.** Slice 6.10's cross-model critique stage produces a
  `CritiqueSchema` payload — four numeric per-dimension scores
  (`accuracy`, `clarity`, `completeness`, `cohesion`, each `int 1..5`)
  + verdict (`PASS` / `FAIL` / `NEEDS_REVIEW`) — and writes the raw
  JSON to R2 at `s3://<bucket>/ingestion/<job_id>/critique.json`
  (see `app/jobs/ingestion_worker.py:374-405`). The
  `ingestion_jobs.critique_verdict` column persists only the verdict
  string; the four numeric scores never reach a queryable table.
  Spec #10 §3 explicitly defers numeric persistence: "The R2
  critique.json artifact preserves the raw critique payload so slice
  6.11 can backfill scores from history if desired" (spec #10 §3,
  fourth bullet). Slice 6.11 chose user-signal layer only; the
  critique payload remains R2-only and admins cannot SQL-query
  per-dimension critique scores today.

- **Per-quiz_item user-aggregate writeback is deferred from slice
  6.11.** Slice 6.11 §12 D-5 + D-9 lock lesson-level writeback only;
  per-quiz_item rollups appear in the dashboard payload as read-time
  aggregations but never persist. Slice 6.11 §13 explicitly defers
  per-quiz_item writeback to this slice: "Per-quiz_item
  `quality_score` writeback to disk — defer to slice 6.13.5 + LD J2's
  `card_quality_signals` table." Without per-quiz_item persistence,
  the `_avg_quality_score` ranker term cannot be sharpened with
  per-quiz_item granularity (slice 6.6 D-2 keeps lesson-level
  null-coercion as the only signal), and admins cannot trend-track
  individual quiz_item recall over time.

- **User-thumbs feedback has no surface, no model, no route.**
  curriculum.md §7 layer-3 calls out user-thumbs as the second
  layer-3 source (alongside the user-review aggregate that slice 6.11
  ships): "Future user-thumbs feedback is layer-3 too but lands on
  `card_quality_signals` when slice 6.13.5 ships." No FE thumbs UI
  exists today (`grep -r "thumb" hirelens-frontend/src/components/`
  returns zero hits at audit time). No BE thumbs service exists.
  This is the first explicit-feedback channel for content quality
  in the codebase — `quiz_review_events` capture *behavioural*
  signal (did the user pass the quiz_item?), not *judgemental*
  signal (does the user think the lesson is well-written?).

Slice 6.13.5 closes all four gaps by introducing:

1. **A new `card_quality_signals` table** per LD J2 key shape — one
   row per `(lesson_id, quiz_item_id NULLABLE, signal_source,
   dimension)` tuple with a numeric `score` column + provenance
   metadata (`source_ref`, `recorded_at`, `recorded_by_user_id`).
2. **A critique-score consumer** that lifts the four per-dimension
   scores from each `ingestion_jobs.critique_r2_key` blob and
   writes them as `signal_source='critique'` rows on
   `card_quality_signals` (one row per dimension per lesson).
3. **A per-quiz_item user-aggregate writeback** that extends the
   slice 6.11 Bayesian-smoothed pass_rate pattern down to
   per-quiz_item granularity, persisted as
   `signal_source='user_review'` rows.
4. **A user-thumbs ingestion path** — new
   `POST /api/v1/lessons/:id/thumbs` (and per-quiz_item variant)
   route, new `thumbs_service` writing
   `signal_source='user_thumbs'` rows, new FE thumbs UI on
   `pages/Lesson.tsx` and per-quiz_item answer-flow surface.

This slice is the **first user of `card_quality_signals`** — every
downstream consumer (admin content-quality dashboard expansion,
ranker enhancement, future "explain my recommendation" surface)
reads this table. It **subsumes the slice 6.11 lesson-level
writeback** as a special case (lesson-level user-review aggregate
becomes a `signal_source='user_review'` row with `quiz_item_id IS
NULL`) per **§12 D-?? lock pending** — see §14 OQ-A.

The thumbs UI is the **first user-facing quality surface** in the
codebase. Slice 6.11 was admin-only (G-1); this slice introduces a
read+write user touchpoint that affects the layer-3 signal mix.
The opt-in design (no spam, no required-action) keeps the surface
honest — see §8.

### 1.1 Step 0 audit findings

Audit reads at HEAD `<spec-author-head>` (post-slice-6.13 SHA-backfill,
post-D-030 drift log):

1. **`card_quality_signals` table absent on disk** — confirmed by
   `grep -rn "card_quality_signals\|CardQualitySignal"
   hirelens-backend/app/ --include='*.py'` returning zero hits.
   Greenfield as expected per LD J2 ("Built in slice 6.13.5"). No
   ORM model, no migration, no service. Cross-references in
   `docs/specs/phase-6/00-analytics-tables.md:25` + `01-foundation-schema.md:27,78,521,574` +
   `06-read-time-invariants.md:16,28` + `11-content-quality-retention.md` (multiple §3 / §6.1 / §13)
   + `13-pro-digest-opt-out.md:14,104` + audit `phase-6-scout.md:824,957,1101,1117`
   + skill-catalog comment at `app/services/admin_content_quality_service.py:19`
   + comment at `app/schemas/admin_content_quality.py:72` are all
   **forward references** — they describe a table that this slice
   ships. No on-disk schema or migration exists today.

2. **LD J2 key shape on-disk reference is consistent.** SESSION-STATE
   line 69 + spec #01 line 27 + spec #06 line 28 all carry
   `(id, lesson_id, quiz_item_id NULLABLE, signal_source, dimension)`
   verbatim. Scout audit `phase-6-scout.md:957` carries an earlier
   pre-LD-J2-lock variant `(lesson_id, signal_source, dimension)`
   without `id` PK + without `quiz_item_id` — the canonical LD J2
   shape supersedes the scout's earlier sketch. **Use the LD J2
   shape verbatim** in §5.

3. **`lessons.quality_score: Numeric(3,2) NULLABLE` on disk** at
   `app/models/lesson.py:63` (slice 6.1). Slice 6.11 ships the first
   non-NULL writeback at `app/services/admin_content_quality_service.py`
   computing a Bayesian-smoothed pass_rate over the 30-day
   `quiz_review_events` window. **Migration target locked at
   `admin_content_quality_service.py:19`** (D-16 breadcrumb). This
   slice's writeback path **either** (a) keeps `lessons.quality_score`
   as the lesson-level layer-3 home and uses
   `card_quality_signals` only for per-quiz_item granular signals +
   critique signals + user-thumbs signals, **or** (b) migrates the
   lesson-level user-aggregate to a
   `signal_source='user_review', quiz_item_id IS NULL` row on
   `card_quality_signals` and treats `lessons.quality_score` as a
   denormalized read-cache. See **§14 OQ-A** lock.

4. **`quiz_items.quality_score` does NOT exist on disk** at
   `app/models/quiz_item.py:32-93`. No corresponding column, no
   index, no migration. Slice 6.11 §1.1 finding #3 confirmed the
   same. This slice's per-quiz_item writeback path **either** (a)
   adds the column (mirrors `lessons.quality_score` shape; one
   alembic ALTER), **or** (b) writes only to
   `card_quality_signals` with
   `quiz_item_id IS NOT NULL` rows. The LD J2 key shape was
   designed for option (b) — no schema change to `quiz_items`. See
   **§14 OQ-B** lock.

5. **Slice 6.10 critique-score persistence shape on disk:**
   - `CritiqueSchema` defined at `app/schemas/ingestion.py:121`
     with the per-dimension model `_CritiqueDimension(name in
     ['accuracy','clarity','completeness','cohesion'], score: int
     1..5, rationale: str)` and the top-level
     `CritiqueSchema(verdict: PASS|FAIL|NEEDS_REVIEW, dimensions,
     rationale)`.
   - `ingestion_jobs` columns persist only `critique_verdict:
     String(16) NULLABLE` (the verdict string) +
     `critique_r2_key: String(255) NULLABLE` (the R2 key for the
     full payload). The four numeric per-dimension scores live
     **only** in the R2 blob.
   - The R2 key shape is
     `ingestion/<job_id>/critique.json` per
     `app/services/ingestion_service.py:82-83` (`def critique_r2_key`).
   - Critique-score consumption (this slice) reads from R2 (the
     authoritative payload) — see **§14 OQ-C** lock for write-time
     vs read-time approach.

6. **Slice 6.11 admin-content-quality service has the consumer
   surface for critique-derived per-dimension columns.** The
   `LessonQualityRow` schema currently lacks
   per-dimension fields. Adding critique-score persistence here
   without a consumer is wasted work; the natural consumer is an
   extension to `LessonQualityRow` (and possibly a new
   `LessonQualityCritiqueRow` sub-envelope). **Default proposal:
   extend `LessonQualityRow` with optional `critique_scores:
   dict[str, float] | None` field** populated from
   `card_quality_signals` rows where
   `signal_source='critique'`. See **§14 OQ-D** lock.

7. **No on-disk thumbs UI surface** — `grep -rn "thumb"
   hirelens-frontend/src/components/lesson/` returns zero hits;
   `grep -rn "thumb" hirelens-frontend/src/components/` (broader)
   also returns zero. Greenfield FE component this slice. The
   natural mount point for lesson-level thumbs is
   `pages/Lesson.tsx` (footer area, after content); for
   quiz-item-level thumbs the natural mount is the answer-flow
   surface inside `components/study/` (audit at impl Step 1
   determines exact site). See **§14 OQ-G** lock.

8. **B-078 cron decision LD G2 carry-forward.** Per
   `CODE-REALITY.md:848`: "G2 cron decision is also tracked at
   B-078 🟦 awaiting re-evaluation when 6.13.5 closes." This
   slice's recompute cadence (sync-on-read vs cron) directly
   informs the LD G2 re-evaluation. **Default proposal: sync-on-
   read for v1** (mirrors slice 6.11 D-1 sync-on-read writeback;
   no new infra; idempotency makes concurrent admins safe). Cron
   recompute deferred to slice 6.14 / future. See **§14 OQ-F**
   lock + §13.

9. **Layer-numbering vocabulary drift across precedent specs +
   skill catalog (info-only):**
   - `curriculum.md` §7 (canonical skill catalog): **L1=Generation,
     L2=Critique, L3=User signal**.
   - Spec #10 §1.2: "Layer 1 of the curriculum.md §7 three-layer
     quality skeleton lands here [slice 6.10]; layer 2 (critique
     scoring → `card_quality_signals`) is slice 6.11 / 6.13.5."
     → spec #10 calls Generation=L1, Critique=L2, User=L3
     (consistent with curriculum.md).
   - Spec #11 D-16 breadcrumb: "layer-3 user-signal v1; merges with
     layer-1 critique signal in slice 6.13.5..."
     → spec #11 calls User-signal=L3, Critique=L1
     (inconsistent with curriculum.md and spec #10).
   - Spec #11 §1: "Slice 6.10's `CritiqueSchema` payload (per-
     dimension scores) is layer 1; this slice [6.11] is layer 3
     only."
     → spec #11 also calls Critique=L1 (echoes the §13 + D-16
     vocabulary).

   **Resolution chosen this spec:** use **descriptive names**
   throughout — "critique signals" / "user-thumbs signals" /
   "user-review aggregate signals" / "AI-generation signals" — not
   numeric layer labels. Where layer numbers must appear (e.g.
   referencing curriculum.md skill), follow curriculum.md's
   canonical L1/L2/L3 mapping (Generation / Critique / User signal)
   and surface spec #11's drift as info-only without amending spec
   #11 (Q2 surgical change discipline — out-of-scope edits to
   shipped specs). Future curriculum.md skill update may re-lock
   the vocabulary; not this slice's scope.

10. **`audit_admin_request` chain for admin-side reads is mature.**
    Five admin routers in `app/main.py:25-28, 141-151` each use
    `APIRouter(dependencies=[Depends(audit_admin_request)])` +
    per-route `Depends(require_admin)`. Slice 6.11
    `admin_content_quality.py` follows this pattern verbatim;
    slice 6.13.5's admin-side critique-consumer route (if
    introduced — see **§14 OQ-D** lock) follows the same pattern.
    **No new admin auth surface needed.**

11. **`Depends(get_current_user)` chain for user-side writes is
    mature.** Existing user-scoped routes
    (`app/api/v1/routes/lesson_view_events.py`,
    `quiz_items.py`, etc.) gate all user-side writes via
    `Depends(get_current_user)`. The thumbs ingestion route
    follows this pattern verbatim.

12. **Slowapi rate limiter precedent:**
    `app/core/rate_limit.py:12` — global default 100/min;
    per-route override via `@limiter.limit("N/period")`. Thumbs
    submissions are low-volume per-user (one thumbs per
    lesson per user per day at most — see **§14 OQ-E** lock for
    duplicate-prevention semantics). **Default proposal: rely on
    the global 100/min default; no per-route override.** A
    dedicated thumbs-rate-limit-with-Redis-counter is unneeded for
    v1 abuse-bounded by the per-(user, lesson, quiz_item)
    UPSERT semantics under **§14 OQ-E** lock = (b) UPSERT on
    `(user_id, lesson_id, quiz_item_id)` so re-submission
    overwrites rather than appends.

13. **Append-only vs UPSERT for `card_quality_signals`.** Slice
    6.0's `quiz_review_events` + `lesson_view_events` are
    append-only (slice 6.0 §4.4 invariant) — every review is a
    row, no UPSERT. `card_quality_signals` is **NOT** an event
    stream — it's a snapshot of the *current* signal per
    `(lesson_id, quiz_item_id, signal_source, dimension)` tuple.
    The natural shape is an UPSERT-on-tuple semantics where
    re-recording a signal overwrites the prior row. **Default
    proposal: UPSERT on
    `(lesson_id, quiz_item_id NULLS-distinct, signal_source,
    dimension)` UNIQUE constraint** (Postgres `INSERT ... ON
    CONFLICT (...) DO UPDATE SET score=..., recorded_at=...`).
    This means historical drift is NOT preserved — once a critique
    re-runs, the prior critique-score row is overwritten. Audit
    trail lives in R2 critique.json artifacts (slice 6.10
    forever-retention per §12 D-11) and in
    `quiz_review_events` (which IS append-only and feeds the
    user-review aggregate signal). See **§14 OQ-H** lock.

14. **`recorded_by_user_id` provenance column.** For
    `signal_source='user_thumbs'` the recording user is the
    thumbs author (read from `Depends(get_current_user)`). For
    `signal_source='critique'` the recording "user" is the
    ingestion job (no human author — `recorded_by_user_id IS NULL`,
    provenance via `source_ref` pointing at
    `ingestion_jobs.id`). For
    `signal_source='user_review'` (per-quiz_item user-aggregate,
    extending slice 6.11 pattern) the recording user is the admin
    who triggered the dashboard load (mirrors slice 6.11 D-1
    sync-on-read writeback) OR `NULL` if cron-triggered (see **§14
    OQ-F**). **Default proposal: nullable
    `recorded_by_user_id` with `ON DELETE SET NULL` — preserves
    aggregate signal value when the recording user deletes their
    account.** Mirrors slice 6.0 §4.3 user_id semantics on
    `quiz_review_events`.

### 1.2 Why this matters

- **Closes four §13 deferrals from slice 6.11.** Per slice 6.11 §13
  bullets 1-4: per-quiz_item disk writeback, layer-1 critique
  consumption, `card_quality_signals` table, user-thumbs ingestion.
  All four are this slice. The audit-time cost of leaving them open
  is rising — every new spec has a forward-reference to slice
  6.13.5, every admin-side feature has to grep for a table that
  doesn't exist, and the `_avg_quality_score` ranker term stays
  lesson-level only.
- **Activates LD J2.** The `card_quality_signals` table has been
  named in three places in the locked-decisions block (LD J2 line)
  + four specs (`#00`, `#01`, `#06`, `#11`) + the audit + a
  service docstring breadcrumb — but never built. Activation
  delivers the table that 4+ downstream surfaces reference.
- **Activates a third layer-3 signal source.** Today's only
  layer-3 signal is the user-review aggregate (slice 6.11
  Bayesian-smoothed pass_rate). User-thumbs adds a *judgemental*
  signal orthogonal to the *behavioural* signal — admins gain a
  second channel for "is this lesson confusing?" beyond "did the
  user pass the quiz?".
- **Persists critique-derived per-dimension data.** Slice 6.10's
  cross-model critique already runs on every ingestion; the per-
  dimension scores are computed and discarded into R2 today.
  Persisting them in a queryable form means slice 6.11's admin
  dashboard can surface "this lesson was rated 3/5 on accuracy by
  the cross-model critique" without per-request R2 reads.
- **Forward-compatible with cron recompute (LD G2 / B-078).** v1
  ships sync-on-read writeback (mirrors slice 6.11 D-1); the
  `card_quality_signals` UPSERT semantics are idempotent so a
  future cron consumer (slice 6.14 or downstream) can re-fire
  without drift. Closing this slice triggers the LD G2 re-
  evaluation per `CODE-REALITY.md:848`.

---

## 2. Goals

| # | Goal |
|---|------|
| **G-1** | **Build `card_quality_signals` per LD J2.** New ORM model `app/models/card_quality_signal.py` + new alembic migration adding the table with PK `id` + FK `lesson_id` + nullable FK `quiz_item_id` + `signal_source: String(20) NOT NULL` + `dimension: String(30) NOT NULL` + `score: Numeric(4,2) NOT NULL` (range depends on dimension; see §5.1) + provenance columns (`source_ref`, `recorded_by_user_id`, `recorded_at`) + UNIQUE constraint on `(lesson_id, quiz_item_id, signal_source, dimension)` (Postgres NULLS-distinct semantics — see §5.1) + indexes for hot-path reads. |
| **G-2** | **Critique-score consumer.** New service `app/services/critique_signal_consumer.py` (or worker hook in `app/jobs/ingestion_worker.py`; see **§14 OQ-C**) that lifts `_CritiqueDimension` rows from each successful ingestion's `critique.json` R2 blob and writes one `signal_source='critique'` row per dimension per lesson via UPSERT on the LD J2 key. |
| **G-3** | **Per-quiz_item user-aggregate writeback.** Extend the slice 6.11 `aggregate_dashboard` flow (or a new sibling service; see **§14 OQ-D**) so that per-quiz_item Bayesian-smoothed pass_rates ≥ MIN_REVIEW_THRESHOLD persist as `signal_source='user_review', quiz_item_id IS NOT NULL, dimension='pass_rate'` rows on `card_quality_signals`. Mirror slice 6.11 D-2 formula + D-4 threshold + D-13 rating semantics + D-14 IS DISTINCT FROM idempotency gate. |
| **G-4** | **User-thumbs ingestion.** New BE route `POST /api/v1/lessons/:lesson_id/thumbs` + (optional, per **§14 OQ-G**) `POST /api/v1/quiz-items/:quiz_item_id/thumbs` writing `signal_source='user_thumbs'` rows with `dimension='helpful'` and `score ∈ {-1.0, +1.0}` (thumbs-down / thumbs-up). UPSERT-on-(user, target) so re-submission overwrites. New FE component `<ThumbsControl />` mounted on `pages/Lesson.tsx` (lesson-level) + per-quiz_item answer-flow surface (per **§14 OQ-G** scope). |
| **G-5** | **Read-only over user-review data.** Zero writes to `quiz_review_events`, `lesson_view_events`, or any user-owned table. Writes are scoped to `card_quality_signals` (G-1, G-2, G-3, G-4) + `lessons.quality_score` denormalized cache update (per **§14 OQ-A** lock if path (b) chosen). |
| **G-6** | **Reuses existing auth chains.** Admin-side reads via `Depends(require_admin)` + `audit_admin_request`; user-side thumbs writes via `Depends(get_current_user)`. Mirrors slice 6.11 G-6. No new auth primitive. |
| **G-7** | **Synchronous on-read writeback (v1).** Mirror slice 6.11 D-1 — critique-consumer + per-quiz_item user-aggregate writeback fire synchronously as side-effects of the slice 6.11 admin dashboard GET (or, per **§14 OQ-C** option, write-time during ingestion-worker for critique-only). User-thumbs writes are direct (synchronous on the user's POST). No background job in v1. Cron deferred to LD G2 / B-078 / slice 6.14. |
| **G-8** | **Idempotent UPSERT semantics.** UNIQUE constraint on `(lesson_id, quiz_item_id, signal_source, dimension)` (NULLS-distinct) + Postgres `INSERT ... ON CONFLICT DO UPDATE SET score=EXCLUDED.score, recorded_at=NOW()`. Re-running any consumer with unchanged inputs produces the same end-state. Mirrors slice 6.11 finding #14 IS DISTINCT FROM idempotency floor. |

---

## 3. Non-goals (out-of-scope this slice)

- **User-facing critique-score badges.** No "this lesson was rated
  4/5 on clarity by the cross-model AI critic" badge anywhere user-
  visible. Per-dimension critique scores surface in the admin
  dashboard only (G-2 → slice 6.11 dashboard extension). User
  surfaces stay on FSRS-progression + completion signals.

- **User-facing aggregate-quality badges.** No "this lesson is rated
  4.8/5 by N users" badge user-visible. Same rationale as slice 6.11
  §3 first bullet — quality drives ranker scores transparently;
  direct user-visibility is a distinct future spec.

- **Free-text user feedback.** Thumbs is a binary -1 / +1 signal.
  Optional comment / "tell us why" textarea is **out of scope** —
  free-text feedback is a moderation surface (PII, spam, abuse) and
  is its own design. Future slice may add it; this slice's UI is
  one click, no textarea.

- **Cron-driven recompute.** v1 fires sync-on-read (slice 6.11 D-1
  precedent). Background recompute = LD G2 / B-078 re-evaluation
  (deferred to slice 6.14 / future). Per `CODE-REALITY.md:848` the
  re-evaluation triggers when this slice closes.

- **Cross-lesson semantic similarity scoring.** No LLM-driven
  embedding-similarity signal (e.g., "this lesson is 95% similar to
  lesson X"). The four signal sources locked here (critique,
  user-review-aggregate, user-thumbs, AI-generation) are exhaustive
  for v1; semantic-similarity is a separate Track-D future surface.

- **Multi-source thumbs aggregation in the same row.** Each user's
  thumbs is one row keyed on `(lesson_id, quiz_item_id, user_id)`
  via `recorded_by_user_id` distinguishing rows OR a sibling
  `card_quality_thumbs` table (per **§14 OQ-E** lock). Aggregate
  thumbs-score = average of `score` across rows for the same
  (lesson_id, quiz_item_id, signal_source='user_thumbs',
  dimension='helpful') tuple is a *read-time* computation, not a
  pre-aggregated row.

- **Historical drift / time-series of signals.** UPSERT semantics
  (G-8) overwrite. The R2 critique.json artifacts (slice 6.10
  forever-retention per §12 D-11) are the audit trail for critique
  drift; `quiz_review_events` (append-only, slice 6.0) is the audit
  trail for user-review-aggregate drift. No new
  `card_quality_signals_history` table.

- **Backfill of historical critique payloads.** Existing
  `ingestion_jobs` rows (those that completed before this slice
  ships) can be backfilled by an ops-grade CLI script
  (`python -m app.scripts.backfill_critique_signals`) — but the
  script is **out of scope** as a deliverable here. v1 ships the
  consumer hook; backfill = follow-up sub-slice if needed (likely
  cheap enough to skip — corpus is small).

- **`quiz_review_events` migration to `card_quality_signals`.**
  Slice 6.0 stores raw user-review events; this slice stores
  *signals derived from* events. The two tables have different
  invariants (append-only vs UPSERT) and different read paths
  (per-event audit vs per-(lesson, dimension) snapshot). No
  migration; both stay.

- **Real-time / SSE updates.** Admin dashboard refreshes on page
  load (slice 6.11 D-12 precedent). Thumbs UI optimistically
  updates client-side; server confirms via the POST response.

- **Anonymous (logged-out) thumbs.** Thumbs requires
  `Depends(get_current_user)` — no logged-out submission. **§14
  OQ-J** locks this; default = auth-gated.

- **Persona-gating on thumbs eligibility.** Whether free-tier
  users can submit thumbs vs Pro-only is a product decision — see
  **§14 OQ-I** lock; default proposal = all authed users (no
  paywall on feedback submission).

- **Per-deck rollups in the table.** `card_quality_signals` keys
  on `(lesson_id, quiz_item_id, signal_source, dimension)`; deck-
  level rollups are read-time aggregations (mirrors slice 6.11
  `DeckQualityRow` precedent). No `deck_id` denormalization on the
  table — slice 6.11 admin dashboard joins `lessons.deck_id` for
  the rollup.

- **Free-tier paywall on thumbs submission.** No `check_and_increment`
  call, no usage-quota counter, no `402` path on thumbs POST.
  Thumbs is feedback infrastructure, not a billable feature.

- **Generation-signal source rows.** curriculum.md §7 calls
  Generation = L1, but this slice does NOT introduce a
  `signal_source='generation'` row shape. Slice 6.10 has no
  numeric per-dimension generation signal today (the LLM produces
  content, not a score); the only AI-derived score is critique
  (slice 6.10 stage 2). If a future generation-time signal lands
  (e.g., per-quiz_item difficulty estimate from the generator
  prompt), it adds a new `signal_source='generation'` enum value
  + new dimensions in a follow-up slice — `signal_source` is
  String, not enum, to allow this.

---

## 4. Architecture

### 4.1 Component graph (new + modified files)

```
hirelens-backend/
  app/
    models/
      card_quality_signal.py          ← NEW (~80-120 lines, ORM model)
    schemas/
      card_quality_signal.py          ← NEW (~80-120 lines, Pydantic write + read schemas)
    services/
      card_quality_signal_service.py  ← NEW (~150-200 lines, UPSERT helper + per-source readers)
      critique_signal_consumer.py     ← NEW (~80-130 lines; per §14 OQ-C may be folded into worker)
      thumbs_service.py               ← NEW (~80-130 lines, user-thumbs ingestion + read)
      admin_content_quality_service.py ← MODIFIED (extend to write per-quiz_item + read critique signals; ~50-80 lines added)
    api/v1/routes/
      thumbs.py                       ← NEW (~60-100 lines, POST /lessons/:id/thumbs + optional quiz_item variant)
    jobs/
      ingestion_worker.py             ← MODIFIED (per §14 OQ-C if write-time; ~10-20 lines added)
    schemas/
      admin_content_quality.py        ← MODIFIED (extend LessonQualityRow + QuizItemQualityRow with critique_scores field)
    main.py                           ← MODIFIED (mount thumbs router under /api/v1)
    alembic/versions/
      <hash>_phase6_card_quality_signals.py ← NEW (one migration; one table + indexes + UNIQUE constraint)

hirelens-frontend/
  src/
    components/
      lesson/
        ThumbsControl.tsx             ← NEW (~80-120 lines, lesson-level thumbs UI)
      study/
        QuizItemThumbsControl.tsx     ← NEW (~80-120 lines; per §14 OQ-G if quiz_item-level included)
    hooks/
      useThumbs.ts                    ← NEW (~50-80 lines, useMutation wrapper)
    pages/
      Lesson.tsx                      ← MODIFIED (mount <ThumbsControl /> in footer)
      admin/
        AdminContentQuality.tsx       ← MODIFIED (render critique_scores column in WorstLessonsTable)
    services/
      api.ts                          ← MODIFIED (+1 helper: submitThumbs)
    types/
      index.ts                        ← MODIFIED (+2 types: ThumbsRequest, ThumbsResponse)
```

Two adjacent edits to existing services:
- `admin_content_quality_service.py` — extends per slice 6.11 D-16
  breadcrumb; the per-quiz_item writeback path is the natural
  extension point (per §14 OQ-D may live in a sibling service).
- `ingestion_worker.py` — possibly extended per **§14 OQ-C** if
  critique-consumer is write-time; otherwise unchanged.

### 4.2 Data flows

#### 4.2.1 Critique-score consumer (write-time variant — §14 OQ-C path A)

```
ingestion_worker.run_ingestion_job(job_id)
  ├─ STAGE 2: critique (existing — generates CritiqueSchema)
  ├─ STAGE 2.5: NEW — critique_signal_consumer.persist_signals(
  │     lesson_ids=job.generated_lesson_ids,
  │     critique=critique,
  │     job_id=job.id,
  │     db=session,
  │  )
  │     ├─ for each lesson_id × dimension in critique.dimensions:
  │     │     UPSERT card_quality_signals
  │     │       ON CONFLICT (lesson_id, quiz_item_id, signal_source, dimension)
  │     │       DO UPDATE SET score=EXCLUDED.score, recorded_at=NOW()
  │     │     with quiz_item_id=NULL, signal_source='critique', score=dimension.score / 5.0
  │     └─ commit (session-scoped; matches existing worker pattern)
  ├─ STAGE 3: persist drafts (existing)
  └─ emit ingestion_job_completed (existing)
```

#### 4.2.2 Critique-score consumer (read-time variant — §14 OQ-C path B)

```
admin opens /admin/content-quality
  ├─ admin_content_quality_service.aggregate_dashboard (existing)
  │   └─ NEW substep: for each lesson with non-NULL critique_r2_key,
  │      lazily read R2 blob + UPSERT card_quality_signals signals
  │      (cached check: skip if signals already present + recorded_at >
  │      ingestion_jobs.completed_at)
  └─ render dashboard (existing + new critique_scores column)
```

Default proposal: **Path A (write-time)** — happens once at
ingestion completion, no per-dashboard-load R2 reads. Cleaner
separation; admin dashboard doesn't depend on R2 availability for
critique signals. See **§14 OQ-C** lock.

#### 4.2.3 Per-quiz_item user-aggregate writeback (extends slice 6.11)

```
admin opens /admin/content-quality (existing GET)
  ├─ admin_content_quality_service.aggregate_dashboard (existing)
  │   ├─ EXISTING: lesson-level pass_rate writeback to lessons.quality_score
  │   └─ NEW: per-quiz_item pass_rate writeback to card_quality_signals
  │       ├─ for each quiz_item with review_count_window >= MIN_REVIEW_THRESHOLD:
  │       │     compute Bayesian-smoothed pass_rate (slice 6.11 D-2 formula)
  │       │     UPSERT card_quality_signals
  │       │       ON CONFLICT (lesson_id, quiz_item_id, signal_source, dimension)
  │       │       DO UPDATE SET score=EXCLUDED.score, recorded_at=NOW()
  │       │     with signal_source='user_review', dimension='pass_rate'
  │       └─ writebacks_applied += N (existing counter extends)
  └─ render dashboard (existing)
```

This extends slice 6.11 D-1 sync-on-read writeback to per-
quiz_item granularity. Slice 6.11 chose lesson-level only because
`quiz_items.quality_score` did not exist; this slice writes to
`card_quality_signals` which exists post-migration.

#### 4.2.4 User-thumbs ingestion

```
user clicks 👍 / 👎 on /learn/lesson/:id
  ├─ <ThumbsControl onClick={(score) => useThumbs.mutate({lesson_id, score})} />
  ├─ useThumbs.mutate → POST /api/v1/lessons/:lesson_id/thumbs {score: +1|-1}
  ├─ require_current_user
  ├─ thumbs_service.submit_thumbs(lesson_id, score, user, db)
  │   ├─ verify lesson exists + visible to user (persona/tier per slice 6.5 invariants)
  │   ├─ UPSERT card_quality_signals
  │   │     ON CONFLICT (lesson_id, quiz_item_id, signal_source, dimension)
  │   │     DO UPDATE SET score=EXCLUDED.score, recorded_at=NOW()
  │   │     with quiz_item_id=NULL (lesson-level), signal_source='user_thumbs',
  │   │          dimension='helpful', recorded_by_user_id=user.id
  │   └─ emit posthog event: lesson_thumbs_submitted {lesson_id, score, persona, plan}
  └─ HTTP 200 ThumbsResponse {accepted: true, score}
```

Per **§14 OQ-E** lock: UPSERT-on-(user, lesson) so re-clicking
overwrites. The UNIQUE constraint on `card_quality_signals` does
NOT include `recorded_by_user_id` — see **§14 OQ-E** for whether
per-user thumbs are stored as separate rows (one row per user)
or a single aggregated row. **Default proposal: separate rows
keyed on `(lesson_id, quiz_item_id, signal_source, dimension,
recorded_by_user_id)` UNIQUE + read-time AVG aggregation.**

### 4.3 Failure modes + recovery

- **Critique consumer R2 read fails** (Path B only) — log WARNING,
  return prior persisted signals if any, skip update. Idempotent
  retry on next dashboard load.
- **Critique consumer mid-write fails** (Path A or B) — partial
  rows persist; UPSERT semantics make a re-run a no-op for already-
  written rows. Mirrors slice 6.11 D-1 partial-failure-skip
  pattern.
- **User-thumbs POST fails (DB write error)** — return 503 with
  structured error; FE optimistic update reverts. No retry
  client-side (single click; user can retry manually).
- **User submits thumbs on archived/retired lesson** — 404 (mirror
  slice 6.5 read-time invariants). Thumbs not accepted on hidden
  content.
- **Concurrent thumbs from same user (double-click)** — UPSERT
  semantics make the second submission a no-op (same score) or an
  overwrite (different score). No duplicate-row risk via the
  UNIQUE constraint.
- **`card_quality_signals` table grows unbounded** — at 24 lessons
  × 4 critique dimensions + 24 lessons × N user thumbs + ~72
  quiz_items × 1 user-review aggregate = bounded by content
  + user volume. v1 corpus stays under ~1000 rows even at 100% user
  participation. Pagination / TTL not needed v1 (mirrors slice 6.6
  D-12 ranker bounded-corpus rationale).
- **R2 critique.json blob missing for old ingestion** (Path B
  only) — if `ingestion_jobs.critique_r2_key` is non-NULL but
  R2 fetch returns 404, log ERROR + skip + record
  `critique_signals.persistence_failed_at` (column not added v1;
  log-only). Forever-retention per spec #10 §12 D-11 means this
  shouldn't happen unless R2 is misconfigured.

### 4.4 Cross-cutting composition rules

- **R3 auth:** every new route gets `Depends(...)` chain — admin
  routes use `require_admin` + `audit_admin_request`; user-thumbs
  uses `get_current_user`. Zero unauth surfaces.
- **R5 Pydantic:** all I/O via Pydantic schemas (§5).
- **R6 Alembic:** one new migration (§7).
- **R8 PostHog:** one new FE event (`lesson_thumbs_submitted`) +
  one BE event (per **§14 OQ-K**) — see §9.
- **R11 LLM router:** zero new LLM calls; critique-consumer reads
  pre-existing `CritiqueSchema` payloads from R2 / DB. Not load-
  bearing.
- **R12 design tokens:** every FE color / spacing / shadow uses
  tokens. The `<ThumbsControl />` component uses
  `text-text-primary` for the icon, `bg-bg-surface` for the
  container, `bg-accent-primary` for active state. No hardcoded
  hex.
- **R13 integration tests:** one alembic-roundtrip integration
  test (`@pytest.mark.integration`-gated per the migration; same
  pattern as slice 6.0 + slice 6.13).
- **R14 spec-first:** this spec is authored before impl.
- **R15(c) closure:** B-093 spec-author closes in this slice;
  B-094 forward-files at status 🔴 for the impl slice.
- **R16 audit at impl Step 1:** the impl slice's Step 1 audit
  must cover (a) BE consumer-graph for the new `CardQualitySignal`
  ORM + new `card_quality_signal_service` (predicted consumers:
  `thumbs_service`, `critique_signal_consumer`,
  `admin_content_quality_service` extension; **no live external
  consumer beyond admin dashboard**); (b) FE consumer-graph for
  the new shared `ThumbsRequest` / `ThumbsResponse` types
  (predicted consumers: `useThumbs`, `<ThumbsControl />`,
  `<QuizItemThumbsControl />` if per **§14 OQ-G**; **no external
  consumer**); (c) navigation-graph audit if any new route is
  added — none planned (thumbs is an in-page action, not a route).
- **R17 watermark:** B-093 claimed by this slice for spec-author;
  B-094 claimed for forward-filed impl row; B-095 next-free
  numeric ID post-slice. Watermark grep at impl pickup time
  per R17 (concurrent sessions can shift the watermark).

---

## 5. Schemas

### 5.1 `card_quality_signals` table (LD J2 lock)

New file `app/models/card_quality_signal.py`. Mirrors the LD J2
key shape verbatim:

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | `String(36)` | NOT NULL | (server-generated UUID) | PK; UUIDPrimaryKeyMixin pattern (slice 6.13 precedent at `email_log`). |
| `lesson_id` | `String(36)` | NOT NULL | — | FK `lessons.id` `ON DELETE CASCADE`. Mirrors `quiz_review_events.lesson_id` semantics — if lesson is hard-deleted, the signal loses meaning. |
| `quiz_item_id` | `String(36)` | NULLABLE | — | FK `quiz_items.id` `ON DELETE CASCADE`. NULL = lesson-level signal; non-NULL = per-quiz_item signal. |
| `signal_source` | `String(20)` | NOT NULL | — | One of `'critique'` / `'user_review'` / `'user_thumbs'` (extensible — String, not enum, per §3 last bullet). |
| `dimension` | `String(30)` | NOT NULL | — | Per-source dimension vocab: critique → `'accuracy'\|'clarity'\|'completeness'\|'cohesion'`; user_review → `'pass_rate'` (extensible to `'lapse_rate'`); user_thumbs → `'helpful'` (extensible). |
| `score` | `Numeric(4, 2)` | NOT NULL | — | Range depends on dimension: critique scores normalized to [0.00, 1.00] from raw 1-5 input (`raw / 5.0`); user_review scores in [0.00, 1.00] (smoothed pass_rate); user_thumbs scores in {-1.00, +1.00}. **Numeric(4,2)** chosen over Numeric(3,2) so user_thumbs `-1.00` fits (Numeric(3,2) max abs value < 10 — `-1.00` works at Numeric(3,2) but Numeric(4,2) leaves headroom for future dimensions like a 0..10 quality grade). |
| `source_ref` | `String(36)` | NULLABLE | — | Provenance pointer. For `signal_source='critique'`, contains `ingestion_jobs.id`; for `'user_thumbs'` and `'user_review'`, NULL (provenance lives in `recorded_by_user_id`). No FK constraint (loose pointer; ingestion job may be deleted before signal is). |
| `recorded_by_user_id` | `String(36)` | NULLABLE | — | FK `users.id` `ON DELETE SET NULL`. Anonymizes if user deletes account. NULL for `'critique'` (no human author) or for `'user_review'` if cron-triggered (per **§14 OQ-F**); non-NULL for `'user_thumbs'`. |
| `recorded_at` | `DateTime(timezone=True)` | NOT NULL | `func.now()` | Server-set; updates on UPSERT. |

**Indexes:**

| Name | Columns | Use |
|------|---------|-----|
| `ux_card_quality_signals_key` | UNIQUE `(lesson_id, quiz_item_id, signal_source, dimension, recorded_by_user_id)` (NULLS-distinct) | UPSERT target; per-user thumbs rows distinct via `recorded_by_user_id`. **Distinct from LD J2 4-tuple** — see §14 OQ-E. |
| `ix_card_quality_signals_lesson_source` | `(lesson_id, signal_source, recorded_at DESC)` | Per-lesson per-source rollup (slice 6.11 dashboard extension). |
| `ix_card_quality_signals_quiz_item_source` | `(quiz_item_id, signal_source, recorded_at DESC)` WHERE `quiz_item_id IS NOT NULL` | Per-quiz_item per-source rollup. Partial index since most rows are lesson-level. |
| `ix_card_quality_signals_user` | `(recorded_by_user_id, signal_source, recorded_at DESC)` WHERE `recorded_by_user_id IS NOT NULL` | "Has this user thumbed this lesson?" lookup for FE pre-fill. Partial index since critique/user_review rows have NULL. |

**FK `ON DELETE` semantics** (mirrors slice 6.0 §4.3):

| Column | Behavior | Reasoning |
|--------|----------|-----------|
| `lesson_id` | `CASCADE` | Lesson hard-delete → signal loses anchor. Soft-archive (slice 6.4) does NOT cascade since `archived_at` is application-level only. |
| `quiz_item_id` | `CASCADE` | Same. |
| `recorded_by_user_id` | `SET NULL` | Anonymize on user account deletion; preserve aggregate signal value (mirrors `quiz_review_events.user_id`). |

### 5.2 Pydantic schemas — `app/schemas/card_quality_signal.py`

Three schemas: write input, write output, and a lightweight read
schema for admin-side rollups.

```python
class CardQualitySignalWrite(BaseModel):
    """Internal write schema — used by services, NOT directly accepted at HTTP boundary."""
    lesson_id: str
    quiz_item_id: Optional[str] = None
    signal_source: Literal['critique', 'user_review', 'user_thumbs']
    dimension: str  # validated per-source at service boundary
    score: float = Field(..., ge=-1.0, le=1.0)  # normalized
    source_ref: Optional[str] = None
    recorded_by_user_id: Optional[str] = None


class CardQualitySignalRow(BaseModel):
    """Read row — admin dashboard sub-section + service-side aggregations."""
    id: str
    lesson_id: str
    quiz_item_id: Optional[str] = None
    signal_source: Literal['critique', 'user_review', 'user_thumbs']
    dimension: str
    score: float
    source_ref: Optional[str] = None
    recorded_by_user_id: Optional[str] = None
    recorded_at: datetime


class ThumbsRequest(BaseModel):
    """User-side thumbs route input.

    Lesson-level: POST /api/v1/lessons/:lesson_id/thumbs
    Quiz-item-level: POST /api/v1/quiz-items/:quiz_item_id/thumbs (per §14 OQ-G)
    """
    score: Literal[-1, 1]  # int at HTTP boundary; service normalizes to -1.0 / 1.0


class ThumbsResponse(BaseModel):
    accepted: bool
    score: int  # -1, 0 (cleared), or 1
    aggregate_score: Optional[float] = None  # current mean across all users (read-time)
    aggregate_count: int = 0
```

### 5.3 `LessonQualityRow` extension (slice 6.11 schema modification)

Extends `app/schemas/admin_content_quality.py::LessonQualityRow`
with two additive optional fields:

```python
class LessonQualityRow(BaseModel):
    # ... existing fields from slice 6.11 ...
    critique_scores: Optional[dict[str, float]] = None
    """Per-dimension critique scores (slice 6.13.5) — keys in
    {'accuracy', 'clarity', 'completeness', 'cohesion'} when populated;
    None if no critique-source row exists for this lesson.
    """
    thumbs_aggregate: Optional[float] = None
    """Mean of user-thumbs scores for this lesson, [-1.0, 1.0]; None if no thumbs."""
    thumbs_count: int = 0
```

`QuizItemQualityRow` extension (additive `pass_rate_persisted:
Optional[float] = None` + `thumbs_aggregate` + `thumbs_count`)
mirrors the same shape.

### 5.4 FE TypeScript types — `src/types/index.ts`

```typescript
export interface ThumbsRequest {
  score: -1 | 1;
}

export interface ThumbsResponse {
  accepted: boolean;
  score: -1 | 0 | 1;
  aggregate_score: number | null;
  aggregate_count: number;
}

// Extends existing LessonQualityRow + QuizItemQualityRow with
// critique_scores / thumbs_aggregate / thumbs_count optional fields.
```

---

## 6. Backend

### 6.1 New service — `app/services/card_quality_signal_service.py`

Public API (UPSERT helper + per-source readers):

```python
async def upsert_signal(
    payload: CardQualitySignalWrite,
    db: AsyncSession,
) -> None:
    """Idempotent UPSERT into card_quality_signals.

    Uses Postgres INSERT ... ON CONFLICT (lesson_id, quiz_item_id,
    signal_source, dimension, recorded_by_user_id) DO UPDATE SET
    score=EXCLUDED.score, recorded_at=NOW().

    Caller owns transaction (calls db.flush, not db.commit). Mirrors
    slice 6.0 analytics_event_service write-only pattern.
    """


async def get_signals_for_lesson(
    lesson_id: str,
    db: AsyncSession,
    *,
    signal_source: Optional[str] = None,
) -> list[CardQualitySignalRow]:
    """Read all signals for a lesson (or filtered by signal_source).

    Used by admin_content_quality_service for the dashboard extension.
    """


async def get_thumbs_aggregate(
    lesson_id: str,
    db: AsyncSession,
    *,
    quiz_item_id: Optional[str] = None,
) -> tuple[Optional[float], int]:
    """Mean user-thumbs score + count for (lesson_id, quiz_item_id).

    Returns (None, 0) if no thumbs rows present. Used by ThumbsResponse
    aggregate_score + aggregate_count fields.
    """
```

### 6.2 New service — `app/services/critique_signal_consumer.py`

Per **§14 OQ-C** lock = path A (write-time, default proposal):

```python
async def persist_critique_signals(
    lesson_ids: list[str],
    critique: CritiqueSchema,
    job_id: str,
    db: AsyncSession,
) -> int:
    """Lift CritiqueSchema dimensions into card_quality_signals rows.

    Called from ingestion_worker post-Stage-2 (after critique completes
    successfully). Writes one row per (lesson_id, dimension) tuple
    with signal_source='critique', source_ref=job_id,
    recorded_by_user_id=NULL.

    Returns number of rows UPSERTed. Idempotent — re-running with
    same inputs is a no-op.
    """
```

### 6.3 New service — `app/services/thumbs_service.py`

```python
async def submit_thumbs(
    *,
    lesson_id: str,
    quiz_item_id: Optional[str] = None,
    score: Literal[-1, 1],
    user: User,
    db: AsyncSession,
) -> ThumbsResponse:
    """User-thumbs submission.

    1. Verify lesson + quiz_item visible to user (raises 404 on
       persona/tier-mismatch via existing slice 6.5 invariants).
    2. UPSERT card_quality_signals via card_quality_signal_service.
    3. Read aggregate via card_quality_signal_service.get_thumbs_aggregate.
    4. Emit posthog event lesson_thumbs_submitted (or
       quiz_item_thumbs_submitted per §14 OQ-G).
    5. Return ThumbsResponse.
    """


async def clear_thumbs(...):
    """Optional: future surface for retracting a thumbs (per §14 OQ-K).

    DELETE the prior row; emit cleared event. Not in v1 per §14 OQ-K
    default = no clear surface (UPSERT to zero-score is the v1 way to
    clear via the same POST endpoint).
    """
```

### 6.4 New routes — `app/api/v1/routes/thumbs.py`

```python
router = APIRouter(prefix="/api/v1", tags=["thumbs"])


@router.post("/lessons/{lesson_id}/thumbs", response_model=ThumbsResponse)
async def submit_lesson_thumbs(
    lesson_id: str,
    payload: ThumbsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThumbsResponse:
    return await thumbs_service.submit_thumbs(
        lesson_id=lesson_id,
        quiz_item_id=None,
        score=payload.score,
        user=user,
        db=db,
    )


# Optional per §14 OQ-G:
@router.post("/quiz-items/{quiz_item_id}/thumbs", response_model=ThumbsResponse)
async def submit_quiz_item_thumbs(
    quiz_item_id: str,
    payload: ThumbsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThumbsResponse:
    # service derives lesson_id from quiz_item_id
    ...
```

### 6.5 Modified service — `admin_content_quality_service.py`

Two adjacent extensions to the existing `aggregate_dashboard`:

1. **Per-quiz_item user-aggregate writeback** (G-3): inside the
   existing per-quiz_item rollup loop, for any quiz_item with
   `review_count_window >= MIN_REVIEW_THRESHOLD`, UPSERT
   `card_quality_signals` with `signal_source='user_review',
   dimension='pass_rate', score=smoothed_pass_rate`. Increments
   the existing `writebacks_applied` counter.

2. **Critique-score read-side join** (G-2 consumer surface):
   after the existing query loop, for each lesson in the response
   payload, fetch `signal_source='critique'` rows + aggregate per-
   dimension. Surface as
   `LessonQualityRow.critique_scores: dict[str, float]`. Same for
   `QuizItemQualityRow.thumbs_aggregate +
   QuizItemQualityRow.thumbs_count`.

3. **Lesson-level thumbs-aggregate read-side**: per-lesson
   `thumbs_aggregate` + `thumbs_count` populated via
   `card_quality_signal_service.get_thumbs_aggregate`.

The slice 6.11 D-1 sync-on-read writeback contract extends to
`card_quality_signals` writes. Idempotency via UPSERT
(`ON CONFLICT ... DO UPDATE SET`) mirrors slice 6.11 finding #14
IS DISTINCT FROM gate.

### 6.6 Modified worker — `app/jobs/ingestion_worker.py`

Per **§14 OQ-C** path A: after Stage 2 critique succeeds + before
Stage 3 persist, call
`critique_signal_consumer.persist_critique_signals(lesson_ids,
critique, job_id, session)`.

Stage labeling extends from `'pending → running → generating →
critiquing → publishing → completed | failed'` to insert a
`'persisting_critique'` step between `critiquing` and `publishing`
(per **§14 OQ-C** sub-question — alternatively the persist step
runs inside `critiquing` and no new status label is needed).

### 6.7 Reuse of existing services

- **`Depends(require_admin)`** — admin reads (slice 6.11
  dashboard extension).
- **`Depends(get_current_user)`** — user thumbs writes.
- **`audit_admin_request`** — admin route audit log.
- **`slowapi` rate limiter** — global default 100/min covers v1.
- **`analytics_track`** — PostHog event emission (slice 6.0
  precedent).
- **Slice 6.11 `admin_content_quality_service.aggregate_dashboard`**
  — extension target (G-3 + read-side critique surface).
- **Slice 6.10 `CritiqueSchema` Pydantic model** — input to
  `critique_signal_consumer`.
- **Slice 6.10 `object_storage_service.get_text`** — Path B only;
  read R2 critique.json. Path A doesn't need R2 reads (consumer
  fires write-time with critique payload in memory).
- **Slice 6.5 visibility helpers** (`_persona_visible_to`,
  `_resolve_plan`) — verify user can submit thumbs on the target
  lesson/quiz_item.

### 6.8 Performance envelope

| Stage | Target | Notes |
|---|---|---|
| `submit_thumbs` POST | <200ms | one UPSERT + one aggregate SELECT + one PostHog emit |
| `persist_critique_signals` write-time | <100ms | 4 UPSERTs (one per dimension) per lesson; bounded by lesson count per ingestion |
| Slice 6.11 dashboard extension (per-quiz_item writeback + critique read) | +50-150ms over current ~500ms | adds N quiz_item UPSERTs (bounded by visible quiz_item universe) + 1 SELECT per lesson for critique signals |
| `get_thumbs_aggregate` | <50ms | one indexed SELECT |

---

## 7. Migrations

One alembic migration: `<hash>_phase6_card_quality_signals.py`.

CREATE `card_quality_signals` table per §5.1. Indexes: 4 (1 UNIQUE
+ 2 partial + 1 full). FK constraints per §5.1 ON DELETE rules.

`down_revision`: confirm at impl time per slice 6.10 / 6.13
precedent — likely `f1a2b3c4d5e6` (slice 6.13's email_log
migration) which is the current head as of spec authoring time, but
concurrent slices may shift this; impl Step 0 must verify.

No data backfill (table starts empty). R6 compliance via either
handwritten or autogen migration. AC: `alembic upgrade head →
downgrade -1 → upgrade head` clean (one integration-marked test
asserts this; mirrors slice 6.0 + slice 6.13 precedent).

---

## 8. Frontend

### 8.1 New component — `src/components/lesson/ThumbsControl.tsx`

Mounts in `pages/Lesson.tsx` footer area, after the lesson body
+ before any quiz panel. Two icon buttons (👍 / 👎); one is active
at a time based on the user's prior submission. Click toggles —
clicking the same icon a second time clears (resubmits with score=0
which the service treats as DELETE per **§14 OQ-K** — or v1 ships
without a clear path and the button is sticky).

```typescript
interface ThumbsControlProps {
  lessonId: string;
  initialScore?: -1 | 0 | 1;
  initialAggregate?: number | null;
  initialCount?: number;
}
```

R12 compliance: uses `text-text-primary` for inactive icon,
`text-accent-primary` for active state, `text-text-secondary` for
the aggregate count text. No hardcoded hex.

### 8.2 New component (per §14 OQ-G) — `src/components/study/QuizItemThumbsControl.tsx`

If **§14 OQ-G** locks per-quiz_item thumbs IN scope, this component
mounts in the answer-flow surface inside `components/study/`.
Shape mirrors `<ThumbsControl />` but keys on `quizItemId` and
calls `POST /api/v1/quiz-items/:id/thumbs`.

### 8.3 New hook — `src/hooks/useThumbs.ts`

```typescript
export function useThumbs(opts: { lessonId: string; quizItemId?: string }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: ThumbsRequest) => submitThumbs(opts, req),
    onSuccess: (response) => {
      // invalidate the parent query for the lesson detail / aggregate
    },
  });
}
```

### 8.4 Modified pages

- `pages/Lesson.tsx` — mount `<ThumbsControl />` in footer; wire
  `lessonId` from existing route param. Initial score / aggregate
  fetched via the existing lesson detail route (which returns the
  user's prior thumbs row in the response body — see **§14 OQ-L**
  for whether to extend the lesson detail response or add a
  separate read endpoint).
- `pages/admin/AdminContentQuality.tsx` — render
  `critique_scores` per dimension as a small inline column on
  `<WorstLessonsTable />`; render `thumbs_aggregate +
  thumbs_count` as a separate column. Extends slice 6.11 surface.

### 8.5 Modified files

- `src/services/api.ts` — `+1` helper:
  `submitThumbs(lessonId, payload)` (per **§14 OQ-G** + a sibling
  `submitQuizItemThumbs` if scope includes quiz-item thumbs).
- `src/types/index.ts` — `+2` types: `ThumbsRequest`,
  `ThumbsResponse` (matches §5.4).

### 8.6 Existing files explicitly NOT touched

- `pages/Dashboard.tsx` (slice 6.8 user-self) — no thumbs surface
  here; thumbs is per-lesson.
- `pages/AdminAnalytics.tsx` (Phase 5 spec #38) — orthogonal
  surface; no cross-link.
- `App.tsx` — no new route; thumbs are in-page POSTs, not routes.

---

## 9. Analytics

### 9.1 New events

| Event | Source | Properties |
|-------|--------|-----------|
| `lesson_thumbs_submitted` | `components/lesson/ThumbsControl.tsx` (FE) — fires on click via `useMutation.onSuccess` | `{lesson_id, score: -1\|+1, persona, plan, was_clearing: bool}` |
| `quiz_item_thumbs_submitted` (per §14 OQ-G) | `components/study/QuizItemThumbsControl.tsx` (FE) | `{quiz_item_id, lesson_id, score, persona, plan, was_clearing}` |
| `lesson_critique_signal_persisted` (per §14 OQ-K — info-only, BE) | `app/services/critique_signal_consumer.py` (BE) — fires once per ingestion job | `{job_id, lesson_id, dimension_count, internal: true}` |

`internal: true` discriminator on the BE event keeps it out of
user-facing PostHog dashboards (slice 6.10 D-13 / slice 6.11 D-11
convention).

### 9.2 Existing events touched

None. `quiz_item_reviewed` / `lesson_viewed` shapes unchanged.

### 9.3 Catalog discipline

`.agent/skills/analytics.md` — append two new rows in the FE
catalog (`lesson_thumbs_submitted` + per-§14-OQ-G
`quiz_item_thumbs_submitted`) and one in the BE catalog
(`lesson_critique_signal_persisted` if **§14 OQ-K** locks it ON).
Lock-step update in the impl commit per slice 6.10 / 6.11
precedent.

---

## 10. Test plan

Test envelope locked at impl. Estimates below.

### 10.1 BE unit — `tests/services/`

- `test_card_quality_signal_service.py` (~6-10 tests): UPSERT
  happy-path / UPSERT idempotency / per-source filter readers /
  thumbs aggregate computation / NULL-distinct UNIQUE on
  `quiz_item_id`.
- `test_critique_signal_consumer.py` (~4-6 tests): persist 4
  dimensions for one lesson / persist for multi-lesson ingestion
  job / re-run no-op / partial-failure-skip per §4.3.
- `test_thumbs_service.py` (~6-8 tests): submit lesson-level
  thumbs / submit quiz-item-level thumbs (per §14 OQ-G) / re-submit
  same direction (UPSERT no-op) / re-submit reverse (UPSERT
  overwrite) / 404 on archived lesson / aggregate computation
  cross-user.
- `test_admin_content_quality_service_phase2.py` (~4-6 tests):
  per-quiz_item user-aggregate writeback / critique read-side
  surfacing / thumbs aggregate join.

### 10.2 BE route — `tests/api/`

- `test_thumbs_routes.py` (~5-7 tests): unauthed POST → 401 /
  authed POST → 200 + ThumbsResponse / score validation (only
  -1 / +1 accepted) / 404 on non-existent lesson / 404 on archived
  lesson / persona-mismatch handled.

### 10.3 BE migration — `tests/test_phase6_card_quality_signals_migration.py`

- one integration-marked alembic round-trip test (mirrors slice
  6.0 + slice 6.13).
- one test asserting UNIQUE + NULL-distinct semantics work as
  expected (insert two rows differing only in NULL `quiz_item_id`
  → second succeeds).

### 10.4 FE — `tests/components/lesson/`

- `ThumbsControl.test.tsx` (~5-8 tests): initial render /
  click-to-submit / re-click-to-clear / aggregate display /
  loading state / error state / a11y label correctness.
- `QuizItemThumbsControl.test.tsx` (per §14 OQ-G) (~4-6 tests).

### 10.5 FE — `tests/hooks/useThumbs.test.ts` (~3-4 tests)

mutation success / mutation error / cache invalidation.

### 10.6 FE — `tests/pages/admin/AdminContentQuality.test.tsx` (extension)

- `+2-3 tests`: critique_scores column renders / thumbs_aggregate
  column renders / null-handling for both.

### 10.7 Test envelope (estimates, locked at impl)

- BE: **766 → ~788..808** (+22..+42 across new service + route +
  migration + slice-6.11-extension).
- FE: **451 → ~462..475** (+11..+24 across new components + hook
  + admin page extension).
- Integration: **+1** (alembic round-trip; CI deselected via
  R13).

---

## 11. Acceptance criteria

- **AC-1** Migration `<hash>_phase6_card_quality_signals.py`
  applies cleanly (`alembic upgrade head`); table + indexes +
  UNIQUE constraint exist on Postgres.
- **AC-2** `alembic upgrade head → downgrade -1 → upgrade head`
  round-trip is clean (integration-marked test).
- **AC-3** UPSERT semantics: re-submitting a thumbs with the same
  score is a no-op (`recorded_at` updates but row identity stable);
  re-submitting with a different score overwrites.
- **AC-4** UNIQUE constraint NULL-distinct: two rows differing
  only in `quiz_item_id IS NULL` vs `quiz_item_id='abc'` both
  insert.
- **AC-5** `POST /api/v1/lessons/:id/thumbs` unauthed → 401.
- **AC-6** `POST /api/v1/lessons/:id/thumbs` authed user on
  archived lesson → 404.
- **AC-7** `POST /api/v1/lessons/:id/thumbs` authed user on
  visible lesson → 200 + `ThumbsResponse {accepted: true, score:
  ±1, aggregate_score, aggregate_count}`.
- **AC-8** `score` validator rejects values outside {-1, +1} →
  422.
- **AC-9** Critique-consumer persists 4 rows per dimension for a
  single-lesson ingestion job (locked at the four
  `_CritiqueDimension.name` enum values per spec #10 §5.5).
- **AC-10** Critique-consumer is idempotent: running twice on
  the same `(job_id, lesson_id)` produces the same end-state row
  count.
- **AC-11** Per-quiz_item user-aggregate writeback fires on slice
  6.11 admin dashboard load when `review_count_window >=
  MIN_REVIEW_THRESHOLD` (slice 6.11 D-4 = 10).
- **AC-12** Per-quiz_item user-aggregate writeback skips below
  threshold (no row written).
- **AC-13** Slice 6.11 admin dashboard `LessonQualityRow.critique_scores`
  populated when critique signals exist for the lesson; `None`
  otherwise.
- **AC-14** Slice 6.11 admin dashboard `LessonQualityRow.thumbs_aggregate
  + thumbs_count` populated; `None` / `0` for empty case.
- **AC-15** `<ThumbsControl />` renders correct initial state from
  `initialScore` prop.
- **AC-16** `<ThumbsControl />` click submits via `useThumbs`
  mutation; on success, optimistically updates local state to
  match server response.
- **AC-17** `<ThumbsControl />` design tokens only (R12 grep:
  zero hardcoded `#hex` colors in component file).
- **AC-18** PostHog `lesson_thumbs_submitted` event fires once
  per click with correct payload shape per §9.1.
- **AC-19** FK `ON DELETE CASCADE` on `lesson_id` verified by
  test (insert signal → delete lesson → signal row deleted).
- **AC-20** FK `ON DELETE SET NULL` on `recorded_by_user_id`
  verified by test (insert thumbs → delete user → row remains
  with `recorded_by_user_id=NULL`).

---

## 12. Decisions

> **LOCKED DECISIONS — empty placeholder.**
>
> Per the slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11
> §12 amendment-slice precedent, this section is left empty in the
> spec-author commit. A follow-up §12 amendment slice will
> resolve §14 OQ-A..OQ-N (with author-hint dispositions per
> Dhamo) and lock D-1..D-N here.
>
> Cross-ref the amendment commits at:
> - Slice 6.0 amendment `e8eecdd` (D-1..D-10)
> - Slice 6.4.5 amendment `df58eaf` (D-1..D-10)
> - Slice 6.5 amendment `acba7ed` (D-1..D-9)
> - Slice 6.6 amendment `fb92396`
> - Slice 6.7 amendment `0c21223`
> - Slice 6.8 amendment `ab07168`
> - Slice 6.10 amendment `be7d59a` (D-1..D-16)
> - Slice 6.11 amendment `d9bfcfc` (D-1..D-16)
> - Slice 6.13 amendment (pending — separate from this slice)
>
> The §12 amendment slice for slice 6.13.5 will follow the same
> Mode 2 (impl-to-spec) shape: read §14 OQ-A..OQ-N, lock D-1..D-N
> from author-hint dispositions, rewrite §14 to RESOLVED form
> (heading + first-sentence question preserved, option bodies
> + author hints removed), update §1 status line + §15 forward-
> link, and bump test counts (no test surface change — pure
> spec amendment).
>
> Until the amendment slice ships, B-094 stays at status 🔴 and
> impl is blocked on amendment closure.

---

## 13. Out of scope (deferred to other slices)

- **User-facing critique badges / aggregate quality badges** —
  no spec yet; future work if a product decision warrants it.
- **Free-text user feedback** — separate moderation surface;
  this slice ships binary thumbs only.
- **Cron-driven recompute** — LD G2 / B-078 re-evaluation triggers
  when this slice closes (per `CODE-REALITY.md:848`); cron consumer
  if any lives at slice 6.14 / future.
- **Cross-lesson semantic similarity scoring** — not a
  `card_quality_signals` row source; separate Track-D future
  surface.
- **`signal_source='generation'` rows** — slice 6.10 has no
  numeric per-dimension generation signal today; if a future
  generation-time signal lands, it adds a new enum value.
- **Backfill CLI for historical critique payloads** — out of
  scope this slice; thin script if needed.
- **`card_quality_signals_history` audit-trail table** — UPSERT
  semantics overwrite; R2 critique.json + `quiz_review_events`
  are the audit trail. No history table.
- **Real-time / SSE updates of admin dashboard** — slice 6.11
  D-12 precedent; page reload triggers recompute.
- **Anonymous (logged-out) thumbs** — auth-gated per **§14
  OQ-J** default = no.
- **Persona / tier paywall on thumbs submission** — per **§14
  OQ-I** default = all authed users; no paywall on feedback.
- **Per-deck rollups stored in the table** — read-time
  aggregation only (mirrors slice 6.11).
- **Thumbs-clearing endpoint** — UPSERT to score=0 (per **§14
  OQ-K**) is the v1 way to clear; no separate DELETE route.

---

## 14. Open questions

> All OQs below carry author hints (per slice 6.10 / 6.11
> author-hint precedent). The §12 amendment slice will lock
> D-1..D-N from these dispositions.

- **OQ-A — `card_quality_signals`: one table or per-source
  split?** (resolves G-1)

  Option (a): one table with `signal_source` column (current
  default in §5.1 — matches LD J2 lock verbatim).
  Option (b): three tables (`critique_signals`, `user_review_signals`,
  `user_thumbs_signals`) with shared schema fragments. Each
  source has its own UPSERT semantics + index strategy.

  **Author hint: (a).** LD J2 explicitly names ONE table with
  `signal_source` column. Splitting into three would require an
  amendment to LD J2 (chat-Claude scope, not impl-slice scope).
  One table also matches the user-facing "show me all signals
  for this lesson" admin query better — `WHERE lesson_id = X`
  hits one table, not three. Storage / index cost is bounded by
  v1 corpus size.

- **OQ-B — Per-quiz_item writeback target: `quiz_items.quality_score`
  column or `card_quality_signals` row only?** (resolves G-3)

  Option (a): add `quiz_items.quality_score: Numeric(3,2) NULLABLE`
  column mirroring `lessons.quality_score` shape. Slice 6.11 §13
  bullet 1 explicitly defers this column-add to "slice 6.13.5 +
  LD J2's `card_quality_signals` table". Option (b) below was
  the slice 6.11 D-5 lock direction.
  Option (b): `card_quality_signals` row only with
  `quiz_item_id IS NOT NULL, signal_source='user_review',
  dimension='pass_rate'`.

  **Author hint: (b).** LD J2's whole point is per-quiz_item
  granularity in the unified table. Adding the column duplicates
  state across two tables (column + row). The ranker (slice 6.6)
  doesn't read per-quiz_item scores today (`_avg_quality_score`
  is a lesson-level field); when it does, it can read from
  `card_quality_signals` directly. Skipping the column also
  saves one alembic migration.

- **OQ-C — Critique-score consumption: write-time during
  ingestion or read-time via aggregator service?** (resolves G-2)

  Option (a): write-time. `ingestion_worker.run_ingestion_job`
  calls `critique_signal_consumer.persist_critique_signals`
  after Stage 2 critique succeeds, before Stage 3 persist.
  Adds a `'persisting_critique'` status step.
  Option (b): read-time. Slice 6.11 admin dashboard service
  reads R2 critique.json blobs lazily on dashboard load and
  UPSERTs `card_quality_signals` rows. Cached check skips
  re-read if signals already present + `recorded_at >
  ingestion_jobs.completed_at`.

  **Author hint: (a).** Write-time decouples admin dashboard
  from R2 availability. One write per ingestion (already the
  natural batch unit). Cleaner code-locality — the ingestion
  worker owns critique creation; persisting it is a one-line
  service call. Read-time would require R2 reads on every
  dashboard load (or sophisticated caching), and the cache key
  is fragile (R2 blob mutation possible if we ever reprocess).

- **OQ-D — Lesson-level user-aggregate: keep
  `lessons.quality_score` denormalized cache or move to
  `card_quality_signals`?** (resolves G-3 + closes slice 6.11
  D-5 / D-9 superseding question)

  Option (a): keep `lessons.quality_score` as the canonical
  lesson-level home (slice 6.11's writeback path stays
  unchanged); use `card_quality_signals` only for per-quiz_item
  + critique + user-thumbs.
  Option (b): move lesson-level user-aggregate to
  `card_quality_signals` row with `quiz_item_id IS NULL,
  signal_source='user_review', dimension='pass_rate'`. Treat
  `lessons.quality_score` as a denormalized read-cache
  populated post-write for ranker consumption (slice 6.6
  reads `lessons.quality_score` directly).

  **Author hint: (a) for v1.** Slice 6.11 ships `lessons.quality_score`
  as the lesson-level layer-3 home + ranker reads it directly.
  Migrating that to a `card_quality_signals` row + read-cache
  re-population pattern is more refactor than feature for v1.
  The pattern is reversible — option (b) can land as a
  follow-up slice if cron consumer (LD G2) needs the unified
  shape. Keeping (a) means the slice 6.11 service code stays
  unchanged for the lesson-level path; only the per-quiz_item
  extension touches new code.

- **OQ-E — User-thumbs row identity: per-(user, target) or
  aggregated single row?** (resolves G-4)

  Option (a): per-user rows. UNIQUE on
  `(lesson_id, quiz_item_id, signal_source, dimension,
  recorded_by_user_id)` (NULLS-distinct). Each user's thumbs is
  a row; aggregate is a read-time AVG / SUM.
  Option (b): aggregated single row per (lesson_id,
  quiz_item_id, signal_source='user_thumbs', dimension='helpful').
  Score = running average; count column tracks N. Re-submission
  recomputes the average.

  **Author hint: (a).** Per-user rows preserve audit trail
  (admin can see who thumbed what), prevent gaming (a single
  user can't replay thumbs to inflate aggregate), and let us
  later add per-user features (e.g., "what lessons has this
  user marked helpful?"). Storage cost is bounded by user
  count × lesson count; v1 corpus stays under 100K rows even
  with high engagement. Option (b) would complicate the UNIQUE
  constraint design (LD J2 4-tuple key conflicts with per-user
  storage) and lose audit trail.

- **OQ-F — Recompute cadence: sync-on-read only or also cron?**
  (cross-refs LD G2 / B-078 re-evaluation)

  Option (a): sync-on-read only (slice 6.11 D-1 precedent).
  Critique-consumer is write-time (per OQ-C); per-quiz_item
  user-aggregate fires on admin dashboard load.
  Option (b): add cron consumer that recomputes signals
  nightly. Rejected reason: LD G2 cron decision is not yet
  re-evaluated; this slice triggers the re-evaluation per
  `CODE-REALITY.md:848`. Spec author hint should not pre-empt
  product decision.

  **Author hint: (a) for v1.** No cron. Closing this slice
  triggers LD G2 re-evaluation at B-078 — chat-Claude /
  Dhamo decide cron architecture there. v1 ships forward-
  compatible: `card_quality_signals` UPSERT semantics are
  idempotent so a future cron can reuse the same writers.

- **OQ-G — Per-quiz_item thumbs UI: in scope or lesson-level
  only?** (resolves G-4 scope)

  Option (a): lesson-level only v1. `<ThumbsControl />` mounts
  on `pages/Lesson.tsx` only; no per-quiz_item surface.
  Option (b): both lesson-level + per-quiz_item.
  `<QuizItemThumbsControl />` mounts in the answer-flow
  surface inside `components/study/`.

  **Author hint: (a) for v1.** Lesson-level is enough to
  validate the thumbs surface + the admin signal mix. Per-
  quiz_item adds a second mount-point + UX design surface
  (where exactly does the thumbs go in the answer flow?
  during, after, on review?) without proportionate signal
  value. The schema supports per-quiz_item via nullable
  `quiz_item_id`; the FE component is a sibling slice if
  needed.

- **OQ-H — UPSERT semantics: row-level overwrite or version
  history?** (resolves G-8)

  Option (a): UPSERT-on-tuple. `INSERT ... ON CONFLICT DO
  UPDATE SET score=EXCLUDED.score, recorded_at=NOW()`. Prior
  values overwritten; no history.
  Option (b): append + view-on-latest. Insert every signal as
  a new row; reads MAX(recorded_at) per tuple.

  **Author hint: (a).** UPSERT matches the snapshot semantics
  of `card_quality_signals` (current signal per tuple, not
  event stream). Append-mode bloats storage (every dashboard
  load adds rows) and shifts complexity to read paths. R2
  critique.json + `quiz_review_events` are the audit trails
  for the underlying inputs; the signals table is a derived
  snapshot.

- **OQ-I — Persona/tier gating on thumbs submission: free vs
  Pro vs all?**

  Option (a): all authed users (no paywall).
  Option (b): Pro-only (mirrors slice 6.13 daily-digest opt-out).
  Option (c): free-tier rate-limited.

  **Author hint: (a).** Thumbs is feedback infrastructure, not
  billable feature. Restricting to Pro inverts the product
  signal — we want maximum feedback volume, including from
  free-tier users (the cohort most likely to identify
  confusing content). Slowapi 100/min global default covers
  abuse cases.

- **OQ-J — Anonymous (logged-out) thumbs?**

  Option (a): no — `Depends(get_current_user)` required.
  Option (b): yes — accept anonymous via session cookie or
  IP hash.

  **Author hint: (a).** `recorded_by_user_id` is required for
  per-user UPSERT semantics (OQ-E option (a)) and audit
  trail. Anonymous thumbs would require a separate cookie/IP
  identity scheme + abuse mitigation. Not v1 scope.

- **OQ-K — Thumbs-clearing UX: separate DELETE route or
  POST-with-zero?**

  Option (a): no clear surface in v1 — thumbs is sticky after
  first submission; user can change direction (👍 → 👎) but
  not unsubmit.
  Option (b): POST with `score=0` clears the row (DELETE
  semantics in service layer).
  Option (c): separate DELETE route.

  **Author hint: (a) for v1.** Sticky thumbs is the simplest
  UX + matches user mental model ("I rated this lesson"). If
  users complain about wanting to unsubmit, ship (b) as a
  follow-up. (c) is over-engineered.

- **OQ-L — Initial-state read for `<ThumbsControl />`: extend
  lesson detail response or new endpoint?**

  Option (a): extend `GET /api/v1/lessons/:id` response with
  `viewer_thumbs: ThumbsResponse | null` field that the FE
  reads on mount.
  Option (b): separate `GET /api/v1/lessons/:id/thumbs` endpoint
  the FE calls in parallel with the lesson detail GET.

  **Author hint: (a).** One fetch is cleaner than waterfall;
  matches slice 6.11 D-6 single-envelope precedent. Adds one
  field to existing response (additive, non-breaking).

- **OQ-M — `recorded_at` semantics on UPSERT: keep insertion
  time or update on every UPSERT?**

  Option (a): update on every UPSERT (default in §5.1
  `DO UPDATE SET ..., recorded_at=NOW()`). Reflects "most
  recent recording".
  Option (b): preserve original insert time; add separate
  `updated_at` column.

  **Author hint: (a).** One column captures "when did this
  signal last change". Adding `updated_at` doubles the
  timestamp cost without proportionate value. R2 / events
  tables track historical drift.

- **OQ-N — Migration `down_revision` choice — which slice's
  migration are we chaining onto?**

  Option (a): `f1a2b3c4d5e6` (slice 6.13 `email_log` migration —
  current head as of spec authoring time).
  Option (b): later head if concurrent slices ship between
  spec-author and impl pickup.

  **Author hint: (b) — verify at impl time.** Slice 6.10 +
  slice 6.13 precedent: `down_revision` is verified at impl
  Step 0 by `alembic heads` + concurrent-session check (SOP-8).
  Locking a specific revision in the spec body would hard-code
  drift if a concurrent slice ships first.

---

## 15. Implementation slice forward-link

Implementation row: **B-094** 🔴 (filed by this slice; closure
happens in the impl commit per R15(c)).

Forward dependencies before impl can start:

1. **§12 amendment slice** — locks D-1..D-N from §14 OQ-A..OQ-N
   per author-hint dispositions; mirrors slice 6.0 / 6.4.5 / 6.5 /
   6.6 / 6.7 / 6.8 / 6.10 / 6.11 §12 amendment pattern.
2. No BE primitive prerequisite — every existing data source is
   on disk:
   - `lessons` + `quiz_items` + `decks` (slice 6.1, `a989539`).
   - `quiz_review_events` + `lesson_view_events` (slice 6.0,
     `e7a0044`).
   - `lessons.quality_score Numeric(3,2) NULLABLE` (slice 6.1,
     `a989539`).
   - `ingestion_jobs.critique_r2_key` (slice 6.10, `8735373`).
   - `CritiqueSchema` Pydantic model (slice 6.10,
     `app/schemas/ingestion.py:121`).
   - `object_storage_service` (slice 6.10).
   - `Depends(require_admin)` + `audit_admin_request`
     (pre-Phase-6).
   - `Depends(get_current_user)` (pre-Phase-6).
   - `slowapi` rate-limiter (`app/core/rate_limit.py`).

Impl slice expected scope (from §4.1 component graph + §6
backend + §7 migrations + §8 frontend):

- New file `app/models/card_quality_signal.py` (~80-120 lines).
- New file `app/schemas/card_quality_signal.py` (~80-120 lines).
- New file `app/services/card_quality_signal_service.py` (~150-200
  lines).
- New file `app/services/critique_signal_consumer.py` (~80-130
  lines).
- New file `app/services/thumbs_service.py` (~80-130 lines).
- New file `app/api/v1/routes/thumbs.py` (~60-100 lines).
- Modify `app/jobs/ingestion_worker.py` (per §14 OQ-C lock; ~10-20
  lines if path A).
- Modify `app/services/admin_content_quality_service.py` (extend
  per §6.5; ~50-80 lines).
- Modify `app/schemas/admin_content_quality.py` (extend
  `LessonQualityRow` + `QuizItemQualityRow` per §5.3; ~5-10 lines).
- Modify `app/main.py` (mount thumbs router; ~3-5 lines).
- New alembic migration `<hash>_phase6_card_quality_signals.py`.
- New file `src/components/lesson/ThumbsControl.tsx` (~80-120
  lines).
- New file `src/components/study/QuizItemThumbsControl.tsx`
  (per §14 OQ-G; ~80-120 lines if in scope).
- New file `src/hooks/useThumbs.ts` (~50-80 lines).
- Modify `src/pages/Lesson.tsx` (mount `<ThumbsControl />`; ~5-10
  lines).
- Modify `src/pages/admin/AdminContentQuality.tsx` (render
  critique_scores + thumbs columns; ~20-40 lines).
- Modify `src/services/api.ts` (`+1` helper, `+1` per OQ-G).
- Modify `src/types/index.ts` (`+2` types per §5.4).
- 5-7 new BE/FE test files per §10 (~25-45 unit tests + 1
  integration).
- `.agent/skills/analytics.md` updates: 2-3 new event rows per
  §9.
- `.agent/skills/curriculum.md` — §7 layer-3 update flipping
  user-thumbs from "future" to "active"; §7 layer-2 update
  flipping critique-storage from "future" to "active". Possibly
  also a §8 ranker update if per-quiz_item signals start feeding
  ranker (deferred).
- BACKLOG B-094 closure with impl SHA (R15(c)).
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new model + schemas
  + services + route + components + hook + types + admin page
  extension).

Impl test envelope (estimates, locked at impl):
- BE: **766 → ~788..808** (+22..+42).
- BE integration: **+1**.
- FE: **451 → ~462..475** (+11..+24).

R16 consumer-graph audit at impl Step 1:
- New shared BE types (`CardQualitySignalWrite` /
  `CardQualitySignalRow` / `ThumbsRequest` / `ThumbsResponse`)
  — predicted consumers leaf-surface (service + route + tests +
  admin dashboard extension); no external consumer.
- New shared FE types (`ThumbsRequest` / `ThumbsResponse`) —
  predicted consumers `useThumbs`, `<ThumbsControl />`,
  `<QuizItemThumbsControl />` (per §14 OQ-G), admin dashboard
  card row extension; no external consumer.
- Navigation graph: NO new routes mounted; thumbs is in-page
  POST. `App.tsx` untouched.

R11 + LLM-strategy compliance: zero new LLM calls this slice.
Critique-consumer reads pre-existing payloads from R2 / DB. Not
load-bearing.

R12 design-tokens compliance: new components use tokens only;
pre-impl audit grep for hardcoded hex in
`src/components/lesson/ThumbsControl.tsx` +
`src/components/study/QuizItemThumbsControl.tsx` (per OQ-G) +
admin dashboard extension diff.

R13 integration tests: one alembic-roundtrip test gated by
`@pytest.mark.integration` per slice 6.0 + slice 6.13 precedent;
CI deselected.

R14 default — implements an authored spec (this slice IS the
authoring slice; impl pickup is the normal one).

R15(c) closure plan:
- This slice (spec-author): B-093 🔴 → ✅ in this commit; B-094
  🔴 forward-filed.
- §12 amendment slice (separate): no closure (B-094 stays 🔴).
- Impl slice: B-094 🔴 → ✅ at impl-merge.

R17 watermark: B-093 spec-author + B-094 forward-filed impl
claimed by this slice; B-095 next-free numeric ID post-slice.
Watermark grep at amendment + impl pickup time per R17.

Out-of-scope at impl (cross-ref §13): user-facing badges, free-
text feedback, cron recompute (LD G2 / B-078 re-evaluation),
cross-lesson similarity, generation-source rows, history table,
SSE updates, anonymous thumbs, paywall on submission,
deck-rollup persistence.

Skill-author work potentially surfaced post-impl (NOT this
slice's scope): possibly a NEW skill `quality-signals.md`
covering the unified table + signal vocabulary (cross-ref to
curriculum.md §7) — flag at impl Step 1 audit if existing
`curriculum.md` §7 + `analytics.md` cannot absorb the surface
cleanly. SOP-4 close-loop applies (auto-file 🟦 BACKLOG row at
flag #2 per CLAUDE.md SOP-4 sharpening).

LD G2 cron decision (B-078 🟦) re-evaluation triggers when this
slice's impl ships per `CODE-REALITY.md:848`. Chat-Claude /
Dhamo own the re-evaluation; not this slice's scope.

---

*Spec authored at `<spec-author-sha>` against HEAD `<spec-author-head>`.
All on-disk citations verified at audit time per SOP-5; phantom
citations zero. Forward-filed B-094 at status 🔴 per R15(c).
§12 LOCKED DECISIONS empty placeholder; §14 OQ-A..OQ-N carry
author hints; §12 amendment slice locks D-1..D-N before impl
pickup.*
