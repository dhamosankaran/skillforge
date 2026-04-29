# Phase 6 — Slice 6.10: AI Ingestion Pipeline (Gemini Gen + Cross-Model Critique)

## Status: Drafted, not shipped — §12 EMPTY at spec-author; locks via amendment slice mirroring slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 precedent (`e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` / `0c21223` / `ab07168`)

| Field | Value |
|-------|-------|
| **Slice** | 6.10 (Track D opener — first AI-content-generation slice) |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `<this-slice>` (spec-author HEAD pin) |
| **BACKLOG row** | **B-083** 🔴 (filed by this slice) |
| **Depends on** | spec #00 (`docs/specs/phase-6/00-analytics-tables.md` — `quiz_review_events` + `lesson_view_events` + dual-write contract; shipped `e7a0044`) ▪ spec #01 (`docs/specs/phase-6/01-foundation-schema.md` — `decks` / `lessons` / `quiz_items` + `superseded_by_id` self-ref FK; shipped `a989539`) ▪ spec #04 (`docs/specs/phase-6/04-admin-authoring.md` — admin services + write schemas + substantive-edit cascade + admin auth chain; shipped `d6bda3b` BE + `634f633` FE) ▪ spec #05 (`docs/specs/phase-6/05-seed-lessons.md` — savepoint-protected UPSERT pattern + natural-key idempotency; shipped `ac5b905`) ▪ existing `app/core/llm_router.py::generate_for_task` (R11 contract) ▪ existing `Depends(require_admin)` + `audit_admin_request` chain (`app/core/deps.py`) ▪ existing `slowapi` rate limiter (`app/core/rate_limit.py`). |
| **Blocks** | Slice 6.11 (cross-model critique scoring → `card_quality_signals` table — slice 6.13.5 builds the table; this slice writes layer 1 of the curriculum.md §7 three-layer quality skeleton). Slice 6.13.5 (user-thumbs feedback layer) consumes the same admin-write surfaces this slice exercises. |
| **Cross-refs** | scout `docs/audits/phase-6-scout.md` §7.2 (no object storage today), §7.3 (no background job system; recommend RQ-on-Redis), §8.1 (LLM router surface), §8.2 (cross-model critique greenfield), §8.3 (no prompt registry), §8.4 (no eval harness), cross-cutting #1 (no background-job system), #2 (no object storage), #5 (no prompt registry), slice-by-slice 6.10 entry, **R-5** (RQ-on-Redis recommendation), **R-6** (provider_override extension recommendation), **R-10** (file-storage decision); `curriculum.md` §4 (substantive-edit cascade), §6 (seed-corpus UPSERT pattern), §7 (three-layer quality skeleton — this slice = layer 1); `backend.md` §1 (service-layer conventions, savepoint pattern), §2 (route conventions, error mapping); `analytics.md` (catalog discipline, dual-write contract); `llm-strategy.md` (R11 contract); SESSION-STATE Phase 6 LDs **G2** (RQ on Redis), **H1** (Cloudflare R2 for ingestion artifacts), **I1** (dual-write Postgres events); D-016 (open drift — `response_schema` not plumbed in `_call_gemini`). |

> **Slice numbering note (info-only):** the scout audit at `5b0aa23` (2026-04-26) numbered slice 6.10 as the AI ingestion pipeline. That numbering held through Phase 6 re-sequencing (slice 6.10 unchanged); see SESSION-STATE Phase 6 specs block for the authoritative slice → spec mapping.

---

## 1. Problem

The Phase-6 curriculum platform now has every load-bearing primitive
in place for *hand-authored* content: the schema (slice 6.1), FSRS
scheduler (slice 6.2), the lesson-card UX (slice 6.3), the multi-route
admin shell + admin authoring services (slice 6.4 / 6.4b), reference
seed corpus (slice 6.4.5), the read-time invariant chain (slice 6.5),
the Lens-ranked deck ordering (slice 6.6), the persona-aware Learn
page (slice 6.7), the user-self FSRS dashboard (slice 6.8), and the
edit-classification rule (slice 6.4b §7 / B-082 retro-close).

What does **not** yet exist is any *machine-assisted authoring
loop*. Today, every lesson + quiz_item that lands in `decks` /
`lessons` / `quiz_items` is hand-authored via slice 6.4b's admin
PATCH/POST routes (or hand-seeded via the slice 6.4.5 corpus loader).
This does not scale to the 12-deck × N-lesson catalogue the PRD
contemplates — the locked decks alone span thousands of lessons over
their lifetime, and the curriculum.md §7 three-layer quality model
explicitly anticipates an **AI-assisted generation layer** (layer 1)
followed by a **cross-model critique layer** (layer 2) before content
reaches users.

Three concrete gaps motivate this slice:

- **No machine-assisted lesson drafting.** Admins author lessons one
  field at a time via the slice 6.4b editor pages
  (`pages/admin/LessonEditor.tsx`). There is no path that takes a
  source-of-truth Markdown blob (e.g., a transcript, a spec PDF, or a
  hand-authored long-form Markdown doc) and produces a lesson + N
  quiz_items as a draft for admin review.
- **No durable job storage.** The `BackgroundTasks` primitive in use
  for `audit_admin_request` and `_fire_admin_analytics_viewed` cannot
  survive process restart, cannot be retried by the framework, and
  cannot fan out across workers (scout §7.3). A multi-step LLM
  pipeline (Gemini gen → cross-model critique) routinely takes ~60s
  end-to-end and is retry-prone — `BackgroundTasks` is the wrong
  tool.
- **No object storage for source artifacts.** Source markdown blobs,
  generated lesson markdown, and critique reports want durable
  storage outside the request lifecycle so admins can re-trigger the
  pipeline against a saved input without re-pasting and so post-hoc
  audits can replay the prompts that produced a given lesson. Scout
  §7.2 confirms zero R2 / S3 wiring on disk — `AGENTS.md`'s "R2 for
  files" line is aspirational.

Slice 6.10 closes all three by introducing:

1. **Async job framework: RQ on Redis** (LD G2, scout R-5). Redis is
   already a hard dep (`redis>=5.0.0` in `requirements.txt`;
   `REDIS_URL` already wired through `Settings.redis_url`).
2. **Object storage: Cloudflare R2** for source-content artifacts +
   generated draft markdown + critique reports (LD H1).
3. **Two-stage AI pipeline**: Gemini-reasoning-tier generates a
   lesson draft + N quiz_item drafts → cross-model (Anthropic Claude)
   critique scores the draft against a quality rubric → drafts land
   under the existing `decks` / `lessons` / `quiz_items` tables via
   the slice 6.4b admin services (per **G-5** single-source-of-
   truth).

This slice is the **first** Track D slice (AI-assisted authoring) and
the **first user of the LLM router for content generation at the
deck/lesson scale**. It locks the durable-job + object-storage +
cross-model-critique primitives that the rest of Phase 6's quality
loop (slices 6.11 / 6.13 / 6.13.5) depends on.

The pipeline is **admin-only in v1** (G-4) — no user-facing upload
UX; no per-user AI-generated content. The product loop is "admin
pastes source Markdown → ingestion produces a draft lesson + N
quiz_items → admin reviews and publishes via existing slice 6.4b
admin routes". User-facing AI authoring (e.g. "generate a flashcard
from this question I just got wrong") is explicitly out of scope and
not implied to come later.

### 1.1 Step 0 audit findings

Audit reads at HEAD `c2491e0` (post-B-082 SHA-backfill,
post-slice-6.9 retro-close):

1. **Background-job framework on disk: greenfield.**
   `requirements.txt` has no `rq`, `celery`, `dramatiq`, `huey`,
   `apscheduler` entries. The only async primitive in use is
   `fastapi.BackgroundTasks` (consumed by `core/deps.py:7,106` for
   `audit_admin_request` writes and `_fire_admin_analytics_viewed`).
   `BackgroundTasks` runs in the same Python process as the request
   handler after the response returns but inside the same async
   event loop — cannot survive process restart, cannot be retried by
   the framework, cannot fan out across workers (scout §7.3).
   `redis>=5.0.0` IS already a dep (`requirements.txt:37`); the
   Python `redis` client is consumed by `home_state_service.py:69-72`,
   `geo_pricing_service.py:38-41`, `study_service.py:157-160`, and
   `admin_analytics_service.py:65-68` for cache + counter use.
   `REDIS_URL` is wired through `Settings.redis_url` at
   `app/core/config.py:33` (default `redis://localhost:6379`) and
   appears in `.env.example`. There is **no `app/jobs/` or
   `app/workers/` directory** on disk — RQ infrastructure stand-up is
   greenfield this slice.

