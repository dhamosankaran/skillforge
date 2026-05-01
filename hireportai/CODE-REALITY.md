# CODE-REALITY — SkillForge / HirePort AI

> **Purpose:** frozen-in-time map of the codebase for off-disk advisors (chat-Claude) to draft accurate prompts. If the header sha below doesn't match `git rev-parse --short HEAD`, regenerate this file.
> **Read-only artifact.** Nothing here authorizes code changes.

---

## Section 1 — Repo metadata

| Field | Value |
|-------|-------|
| Commit sha (short) | `<this-slice>` (full regen — closes no BACKLOG row; CR self-staleness restoration). **Scope:** §1–§13 fully regenerated from on-disk truth. **Prior anchor:** `691934a` (B-085 targeted regen, 2026-04-30). **Raw gap:** 11 commits since the prior CR-cycle SHA-backfill `7b82603`. **Code-touching commits in window:** 2 — `210dcb2` (B-086a — Phase 5 E-043 foundation: alembic `e043a1b2c3d4` adding `jd_text` + `jd_hash` columns to `tracker_applications_v2` + `tracker_application_scores` table; new `app/models/tracker_application_score.py`; new `app/services/analysis_service.py` extracting `score_resume_against_jd` per G-6; new `app/schemas/rescan.py` scaffolds; new ORM-getter sibling `tracker_service_v2.get_application_model_by_id`; closes drift D-020) and `4aab0bf` (B-086b — orchestrator + admin route + UI: new `app/services/tracker_application_score_service.py`; new `POST /api/v1/analyze/rescan` route in `app/api/routes/analyze.py:188`; new `GET /api/v1/tracker/{app_id}/scores` route in `app/api/v1/routes/tracker.py:79`; new `<ScoreDeltaWidget>` (tracker focused-row inline-expand) + new `<HomeScoreDeltaWidget>` (home `interview_prepper` variant below CountdownWidget); new `useScoreHistory` hook + `fetchScoreHistory`/`triggerRescan` api helpers; 4 new PostHog events `rescan_initiated`/`rescan_completed`/`rescan_failed`/`rescan_short_circuited`; cascade-closes B-086 umbrella + E-043). The other 9 commits = E-043 spec-author + §12 amendment + §5.3/§6.1 correction-amendment (D-027 NEW filed at `1b86bf0`) + 4 SHA-backfill / push-watermark cycles. Full-regen scope justified per slice prompt rationale: greenfield feature surface (re-scan loop) + cross-cutting refactor (`score_resume_against_jd` extraction with caller migration) amortizes correctly only with whole-file regen. **Lineage from `691934a`:** `691934a` (B-085 regen) → `7b82603` SHA backfill → `da14c01` E-043 spec-author → `9834abe` SHA backfill → `a02fed5` push-watermark → `71a77e3` E-043 §12 amendment → `b509276` SHA backfill → `210dcb2` **B-086a impl** → `090d4b4` SHA backfill → `1b86bf0` E-043 §5.3/§6.1 corrections (D-027 NEW) → `5dba1bf` SHA backfill → `4aab0bf` **B-086b impl** → `be12717` SHA backfill THIS HEAD. |
| Branch | `main` (last push to `origin/main` at `9834abe` per SESSION-STATE; commits `a02fed5..be12717` queued unpushed; this regen's two commits will queue on top of `be12717`). |
| Generated | 2026-04-30 (full regen at HEAD `<this-slice>`). Raw gap 11 commits with 2 code-touching deltas; full scope justified per slice prompt — **PRD §1.3 core loop closure milestone** (`scan → study → re-scan → improve` is now real product surface; Phase 5 ✅ complete: E-040 + E-041 + E-042 + E-043 all shipped). LD-2: counts via `find` / `wc` enumeration, not estimation. LD-3: ambiguous fields flagged. |
| Backend model files | **26** (`app/models/*.py`, excl. `__init__`, `request_models`, `response_models`). 29 ORM model classes (some files declare 2: `analytics_event.py` → `QuizReviewEvent` + `LessonViewEvent`; `gamification.py` → `GamificationStats` + `Badge` + `UserBadge`; `mission.py` → `Mission` + `MissionDay`). **+1 since `691934a`**: `tracker_application_score.py` (B-086a, `210dcb2`). |
| Backend service files | **48** functional top-level (in `app/services/`, excl. `__init__.py`) + 3 under `services/llm/` + 1 under `app/jobs/` = 52. **+2 top-level since `691934a`**: `analysis_service.py` (B-086a, `210dcb2` — G-6 extraction of `score_resume_against_jd` from in-line `analyze_resume` route handler), `tracker_application_score_service.py` (B-086b, `4aab0bf` — score-history reads/writes + delta math). Service-count basis convention preserved: top-level functional `services/` files form the canonical "service file" count; `services/llm/` (legacy provider abstraction) and `jobs/` are tracked as separate hierarchies in this row. |
| Backend schema files | **19** (`app/schemas/*.py`, excl. `__init__.py`). **+1 since `691934a`**: `rescan.py` (B-086a, `210dcb2`) — 5 Pydantic v2 schemas (`RescanRequest`, `ScoreHistoryEntry`, `ScoreDelta`, `ScoreHistoryResponse`, `ScoreDeltaResponse`). |
| Backend router files | **34** total = 28 v1 + 6 legacy. Unchanged this window (B-086a/b add endpoints to existing routers — `app/api/routes/analyze.py` for `POST /analyze/rescan`, `app/api/v1/routes/tracker.py` for `GET /tracker/{id}/scores`). |
| Backend endpoints | **88 unique decorators** (was 86) across both folders + 7 re-export double-mounts (the v1 thin re-exports of `analyze` / `cover_letter` / `interview` / `rewrite` — `analyze.py` now decorates 3 endpoints: `POST /analyze`, `POST /analyze/rescan`, `GET /analyze/{scan_id}`) = **95 mount-point appearances** (was 92, +3: legacy `POST /api/analyze/rescan` + v1 re-export double-mount `POST /api/v1/analyze/rescan` + v1 native `GET /api/v1/tracker/{app_id}/scores`). |
| Alembic revisions | **29** (Head = `e043a1b2c3d4`). **+1 since `691934a`**: `e043a1b2c3d4_phase5_e043_jd_columns_and_scores_table.py` (B-086a, `210dcb2`; down_revision `c4e21d8a7f12`). |
| Frontend pages | **27** — unchanged since `691934a`. 21 top-level + 6 under `pages/admin/`. (Note: `Tracker.tsx` + `HomeDashboard.tsx` modified by B-086b `4aab0bf` to mount the new widgets, but file count unchanged.) |
| Frontend components | **80** (excl. `__tests__/*`). **+2 since `691934a`** (B-086b, `4aab0bf`): `components/tracker/ScoreDeltaWidget.tsx` + `components/home/widgets/HomeScoreDeltaWidget.tsx`. |
| Frontend utils | **7** utility .ts files in `src/utils/` (unchanged). `services/api.ts` extended with two new helpers in this window: `fetchScoreHistory(trackerApplicationId)` at `:972` + `triggerRescan(...)` at `:981` (B-086b). |
| Shared TS types | `src/types/index.ts` (**~720 lines**, +3 interfaces since `691934a`) + `src/types/homeState.ts` (40 lines, unchanged). **In `index.ts`** B-086b added 3 interfaces at `:134` (`ScoreHistoryEntry`), `:146` (`ScoreDelta`), `:155` (`ScoreHistoryResponse`) — mirror of `app/schemas/rescan.py` Pydantic schemas (FE drops the request/response-envelope-only `RescanRequest` + `ScoreDeltaResponse` since the route returns `AnalysisResponse` directly). |
| Frontend hooks | **19** (`src/hooks/*.ts`, excl. `__tests__`). **+1 since `691934a`**: `useScoreHistory.ts` (B-086b, `4aab0bf` — bare `useState`/`useEffect` pattern matching `useHomeState`; no @tanstack/react-query in this codebase). |
| Frontend context providers | 5 (`AnalysisContext`, `AuthContext`, `GamificationContext`, `ThemeContext`, `UsageContext`) — unchanged. |
| Skills (tracked) | **22** in `.agent/skills/*.md`. Unchanged since `691934a`. `analytics.md` modified by B-086b (`4aab0bf`) — 4 new rescan event rows (`rescan_initiated` / `rescan_completed` / `rescan_short_circuited` / `rescan_failed`) at lines 163–166. Content delta only, not a count change. |
| Skills (untracked) | 3 directory-style under `.agent/skills/` — `stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/` (each contains `SKILL.md` + optional `references/`); not in git, source unknown — see §10. |
| Prompts | `app/prompts/` directory shipped at slice 6.10b — 2 Markdown templates (`lesson_gen.md` + `ingestion_critique.md`). Unchanged this window — B-086a/b add no new prompt files (the LLM call inside `score_resume_against_jd` flows through `app/services/gpt_service.py::generate_job_fit_explanation` which uses inline prompts, not the template loader). |
| Specs | **93 across 7 phases** (phase-0=6, phase-1=13, phase-2=8, phase-3=11, phase-4=6, phase-5=**37**, phase-6=12). **+1 since `691934a`** (phase-5): `63-ats-rescan-loop.md` (E-043 spec-author at `da14c01`; §12 amendment `71a77e3`; §5.3/§6.1 corrections `1b86bf0`). **Numbering anomaly:** phase-5 now has TWO files at slot 63 — the new `63-ats-rescan-loop.md` (E-043) and pre-existing `63-daily-review-preflight-gate.md` (B-059); see §13. |
| Tests | **BE 713** / **FE 428** (carried forward verbatim from B-086b final report). Slice B-086a was BE 692→700 (+8 within +3..+6 forecast over-bound by +2: 4 model smoke + 4 extraction parity); +1 integration test (alembic round-trip, `@pytest.mark.integration`-gated per R13). Slice B-086b was BE 700→713 (+13) and FE 417→428 (+11). 5 D-027 pre-existing failures persist under prod-default env vars (tracking-only, non-blocking; see §11 #27). R14 exception (b) — process slice (CR doc regen), no test runs. BE counts under `FREE_DAILY_REVIEW_LIMIT=10 FREE_LIFETIME_SCAN_LIMIT=1 FREE_MONTHLY_INTERVIEW_LIMIT=3 python -m pytest tests/ -m "not integration"` (canonical CI invocation per `backend.md`). |

**Slice absorption (this regen):** B-086a (Phase 5 E-043 foundation — `210dcb2`; closes drift D-020 + B-086a) and B-086b (Phase 5 E-043 orchestrator + admin route + UI — `4aab0bf`; cascade-closes B-086 umbrella + E-043). Plus context: E-043 spec-author + §12 amendment + §5.3/§6.1 corrections + 4 SHA-backfill / push-watermark process commits.

**Milestone callout — PRD §1.3 core loop closure.** E-043 close at `4aab0bf` seals the PRD core loop: **scan → study → re-scan → improve** is now real product surface. Phase 5 ✅ complete (E-040 admin role + E-041 admin analytics + E-042 tracker-level interview date + E-043 ATS re-scan loop all shipped). The tracker focused-row block now exposes a per-application score-history surface with BE-pre-computed deltas; the home dashboard surfaces a slim variant for `interview_prepper` users keyed off `next_interview.tracker_id`. From this regen forward, the codebase carries the data model + routes + UI to support the "ship resume update → measurable score delta" feedback loop the PRD has called for since Phase 0.

---

## Section 2 — Backend models

All 26 model files under `app/models/` (excl. `__init__`, `request_models`, `response_models`). 29 ORM model classes total (some files declare multiple). Mixins-only file `base.py` excluded from class count. **+1 since `691934a`**: `tracker_application_score.py` (B-086a, `210dcb2`).

### `admin_audit_log.py`
**Class:** `AdminAuditLog` (`app/models/admin_audit_log.py:11`)  **Table:** `admin_audit_log`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | — |
| admin_id | String FK `users.id` ON DELETE RESTRICT, indexed | NOT NULL — forensic guardrail |
| route | String(255) | NOT NULL |
| method | String(10) | NOT NULL |
| query_params | JSONB | NOT NULL, server default `{}` |
| ip_address | String(45) | NOT NULL |
| created_at | DateTime(tz) indexed | server default `now()` |

**Indexes:** `ix_admin_audit_admin_created` `(admin_id, created_at)`, `ix_admin_audit_route_created` `(route, created_at)`. Append-only audit trail written by `core.deps.audit_admin_request` (router-level dep on `/api/v1/admin/*`) and by `auth.py::_log_role_reconciliation` on admin promote/demote events. Spec: `docs/specs/phase-5/38-admin-analytics.md` + `54-admin-email-whitelist.md`.

### `analytics_event.py` (Phase 6 slice 6.0, `e7a0044`)
Two ORM classes in one module per Phase 6 D-8 denormalization (spec `docs/specs/phase-6/00-analytics-tables.md` §4.1 + §4.2; LD I1 dual-write).

**`QuizReviewEvent`** (`app/models/analytics_event.py:31`)  **Table:** `quiz_review_events`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | — |
| user_id | String(36) FK `users.id` ON DELETE SET NULL | nullable *(D-1)* |
| quiz_item_id | String(36) FK `quiz_items.id` ON DELETE CASCADE | NOT NULL |
| lesson_id | String(36) FK `lessons.id` ON DELETE CASCADE | NOT NULL *(D-2/D-8 denormalized)* |
| deck_id | String(36) FK `decks.id` ON DELETE CASCADE | NOT NULL *(denormalized)* |
| rating | Integer | NOT NULL *(py-fsrs Rating: 1=Again..4=Easy)* |
| fsrs_state_before / fsrs_state_after | String(20) | NOT NULL *(ENUM-as-String per slice 6.1 D-3)* |
| reps / lapses | Integer | NOT NULL |
| time_spent_ms | Integer | NOT NULL, default `0` |
| session_id | String(64) | nullable |
| plan / persona | String(20) / String(30) | nullable |
| reviewed_at | DateTime(tz) | server default `now()` |

**Indexes:** four `(content_fk, reviewed_at)` composites — `user`, `quiz_item`, `lesson`, `deck`. Written from `quiz_item_study_service.review_quiz_item` post-flush via `analytics_event_service.write_quiz_review_event`. Best-effort try/except per D-7.

**`LessonViewEvent`** (`app/models/analytics_event.py:107`)  **Table:** `lesson_view_events`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | — |
| user_id | String(36) FK ON DELETE SET NULL | nullable |
| lesson_id | String(36) FK ON DELETE CASCADE | NOT NULL |
| deck_id | String(36) FK ON DELETE CASCADE | NOT NULL |
| version | Integer | NOT NULL *(`lessons.version` snapshot)* |
| session_id / plan / persona | nullable | — |
| viewed_at | DateTime(tz) | server default `now()` |

**Indexes:** three `(content_fk, viewed_at)` composites. Written from `POST /api/v1/lessons/{lesson_id}/view-event` (called best-effort from `pages/Lesson.tsx` `useEffect`).

### `base.py`
**Mixins only:** `Base` (`base.py:9`), `TimestampMixin` (`:14`), `UUIDPrimaryKeyMixin` (`:25`). No models.

### `card.py`
**Class:** `Card` (`app/models/card.py:11`)  **Table:** `cards`

Cols: `id` UUID PK; `category_id` FK; `question`/`answer` Text; `difficulty` String(10); `tags` JSON; `embedding` Vector(1536) nullable; `deleted_at` nullable (soft-delete); `created_at`/`updated_at`. Rel: `category → Category` (back_populates `cards`).

### `card_feedback.py`
**Class:** `CardFeedback` (`app/models/card_feedback.py:10`)  **Table:** `card_feedback`. Cols: `id`, `user_id`, `card_id`, `vote` String(4), `comment` nullable, `created_at`. Rel: `user`, `card`.

### `card_progress.py`
**Class:** `CardProgress` (`app/models/card_progress.py:10`)  **Table:** `card_progress`. FSRS-state per (`user_id`, `card_id`) unique. Cols: `state` default `"new"`, `stability` / `difficulty_fsrs` / `elapsed_days` / `scheduled_days` Float, `reps` / `lapses` Integer, `fsrs_step` nullable, `last_reviewed` nullable, `due_date` default `now()`, timestamps.

### `category.py`
**Class:** `Category` (`app/models/category.py:9`)  **Table:** `categories`. Cols: `id`, `name` unique, `icon`, `color`, `display_order`, `source` nullable (`foundation`/`premium`), `tags` JSONB. Rel: `cards → list[Card]`.

### `deck.py` (Phase 6 slice 6.1, `a989539`)
**Class:** `Deck` (`app/models/deck.py:19`)  **Table:** `decks`. Top-level curriculum bucket replacing `categories` for Phase 6.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | — |
| slug | String(100) unique | NOT NULL |
| title | String(200) | NOT NULL |
| description | Text | NOT NULL |
| display_order | Integer default `0` | server default `"0"` |
| icon | String(10) | nullable |
| persona_visibility | String(20) default `"both"` | ENUM-as-String per D-3: `'climber'`/`'interview_prepper'`/`'both'` |
| tier | String(20) default `"premium"` | ENUM-as-String: `'foundation'`/`'premium'` |
| created_at / updated_at | DateTime(tz) | server defaults |
| archived_at | DateTime(tz) | nullable (soft-delete) |

**Index:** `ix_decks_persona_display_active` `(persona_visibility, display_order) WHERE archived_at IS NULL` — partial index for Learn-page primary query.

**Rel:** `lessons → list[Lesson]` (back_populates, lazy=`select`).

### `email_preference.py`
**Class:** `EmailPreference` (`app/models/email_preference.py:11`)  **Table:** `email_preferences`. Cols: `user_id` PK, `daily_reminder` bool, `timezone`, `unsubscribe_token` unique.

### `gamification.py`
Three classes: `GamificationStats` (`gamification.py:28`), `Badge` (`:57`), `UserBadge` (`:74`). Tables: `gamification_stats` / `badges` / `user_badges`. Streaks/XP/badge progress per user.

### `ingestion_job.py` (Phase 6 slice 6.10a, `9bd9397`)
**Class:** `IngestionJob` (`app/models/ingestion_job.py:34`)  **Table:** `ingestion_jobs`

Status state machine (`pending` / `running` / `generating` / `critiquing` / `publishing` / `completed` / `failed`); R2 key shape `ingestion/{job_id}/{source.md, draft.json, critique.json}`; `source_content_sha256` indexed for slice 6.10b D-5 dedupe; `current_attempt` / `max_attempts` (default 3) per slice 6.10b D-6. Index list: `ix_ingestion_jobs_status_created_at`, `ix_ingestion_jobs_admin_created_at`, plus column-level `index=True` on `source_content_sha256`. Spec: `docs/specs/phase-6/10-ai-ingestion-pipeline.md` §5.3 + §7. Lifecycle: `ingestion_service.enqueue_ingestion` writes the pending row + uploads source to R2 + enqueues an RQ job; `jobs/ingestion_worker.run_ingestion(job_id)` advances `status` per stage. Unchanged this window.

### `interview_question_set.py`
**Class:** `InterviewQuestionSet` (`app/models/interview_question_set.py:16`)  **Table:** `interview_question_sets`. Stores per-user generated interview Q sets.

### `lesson.py` (Phase 6 slice 6.1)
**Class:** `Lesson` (`app/models/lesson.py:32`)  **Table:** `lessons`. Cols: `id`, `deck_id` FK, `slug`, `title`, `concept_md`/`production_md`/`examples_md` Text (3-section body shape per spec #03 D-3), `display_order`, `version` Integer (bumped on substantive edit per slice 6.4 D-17), `published_at` nullable, `archived_at` nullable, timestamps.

### `mission.py`
Two classes: `Mission` (`mission.py:45`), `MissionDay` (`:71`). Interview sprint config + per-day tracking.

### `payment.py`
**Class:** `Payment` (`app/models/payment.py:10`)  **Table:** `payments`. Stripe payment intent records.

### `paywall_dismissal.py`
**Class:** `PaywallDismissal` (`app/models/paywall_dismissal.py:18`)  **Table:** `paywall_dismissals`. Tracks user dismissals for grace-period logic. Spec #42.

### `quiz_item.py` (Phase 6 slice 6.1)
**Class:** `QuizItem` (`app/models/quiz_item.py:32`)  **Table:** `quiz_items`. Cols: `id`, `lesson_id` FK CASCADE, `question` Text, `answer` Text, `question_type` String, `distractors` JSONB nullable (mcq), `difficulty` String, `display_order`, `version`, `retired_at` nullable, timestamps.

### `quiz_item_progress.py` (Phase 6 slice 6.1)
**Class:** `QuizItemProgress` (`app/models/quiz_item_progress.py:28`)  **Table:** `quiz_item_progress`. FSRS-state per (`user_id`, `quiz_item_id`) unique. Mirrors `card_progress` shape; written by `quiz_item_study_service`.

### `registration_log.py`
**Class:** `RegistrationLog` (`app/models/registration_log.py:10`)  **Table:** `registration_logs`. IP-keyed sign-up audit for abuse prevention.

### `resume_model.py`
**Class:** `Resume` (`app/models/resume_model.py:11`)  **Table:** `resumes`. Cols: `id`, `user_id`, `original_content`, `optimized_content`, `template_type`, `embedding` pgvector(1536).

### `stripe_event.py`
**Class:** `StripeEvent` (`app/models/stripe_event.py:10`)  **Table:** `stripe_events`. PK = Stripe `evt_*` id. Webhook idempotency record per spec `43-stripe-webhook-idempotency.md`.

### `subscription.py`
**Class:** `Subscription` (`app/models/subscription.py:10`)  **Table:** `subscriptions`. One row per user (unique FK). Plan/status/Stripe customer/subscription IDs/current_period_end.

### `tracker.py` (extended Phase 5 E-043 / B-086a, `210dcb2`)
**Class:** `TrackerApplicationModel` (`app/models/tracker.py:12`)  **Table:** `tracker_applications_v2`. Per-application job-tracker rows.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | — |
| user_id | String FK `users.id` ON DELETE CASCADE, indexed | nullable (anonymous-usage backward-compat) |
| company / role | String(200) | NOT NULL |
| date_applied | String(20) | NOT NULL |
| ats_score | Integer default `0` | NOT NULL — flipped by `/rescan` to latest `overall_score` per E-043 §4.2 step 8 |
| status | String(20) default `"Applied"` | NOT NULL |
| scan_id | String(36) indexed | nullable; preserved across rescans (the original scan stays the canonical "first scan" anchor for spec #59 rehydration) |
| skills_matched / skills_missing | Text | nullable |
| **`jd_text`** | **Text** | **nullable — NEW B-086a `210dcb2`.** Source of truth for `/rescan` re-scoring. Q1 LOCKED per spec #63 §1.3. NULL on pre-migration rows (no backfill per D-10); D-9 422 path covers the gap when `/rescan` hits a row with `jd_text=NULL`. |
| **`jd_hash`** | **String(64) indexed** | **nullable — NEW B-086a `210dcb2`.** `(jd_hash, resume_hash)` dedupe key for §12 D-2 short-circuit. Indexed via `ix_tracker_apps_jd_hash`. **Closes drift D-020.** |
| interview_date | Date | nullable; spec #57 — per-application interview target. Home countdown selects MIN(interview_date) across the user's active (Applied/Interview) rows; see `home_state_service.get_next_interview`. |
| analysis_payload | JSONB (`deferred()`) | nullable; spec #59 — full `AnalysisResponse` payload for scan re-view. Loaded via `deferred()` so GET /tracker list responses do not inflate (LD-2). Access through `tracker_service_v2.get_scan_by_id` which applies `undefer()`. |
| created_at | DateTime | server default `now()` |

**Rel:** `user` (back_populates `tracker_applications`).

### `tracker_application_score.py` (Phase 5 E-043 / B-086a, `210dcb2`) **— NEW**
**Class:** `TrackerApplicationScore` (`app/models/tracker_application_score.py:19`)  **Table:** `tracker_application_scores`

Append-only event-shape table — no UPDATE/DELETE from application code. One row per re-scan against a tracker application; the tracker row's `ats_score` column carries the "latest snapshot" while this table carries the chronological history.

| Column | Type | Notes |
|--------|------|-------|
| id | String(36) PK | UUID4 stringified |
| tracker_application_id | String(36) FK `tracker_applications_v2.id` ON DELETE CASCADE | NOT NULL — history dies with the tracker row |
| user_id | String(36) FK `users.id` ON DELETE CASCADE | NOT NULL — denormalized FK per D-7 LOCKED; mirrors slice 6.0 `quiz_review_events.user_id` for cross-user analytics queries |
| scan_id | String(36) | nullable, **NO FK** — `scans` table does not exist on disk; matches `tracker_applications_v2.scan_id` shape per JC #2 from B-086a impl |
| overall_score | Integer | NOT NULL — mirrors `AnalysisResponse.ats_score` int |
| keyword_match_score | Float | NOT NULL — from `ATSScoreBreakdown.keyword_match` |
| skills_coverage_score | Float | NOT NULL |
| formatting_compliance_score | Float | NOT NULL |
| bullet_strength_score | Float | NOT NULL |
| jd_hash | String(64) | NOT NULL — §12 D-2 dedupe key (NOT FK; hash string not row ref) |
| resume_hash | String(64) | NOT NULL — §12 D-2 dedupe key |
| scanned_at | DateTime(tz) | NOT NULL, server default `now()` |

**Indexes:** `ix_tas_tracker_app_scanned_at` `(tracker_application_id, scanned_at)` (chronological history fetch), `ix_tas_user_scanned_at` `(user_id, scanned_at)` (admin analytics "avg score improvement"), `ix_tas_dedupe_lookup` `(tracker_application_id, jd_hash, resume_hash)` (D-2 short-circuit lookup). Spec: `docs/specs/phase-5/63-ats-rescan-loop.md` §5.3 (Q2 LOCKED).

**Re-export:** `app/models/__init__.py:8` adds `from app.models.tracker_application_score import TrackerApplicationScore  # noqa: F401`.

### `usage_log.py`
**Class:** `UsageLog` (`app/models/usage_log.py:10`)  **Table:** `usage_logs`. Per-user tokenized feature-use ledger; powers admin analytics. Note: `check_and_increment` short-circuits on `max_uses == -1` (Pro/admin) BEFORE reaching `log_usage` — Pro spend invisible to admin dashboard (D-021c open drift).

### `user.py`
**Class:** `User` (`app/models/user.py:10`)  **Table:** `users`. Cols: `id`, `google_id` unique, `email` unique, `name`, `role` (`user`/`admin`), `persona` (`career_climber`/`interview_prepper`/null), `onboarding_completed`, `interview_target_company`, `interview_target_date` (both deprecated by E-042; FE consumers fully migrated post-`b13f410` — columns remain on disk pending Phase-6 cleanup), `home_first_visit_seen_at` (B-016), timestamps.

---

## Section 3 — Backend routes

### Router-file summary

| File | Mounts | Endpoints | Notes |
|------|--------|-----------|-------|
| `app/api/routes/analyze.py` | `/api` (line 129 `main.py`) + `/api/v1` re-export | **3 endpoints** (was 2): POST `/analyze`, **POST `/analyze/rescan` NEW B-086b**, GET `/analyze/{scan_id}` | Legacy ATS scan + auto-tracker on success + **NEW** re-scan loop. `analyze_resume` post-extraction now calls `score_resume_against_jd` from `app/services/analysis_service.py` per E-043 §6.1 G-6. |
| `app/api/routes/cover_letter.py` | `/api` + `/api/v1` re-export | 1 (POST `/cover-letter`) | Underscore→hyphen drift in AGENTS.md (§11 #1). |
| `app/api/routes/interview.py` | `/api` + `/api/v1` re-export | 1 (POST `/interview-prep`) | Decorator path `/interview-prep` not `/interview` (§11 #1). |
| `app/api/routes/onboarding.py` | `/api/v1` only | 2 (GET, GET) | Persona + recommendations. Mounted from legacy folder (§11 #2). |
| `app/api/routes/payments.py` | `/api/v1` only | 8 | Pricing, checkout, portal, paywall-dismiss, webhook, usage. Mounted from legacy folder (§11 #2). |
| `app/api/routes/rewrite.py` | `/api` + `/api/v1` re-export | 2 (POST `/rewrite`, POST `/rewrite/section`) | Resume rewrite + bullet rewrite. |
| `app/api/v1/routes/admin.py` | `/api/v1` | 8 | Card CRUD + import + AI generate + registration logs + audit. Router-level `audit_admin_request` dep. |
| `app/api/v1/routes/admin_analytics.py` | `/api/v1` | 2 (metrics, performance) | Spec #38 / E-018b. Router-level audit dep. |
| `app/api/v1/routes/admin_decks.py` | `/api/v1` | 4 (POST/PATCH/POST archive/GET list) | Phase 6 slice 6.4b. Router-level audit dep. |
| `app/api/v1/routes/admin_ingest.py` | `/api/v1` | 3 (POST `/admin/ingest`, GET `/admin/ingest/{id}`, GET `/admin/ingest`) | Phase 6 slice 6.10b (`8735373`). Router-level `audit_admin_request` dep + per-handler `Depends(require_admin)`. Custom slowapi `@limiter.limit("10/hour", key_func=_admin_rate_key)` on POST per spec #10 D-8 (per-admin not per-IP). |
| `app/api/v1/routes/admin_lessons.py` | `/api/v1` | 5 (POST/GET/PATCH/POST publish/POST archive) | Slice 6.4b. Audit dep. |
| `app/api/v1/routes/admin_quiz_items.py` | `/api/v1` | 4 | Slice 6.4b. Audit dep. |
| `app/api/v1/routes/analyze.py` | `/api/v1` | (re-export) | Thin re-export of `app/api/routes/analyze.py`. **Now re-exports 3 endpoints** (was 2) per the new POST `/analyze/rescan` decorator on the legacy file. |
| `app/api/v1/routes/auth.py` | `/api/v1` | 4 (Google login, refresh, logout, me) | Auth router; ungated. |
| `app/api/v1/routes/cards.py` | `/api/v1` | 4 (list, search, by-category, by-id) | User-facing card reads. |
| `app/api/v1/routes/cover_letter.py` | `/api/v1` | (re-export) | Re-export of legacy. |
| `app/api/v1/routes/dashboard.py` | `/api/v1` | 1 (GET `/learn/dashboard`) | Slice 6.8 (`0968a13`). User-self FSRS dashboard. Query param `?retention_window_days=N` range [1, 365], default 30. |
| `app/api/v1/routes/decks.py` | `/api/v1` | 2 (list, by-id) | Phase 6 slice 6.3. |
| `app/api/v1/routes/email_prefs.py` | `/api/v1` | 2 (GET, PUT) | Mounted at `/email-preferences`; AGENTS.md table says `/email-prefs` (§11 #7 drift). |
| `app/api/v1/routes/feedback.py` | `/api/v1` | 3 (POST + 2 admin) | NPS + card feedback. |
| `app/api/v1/routes/gamification.py` | `/api/v1` | 1 (GET stats) | Streaks/XP/badges read. |
| `app/api/v1/routes/home.py` | `/api/v1` | 1 (GET state) | State-aware home dashboard payload. Spec #40. |
| `app/api/v1/routes/interview.py` | `/api/v1` | (re-export) | Re-export. |
| `app/api/v1/routes/lesson_view_events.py` | `/api/v1` | 1 (POST `/lessons/{id}/view-event`) | Phase 6 slice 6.0 dual-write. 204 fire-and-forget. |
| `app/api/v1/routes/lessons.py` | `/api/v1` | 1 (GET by-id with quizzes) | Slice 6.3. |
| `app/api/v1/routes/mission.py` | `/api/v1` | 4 | Mission CRUD + active + daily. AGENTS.md says singular `/mission`; actual decorators are plural `/missions/*` (§11 #4). |
| `app/api/v1/routes/progress.py` | `/api/v1` | 2 (radar, heatmap) | Skill radar + activity heatmap. |
| `app/api/v1/routes/quiz_items.py` | `/api/v1` | 3 (daily, review, progress) | Slice 6.2. FSRS quiz-item study. |
| `app/api/v1/routes/ranker.py` | `/api/v1` | 1 (GET `/learn/ranked-decks`) | Slice 6.6 (`5011518`). Lens-ranked deck ordering. |
| `app/api/v1/routes/resume.py` | `/api/v1` | 4 (upload, optimize, get, diff) | Resume storage + AI optimize. |
| `app/api/v1/routes/rewrite.py` | `/api/v1` | (re-export) | Re-export. |
| `app/api/v1/routes/study.py` | `/api/v1` | 4 (daily queue, review, status, dismiss) | FSRS daily card study. |
| `app/api/v1/routes/tracker.py` | `/api/v1` | **5 endpoints** (was 4): list, create, patch, delete, **GET `/tracker/{app_id}/scores` NEW B-086b** | Application tracker CRUD + score history read. New endpoint at `tracker.py:79`. |
| `app/api/v1/routes/users.py` | `/api/v1` | 2 (PATCH persona, POST home-first-visit) | User profile mutations. |

### Flat endpoint table (mount-point convention; **95** appearances)

Listed in router-file order. Re-export double-mounts marked with `[2x]`. Files with explicit decorators in `app/api/routes/` are listed once at `/api/...` and once at `/api/v1/...` per `main.py:135-170` mount.

Legacy `/api/*` (4 files double-mounted at `/api/v1/*` via re-export, +`onboarding`/`payments` mounted only at `/api/v1`):

| Method + Path | File:Line |
|---|---|
| POST `/api/analyze` `[2x]` | `app/api/routes/analyze.py:41` |
| **POST `/api/analyze/rescan`** `[2x]` **NEW B-086b** | `app/api/routes/analyze.py:188` |
| GET `/api/analyze/{scan_id}` `[2x]` | `app/api/routes/analyze.py:370` |
| POST `/api/cover-letter` `[2x]` | `app/api/routes/cover_letter.py:22` |
| POST `/api/interview-prep` `[2x]` | `app/api/routes/interview.py:17` |
| POST `/api/rewrite` `[2x]` | `app/api/routes/rewrite.py:94` |
| POST `/api/rewrite/section` `[2x]` | `app/api/routes/rewrite.py:191` |
| GET `/api/v1/onboarding/...` (×2) | `app/api/routes/onboarding.py:60`, `:90` |
| GET `/api/v1/payments/pricing` | `app/api/routes/payments.py:61` |
| POST `/api/v1/payments/checkout` | `app/api/routes/payments.py:69` |
| POST `/api/v1/payments/portal` | `app/api/routes/payments.py:96` |
| POST `/api/v1/payments/paywall-dismiss` | `app/api/routes/payments.py:167` |
| GET `/api/v1/payments/...` | `app/api/routes/payments.py:200` |
| GET `/api/v1/payments/usage` | `app/api/routes/payments.py:225` |
| POST `/api/v1/payments/webhook` | `app/api/routes/payments.py:241` |

v1 `/api/v1/*` (alphabetical by file):

| Method + Path | File:Line |
|---|---|
| GET `/api/v1/admin/ping` | `admin.py:70` |
| GET `/api/v1/admin/cards` | `admin.py:76` |
| POST `/api/v1/admin/cards` | `admin.py:93` |
| PUT `/api/v1/admin/cards/{card_id}` | `admin.py:106` |
| DELETE `/api/v1/admin/cards/{card_id}` | `admin.py:116` |
| POST `/api/v1/admin/cards/import` | `admin.py:125` |
| POST `/api/v1/admin/cards/generate` | `admin.py:136` |
| GET `/api/v1/admin/registration-logs` | `admin.py:146` |
| GET `/api/v1/admin/audit` | `admin.py:206` |
| GET `/api/v1/admin/analytics/metrics` | `admin_analytics.py:53` |
| GET `/api/v1/admin/analytics/performance` | `admin_analytics.py:83` |
| POST `/api/v1/admin/decks` | `admin_decks.py:28` |
| PATCH `/api/v1/admin/decks/{deck_id}` | `admin_decks.py:47` |
| POST `/api/v1/admin/decks/{deck_id}/archive` | `admin_decks.py:67` |
| GET `/api/v1/admin/decks` | `admin_decks.py:81` |
| POST `/api/v1/admin/ingest` | `admin_ingest.py:65` |
| GET `/api/v1/admin/ingest/{job_id}` | `admin_ingest.py:91` |
| GET `/api/v1/admin/ingest` | `admin_ingest.py:111` |
| POST `/api/v1/admin/lessons` | `admin_lessons.py:35` |
| GET `/api/v1/admin/lessons` | `admin_lessons.py:61` |
| PATCH `/api/v1/admin/lessons/{lesson_id}` | `admin_lessons.py:85` |
| POST `/api/v1/admin/lessons/{lesson_id}/publish` | `admin_lessons.py:119` |
| POST `/api/v1/admin/lessons/{lesson_id}/archive` | `admin_lessons.py:140` |
| POST `/api/v1/admin/lessons/{lesson_id}/quiz-items` | `admin_quiz_items.py:41` |
| GET `/api/v1/admin/lessons/{lesson_id}/quiz-items` | `admin_quiz_items.py:67` |
| PATCH `/api/v1/admin/quiz-items/{quiz_item_id}` | `admin_quiz_items.py:90` |
| POST `/api/v1/admin/quiz-items/{quiz_item_id}/retire` | `admin_quiz_items.py:119` |
| POST `/api/v1/auth/google` | `auth.py:96` |
| POST `/api/v1/auth/refresh` | `auth.py:234` |
| POST `/api/v1/auth/logout` | `auth.py:249` |
| GET `/api/v1/auth/me` | `auth.py:256` |
| GET `/api/v1/cards` | `cards.py:18` |
| GET `/api/v1/cards/search` | `cards.py:27` |
| GET `/api/v1/cards/category/{category_id}` | `cards.py:39` |
| GET `/api/v1/cards/{card_id}` | `cards.py:61` |
| GET `/api/v1/decks` | `decks.py:25` |
| GET `/api/v1/decks/{deck_id}` | `decks.py:50` |
| GET `/api/v1/email-preferences` | `email_prefs.py:66` |
| PUT `/api/v1/email-preferences` | `email_prefs.py:79` |
| POST `/api/v1/feedback` | `feedback.py:55` |
| GET `/api/v1/admin/feedback` | `feedback.py:102` |
| GET `/api/v1/admin/feedback/summary` | `feedback.py:144` |
| GET `/api/v1/gamification/stats` | `gamification.py:50` |
| GET `/api/v1/home` | `home.py:14` |
| POST `/api/v1/lessons/{lesson_id}/view-event` | `lesson_view_events.py:37` |
| GET `/api/v1/lessons/{lesson_id}` | `lessons.py:24` |
| POST `/api/v1/missions/create` | `mission.py:52` |
| GET `/api/v1/missions/active` | `mission.py:84` |
| GET `/api/v1/missions/daily` | `mission.py:130` |
| POST `/api/v1/missions/complete-day` | `mission.py:167` |
| GET `/api/v1/progress/radar` | `progress.py:22` |
| GET `/api/v1/progress/heatmap` | `progress.py:41` |
| GET `/api/v1/quiz-items/daily` | `quiz_items.py:28` |
| POST `/api/v1/quiz-items/review` | `quiz_items.py:54` |
| GET `/api/v1/quiz-items/progress` | `quiz_items.py:111` |
| GET `/api/v1/learn/dashboard` | `dashboard.py:28` |
| GET `/api/v1/learn/ranked-decks` | `ranker.py:27` |
| POST `/api/v1/resume/upload` | `resume.py:21` |
| POST `/api/v1/resume/{resume_id}/optimize` | `resume.py:66` |
| GET `/api/v1/resume/{resume_id}` | `resume.py:119` |
| GET `/api/v1/resume/{resume_id}/diff` | `resume.py:143` |
| GET `/api/v1/study/...` (×2) | `study.py:51`, `:128` |
| POST `/api/v1/study/...` (×2) | `study.py:77`, `:159` |
| GET `/api/v1/tracker` | `tracker.py:28` |
| POST `/api/v1/tracker` | `tracker.py:37` |
| PATCH `/api/v1/tracker/{app_id}` | `tracker.py:51` |
| DELETE `/api/v1/tracker/{app_id}` | `tracker.py:66` |
| **GET `/api/v1/tracker/{app_id}/scores`** **NEW B-086b** | `tracker.py:79` |
| PATCH `/api/v1/users/me/persona` | `users.py:74` |
| POST `/api/v1/users/me/home-first-visit` | `users.py:108` |

App factory at `app/main.py:62` — middleware stack: Sentry init (line 66), CORS (line 87), request-size limit (line 95), slowapi rate limit (line 82). Health check at `/health` (line 123).

### `POST /api/v1/analyze/rescan` (NEW B-086b — E-043 §6.2 orchestrator)

`app/api/routes/analyze.py:188` (decorated on the legacy router; double-mounted at `/api/v1/analyze/rescan` via `app/api/v1/routes/analyze.py` thin re-export). Auth: `Depends(get_current_user)` REQUIRED (NOT optional like the legacy `/analyze` upload path) — re-scan is by definition a user-owned operation against a tracker row. Slowapi default rate limit (100/min) inherits per §12 D-8 (no per-route override).

Flow (handler lines `:213–367`):

1. **Ownership read** — `get_application_model_by_id(request.tracker_application_id, db, user_id=current_user.id)` (ORM-getter sibling — see §4 disk-reality note); 404 with `{error: "tracker_not_found"}` on miss.
2. **D-9 422** — `if row.jd_text is None: raise HTTPException(422, {error: "jd_text_missing", message: "JD text not stored on this tracker — please run a fresh scan to populate."})`.
3. **D-2 dedupe short-circuit** — `resume_hash = hash_jd(request.resume_text); jd_hash = row.jd_hash or hash_jd(row.jd_text); existing = find_by_dedupe(...)`; on hit, fire `rescan_short_circuited{tracker_application_id, jd_hash_prefix: jd_hash[:8]}` and return synthesized `AnalysisResponse` from the existing row's per-axis floats; **counter is NOT consumed**.
4. **G-7 counter** — `usage = await check_and_increment(current_user.id, "analyze", db, window="lifetime")`; on `not allowed`, raise 402 with `{error: "free_tier_limit", trigger: "scan_limit", scans_used, scans_limit, plan}` (mirrors spec #50 / spec #56 free-tier-limit envelope verbatim).
5. **`rescan_initiated`** event — fired between counter pass and LLM call.
6. **Score** — `score_resume_against_jd(resume_text, jd_text, db, user_id, prior_scan_id=row.scan_id)` from `app/services/analysis_service.py`; `parsed_resume=None` (text-only path; degraded formatting + bullet analysis per spec G-6). On exception → fire `rescan_failed{tracker_application_id, error_class: "scoring_error"}` + raise 502 with `{error: "scoring_failed"}`; **counter is NOT consumed** (request rolls back via auto-rollback on exception under `get_db()`).
7. **Persist** — `write_score_row(...)` then `row.ats_score = response.ats_score` (transactional within the same session; `get_db()` auto-commits on success, no explicit `db.commit()` in the handler).
8. **`rescan_completed`** event — full per-axis delta envelope per §12 D-12: `{tracker_application_id, scan_id, jd_hash, ats_score_before, ats_score_after, ats_score_delta, keyword_match_delta, skills_coverage_delta, formatting_compliance_delta, bullet_strength_delta, short_circuited: false}`. Pre-computed values from `compute_delta(history)` — None on cold-start (single history row).
9. **Return** — fresh `AnalysisResponse` (same shape as `/analyze`).

### `GET /api/v1/tracker/{app_id}/scores` (NEW B-086b — E-043 §6.4 history read)

`app/api/v1/routes/tracker.py:79`. Auth: `Depends(get_current_user)`; ownership-enforced via `get_application_model_by_id` (404 on miss / cross-user). Returns `ScoreHistoryResponse {tracker_application_id, history: ScoreHistoryEntry[], delta: ScoreDelta | null}`. History is chronological (oldest-first) per §12 D-3; no pagination v1; bounded to ~20 rows in practice. `delta` is None when `len(history) < 2` (cold-start / first-scan baseline).

---

## Section 4 — Backend services

### Top-level `app/services/` (48 files)

| File | Public surface | Notes |
|------|----------------|-------|
| `admin_analytics_service.py` | `compute_metrics`, `compute_performance` | Spec #38 admin dashboard. Maps `usage_logs` → token spend × `TIER_PRICE_USD_PER_1M_TOKENS` (in `llm_router.py`). Read-only. |
| `admin_errors.py` | `AdminWriteError`, `EditClassificationError` | Phase 6 slice 6.4b error envelopes. |
| `ai_card_service.py` | `generate_card_drafts` | AI-assisted admin card generation. Uses `generate_for_task(task="card_draft", ...)`. |
| `ai_service.py` | `generate_resume_optimization` | Enterprise-only path; **duplicates** `gpt_service.py` public API verbatim. `[S47-defer]`. |
| `analytics_event_service.py` | `write_quiz_review_event`, `write_lesson_view_event` | Slice 6.0 append-only writers (no UPDATE/DELETE per AC-10). Best-effort (try/except wraps caller). |
| **`analysis_service.py`** **NEW B-086a (`210dcb2`)** | `score_resume_against_jd(resume_text, jd_text, db, *, user_id=None, prior_scan_id=None, parsed_resume=None) -> AnalysisResponse:40` | Phase 5 E-043 §6.1 G-6 extraction. Lifts the file-format-agnostic scoring half from the in-line `analyze_resume` route handler so both `/analyze` (file-upload entry, threads `parsed_resume` from `parse_pdf`/`parse_docx`) and `/rescan` (B-086b text-only entry, `parsed_resume=None`) share the same pipeline. AC-17 byte-identity invariant: `/analyze` post-extraction produces the same `AnalysisResponse` as the pre-extraction inline code path; the optional `parsed_resume` kwarg threads file-derived `formatting_hints` + `bullet_points` through. Mints a fresh `scan_id` (UUID4) inside the helper; `prior_scan_id` accepted for B-086b telemetry threading but unused in v1. Module-level `_scorer = ATSScorer()` (singleton instance reused across calls). Inside the helper: `extract_skills` → `extract_job_requirements` → `match_keywords` → `check_formatting` → `analyze_bullets` → `_scorer.score(...)` → `detect_gaps` → `get_skills_overlap_data` → `get_keyword_chart_data` → optional `gpt_service.generate_job_fit_explanation` (try/except with deterministic fallback prose) → fire `ats_scanned` PostHog event. Returns the constructed `AnalysisResponse(scan_id, ats_score, grade, score_breakdown=ATSScoreBreakdown(...), matched_keywords, missing_keywords, skill_gaps, bullet_analysis, formatting_issues, job_fit_explanation, top_strengths, top_gaps, keyword_chart_data, skills_overlap_data, resume_text)`. |
| `bullet_analyzer.py` | `analyze_bullets` | Per-bullet ATS analyzer. |
| `card_admin_service.py` | Card CRUD + import | Backed by `admin.py`. |
| `card_service.py` | Read-side card lookup, search, category bundles. |  |
| `curriculum_visibility.py` (slice 6.6) | `_persona_visible_to:30`, `_visible_persona_set:45`, `_resolve_plan:56`, `_allowed_tiers_for_user:77` | Extracted from `lesson_service` per slice 6.5 D-5 escape hatch (rule-of-three, slice 6.6 D-6). Re-used by slice 6.8 `dashboard_service` for D-10 free-vs-premium deck filtering. |
| `dashboard_service.py` (slice 6.8) | `aggregate_user_dashboard:77` (public) + 7 private `_aggregate_*` helpers | User-self FSRS dashboard aggregator. Reuses `curriculum_visibility` helpers (D-10), `gamification_service.get_stats` (no streak math re-derivation), `email_preferences.timezone` for D-6 user-local date bucketing. Reads-only across `quiz_item_progress` + `quiz_review_events` + `lesson_view_events` + `decks` + `lessons` + `quiz_items` + `gamification_stats`. Constants: `MAX_RECENT_REVIEWS = 20`, `MASTERY_REPS_THRESHOLD = 3`, `_RECALL_RATINGS = (3, 4)`, `DEFAULT_RETENTION_WINDOW_DAYS = 30`. |
| `deck_admin_service.py` | Deck CRUD | Slice 6.4b admin authoring. |
| `deck_ranker_service.py` (slice 6.6) | `get_recent_skill_gaps:85`, `rank_decks_for_user:169`, helpers | Lens-ranked deck ordering. Aggregates skill gaps from `tracker_applications_v2.analysis_payload` (D-14 defaults: 30 days / 5 scans). 4 signals at default weights 0.55/0.25/0.10/0.10. |
| `email_service.py` | `send_email` (Resend wrapper) | Spec #15 daily reminders. |
| `experience_service.py` | `generate_experience_narrative` | Spec #22 "My Experience". |
| `formatter_check.py` | `check_formatting` | ATS formatting linter. (Note: `find_formatting_issues` was the prior export name; current API exports `check_formatting`.) |
| `gamification_service.py` | Streak, XP, badge updates | Server-side FSRS-adjacent gamification. |
| `gap_detector.py` | `detect_gaps`, `get_skills_overlap_data` | Resume-vs-JD skill diff. |
| `gap_mapping_service.py` | Map ATS gaps → study cards | Spec ats-card-bridge. |
| `geo_pricing_service.py` | `get_pricing_for_ip` | IP→country→Stripe price ID. Redis cached. |
| `gpt_service.py` | `generate_resume_rewrite`, `generate_resume_rewrite_async`, `generate_cover_letter`, `generate_interview_questions`, `generate_job_fit_explanation` | Returns `Tuple[X, telemetry_str]` for rewrite calls (D-014 open). All LLM calls via `generate_for_task()`. **Now consumed by `analysis_service.score_resume_against_jd`** for the job-fit explanation step (carried over from the in-line route handler — same call shape, same try/except fallback prose). |
| `home_state_service.py` | `compute_home_state`, `invalidate(user_id)` | Spec #40 priority slot evaluator. Redis cached with invalidation hooks. Includes `next_interview` envelope on `HomeStateContext` (E-042). Invalidation hooks fired by `tracker.py` create/patch/delete handlers; `/rescan` does NOT invalidate (the rescan flow does not change `next_interview` selection — interview_date column is independent of jd_text/jd_hash/ats_score). |
| `ingestion_errors.py` (slice 6.10b) | `IngestionPayloadError` (400) / `IngestionRateLimitedError` (429) / `R2UploadError` (502) / `IngestionJobNotFoundError` (404) | Domain error envelopes for the ingestion pipeline. |
| `ingestion_service.py` (slice 6.10b) | `enqueue_ingestion:165` (public), `get_ingestion_job:253`, `list_recent_ingestion_jobs:266`, helpers | Module constants `INGESTION_JOB_TIMEOUT_SECONDS=600` + `INGESTION_MAX_ATTEMPTS=3` + `INGESTION_BACKOFF_SCHEDULE=[5,15,45]`. Dedupe via `source_content_sha256` + active-status window. |
| `interview_storage_service.py` | Interview Q set persistence | Uses `text_hash.hash_jd` (now one of TWO call sites — see hashing-helper note below). |
| `keywords.py` | `match_keywords`, `get_keyword_chart_data` | TF-IDF / RAKE keyword extraction. |
| `lesson_admin_service.py` | Lesson CRUD + publish + archive | Slice 6.4b. |
| `lesson_service.py` | `get_lesson_with_quizzes`, `get_deck_with_meta`, `list_lessons_in_deck`, `get_deck_lessons_bundle` | Phase 6 lesson reads. Slice 6.5 (B-072) added persona-narrowing filters per spec #06 §6.2. |
| `mission_service.py` | Mission CRUD + active + daily card pull. |  |
| `nlp.py` | `extract_skills`, `extract_job_requirements` | spaCy wrapper utilities. |
| `object_storage_service.py` (slice 6.10a) | `ObjectStorageService:40` class, `ObjectStorageError:31`, `get_storage:87` factory | R2 (Cloudflare) artifacts adapter. |
| `onboarding_checklist_service.py` | First-action checklist computation. |  |
| `parser.py` | `parse_pdf`, `parse_docx` | PDF/DOCX → text extraction (returns dict with `full_text`, `formatting_hints`, `bullet_points`). |
| `payment_service.py` | Stripe checkout/portal/webhook handling. |  |
| `paywall_service.py` | Paywall dismissal grace logic. Spec #42. |  |
| `progress_service.py` | Radar + heatmap aggregation. |  |
| `prompt_template_service.py` (slice 6.10b) | `load_prompt(name) → str` | Reads `app/prompts/{name}.md` via `Path.read_text()` + `@functools.cache`. |
| `quiz_item_admin_service.py` | Quiz-item CRUD + retire | Slice 6.4b. |
| `quiz_item_study_service.py` | `get_daily_quiz_items`, `review_quiz_item`, `get_quiz_progress` | Slice 6.2 FSRS quiz-item study. |
| `reminder_service.py` | Daily-reminder send-time computation. |  |
| `resume_templates.py` | Template metadata. |  |
| `scorer.py` | `ATSScorer` class with `.score(...)` method | ATS scoring algorithms. Module-instantiated singleton in `analysis_service`. |
| `seed_lessons_service.py` | `load_seed_corpus(db, *, dry_run=False, seed_root=None) → SeedLoadReport` | Slice 6.4.5. Idempotent UPSERT loader (savepoint-protected per D-10). |
| `study_service.py` | FSRS daily-card surface for `card_progress`. Pre-Phase-6 study path. |  |
| **`tracker_application_score_service.py`** **NEW B-086b (`4aab0bf`)** | `write_score_row:34`, `find_by_dedupe:72`, `get_score_history:100`, `compute_delta:126`, `to_history_entry:157`, `get_prior_overall_score:171`, `update_tracker_ats_score:209` | Phase 5 E-043 §6.3 score-history reads/writes + delta math. **Append-only event-shape table** per §4.4 of the spec — no UPDATE/DELETE from application code; rows cascade with their owning tracker row / user. All public functions are tenant-scoped (`_require_user_id` guard); a `None` user_id raises `ValueError` rather than silently producing cross-tenant results. **Field-name mapping** (per JC #1 disk-truth from B-086a impl): per-axis floats from `response.score_breakdown` (`keyword_match` / `skills_coverage` / `formatting_compliance` / `bullet_strength`) land on the `*_score` columns; `response.ats_score` (int) lands on `overall_score`. **`compute_delta`** is a pure helper — returns None when `len(history) < 2`; works on the chronological (oldest-first) list returned by `get_score_history`; latest=`history[-1]`, prev=`history[-2]`; `days_between = max(0, (latest.scanned_at - prev.scanned_at).days)`. `find_by_dedupe` orders by `scanned_at DESC limit 1` for §12 D-2 short-circuit. `get_prior_overall_score(tracker_application_id, before)` returns the most recent `overall_score` strictly before the given timestamp — used by the `/rescan` handler to thread `ats_score_before` into the `rescan_completed` event payload. `update_tracker_ats_score(tracker, new_score)` flips `tracker.ats_score = new_score` (no commit; relies on caller's session auto-commit). |
| `tracker_service_v2.py` | `create_application` (extended jd_text/jd_hash kwargs), `find_by_scan_id`, `get_applications`, `get_application_by_id` (Pydantic), **`get_application_model_by_id`** (ORM, NEW B-086b at `:172`), `get_scan_by_id` (ORM with `undefer(analysis_payload)`), `update_application`, `delete_application` | Tracker CRUD; auto-tracker-on-scan-success hook. **§6.2 disk-reality artifacts** — see service-layer conventions below. |
| `usage_service.py` | `check_and_increment`, `log_usage`, `PLAN_LIMITS` dict | Source of truth for free-tier caps. Short-circuit at `max_uses == -1` for Pro/admin (D-021c open). The `/rescan` handler uses `feature="analyze"` + `window="lifetime"` (G-7 counter reuse — the same lifetime budget guards both fresh scans and re-scans per §12 D-1). |
| `user_service.py` | `reconcile_admin_role` (E-040 spec #54), persona PATCH, etc. |  |

### `app/services/llm/` (legacy provider factory — do not extend)

| File | Notes |
|------|-------|
| `factory.py` | `get_llm_provider()` legacy abstraction; do NOT import from service code. Phase-6 consolidation pending. |
| `claude_provider.py`, `gemini_provider.py` | Legacy provider wrappers. |

### `app/jobs/` (slice 6.10a / 6.10b)

| File | Notes |
|------|-------|
| `__init__.py` | Slice 6.10a (`9bd9397`) package marker. |
| `ingestion_worker.py` (slice 6.10b) | `run_ingestion(job_id) → None:518` RQ entry point. Three-stage pipeline (generate → critique → persist) per spec §6.2. |

### LLM router

`app/core/llm_router.py:1`. `generate_for_task(task, prompt, ..., provider_override=None, response_schema=None)` dispatches on `FAST_TASKS` / `REASONING_TASKS` frozensets. Provider chosen from `LLM_FAST_PROVIDER` / `LLM_REASONING_PROVIDER` env, or directly from `provider_override` when supplied (slice 6.10a D-14). `response_schema: Optional[Type[BaseModel]]` plumbs into `types.GenerateContentConfig(response_schema=...)` on the Gemini path (slice 6.10a, closed drift D-016). `TIER_PRICE_USD_PER_1M_TOKENS` constant feeds admin spend.

### `tracker_service_v2` §6.2 disk-reality artifacts (Phase 5 E-043 conventions)

The B-086b orchestrator forced three convention crystallizations worth surfacing here verbatim — they ARE the ground truth going forward:

1. **Pydantic-firewall on tracker reads** — `get_application_by_id(app_id, db, user_id) → Optional[TrackerApplication]:155` returns the Pydantic `TrackerApplication` summary (defined in `app/schemas/responses.py`), which **deliberately omits** `jd_text` and `jd_hash` (full JD body would inflate list responses if every read leaked it). Used by handlers that only need company/role/status/ats_score/scan_id/skills/interview_date.

2. **Sibling ORM-getter for write-path/read-detail** — `get_application_model_by_id(app_id, db, user_id) → Optional[TrackerApplicationModel]:172` returns the SQLAlchemy ORM row (mirrors `get_scan_by_id:99` shape). Used by handlers that need direct column access — including `jd_text` / `jd_hash` for `/rescan` re-scoring (`app/api/routes/analyze.py:214`) and the `/scores` history read (`app/api/v1/routes/tracker.py:93`). Both reads enforce ownership by matching `user_id`; rows owned by other users return None (→ 404 at the route, not 403, per spec #59 LD-4).

3. **Service-flush-only commit convention** — neither `tracker_service_v2` nor `tracker_application_score_service` calls `db.commit()` explicitly in any function. Service writers use `db.flush()` + `db.refresh()` only; route handlers do not call `db.commit()` either. The `get_db()` dependency in `app/db/session.py` auto-commits on success (and auto-rollbacks on exception). Test fixtures rely on this for rollback isolation between tests. The `/rescan` handler at `app/api/routes/analyze.py:188` is the canonical reference: `write_score_row` flushes, `row.ats_score = response.ats_score` is a session-attached attribute write, and the handler returns the response — `get_db()` commits once after the handler returns successfully.

### Hashing helper convention

`app/utils/text_hash.py:16` — `hash_jd(text: str) -> str`. Internal pipeline: `_normalize_jd(text)` collapses whitespace + casefolds + strips, then `hashlib.sha256(...).hexdigest()`. **No standalone `sha256_hex` helper exists.** Both `interview_storage_service` (spec #49 — sole pre-existing consumer) and the new `/rescan` handler call `hash_jd` directly. The `/rescan` handler hashes both the resume text and (when needed) the JD text via the same `hash_jd` function — the `_normalize_jd` step is benign for non-JD text (collapsing whitespace + casefolding never produces hash collisions; the function's name is documentation, not a content-type assertion).

### CLI / scripts

- `app/scripts/seed_phase6.py` — `python -m app.scripts.seed_phase6 [--dry-run] [--seed-root PATH]`. Loads `app/data/decks/seed_lessons/<slug>/{_meta.md, *.md}` corpus via `seed_lessons_service.load_seed_corpus`. Slice 6.4.5.

---

## Section 5 — Alembic revisions

**29 revisions** in `hirelens-backend/alembic/versions/`. Linear chain. **Head: `e043a1b2c3d4`**.

| Revision | Summary | Down-revision |
|---|---|---|
| `0001_initial_postgres_pgvector` | Initial PG+pgvector schema | None (root) |
| `02bf7265b387` | Rename `users.target_*` → `interview_target_*` | (chain) |
| `1176cc179bf0` | Add `paywall_dismissals` + user paywall fields | (chain) |
| `30bf39fa04f8` | Add `analysis_payload` JSONB to `tracker_applications_v2` | (chain) |
| `508df0110037` | Add `users.home_first_visit_seen_at` (B-016) | (chain) |
| `9543aa466524` | Add `tracker_applications_v2.interview_date` (E-042 BE) | (chain) |
| `eb59d4fc1f7e` | Backfill `tracker_applications_v2.interview_date` from users | `9543aa466524` |
| `ed902312e4ac` | Add `users.role` column (admin role) | (chain) |
| `f3350dcba3a5` | Add `interview_question_sets` table | (chain) |
| `f75789e4967f` | Add `registration_logs` table | (chain) |
| `fdc5af6f825f` | Add `card_progress.fsrs_step` | (chain) |
| `57951e9f4cdc` | Phase 6 slice 6.1 — `decks` + `lessons` + `quiz_items` + `quiz_item_progress` | (chain) |
| `b8a9d4f3e2c1` | Phase 6 slice 6.0 — `quiz_review_events` + `lesson_view_events` | `57951e9f4cdc` |
| `c4e21d8a7f12` | Phase 6 slice 6.10a — `ingestion_jobs` table | `b8a9d4f3e2c1` |
| **`e043a1b2c3d4`** | **Phase 5 E-043 / B-086a — `jd_text` + `jd_hash` columns on `tracker_applications_v2` + `ix_tracker_apps_jd_hash` (Q1 LOCK; closes drift D-020) AND `tracker_application_scores` table + 3 indexes (Q2 LOCK) (HEAD)** | `c4e21d8a7f12` |

(Other 14 revisions are middle-of-chain Phase 1–5 migrations. Full enumeration via `ls hirelens-backend/alembic/versions/*.py`.)

The `e043a1b2c3d4` migration bundles two locked decisions per spec #63 §1.3 + §7. Both nullable per D-10 (no backfill of pre-migration rows; the `/rescan` route returns 422 with explicit copy when `jd_text=NULL` per D-9). FK shapes per spec §5.3:

- `tracker_application_id` → `tracker_applications_v2.id` ON DELETE **CASCADE** (history dies with the tracker row).
- `user_id` → `users.id` ON DELETE **CASCADE** (denormalized FK, mirrors slice 6.0 D-1 / D-7 convention).
- `scan_id` carries no FK on disk because no `scans` table exists (matches the `tracker_applications_v2.scan_id` shape — see B-086a JC #2).

**AC-12 / AC-15 verification:** alembic round-trip clean (`upgrade head → downgrade -1 → upgrade head`); column presence + index presence verified shell-side at B-086a impl close. Integration test `tests/test_e043_jd_columns_migration.py` (single test, `@pytest.mark.integration`-gated per R13) covers the round-trip in CI.

CI migration-rollback job at `.github/workflows/ci.yml:101-149` runs `alembic upgrade head` → `downgrade -1` → `upgrade head` to verify reversibility on every push.

---

## Section 6 — Frontend routes (live component graph)

Routes declared in `src/App.tsx:78-138`. Public + protected, with namespace migration (`/learn/*` study + `/prep/*` interview prep) and transitional `<Navigate replace>` shims. Unchanged this window — B-086b mounts new widgets inside existing pages (`Tracker.tsx` + `HomeDashboard.tsx`), not new routes.

| Path | Element | File:Line | Access |
|---|---|---|---|
| `/` | `<HomeRoute>` (LandingPage for guests, redirect `/home` for auth) | `App.tsx:81` | Public |
| `/login` | `LoginPage` | `App.tsx:82` | Public |
| `/pricing` | `Pricing` | `App.tsx:83` | Public (chrome only for guests) |
| `/home` | `HomeDashboard` (persona-aware, 3 modes per spec #34) | `App.tsx:86` | Protected |
| `/onboarding` | `Onboarding` | `App.tsx:89` | Protected |
| `/onboarding/persona` | `PersonaPicker` (full-page) | `App.tsx:90` | Protected |
| `/first-action` | `FirstAction` (full-page interstitial spec #46) | `App.tsx:91` | Protected |
| `/learn` | `Learn` (slice 6.7) | `App.tsx:94` | Protected |
| `/learn/dashboard` | `Dashboard` (slice 6.8) | `App.tsx:95` | Protected |
| `/learn/daily` | `DailyReview` | `App.tsx:96` | Protected |
| `/learn/category/:id` | `CategoryDetail` | `App.tsx:97` | Protected |
| `/learn/card/:id` | `CardViewer` | `App.tsx:98` | Protected |
| `/learn/lesson/:id` | `Lesson` | `App.tsx:99` | Protected |
| `/learn/mission` | `MissionMode` (lazy) | `App.tsx:100` | Protected |
| `/prep` → `/prep/analyze` | `<Navigate replace>` | `App.tsx:103` | Protected |
| `/prep/analyze` | `Analyze` | `App.tsx:104` | Protected |
| `/prep/results` | `Results` | `App.tsx:105` | Protected |
| `/prep/rewrite` | `Rewrite` | `App.tsx:106` | Protected |
| `/prep/interview` | `Interview` | `App.tsx:107` | Protected |
| `/prep/tracker` | `Tracker` (focused-row mounts `<ScoreDeltaWidget>` — see §6 absorption note) | `App.tsx:108` | Protected |
| `/profile` | `Profile` (lazy) | `App.tsx:111` | Protected |
| `/admin` | `<AdminGate><AdminLayout>` (lazy) | `App.tsx:115` | Admin only (E-040) |
| `/admin/cards` | `AdminCards` | `App.tsx:117` | Admin (nested) |
| `/admin/decks` | `AdminDecks` | `App.tsx:118` | Admin (nested) |
| `/admin/decks/:deckId` | `AdminDeckDetail` | `App.tsx:119` | Admin (nested) |
| `/admin/lessons` | `AdminLessons` | `App.tsx:120` | Admin (nested) |
| `/admin/lessons/:lessonId` | `AdminLessonEditor` | `App.tsx:121` | Admin (nested) |
| `/admin/lessons/:lessonId/quiz-items` | `AdminQuizItems` | `App.tsx:122` | Admin (nested) |
| `/admin/analytics` | `AdminAnalytics` | `App.tsx:123` | Admin (nested) |
| `/analyze` `/results` `/rewrite` `/interview` `/tracker` `/study` `/study/daily` `/study/category/:id` `/study/card/:id` `/mission` | `<Navigate replace>` → new namespaced path | `App.tsx:127-136` | Transitional — drop in Phase 6 cleanup |
| `*` | `<Navigate to="/" replace>` | `App.tsx:138` | Catch-all |

`<ProtectedRoute>` (`App.tsx:48`) redirects unauthenticated users to `/`; `<PersonaGate>` handles persona-null routing inside it. `<AdminGate>` (`components/auth/AdminGate.tsx:10`) returns 403 view if `user?.role !== 'admin'`, preventing AdminLayout lazy-chunk download.

### Component graph (80 components, organized by directory)

| Directory | Files | Notes |
|---|---|---|
| `components/admin/` | `AdminLayout.tsx`, `ConfirmCascadeModal.tsx`, `ConfirmPersonaNarrowingModal.tsx`, `MarkdownEditor.tsx` | Slice 6.4a + 6.4b. |
| `components/auth/` | `AdminGate.tsx` | E-040 frontend admin guard. |
| `components/dashboard/` | 15 components — 10 ATS-analysis panels (consumed by `pages/Results.tsx`) + 5 slice 6.8 FSRS-dashboard sections (consumed by `pages/Dashboard.tsx`). Directory hosts both surfaces; consumers do not cross. |
| `components/home/` | `DashboardWidget`, `StateAwareWidgets` + `widgets/` (16 widgets — was 15) | Spec #40 / #61 / #62 home composition. |
| `components/home/widgets/` | `CountdownWidget`, `FirstSessionDoneWidget`, **`HomeScoreDeltaWidget` NEW B-086b**, `InactiveReturnerWidget`, `InterviewPrepperChecklist`, `InterviewTargetWidget`, `LastScanWidget`, `MissionActiveWidget`, `MissionOverdueWidget`, `ResumeStaleWidget`, `StreakAtRiskWidget`, `StreakWidget`, `StudyGapsPromptWidget`, `TeamComingSoonWidget`, `TodaysReviewWidget`, `WeeklyProgressWidget` | **16 files** (+1 since `691934a`). |
| `components/layout/` | `AppShell`, `MobileNav`, `Navbar` *(unused — §9)*, `PageWrapper`, `TopNav`, `UserMenu` | AppShell mounts TopNav (md:+) and MobileNav. |
| `components/learn/` | `RankedDeckList.tsx` | Slice 6.7. |
| `components/lesson/` | `LessonRenderer`, `QuizItemPanel` | Slice 6.3. |
| `components/mission/` | `Countdown`, `DailyTarget`, `MissionDateGate`, `MissionSetup` | Mission-mode chrome. |
| `components/onboarding/` | `GuidedTour` *(unused — §9)* | — |
| `components/profile/` | `StreakBadge`, `XPBar` | — |
| `components/progress/` | `ActivityHeatmap`, `SkillRadar` | Spec #13. |
| `components/rewrite/` | `CoverLetterViewer`, `ResumeEditor`, `ResumePDFTemplate` *(unused — §9)* | — |
| `components/settings/` | `EmailPreferences`, `ThemePicker` | — |
| `components/study/` | `CategoryCard`, `DailyReviewWalledView`, `FlipCard`, `QuizPanel`, `WallInlineNudge` | — |
| `components/tracker/` | `ApplicationCard`, `KanbanBoard`, **`ScoreDeltaWidget` NEW B-086b** | **3 files** (+1 since `691934a`). |
| `components/ui/` | `AnimatedCard`, `GlowButton`, `ProgressBar`, `ScoreBadge`, `SkeletonLoader`, `Tooltip`, `UpgradeModal` | App-root `<UpgradeModal>` mounted in `main.tsx:81`. |
| `components/upload/` | `JDInput`, `ResumeDropzone` | — |
| `components/PaywallModal.tsx` | (top-level, not in a subdir) | Modal triggered by paywall events. |
| `components/PersonaGate.tsx` | (top-level) | Persona-null routing guard. |

### B-086b mount-point absorption

**`<ScoreDeltaWidget>`** — Tracker focused-row inline-expand block. Mounted at `pages/Tracker.tsx:205` inside the focused-row's expanded panel (immediately after the interview-date editor row). Self-loads via `useScoreHistory(focusedRow.id)`. Three render states by history length:

- 0 rows → empty CTA `data-testid="score-delta-widget-empty"` ("Re-scan this application to see how your resume has improved.").
- 1 row → first-scan baseline `data-testid="score-delta-widget-baseline"` (overall score + "Re-scan after improving your resume to see the delta.").
- 2+ rows → full delta render `data-testid="score-delta-widget"` with overall before→after + 4 per-axis delta rows (`Keyword match` / `Skills coverage` / `Formatting` / `Bullets`) + days-between footnote when `days_between > 0`. Per-axis values rendered from BE-pre-computed `ScoreDelta` (D-6 — FE never re-does the math).

Loading + error states surfaced via `data-testid="score-delta-widget-loading"` / `data-testid="score-delta-widget-error"`. Re-scan trigger UX is intentionally NOT inside this widget — the spec describes the data display surface; the trigger is wired by the parent (Tracker.tsx) when resume_text is available.

**`<HomeScoreDeltaWidget>`** — Home dashboard `interview_prepper`-only variant. Mounted at `pages/HomeDashboard.tsx:54` directly below `<CountdownWidget>` inside the `InterviewPrepperMode` JSX (D-5 — same `tracker_id` as CountdownWidget; both widgets surface the same tracker row). Self-loads via `useScoreHistory(trackerId ?? null)`. **Render gate:** `trackerId != null && history.length >= 2`. Cold-start (single history row) hides the widget entirely (no empty state on the home dashboard — minimalism per spec #61). Renders inside the standard `<DashboardWidget>` chrome with title "Score improvement" + view-detail action linking to `/prep/tracker?focus=${trackerId}`. `company` prop carries the display label routed in from CountdownWidget's `next_interview` source.

---

## Section 7 — Frontend pages

27 files (21 top-level in `src/pages/` + 6 under `pages/admin/`). **Unchanged file count this window** — B-086b modifies `Tracker.tsx` + `HomeDashboard.tsx` to mount the new widgets, but adds no new pages.

| File | Mounted at | Notes |
|------|-----------|-------|
| `pages/AdminAnalytics.tsx` | `/admin/analytics` (lazy) | Spec #38 / E-018b dashboard. |
| `pages/Analyze.tsx` | `/prep/analyze` | ATS scan upload. App-root `<UpgradeModal>` triggered via `setShowUpgradeModal(true)` (spec #60 LD-1). |
| `pages/CardViewer.tsx` | `/learn/card/:id` | Single-card flip view. |
| `pages/CategoryDetail.tsx` | `/learn/category/:id` | Category card list. Comment at line 13 references the deleted `StudyDashboard` (stale; harmless — §9). |
| `pages/DailyReview.tsx` | `/learn/daily` | FSRS daily review flow. |
| `pages/Dashboard.tsx` | `/learn/dashboard` | Slice 6.8 user-self FSRS dashboard. |
| `pages/FirstAction.tsx` | `/first-action` | Spec #46 one-CTA interstitial. |
| `pages/HomeDashboard.tsx` | `/home` | Spec #34/#40 persona-aware home. 3 inline render modes (career_climber / interview_prepper / team_lead). **Modified by B-086b (`4aab0bf`)** — `interview_prepper` mode mounts `<HomeScoreDeltaWidget persona={...} trackerId={nextInterview?.tracker_id ?? null} company={nextInterview?.company ?? null} />` directly below `<CountdownWidget>` inside the GRID flex (line 54). Import added at line 12. |
| `pages/Interview.tsx` | `/prep/interview` | Interview Q generator + persistence. |
| `pages/LandingPage.tsx` | `/` (guests) | Public marketing landing. |
| `pages/Learn.tsx` | `/learn` | Slice 6.7 — three inline persona-mode functions. |
| `pages/Lesson.tsx` | `/learn/lesson/:id` | Slice 6.3 lesson viewer. |
| `pages/LoginPage.tsx` | `/login` | Google OAuth flow. |
| `pages/MissionMode.tsx` | `/learn/mission` (lazy) | Interview sprint mode. |
| `pages/Onboarding.tsx` | `/onboarding` | Welcome flow before persona. |
| `pages/PersonaPicker.tsx` | `/onboarding/persona` | Persona selection (spec #34). |
| `pages/Pricing.tsx` | `/pricing` | Stripe pricing card. Geo-routed via IP (Phase 3). |
| `pages/Profile.tsx` | `/profile` (lazy) | User settings. |
| `pages/Results.tsx` | `/prep/results` | ATS scan results detail. |
| `pages/Rewrite.tsx` | `/prep/rewrite` | Resume + cover-letter rewrite. PDF export inline via jsPDF. |
| `pages/Tracker.tsx` | `/prep/tracker` | Application tracker (Kanban + list). **Modified by B-086b (`4aab0bf`)** — focused-row block now mounts `<ScoreDeltaWidget trackerApplicationId={focusedRow.id} />` (line 205) inside the expanded panel (after interview-date editor). Import added at line 8. |
| `pages/admin/AdminCards.tsx` | `/admin/cards` (nested, lazy) | Card CRUD UI. |
| `pages/admin/AdminDeckDetail.tsx` | `/admin/decks/:deckId` (lazy) | Deck editor. Slice 6.4b. |
| `pages/admin/AdminDecks.tsx` | `/admin/decks` (lazy) | Deck list. Slice 6.4a placeholder filled in 6.4b. |
| `pages/admin/AdminLessonEditor.tsx` | `/admin/lessons/:lessonId` (lazy) | Lesson editor with cascade-confirm. Slice 6.4b. |
| `pages/admin/AdminLessons.tsx` | `/admin/lessons` (lazy) | Lesson list. |
| `pages/admin/AdminQuizItems.tsx` | `/admin/lessons/:lessonId/quiz-items` (lazy) | Quiz-item editor. Slice 6.4b. |

**Deleted this regen window:** none. **Carry-forward deletes from prior regens:** `components/home/InterviewDateModal.tsx` (E-042 FE migration `b13f410`), `pages/StudyDashboard.tsx` (slice 6.7 `c6d9274`).

---

## Section 8 — Frontend shared types

### `src/types/index.ts` (~720 lines, 60 exports)

Top-of-file domain types: `ATSScoreBreakdown:3`, `SkillGap:10`, `BulletAnalysis:16`, `FormattingIssue:23`, `KeywordChartData:29`, `SkillOverlapData:36`, `AnalysisResponse:42`, `RewriteEntry:60`, `RewriteSection:69`, `RewriteHeader:75`, `RewriteResponse:80`, `CoverLetterRecipient:87`, `CoverLetterResponse:92`, `InterviewQuestion:103`, `InterviewPrepResponse:108`.

Application/tracker: `ApplicationStatus:115`, `TrackerApplication:117` (carries `interview_date?: string | null` per E-042 spec #57).

### Phase 5 E-043 score-history types (NEW B-086b, `4aab0bf`)

Mirror of `app/schemas/rescan.py` (FE drops `RescanRequest` + `ScoreDeltaResponse` since the route returns `AnalysisResponse` directly):

```ts
ScoreHistoryEntry:134   // id, scan_id, overall_score, keyword_match_score,
                         // skills_coverage_score, formatting_compliance_score,
                         // bullet_strength_score, scanned_at
ScoreDelta:146           // overall_delta, keyword_match_delta,
                         // skills_coverage_delta, formatting_compliance_delta,
                         // bullet_strength_delta, days_between
ScoreHistoryResponse:155  // tracker_application_id, history[], delta | null
```

Consumed by `useScoreHistory.ts:3`, `<ScoreDeltaWidget>` (`tracker/ScoreDeltaWidget.tsx:2`), `<HomeScoreDeltaWidget>` (`home/widgets/HomeScoreDeltaWidget.tsx` via `useScoreHistory`). FE never re-does the delta math — `ScoreDelta` is read straight from the BE `ScoreHistoryResponse.delta` field per §12 D-6.

Cards/categories + Mission + Onboarding/gamification + Email + Admin (cards) + Analysis state machine: unchanged from prior regens.

### Phase 6 Curriculum types (`index.ts`, slice 6.1 / 6.6 / 6.7)

`PersonaVisibility`, `DeckTier`, `LessonVersionType`, `QuestionType`, `QuizDifficulty`, `Deck`, `Lesson`, `QuizItem`, `LessonWithQuizzes`, `DeckWithLessons`, `ScoreBreakdown`, `RankedDeck`, `RankedDecksResponse`, `QuizReviewRequest`, `QuizReviewResponse`. Unchanged this window.

### Admin write-shape interfaces (slice 6.4b-2)

`EditClassification`, `AdminDeckStatusFilter`, `AdminLessonStatusFilter`, `AdminQuizItemStatusFilter`, `DeckCreateRequest`, `DeckUpdateRequest`, `LessonCreateRequest`, `LessonUpdateRequest`, `LessonUpdateResponse`, `QuizItemCreateRequest`, `QuizItemUpdateRequest`. Unchanged.

### Backend rescan schemas (B-086a, `210dcb2`) **— NEW**

`app/schemas/rescan.py:18-89` declares **5 Pydantic v2 schemas:**

| Schema | Lines | Purpose |
|--------|-------|---------|
| `RescanRequest` | 18 | POST /api/v1/analyze/rescan body — `{tracker_application_id: str, resume_text: str (200..50_000 chars)}` |
| `ScoreHistoryEntry` | 31 | Flattened row of `tracker_application_scores` for the wire — id / scan_id / overall_score / 4 per-axis floats / scanned_at |
| `ScoreDelta` | 44 | Pre-computed delta between latest two history rows; **None when len(history) < 2**. Includes `days_between: int`. |
| `ScoreHistoryResponse` | 59 | GET /api/v1/tracker/{id}/scores envelope — `{tracker_application_id, history[], delta | null}` |
| `ScoreDeltaResponse` | 71 | Per-axis envelope reserved for future `/rescan` response shape (B-086b currently returns `AnalysisResponse` directly per §5.2; this schema captures the audit-#11 / D-12 shape for future contract evolution). Carries `short_circuited: bool` flag + `ats_score_before/after/delta` + 4 per-axis deltas. |

### Backend ingestion schemas (slice 6.10b)

`app/schemas/ingestion.py:37-148` declares 7 Pydantic v2 schemas. Unchanged this window — NOT mirrored to FE (slice 6.10b D-10 deferred FE consumer).

### Backend dashboard schemas (slice 6.8)

`app/schemas/dashboard.py:19-160` declares 10 Pydantic v2 schemas (FSRS dashboard). FE mirror at `src/types/index.ts` (slice 6.8 D-3 single-envelope). Unchanged this window.

### Backend analytics-event schemas (slice 6.0)

`app/schemas/analytics_event.py:13-58`. Unchanged.

### Backend ranker schemas (slice 6.6)

`app/schemas/ranker.py:21-76`. Unchanged.

### Persona / auth types (`src/context/AuthContext.tsx`)

`Persona = 'career_climber' | 'interview_prepper' | 'team_lead' | null`. Defined in AuthContext; consumed across pages + widgets.

### Home-state types (`src/types/homeState.ts`, 40 lines)

Spec #40 priority-slot types. Includes `NextInterview:19` interface (mirrors BE `NextInterview` Pydantic in `app/schemas/home.py`) — `{tracker_id, company, role, date, days_until, source: 'tracker' | 'soonest_upcoming'}` — and `next_interview: NextInterview | null` field on `HomeStateContext:33`. **Now consumed by `<HomeScoreDeltaWidget>`** (B-086b) — `nextInterview?.tracker_id` routes the home variant to the same tracker row CountdownWidget surfaces.

---

## Section 9 — Known-dead or transitional code

| Path | Why flagged | Suggested action |
|------|-------------|------------------|
| `hirelens-frontend/src/components/layout/Navbar.tsx` | `AppShell` only imports `TopNav`/`MobileNav`; no file imports `Navbar`. Phase-6 cleanup (B-010). | delete |
| `hirelens-frontend/src/components/onboarding/GuidedTour.tsx` | Only self-reference; no consumer. | delete (or migrate — see §12 Q1) |
| `hirelens-frontend/src/components/rewrite/ResumePDFTemplate.tsx` | Only self-reference. PDF inline via jsPDF in `Rewrite.tsx`. | delete (see §12 Q2) |
| `hirelens-backend/app/services/ai_service.py` | Duplicates `gpt_service.py` API. Consumed only by enterprise `/api/v1/resume/{id}/optimize`. `[S47-defer]`. | leave (tracked) |
| `hirelens-backend/app/services/llm/` | Legacy provider abstraction parallel to `app/core/llm_router.py`. Phase-6 consolidation pending. | leave (Phase-6) |
| `pages/CategoryDetail.tsx:13`, `components/PaywallModal.tsx:5` | Comments reference the deleted `StudyDashboard` page. Stale refs but harmless (comment-only). | clean on next edit |
| `users.interview_target_company`, `users.interview_target_date` columns | Transitional — schema-comment-only deprecation per E-042 AC-7 (`b13f410`). FE consumers fully migrated to `homeState.context.next_interview` (`tracker_applications_v2.interview_date` source-of-truth). Columns still on disk; no FE reads. Phase-6 cleanup will drop the columns. | drop columns in dedicated alembic migration during Phase-6 cleanup (cross-ref BACKLOG B-018 / spec #53) |
| `app/schemas/rescan.py::ScoreDeltaResponse` | Reserved for future `/rescan` response evolution; B-086b route currently returns `AnalysisResponse` directly per spec §5.2. Schema lives on disk for stable-contract reasons. | leave (post-MVP shape) |

No components found behind `{false && …}` guards or dormant feature flags at HEAD `<this-slice>`. **Background-job framework ACTIVE** as of slice 6.10b (`8735373`) — RQ-on-Redis worker (`app/jobs/ingestion_worker.py`) is the first runtime consumer. **B-086b adds NO new background-job consumer** — the rescan flow is fully synchronous (LLM call inside the request handler with try/except + 502 mapping); no `enqueue` to any queue. Cron architecture decision still pending at B-078 🟦.

---

## Section 10 — Skills inventory

### Tracked skills (`.agent/skills/*.md`, 22 files)

| File | Description |
|------|-------------|
| admin-panel.md | Card CRUD, bulk import, AI-assisted card generation (Phase 3) |
| analytics.md | PostHog event catalog (frontend + backend), funnels, conventions. **Modified this window** by B-086b (`4aab0bf`, +4 rescan event rows at lines 163–166: `rescan_initiated` / `rescan_completed` (per-axis delta envelope per §12 D-12 + `short_circuited: false` flag) / `rescan_short_circuited` / `rescan_failed{error_class}`). Content-only delta — file count unchanged. |
| ats-card-bridge.md | Maps ATS scan skill gaps to study cards |
| ats-scanner.md | ATS resume scanning, scoring, keyword extraction, bullet rewriting, auto-tracker |
| backend.md | Service-layer conventions, route mounting, audit dependency chains, dual-write best-effort wrapper, CI invocation pattern. (B-073 cohort item 1, `84060b3`.) |
| card-extraction.md | JSX → PostgreSQL card extraction pipeline |
| content-pipeline.md | End-to-end content pipeline — extraction, AI generation, admin CRUD, bulk import |
| curriculum.md | Phase 6 domain skill — deck/lesson/quiz_item conventions, persona/tier visibility, FSRS quiz-item progress, ranker pipeline, seed-corpus loader, dual-write hooks. (B-075, `49fc7e7`.) |
| database-schema.md | Living reference of all DB tables, columns, types, indexes, relationships |
| db-migration.md | Alembic patterns and schema change rules |
| design-system.md | Theme tokens, multi-theme switching, Tailwind integration |
| experience-gen.md | "My Experience" AI generation |
| gamification.md | Streaks, XP, badges, skill radar, activity heatmap |
| geo-pricing.md | IP-based geo pricing (INR vs USD) with Redis caching |
| home.md | State-aware home dashboard — priority slot, state evaluator, Redis cache |
| llm-strategy.md | LLM task tiering, provider routing, `generate_for_task()` interface |
| mission-mode.md | Interview sprint — countdown, daily targets, focused card set |
| notifications.md | Daily email reminders, email preferences, Resend integration |
| payments.md | Stripe checkout, webhooks, plan gating, free tier limits, geo pricing, usage caps |
| security.md | Auth hardening, rate limiting, CORS, request size, webhook idempotency |
| study-engine.md | **(frontmatter has no `description:` field — see §11 #8)** |
| testing.md | Test patterns, fixtures, mocks |

### Untracked skill surfaces

Three directory-style skills on disk but not in git (each shows `??` in `git status`). Source/intent unknown; appeared 2026-04-21 per filesystem mtime. **Unchanged since prior regen.**

| Path | Files | Status |
|------|-------|--------|
| `.agent/skills/stripe-best-practices/SKILL.md` | + `references/` (5 entries) | UNTRACKED |
| `.agent/skills/stripe-projects/SKILL.md` | (single file) | UNTRACKED |
| `.agent/skills/upgrade-stripe/SKILL.md` | (single file) | UNTRACKED |

`SKILL.md` (uppercase) doesn't match SkillForge convention (lowercase slug). Skill discovery walking `.agent/skills/*.md` (top-level glob) won't find these. See §12 Q8.

**Skill-inventory gaps surfaced this regen:** none new. **`background-jobs.md` candidate stays at flag #1 dormant** (1/3 consumers). B-086b is **NOT** a second consumer — the rescan flow is synchronous in the request handler, no `enqueue` to any queue. Counter unchanged. Slice 6.14 (daily Pro digest) remains the next expected consumer per LD G-2. SOP-4 close-loop (per CLAUDE.md `b468025`): no auto-file fires this slice — consistent with B-079 / B-081 / B-085 prior regen handling of the dormant flag.

---

## Section 11 — Drift flags (AGENTS.md / master-doc vs code)

Re-verified at HEAD `<this-slice>`. **Item #9 newly RESOLVED** by `210dcb2` (B-086a foundation slice) — `tracker_applications_v2` now carries `jd_hash` + `jd_text` columns + `ix_tracker_apps_jd_hash` index per migration `e043a1b2c3d4`; SESSION-STATE D-020 closure mirrors. Items #18, #19, #20, #22, #23 carry forward as RESOLVED (kept for traceability per existing CR convention). All other items unchanged.

1. **AGENTS.md legacy-routes paths use underscores; decorators use hyphens.** `app/api/routes/cover_letter.py:22` decorates `/cover-letter`; AGENTS.md row says `/api/cover_letter`. Same for `/api/interview` → `/api/interview-prep`. **Status: still drifted.**

2. **AGENTS.md Routes table lists `/api/v1/onboarding` and `/api/v1/payments` as v1 routers, but the files live in the legacy folder** (`app/api/routes/onboarding.py`, `app/api/routes/payments.py`). Mounted at `/api/v1` via `main.py:169-170`. **Status: still drifted.**

3. **AGENTS.md Models table User row still lists `target_company`, `target_date`** (line 270). Disk: `interview_target_company` (String(100)), `interview_target_date` (Date). Migration `02bf7265b387` did the rename. **Status: still drifted post-E-042 FE migration (`b13f410`, 2026-04-29).** AGENTS.md User row also lacks the DEPRECATED flag despite spec #57 schema-comment-only deprecation; FE consumers no longer read the columns but columns remain on disk pending Phase-6 cleanup. AGENTS.md is process-doc drifted; not blocking. Cleanup: amend AGENTS.md User row to mark fields DEPRECATED on next AGENTS.md touch. **Carry-forward — chat-Claude flagged for re-verification this regen; on-disk state unchanged.**

4. **AGENTS.md Routes table references `/api/v1/mission` (singular)** (line 213). Decorators are plural `/missions/create`, `/missions/active`, `/missions/daily`, `/missions/complete-day` (`mission.py:52,84,130,167`). `[S35-flag]`. **Status: still drifted.**

5. **AGENTS.md says `Category` has `source` column.** True, but it also has `tags` JSONB column (migration `d16ca29a5d08`). AGENTS.md doesn't mention it. **Status: still drifted.**

6. **AGENTS.md Models table references `UsageLimit`** (line 276). No `UsageLimit` model file or class on disk. Limits are enforced via `usage_service.py::PLAN_LIMITS` dict, not a DB table. **Status: still drifted (phantom).**

7. **Email-preferences route path mismatch.** `email_prefs.py:66,79` mounts `/email-preferences`; FE calls `/api/v1/email-preferences`. AGENTS.md table line 212 says `/api/v1/email-prefs`. **Status: still drifted.**

8. **`study-engine.md` skill file has no `description:` frontmatter.** Other 21 skill files have one. `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md` flags as critical. **Status: still drifted.**

9. ~~**Tracker auto-save JD dedupe documented as locked but not implemented.**~~ ✅ RESOLVED 2026-04-30 by `210dcb2` (B-086a foundation slice). `tracker_applications_v2` now carries `jd_hash` (String(64), indexed via `ix_tracker_apps_jd_hash`) + `jd_text` (Text), both nullable per D-10 (no backfill of pre-migration rows). Migration `e043a1b2c3d4` bundles Q1 LOCK alongside the `tracker_application_scores` table. `tracker_service_v2.create_application` now accepts `jd_text` + `jd_hash` kwargs (purely additive); `app/api/routes/analyze.py:173` populates both for new rows via `jd_hash=hash_jd(job_description)`. SESSION-STATE D-020 closure ledger mirrors. **Status: resolved (kept for traceability).**

10. **Four legacy `/api/*` routers still mounted alongside v1 counterparts.** `analyze` / `rewrite` / `cover_letter` / `interview` in `main.py:129-132`. v1 equivalents are *re-exports* of legacy router objects, so deprecating legacy mounts requires moving handlers first. **Status: still drifted.** Note: B-086b's `POST /analyze/rescan` decorator landed on the legacy `app/api/routes/analyze.py` file (consistent with the `POST /analyze` precedent), so the v1 re-export double-mount is preserved per existing pattern — does NOT widen the drift.

11. **AGENTS.md and skills do not reference R19 / SOP-8 / SOP-9 / H1–H4.** AGENTS.md was not swept during B-048. Quick grep shows no stale rule citations either, so this is a "no-stale-citations" finding. **Status: confirmed clean.**

12. **Three untracked skill directories** (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`). See §10 + §12 Q8. **Status: open — unchanged this regen.**

13. **N1-SUPPLEMENT → N9 promotion deferred** (per B-048 close-line). 6 callsites flagged in SESSION-STATE Deferred Hygiene. **Status: open.**

14. **Spec section header rename `## 12. R15` / `## 13. R15` across 5 spec files** deferred per B-048. TOC anchor risk. **Status: open.**

15. **Pre-existing dirty / untracked working-tree items (long-standing):** `Enhancements.txt`, `hirelens-backend/scripts/wipe_local_user_data.py`, `../.DS_Store`. Untracked: `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md`, `docs/status/E2E-READINESS-2026-04-21.md`, `skills-lock.json`, `.gitattributes`, `CLAUDE_old.md`, `.agent/skills/{stripe-*,upgrade-stripe}/`. None bundled into commits per C2/C5. **Status: long-standing; not blocking.**

16. **Duplicated chromeless-paths sets across `AppShell.tsx` + `MobileNav.tsx`** (B-058). `AppShell.CHROMELESS_PATHS = {'/', '/login', '/onboarding/persona', '/first-action'}` + `/pricing` guest carve-out; `MobileNav.HIDDEN_PATHS = {'/', '/login'}` + same `/pricing` carve-out. Drift risk: any future change must be in two places. Tracked at B-058 P3. **Status: open.**

17. **Three free-tier paywall env vars not yet reflected in AGENTS.md env-vars table.** `Settings.free_daily_review_limit` (env `FREE_DAILY_REVIEW_LIMIT`, default 10 per LD-001 amendment), `Settings.free_lifetime_scan_limit` (default 1, env `FREE_LIFETIME_SCAN_LIMIT`), `Settings.free_monthly_interview_limit` (default 3, env `FREE_MONTHLY_INTERVIEW_LIMIT`). `payments.md` skill records them; AGENTS.md table doesn't. **Status: still drifted on AGENTS.md; no code drift.**

18. ~~**Phase-6 spec body Status lines stuck at `Drafted, not shipped` despite impl ship.**~~ ✅ RESOLVED 2026-04-27 by `95bb3c5`. **Status: resolved (kept for traceability).**

19. ~~**Spec status convention gap for split-impl specs (#04 admin-authoring).**~~ Both halves of spec #04 shipped (`b0806d0` + `d6bda3b` + `634f633`); spec body Status line still reads "Partially shipped — … pending B-065" (stale). **Status: SHIPPING-RESOLVED but Status line still stale on disk** — needs flip to canonical `Shipped (spec + impl) — closes B-064 + B-065 + B-068.` form on next legitimate spec edit. CR is read-only; will not edit spec source.

20. ~~**BE test count "regression" 520 → 510 was env-var dependent baseline drift.**~~ ✅ EXPLAINED 2026-04-27. Tests need `FREE_DAILY_REVIEW_LIMIT=10 FREE_LIFETIME_SCAN_LIMIT=1 FREE_MONTHLY_INTERVIEW_LIMIT=3` (canonical CI invocation). **Status: resolved (kept for traceability).**

21. **D-026 process lesson — spec authors must verify FE files referenced in mount-paths exist.** Slice 6.4 spec referenced `pages/AdminAudit.tsx` based on BE endpoint existence; only `AdminAnalytics.tsx` + `AdminPanel.tsx` existed. Slice 6.4a R19 fired; resolved via spec amendment `cbf878f`. SOP-5 enhancement candidate; not yet promoted to R-rule (pattern not recurred since). **Status: REAFFIRMED.**

22. ~~**§8 Frontend shared types lags `src/types/index.ts` reality (admin write-shapes deferred from B-067).**~~ ✅ RESOLVED 2026-04-28 by `6a2a224` (admin write-shapes enumerated in §8). **Status: resolved.**

23. ~~**Slice 6.5 spec describes pending filter additions to `quiz_item_study_service` + `lesson_service` (B-072).**~~ ✅ RESOLVED 2026-04-28 by `930a6a2` (slice 6.5 implementation shipped — closes B-072). **Status: resolved.**

24. **Pro-path admin-analytics still invisible.** `usage_service.py::check_and_increment` short-circuits on `max_uses == -1` BEFORE reaching `log_usage` (line ~151-152); `admin_analytics_service.py:53-54` maps `rewrite` / `cover_letter` → reasoning tier but the input table stays empty for Pro/admin callers. Same shape as D-021c open drift. Spec #58 §12 errata recorded the overclaim; no fix has shipped. **Status: open (carry-forward).** Close shape: either (i) docs slice amends spec #58 §12 to strike the "retroactively surfaces" claim, or (ii) impl slice moves `log_usage` to fire for every authed request (broad blast radius).

25. **CLAUDE.md uncommitted Q1-Q4 + "This file is working if" additions in working tree.** Pre-authored content from another slice (preserve-and-coexist per D-019). Carried forward from prior regens. **Status: still open (carry-forward) — info-only.**

26. **Spec #57 §AC-7 cites `StudyDashboard.tsx` as a migration path, but the file was deleted in slice 6.7 (`c6d9274`).** Surfaced as JC #4 in E-042 FE final report. Spec #57 is in shipped (`Done`) status per BACKLOG; AC tracked complete via E-042 FE final report. Spec amendment cleanup non-blocking — the file deletion predates the spec citation; no functional impact. **Status: open (carry-forward) — harmless on disk; cleanup on next natural spec #57 touch.**

27. **D-027 — 5 pre-existing test failures under prod-default env vars.** Surface: `hirelens-backend/tests` — interview-prep + admin-analytics modules (`tests/test_admin_analytics.py::test_performance_llm_spend_from_usage_logs` + `tests/test_payments_usage_route.py::test_usage_free_user_at_interview_prep_cap_shows_zero_remaining` + `tests/test_payments_usage_route.py::test_usage_pro_user_interview_prep_unlimited_sentinel` + `tests/test_payments_usage_route.py` (third interview-prep test) + `tests/test_usage_limits.py::test_free_user_limited_to_3_interview_generations`). Repro: BE test suite under `FREE_DAILY_REVIEW_LIMIT=10 FREE_LIFETIME_SCAN_LIMIT=1 FREE_MONTHLY_INTERVIEW_LIMIT=3`. Reproduced clean with B-086a stash and again at B-086b post-merge — **not regression-caused by `210dcb2` or `4aab0bf`**. Suspected root cause: pydantic `@lru_cache` on `get_settings()` — env-var changes don't invalidate cache across test modules; `usage_service.py:24` captures `_settings = get_settings()` at module-import time so `interview_prep` limit can resolve differently than the test asserts depending on pytest collection order. Tracking-only, non-blocking. Triage as separate slice when env-var-cache pattern needs broader fix. Filed at SESSION-STATE drift table at `1b86bf0`. **Status: open (carry-forward) — non-blocking, tracking-only.**

### Recently closed in this regen window

- **#9 (D-020 closure)** — see item #9 above. Closed at `210dcb2` (B-086a). Migration `e043a1b2c3d4`; ORM model `tracker.py` extended with `jd_text` + `jd_hash`; tracker-write hook in `analyze.py` populates both for new rows. AC-15 verified.

---

## Section 12 — Open questions for Dhamo

1. `components/onboarding/GuidedTour.tsx` has zero imports. Is this (A) dead code safe to delete, or (B) a scaffold for a future onboarding tour spec? *(carried)*
2. `components/rewrite/ResumePDFTemplate.tsx` has zero imports and PDF generation is inline in `Rewrite.tsx`. Delete in next cleanup slice — yes/no? *(carried)*
3. Is `UsageLimit` supposed to exist as a DB-backed model, or is the AGENTS.md Models table row stale? *(carried)*
4. ~~`AdminPanel` (`/admin`) has no route-level admin guard~~ ✅ RESOLVED by E-040 (`1148354`, spec #54). *(resolved — drop next regen if no follow-up)*
5. `study-engine.md` skill file is missing `description:` frontmatter — backfill to match the other 21 skills? *(carried)*
6. `ai_service.py` duplicates `gpt_service.py` verbatim and is consumed only by an enterprise-tier endpoint. Safe to delete now, or wait per `[S47-defer]`? *(carried)*
7. Legacy mounts `/api/analyze`, `/api/rewrite`, `/api/cover-letter`, `/api/interview-prep`, **`/api/analyze/rescan` (NEW)** — known external caller, or purely FE-migration holdover? Note: B-086b's new `/analyze/rescan` decorator landed on the legacy file per the existing `/analyze` precedent; same legacy/v1 double-mount applies. *(carry-forward; widened scope)*
8. Three untracked skill directories (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`). Source/intent unknown. (a) Commit, (b) `.gitignore`, (c) delete? `SKILL.md` (uppercase) doesn't match SkillForge convention. *(carried)*
9. ~~E-042 deprecates `users.interview_target_company` and `users.interview_target_date` in favor of `tracker_applications_v2.interview_date`. FE consumers (CountdownWidget, MissionDateGate) still read user-level fields.~~ Cleared by E-042 FE migration (`b13f410`); 10 consumers migrated; columns remain on disk pending Phase-6 cleanup. **Drop next regen unless Phase-6 cleanup deferral surfaces.**

The four Phase 6 product decisions chat sometimes references (cron arch G2, file storage H1, events sink I1, `card_quality_signals` J2) live in **SESSION-STATE Phase 6 locked-decisions block**, not here. G2 cron decision is also tracked at B-078 🟦 awaiting re-evaluation when 6.13.5 closes.

---

## Section 13 — Specs inventory

Walked `docs/specs/**/*.md` — **93 spec files across 7 phases** (+1 since `691934a`: phase-5 +1 — `63-ats-rescan-loop.md` E-043 spec-author at `da14c01` + §12 amendment `71a77e3` + §5.3/§6.1 corrections `1b86bf0`).

### Per-phase counts
| Phase | Files | With explicit Status line | No status field |
|-------|-------|---------------------------|-----------------|
| phase-0 | 6 | 6 | 0 |
| phase-1 | 13 | 6 | 7 |
| phase-2 | 8 | 7 | 1 |
| phase-3 | 11 | 8 | 3 |
| phase-4 | 6 | 6 | 0 |
| phase-5 | **37** | 15 | 22 |
| phase-6 | 12 | 12 | 0 |
| **Total** | **93** | **60** | **33** |

### Status legend
`Done` · `Complete` · `Implemented — Spec Backfill Pending (P5-S###)` · `Draft` · `Drafted, not shipped` · `Shipped (spec + impl)` · `Done — Shipped in <sha>` · `Partially Done` · `Planned — Known-Broken` · `Deferred` · `Complete — Spec Backfill Pending`

### Slice absorption log (this regen)

| Slice | Spec | BACKLOG | Closing commit | Notes |
|---|---|---|---|---|
| B-086a | `63-ats-rescan-loop.md` | B-086a ✅ | `210dcb2` | **Phase 5 E-043 foundation** — alembic migration `e043a1b2c3d4` (Q1 LOCK: `jd_text` + `jd_hash` on `tracker_applications_v2` + `ix_tracker_apps_jd_hash` — closes drift D-020; Q2 LOCK: `tracker_application_scores` table + 3 indexes); new model `app/models/tracker_application_score.py`; new service `app/services/analysis_service.py` extracting `score_resume_against_jd` per §6.1 G-6; new schema module `app/schemas/rescan.py` (5 schemas — scaffolds B-086b consumes); new ORM-getter `tracker_service_v2.get_application_model_by_id`; `tracker_service_v2.create_application` extended with optional `jd_text` + `jd_hash` kwargs (additive); `app/api/routes/analyze.py` reduced to parse → call helper → write tracker row with `jd_text` + `jd_hash` populated. Tests BE 692→700 (+8); +1 integration (alembic round-trip). FE 417 unchanged. AC-12 / AC-15 / AC-17 covered. JC #1 (BACKLOG ID — sub-ID convention preserved per slice-6.10 precedent), JC #2 (`scan_id` no FK — no `scans` table on disk), JC #3 (`parsed_resume` kwarg added to function signature for AC-17 byte-identity). |
| B-086b | `63-ats-rescan-loop.md` | B-086b ✅ + B-086 ✅ (cascade) + E-043 ✅ (cascade) | `4aab0bf` | **Phase 5 E-043 orchestrator + admin route + UI** — new service `app/services/tracker_application_score_service.py` (write_score_row / find_by_dedupe / get_score_history / compute_delta / to_history_entry / get_prior_overall_score / update_tracker_ats_score); new route `POST /api/v1/analyze/rescan` at `app/api/routes/analyze.py:188` (orchestrator: ownership read → 422 jd_text=NULL → D-2 dedupe short-circuit → G-7 counter → score → persist + ats_score flip → `rescan_completed` event); new route `GET /api/v1/tracker/{app_id}/scores` at `app/api/v1/routes/tracker.py:79`; new FE component `<ScoreDeltaWidget>` (tracker focused-row inline-expand, 3 render states); new FE component `<HomeScoreDeltaWidget>` (interview_prepper-only home variant below CountdownWidget, history.length≥2 render gate); new hook `useScoreHistory`; new api helpers `fetchScoreHistory` + `triggerRescan`; 3 new FE types in `src/types/index.ts:134-160` (ScoreHistoryEntry / ScoreDelta / ScoreHistoryResponse); 4 new PostHog events at `analytics.md:163-166`. Tests BE 700→713 (+13); FE 417→428 (+11). AC-1..AC-11, AC-13, AC-14, AC-16 covered (AC-12/AC-15/AC-17 covered by B-086a). JC #1 (`get_application_by_id` returns Pydantic — added sibling ORM-getter `get_application_model_by_id`). **Cascade-closes B-086 umbrella + E-043** per R15(c). |
| (process) | (none) | none | `<this-slice>` | This CR full regen. All 13 sections regenerated. PRD §1.3 core loop closure milestone surfaced in §1. R14 exception (b) — pure CR doc regen, no test surface. Carry BE 713 / FE 428 forward verbatim. Two-commit close pattern (regen + SHA backfill). |
| (carry) | (prior log) | B-061..B-085 | (see prior CR at `691934a`) | Slices 6.0–6.8 + 6.10 family + B-073..B-085 process work absorbed in B-079 / B-081 / B-085 prior regens. Not re-listed here. |

### phase-0
| File | Status |
|------|--------|
| 00-postgresql-migration.md | Done |
| 01-alembic-setup.md | Done |
| 02-auth-unification.md | Done |
| 02a-skeleton-deploy.md | Done |
| 02b-cicd-pipeline.md | Done |
| 03-user-role-admin.md | Done |

### phase-1
| File | Status |
|------|--------|
| 03-card-extraction.md | Partially Done |
| 04-cards-api.md | Done |
| 05-fsrs-daily-review.md | (no status field) |
| 06-study-dashboard-ui.md | (no status field) |
| 07-card-viewer-ui.md | (no status field) |
| 08-ats-card-mapping.md | (no status field) |
| 09-onboarding-flow.md | (no status field) |
| 10-posthog-analytics.md | (no status field) |
| 11-stripe-integration.md | (no status field) |
| 11a-free-tier-limits.md | Implemented — Spec Backfill Pending (P5-S6) |
| 11b-tracker-autopopulate.md | Implemented — Spec Backfill Pending (P5-S5) |
| 11c-ip-registration-blocking.md | Implemented — Spec Backfill Pending (P5-S4) |
| 11d-llm-router.md | Implemented — Spec Backfill Pending (P5-S1) |

### phase-2
| File | Status |
|------|--------|
| 10-streaks-xp-badges.md | Done |
| 11-gamification-ui.md | Done |
| 13-skill-radar-heatmap.md | (no status field) |
| 14-mission-mode.md | Done |
| 14a-mission-mode-api.md | Done |
| 14b-mission-mode-ui.md | Done |
| 15-daily-email.md | Done |
| 16-email-preferences.md | Done |

### phase-3
| File | Status |
|------|--------|
| 15-ats-scorer-upgrade.md | Done |
| 16-experience-generator-api.md | Done |
| 17-admin-card-crud.md | Done |
| 18-ai-card-generation.md | Done |
| 19-landing-page.md | (no status field) |
| 20-onboarding-polish.md | (no status field) |
| 20b-design-system-themes.md | Implemented — Spec Backfill Pending (P5-S2) |
| 20c-resume-cover-letter-fix.md | Planned — Known-Broken |
| 21-card-feedback.md | Done |
| 22-my-experience.md | Done |
| 25-feedback-nps-system.md | Done |

### phase-4
| File | Status |
|------|--------|
| 20-ai-feedback-digest.md | Deferred |
| 22-error-monitoring.md | Done |
| 23-error-monitoring.md | Complete |
| 24-posthog-dashboards.md | Complete |
| 25-performance-hardening.md | Complete |
| 25a-custom-domain-golive.md | Complete — Spec Backfill Pending |

### phase-5 (most active phase)
| File | Status |
|------|--------|
| 01-admin-analytics-early-draft.md | Done |
| 09-resume-rewrite-fix.md | (no status field) |
| 10-cover-letter-format-fix.md | (no status field) |
| 11-generate-experience-fix.md | (no status field) |
| 12-navigation-restructure.md | (no status field) |
| 21-analysis-results-improvements.md | Done — Shipped in `1c0817a` |
| 22-plan-aware-missing-skills-cta.md | Draft |
| 27-geo-pricing.md | (no status field) |
| 34-persona-picker-and-home.md | (no status field) |
| 35-home-dashboard-and-widgets.md | (no status field) |
| 36-subscription-cancellation.md | (no status field) |
| 38-admin-analytics.md | Draft |
| 40-home-dashboard-state-aware.md | (no status field, but P5-S18b retrofit per SESSION-STATE) |
| 41-interview-prepper-checklist.md | (no status field) |
| 42-paywall-dismissal.md | (no status field) |
| 43-stripe-webhook-idempotency.md | (no status field) |
| 44-home-widget-empty-states.md | (no status field) |
| 45-legacy-route-cleanup.md | (no status field) |
| 46-post-persona-first-action.md | (no status field) |
| 47-resume-rewrite-content-preservation.md | (no status field) |
| 48-doc-audit-pattern.md | (no status field) |
| 49-interview-question-storage.md | (no status field) |
| 50-free-tier-daily-card-wall.md | Draft (amended `b8d0c8c` — LD-001 cap 15→10) |
| 51-ai-rewrite-section-preservation.md | (no status field — B-001 closed) |
| 52-cover-letter-format-enforcement.md | (no status field — B-002 closed) |
| 53-interview-target-optional-fields.md | (no status field — B-018 shipped) |
| 54-admin-email-whitelist.md | Draft |
| 55-reanalyse-paywall-gate.md | Draft |
| 56-free-tier-scan-lifetime-cap.md | Draft |
| 57-tracker-level-interview-date.md | (no status field — E-042 BE + FE shipped) |
| 58-legacy-rewrite-router-auth-quota.md | Shipped (spec + impl) — closes B-033 |
| 59-scan-persistence.md | Drafted, not shipped *(actually shipped per B-035 `0b35440`)* |
| 60-analyze-page-preflight-gate.md | (no status field — B-045 closed) |
| 61-home-dashboard-composition-rules.md | Drafted, not shipped *(impl `ecef895` closes B-051)* |
| 62-study-dashboard-source-hint.md | Drafted, not shipped *(impl `df035e1` closes B-052 + B-053)* |
| 63-ats-rescan-loop.md | **Done — Shipped (spec + impl). Spec authored `da14c01` 2026-04-30; §12 amendment `71a77e3` (D-1..D-12 locked from §14 OQ-A..OQ-L); §5.3 + §6.1 disk-truth corrections `1b86bf0`; foundation `210dcb2` (B-086a); orchestrator + admin route + UI `4aab0bf` (B-086b). Cascade-closes B-086 umbrella + E-043. Closes drift D-020.** |
| 63-daily-review-preflight-gate.md | Draft *(impl `20562ea` closes B-059)* — **shares slot 63 with `63-ats-rescan-loop.md`; see numbering anomalies below.** |

### phase-6 (Curriculum Platform)
| File | Status |
|------|--------|
| 00-analytics-tables.md | Shipped (spec + impl) — closes B-069. Impl `e7a0044`. |
| 01-foundation-schema.md | Shipped (spec + impl) — closes B-061. Impl `a989539`. |
| 02-fsrs-quiz-item-binding.md | Shipped (spec + impl) — closes B-062. Impl `7b654fb`. |
| 03-lesson-ux.md | Shipped (spec + impl) — closes B-063. Impl `ba00331`. |
| 04-admin-authoring.md | Partially shipped (spec body line stale per §11 #19 — both halves shipped) |
| 05-seed-lessons.md | Shipped (spec + impl) — closes B-071. Impl `ac5b905`. |
| 06-read-time-invariants.md | Shipped (spec + impl) — closes B-072. Impl `930a6a2`. |
| 07-deck-lesson-ranker.md | Shipped (spec + impl) — closes B-074. Impl `5011518`. |
| 08-persona-learn-page.md | Shipped (spec + impl) — closes B-077. Impl `c6d9274`. |
| 09-fsrs-dashboard.md | Shipped (spec + impl) — closes B-080. Impl `0968a13`. |
| 10-ai-ingestion-pipeline.md | Shipped (spec + impl) — closes B-083 (cascade), B-083a, B-083b. Impl `8735373` (cascade SHA = B-083b) preceded by `9bd9397` (B-083a foundation). |
| 11-content-quality-retention.md | Drafted, not shipped *(spec authored `7d7c6e8` 2026-04-29; §12 amendment `d9bfcfc`. Implementation pending — files B-084 forward at 🔴 status.)* |

### Numbering anomalies / duplicates / gaps

- **phase-3 spec numbering:** `20-onboarding-polish.md`, `20b-design-system-themes.md`, `20c-resume-cover-letter-fix.md` share `20*` slot via letter suffixes. Convention consistent with phase-1 `11a/b/c/d`.
- **phase-4 numbering:** `22-error-monitoring.md` and `23-error-monitoring.md` — two specs with identical title at adjacent numbers; one Done, one Complete. Likely supersession.
- **phase-5 NEW slot 63 collision:** `63-ats-rescan-loop.md` (E-043, shipped this window) and pre-existing `63-daily-review-preflight-gate.md` (B-059, Draft / shipped per `20562ea`) both occupy slot 63. The two specs cover unrelated surfaces (re-scan loop vs daily-review preflight gate). Resolution candidates: (a) renumber `daily-review-preflight-gate.md` to a free slot (e.g., 64-), (b) add a letter suffix per phase-3 `20a/b/c` precedent (`63a-` / `63b-`), (c) accept the collision since both are post-author slug-distinct on disk. SOP-1 spec-author guard does not enforce phase-internal slot uniqueness; the convention is human-coordinated. Surface for chat-Claude calibration on next phase-5 spec-author slice.
- **phase-5 gaps:** `01`, `09–12`, `21–22`, `27`, `34–63` (gaps at 23–26, 28–33, 37, 39). Reserved-but-not-authored slots.
- **phase-5 number `1` reuse:** `01-admin-analytics-early-draft.md` superseded by `38-admin-analytics.md` per same OKR. Consider archiving or marking Superseded.
- **Total spec status hygiene gap:** 33 of 93 specs (35%) have no Status line. Concentration in phase-1 (7), phase-3 (3), phase-5 (22). Phase-6 sweep at `95bb3c5` flipped 6 phase-5 + 3 phase-6 specs to canonical post-ship form. Phase-5 specs #51, #52, #57 remain unflipped despite shipping per BACKLOG. Spec #04 (phase-6 admin-authoring) Status line stale (§11 #19).
- **Status format inconsistency:** `## Status:` (heading-2) vs `**Status:**` (bolded) appear interchangeably. Standardize on heading-2.

---

*End of snapshot. Generated 2026-04-30 at HEAD `<this-slice>` — full regen (no BACKLOG row claimed; CR self-staleness restoration). All 13 sections regenerated from on-disk truth. Slice absorption: B-086a (`210dcb2`) + B-086b (`4aab0bf` cascade-closes B-086 umbrella + E-043). Lineage extends `691934a` → 11 raw commits (2 code-touching, 9 doc/process) → THIS commit. **Closed in this regen:** drift CR §11 #9 (D-020 cross-reference) — `tracker_applications_v2` now carries `jd_hash` + `jd_text` columns + `ix_tracker_apps_jd_hash` index per migration `e043a1b2c3d4`. **NEW drift:** none (D-027 was filed at prior `1b86bf0` and carries forward as item #27). **Milestone:** PRD §1.3 core loop closure — `scan → study → re-scan → improve` is now real product surface; Phase 5 ✅ complete (E-040 + E-041 + E-042 + E-043 all shipped). Drift table active+resolved count 27 (below 30-row archive cut threshold). Next regen recommended once another ~10-commit code-touching delta accumulates (LD-1 sharpened threshold) — likely after slice 6.11 implementation ships or the next P5/P6 feature slice closes.*
