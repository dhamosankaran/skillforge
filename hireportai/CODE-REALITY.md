# CODE-REALITY — SkillForge / HirePort AI

> **Purpose:** frozen-in-time map of the codebase for off-disk advisors (chat-Claude) to draft accurate prompts. If the header sha below doesn't match `git rev-parse --short HEAD`, regenerate this file.
> **Read-only artifact.** Nothing here authorizes code changes.

---

## Section 1 — Repo metadata

| Field | Value |
|-------|-------|
| Commit sha (short) | `192e97d` (B-128 — full regen at this HEAD; closes B-128). **Scope:** all 13 sections regenerated against on-disk filesystem enumeration. **Prior anchor:** `ac0466c` (full regen 2026-05-02, B-110 absorption). **Raw gap:** 57 commits. **Code-touching slice closes in window: 14** — `686a624` E-037 (Pro-tier auth + LLM rate limits hardening), `49aee35` B-008 (deprecated_route_hit telemetry — new `DeprecatedRedirect.tsx`), `0cb10ad` B-009 + B-013 (AGENTS.md — docs, no code), `c4132fb` B-006 + E-015 (settings audit verdict — no code), `ace4584` B-118 (AuthContext `refreshUser()` post-Stripe), `2ae9a69` B-117 (cancel-pending UI bundle — Profile + Pricing), `06ea5f6` B-116 (`customer.subscription.updated` webhook + alembic `c2ba25f1d9a7` adds `Subscription.cancel_at_period_end`), `3fbc252` B-115 (LastScanWidget Rules-of-Hooks crash fix), `7b09116` B-114 + E-033 + E-039 (Stripe SDK v14+ `.get()` → bracket-access hotfix), `5ee327e` B-113 (F-1 Pro short-circuit on /payments/checkout + F-5 STRIPE_* env vars), `b58a42d` B-119 + E-049 (static `<LoopFrame>` on Results), `58bb9a9` B-120 + E-050 (`<HomeStatusHero>` on /home), `261dc66` B-122 + E-051 (live `<LoopProgressStrip>` in AppShell + new `loop_progress_service` + new `GET /api/v1/learn/loop-progress`), `9082a7b` B-125a (career-intent BE half — new `user_career_intents` table + alembic `e052b125a4f1` + service + 3 routes + `pro_digest_service` extension), `e3fdf01` B-125 + E-052 (career-intent FE half — `<CareerGoalSection>` + PersonaPicker CC expansion + `careerIntent.ts` util + 3 api helpers). Process commits in window: B-006/008/009/011/012/013 (audit + docs), B-111/112 (Phase 6 + Stripe audit docs), B-119/120/121/122/123/124/125/126/127 spec-author + §12 amendment + hygiene clusters, 19 SHA-backfill commits. |
| Branch | `main` — at `192e97d`. Local-vs-origin gap: 0 (push state was reconciled mid-session per `git status`). |
| Generated | 2026-05-04 (full regen at HEAD `192e97d`). 57-commit raw gap with 14 code-touching slice closes; **full-scope regen** per prompt — all 13 sections re-anchored. Cleared §11 verification anchor from `ac0466c` to `192e97d`. |
| Backend model files | **29** (`app/models/*.py`, excl. `__init__`, `request_models`, `response_models`). **30** ORM model classes — `analytics_event.py` declares 2 (`QuizReviewEvent` + `LessonViewEvent`) + 28 single-class files. **+1 since `ac0466c`**: `user_career_intent.py` (B-125a — append-only history table per spec #67 §5.1; `UserCareerIntent` UUID PK + user_id FK CASCADE + `target_role`/`target_quarter`/`created_at`/nullable `superseded_at` + 3 composite indexes). |
| Backend service files | **56** top-level (`app/services/*.py`, excl. `__init__.py`). **+2 since `ac0466c`**: `loop_progress_service.py` (B-122 — `get_loop_progress(tracker_id, user_id, db)` per spec #66 §6.1 D-3 skill→category lookup; backs the AppShell loop-progress strip), `career_intent_service.py` (B-125a — `set_intent` append-only supersede + `get_current_intent` + `clear_intent` + `get_aggregate_stats` w/ `MIN_COHORT_SIZE=10` privacy-contract enforcement at the single entry point per spec #67 §4.4). Plus `services/llm/` 3 files + `app/jobs/` 1 file unchanged. **Modified this window:** `pro_digest_service.py` extended by B-125a (composer reads intent + aggregate; `_aggregate_intent_block` try/except → fires `pro_digest_intent_aggregate_failed`; `_build_html` adds `intent_section_style` + `intent_role_label` + `intent_copy` substitutions; send-success path fires `career_intent_email_block_rendered`). |
| Backend schema files | **25** (`app/schemas/*.py`, excl. `__init__.py`). **+2 since `ac0466c`**: `loop_progress.py` (B-122 — `LoopProgressResponse`) + `career_intent.py` (B-125a — `CareerIntentCreate` w/ `ALLOWED_ROLES` frozenset validator + current-or-future quarter validator + `AggregateStats` + `CategoryShare` per spec §5.3/5.4 + D-11). |
| Backend router files | **38** total = **32** v1 + 6 legacy — **+2 since `ac0466c`**: `loop_progress.py` (B-122 — 1 endpoint) + `career_intent.py` (B-125a — 3 endpoints; persona guard 422). |
| Backend endpoints | **~99 unique decorators** (was ~95). +4 this window: `GET /api/v1/learn/loop-progress` (B-122) + `POST/GET/DELETE /api/v1/users/me/career-intent` (B-125a). |
| Alembic revisions | **33** (Head = `e052b125a4f1`). **+2 since `ac0466c`**: `c2ba25f1d9a7` (B-116 — `Subscription.cancel_at_period_end Boolean NOT NULL server_default false`; backfill of 0 rows safe per nullable=False+default) + `e052b125a4f1` (B-125a — new `user_career_intents` table; down_revision `c2ba25f1d9a7` re-confirmed at impl Step 0 per disk truth, NOT spec §7's stale `f1a2b3c4d5e6` placeholder). |
| Frontend pages | **28** (21 top-level + 7 under `pages/admin/`). **Unchanged file count** — slices this window mounted new components inside existing pages (PersonaPicker, Profile, Results, HomeDashboard, AppShell). |
| Frontend components | **89** (excludes `*.test.tsx`). **+5 since `ac0466c`**: `dashboard/LoopFrame.tsx` (B-119 — 4-step "Scanned/Studying/Re-scan/Interview" strip), `home/HomeStatusHero.tsx` (B-120 — one-line persona-aware status sentence), `layout/LoopProgressStrip.tsx` (B-122 — live IP-only AppShell strip), `profile/CareerGoalSection.tsx` (B-125 — CC-gated Profile section), `DeprecatedRedirect.tsx` (B-008 — wraps `<Navigate replace>` + fires `deprecated_route_hit` once-on-mount; consumed by all 10 transitional redirects in `App.tsx`). |
| Frontend utils | **8** utility .ts files in `src/utils/`. **+1 since `ac0466c`**: `careerIntent.ts` (B-125 — `CAREER_ROLES` frozen list + `CAREER_ROLE_LABELS` record + `quarterOptions(now, futureCount=7)` per D-4 + `quarterLabel(value)` formatter). `services/api.ts` extended (+3 helpers): `setCareerIntent` (POST + `X-Capture-Source` header per D-13) / `getCareerIntent` (404 → null via `validateStatus` so the response interceptor does NOT toast on the expected no-intent path) / `clearCareerIntent` (DELETE 204). |
| Shared TS types | `src/types/index.ts` — **+3 exports**: `LoopProgressResponse` (mirrors BE `app/schemas/loop_progress.py` per spec #66 §5) + `CareerIntent` + `CareerIntentCreateRequest` (mirror `app/schemas/career_intent.py` per spec #67 §5.3). |
| Frontend hooks | **22** (`src/hooks/*.ts`). **+1 since `ac0466c`**: `useLoopProgress.ts` (B-122 — fetches `LoopProgressResponse` for the AppShell strip; mirrors `useScoreHistory` shape). |
| Frontend context providers | 5 — unchanged. `AuthContext.tsx` extended by B-118 (`refreshUser()` deduplicated re-fetch of `/auth/me` post-Stripe redirects; concurrent calls coalesce via `inflightRefresh.current`). |
| Skills (tracked) | **22** in `.agent/skills/*.md`. Unchanged count. **Content delta this window:** `analytics.md` +9 rows across slices: `deprecated_route_hit` (B-008), `loop_frame_rendered` (B-119), `home_status_hero_rendered` (B-120), `loop_strip_rendered` + `loop_strip_step_clicked` + `loop_strip_rescan_unlocked` + `loop_strip_step_completed` (B-122), `career_intent_captured` + `career_intent_updated` + `career_intent_email_block_rendered` (B-125a/125), `pro_digest_sent.has_aggregate_block` property (B-125a §9.2), `pro_digest_intent_aggregate_failed` (B-125a §6.5). |
| Skills (untracked) | 3 directory-style — unchanged (see §10 + §12 Q8). |
| Prompts | `app/prompts/` 2 Markdown templates — unchanged. `app/templates/pro_digest.html` extended by B-125a (4th conditional `<div data-section="intent">` block per spec #67 §8.5 D-7 — extends, does NOT fork). |
| Specs | **102 across 8 directories** (phase-0=6, phase-1=13, phase-2=8, phase-3=11, phase-4=6, phase-5=**41**, phase-6=**16**, process=**1**). **+4 since `ac0466c`**, all phase-5: `64-results-loop-frame.md` (B-119 spec-author `8b70037` + §12 amended same impl commit `b58a42d`), `65-home-status-hero.md` (B-120 combined Mode-2 spec+impl `58bb9a9`), `66-appshell-loop-progress-strip.md` (B-122 spec-author `8dcdccd` + §12 amendment `042f92c`), `67-career-climber-role-intent.md` (B-125 spec-author `d407e6e` + §12 amendment `b2248d2`). |
| Tests | **BE 823 passing / 64 failed** (B-127 hygiene measurement under prod-default env vars at HEAD `de226b9`; the 64 failures are D-027/D-028/D-032 cascade carry-forward — full-suite local runs surface the cascade pattern that B-125a's clean-env 877 measurement didn't reproduce). **FE 543 passing** (B-127 hygiene measurement; +77 since `ac0466c`'s 466 baseline: +6 deprecated-route, +10 LoopFrame, +12 HomeStatusHero, +22 LoopProgressStrip + AppShell, +13 career-intent FE half, +2 LastScanWidget regression, +14 misc B-117/118 + B-006 audit). R14 exception (a) — regenerated audit artifact, no test runs this slice. |

**Slice absorption (this regen — code-touching, 14):** Stripe-launch cluster (B-113 + B-114 + B-115 + B-116 + B-117 + B-118 + E-033 + E-039 — 7 fixes spanning webhook handler hardening, Stripe SDK v14+ compatibility, LastScanWidget hook-order crash, `customer.subscription.updated` plumbing, cancel-pending UI surface, AuthContext post-Stripe staleness), security cluster (E-037 — Pro-tier auth + LLM rate limit hardening), nav-cleanup (B-008 — `deprecated_route_hit` telemetry + `<DeprecatedRedirect>` wrapper), Phase-5 design-review impl batch (B-119 + E-049 static `<LoopFrame>`, B-120 + E-050 `<HomeStatusHero>`, B-122 + E-051 live `<LoopProgressStrip>` + new BE `loop_progress_service`), Phase-5 career-climber capture (B-125a BE half — `user_career_intents` table + service + 3 routes + alembic + `pro_digest_service` extension; B-125 + E-052 FE half — `<CareerGoalSection>` + PersonaPicker CC expansion). **Process slices in window:** B-110 prior CR full regen at `ac0466c` (this regen's anchor); B-111 Phase-6 completion assessment audit; B-112 + E-035 Stripe integration audit; B-006 + E-015 zero-gap settings audit verdict; B-009 + B-013 + B-011 + B-012 docs sweeps (AGENTS.md alignment, v2.1 historical-artifact verdict); spec-author + §12 amendment slices for specs #64/#65/#66/#67 (B-119/B-120/B-122/B-123/B-125/B-126); B-121 + B-127 hygiene compactions; B-124 date-bomb test fix.

**Milestone callout — Phase 5 retention-loop infrastructure landed.** With B-119 + B-120 + B-122 (Results loop frame → Home status hero → AppShell live strip), the persona-aware Interview-Prepper home → results → study → re-scan → interview loop is now visible end-to-end across three surfaces. With B-125 + E-052 (career-intent capture + aggregate-only daily digest framing), the Career-Climber persona — previously the silent half of the B2C product — gets target-role + target-quarter capture at PersonaPicker + Profile and peer-aspirational copy in the daily digest (≥10 cohort minimum cell size; ban-list snapshot AC-X enforces aggregate-only privacy contract). E-052 cascade-closed at `e3fdf01`.

**Milestone callout — Stripe production launch readiness.** B-112's audit deliverable (`docs/audits/stripe-integration-audit-2026-05.md`) surfaced 11 findings; F-1 + F-5 (B-113), F-2 + F-4 (B-116), the SDK v14+ webhook hotfix (B-114, also flips E-033 + E-039 ✅), the cancel-pending UI bundle (B-117), and the AuthContext staleness fix (B-118) collectively closed the launch-blocker cluster. Live-mode Stripe Dashboard config + upgrade-flow validation owned by Dhamo per B-111 phase-6 completion-assessment recommendation.

---

## Section 2 — Backend models

All **29** model files under `app/models/` (excl. `__init__`, `request_models`, `response_models`). **30** ORM model classes total — `analytics_event.py` declares 2 (`QuizReviewEvent` + `LessonViewEvent`); other 28 files declare 1 each. Mixins-only file `base.py` excluded from class count. **+1 since `ac0466c`**: `user_career_intent.py` (B-125a `9082a7b`). Cumulative additions tracked in prior regens: `tracker_application_score.py` (B-086a `210dcb2`), `email_log.py` (B-087 `d020f4d`), `card_quality_signal.py` (B-094a `91be54f`).

### `user_career_intent.py` (NEW B-125a, `9082a7b`)
**Class:** `UserCareerIntent` (`app/models/user_career_intent.py:11`)  **Table:** `user_career_intents`

| Column | Type | Notes |
|--------|------|-------|
| id | String(36) PK | UUIDPrimaryKeyMixin |
| user_id | String(36) FK `users.id` ON DELETE CASCADE, indexed | NOT NULL — append-only history (one user → many rows) |
| target_role | String(30) | NOT NULL; validated against frozen 7-value list in `app/schemas/career_intent.py::ALLOWED_ROLES` (D-11) |
| target_quarter | String(7) | NOT NULL; regex `^\d{4}-Q[1-4]$` enforced by Pydantic + current-or-future quarter validator |
| created_at | DateTime(tz) | NOT NULL, server default `now()` |
| superseded_at | DateTime(tz) | NULLABLE — NULL = current row; non-NULL = stamped at the moment a newer row was inserted OR explicit `clear_intent` was called (D-6) |

**Indexes:** `ix_user_career_intents_user_id` `(user_id)`; `ix_user_career_intents_user_current` `(user_id, superseded_at)` — drives current-intent lookup `WHERE user_id=? AND superseded_at IS NULL`; `ix_user_career_intents_bucket_current` `(target_role, target_quarter, superseded_at)` — drives aggregate cohort query. **No `back_populates`** on User per spec §5.2 (avoids N+1 risk in the digest composer's per-user loop). Spec: `docs/specs/phase-5/67-career-climber-role-intent.md` §5.1/§5.2.

### `subscription.py` (modified by B-116, `06ea5f6`)

`Subscription` ORM gains `cancel_at_period_end: Boolean NOT NULL server_default false` via alembic `c2ba25f1d9a7` per spec audit-2026-05 F-2 + F-4 fixes. The `_handle_subscription_updated` webhook dispatcher reads `cancel_at_period_end` / `current_period_end` (unix→naive UTC) / `status` and writes via the B-114 `_field()` helper; plan stays `pro` until `customer.subscription.deleted` fires.

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

### `card_quality_signal.py` (Phase 6 slice 6.13.5a / B-094a, `91be54f`) **— NEW**
**Class:** `CardQualitySignal` (`app/models/card_quality_signal.py:36`)  **Table:** `card_quality_signals` (LD J2 home — unified storage for critique + per-quiz_item user-review aggregate + per-user user-thumbs signals).

| Column | Type | Notes |
|--------|------|-------|
| id | String(36) UUID PK | UUIDPrimaryKeyMixin |
| lesson_id | String(36) FK `lessons.id` ON DELETE CASCADE | NOT NULL |
| quiz_item_id | String(36) FK `quiz_items.id` ON DELETE CASCADE | NULLABLE — NULL = lesson-level signal |
| signal_source | String(20) | NOT NULL — one of `'critique'` / `'user_review'` / `'user_thumbs'` (extensible String, not enum) |
| dimension | String(30) | NOT NULL — per-source vocab: critique → `'accuracy'`/`'clarity'`/`'completeness'`/`'cohesion'`; user_review → `'pass_rate'`; user_thumbs → `'helpful'` |
| score | Numeric(4,2) | NOT NULL — critique normalised `raw/5.0` to [0.20, 1.00]; user_review smoothed pass_rate [0.00, 1.00]; user_thumbs ∈ {-1.00, +1.00} |
| source_ref | String(36) | NULLABLE — provenance pointer (critique → `ingestion_jobs.id`; user_review/user_thumbs → NULL) |
| recorded_by_user_id | String(36) FK `users.id` ON DELETE SET NULL | NULLABLE — non-NULL only for `signal_source='user_thumbs'` |
| recorded_at | DateTime(tz) server_default `func.now()` | NOT NULL — bumps on every UPSERT (§12 D-13) |

**Indexes / constraints:** `ux_card_quality_signals_key` UNIQUE NULLS NOT DISTINCT on `(lesson_id, quiz_item_id, signal_source, dimension, recorded_by_user_id)` via raw-DDL ALTER ADD (see drift D-032); `ix_card_quality_signals_lesson_source` `(lesson_id, signal_source, recorded_at DESC)`; `ix_card_quality_signals_quiz_item_source` partial WHERE `quiz_item_id IS NOT NULL`; `ix_card_quality_signals_user` partial WHERE `recorded_by_user_id IS NOT NULL`.

### `email_log.py` (Phase 6 slice 6.13 / B-087, `d020f4d`) **— NEW**
**Class:** `EmailLog` (`app/models/email_log.py:25`)  **Table:** `email_log` (dedup ledger for the slice 6.14 cron Pro daily digest; supersedes Phase-2 spec #15 `email_send_log`).

| Column | Type | Notes |
|--------|------|-------|
| id | String(36) UUID PK | UUIDPrimaryKeyMixin |
| user_id | String(36) FK `users.id` ON DELETE CASCADE | NOT NULL |
| email_type | String(30) | NOT NULL |
| sent_date | Date | NOT NULL — caller-supplied (timezone-agnostic per OQ-G) |
| resend_id | String(100) | NULLABLE — Resend message id; NULL for dev/CI no-op |
| created_at | DateTime(tz) server_default `func.now()` | NOT NULL |

**Indexes / constraints:** `uq_email_log_user_type_date` UNIQUE on `(user_id, email_type, sent_date)`; `ix_email_log_user_sent_date` composite on `(user_id, sent_date)` mirroring `ix_quiz_review_events_user_reviewed_at` shape.

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
| **`app/api/v1/routes/loop_progress.py`** **NEW B-122 (`261dc66`)** | `/api/v1` | 1 (GET `/learn/loop-progress?tracker_id={id}`) | Phase 5 spec #66 §6.1 D-13. Returns `LoopProgressResponse{total_gap_cards, reviewed_gap_cards, percent_reviewed, days_since_last_scan}`. Backs the AppShell live IP-only loop-progress strip. Auth required + ownership-enforced. |
| **`app/api/v1/routes/career_intent.py`** **NEW B-125a (`9082a7b`)** | `/api/v1` | 3 (POST/GET/DELETE `/users/me/career-intent`) | Phase 5 spec #67 §6.2. POST 201 returns `CareerIntentResponse`; first-vs-subsequent decided by `prior is None` → fires `career_intent_captured` or `career_intent_updated`; reads optional `X-Capture-Source` header per D-13. Persona guard: 422 if `user.persona != 'career_climber'`. GET 200 with current intent or 404 `{detail: "No current career intent"}`. DELETE 204; idempotent no-op when nothing to clear. |
| `app/api/v1/routes/mission.py` | `/api/v1` | 4 | Mission CRUD + active + daily. AGENTS.md says singular `/mission`; actual decorators are plural `/missions/*` (§11 #4). |
| `app/api/v1/routes/progress.py` | `/api/v1` | 2 (radar, heatmap) | Skill radar + activity heatmap. |
| `app/api/v1/routes/quiz_items.py` | `/api/v1` | 3 (daily, review, progress) | Slice 6.2. FSRS quiz-item study. |
| `app/api/v1/routes/ranker.py` | `/api/v1` | 1 (GET `/learn/ranked-decks`) | Slice 6.6 (`5011518`). Lens-ranked deck ordering. |
| `app/api/v1/routes/resume.py` | `/api/v1` | 4 (upload, optimize, get, diff) | Resume storage + AI optimize. |
| `app/api/v1/routes/rewrite.py` | `/api/v1` | (re-export) | Re-export. |
| `app/api/v1/routes/study.py` | `/api/v1` | 4 (daily queue, review, status, dismiss) | FSRS daily card study. |
| `app/api/v1/routes/tracker.py` | `/api/v1` | **5 endpoints** (was 4): list, create, patch, delete, **GET `/tracker/{app_id}/scores` NEW B-086b** | Application tracker CRUD + score history read. New endpoint at `tracker.py:79`. |
| `app/api/v1/routes/users.py` | `/api/v1` | 2 (PATCH persona, POST home-first-visit) | User profile mutations. |

### Flat endpoint table (mount-point convention; **99** appearances)

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
| **GET `/api/v1/learn/loop-progress`** **NEW B-122** | `loop_progress.py` |
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
| **POST `/api/v1/users/me/career-intent`** **NEW B-125a** | `career_intent.py:53` |
| **GET `/api/v1/users/me/career-intent`** **NEW B-125a** | `career_intent.py:100` |
| **DELETE `/api/v1/users/me/career-intent`** **NEW B-125a** | `career_intent.py:118` |

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

### Top-level `app/services/` (56 files)

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
| **`loop_progress_service.py`** **NEW B-122 (`261dc66`)** | `get_loop_progress(tracker_application_id, user_id, db) -> LoopProgressResponse` | Phase 5 spec #66 §6.1 — backs the AppShell live IP-only loop-progress strip. Skill→category lookup per D-3 (no card-tag traversal v1). Returns `{total_gap_cards, reviewed_gap_cards, percent_reviewed, days_since_last_scan}`. Ownership-enforced via `tracker_service_v2.get_application_model_by_id`. |
| **`career_intent_service.py`** **NEW B-125a (`9082a7b`)** | `set_intent` / `get_current_intent` / `clear_intent` / `get_aggregate_stats` | Phase 5 spec #67 §6.1. `set_intent` is append-only with explicit supersede — stamps prior current row's `superseded_at=now()` then INSERTs new row. `get_current_intent` queries `WHERE user_id=? AND superseded_at IS NULL`. `clear_intent` stamps `superseded_at=now()` without INSERT (D-6 explicit clear semantics). **`get_aggregate_stats(target_role, target_quarter)` is the single privacy-contract enforcement point** per §4.4 — counts distinct cohort users with current intent in bucket; if `cohort_size < MIN_COHORT_SIZE` (=10), returns `None` (composer omits the digest block silently per D-8); otherwise returns `AggregateStats{cohort_size, top_categories: [CategoryShare(name, percent_of_study_time)]}`. Aggregate query: `CardProgress.reps × Category` join (D-033 — spec §6.1's `quiz_review_events JOIN cards` was structurally inconsistent on disk; legacy FSRS surface is where CC users have data today). |
| `mission_service.py` | Mission CRUD + active + daily card pull. |  |
| `nlp.py` | `extract_skills`, `extract_job_requirements` | spaCy wrapper utilities. |
| `object_storage_service.py` (slice 6.10a) | `ObjectStorageService:40` class, `ObjectStorageError:31`, `get_storage:87` factory | R2 (Cloudflare) artifacts adapter. |
| `onboarding_checklist_service.py` | First-action checklist computation. |  |
| `parser.py` | `parse_pdf`, `parse_docx` | PDF/DOCX → text extraction (returns dict with `full_text`, `formatting_hints`, `bullet_points`). |
| `payment_service.py` | Stripe checkout/portal/webhook handling. |  |
| `paywall_service.py` | Paywall dismissal grace logic. Spec #42. |  |
| **`pro_digest_service.py`** **NEW B-098 (`bcd89ce`); EXTENDED by B-125a (`9082a7b`)** | `select_candidates`, `compose_digest`, `send_pro_digest` (+ B-125a internals: `_aggregate_intent_block`, `_intent_block_copy`, `_build_html` substitutions) | Phase 6 slice 6.14 base + Phase 5 spec #67 §6.3 extension. Composer extension reads current intent + aggregate via `career_intent_service.get_current_intent` + `get_aggregate_stats` (try/except → fires `pro_digest_intent_aggregate_failed` on errors with graceful None fallback per spec §6.5). Strict empty-rule extended additively per §6.3 — a CC user with intent + cohort still gets a digest even if cards/mission/scan are empty (additive carve-out vs spec #6/14 D-7). `_build_html` adds `intent_section_style` + `intent_role_label` + `intent_copy` substitutions; `_intent_block_copy` formats aggregate copy with the §8.5 ban-list-safe phrasing ("Engineers targeting {role} this quarter spend X% on {cat}…"). Send-success path fires `career_intent_email_block_rendered` per D-13 (gated on `payload.aggregate_intent_block is not None` — only fires on actual `email_service.send_email` success path, not test-render). `pro_digest_sent` event payload gains `has_aggregate_block: bool` per §9.2. **Service is flush-only**; CLI commits post-orchestrator so `email_log` rows persist past the tick (B-098 JC #1 carry — moved commit from service to CLI for test-fixture rollback isolation). |
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
- **`app/scripts/send_pro_digest.py`** **NEW B-098 (`bcd89ce`)** — `python -m app.scripts.send_pro_digest`. Entry point for the daily Pro digest Railway cron tick (`schedule = "0 14 * * *"` UTC per §12 D-1). 43-line CLI mirrors `seed_phase6.py` boot pattern: opens a session via `SessionLocal()`, calls `pro_digest_service.send_pro_digest(db)`, commits the session post-orchestrator (the service itself is flush-only — committing inside the service breaks `conftest.py db_session` rollback isolation per JC #1 from B-098 impl), logs the `SendSummary`, exits 0 on success or non-zero on uncaught exception. No FastAPI endpoint surface — by design per §12 D-2 (no auth surface to design for a server-internal tick).
- **`app/utils/local_time.py`** **NEW B-102 (`e36902c`)** — small util module hosting `next_local_midnight(now_utc, tz_name) -> datetime` (the function publicly renamed from the prior leading-underscore `_next_local_midnight` per §12 D-3; helper deleted from `study_service.py` + `quiz_item_study_service.py` to satisfy DRY per spec #15 T7.2). 3 callsites flipped (`study_service.py:241`, `:289` + `quiz_item_study_service.py:211`).

---

## Section 5 — Alembic revisions

**33 revisions** in `hirelens-backend/alembic/versions/`. Linear chain. **Head: `e052b125a4f1`** — **+2 since `ac0466c`**: `c2ba25f1d9a7` (B-116 — `Subscription.cancel_at_period_end Boolean NOT NULL server_default false` per audit-2026-05 F-2 + F-4 fixes) + `e052b125a4f1` (B-125a — new `user_career_intents` table + 3 composite indexes per spec #67 §5.1/5.2). Both additive; both round-trip clean (`upgrade head → downgrade -1 → upgrade head` integration-marked tests).

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
| `e043a1b2c3d4` | Phase 5 E-043 / B-086a — `jd_text` + `jd_hash` columns on `tracker_applications_v2` + `ix_tracker_apps_jd_hash` (Q1 LOCK; closes drift D-020) AND `tracker_application_scores` table + 3 indexes (Q2 LOCK) | `c4e21d8a7f12` |
| `f1a2b3c4d5e6` | Phase 6 slice 6.13 / B-087 — additive `email_preferences.daily_digest_opt_out` (server-default false) + new `email_log` table (UUID PK + UNIQUE `(user_id, email_type, sent_date)` + composite index `(user_id, sent_date)` + CASCADE FK to `users.id`); precondition for slice 6.14 cron daily Pro digest | `e043a1b2c3d4` |
| `c2b8a4d9e6f1` | Phase 6 slice 6.13.5a / B-094a — new `card_quality_signals` table per LD J2 (5-tuple UNIQUE on `(lesson_id, quiz_item_id, signal_source, dimension, recorded_by_user_id)` with `NULLS NOT DISTINCT` via raw-DDL `ALTER TABLE ADD CONSTRAINT`; 1 partial `quiz_item_source` WHERE quiz_item_id IS NOT NULL + 1 partial `user` WHERE recorded_by_user_id IS NOT NULL + 1 full `lesson_source`; CASCADE on lesson_id + quiz_item_id, SET NULL on recorded_by_user_id) | `f1a2b3c4d5e6` |
| `c2ba25f1d9a7` | **NEW B-116** — Phase 5 audit-2026-05 F-2/F-4 — additive `subscriptions.cancel_at_period_end Boolean NOT NULL server_default false`. Backfill is no-op (column NOT NULL with default; existing rows get false). | `c2b8a4d9e6f1` |
| **`e052b125a4f1`** | **NEW B-125a (HEAD)** — Phase 5 spec #67 §5.1 — new `user_career_intents` table (UUID PK + `user_id` FK CASCADE + `target_role`/`target_quarter` String + `created_at` server-default + nullable `superseded_at`) + 3 composite indexes (`user_id`, `(user_id, superseded_at)` for current-intent lookup, `(target_role, target_quarter, superseded_at)` for cohort aggregate). Down_revision `c2ba25f1d9a7` re-confirmed at impl Step 0 — spec §7's `f1a2b3c4d5e6` placeholder was stale by 1 head when B-125a impl ran (stale by 2 heads at this regen since B-116 also intervened). | `c2ba25f1d9a7` |

(Other 16 revisions are middle-of-chain Phase 1–5 migrations. Full enumeration via `ls hirelens-backend/alembic/versions/*.py`.)

The `e043a1b2c3d4` migration bundles two locked decisions per spec #63 §1.3 + §7. Both nullable per D-10 (no backfill of pre-migration rows; the `/rescan` route returns 422 with explicit copy when `jd_text=NULL` per D-9). FK shapes per spec §5.3:

- `tracker_application_id` → `tracker_applications_v2.id` ON DELETE **CASCADE** (history dies with the tracker row).
- `user_id` → `users.id` ON DELETE **CASCADE** (denormalized FK, mirrors slice 6.0 D-1 / D-7 convention).
- `scan_id` carries no FK on disk because no `scans` table exists (matches the `tracker_applications_v2.scan_id` shape — see B-086a JC #2).

**AC-12 / AC-15 verification:** alembic round-trip clean (`upgrade head → downgrade -1 → upgrade head`); column presence + index presence verified shell-side at B-086a impl close. Integration test `tests/test_e043_jd_columns_migration.py` (single test, `@pytest.mark.integration`-gated per R13) covers the round-trip in CI.

CI migration-rollback job at `.github/workflows/ci.yml:101-149` runs `alembic upgrade head` → `downgrade -1` → `upgrade head` to verify reversibility on every push.

---

## Section 6 — Frontend routes (live component graph)

Routes declared in `src/App.tsx`. Public + protected, with namespace migration (`/learn/*` study + `/prep/*` interview prep) and transitional `<Navigate replace>` shims. **B-008 (`49aee35`) wraps all 10 transitional shims in `<DeprecatedRedirect from="/x" to="/y" />`** — fires `deprecated_route_hit{from_path, to_path}` once-on-mount via `useRef` guard; legacy `RedirectWithParam` helper deleted. Route table itself unchanged (B-119/B-120/B-122/B-125 mount new components inside existing pages, not new routes).

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

### Component graph (89 components, organized by directory)

| Directory | Files | Notes |
|---|---|---|
| `components/admin/` | `AdminLayout.tsx`, `ConfirmCascadeModal.tsx`, `ConfirmPersonaNarrowingModal.tsx`, `MarkdownEditor.tsx` | Slice 6.4a + 6.4b. |
| `components/auth/` | `AdminGate.tsx` | E-040 frontend admin guard. |
| `components/dashboard/` | 16 components — 10 ATS-analysis panels (consumed by `pages/Results.tsx`) + 5 slice 6.8 FSRS-dashboard sections (consumed by `pages/Dashboard.tsx`) + **`LoopFrame.tsx` NEW B-119** (4-step horizontal-at-md+/vertical-stack-<md strip with `surface: 'results' \| 'appshell'`, `compact?` prop, `stepStates?: Partial<Record<step, state>>`, `onStepClick?` — backward-compatible extension per §4.1 hybrid a+c lock; `loop_frame_rendered` analytics suppressed when `surface === 'appshell'` per D-4 to avoid double-counting). |
| `components/home/` | `DashboardWidget`, `StateAwareWidgets` + `HomeStatusHero.tsx` (NEW B-120) + `widgets/` (16 widgets) | Spec #40 / #61 / #62 / #65 / #66 home composition. |
| `components/home/HomeStatusHero.tsx` (**NEW B-120**) | One-line `<p>` mounted in `HomeDashboard.tsx` between greeting `<h1>` and `<StateAwareWidgets>` per spec #65 D-1. IP copy `${company} interview in ${days}d. ${dueCount} cards due today. Last scan was ${score}%.`; CC copy `${streak}-day streak. ${dueCount} cards due today.`; clauses omit gracefully on null/zero/error. team_lead returns null. Reads `useAuth` + `useHomeState` + `fetchDailyQueue` + `fetchUserApplications` (IP only). Fires `home_status_hero_rendered{persona, plan, clauses_shown[]}` once-on-mount via `useRef`. R12 token-only styling. |
| `components/home/widgets/` | `CountdownWidget`, `FirstSessionDoneWidget`, `HomeScoreDeltaWidget` (B-086b), `InactiveReturnerWidget`, `InterviewPrepperChecklist`, `InterviewTargetWidget`, `LastScanWidget`, `MissionActiveWidget`, `MissionOverdueWidget`, `ResumeStaleWidget`, `StreakAtRiskWidget`, `StreakWidget`, `StudyGapsPromptWidget`, `TeamComingSoonWidget`, `TodaysReviewWidget`, `WeeklyProgressWidget` | **16 files**. `LastScanWidget.tsx` modified by B-115 (`3fbc252`): early-return moved AFTER all hooks (Rules-of-Hooks compliance — prior `if (suppressed) return null` BEFORE `useCallback`/`useEffect` crashed the ErrorBoundary subtree). |
| `components/layout/` | `AppShell`, `MobileNav`, `Navbar` *(unused — §9)*, `PageWrapper`, `TopNav`, `UserMenu`, **`LoopProgressStrip.tsx` NEW B-122** | AppShell mounts TopNav (md:+) and MobileNav + new `<LoopProgressStrip>` as sibling below TopNav (D-8 placement). |
| `components/layout/LoopProgressStrip.tsx` (**NEW B-122**) | Live IP-only AppShell loop strip. Render gate `persona === 'interview_prepper' && next_interview != null` (chromeless gated by parent `showChrome`). Hook composition: `useAuth` + `useHomeState` + `useScoreHistory(tracker_id)` + `useLoopProgress(tracker_id)`. Step-state derivation per spec #66 §8.2 (D-1 heuristic for step 3 'done'; INTERVIEW_ALERT_WINDOW_DAYS=7; MIN_DAYS_SINCE_SCAN=3; MIN_PERCENT_REVIEWED=50). Step 3 click → `/prep/tracker?focus={id}&action=rescan`. 4 PostHog events: `loop_strip_rendered` (once-per-mount keyed on tracker_id), `loop_strip_step_clicked` (step 3 only), `loop_strip_rescan_unlocked` (locked→current via `useRef<boolean>`), `loop_strip_step_completed` (per-step via `useRef<Set<step>>` Strict-Mode idempotent per D-12). |
| `components/learn/` | `RankedDeckList.tsx` | Slice 6.7. |
| `components/lesson/` | `LessonRenderer`, `QuizItemPanel`, `ThumbsControl` | Slice 6.3 + 6.13.5b. |
| `components/mission/` | `Countdown`, `DailyTarget`, `MissionDateGate`, `MissionSetup` | Mission-mode chrome. |
| `components/onboarding/` | `GuidedTour` *(unused — §9)* | — |
| `components/profile/` | `StreakBadge`, `XPBar`, **`CareerGoalSection.tsx` NEW B-125** | CC-gated section in `Profile.tsx` between Theme and Subscription. Inline-form modality per spec #67 D-2; `[Clear]` button via `window.confirm` per D-6. Self-loads via `getCareerIntent()` on mount; renders 2 states (no-intent CTA / has-intent display + Edit + Clear). Submit fires `career_intent_captured` (first) / `career_intent_updated` (subsequent + cleared semantics) with `source: 'profile_edit'`. |
| `components/progress/` | `ActivityHeatmap`, `SkillRadar` | Spec #13. |
| `components/rewrite/` | `CoverLetterViewer`, `ResumeEditor`, `ResumePDFTemplate` *(unused — §9)* | — |
| `components/settings/` | `EmailPreferences`, `ThemePicker` | — |
| `components/study/` | `CategoryCard`, `DailyReviewWalledView`, `FlipCard`, `QuizPanel`, `WallInlineNudge` | — |
| `components/tracker/` | `ApplicationCard`, `KanbanBoard`, `ScoreDeltaWidget` (B-086b) | 3 files. |
| `components/ui/` | `AnimatedCard`, `GlowButton`, `ProgressBar`, `ScoreBadge`, `SkeletonLoader`, `Tooltip`, `UpgradeModal`, `SentryFallback` (B-115 dev-mode diagnostic) | App-root `<UpgradeModal>` mounted in `main.tsx`. |
| `components/upload/` | `JDInput`, `ResumeDropzone` | — |
| `components/PaywallModal.tsx` | (top-level, not in a subdir) | Modal triggered by paywall events. |
| `components/PersonaGate.tsx` | (top-level) | Persona-null routing guard. |
| **`components/DeprecatedRedirect.tsx`** **NEW B-008 (`49aee35`)** | (top-level) | Wraps `<Navigate replace>` and fires `deprecated_route_hit{from_path, to_path}` once-on-mount via `useRef` guard. Consumed by all 10 transitional redirects in `App.tsx`; legacy `RedirectWithParam` helper deleted. |

### B-086b mount-point absorption

**`<ScoreDeltaWidget>`** — Tracker focused-row inline-expand block. Mounted at `pages/Tracker.tsx:205` inside the focused-row's expanded panel (immediately after the interview-date editor row). Self-loads via `useScoreHistory(focusedRow.id)`. Three render states by history length:

- 0 rows → empty CTA `data-testid="score-delta-widget-empty"` ("Re-scan this application to see how your resume has improved.").
- 1 row → first-scan baseline `data-testid="score-delta-widget-baseline"` (overall score + "Re-scan after improving your resume to see the delta.").
- 2+ rows → full delta render `data-testid="score-delta-widget"` with overall before→after + 4 per-axis delta rows (`Keyword match` / `Skills coverage` / `Formatting` / `Bullets`) + days-between footnote when `days_between > 0`. Per-axis values rendered from BE-pre-computed `ScoreDelta` (D-6 — FE never re-does the math).

Loading + error states surfaced via `data-testid="score-delta-widget-loading"` / `data-testid="score-delta-widget-error"`. Re-scan trigger UX is intentionally NOT inside this widget — the spec describes the data display surface; the trigger is wired by the parent (Tracker.tsx) when resume_text is available.

**`<HomeScoreDeltaWidget>`** — Home dashboard `interview_prepper`-only variant. Mounted at `pages/HomeDashboard.tsx:54` directly below `<CountdownWidget>` inside the `InterviewPrepperMode` JSX (D-5 — same `tracker_id` as CountdownWidget; both widgets surface the same tracker row). Self-loads via `useScoreHistory(trackerId ?? null)`. **Render gate:** `trackerId != null && history.length >= 2`. Cold-start (single history row) hides the widget entirely (no empty state on the home dashboard — minimalism per spec #61). Renders inside the standard `<DashboardWidget>` chrome with title "Score improvement" + view-detail action linking to `/prep/tracker?focus=${trackerId}`. `company` prop carries the display label routed in from CountdownWidget's `next_interview` source.

---

## Section 7 — Frontend pages

**28 files** (21 top-level in `src/pages/` + 7 under `pages/admin/`). **Unchanged file count this window** — slices this window mounted new components inside existing pages (PersonaPicker CC expansion, Profile CareerGoalSection mount, Results LoopFrame mount, HomeDashboard HomeStatusHero mount, AppShell LoopProgressStrip mount).

| File | Mounted at | Notes |
|------|-----------|-------|
| `pages/AdminAnalytics.tsx` | `/admin/analytics` (lazy) | Spec #38 / E-018b dashboard. |
| `pages/Analyze.tsx` | `/prep/analyze` | ATS scan upload. App-root `<UpgradeModal>` triggered via `setShowUpgradeModal(true)` (spec #60 LD-1). |
| `pages/CardViewer.tsx` | `/learn/card/:id` | Single-card flip view. |
| `pages/CategoryDetail.tsx` | `/learn/category/:id` | Category card list. Comment at line 13 references the deleted `StudyDashboard` (stale; harmless — §9). |
| `pages/DailyReview.tsx` | `/learn/daily` | FSRS daily review flow. |
| `pages/Dashboard.tsx` | `/learn/dashboard` | Slice 6.8 user-self FSRS dashboard. |
| `pages/FirstAction.tsx` | `/first-action` | Spec #46 one-CTA interstitial. |
| `pages/HomeDashboard.tsx` | `/home` | Spec #34/#40 persona-aware home. 3 inline render modes (career_climber / interview_prepper / team_lead). **Modified by B-086b** (HomeScoreDeltaWidget mount) and **B-120** (`<HomeStatusHero>` mounted between greeting `<h1>` and `<StateAwareWidgets>` per spec #65 D-1, sibling-of-persona-mode JSX). |
| `pages/PersonaPicker.tsx` | `/onboarding/persona` | Persona selection (spec #34 / #67). **Modified by B-125** — CC card auto-expands on select (D-1) showing optional `target_role` + `target_quarter` selects mirroring IP precedent. Submit fires `setCareerIntent(...)` after `updatePersona` only when both fields filled (AC-19/20/21 per §8.1; failure toasts "Goal not saved — set it from Profile." + nav still proceeds). |
| `pages/Profile.tsx` | `/profile` (lazy) | User settings. **Modified by B-117** (Reactivate Pro button when `cancelAtPeriodEnd===true` — opens Stripe portal), **B-118** (`refreshUser()` on mount per Stripe portal return), **B-125** (`<CareerGoalSection>` mount between Theme and Subscription, CC-gated). |
| `pages/Pricing.tsx` | `/pricing` | Stripe pricing card. Geo-routed via IP (Phase 3). **Modified by B-117** (cancel-pending Pro tile swaps "Current Plan" → "Cancels {date}"; `handleCta` opens portal in cancel-pending state, sidestepping B-113 `AlreadyProError`) + **B-118** (`refreshUser()` on `?upgrade=success` post-checkout branch). |
| `pages/Results.tsx` | `/prep/results` | ATS scan results detail. **Modified by B-119** — `<LoopFrame>` mounted ABOVE the dashboard grid container as sibling element (NOT 12th grid child — JC #1 to avoid 11-row-shift cascade). `useHomeState` newly imported for D-8 `next_interview` source. Render-gated on `result.ats_score != null`. |
| `pages/Interview.tsx` | `/prep/interview` | Interview Q generator + persistence. |
| `pages/LandingPage.tsx` | `/` (guests) | Public marketing landing. |
| `pages/Learn.tsx` | `/learn` | Slice 6.7 — three inline persona-mode functions. |
| `pages/Lesson.tsx` | `/learn/lesson/:id` | Slice 6.3 lesson viewer. |
| `pages/LoginPage.tsx` | `/login` | Google OAuth flow. |
| `pages/MissionMode.tsx` | `/learn/mission` (lazy) | Interview sprint mode. |
| `pages/Onboarding.tsx` | `/onboarding` | Welcome flow before persona. |
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

### `src/types/index.ts` (~830 lines, 63 exports)

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

### Phase 5 spec #66 loop-progress types (NEW B-122, `261dc66`)

```ts
LoopProgressResponse:166  // tracker_application_id, total_gap_cards,
                           // reviewed_gap_cards, percent_reviewed,
                           // days_since_last_scan
```

Mirrors BE `app/schemas/loop_progress.py::LoopProgressResponse`. Consumed by `useLoopProgress.ts` + `<LoopProgressStrip>`.

### Phase 5 spec #67 career-intent types (NEW B-125, `e3fdf01`)

```ts
CareerIntent:177            // id, user_id, target_role, target_quarter,
                             // created_at, superseded_at | null
CareerIntentCreateRequest:186 // target_role, target_quarter
```

Mirrors BE `app/schemas/career_intent.py`. Consumed by `<CareerGoalSection>` + 3 api helpers in `services/api.ts` (`setCareerIntent` POST + `X-Capture-Source` header per D-13; `getCareerIntent` 404 → null via `validateStatus` so the response interceptor does NOT toast on the expected no-intent path; `clearCareerIntent` DELETE 204).

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

No components found behind `{false && …}` guards or dormant feature flags at HEAD `1ca046f`. **Background-job framework ACTIVE** as of slice 6.10b (`8735373`) — RQ-on-Redis worker (`app/jobs/ingestion_worker.py`) is the first runtime consumer. **B-086b adds NO new background-job consumer** — the rescan flow is fully synchronous (LLM call inside the request handler with try/except + 502 mapping); no `enqueue` to any queue. Cron architecture decision still pending at B-078 🟦.

---

## Section 10 — Skills inventory

### Tracked skills (`.agent/skills/*.md`, 22 files)

| File | Description |
|------|-------------|
| admin-panel.md | Card CRUD, bulk import, AI-assisted card generation (Phase 3) |
| analytics.md | PostHog event catalog (frontend + backend), funnels, conventions. **Modified this window** by B-008 (+1 `deprecated_route_hit{from_path, to_path}`), B-117 (+1 `subscription_portal_opened` w/ `source: 'pricing_reactivate'`), B-119 (+1 `loop_frame_rendered{surface, current_step, has_interview_date, plan}`), B-120 (+1 `home_status_hero_rendered{persona, plan, clauses_shown[]}`), B-122 (+4 `loop_strip_rendered` / `_step_clicked` / `_rescan_unlocked` / `_step_completed`; existing `loop_frame_rendered` row note updated for surface widening + appshell suppression), B-125a (+3 `career_intent_captured` / `_updated` / `_email_block_rendered` + `pro_digest_sent.has_aggregate_block: bool` property + 1 failure event `pro_digest_intent_aggregate_failed`). Net delta: +12 rows + 1 property + 1 row note update. Content-only delta — file count unchanged. |
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

Re-verified at HEAD `192e97d`. **One new drift item this window** — D-033 (spec #67 §6.1 `quiz_review_events JOIN cards` structurally inconsistent with on-disk `QuizReviewEvent` keyed on `quiz_items`; resolved at B-125a impl by aggregating `CardProgress.reps × Category` instead, runtime correct). Five carry-forward ✅ RESOLVED rows (D-016, D-019, D-020, D-022, D-029) cut to `docs/archive/session-state-history.md` §10 by B-127 hygiene compaction (this regen window). All remaining drift items re-verified against current HEAD; status lines reflect `192e97d` reality. Items #9, #18, #19, #20, #22, #23 carry forward as RESOLVED (kept for traceability per existing CR convention).

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

28. **D-028 — alembic-roundtrip cascade fragility.** Surface: marker-gated integration tests (`@pytest.mark.integration`) that run `alembic upgrade head → downgrade -1 → upgrade head` against the test database. Multiple round-trip tests in one process interfere; mid-suite schema corruption breaks downstream tests. Cascade size scales with the alembic chain: 4 fails at slice 6.11 baseline → 25 fails at slice 6.13 ship (chain extension) → 10 fails at slice 6.13.5a → 15 fails at slice 6.13.5b. **Material impact: ZERO on CI** — CI runs `-m "not integration"` per R13; cascade is local-dev-only. Close shape: separate Mode 3 scout slice that drops affected tables explicitly + re-stamps `alembic_version` to head + `Base.metadata.create_all` between integration tests, OR pytest-alembic fixture isolation. Tracking-only across all subsequent slices. Filed at SESSION-STATE drift table around slice 6.11 (B-084 baseline measurement). **Status: open (carry-forward) — non-blocking, tracking-only.**

29. **D-030 — spec `user.is_admin` shorthand vs disk reality.** Surface: `docs/specs/phase-6/13-pro-digest-opt-out.md` §6.4 (and any future spec authoring against this one as precedent). Disk: `app/models/user.py` `role` String column (admin = `"admin"`); precedent `(user.role or "user") == "admin"` per `study_service.py:193` / `usage_service.py:288`. No `is_admin` boolean attribute exists on the User model. Surfaced as JC #2 during B-087 impl (resolved correctly via existing precedent; runtime unaffected). Close shape: either (a) spec-author convention update banishing `is_admin` shorthand (cheaper) or (b) add `is_admin` as a computed property on the User model so spec shorthand becomes literal. Filed at `a7145a7` (2026-05-01). **Status: open (carry-forward) — cosmetic / documentation, non-blocking.**

30. **D-032 — spec `(NULLS-distinct)` parenthetical vs `NULLS NOT DISTINCT` migration intent.** Surface: `docs/specs/phase-6/12-quality-signals.md` §5.1 parenthetical after the UNIQUE constraint description. Disk: alembic `c2b8a4d9e6f1` applies UNIQUE with `NULLS NOT DISTINCT` (Postgres 15+) via raw-DDL `ALTER TABLE ADD CONSTRAINT` since SQLAlchemy 2.0.49's `UniqueConstraint(postgresql_nulls_not_distinct=True)` covers `create_all` only — default Postgres semantics (NULLS DISTINCT) would re-INSERT critique rows where `quiz_item_id` + `recorded_by_user_id` are both NULL instead of UPSERT-conflicting. Surfaced as JC #2 during B-094a impl (resolved correctly; runtime unaffected). Close shape: one-character correction in §5.1 from "NULLS-distinct" to "NULLS NOT DISTINCT" — surgical doc edit. Filed at `3981560` (2026-05-02). **Status: open (carry-forward) — cosmetic / documentation, non-blocking.**

31. **D-033 — spec #67 §6.1 sketch references `quiz_review_events JOIN cards` but `QuizReviewEvent` keys on `quiz_items` not `cards`.** Surface: `docs/specs/phase-5/67-career-climber-role-intent.md` §6.1 inline comment. Disk: `app/models/analytics_event.py::QuizReviewEvent` FKs `quiz_items.id`, NOT `cards.id`; the two surfaces don't share a join column (no `quiz_item.card_id` exists). Spec comment as written would not type-check. Surfaced as JC #1 during B-125a impl (`9082a7b`); resolved at impl time by aggregating `CardProgress.reps × Category` instead (legacy FSRS surface where CC users currently have study data). Tests pass; aggregate-block populates correctly. **Close shape:** spec §6.1 amendment to either (a) replace the comment with the on-disk reality (`CardProgress.reps × Category` join — pragmatic v1, cheaper close) or (b) gate impl on a future Phase-6 generalization that promotes CC users onto `quiz_items` content. Filed at SESSION-STATE drift table at B-125a impl. **Status: open (carry-forward) — cosmetic / spec-comment, runtime unaffected, non-blocking.**

### Recently closed in this regen window

- **D-016, D-019, D-020, D-022, D-029** — 5 ✅ RESOLVED rows cut to `docs/archive/session-state-history.md` §10 by B-127 hygiene compaction (`401b95d`, 2026-05-04). The drift items themselves were resolved in earlier slices; this regen window saw the archive migration only.
- **D-033 (NEW this window)** — spec #67 §6.1 / on-disk `QuizReviewEvent` FK shape mismatch. See item #31. Filed at B-125a impl; runtime unaffected.

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

Walked `docs/specs/**/*.md` — **102 spec files across 8 directories** (phase-0..phase-6 + `process/`). **+4 since `ac0466c`**, all phase-5: `64-results-loop-frame.md` (B-119 spec-author `8b70037` + §12 amended same impl commit `b58a42d` per combined-slice precedent), `65-home-status-hero.md` (B-120 combined Mode-2 spec+impl `58bb9a9`; §12 D-1..D-10 pre-locked at spec-author), `66-appshell-loop-progress-strip.md` (B-122 spec-author `8dcdccd` + §12 amendment `042f92c` D-1..D-14 from §14 OQ-1..OQ-14), `67-career-climber-role-intent.md` (B-125 spec-author `d407e6e` + §12 amendment `b2248d2` D-1..D-14 from §14 OQ-1..OQ-14).

### Per-phase counts
| Phase | Files | With explicit Status line | No status field |
|-------|-------|---------------------------|-----------------|
| phase-0 | 6 | 6 | 0 |
| phase-1 | 13 | 6 | 7 |
| phase-2 | 8 | 7 | 1 |
| phase-3 | 11 | 8 | 3 |
| phase-4 | 6 | 6 | 0 |
| phase-5 | **41** | 19 | 22 |
| phase-6 | **16** | 16 | 0 |
| process | **1** | 1 | 0 |
| **Total** | **102** | **69** | **33** |

### Status legend
`Done` · `Complete` · `Implemented — Spec Backfill Pending (P5-S###)` · `Draft` · `Drafted, not shipped` · `Shipped (spec + impl)` · `Done — Shipped in <sha>` · `Partially Done` · `Planned — Known-Broken` · `Deferred` · `Complete — Spec Backfill Pending`

### Slice absorption log (this regen — full-scope at `192e97d`)

| Slice | Spec | BACKLOG | Closing commit | Notes |
|---|---|---|---|---|
| B-128 | (this regen) | B-128 ✅ | `4655be9` | **CR full regen at HEAD `192e97d`.** All 13 sections re-anchored. R14 exception (a) — regenerated audit artifact, no test runs. Two-commit pattern (regen + SHA backfill replacing `4655be9` placeholders). |
| B-125 + E-052 | `phase-5/67-career-climber-role-intent.md` | B-125 ✅ + E-052 ✅ (cascade) | `e3fdf01` | **Phase 5 spec #67 FE half — CC career-intent capture surfaces.** New `<CareerGoalSection>` mounted in `Profile.tsx` between Theme + Subscription (CC-gated per §8.2 D-2 inline-form + D-6 explicit `[Clear]` via `window.confirm`); PersonaPicker CC card auto-expand (D-1) carrying optional `target_role` + `target_quarter` selects mirroring IP precedent (submit fires `setCareerIntent` after `updatePersona` only when both filled — AC-19/20/21); new `src/utils/careerIntent.ts` (CAREER_ROLES + labels + `quarterOptions(now, 7)` per D-4 + `quarterLabel`); `services/api.ts` adds 3 helpers (POST + GET 404→null via `validateStatus` + DELETE); `types/index.ts` gains `CareerIntent` + `CareerIntentCreateRequest`. PostHog `career_intent_captured` (first) / `career_intent_updated` (subsequent + cleared semantics). Tests +13 FE (5 PersonaPicker + 5 Profile + 3 api). FE 530 → 543. |
| B-125a | `phase-5/67-career-climber-role-intent.md` | B-125a ✅ | `9082a7b` | **Phase 5 spec #67 BE half — append-only `user_career_intents` + privacy-safe aggregate digest framing.** New `app/models/user_career_intent.py` (UUID PK + user_id FK CASCADE + 3 composite indexes per §5.1/5.2), `app/schemas/career_intent.py` (`CareerIntentCreate` w/ `ALLOWED_ROLES` frozenset validator + current-or-future quarter validator + `AggregateStats` + `CategoryShare` per §5.3/5.4 D-11), alembic `e052b125a4f1` (down_revision `c2ba25f1d9a7` per actual head, NOT spec §7's stale `f1a2b3c4d5e6`), `app/services/career_intent_service.py` (set/get/clear/get_aggregate_stats with `MIN_COHORT_SIZE=10` privacy-contract single entry point per §4.4), 3 routes at `app/api/v1/routes/career_intent.py` (POST 201 / GET 200/404 / DELETE 204; persona guard 422 with `X-Capture-Source` header per D-13). **Composer extension:** `pro_digest_service` reads intent + aggregate (try/except → `pro_digest_intent_aggregate_failed` per §6.5; strict-empty-rule extended additively per §6.3); `_build_html` adds intent_section_style + intent_role_label + intent_copy substitutions; send-success path fires `career_intent_email_block_rendered` per D-13. **Template:** `pro_digest.html` adds 4th `<div data-section="intent">` block per D-7. **Analytics:** 3 new event rows + `pro_digest_sent.has_aggregate_block` property + 1 failure event. Tests +30 BE. **JC #1:** spec §6.1 said `quiz_review_events JOIN cards` but `QuizReviewEvent` keys on `quiz_items` — used `CardProgress.reps × Category` (drift D-033). |
| B-126 | `phase-5/67-career-climber-role-intent.md` | B-126 ✅ | `b2248d2` | Spec #67 §12 amendment locking D-1..D-14 from §14 OQ-1..OQ-14. R14 exception (b) — pure rule refinement. |
| B-122 + E-051 | `phase-5/66-appshell-loop-progress-strip.md` | B-122 ✅ + E-051 ✅ (cascade) | `261dc66` | **Phase 5 spec #66 — live AppShell loop-progress strip for IP persona.** New `app/schemas/loop_progress.py` (LoopProgressResponse) + `app/services/loop_progress_service.py` (`get_loop_progress` per D-3 skill→category lookup) + `app/api/v1/routes/loop_progress.py` (`GET /api/v1/learn/loop-progress?tracker_id={id}` per D-13) + `main.py` router mount. New `src/components/layout/LoopProgressStrip.tsx` mounted as sibling below `<TopNav />` (D-8); render gate `persona === 'interview_prepper' && next_interview != null`. Hook composition: `useAuth` + `useHomeState` + `useScoreHistory(tracker_id)` + new `useLoopProgress(tracker_id)`. **LoopFrame extension** (§4.1 hybrid a+c): backward-compatible `stepStates?` + `onStepClick?` + `compact?` + `surface` widened `'results' \| 'appshell'`; Results.tsx call site byte-untouched. `loop_frame_rendered` suppressed when `surface === 'appshell'` per D-4. **4 new PostHog events** (`loop_strip_rendered/_step_clicked/_rescan_unlocked/_step_completed`). Hardcoded constants per D-5; existing `border-danger`/`text-danger` reused per D-6. Tests +10 BE / +22 FE. |
| B-123 | `phase-5/66-appshell-loop-progress-strip.md` | B-123 ✅ | `042f92c` | Spec #66 §12 amendment locking D-1..D-14. R14 exception (b). |
| B-120 + E-050 | `phase-5/65-home-status-hero.md` | B-120 ✅ + E-050 ✅ (cascade) | `58bb9a9` | **Phase 5 spec #65 — status-sentence hero on `/home` (combined Mode-2 spec+impl).** Authors spec #65 + ships impl same commit per single-slice precedent. New `<HomeStatusHero>` (one-line `<p>`, R12 token-only) mounted in `HomeDashboard.tsx` between greeting `<h1>` and `<StateAwareWidgets>` per D-1 — sibling of persona modes. IP/CC copy templates with graceful clause omission. team_lead returns null (D-8). New `home_status_hero_rendered` event. Tests +12 FE. |
| B-119 + E-049 | `phase-5/64-results-loop-frame.md` | B-119 ✅ + E-049 ✅ (cascade) | `b58a42d` | **Phase 5 spec #64 — static loop frame on Results.** New `<LoopFrame>` (4-step "Scanned/Studying/Re-scan/Interview" per §14 OQ-2; horizontal at md+, vertical stack <md). Mounted in `Results.tsx` ABOVE the grid container (sibling, NOT 12th grid child — JC #1 to avoid 11-row-shift cascade). `useHomeState` newly imported. New `loop_frame_rendered` event. Tests +10 FE. §12 amended same commit — D-1..D-14 from §14 OQs. |
| B-125 + B-126 + B-119 + B-120 + B-122 + B-123 (spec author) | (specs 64/65/66/67) | (cluster) | `8b70037` + `8dcdccd` + `d407e6e` | Spec-author slices for #64 + #66 + #67. Each forward-files an impl row that closes at the corresponding impl slice. R14 exception (b). |
| B-117 | (no spec — single-slice fix bundle) | B-117 ✅ | `2ae9a69` | Stripe cancel-pending UI bundle — Profile Reactivate CTA (cancel_at_period_end===true → portal); Pricing Pro tile swaps "Current Plan" → "Cancels {date}" + handleCta opens portal sidestepping B-113 `AlreadyProError`. New `subscription_portal_opened{source: 'pricing_reactivate'}`. Tests +5 FE. |
| B-118 | (no spec — single-slice fix) | B-118 ✅ | `ace4584` | AuthContext `refreshUser()` re-fetches `/auth/me` post-Stripe redirects (concurrent calls dedupe via `useRef<Promise>` inflight flag). Wired into `Pricing.tsx` (`?upgrade=success` post-checkout) + `Profile.tsx` mount (portal return_url). Tests +7 FE. |
| B-116 | (no spec — audit-2026-05 F-2/F-4 fix) | B-116 ✅ | `06ea5f6` | `customer.subscription.updated` webhook handler + alembic `c2ba25f1d9a7` adds `Subscription.cancel_at_period_end Boolean NOT NULL`. FE: `/auth/me` exposes new flag; `AuthUser` gains optional `subscription`; Profile renders "Cancels {date}". Tests +6 (BE +4 / FE +2). |
| B-115 | (no spec — P0 hotfix) | B-115 ✅ | `3fbc252` | LastScanWidget Rules-of-Hooks crash — `if (suppressed) return null` was BEFORE `useCallback`/`useEffect` causing hook-count mismatch + ErrorBoundary crash mid-mount. Fix: moved early return AFTER all hooks. Bundled `SentryFallback` dev-mode improvement (renders error message + stack inline). |
| B-114 + E-033 + E-039 | (no spec — P0 hotfix) | B-114 ✅ + E-033 ✅ + E-039 ✅ (cascade) | `7b09116` | **Stripe SDK v14+ hotfix.** Webhook 500'd with `AttributeError: get` because Stripe SDK v14+ stopped subclassing `dict` for `StripeObject`. Fix: `_field(obj, key, default)` helper unifies `dict.get` + `getattr` paths; `event["id"]` replaces `event.get("id", "")`; all 5 `.get()` callsites in `_handle_*` migrated. Test parity: 2 new regression tests use `stripe.Event.construct_from()` (catches next SDK rename). E-033 + E-039 cascade-close. |
| B-113 | (no spec — audit-2026-05 F-1/F-5 fix) | B-113 ✅ | `5ee327e` | F-1 P0 — `AlreadyProError` raised when `sub.plan=="pro" AND status=="active" AND stripe_subscription_id`; route maps to 409 "Already subscribed to Pro plan" (double-subscription guard on `/payments/checkout`). F-5 P1 — `.env.example` gains `STRIPE_PRO_PRICE_ID_INR` + `STRIPE_ENTERPRISE_PRICE_ID`. Tests +3 BE. Unblocks E-039. |
| B-112 + E-035 | (Mode-3 audit deliverable) | B-112 ✅ + E-035 ✅ (cascade) | `999acc2` | Stripe integration audit — `docs/audits/stripe-integration-audit-2026-05.md`. 11 findings — F-1 P0 (no Pro short-circuit on checkout — addressed by B-113), F-2/F-3/F-4 P1 (subscription.updated unhandled — addressed by B-116), F-5 P1 (env.example missing 2 STRIPE_* vars — addressed by B-113), F-6..F-11 P2/P3. |
| B-111 | (Mode-3 audit deliverable) | B-111 ✅ | `31b983e` | Phase 6 completion assessment — `docs/audits/phase-6-completion-assessment.md` verdict YES-WITH-CAVEATS. 16/16 Phase-6 specs (00..15) shipped; user-facing surface live. Slice 6.16 (cards-schema retirement umbrella) deferred — non-launch-blocking. |
| E-037 | (no spec — security hardening) | E-037 ✅ | `686a624` | Pro-tier auth + LLM rate limit hardening on `interview_prep` + Pro-tier Lens endpoints (rewrite, rewrite/section, cover_letter). |
| B-008 | `phase-5/12-navigation-restructure.md` §Analytics | B-008 ✅ | `49aee35` | `deprecated_route_hit{from_path, to_path}` telemetry wired in 10 `<Navigate>` redirect nodes via new `<DeprecatedRedirect>` wrapper component. Legacy `RedirectWithParam` helper deleted. Tests +6 FE. |
| B-006 + E-015 | (no spec — audit verdict) | B-006 ✅ + E-015 ✅ (cascade) | `c4132fb` | Settings persistence audit verdict — zero gaps. All 9 User columns + 4 per-user settings tables (EmailPreference / GamificationStats / Subscription / paywall_dismissals) verified to ship with `server_default` or signup-payload values; nullable columns have explicit None-handling. |
| B-009 + B-013 | (docs sync) | B-009 ✅ + B-013 ✅ | `0cb10ad` | AGENTS.md alignment — replaced AGENTS.md drifted "80%+ coverage target" line with pointer to CLAUDE.md R13; added "Repository layout" section clarifying git root vs working dir + cross-ref to CLAUDE.md C1 footgun. |
| B-011 + B-012 | (docs verdict) | B-011 ✅ + B-012 ✅ | `9db9b9f` | v2.1 historical-artifact verdict — periodic doc-audit pattern locked at spec #48; no v2.3 patch needed. |
| B-127 | (no spec — hygiene) | B-127 ✅ | `401b95d` | SS + BACKLOG light-hygiene compaction. RC archive cut (9 entries 4+ to §10), Drift archive cut (5 ✅ RESOLVED rows: D-016/D-019/D-020/D-022/D-029), BACKLOG closed-row archive cut (136 rows ≤2026-05-02), worst-RC trim (B-125a entry 298→245 words per R15(d) hard ceiling). Test Suite Status refreshed BE 823/64-fail / FE 543. |
| (rolled up) | (process slices) | B-119/B-120/B-121/B-122/B-123/B-124/B-125/B-126 | (per-row commits) | Spec-author + §12 amendment + hygiene clusters for the Phase 5 design-review batch. R14 exception (b). |


### Slice absorption log (carry-forward, prior regen at `ac0466c` — B-110 window)

| Slice | Spec | BACKLOG | Closing commit | Notes |
|---|---|---|---|---|
| B-098 | `phase-6/14-daily-digest-cron.md` | B-098 ✅ | `bcd89ce` | **Phase 6 slice 6.14 — daily Pro digest cron impl.** First scheduled job in codebase per LD G2. New `[[cron]]` in `railway.toml` + new CLI `app/scripts/send_pro_digest.py` + new orchestrator `app/services/pro_digest_service.py` + new schemas `app/schemas/pro_digest.py` + new email template `app/templates/pro_digest.html`. +4 PostHog events. **Zero new migrations** (consumes B-087's `email_log`). Tests BE 802 → 824. **B-078 cron architecture decision ✅ resolved at spec ship.** |
| B-102 | `phase-6/15-legacy-retirement-easy-wins.md` | B-102 ✅ | `e36902c` | **Phase 6 slice 6.15 — legacy retirement easy-wins refactor.** Pure refactor — zero new feature surface. New `app/schemas/daily_status.py` (`DailyStatus` lifted byte-identically per §12 D-1) + `schemas/study.py` back-compat re-export (until spec-16 cards-schema retirement) + 3 import-flip sites; new `app/utils/local_time.py` (`next_local_midnight` public per D-2 + D-3) + helper deletions in both services + 3 callsite renames + unused `time`/`timedelta` imports cleaned; `study_dashboard_viewed` analytics catalog row hard-deleted per D-5. Tests BE 842 → 849 (+7, in spec env). FE 466 unchanged. AC-1..AC-10 all green. Zero alembic. 1 info-only JC (spec said 4 callsites; disk had 3 — spec-author double-counted). |
| B-096 | (no spec — process slice) | B-096 ✅ | `d6fab75` | Prior CR targeted regen at HEAD `246b4ec` + RC compaction. §1 fully refreshed; §2 / §5 / §11 / §13 patched. Carry-forward anchor for this regen. |
| B-097 + B-099 | `phase-6/14-daily-digest-cron.md` | B-097 ✅ + B-099 ✅ + B-078 ✅ | `86bc442` + `b5bec37` | Slice 6.14 spec-author + §12 amendment locking D-1..D-14 from §14 OQ-A..OQ-N. Spec body 992 lines. R14 exception (b). |
| B-100 | (no spec — Mode 3 scout audit) | B-100 ✅ | `5291d9e` | Phase 6 cleanup triage producing per-item retire/migrate/defer verdicts. ~25 deferred-cleanup items across 8 themes. Bucket counts: 4 RETIRE-NOW + 18 RETIRE-WITH-MIGRATION + 9 DEFER + 1 DONE + 1 PROCESS. **>15 stop threshold tripped** — recommended scope = Option C: split into easy-wins spec (1 impl slice = slice 6.15) + cards-schema-retirement umbrella (4 cascading impl slices, gated on slice 6.16). Flagged B-010 stale (Navbar.tsx is live). |
| B-101 + B-103 | `phase-6/15-legacy-retirement-easy-wins.md` | B-101 ✅ + B-103 ✅ + B-104 🟦 | `b50a592` + `174e479` | Slice 6.15 spec-author + §12 amendment locking D-1..D-7 from §14 OQ-A..OQ-G. Scope = Option C from B-100 triage — 3 mechanical cleanups (T7.1 + T7.2 + T8.1). B-104 forward-filed at 🟦 per D-7 (B-010 follow-up — Navbar.tsx update-or-close decision). R14 exception (b). |
| B-105 | (no spec — single-slice tooling) | B-105 ✅ | `3cdc890` | `scripts/chat-sync-check.sh` — chat-Project sync sentinel. Reads stored short SHA from gitignored `.chat-sync-sha`, diffs against HEAD for 5 watched files (SESSION-STATE / CODE-REALITY / BACKLOG / CLAUDE / AGENTS), prints `⚠ <file> changed (<N> commits since sync)` per stale file. `--mark` stamps current SHA; `--quiet` suppresses ✅ line. R14 exception (b). |
| B-106 | (no spec — process amendment) | B-106 ✅ | `274ed44` | R14 spec-length governance amendment — appended *Spec length governance* paragraph: target ≤800 lines; specs over 1200 lines trigger a JC explaining why the feature can't split into sub-specs linked by a parent spec. Guideline not gate. R14 exception (b). |
| B-107 | (no spec — process amendment) | B-107 ✅ | `24c3122` | R16 scout-first amendment — replaced "regenerate CR before audit" closing paragraph with split: orientation queries → CR; precision queries (who calls X, consumers of type Y, does route Z exist) → live `rg`/`grep` at Step 0; CR regen still valuable before heavy multi-file slices. **This regen exercises the rule** — orientation-grade enumeration via filesystem; precision-grade fact-checking via `git log --name-status` + grep against on-disk schemas. R14 exception (b). |
| B-108 | (no spec — single-slice tooling) | B-108 ✅ | `6d39980` | `scripts/process-health-check.sh` 6th metric — process-tax ratio (warn >30% / fail >45%). Greps `\| ✅ \|` rows, takes `tail -15`, counts those matching `R14 exception\|(no spec\|tooling\|process`, prints `N/M (XX%)`. First-run output: 7/15 (46%) → ✗ FAIL. JC: active table not strictly chronological so `tail -15` is "recent-but-not-newest" sample window (documented inline). R14 exception (b). |
| B-109 | (no spec — doc compaction) | B-109 ✅ | `84f906b` | Doc compaction bundle. Task 1 no-op (all 7 CLAUDE.md revision entries within 30-day window). Task 2: cut RC entries 6-16 (11 entries B-093..B-103) to `docs/archive/session-state-history.md` §8; SESSION-STATE.md 605 → 472 lines (cleared 600 fail); archive 1489 → 1629. Footer note updated. R14 exception (b). |
| B-110 | (no spec — this regen) | B-110 ✅ | `3f05a80` | This CR full regen at HEAD `ac0466c`. All 13 sections re-anchored. R14 exception (a) — regenerated audit artifact, no test runs. Two-commit pattern (regen `3f05a80` + SHA backfill replacing `4655be9` placeholders in BACKLOG.md + SESSION-STATE.md + this row). |

### Slice absorption log (carry-forward, prior regen at `246b4ec` — B-096 window)

| Slice | Spec | BACKLOG | Closing commit | Notes |
|---|---|---|---|---|
| B-086a | `63-ats-rescan-loop.md` | B-086a ✅ | `210dcb2` | **Phase 5 E-043 foundation** — alembic migration `e043a1b2c3d4` (Q1 LOCK: `jd_text` + `jd_hash` on `tracker_applications_v2` + `ix_tracker_apps_jd_hash` — closes drift D-020; Q2 LOCK: `tracker_application_scores` table + 3 indexes); new model `app/models/tracker_application_score.py`; new service `app/services/analysis_service.py` extracting `score_resume_against_jd` per §6.1 G-6; new schema module `app/schemas/rescan.py` (5 schemas — scaffolds B-086b consumes); new ORM-getter `tracker_service_v2.get_application_model_by_id`; `tracker_service_v2.create_application` extended with optional `jd_text` + `jd_hash` kwargs (additive); `app/api/routes/analyze.py` reduced to parse → call helper → write tracker row with `jd_text` + `jd_hash` populated. Tests BE 692→700 (+8); +1 integration (alembic round-trip). FE 417 unchanged. AC-12 / AC-15 / AC-17 covered. JC #1 (BACKLOG ID — sub-ID convention preserved per slice-6.10 precedent), JC #2 (`scan_id` no FK — no `scans` table on disk), JC #3 (`parsed_resume` kwarg added to function signature for AC-17 byte-identity). |
| B-086b | `63-ats-rescan-loop.md` | B-086b ✅ + B-086 ✅ (cascade) + E-043 ✅ (cascade) | `4aab0bf` | **Phase 5 E-043 orchestrator + admin route + UI** — new service `app/services/tracker_application_score_service.py` (write_score_row / find_by_dedupe / get_score_history / compute_delta / to_history_entry / get_prior_overall_score / update_tracker_ats_score); new route `POST /api/v1/analyze/rescan` at `app/api/routes/analyze.py:188` (orchestrator: ownership read → 422 jd_text=NULL → D-2 dedupe short-circuit → G-7 counter → score → persist + ats_score flip → `rescan_completed` event); new route `GET /api/v1/tracker/{app_id}/scores` at `app/api/v1/routes/tracker.py:79`; new FE component `<ScoreDeltaWidget>` (tracker focused-row inline-expand, 3 render states); new FE component `<HomeScoreDeltaWidget>` (interview_prepper-only home variant below CountdownWidget, history.length≥2 render gate); new hook `useScoreHistory`; new api helpers `fetchScoreHistory` + `triggerRescan`; 3 new FE types in `src/types/index.ts:134-160` (ScoreHistoryEntry / ScoreDelta / ScoreHistoryResponse); 4 new PostHog events at `analytics.md:163-166`. Tests BE 700→713 (+13); FE 417→428 (+11). AC-1..AC-11, AC-13, AC-14, AC-16 covered (AC-12/AC-15/AC-17 covered by B-086a). JC #1 (`get_application_by_id` returns Pydantic — added sibling ORM-getter `get_application_model_by_id`). **Cascade-closes B-086 umbrella + E-043** per R15(c). |
| (process) | (none) | none | `1ca046f` | Prior CR full regen (B-085-equivalent absorption of B-086a + B-086b). Carry BE 713 / FE 428 forward verbatim from that anchor. |
| B-084 | `phase-6/11-content-quality-retention.md` | B-084 ✅ | `95104d2` | Phase 6 slice 6.11 — admin content-quality retention dashboard + first non-NULL `lessons.quality_score` writeback (Bayesian-smoothed pass_rate over `quiz_review_events`; idempotent IS DISTINCT FROM gate; MIN_REVIEW_THRESHOLD=10 per D-4). New v1 router `admin_content_quality.py` + service + 4 schemas + admin page + 3 components + hook + types + analytics catalog row + curriculum.md §7 layer-3 active. |
| B-088 + B-089 | `phase-5/63-ats-rescan-loop.md` §16 | B-088 ✅ + B-089 ✅ + D-029 ✅ | `2c92f11` + `2cf7c89` | E-043 §16 reconciliations (IFD-1 + IFD-4 + IFD-6 + R-5). `rescan_failed` event-fires on 402/422/404 + `rescan_completed` payload `jd_hash` → `jd_hash_prefix`; `/analyze` writes baseline `tracker_application_scores` row. D-029 cascade-closed at slice 2 ship. |
| B-090 | `process/01-light-mode-reporting.md` | B-090 ✅ | `e0e9b29` | LIGHT MODE reporting discipline applied to CLAUDE.md §340. NEW `docs/specs/process/` phase directory. R14 exception (b) — pure rule codification. |
| B-091 | (no spec — single-slice tooling) | B-091 ✅ | `c77861f` | `scripts/sha-backfill.sh` pilot (~72-line bash; `--dry-run`; idempotent re-run; macOS bash 3.2+ portable). Eat-own-dogfood validation at commit-2 SHA backfill. |
| B-092 | (no spec — single-slice tooling) | B-092 ✅ | `d5602c3` | Process compaction bundle: SS RC entries 5+ → `docs/archive/session-state-history.md` §6; BACKLOG closed-table pre-2026-04-29 → NEW `docs/archive/backlog-closed.md`; `scripts/process-health-check.sh` pilot (5 caps); R15(d) hard-ceiling 250 = health-check fail; LIGHT MODE §340 SOP-gate-narration rule. |
| B-087 | `phase-6/13-pro-digest-opt-out.md` | B-087 ✅ | `d020f4d` | Phase 6 slice 6.13 — Pro daily digest opt-out + `email_log` dedup table. Migration `f1a2b3c4d5e6` adds additive `email_preferences.daily_digest_opt_out` + new `email_log` (UUID PK + UNIQUE `(user_id, email_type, sent_date)` + composite index + CASCADE FK). Route Pro-tier guard returning 403 + admin bypass; FE `<EmailPreferences />` Pro-gated digest toggle. **Cascade-amplified D-028** (chain extension exposes alembic-roundtrip brittleness). Drift D-030 surfaced (spec `user.is_admin` shorthand). 16/16 ACs. |
| B-093 + B-095 | `phase-6/12-quality-signals.md` | B-093 ✅ + B-095 ✅ | `b93beb8` + `4bf5220` | Phase 6 slice 6.13.5 spec-author + §12 amendment locking D-1..D-14 from §14 OQ-A..OQ-N. R14 exception (b). |
| B-094a | `phase-6/12-quality-signals.md` (foundation half) | B-094a ✅ | `91be54f` | Phase 6 slice 6.13.5a — `card_quality_signals` foundation per LD J2. New ORM model + schemas + `card_quality_signal_service.upsert_signal` (read-after-write w/ `populate_existing=True`) + `critique_signal_consumer.persist_critique_signals` (write-time hook in `ingestion_worker` Stage 2.5 post-`_persist_drafts` per JC #1) + admin dashboard per-quiz_item user-aggregate writeback (IS DISTINCT FROM-gated) + critique read-side join. New BE event `lesson_critique_signal_persisted`. Drift D-032 surfaced (NULLS NOT DISTINCT raw-DDL). 12/20 ACs. |
| B-094b | `phase-6/12-quality-signals.md` (UI/route half) | B-094b ✅ | `85860d5` | Phase 6 slice 6.13.5b — user-thumbs route + `<ThumbsControl />` FE. New `thumbs_service.submit_thumbs` (re-uses slice 6.5 visibility filter) + `POST /api/v1/lessons/{id}/thumbs` + `LessonWithQuizzesResponse.viewer_thumbs` per §12 D-12 + admin thumbs columns populated + `WorstLessonsTable` Thumbs column. New FE event `lesson_thumbs_submitted` + custom-hook `useThumbs` (mirrors `useLesson` idiom). 8/20 ACs (closes 6.13.5 split at 20/20). |
| B-096 | (no spec — process slice) | B-096 ✅ | `d6fab75` (anchored at `246b4ec`) | Prior CR targeted regen at HEAD `246b4ec` + SS RC compaction. §1 fully refreshed; §2 / §5 / §11 / §13 patched for since-anchor delta. Two RC entries compacted: B-087 (518 → 199 words) + B-092 (285 → 145 words). R14 exception (b) — pure CR + SS doc, no test surface. Single-commit close pattern (no SHA backfill — internal cross-refs only). |
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
| 63-ats-rescan-loop.md | **Done — Shipped (spec + impl). Cascade-closes B-086 umbrella + E-043.** |
| 63-daily-review-preflight-gate.md | Draft *(impl `20562ea` closes B-059)* — **shares slot 63 with `63-ats-rescan-loop.md`; see numbering anomalies below.** |
| **64-results-loop-frame.md** | **NEW B-119 — Done — Shipped (spec + impl). Spec authored + §12 amended `8b70037`; impl `b58a42d`. Cascade-closes E-049 part (b).** |
| **65-home-status-hero.md** | **NEW B-120 — Done — Shipped (combined spec+impl) `58bb9a9`. Cascade-closes E-050.** |
| **66-appshell-loop-progress-strip.md** | **NEW B-122 — Done — Shipped (spec + impl). Spec authored `8dcdccd`; §12 amendment `042f92c`; impl `261dc66`. Cascade-closes E-051.** |
| **67-career-climber-role-intent.md** | **NEW B-125 — Done — Shipped (spec + impl). Spec authored `d407e6e`; §12 amendment `b2248d2`; BE half `9082a7b` (B-125a); FE half `e3fdf01`. Cascade-closes E-052.** |

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
| 11-content-quality-retention.md | Shipped (spec + impl) — closes B-084. Impl `95104d2`. |
| 12-quality-signals.md | Shipped (spec + impl) — closes B-093 + B-094a + B-094b + B-095. Foundation `91be54f` + UI `85860d5`. |
| 13-pro-digest-opt-out.md | Shipped (spec + impl) — closes B-087. Impl `d020f4d`. |
| 14-daily-digest-cron.md | Shipped (spec + impl) — closes B-097 + B-098 + B-099 + B-078. Impl `bcd89ce`. |
| 15-legacy-retirement-easy-wins.md | Shipped (spec + impl) — closes B-101 + B-102 + B-103. Impl `e36902c`. |

### Numbering anomalies / duplicates / gaps

- **phase-3 spec numbering:** `20-onboarding-polish.md`, `20b-design-system-themes.md`, `20c-resume-cover-letter-fix.md` share `20*` slot via letter suffixes. Convention consistent with phase-1 `11a/b/c/d`.
- **phase-4 numbering:** `22-error-monitoring.md` and `23-error-monitoring.md` — two specs with identical title at adjacent numbers; one Done, one Complete. Likely supersession.
- **phase-5 NEW slot 63 collision:** `63-ats-rescan-loop.md` (E-043, shipped this window) and pre-existing `63-daily-review-preflight-gate.md` (B-059, Draft / shipped per `20562ea`) both occupy slot 63. The two specs cover unrelated surfaces (re-scan loop vs daily-review preflight gate). Resolution candidates: (a) renumber `daily-review-preflight-gate.md` to a free slot (e.g., 64-), (b) add a letter suffix per phase-3 `20a/b/c` precedent (`63a-` / `63b-`), (c) accept the collision since both are post-author slug-distinct on disk. SOP-1 spec-author guard does not enforce phase-internal slot uniqueness; the convention is human-coordinated. Surface for chat-Claude calibration on next phase-5 spec-author slice.
- **phase-5 gaps:** `01`, `09–12`, `21–22`, `27`, `34–63` (gaps at 23–26, 28–33, 37, 39). Reserved-but-not-authored slots.
- **phase-5 number `1` reuse:** `01-admin-analytics-early-draft.md` superseded by `38-admin-analytics.md` per same OKR. Consider archiving or marking Superseded.
- **Total spec status hygiene gap:** 33 of 93 specs (35%) have no Status line. Concentration in phase-1 (7), phase-3 (3), phase-5 (22). Phase-6 sweep at `95bb3c5` flipped 6 phase-5 + 3 phase-6 specs to canonical post-ship form. Phase-5 specs #51, #52, #57 remain unflipped despite shipping per BACKLOG. Spec #04 (phase-6 admin-authoring) Status line stale (§11 #19).
- **Status format inconsistency:** `## Status:` (heading-2) vs `**Status:**` (bolded) appear interchangeably. Standardize on heading-2.

---

*End of snapshot. Generated 2026-05-04 at HEAD `192e97d` — **full regen** (closes B-128). All 13 sections re-anchored from on-disk filesystem enumeration. Lineage extends `ac0466c` → 57 raw commits (14 code-touching, 43 process/spec-author/SHA-backfill) → THIS commit. **Slice absorption (code-touching, 14):** Stripe-launch cluster (B-113 + B-114 + B-115 + B-116 + B-117 + B-118 + E-033 + E-039), security cluster (E-037), nav telemetry (B-008), Phase-5 design-review impl batch (B-119/E-049 LoopFrame, B-120/E-050 HomeStatusHero, B-122/E-051 LoopProgressStrip), Phase-5 career-climber capture (B-125a BE half + B-125/E-052 FE half). **Process absorption:** B-110 prior CR full regen (this regen's anchor) + B-111/B-112+E-035 audit deliverables + B-006+E-015/B-009+B-013/B-011+B-012 docs sweeps + spec-author/§12 amendment slices for #64/#65/#66/#67 (B-119/B-120/B-122/B-123/B-125/B-126) + B-121+B-127 hygiene compactions + B-124 date-bomb test fix. **New drift item:** D-033 (spec #67 §6.1 `quiz_review_events JOIN cards` vs disk `QuizReviewEvent`-on-`quiz_items`; runtime resolved at impl via `CardProgress × Category` join). **Drift archive cut by B-127 hygiene:** 5 ✅ RESOLVED rows (D-016, D-019, D-020, D-022, D-029) cut to `docs/archive/session-state-history.md` §10. **Milestones:** Phase 5 retention-loop infrastructure end-to-end (Results frame → Home status hero → AppShell live strip); Career-Climber capture surfaces + privacy-safe aggregate digest framing live; Stripe production-launch readiness cluster closed (F-1 + F-2 + F-4 + F-5 + SDK v14+ hotfix + cancel-pending UI + AuthContext staleness). E-052 cascade-closed at `e3fdf01`. Drift table active count 25 (post-cut); active+resolved 31. Next regen recommended once another ~10-commit code-touching delta accumulates (LD-1 sharpened threshold) or before any heavy multi-file slice (per R16 scout-first preference).*