2. **Object-storage on disk: greenfield.**
   `requirements.txt` has no `boto3`, `aiobotocore`, `cloudflare`,
   `s3fs`, `aioboto3` entries. There is no
   `app/services/storage_service.py` or `app/core/object_storage.py`
   (scout §7.2). Resume bytes today are streamed via FastAPI's
   `UploadFile`, parsed in-memory via `pdfplumber` / `python-docx`,
   and dropped at the end of the request. `AGENTS.md` line 326-327
   ("R2 for files (zero egress)") is aspirational — no R2 / S3
   binding exists. R2's S3-compatible API means `boto3` + an
   R2-flavored endpoint URL is the simplest path; new env vars
   needed: `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   `R2_ACCOUNT_ID`, `R2_BUCKET_INGESTION_ARTIFACTS`. Greenfield
   wiring this slice (or a thin sub-slice prereq — see **§14
   OQ-K**).

3. **`llm_router.generate_for_task` signature audit.**
   `app/core/llm_router.py:210-266` exposes:
   ```python
   def generate_for_task(
       task: str,
       prompt: str,
       system_prompt: Optional[str] = None,
       json_mode: bool = False,
       max_tokens: int = 4096,
       temperature: float = 0.7,
       thinking_budget: Optional[int] = None,
   ) -> str: ...
   ```
   Provider dispatch is module-level (`_call_gemini` / `_call_anthropic`
   / `_call_openai`) chosen from `LLM_FAST_PROVIDER` /
   `LLM_REASONING_PROVIDER` env vars at request time. Two
   audit-driven gaps for slice 6.10:
   - **No `provider_override` parameter.** Cross-model critique
     (Gemini gen + Claude critique) requires either (a) extending
     `generate_for_task` with `provider_override: str | None = None`
     so a single ingestion job can target two providers without
     flipping the global env var (scout R-6 recommendation), or (b)
     hot-swapping `LLM_REASONING_PROVIDER` mid-job (fragile per
     scout). See **§14 OQ-D + OQ-N**.
   - **No `response_schema` plumbing.** `_call_gemini:68-126` accepts
     `json_mode` (which maps to `response_mime_type="application/
     json"` in `types.GenerateContentConfig`) but never accepts a
     `response_schema=…`. D-016 in `SESSION-STATE.md` Drift flags
     captures this gap. Ingestion's structured-output need (the
     orchestrator parses LLM output into `LessonCreateRequest` +
     `list[QuizItemCreateRequest]`) is the natural impl driver to
     close D-016. See **§14 OQ-O**.

4. **Prompt-template registry on disk: greenfield.**
   Prompts are inlined in service code as f-strings. Examples:
   `gpt_service.py::_build_cover_letter_prompt` (multi-tone
   `match`-statement); `nlp.py::_extract_company_name_llm` lines
   273-300; `experience_service.py` body. No `app/prompts/`
   directory; no template loader; no version control of prompts
   beyond git (scout §8.3 + cross-cutting #5). For slice 6.10 the
   ingestion service iterates on two prompt families (lesson_gen +
   critique) and admin authoring will likely tune them post-launch —
   a thin loader (`app/prompts/<task>.md` +
   `Path(...).read_text()`) is greenfield work this slice.

5. **Admin auth + audit chain: mature.** `Depends(require_admin)` at
   `app/core/deps.py`; `audit_admin_request` writes one
   `admin_audit_log` row per admin request via `BackgroundTasks`.
   Both attached at the router level via
   `APIRouter(dependencies=[Depends(audit_admin_request)])` —
   pattern verified at `app/api/v1/routes/admin_lessons.py:32`,
   `admin_decks.py:32`, `admin_quiz_items.py:32`. New ingestion
   routes plug into the same chain, no new auth surface needed.

6. **Slowapi rate limiter: mature.** `Limiter` instance at
   `app/core/rate_limit.py:12` keyed on `slowapi.util.
   get_remote_address`. Global default 100 req/min; `/auth/*`
   10/min; `POST /admin/cards/generate` 5/min (the canonical
   `@limiter.limit("5/minute")` precedent at
   `app/api/v1/routes/admin.py:137`). Per-route override via the
   `@limiter.limit(...)` decorator. New ingestion enqueue endpoint
   needs a stricter cap (per **§14 OQ-H** author hint = 10/hour per
   admin user) — slowapi's per-key limit by `get_remote_address` is
   IP-based; per-user keying needs a custom `key_func` or the
   ingestion service can enforce its own per-admin counter via
   Redis (`INCR ingestion:enqueue:{user_id}:{hour}` with TTL).

7. **Admin authoring services: mature; **single source of truth**
   write path locked.** `lesson_admin_service.create_lesson` /
   `update_lesson` / `publish_lesson` / `archive_lesson` (lines
   1-300+); `quiz_item_admin_service.create_quiz_item` /
   `update_quiz_item` / `retire_quiz_item`;
   `deck_admin_service.create_deck` / `update_deck` /
   `archive_deck`. Per **G-5** the ingestion pipeline writes
   exclusively through these services — no parallel staging schema,
   no direct ORM writes from the worker. The substantive-edit
   cascade (curriculum.md §4 + spec #04 §7) and the
   `EditClassificationConflictError` 409 mapping
   (`admin_lessons.py:107-116`) apply when ingestion overwrites an
   existing lesson — see **§14 OQ-E** for idempotency / overwrite
   semantics.

8. **Natural-key UPSERT pattern: mature.** `seed_lessons_service.
   load_seed_corpus` (slice 6.4.5, `ac5b905`) uses
   `db.begin_nested()` savepoints around per-row INSERT to tolerate
   partial-failure during bulk loads; natural keys are
   `decks.slug`, `(lessons.deck_id, lessons.slug)`,
   `(quiz_items.lesson_id, sha256(question)[:16])` per spec #05 §6.1.2.
   Ingestion v1 reuses the same UPSERT pattern when re-running
   against the same source content (idempotency floor: re-run is a
   no-op if source-content-hash matches). See **§14 OQ-E**.

9. **Pre-existing ingestion event surface: zero.**
   `rg "ingestion_|generate_lesson_|critique_"` against
   `hirelens-frontend/src/` and `hirelens-backend/app/` returns no
   hits. Greenfield event surface (no deprecated rows, no
   collisions). Per **§14 OQ-M** author hint, three events
   (`ingestion_job_enqueued`, `ingestion_job_completed`,
   `ingestion_job_failed`) is the v1 minimum — admin observability
   demands at least the start/end/error triple.

10. **Eval harness: greenfield.** No `tests/integration_llm/`
    evaluating prompt outputs against golden sets; the only LLM-
    touching tests are unit tests with mocks (`@pytest.mark.integration`
    markers gate live-call asserts at `tests/services/test_resume_
    rewrite.py` and similar — small suite per scout §8.4). Slice
    6.10's critique-prompt iteration would benefit from a golden-
    set harness, but this slice ships the *infra* that generation +
    critique runs on, not the eval harness itself. Eval harness is
    **out of scope this slice** (§13); slice 6.11 (critique scoring
    →`card_quality_signals`) is the natural home.

11. **Multi-route admin shell on disk: mature.** `App.tsx` mounts
    `/admin/decks`, `/admin/lessons`, `/admin/quiz-items`,
    `/admin/analytics`. AdminGate wraps `/admin/*` routes per slice
    6.4a (`b0806d0`). New `/admin/ingest` (or alternatives — see
    **§14 OQ-J**) mounts alongside; no auth surface change.

12. **Substantive-edit cascade ON: lessons / quiz_items.** Per
    curriculum.md §4 + spec #04 §7, lesson updates that exceed the
    15% character-delta threshold on `concept_md` /
    `production_md` / `examples_md` retire all active quiz_items
    under the lesson in the same DB transaction.
    `EditClassificationConflictError` 409 enforces admin-claimed-
    classification consistency. Ingestion's "re-ingest the same
    source markdown after admin tweaks" path crosses this cascade —
    the orchestrator declares a classification claim per-PATCH and
    handles the 409 retry-with-corrected-claim path. See **§14 OQ-E**.

13. **Event-table FK shape (slice 6.0):** `quiz_review_events` and
    `lesson_view_events` are append-only with `FK ON DELETE CASCADE`
    on `quiz_item_id` / `lesson_id` / `deck_id`. Ingestion writes
    do NOT emit `quiz_review_events` (those track user reviews, not
    admin-cum-machine writes); they DO touch lesson rows that may
    later receive `lesson_view_events` writes. No new event table
    needed for ingestion — three PostHog events (per finding #9 +
    §14 OQ-M) are the v1 telemetry envelope.

14. **`thinking_budget` plumbing:** `_call_gemini:75-105` accepts
    `thinking_budget: Optional[int]` and plumbs into
    `types.ThinkingConfig(thinking_budget=…)` for Gemini 2.5 Pro.
    Ingestion's lesson_gen prompt benefits from a generous budget
    (e.g. 1500-2000 tokens) so the model can structure the output
    cleanly; cap is critical so thinking doesn't starve the
    `max_output_tokens` pool (per B-001 / spec #51 LD-4 Option A
    rationale). The orchestrator passes a non-default
    `thinking_budget` for the gen call; critique runs on a faster
    tier without thinking. See **§14 OQ-D**.

15. **Existing `ai_card_service.generate_card_draft` precedent:**
    the closest on-disk pattern to "LLM generates structured
    content with admin-review gate" is
    `app/services/ai_card_service.py::generate_card_draft` (called
    from `POST /admin/cards/generate` with the 5/min slowapi cap
    per finding #6). It uses `generate_for_task(task="card_draft",
    json_mode=True, ...)` and parses `text` into a draft via
    `json.loads`. The pattern is sync (request-time) + small
    output (one card). Ingestion v1 differs by being *async*
    (RQ-queued) + *multi-output* (lesson + N quiz_items) +
    *cross-model* (gen + critique). The shape rhymes; the scaling
    differs.

### 1.2 Why this matters

- **Activates Track D (AI-assisted authoring).** Slice 6.10 is the
  first Phase-6 slice that *generates* content rather than
  filtering, ranking, or surfacing it. Layer 1 of the curriculum.md
  §7 three-layer quality skeleton lands here; layer 2 (critique
  scoring → `card_quality_signals`) is slice 6.11; layer 3
  (user-thumbs feedback) is slice 6.13.5.
- **Locks the async-job + object-storage primitives** that slice
  6.14 (daily Pro digest cron) and any future content-cleanup batch
  job will reuse. Investing in RQ-on-Redis + R2 wiring once pays
  forward for every async / durable-job slice in Phase 6 and
  beyond.
- **Closes the scout's largest infra gap.** Cross-cutting findings
  #1 + #2 + #5 (no background-job system, no object storage, no
  prompt registry) are all addressed by this slice. After ship,
  Phase-6 has every load-bearing infra primitive named in scout
  §7-§8.
- **Resolves D-016** (open drift — `response_schema` not plumbed in
  `_call_gemini`). Ingestion's structured-output use case is the
  first natural impl driver — the prompt-only enforcement that
  D-016 flagged as belt-and-suspenders-missing on cover-letter is
  acceptable for short-form output but unacceptable for a 2000-
  token JSON-shaped lesson + quiz_item batch. Plumbing
  `response_schema` (per **§14 OQ-O**) lands as part of the impl
  slice's natural blast radius.
- **Forward-compatible with multi-source v2.** v1 accepts paste-
  text Markdown only (per **G-3** + **§14 OQ-A**); the
  R2-artifact-key abstraction in the `ingestion_jobs` row (§5.3)
  lets a future v2 PDF / DOCX / URL upload slice slot in without
  schema migration.

---

## 2. Goals

| # | Goal |
|---|------|
| **G-1** | **Async job framework: RQ on Redis** per LD G2 + scout R-5. New `app/jobs/ingestion_worker.py` consumed by an `rq worker` process; Redis already a dep. New deps: `rq>=1.16` (additive `requirements.txt` line). The same primitive is reused by slice 6.14 (daily digest) and any future async-job slice; this slice is the canonical ground-up reference for RQ-on-Redis conventions in this codebase. |
| **G-2** | **Source-content artifact storage: Cloudflare R2** per LD H1. New `app/services/object_storage_service.py` wraps an R2 client (S3-compatible API). Source markdown blobs and generated draft markdown + critique reports persist under `s3://<bucket>/ingestion/<job_id>/{source.md, draft.md, critique.json}`. New env vars: `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ACCOUNT_ID`, `R2_BUCKET_INGESTION_ARTIFACTS`. |
| **G-3** | **Source content format v1: Markdown only.** Admin pastes Markdown text in the request body; ingestion parses Markdown frontmatter (optional `target_deck_slug`) + body. PDF / DOCX upload deferred to a future slice (§13); multipart `UploadFile` upload deferred (§14 OQ-A author hint). |
| **G-4** | **Admin-only access in v1.** `POST /api/v1/admin/ingest` and `GET /api/v1/admin/ingest/{job_id}` gated by the existing `Depends(require_admin)` + `audit_admin_request` chain at the router level (`APIRouter(dependencies=[Depends(audit_admin_request)])`). No user-facing upload UX. |
| **G-5** | **Single source of truth.** Ingestion writes go through the existing slice 6.4b admin services (`deck_admin_service` / `lesson_admin_service` / `quiz_item_admin_service`) — same UPSERT semantics, same substantive-edit cascade, same admin-attribution pattern. **No parallel ingestion-staging schema; no direct ORM writes from the worker.** |
| **G-6** | **Two-stage AI pipeline: Gemini reasoning-tier gen → cross-model critique.** Ingestion orchestrator routes the lesson-generation step through `llm_router.generate_for_task(task="lesson_gen", ...)` with the reasoning-tier provider (Gemini 2.5 Pro per env defaults), then routes the critique step through the same router with a `provider_override` parameter (per §14 OQ-D author hint = Anthropic Claude). Both steps emit structured output (per §14 OQ-O = `response_schema` plumbed). Critique runs **pre-publish** so generated drafts land at `published_at=NULL` (per §14 OQ-G author hint). |
| **G-7** | **Durable job state + observable retry.** New `ingestion_jobs` table (one Alembic migration, §7) tracks `status` per job through the pipeline (`pending → running → generating → critiquing → publishing → completed | failed`). Per-step retry budget per **§14 OQ-F**; total job timeout cap per **§14 OQ-F**. Failed jobs surface a structured `error_message` so admins can re-trigger from the saved R2 source artifact without re-pasting. |

---

## 3. Non-goals (out-of-scope this slice)

- **No PDF / DOCX / URL ingestion in v1.** Markdown-only per G-3.
  Source-format expansion is a future slice that builds on the same
  R2-artifact-key abstraction (§5.3); the `source_format` column on
  `ingestion_jobs` is a forward-compat hook, not a feature.
- **No multipart `UploadFile` in v1** (per §14 OQ-A author hint).
  Admin pastes text in the JSON request body; v1's request size cap
  is 1MB (per §14 OQ-I author hint). Multipart upload + larger size
  cap is a v2 sub-slice.
- **No user-facing ingestion UX.** No "submit a question for the AI to
  generate a flashcard" surface. Per G-4, ingestion is an admin
  authoring affordance, not a user-feature.
- **No quality-score emission v1** (per §14 OQ-L author hint). Layer
  2 of curriculum.md §7 (critique-derived `quality_score` writes to
  `lessons.quality_score` + `card_quality_signals`) is **slice 6.11
  / 6.13.5** territory. This slice's critique step gates publish-
  readiness (PASS / FAIL / NEEDS_REVIEW) but does NOT write a
  numeric score. The R2 critique.json artifact preserves the raw
  critique payload so slice 6.11 can backfill scores from history if
  desired.
- **No cron / scheduled trigger surface.** Ingestion is admin-
  triggered (one job per `POST /admin/ingest` call). Scheduled bulk
  ingestion (e.g. "ingest the entire seed corpus weekly") is out of
  scope; slice 6.14's cron architecture decision (B-078 🟦) is the
  natural home for any future scheduled trigger.
- **No FE consumer this slice** (per §14 OQ-J author hint). The
  job-status endpoint scaffolds BE-side; the FE polling consumer
  (`pages/admin/Ingest.tsx` + a `useIngestionJob` hook) is a follow-
  up slice. Admin in v1 reads logs / `ingestion_jobs` rows directly
  (or via a one-liner CLI script for ops-grade observability).
- **No eval harness.** Per scout §8.4 finding #10 + §1.1 audit
  finding #10, golden-set evaluation of generation + critique
  prompt outputs is a future slice. v1 ships unit tests with mocked
  LLM responses; live-LLM integration tests are gated by
  `@pytest.mark.integration` per R13.
- **No prompt-template hot-reload.** Prompts live in
  `app/prompts/<task>.md`; the loader does `Path.read_text()` at
  module import (or per-call lazy with no caching reset path). Hot-
  reload, A/B variants, prompt versioning — all future-slice scope.
- **No retry queue UI for failed jobs.** Failed jobs surface an
  error_message in the `ingestion_jobs` row; admin retry is a fresh
  `POST /admin/ingest` (or a follow-up sub-slice that exposes a
  "retry" endpoint reading the same R2 source artifact).
- **No automatic publish-on-pass-critique.** Critique-PASS jobs
  still land lessons at `published_at=NULL` (per **G-6** + §14 OQ-G).
  Admin reviews and publishes via existing slice 6.4b
  `POST /admin/lessons/{id}/publish`. Auto-publish gating is a
  product decision deferred until layer 2 quality-score is in flight.
- **No admin-user-pool fan-out.** v1 has one admin queue. Per-admin
  job isolation, priority queues, etc. — out of scope.
- **No cross-deck dependency analysis.** Generated lessons may
  reference concepts from other decks; v1 does not model these
  references or surface them. Future "lesson cross-references"
  slice is a separate concern.
- **No embedding-based retrieval / RAG.** Generation prompt receives
  only the source markdown blob; it does NOT receive other on-disk
  lessons as few-shot examples. Future "RAG-augmented critique"
  slice is downstream of slice 6.13.5 user-feedback signals.
- **No layer-3 user-feedback consumption** in critique. Critique
  scores against a static rubric (the prompt template); user-
  thumbs signals from `card_quality_signals` (slice 6.13.5) are NOT
  fed back into this slice's pipeline. That feedback loop is a
  later integration.
- **No in-house provider for generation or critique.** Both tiers
  go through `llm_router.generate_for_task` with the existing
  provider catalogue (gemini / anthropic / openai). No new
  provider integration this slice.
- **Tier-gating for triggering ingestion** is unchanged — admin-
  only is the only gate, and admins are not subject to the
  `subscriptions.plan` paywall logic. Free vs Pro differentiation
  applies to the *output* (generated lessons inherit `decks.tier`
  per the parent deck) but not to the trigger.

---

## 4. Architecture

### 4.1 Component graph (new files)

```
hirelens-backend/app/
├── jobs/                                    [NEW dir]
│   ├── __init__.py                          [NEW]
│   └── ingestion_worker.py                  [NEW; RQ worker entry point]
├── prompts/                                 [NEW dir; minimal loader stays elsewhere]
│   ├── lesson_gen.md                        [NEW; Gemini gen prompt template]
│   └── ingestion_critique.md                [NEW; cross-model critique rubric]
├── services/
│   ├── ingestion_service.py                 [NEW; orchestrator + status query]
│   ├── object_storage_service.py            [NEW; R2 client wrapper]
│   ├── prompt_template_service.py           [NEW; thin Path.read_text() loader]
│   └── ingestion_errors.py                  [NEW; ingestion-shaped error classes]
├── schemas/
│   └── ingestion.py                         [NEW; request + response + job-row schemas]
├── api/v1/routes/
│   └── admin_ingest.py                      [NEW; POST + GET routes, admin-gated]
├── models/
│   └── ingestion_job.py                     [NEW; ORM model for ingestion_jobs]
├── core/
│   ├── config.py                            [MOD; +R2_* env vars + RQ_* env vars]
│   └── llm_router.py                        [MOD; +provider_override + response_schema]
├── alembic/versions/
│   └── <hash>_ingestion_jobs.py             [NEW; one migration]
└── main.py                                  [MOD; +admin_ingest router mount]
```

Two adjacent edits to existing services per **§14 OQ-N + OQ-O**:
- `app/core/llm_router.py` — additive `provider_override: str | None = None`
  parameter to `generate_for_task` + plumbing into provider dispatch.
- `app/core/llm_router.py::_call_gemini` — additive
  `response_schema: Optional[Type[BaseModel]] = None` parameter +
  plumbing into `types.GenerateContentConfig(response_schema=…)` (per
  D-016 close-shape).

### 4.2 Data flow

```
admin pastes Markdown → POST /api/v1/admin/ingest
  ├─ slowapi 10/hour gate (per-admin via Redis counter; §6.3)
  ├─ require_admin + audit_admin_request (router-level)
  ├─ ingestion_service.enqueue_ingestion(payload, db, admin)
  │    1. compute source_content_sha256
  │    2. dedupe lookup (§14 OQ-E): if active job with same hash, return existing job
  │    3. write source markdown to R2 (s3://<bucket>/ingestion/<job_id>/source.md)
  │    4. INSERT ingestion_jobs row (status='pending')
  │    5. enqueue RQ job: ingestion_worker.run_ingestion_job(job_id)
  │    6. emit posthog event: ingestion_job_enqueued
  │    7. return IngestionJobResponse {job_id, status}
  └─ HTTP 202 Accepted

(async, in RQ worker process)
ingestion_worker.run_ingestion_job(job_id):
  ├─ FETCH ingestion_jobs row → mark status='running'
  ├─ FETCH source markdown from R2
  ├─ STAGE 1: lesson_gen (Gemini reasoning-tier)
  │    - load app/prompts/lesson_gen.md template
  │    - generate_for_task(task="lesson_gen", prompt=..., json_mode=True,
  │                        response_schema=LessonGenSchema, thinking_budget=2000)
  │    - parse → LessonGenSchema {target_deck_slug, lesson, quiz_items[]}
  │    - write draft.md to R2
  │    - mark status='critiquing'
  ├─ STAGE 2: critique (cross-model — provider_override="anthropic")
  │    - load app/prompts/ingestion_critique.md template + draft from STAGE 1
  │    - generate_for_task(task="ingestion_critique", prompt=...,
  │                        provider_override="anthropic",
  │                        json_mode=True, response_schema=CritiqueSchema)
  │    - parse → CritiqueSchema {verdict: PASS|FAIL|NEEDS_REVIEW, dimensions[], rationale}
  │    - write critique.json to R2
  │    - if verdict == FAIL: mark status='failed', error_message=critique.rationale, return
  │    - mark status='publishing'
  ├─ STAGE 3: persist via slice 6.4b admin services
  │    - if target_deck not on disk: deck_admin_service.create_deck(...)
  │    - lesson_admin_service.create_lesson(deck_id, ...)  [G-5 single source]
  │    - for each quiz_item: quiz_item_admin_service.create_quiz_item(lesson_id, ...)
  │    - lessons.published_at stays NULL (drafts; per G-6 + §14 OQ-G)
  │    - mark status='completed'
  └─ emit posthog event: ingestion_job_completed (or _failed on exception)

admin polls GET /api/v1/admin/ingest/{job_id} → IngestionJobResponse
```

### 4.3 Failure modes + recovery

Per **§14 OQ-F** author hint = per-step retry budget of 3 attempts;
total job timeout cap of 600s (10 min) — generous because Gemini 2.5
Pro reasoning-tier latency on 2000-token output can exceed 60s and
critique adds another 30-60s.

| Failure | Detection | Action | Status |
|---|---|---|---|
| R2 source upload fails (network) | `ClientError` from boto3 | Fail-fast at `enqueue_ingestion` (no job row created) | 503 returned to admin |
| RQ enqueue fails (Redis down) | `redis.exceptions.RedisError` | Fail-fast at `enqueue_ingestion` (no job row created) | 503 returned to admin |
| Stage 1 (gen) timeout / 5xx | LLM call raises | Retry up to 3× with exponential backoff (5s/15s/45s) | If exhausted: status='failed', error_message=…, ingestion_job_failed event |
| Stage 1 returns invalid JSON | `pydantic.ValidationError` | Same retry budget | If exhausted: status='failed' |
| Stage 2 (critique) timeout / 5xx | LLM call raises | Same per-step retry budget | If exhausted: status='failed' |
| Stage 2 returns FAIL verdict | Parsed critique.verdict == 'FAIL' | NO retry (LLM-judge said no) | status='failed', error_message=critique.rationale |
| Stage 3 — `EditClassificationConflictError` 409 | service raises | Retry once with `claimed_classification='substantive'` | If exhausted: status='failed' |
| Stage 3 — `LessonSlugConflictError` | service raises | NO retry (deterministic slug collision; admin must rename) | status='failed' |
| Total job timeout (>600s) | RQ job_timeout | RQ kills the worker job | status='failed', error_message='timeout' |
| Worker process crash mid-job | RQ failed registry | RQ retries the *whole job* once, then dead-letter | If exhausted: status='failed' (manual recovery via re-enqueue) |

Per-step backoff sleeps inside the worker (not via RQ
`failure_callback`) so the per-job retry budget is observable in a
single `ingestion_jobs.current_attempt` column.

### 4.4 Cross-cutting composition rules

1. **No worker-side direct ORM writes.** All persistence goes
   through `deck_admin_service` / `lesson_admin_service` /
   `quiz_item_admin_service` per **G-5**. The worker constructs the
   `*CreateRequest` / `*UpdateRequest` Pydantic models and delegates.
2. **Worker-side admin attribution.** Slice 6.4 §4.5 admin-
   attribution pattern requires the admin user_id be passed to
   `*_admin_service.*` methods. The worker reads
   `ingestion_jobs.created_by_user_id` and threads it through —
   ingestion appears in `admin_audit_log` with the admin who
   triggered the run, not the worker process.
3. **Idempotency floor: source-content-hash dedupe** (per **§14
   OQ-E** author hint). Active job (`status IN
   ('pending','running','generating','critiquing','publishing')`)
   with the same `source_content_sha256` returns the existing job's
   `IngestionJobResponse` instead of enqueueing a duplicate. Admin
   gets the same `job_id` back.
4. **Drafts only, never auto-publish** (per **G-6** + §14 OQ-G).
   `lesson_admin_service.create_lesson` defaults to
   `published_at=NULL` per spec #04 §4.4 LessonCreateRequest;
   ingestion never sets `published_at` directly. Admin publish via
   existing `POST /admin/lessons/{id}/publish` route.
5. **R2 retention: forever v1** (per **§14 OQ-K** author hint). No
   TTL, no scheduled deletion. Cost is negligible (Markdown +
   JSON), and forever-retention aligns with audit-log-style
   reasoning ("we want to be able to replay any prompt that
   produced any lesson"). Revisit at first cost-concern.

---

## 5. Schemas

### 5.1 `IngestionJobCreateRequest` (new — `app/schemas/ingestion.py`)

```python
class IngestionJobCreateRequest(BaseModel):
    """Admin pastes Markdown; ingestion produces lesson + N quiz_items
    drafts under the target deck.
    """
    source_text: str = Field(..., min_length=100, max_length=1_048_576)  # 1MB cap (OQ-I)
    target_deck_slug: Optional[str] = Field(
        None,
        description="If supplied, lesson lands under existing deck. "
                    "If None or unknown slug, ingestion creates a deck "
                    "from the source_text frontmatter (or fails if no "
                    "frontmatter).",
    )
    expected_lesson_count: int = Field(default=1, ge=1, le=5)
    notes: Optional[str] = Field(None, max_length=2000)  # admin-side memo
```

Length validators bound the request (G-3 + OQ-I = 1MB cap;
`expected_lesson_count` capped at 5 to prevent runaway batches).

### 5.2 `IngestionJobResponse` (new)

```python
class IngestionJobResponse(BaseModel):
    job_id: str
    status: Literal[
        'pending', 'running', 'generating', 'critiquing',
        'publishing', 'completed', 'failed'
    ]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    source_content_sha256: str
    target_deck_slug: Optional[str]
    target_deck_id: Optional[str]
    generated_lesson_ids: list[str] = Field(default_factory=list)
    generated_quiz_item_count: int = 0
    critique_verdict: Optional[Literal['PASS', 'FAIL', 'NEEDS_REVIEW']] = None
    error_message: Optional[str] = None
    current_attempt: int = 0
    artifacts: IngestionArtifacts  # see 5.4
```

### 5.3 `ingestion_jobs` row shape

```python
class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID4
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_format: Mapped[str] = mapped_column(String(16), default="markdown")  # forward-compat
    source_content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_r2_key: Mapped[str] = mapped_column(String(255), nullable=False)
    draft_r2_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    critique_r2_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # nullable for ON DELETE SET NULL
    target_deck_slug: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_deck_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("decks.id", ondelete="SET NULL"), nullable=True
    )
    generated_lesson_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    generated_quiz_item_count: Mapped[int] = mapped_column(Integer, default=0)
    critique_verdict: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

Indexes: `(status, created_at DESC)` for the admin "recent jobs"
query; `source_content_sha256` for dedupe lookup;
`(created_by_user_id, created_at DESC)` for per-admin filtering.

### 5.4 `IngestionArtifacts` (R2 metadata)

```python
class IngestionArtifacts(BaseModel):
    source_r2_key: str
    draft_r2_key: Optional[str] = None
    critique_r2_key: Optional[str] = None
    # Pre-signed URLs are NOT exposed in v1 — admins read R2 keys
    # via direct R2 dashboard / wrangler CLI access. Pre-signed URL
    # surfacing is OQ-J's FE-follow-up scope.
```

### 5.5 `LessonGenSchema` + `CritiqueSchema` (LLM structured output)

```python
class _GeneratedQuizItem(BaseModel):
    question: str
    answer: str
    question_type: Literal['recall', 'application']
    difficulty: Literal['easy', 'medium', 'hard']

class LessonGenSchema(BaseModel):
    target_deck_slug: str  # may match an existing deck or propose a new one
    lesson_slug: str
    title: str
    concept_md: str
    production_md: str
    examples_md: str
    quiz_items: list[_GeneratedQuizItem]  # 1..5 per OQ-D author hint

class _CritiqueDimension(BaseModel):
    name: Literal['accuracy', 'clarity', 'completeness', 'cohesion']
    score: int = Field(..., ge=1, le=5)
    rationale: str

class CritiqueSchema(BaseModel):
    verdict: Literal['PASS', 'FAIL', 'NEEDS_REVIEW']
    dimensions: list[_CritiqueDimension]
    rationale: str
```

Both schemas are passed as `response_schema=…` per **§14 OQ-O**;
Pydantic validates the LLM output before persistence.

---

## 6. Backend

### 6.1 New service — `app/services/ingestion_service.py`

```python
async def enqueue_ingestion(
    payload: IngestionJobCreateRequest,
    db: AsyncSession,
    *,
    admin: User,
) -> IngestionJobResponse:
    """Validate, dedupe, write source to R2, INSERT job row, enqueue RQ."""

async def get_ingestion_job(
    job_id: str, db: AsyncSession
) -> IngestionJobResponse | None:
    """Return job status; None if not found."""

async def list_recent_ingestion_jobs(
    db: AsyncSession,
    *,
    admin_id: Optional[str] = None,
    limit: int = 20,
) -> list[IngestionJobResponse]:
    """Recent jobs, status × created_at-DESC ordered."""
```

Module-level constants per `backend.md` §1 conventions:
`INGESTION_JOB_TIMEOUT_SECONDS = 600`, `INGESTION_MAX_ATTEMPTS = 3`,
`INGESTION_BACKOFF_SCHEDULE = [5, 15, 45]`.

### 6.2 New worker — `app/jobs/ingestion_worker.py`

```python
def run_ingestion_job(job_id: str) -> None:
    """RQ entry point. Called by `rq worker ingestion`.

    Synchronous (RQ is sync); creates its own DB session via the
    `SessionLocal` factory and runs the orchestrator. Wrapped in a
    top-level try/except that updates `ingestion_jobs.status = 'failed'`
    + `error_message` on any uncaught exception.
    """

def _generate_lesson(source_md: str) -> LessonGenSchema:
    """Stage 1 — Gemini reasoning-tier."""

def _critique_lesson(draft: LessonGenSchema) -> CritiqueSchema:
    """Stage 2 — cross-model (Anthropic per OQ-D author hint)."""

def _persist_drafts(
    job: IngestionJob, gen: LessonGenSchema, critique: CritiqueSchema, db: Session
) -> None:
    """Stage 3 — write through slice 6.4b admin services."""
```

Per-step retry logic uses a small `_with_retry(fn, attempts, backoff)`
helper colocated in the worker module (Q1 simplicity — not promoted
to shared util until rule-of-three trips).

### 6.3 New routes — `app/api/v1/routes/admin_ingest.py`

```python
router = APIRouter(dependencies=[Depends(audit_admin_request)])

@router.post("/admin/ingest", response_model=IngestionJobResponse,
             status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/hour")  # per OQ-H author hint
async def enqueue_ingestion_route(
    request: Request,  # required for slowapi
    payload: IngestionJobCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> IngestionJobResponse: ...

@router.get("/admin/ingest/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job_route(
    job_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> IngestionJobResponse: ...

@router.get("/admin/ingest", response_model=list[IngestionJobResponse])
async def list_ingestion_jobs_route(
    limit: int = Query(default=20, ge=1, le=100),
    mine_only: bool = Query(default=False),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[IngestionJobResponse]: ...
```

Error mapping per `backend.md` §2.4:
- `IngestionRateLimitedError` → 429 (custom slowapi handler reuses existing pattern)
- `R2UploadError` → 503
- `IngestionJobNotFoundError` → 404
- `IngestionPayloadError` (frontmatter parse / size cap) → 400

Wired in `app/main.py`:
```python
app.include_router(v1_admin_ingest.router, prefix="/api/v1", tags=["v1 Admin Ingest"])
```

### 6.4 New service — `app/services/object_storage_service.py`

```python
class ObjectStorageService:
    def __init__(self, settings: Settings): ...
    def put_text(self, key: str, content: str, *, content_type: str = "text/markdown") -> None: ...
    def get_text(self, key: str) -> str: ...
    def exists(self, key: str) -> bool: ...
```

Per **§14 OQ-K** sub-question: `boto3` (sync) wrapped in
`asyncio.to_thread` for async surfaces. boto3 talks to R2 via the
S3-compatible `endpoint_url` parameter (Cloudflare convention:
`https://<account_id>.r2.cloudflarestorage.com`). Retain the sync
client since the RQ worker is sync; the FastAPI route's R2 write
(source.md upload at enqueue time) is the only async-side call and
uses `await asyncio.to_thread(storage.put_text, …)`.

### 6.5 New service — `app/services/prompt_template_service.py`

```python
def load_prompt(template_name: str) -> str:
    """Read app/prompts/<template_name>.md. Cached at module-import."""
```

Implementation: `Path(__file__).parent.parent / "prompts"` rooted;
`@functools.cache` on the function for one-time read (no hot-reload).
Per scout R-7-style philosophy: thin loader, no version registry.

### 6.6 Reuse of existing services

| Existing service | How ingestion uses it | Why |
|---|---|---|
| `deck_admin_service.create_deck` | Stage 3 if target deck missing | G-5 single source of truth |
| `deck_admin_service.get_deck_by_slug` | Stage 3 lookup | dedupe + idempotency |
| `lesson_admin_service.create_lesson` | Stage 3 (always) | G-5 + draft default |
| `quiz_item_admin_service.create_quiz_item` | Stage 3 (per item) | G-5 |
| `llm_router.generate_for_task` | Stages 1 + 2 | R11 |
| `core.analytics.track` | enqueue + completion + failure | analytics.md catalog |
| `core.deps.audit_admin_request` | route dependency | admin observability |

`llm_router.generate_for_task` requires two additive parameters per
**§14 OQ-N + OQ-O** (`provider_override` + `response_schema`); see
§4.1 component graph.

### 6.7 Performance envelope

| Stage | p95 latency target | Notes |
|---|---|---|
| `enqueue_ingestion` (admin's HTTP request) | <2s | R2 upload + INSERT + enqueue |
| Stage 1 (Gemini gen reasoning-tier) | <90s | thinking_budget=2000; 2000-token output |
| Stage 2 (Anthropic critique) | <60s | smaller output (<500 tokens) |
| Stage 3 (admin-service persist) | <2s | 1 deck + 1 lesson + ≤5 quiz_items via existing services |
| **End-to-end** | **<180s** | total job timeout cap = 600s (3.3× safety margin) |

---

## 7. Migrations

One Alembic migration: `<hash>_ingestion_jobs.py`.

CREATE `ingestion_jobs` table per §5.3 column shape. Indexes:
- `ix_ingestion_jobs_status_created_at` ON `(status, created_at DESC)`
- `ix_ingestion_jobs_source_hash` ON `(source_content_sha256)`
- `ix_ingestion_jobs_admin_created_at` ON `(created_by_user_id, created_at DESC)`

FK constraints:
- `created_by_user_id REFERENCES users(id) ON DELETE SET NULL`
  (admin account deletion does not orphan job history; matches
  `quiz_review_events` precedent per analytics-tables spec §4.4)
- `target_deck_id REFERENCES decks(id) ON DELETE SET NULL`
  (deck deletion does not orphan ingestion history)

No data migration; table starts empty. R6 (Alembic for all schema
changes) compliance: handwritten or autogen — both acceptable per
db-migration.md.

---

## 8. Frontend

**Zero new FE surface in v1.** Per **§14 OQ-J** author hint, the
job-status endpoint is scaffolded BE-side; admin reads job status
via direct API call (e.g. `httpie GET /api/v1/admin/ingest/{job_id}`)
or via a one-liner ops CLI (out of scope this slice).

The FE consumer (`pages/admin/Ingest.tsx` + `useIngestionJob` hook +
polling effect + the editor surface for paste-Markdown) is a follow-
up sub-slice tracked via a new BACKLOG row at impl close (per the
§15 forward-link).

R12 token compliance is moot this slice (no FE styling). Existing
admin chrome (`AdminGate` + `AdminLayout`) consumes the future
`/admin/ingest` mount transparently when added.

---

## 9. Analytics

Per **§14 OQ-M** author hint = three events (start / complete /
fail). All BE-emitted, all gated by ingestion's admin-only audience
(`internal: true` discriminator per `analytics.md` admin-event
convention).

| Event | Source | Properties |
|---|---|---|
| `ingestion_job_enqueued` | `ingestion_service.enqueue_ingestion` | `{admin_id, job_id, source_content_sha256, target_deck_slug, source_size_bytes, internal: true}` |
| `ingestion_job_completed` | `ingestion_worker.run_ingestion_job` (success branch) | `{admin_id, job_id, target_deck_id, generated_lesson_ids: list[str], generated_quiz_item_count: int, critique_verdict, duration_seconds: int, internal: true}` |
| `ingestion_job_failed` | `ingestion_worker.run_ingestion_job` (failure branch) | `{admin_id, job_id, stage: 'gen'\|'critique'\|'persist'\|'timeout'\|'enqueue_dedup'\|'unknown', error_class: str, current_attempt: int, internal: true}` |

Catalog discipline: `.agent/skills/analytics.md` updated in lock-step
with the impl slice (per the §15 forward-link). Three events,
zero deprecated rows touched.

No Postgres dual-write — `ingestion_jobs` table itself is the
SQL-queryable record; PostHog covers the admin funnel side.

---

## 10. Test plan

### 10.1 BE unit — `tests/test_ingestion_service.py` (~6-8 tests)

- `enqueue_ingestion` writes source.md to R2, INSERTs job row,
  returns `IngestionJobResponse` with `status='pending'`.
- Dedupe: second call with identical source_text returns the
  existing job_id, no second R2 upload, no second RQ enqueue.
- Source size > 1MB → `IngestionPayloadError` 400.
- Source size < 100 chars → `IngestionPayloadError` 400.
- `get_ingestion_job` returns `None` for unknown id.
- `list_recent_ingestion_jobs` filters `mine_only` correctly.
- `R2UploadError` at upload time → 503; no job row created.

### 10.2 BE unit — `tests/test_ingestion_worker.py` (~6-9 tests)

Mocks: `llm_router.generate_for_task` (both stages),
`object_storage_service.put_text` / `get_text`,
`deck_admin_service` / `lesson_admin_service` /
`quiz_item_admin_service` (the persist-stage delegation).

- Happy path: gen → critique=PASS → persist → status='completed'.
- Critique=FAIL → status='failed', error_message=critique.rationale,
  no Stage 3 invoked.
- Stage 1 raises 5xx 3× → status='failed', error_message=…
- Stage 2 raises 5xx 3× → status='failed'.
- Stage 1 returns invalid JSON 3× (`pydantic.ValidationError`) →
  status='failed'.
- Stage 3 `EditClassificationConflictError` → retry once with
  corrected claim → success.
- Stage 3 `LessonSlugConflictError` → no retry → status='failed'.
- `published_at IS NULL` on the created lesson rows
  post-completion (G-6 + OQ-G assertion).

### 10.3 BE route — `tests/test_admin_ingest_routes.py` (~6-8 tests)

- POST unauthed → 401.
- POST authed-non-admin → 403.
- POST authed-admin happy path → 202 + `IngestionJobResponse`.
- POST 11th call from same admin within an hour → 429 (slowapi).
- GET unknown job_id → 404.
- GET job_id created by another admin → 200 (admins see all jobs;
  `mine_only=true` query param scopes to caller).
- POST source_text with frontmatter `target_deck_slug` matching an
  existing deck → 202; subsequent worker run lands lesson under
  that deck.
- `audit_admin_request` writes one `admin_audit_log` row per POST.

### 10.4 BE integration — `tests/integration_llm/test_ingestion_pipeline.py` (~2 tests)

Decorated `@pytest.mark.integration` per R13. Live LLM keys
required.

- End-to-end: enqueue → worker → persisted lesson + quiz_items;
  `lessons.published_at IS NULL`; `ingestion_jobs.status='completed'`.
- Cross-model verification: Stage 1 provider == Gemini; Stage 2
  provider == Anthropic; assertion via `caplog` capture of the
  router's `LLM call: task=…, provider=…` log lines.

### 10.5 Object storage — `tests/test_object_storage_service.py` (~3 tests)

- `put_text` + `get_text` round-trip (mocked boto3 client).
- `exists` returns False for unknown key.
- Network error in `put_text` raises `R2UploadError`.

### 10.6 Prompt template — `tests/test_prompt_template_service.py` (~2 tests)

- `load_prompt('lesson_gen')` returns non-empty Markdown.
- `load_prompt('unknown')` raises `FileNotFoundError`.

### 10.7 LLM router extension — `tests/test_llm_router_extensions.py` (~3-4 tests)

Per **§14 OQ-N + OQ-O** new params:
- `generate_for_task(provider_override='anthropic')` dispatches to
  `_call_anthropic` regardless of `LLM_REASONING_PROVIDER` env.
- `generate_for_task(response_schema=Schema)` plumbs into
  `_call_gemini`'s `types.GenerateContentConfig(response_schema=...)`
  (mocked Gemini SDK).
- Unknown `provider_override` → `ValueError`.
- Existing call sites unaffected (regression: `cover_letter` /
  `card_draft` / `resume_rewrite` still pass tests).

### 10.8 Regression set must stay green

- All BE 651 + FE 414 baseline tests still pass.
- `tests/test_lesson_admin_service.py` — admin write path
  unaffected by ingestion's invocation.
- `tests/test_admin_decks.py` / `tests/test_admin_lessons.py` /
  `tests/test_admin_quiz_items.py` — slice 6.4b routes unchanged.
- `tests/test_llm_router.py` — provider dispatch unchanged for
  existing call sites.

### 10.9 Test envelope (estimates, locked at impl)

- BE: **651 → ~676..686** (+25..+35) across §10.1-§10.7.
- BE integration: **+2** (slow-marker, gated).
- FE: **414 → 414** (zero new FE this slice).

---

## 11. Acceptance criteria

| AC | Surface | Trigger | Expected behavior | Test harness |
|---|---|---|---|---|
| **AC-1** | `POST /api/v1/admin/ingest` | unauthed | 401 | pytest `httpx_client` |
| **AC-2** | `POST /api/v1/admin/ingest` | authed non-admin | 403 | pytest |
| **AC-3** | `POST /api/v1/admin/ingest` | authed admin, valid Markdown | 202 + IngestionJobResponse with `status='pending'`; one R2 source-upload call; one RQ enqueue call | pytest with mocks |
| **AC-4** | `POST /api/v1/admin/ingest` | dedupe — same source_text within an active job window | 202 + same `job_id` returned; no second R2 write; no second RQ enqueue | pytest |
| **AC-5** | `POST /api/v1/admin/ingest` | source_text > 1MB | 400 IngestionPayloadError | pytest |
| **AC-6** | `POST /api/v1/admin/ingest` | 11th call from same admin within an hour | 429 (slowapi) | pytest |
| **AC-7** | `run_ingestion_job` | gen stage timeout 3× | `status='failed'`, `error_message` populated, `current_attempt=3`; `ingestion_job_failed` event fires with `stage='gen'` | pytest |
| **AC-8** | `run_ingestion_job` | critique verdict=FAIL | `status='failed'`, `error_message=critique.rationale`; Stage 3 NOT invoked | pytest |
| **AC-9** | `run_ingestion_job` | happy path | `status='completed'`; lesson row exists with `published_at IS NULL`; quiz_items exist; `ingestion_job_completed` event fires | pytest |
| **AC-10** | `run_ingestion_job` | Stage 3 EditClassificationConflictError | retry once with corrected claim; final status='completed' if retry succeeds | pytest |
| **AC-11** | `GET /api/v1/admin/ingest/{job_id}` | known id | 200 + IngestionJobResponse | pytest |
| **AC-12** | `GET /api/v1/admin/ingest/{job_id}` | unknown id | 404 | pytest |
| **AC-13** | `lesson_admin_service` invocation by worker | persist stage | admin attribution = `ingestion_jobs.created_by_user_id`; one `admin_audit_log` row per service call | pytest |
| **AC-14** | `llm_router.generate_for_task` | with `provider_override='anthropic'` | Anthropic dispatch regardless of `LLM_REASONING_PROVIDER` env | pytest |
| **AC-15** | `llm_router._call_gemini` | with `response_schema=LessonGenSchema` | Plumbed into `types.GenerateContentConfig`; D-016 closed | pytest with mocked SDK |
| **AC-16** | `tsc --noEmit` (FE baseline) | post-impl | type-check still passes; no new FE types added | `npm run typecheck` |
| **AC-17** | All existing FE + BE tests | post-impl baseline | 651 BE + 414 FE baseline still passes; +25..+35 BE + +2 integration | `pytest -m "not integration"` + `npx vitest run` |
| **AC-18** | `alembic upgrade head` then `alembic downgrade -1` | post-impl | `ingestion_jobs` table created + dropped cleanly | local DB CI check |
| **AC-19** | `ingestion_jobs.status` | terminal state | exactly one of `'completed' \| 'failed'`; intermediate states are not visible at completion of `run_ingestion_job` | pytest |

---

## 12. Decisions

> **EMPTY at spec-author.** Locks via §12 amendment slice mirroring
> slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 §12 amendment pattern at
> `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` / `0c21223` /
> `ab07168`. Each D-N below will resolve a §14 OQ; §14 retains the
> question + RESOLVED pointer back here for traceability after
> amendment.

(populated by §12 amendment slice; placeholder per spec-author convention)

---

## 13. Out of scope (deferred to other slices)

- **PDF / DOCX / URL ingestion source formats.** Markdown-only v1
  per G-3. The `source_format` column on `ingestion_jobs` is a
  forward-compat hook — non-Markdown shapes ship in their own
  source-format slices.
- **User-facing AI generation surface.** No "submit a question →
  AI flashcard" UX. v1 is an admin authoring affordance per G-4.
  User-facing AI features would require a separate quota / pricing /
  abuse-control surface.
- **Quality score emission v1** (per §14 OQ-L author hint). Layer 2
  of curriculum.md §7 (`lessons.quality_score` writes,
  `card_quality_signals` table) is **slice 6.11 / 6.13.5**
  territory.
- **Eval harness.** Golden-set evaluation of generation + critique
  prompts is greenfield (scout §8.4). Future slice; depends on the
  static rubric stabilising via slice 6.13.5 user feedback.
- **Cron / scheduled trigger surface.** Admin-trigger only in v1.
  Scheduled bulk ingestion, daily content refresh, etc. — slice
  6.14 (B-078 🟦) cron architecture decision territory.
- **FE consumer surface.** No `/admin/ingest` page in v1 (per §14
  OQ-J author hint). FE consumer is a follow-up sub-slice tracked
  via a new BACKLOG row at impl close.
- **Pre-signed URL surfacing for R2 artifacts.** Admins read R2 via
  direct dashboard / wrangler CLI in v1; pre-signed URL endpoints
  are FE-follow-up scope.
- **Retry-from-saved-source-artifact endpoint.** Failed jobs can be
  re-triggered by re-pasting the source markdown (or via a one-
  liner ops CLI that reads the R2 source.md). A first-class
  `POST /admin/ingest/{job_id}/retry` endpoint is a follow-up.
- **Per-step prompt versioning / A/B testing.** Prompts live as
  files under `app/prompts/<task>.md`; git is the version-control
  layer. Hot-reload, A/B variants, runtime-resolved prompt
  selection — all future-slice scope.
- **Multi-deck batch ingestion.** v1 produces one lesson per job
  (capped at `expected_lesson_count <= 5` quiz_items per lesson).
  "Ingest 50 lessons across 3 decks in one job" is a future
  slice's scope.
- **Embedding-based retrieval / RAG augmentation of generation.**
  Generation prompt receives only the source markdown blob; future
  RAG slice can augment by retrieving similar on-disk lessons.
- **Layer-3 user-feedback consumption** in critique. User thumbs
  signals from `card_quality_signals` (slice 6.13.5) are not fed
  back into critique in v1.
- **Cross-deck dependency analysis.** Generated lessons may
  reference concepts from other decks; v1 does not model these.
- **In-house provider for generation or critique.** External
  providers only via `llm_router`.
- **Non-English ingestion.** Generation + critique prompt language
  is English; multi-language support is future-slice scope.

---

## 14. Open questions

> Spec-author surface for §12 amendment lock-down. Each OQ carries
> author-hint guidance (chat-Claude pre-draft + audit refinement).
> §12 amendment will lock D-1..D-N from these per slice 6.0 /
> 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 precedent.

**OQ-A — Source-content delivery shape.** Paste-text-only v1, file-
upload v1 (multipart `UploadFile`), or both?
*Author hint:* paste-text-only v1 (simplest; defer multipart upload to
a future slice). Bounded by 1MB request size cap per OQ-I.

**OQ-B — Job framework readiness.** Is RQ already wired or is
greenfield infra stand-up required this slice?
*Author hint (audit-confirmed):* greenfield. `requirements.txt` has no
`rq` entry; no `app/jobs/` directory. Stand up RQ-on-Redis primitive
in this slice's impl.

**OQ-C — Prompt-template-registry shape.** New
`app/services/prompt_template_service.py` with `Path.read_text()` +
`@functools.cache`, OR inline f-strings co-located with the
ingestion service?
*Author hint:* new module. Two prompts (lesson_gen +
ingestion_critique) are non-trivial Markdown bodies (~1-2KB each);
inlining as f-strings hurts readability and complicates iteration.
Thin loader is ~30 LoC.

**OQ-D — Cross-model critique provider.** Same-provider-different-
model (e.g. Gemini Flash for critique vs Gemini Pro for gen) or true
cross-provider (Anthropic Claude for critique vs Gemini for gen)?
*Author hint:* true cross-provider — Gemini Pro reasoning-tier for
gen + Claude (Sonnet 4.6 or Haiku 4.5 — the impl slice picks the
specific model via env override) for critique. Cross-provider
critique is what the slice 6.10 framing literally promises ("Gemini
gen, cross-model critique"); same-provider critique is a same-prior
risk.

**OQ-E — Idempotency on re-ingestion.** Content-hash dedupe at job-
enqueue / deck-slug overwrite triggers substantive-edit cascade /
reject duplicate as 409?
*Author hint:* compound — content-hash dedupe (same source text
returns existing active job) + slug-based UPSERT in Stage 3 (re-
ingest of edited source against existing slug triggers
substantive-edit cascade per spec #04 §7). Reject-as-409 (option c)
is too brittle for the "edit source markdown, re-ingest" loop.

**OQ-F — Retry semantics.** Per-job retry budget (3 attempts default)
/ per-step retry (gen-only, critique-only, persist-only) / no-retry-
LLM-only-flake?
*Author hint:* per-step with 3-attempt budget per stage; total job
timeout cap of 600s. Pipeline-level retry (option a) restarts the
whole 90s gen on a critique flake — wasteful. Per-step keeps the
retry granular and observable via `current_attempt` column.

**OQ-G — Visibility timing.** Ingested lessons land as drafts
(`published_at=NULL`) / auto-publish on critique=PASS / configurable
per-deck?
*Author hint:* drafts only — admin publishes via existing slice 6.4b
admin route. Auto-publish (option b) requires layer-2 quality-score
infra + a confidence threshold; configurable per-deck (option c)
adds a column with no consumer. Drafts-only is the strict G-5
single-source-of-truth read.

**OQ-H — Rate-limit shape.** Per-admin-user / global / no limit
(admin trust)?
*Author hint:* per-admin-user 10/hour. Slowapi's default IP keying is
inappropriate (admins share dev / production IP pools); a custom
key_func reads the admin's user_id from the request scope.
Implementation may also enforce a Redis-backed `INCR
ingestion:enqueue:{user_id}:{hour}` counter inside the service for
clarity.

**OQ-I — Source-content size cap.** 100KB / 1MB / 10MB / no cap?
*Author hint:* 1MB v1. Markdown above 1MB is a smell (raw transcript
or raw OCR); revisit if a legitimate use case surfaces (book-length
ingestion would chunk on the way in anyway, future-slice scope).

**OQ-J — Job-status surface.** FE-polling endpoint
(`GET /api/v1/admin/ingest/{job_id}` + `useIngestionJob` hook) /
SSE / no-FE-this-slice (admin reads logs)?
*Author hint:* FE-polling endpoint scaffolded BE but no FE consumer
this slice. The polling pattern is identical to the slice 6.4b admin
editor pages and will be cheap to wire in a follow-up. SSE (option
b) is overkill for ~3 minute jobs.

**OQ-K — Source-content + artifact retention in R2.** Forever / TTL
90d / TTL 30d / delete on ingest-complete? Sub-question: SDK choice
— `boto3` (sync, mature) / `aiobotocore` (async, less mature) /
`aioboto3`?
*Author hint:* forever v1 (R2 is cheap; retention adds infra surface;
revisit on first cost concern). Sub-question: `boto3` sync wrapped
in `asyncio.to_thread` for the FastAPI side; the RQ worker runs sync
natively. Avoid `aiobotocore` until async R2 patterns prove
load-bearing elsewhere.

**OQ-L — Quality signal v1.** Emit `quality_score` from this slice
(layer-2 partial implementation) / defer entirely to slice 6.11 +
6.13.5?
*Author hint:* defer entirely. This slice is layer-1 (gen) of the
curriculum.md §7 three-layer skeleton; layer-2 (critique-derived
score) and layer-3 (user-signal-derived score) belong to slices
6.11 and 6.13.5 respectively. Critique here gates publish-readiness
(PASS/FAIL/NEEDS_REVIEW) but does NOT write a numeric score; the R2
critique.json artifact preserves dimensions + scores so 6.11 can
backfill from history.

**OQ-M — Telemetry events.** Zero / `ingestion_started` only /
`ingestion_started` + `ingestion_completed` + `ingestion_failed`
three-event minimum / four-event (add per-stage events)?
*Author hint:* three-event minimum. Admin needs observability;
matches scout's "durable job storage" framing. Per-stage events
(option d) over-instrument before there is a consumer dashboard.

**OQ-N — `llm_router.generate_for_task` `provider_override`
extension scope.** Land the additive parameter in this slice's impl
or as a separate prereq sub-slice?
*Author hint:* bundle into this slice's impl. The diff is small (~15
LoC + 1 test) and the alternative (a separate sub-slice solely for
the param addition) churns the spec / BACKLOG / SHA backfill cycle
for negligible isolation gain. Scout R-6 explicitly recommends this
extension and frames it as a slice-6.10 prerequisite.

**OQ-O — `_call_gemini` `response_schema` plumbing scope (D-016
close).** Plumb `response_schema` into `generate_for_task` +
`_call_gemini` per D-016 close-shape this slice (since ingestion's
structured-output use case is the natural impl driver), or defer to
a separate D-016-close sub-slice?
*Author hint:* bundle into this slice's impl. Same reasoning as OQ-N
— ~30 LoC + 1 test, and prompt-only enforcement on a 2000-token
JSON-shaped output is fragile per D-016 finding. Plumbing
`response_schema` makes Stage 1 + Stage 2 deterministic JSON-shaped
outputs; ingestion is the first call site that materially benefits.

**OQ-P — Ingestion job admin attribution audit-log shape.** One
`admin_audit_log` row per `POST /admin/ingest` (current default via
`audit_admin_request`) / additional rows per `lesson_admin_service`
call from the worker (so the audit log has a row for each
generated lesson + quiz_item)?
*Author hint:* one row per admin HTTP request (current default
suffices) plus the worker's slice-6.4b service calls already write
their own admin events (`admin_lesson_created`, etc.) per slice
6.4b. Don't duplicate the trail.

---

## 15. Implementation slice forward-link

Implementation row: **B-083** 🔴 (filed by this slice).

Forward dependencies before impl can start:

1. **§12 amendment slice** to lock D-1..D-N from §14 OQ-A..OQ-P at
   `<§12-amendment-sha>` (mirrors slice 6.0 / 6.4.5 / 6.5 / 6.6 /
   6.7 / 6.8 §12 amendment pattern at `e8eecdd` / `df58eaf` /
   `acba7ed` / `fb92396` / `0c21223` / `ab07168`). 🔴 not yet
   shipped.
2. No BE primitive prerequisite — every existing data source is on
   disk:
   - `decks` / `lessons` / `quiz_items` (slice 6.1, `a989539`).
   - `lesson_admin_service` / `deck_admin_service` /
     `quiz_item_admin_service` (slice 6.4b, `d6bda3b`).
   - `llm_router.generate_for_task` (R11; pre-Phase-6).
   - `Depends(require_admin)` + `audit_admin_request` (pre-Phase-6).
   - `slowapi` rate-limiter (`app/core/rate_limit.py`; spec #25).

Impl slice expected scope (from §4.1 component graph + §6 backend +
§7 migrations):

- New file `app/services/ingestion_service.py` (~200-300 lines).
- New file `app/jobs/ingestion_worker.py` (~250-350 lines).
- New file `app/services/object_storage_service.py` (~80-120 lines).
- New file `app/services/prompt_template_service.py` (~30-50 lines).
- New file `app/services/ingestion_errors.py` (~50-80 lines).
- New file `app/schemas/ingestion.py` (~120-180 lines).
- New file `app/api/v1/routes/admin_ingest.py` (~80-120 lines).
- New file `app/models/ingestion_job.py` (~50-80 lines).
- New files `app/prompts/lesson_gen.md` (~40-80 lines) +
  `app/prompts/ingestion_critique.md` (~40-80 lines).
- New Alembic migration `<hash>_ingestion_jobs.py` (~80-120 lines).
- Modify `app/core/llm_router.py` — additive `provider_override` +
  `response_schema` parameters per OQ-N + OQ-O (~25-40 lines added).
- Modify `app/core/config.py` — add R2_* + RQ_* env vars (~15-25
  lines).
- Modify `app/main.py` — mount admin_ingest router (~3-5 lines).
- New deps in `requirements.txt`: `rq>=1.16`, `boto3>=1.34` (~2 lines).
- New env-var entries in `.env.example`: `R2_*` + RQ-related.
- 7 new BE test files per §10.1-§10.7 (~25-35 unit tests + 2
  integration tests).
- 0 FE files touched.
- `.agent/skills/analytics.md` update: 3 new event rows per §9
  (`ingestion_job_enqueued` / `_completed` / `_failed`).
- `.agent/skills/curriculum.md` — minor §7 layer-1 update referencing
  slice 6.10 by SHA.
- BACKLOG B-083 closure with impl SHA (R15(c)).
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new service + worker +
  route + schema + model + migration + skill catalog updates +
  llm_router signature change + new dep entries).

Impl test envelope (estimates, locked at impl):
- BE: **651 → ~676..686** (+25..+35).
- BE integration: **+2** (slow-marker, gated on live keys).
- FE: **414 → 414** (zero new FE this slice).

R16 consumer-graph audit at impl Step 1: any new shared BE types
(`IngestionJobResponse` / `LessonGenSchema` / `CritiqueSchema`)
need consumer-graph audited. Predicted consumers: ingestion_service,
ingestion_worker, admin_ingest routes, plus their test files. No
external consumer (e.g. cards / study / mission) predicted —
ingestion is a leaf admin-side surface in v1.

R11 + LLM-strategy compliance: every LLM call in this slice goes
through `generate_for_task`. The provider_override extension does
NOT bypass R11 — it extends the router's contract additively. New
`task=` names (`lesson_gen`, `ingestion_critique`) get added to the
router's `FAST_TASKS` / `REASONING_TASKS` frozensets in the impl
slice (lesson_gen → REASONING_TASKS; ingestion_critique →
REASONING_TASKS) per llm-strategy.md catalog discipline.

Out-of-scope at impl (cross-ref §13): PDF / DOCX / URL formats,
user-facing AI surface, quality_score emission, eval harness, cron
trigger, FE consumer page, retry-from-saved-source endpoint, prompt
hot-reload / A/B, multi-deck batch jobs, embedding RAG, layer-3
user-feedback in critique, in-house provider integration.

Skill-author work potentially surfaced post-impl (NOT this slice's
scope): **`background-jobs.md`** (RQ-on-Redis conventions —
worker patterns, retry budgets, status-row UPSERT, dead-letter
handling) becomes load-bearing once slice 6.14 (daily digest) lands
as the second consumer. v1 of this slice flags as a candidate
skill-author follow-up if a third RQ consumer appears.

---

*Spec authored at `<this-slice>` against HEAD `c2491e0`. All on-
disk citations verified at audit time per SOP-5; phantom citations
zero. Forward-fil ed B-083 at status 🔴 per R15(c). §12 amendment
slice locks D-1..D-N from §14 OQ-A..OQ-P before impl pickup.*
