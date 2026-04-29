# CODE-REALITY — SkillForge / HirePort AI

> **Purpose:** frozen-in-time map of the codebase for off-disk advisors (chat-Claude) to draft accurate prompts. If the header sha below doesn't match `git rev-parse --short HEAD`, regenerate this file.
> **Read-only artifact.** Nothing here authorizes code changes.

---

## Section 1 — Repo metadata

| Field | Value |
|-------|-------|
| Commit sha (short) | `<this-slice>` (B-081 targeted regen — closes B-081). **Scope:** §1 / §3 / §4 / §6 / §7 / §8 / §13 regenerated; §2 / §5 / §9 / §10 / §11 / §12 carried forward verbatim. **Prior anchor:** `4c4d88f` (B-079 full regen, 2026-04-28). **Raw gap:** 8 commits. **Code-touching commits in window (under sharpened LD-1):** 1 — `0968a13` slice 6.8 impl (FSRS dashboard: `dashboard_service.py` aggregator + `dashboard.py` schemas/route + `Dashboard.tsx` page + 5 components under `components/dashboard/` + `useFsrsDashboard` hook + 10 FE types + `App.tsx` route mount). The other 7 = `6ff39b7` slice 6.8 spec-author + `ab07168` slice 6.8 §12 amendment + 3 SHA backfills + `7036968` scout-audit slice 6.8/6.14 numbering annotation (process slice annotating `docs/audits/phase-6-scout.md` snapshot) + 1 SHA backfill. Targeted scope justified: single-feature blast radius, well-bounded under LD-1. **Lineage from `4c4d88f`:** `4c4d88f` → `bb3997b` SHA backfill → `6ff39b7` slice 6.8 spec-author → `24db82d` SHA backfill → `ab07168` slice 6.8 §12 amendment → `1e70b99` SHA backfill → `0968a13` slice 6.8 impl → `e3ede6d` SHA backfill → `7036968` scout-annotation → `989b909` SHA backfill → THIS commit (targeted regen, B-081). |
| Branch | `main` (still ahead of `origin/main`; this slice's two commits queued in same un-pushed batch) |
| Generated | 2026-04-29 (targeted regen at HEAD `989b909`). Gap 8 commits with single code-touching delta — well-bounded under LD-1 ~10-commit targeted threshold, so only affected sections rebuilt. LD-2: counts via `find` / `wc` enumeration, not estimation. LD-3: ambiguous fields flagged. |
| Backend model files | 24 (`app/models/*.py`, excl. `__init__`, `request_models`, `response_models`). 27 ORM model classes (some files declare 2: `analytics_event.py` → `QuizReviewEvent` + `LessonViewEvent`; `gamification.py` → `GamificationStats` + `Badge` + `UserBadge`; `mission.py` → `Mission` + `MissionDay`). |
| Backend service files | 42 functional top-level (in `app/services/`, excl. `__init__.py`) + 3 under `services/llm/` = 45. **+1 since `4c4d88f`**: `dashboard_service.py` (slice 6.8, `0968a13`) — single aggregator `aggregate_user_dashboard()` composing 5 private section helpers (cards-due / retention curve / deck-mastery / streak / review-history). Reuses `curriculum_visibility` (D-10) + `gamification_service.get_stats` (D-006). |
| Backend schema files | 17 (`app/schemas/*.py`, excl. `__init__.py`). **+1 since `4c4d88f`**: `dashboard.py` (slice 6.8, `0968a13`) — 10 Pydantic v2 schemas (`CardsDueByState` / `CardsDueSection` / `DailyRetentionPoint` / `RetentionSection` / `DeckMastery` / `DeckMasterySection` / `StreakSection` / `RecentReview` / `ReviewHistorySection` / `DashboardResponse`). |
| Backend router files | 27 v1 + 6 legacy = 33. **+1 since `4c4d88f`** (v1): `dashboard.py` (slice 6.8, `0968a13`; mounts `GET /learn/dashboard`). |
| Backend endpoints | 83 unique decorators across both folders + 6 re-export double-mounts (the v1 thin re-exports of `analyze` / `cover_letter` / `interview` / `rewrite`) = **89 mount-point appearances** in §3 flat table. **+1 since `4c4d88f`** (slice 6.8: `GET /api/v1/learn/dashboard?retention_window_days=N`). |
| Alembic revisions | 27 (Head = `b8a9d4f3e2c1`). Unchanged since `4c4d88f` — slice 6.8 ships zero migrations. |
| Frontend pages | 27 — **+1 since `4c4d88f`**: `pages/Dashboard.tsx` (slice 6.8, `0968a13`). 21 top-level + 6 under `pages/admin/`. |
| Frontend components | **79** (excl. `__tests__/*`). **+5 since `4c4d88f`** (all under `components/dashboard/` slice 6.8 `0968a13`): `DueToday.tsx` / `Streak.tsx` / `RetentionCurve.tsx` / `DeckMastery.tsx` / `ReviewHistory.tsx`. NB: `components/dashboard/` directory now hosts both the prior 10 ATS-analysis panels (Phase 1) AND these 5 FSRS-dashboard sections (Phase 6) — see §6 component graph. |
| Frontend utils | 7 utility .ts files in `src/utils/`. `services/api.ts` (separate module) gained `fetchFsrsDashboard(opts)` exported helper this regen window (slice 6.8, `0968a13`); `fetchRankedDecks(opts)` from prior window unchanged. |
| Shared TS types | `src/types/index.ts` (**702 lines**, +83 since `4c4d88f`) + `src/types/homeState.ts` (28 lines, unchanged). **+10 interfaces in `index.ts:624-702` since `4c4d88f`** (slice 6.8, `0968a13`): `CardsDueByState` / `CardsDueSection` / `DailyRetentionPoint` / `RetentionSection` / `DeckMastery` / `DeckMasterySection` / `StreakSection` / `RecentReview` / `ReviewHistorySection` / `DashboardResponse` (field-for-field mirrors of `app/schemas/dashboard.py`). |
| Frontend hooks | **18** (`src/hooks/*.ts`, excl. `__tests__`). **+1 since `4c4d88f`**: `useFsrsDashboard.ts` (slice 6.8, `0968a13`). |
| Frontend context providers | 5 (`AnalysisContext`, `AuthContext`, `GamificationContext`, `ThemeContext`, `UsageContext`) — unchanged. |
| Skills (tracked) | **22** in `.agent/skills/*.md`. Unchanged since `4c4d88f` (no skill-author slices in this window). |
| Skills (untracked) | 3 directory-style under `.agent/skills/` — `stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/` (each contains `SKILL.md` + optional `references/`); not in git, source unknown — see §10. |
| Specs | **90 across 7 phases** (phase-0=6, phase-1=13, phase-2=8, phase-3=11, phase-4=6, phase-5=36, phase-6=10). **+1 since `4c4d88f`**: phase-6 +1 (`09-fsrs-dashboard.md` slice 6.8). |
| Tests | **BE 651** / **FE 414** carried forward from slice 6.8 implementation final report (`0968a13`: BE 636→651 +15, FE 395→414 +19). R14 exception (b) — process slice, no test runs this regen. BE counts under `FREE_DAILY_REVIEW_LIMIT=10 FREE_LIFETIME_SCAN_LIMIT=1 FREE_MONTHLY_INTERVIEW_LIMIT=3 python -m pytest tests/ -m "not integration"` (canonical CI invocation per `backend.md`). |

**Slice absorption (this regen):** 6.8 (user-self FSRS dashboard, closes B-080). Plus context: scout-audit slice 6.8/6.14 numbering annotation slice (`7036968`, closes JC #1 from slice 6.8 spec-author — annotates `docs/audits/phase-6-scout.md` snapshot at `5b0aa23` with top-of-section drift notice + 2 inline pointer notes; not in CR scope, audit doc is a process artifact). This regen self-closes B-081. **Background work:** still none in repo (FastAPI synchronous request lifecycle only) — slice 6.14 cron architecture decision pending at B-078 🟦 (Phase 6 LD G2 leans Railway cron but row exists for re-evaluation when 6.13.5 closes).

---

## Section 2 — Backend models

All 24 model files under `app/models/`. 27 ORM model classes total (some files declare multiple). Mixins-only file `base.py` excluded from class count.

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

### `tracker.py`
**Class:** `TrackerApplicationModel` (`app/models/tracker.py:12`)  **Table:** `tracker_applications_v2`. Per-application job-tracker rows. Notable cols: `user_id` nullable, `company`, `role`, `date_applied`, `ats_score`, `status`, `scan_id`, `skills_matched` / `skills_missing`, `analysis_payload` JSONB (slice 6.6 ranker reads `recent_skill_gaps` from this), `interview_date` nullable (added by `9543aa466524`/backfilled by `eb59d4fc1f7e` for E-042 BE half).

### `usage_log.py`
**Class:** `UsageLog` (`app/models/usage_log.py:10`)  **Table:** `usage_logs`. Per-user tokenized feature-use ledger; powers admin analytics. Note: `check_and_increment` short-circuits on `max_uses == -1` (Pro/admin) BEFORE reaching `log_usage` — Pro spend invisible to admin dashboard (D-021c open drift).

### `user.py`
**Class:** `User` (`app/models/user.py:10`)  **Table:** `users`. Cols: `id`, `google_id` unique, `email` unique, `name`, `role` (`user`/`admin`), `persona` (`career_climber`/`interview_prepper`/null), `onboarding_completed`, `interview_target_company`, `interview_target_date` (both deprecated by E-042; FE consumers still read), `home_first_visit_seen_at` (B-016), timestamps.

---

## Section 3 — Backend routes

### Router-file summary

| File | Mounts | Endpoints | Notes |
|------|--------|-----------|-------|
| `app/api/routes/analyze.py` | `/api` (line 129 `main.py`) + `/api/v1` re-export | 2 (POST `/analyze`, GET `/analyze/{scan_id}`) | Legacy ATS scan + auto-tracker on success. |
| `app/api/routes/cover_letter.py` | `/api` + `/api/v1` re-export | 1 (POST `/cover-letter`) | Underscore→hyphen drift in AGENTS.md (§11 #1). |
| `app/api/routes/interview.py` | `/api` + `/api/v1` re-export | 1 (POST `/interview-prep`) | Decorator path `/interview-prep` not `/interview` (§11 #1). |
| `app/api/routes/onboarding.py` | `/api/v1` only | 2 (GET, GET) | Persona + recommendations. Mounted from legacy folder (§11 #2). |
| `app/api/routes/payments.py` | `/api/v1` only | 8 | Pricing, checkout, portal, paywall-dismiss, webhook, usage. Mounted from legacy folder (§11 #2). |
| `app/api/routes/rewrite.py` | `/api` + `/api/v1` re-export | 2 (POST `/rewrite`, POST `/rewrite/section`) | Resume rewrite + bullet rewrite. |
| `app/api/v1/routes/admin.py` | `/api/v1` | 8 | Card CRUD + import + AI generate + registration logs + audit. Router-level `audit_admin_request` dep. |
| `app/api/v1/routes/admin_analytics.py` | `/api/v1` | 2 (metrics, performance) | Spec #38 / E-018b. Router-level audit dep. |
| `app/api/v1/routes/admin_decks.py` | `/api/v1` | 4 (POST/PATCH/POST archive/GET list) | Phase 6 slice 6.4b. Router-level audit dep. |
| `app/api/v1/routes/admin_lessons.py` | `/api/v1` | 5 (POST/GET/PATCH/POST publish/POST archive) | Slice 6.4b. Audit dep. |
| `app/api/v1/routes/admin_quiz_items.py` | `/api/v1` | 4 | Slice 6.4b. Audit dep. |
| `app/api/v1/routes/analyze.py` | `/api/v1` | (re-export) | Thin re-export of `app/api/routes/analyze.py`. |
| `app/api/v1/routes/auth.py` | `/api/v1` | 4 (Google login, refresh, logout, me) | Auth router; ungated. |
| `app/api/v1/routes/cards.py` | `/api/v1` | 4 (list, search, by-category, by-id) | User-facing card reads. |
| `app/api/v1/routes/cover_letter.py` | `/api/v1` | (re-export) | Re-export of legacy. |
| `app/api/v1/routes/dashboard.py` | `/api/v1` | 1 (GET `/learn/dashboard`) | **NEW slice 6.8** (`0968a13`). User-self FSRS dashboard. Query param `?retention_window_days=N` range [1, 365], default 30. |
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
| `app/api/v1/routes/ranker.py` | `/api/v1` | 1 (GET `/learn/ranked-decks`) | **NEW slice 6.6** (`5011518`). Lens-ranked deck ordering. |
| `app/api/v1/routes/resume.py` | `/api/v1` | 4 (upload, optimize, get, diff) | Resume storage + AI optimize. |
| `app/api/v1/routes/rewrite.py` | `/api/v1` | (re-export) | Re-export. |
| `app/api/v1/routes/study.py` | `/api/v1` | 4 (daily queue, review, status, dismiss) | FSRS daily card study. |
| `app/api/v1/routes/tracker.py` | `/api/v1` | 4 (list, create, patch, delete) | Application tracker CRUD. |
| `app/api/v1/routes/users.py` | `/api/v1` | 2 (PATCH persona, POST home-first-visit) | User profile mutations. |

### Flat endpoint table (mount-point convention; 89 appearances)

Listed in router-file order. Re-export double-mounts marked with `[2x]`. Files with explicit decorators in `app/api/routes/` are listed once at `/api/...` and once at `/api/v1/...` per `main.py:135-170` mount.

Legacy `/api/*` (4 files double-mounted at `/api/v1/*` via re-export, +`onboarding`/`payments` mounted only at `/api/v1`):

| Method + Path | File:Line |
|---|---|
| POST `/api/analyze` `[2x]` | `app/api/routes/analyze.py:51` |
| GET `/api/analyze/{scan_id}` `[2x]` | `app/api/routes/analyze.py:289` |
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
| GET `/api/v1/learn/dashboard` **NEW slice 6.8** | `dashboard.py:28` |
| GET `/api/v1/learn/ranked-decks` (slice 6.6) | `ranker.py:27` |
| POST `/api/v1/resume/upload` | `resume.py:21` |
| POST `/api/v1/resume/{resume_id}/optimize` | `resume.py:66` |
| GET `/api/v1/resume/{resume_id}` | `resume.py:119` |
| GET `/api/v1/resume/{resume_id}/diff` | `resume.py:143` |
| GET `/api/v1/study/...` (×2) | `study.py:51`, `:128` |
| POST `/api/v1/study/...` (×2) | `study.py:77`, `:159` |
| GET `/api/v1/tracker` | `tracker.py:23` |
| POST `/api/v1/tracker` | `tracker.py:32` |
| PATCH `/api/v1/tracker/{app_id}` | `tracker.py:46` |
| DELETE `/api/v1/tracker/{app_id}` | `tracker.py:61` |
| PATCH `/api/v1/users/me/persona` | `users.py:74` |
| POST `/api/v1/users/me/home-first-visit` | `users.py:108` |

App factory at `app/main.py:62` — middleware stack: Sentry init (line 66), CORS (line 87), request-size limit (line 95), slowapi rate limit (line 82). Health check at `/health` (line 123).

---

## Section 4 — Backend services

### Top-level `app/services/` (42 files)

| File | Public surface | Notes |
|------|----------------|-------|
| `admin_analytics_service.py` | `compute_metrics`, `compute_performance` | Spec #38 admin dashboard. Maps `usage_logs` → token spend × `TIER_PRICE_USD_PER_1M_TOKENS` (in `llm_router.py`). Read-only. |
| `admin_errors.py` | `AdminWriteError`, `EditClassificationError` | Phase 6 slice 6.4b error envelopes. |
| `ai_card_service.py` | `generate_card_drafts` | AI-assisted admin card generation. Uses `generate_for_task(task="card_draft", ...)`. |
| `ai_service.py` | `generate_resume_optimization` | Enterprise-only path; **duplicates** `gpt_service.py` public API verbatim. `[S47-defer]`. |
| `analytics_event_service.py` | `write_quiz_review_event`, `write_lesson_view_event` | Slice 6.0 append-only writers (no UPDATE/DELETE per AC-10). Best-effort (try/except wraps caller). |
| `bullet_analyzer.py` | `analyze_bullets` | Per-bullet ATS analyzer. |
| `card_admin_service.py` | Card CRUD + import | Backed by `admin.py`. |
| `card_service.py` | Read-side card lookup, search, category bundles. |  |
| `curriculum_visibility.py` (slice 6.6) | `_persona_visible_to:30`, `_visible_persona_set:45`, `_resolve_plan:56`, `_allowed_tiers_for_user:77` | Extracted from `lesson_service` per slice 6.5 D-5 escape hatch (rule-of-three, slice 6.6 D-6). Pure helpers: persona/tier visibility resolution. Re-used by slice 6.8 `dashboard_service` for D-10 free-vs-premium deck filtering. |
| `dashboard_service.py` **NEW slice 6.8** | `aggregate_user_dashboard:77` (public) + `_get_user_timezone:133`, `_aggregate_cards_due:163`, `_aggregate_retention_curve:264`, `_aggregate_deck_mastery:340`, `_aggregate_one_deck:392`, `_aggregate_streak:458`, `_aggregate_review_history:479` (private) | User-self FSRS dashboard aggregator. Single read-only entry point composing 5 section helpers (cards-due / retention curve / deck-mastery / streak / review-history) — D-3 single envelope. Reuses `curriculum_visibility` helpers (D-10 — free page + premium decks filtered for free), `gamification_service.get_stats` (no streak math re-derivation, §6.3), `email_preferences.timezone` for D-6 user-local date bucketing. Reads-only across `quiz_item_progress` + `quiz_review_events` + `lesson_view_events` + `decks` + `lessons` + `quiz_items` + `gamification_stats`. Cold-start safe via `is_cold_start` flag; per-section cold-start variants per D-13. Constants (top of file): `MAX_RECENT_REVIEWS = 20` (D-9), `MASTERY_REPS_THRESHOLD = 3` (D-8), `_RECALL_RATINGS = (3, 4)` Good+Easy (D-5), `DEFAULT_RETENTION_WINDOW_DAYS = 30` (D-7). |
| `deck_admin_service.py` | Deck CRUD | Slice 6.4b admin authoring. |
| `deck_ranker_service.py` **NEW slice 6.6** | `get_recent_skill_gaps:85`, `rank_decks_for_user:169`, helpers `_list_visible_decks:260`, `_gap_match_score:283`, `_fsrs_due_score:310`, `_avg_quality_score:346` | Lens-ranked deck ordering. Aggregates skill gaps from `tracker_applications_v2.analysis_payload` (D-14 defaults: 30 days / 5 scans). 4 signals at default weights 0.55/0.25/0.10/0.10 (§12 D-1). Cold-start safe (returns `display_order` ASC if no scans). |
| `email_service.py` | `send_email` (Resend wrapper) | Spec #15 daily reminders. |
| `experience_service.py` | `generate_experience_narrative` | Spec #22 "My Experience". |
| `formatter_check.py` | `find_formatting_issues` | ATS formatting linter. |
| `gamification_service.py` | Streak, XP, badge updates | Server-side FSRS-adjacent gamification. |
| `gap_detector.py` | `detect_skill_gaps` | Resume-vs-JD skill diff. |
| `gap_mapping_service.py` | Map ATS gaps → study cards | Spec ats-card-bridge. |
| `geo_pricing_service.py` | `get_pricing_for_ip` | IP→country→Stripe price ID. Redis cached. |
| `gpt_service.py` | `generate_resume_rewrite`, `generate_resume_rewrite_async`, `generate_cover_letter`, `generate_interview_questions` | Returns `Tuple[X, telemetry_str]` for rewrite calls (D-014 open). All LLM calls via `generate_for_task()`. |
| `home_state_service.py` | `compute_home_state` | Spec #40 priority slot evaluator. Redis cached with invalidation hooks. |
| `interview_storage_service.py` | Interview Q set persistence | Uses `text_hash.hash_jd` (only consumer). |
| `keywords.py` | TF-IDF / RAKE keyword extraction. |  |
| `lesson_admin_service.py` | Lesson CRUD + publish + archive | Slice 6.4b. |
| `lesson_service.py` | `get_lesson_with_quizzes`, `get_deck_with_meta`, `list_lessons_in_deck`, `get_deck_lessons_bundle` | Phase 6 lesson reads. Slice 6.4b swapped fixture loader → DB. Slice 6.5 (B-072) will add persona-narrowing filters per spec #06 §6.2 (pending). |
| `mission_service.py` | Mission CRUD + active + daily card pull. |  |
| `nlp.py` | spaCy wrapper utilities. |  |
| `onboarding_checklist_service.py` | First-action checklist computation. |  |
| `parser.py` | PDF/DOCX → text extraction. |  |
| `payment_service.py` | Stripe checkout/portal/webhook handling. |  |
| `paywall_service.py` | Paywall dismissal grace logic. Spec #42. |  |
| `progress_service.py` | Radar + heatmap aggregation. |  |
| `quiz_item_admin_service.py` | Quiz-item CRUD + retire | Slice 6.4b. |
| `quiz_item_study_service.py` | `get_daily_quiz_items`, `review_quiz_item`, `get_quiz_progress` | Slice 6.2 FSRS quiz-item study. Slice 6.0 added dual-write hook calling `analytics_event_service.write_quiz_review_event` post-flush per spec #00 §6.2. Slice 6.5 will add persona-narrowing per spec #06 §6.1 (pending). |
| `reminder_service.py` | Daily-reminder send-time computation. |  |
| `resume_templates.py` | Template metadata. |  |
| `scorer.py` | ATS scoring algorithms. |  |
| `seed_lessons_service.py` | `load_seed_corpus(db, *, dry_run=False, seed_root=None) → SeedLoadReport` | Slice 6.4.5. Idempotent UPSERT loader (savepoint-protected per D-10). |
| `study_service.py` | FSRS daily-card surface for `card_progress`. Pre-Phase-6 study path. |  |
| `tracker_service_v2.py` | Tracker CRUD; auto-tracker-on-scan-success hook. |  |
| `usage_service.py` | `check_and_increment`, `log_usage`, `PLAN_LIMITS` dict | Source of truth for free-tier caps (no `usage_limits` table — §11 #6). Short-circuit at `max_uses == -1` for Pro/admin (D-021c open). |
| `user_service.py` | `reconcile_admin_role` (E-040 spec #54), persona PATCH, etc. |  |

### `app/services/llm/` (legacy provider factory — do not extend)

| File | Notes |
|------|-------|
| `factory.py` | `get_llm_provider()` legacy abstraction; do NOT import from service code. Phase-6 consolidation pending. |
| `claude_provider.py`, `gemini_provider.py` | Legacy provider wrappers. |

LLM router lives at `app/core/llm_router.py:1`. `generate_for_task(task, prompt, ...)` dispatches on `FAST_TASKS` / `REASONING_TASKS` frozensets (lines 23-39). Provider chosen from `LLM_FAST_PROVIDER` / `LLM_REASONING_PROVIDER` env. `TIER_PRICE_USD_PER_1M_TOKENS` constant (line 47+) feeds admin spend.

### CLI / scripts

- `app/scripts/seed_phase6.py` — `python -m app.scripts.seed_phase6 [--dry-run] [--seed-root PATH]`. Loads `app/data/decks/seed_lessons/<slug>/{_meta.md, *.md}` corpus via `seed_lessons_service.load_seed_corpus`. Slice 6.4.5.

---

## Section 5 — Alembic revisions

27 revisions in `hirelens-backend/alembic/versions/`. Linear chain. Head: `b8a9d4f3e2c1`.

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
| `b8a9d4f3e2c1` | Phase 6 slice 6.0 — `quiz_review_events` + `lesson_view_events` (HEAD) | `57951e9f4cdc` |

(Other 14 revisions are middle-of-chain Phase 1–5 migrations. Full enumeration via `ls hirelens-backend/alembic/versions/*.py`.)

CI migration-rollback job at `.github/workflows/ci.yml:101-149` runs `alembic upgrade head` → `downgrade -1` → `upgrade head` to verify reversibility on every push.

---

## Section 6 — Frontend routes (live component graph)

Routes declared in `src/App.tsx:78-137`. Public + protected, with namespace migration (`/learn/*` study + `/prep/*` interview prep) and transitional `<Navigate replace>` shims.

| Path | Element | File:Line | Access |
|---|---|---|---|
| `/` | `<HomeRoute>` (LandingPage for guests, redirect `/home` for auth) | `App.tsx:81` | Public |
| `/login` | `LoginPage` | `App.tsx:82` | Public |
| `/pricing` | `Pricing` | `App.tsx:83` | Public (chrome only for guests) |
| `/home` | `HomeDashboard` (persona-aware, 3 modes per spec #34) | `App.tsx:86` | Protected |
| `/onboarding` | `Onboarding` | `App.tsx:89` | Protected |
| `/onboarding/persona` | `PersonaPicker` (full-page) | `App.tsx:90` | Protected |
| `/first-action` | `FirstAction` (full-page interstitial spec #46) | `App.tsx:91` | Protected |
| `/learn` | `Learn` (slice 6.7 — replaces `StudyDashboard`) | `App.tsx:94` | Protected |
| `/learn/dashboard` | **`Dashboard`** *(NEW slice 6.8)* | `App.tsx:95` | Protected |
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
| `/prep/tracker` | `Tracker` | `App.tsx:108` | Protected |
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

### Component graph (79 components, organized by directory)

| Directory | Files | Notes |
|---|---|---|
| `components/admin/` | `AdminLayout.tsx`, `ConfirmCascadeModal.tsx`, `ConfirmPersonaNarrowingModal.tsx`, `MarkdownEditor.tsx` | Slice 6.4a (AdminLayout) + 6.4b (modals + editor). |
| `components/auth/` | `AdminGate.tsx` | E-040 frontend admin guard. |
| `components/dashboard/` | 15 components — **prior 10 ATS-analysis panels:** `ATSScoreGauge`, `BulletAnalyzer`, `FormattingIssues`, `ImprovementSuggestions`, `JobFitExplanation`, `KeywordChart`, `MissingSkillsPanel`, `PanelSection`, `ScoreBreakdown`, `SkillOverlapChart` (consumed by `pages/Results.tsx`). **+5 NEW slice 6.8 (`0968a13`) FSRS-dashboard sections:** `DueToday.tsx`, `Streak.tsx`, `RetentionCurve.tsx` (hand-rolled SVG per D-4), `DeckMastery.tsx`, `ReviewHistory.tsx` (consumed by `pages/Dashboard.tsx`). Directory hosts both surfaces; consumers do not cross. |
| `components/home/` | `DashboardWidget`, `InterviewDateModal`, `StateAwareWidgets` + `widgets/` (14 widgets) | Spec #40 / #61 / #62 home composition. |
| `components/home/widgets/` | `CountdownWidget`, `FirstSessionDoneWidget`, `InactiveReturnerWidget`, `InterviewPrepperChecklist`, `InterviewTargetWidget`, `LastScanWidget`, `MissionActiveWidget`, `MissionOverdueWidget`, `ResumeStaleWidget`, `StreakAtRiskWidget`, `StreakWidget`, `StudyGapsPromptWidget`, `TeamComingSoonWidget`, `TodaysReviewWidget`, `WeeklyProgressWidget` | 15 files (note: `StateAwareWidgets.tsx` listed under `home/`). |
| `components/layout/` | `AppShell`, `MobileNav`, `Navbar` *(unused — §9)*, `PageWrapper`, `TopNav`, `UserMenu` | AppShell mounts TopNav (md:+) and MobileNav. |
| **`components/learn/`** | **`RankedDeckList.tsx`** | **NEW slice 6.7.** Consumes `RankedDecksResponse.decks`. Cold-start CTA + empty state + 2-col grid. |
| `components/lesson/` | `LessonRenderer`, `QuizItemPanel` | Slice 6.3. |
| `components/mission/` | `Countdown`, `DailyTarget`, `MissionDateGate`, `MissionSetup` | Mission-mode chrome. |
| `components/onboarding/` | `GuidedTour` *(unused — §9)* | — |
| `components/profile/` | `StreakBadge`, `XPBar` | — |
| `components/progress/` | `ActivityHeatmap`, `SkillRadar` | Spec #13. |
| `components/rewrite/` | `CoverLetterViewer`, `ResumeEditor`, `ResumePDFTemplate` *(unused — §9)* | — |
| `components/settings/` | `EmailPreferences`, `ThemePicker` | — |
| `components/study/` | `CategoryCard`, `DailyReviewWalledView`, `FlipCard`, `QuizPanel`, `WallInlineNudge` | — |
| `components/tracker/` | `ApplicationCard`, `KanbanBoard` | — |
| `components/ui/` | `AnimatedCard`, `GlowButton`, `ProgressBar`, `ScoreBadge`, `SkeletonLoader`, `Tooltip`, `UpgradeModal` | App-root `<UpgradeModal>` mounted in `main.tsx:81`. |
| `components/upload/` | `JDInput`, `ResumeDropzone` | — |
| `components/PaywallModal.tsx` | (top-level, not in a subdir) | Modal triggered by paywall events. |
| `components/PersonaGate.tsx` | (top-level) | Persona-null routing guard. |

---

## Section 7 — Frontend pages

27 files (21 top-level in `src/pages/` + 6 under `pages/admin/`).

| File | Mounted at | Notes |
|------|-----------|-------|
| `pages/AdminAnalytics.tsx` | `/admin/analytics` (lazy) | Spec #38 / E-018b dashboard. |
| `pages/Analyze.tsx` | `/prep/analyze` | ATS scan upload. App-root `<UpgradeModal>` triggered via `setShowUpgradeModal(true)` (spec #60 LD-1). |
| `pages/CardViewer.tsx` | `/learn/card/:id` | Single-card flip view. |
| `pages/CategoryDetail.tsx` | `/learn/category/:id` | Category card list. Comment at line 13 references the deleted `StudyDashboard` (stale; harmless). |
| `pages/DailyReview.tsx` | `/learn/daily` | FSRS daily review flow. |
| **`pages/Dashboard.tsx`** | `/learn/dashboard` | **NEW slice 6.8** (`0968a13`). User-self FSRS dashboard. Universal D-2 composition (no persona modes); 5 sections in §8.1 order: cards-due → streak → retention curve (SVG) → deck-mastery → review-history. Reads via `useFsrsDashboard` hook hitting `GET /api/v1/learn/dashboard?retention_window_days=30`. Cold-start safe (`is_cold_start: true` flag + per-section variants). Fires `dashboard_viewed` PostHog event D-11 once-per-mount via `useRef` with `{persona, plan, is_cold_start, retention_window_days}` payload. Profile.tsx unchanged per D-12 coexistence. |
| `pages/FirstAction.tsx` | `/first-action` | Spec #46 one-CTA interstitial. |
| `pages/HomeDashboard.tsx` | `/home` | Spec #34/#40 persona-aware home. 3 inline render modes (career_climber / interview_prepper / team_lead). |
| `pages/Interview.tsx` | `/prep/interview` | Interview Q generator + persistence. |
| `pages/LandingPage.tsx` | `/` (guests) | Public marketing landing. |
| **`pages/Learn.tsx`** | `/learn` | **NEW slice 6.7** (`c6d9274`). Replaces deleted `StudyDashboard.tsx`. Three inline persona-mode functions per D-5: `LearnInterviewMode:45`, `LearnHabitMode:94`, `LearnTeamMode:214`, dispatched by `Learn:254`. Reuses spec #61 widgets verbatim from `components/home/widgets/`. Consumes `useRankedDecks` hook + `RankedDeckList` component. Cold-start CTA → `/prep/analyze`. Owns `?source=last_scan` (spec #62) + `?category` (spec #09) URL params per spec §7.2. |
| `pages/Lesson.tsx` | `/learn/lesson/:id` | Slice 6.3 lesson viewer. `useEffect` calls `recordLessonView(lessonId, body)` (slice 6.0 dual-write) alongside `capture('lesson_viewed', ...)`. |
| `pages/LoginPage.tsx` | `/login` | Google OAuth flow. |
| `pages/MissionMode.tsx` | `/learn/mission` (lazy) | Interview sprint mode. |
| `pages/Onboarding.tsx` | `/onboarding` | Welcome flow before persona. |
| `pages/PersonaPicker.tsx` | `/onboarding/persona` | Persona selection (spec #34). |
| `pages/Pricing.tsx` | `/pricing` | Stripe pricing card. Geo-routed via IP (Phase 3). |
| `pages/Profile.tsx` | `/profile` (lazy) | User settings. |
| `pages/Results.tsx` | `/prep/results` | ATS scan results detail. |
| `pages/Rewrite.tsx` | `/prep/rewrite` | Resume + cover-letter rewrite. PDF export inline via jsPDF (`ResumePDFTemplate.tsx` is unused, §9). |
| `pages/Tracker.tsx` | `/prep/tracker` | Application tracker (Kanban + list). |
| `pages/admin/AdminCards.tsx` | `/admin/cards` (nested, lazy) | Card CRUD UI. |
| `pages/admin/AdminDeckDetail.tsx` | `/admin/decks/:deckId` (lazy) | Deck editor. Slice 6.4b. |
| `pages/admin/AdminDecks.tsx` | `/admin/decks` (lazy) | Deck list. Slice 6.4a placeholder filled in 6.4b. |
| `pages/admin/AdminLessonEditor.tsx` | `/admin/lessons/:lessonId` (lazy) | Lesson editor with cascade-confirm. Slice 6.4b. |
| `pages/admin/AdminLessons.tsx` | `/admin/lessons` (lazy) | Lesson list. |
| `pages/admin/AdminQuizItems.tsx` | `/admin/lessons/:lessonId/quiz-items` (lazy) | Quiz-item editor. Slice 6.4b. |

**Deleted this regen window:** `pages/StudyDashboard.tsx` (slice 6.7, `c6d9274`, per spec #08 D-3 — `Learn.tsx` absorbed). Test file `tests/StudyDashboard.test.tsx` deleted in same commit. `tests/App.redirects.test.tsx:15,86` updated: stub `@/pages/Learn` (was `@/pages/StudyDashboard`); `/study` redirect testid `page-learn` (was `page-study-dashboard`).

---

## Section 8 — Frontend shared types

### `src/types/index.ts` (702 lines, 57 exports)

Top-of-file domain types: `ATSScoreBreakdown:3`, `SkillGap:10`, `BulletAnalysis:16`, `FormattingIssue:23`, `KeywordChartData:29`, `SkillOverlapData:36`, `AnalysisResponse:42`, `RewriteEntry:60`, `RewriteSection:69`, `RewriteHeader:75`, `RewriteResponse:80`, `CoverLetterRecipient:87`, `CoverLetterResponse:92`, `InterviewQuestion:103`, `InterviewPrepResponse:108`.

Application/tracker: `ApplicationStatus:115`, `TrackerApplication:117`. Cards/categories: `Category:132`, `CategoriesResponse:144`, `Card:148`, `FsrsRating:160`, `ReviewRequest:162`, `ReviewResponse:169`, `DailyCard:181`, `DailyStatus:206`, `DailyQueueResponse:213`. Mission: `MissionDayView:232`..`MissionCreateRequest:282`. Onboarding/gamification: `RecommendedCategory:290`, `GapMapping:299`, `OnboardingRecommendationsResponse:305`, `BadgeView:312`, `GamificationStats:318`. Email: `EmailPreference:330`, `EmailPreferenceUpdate:336`. Admin (cards): `AdminCard:343`..`CardImportResponse:387`. Analysis state machine: `AnalysisState:395`, `AnalysisAction:403`.

### Phase 6 Curriculum types (`index.ts:415-514`)

```ts
PersonaVisibility:415  // 'climber' | 'interview_prepper' | 'both'
DeckTier:416           // 'foundation' | 'premium'
LessonVersionType:417  // 'initial' | 'minor_edit' | 'substantive_edit'
QuestionType:418       // 'mcq' | 'free_text' | 'code_completion'
QuizDifficulty:419     // 'easy' | 'medium' | 'hard'
Deck:421
Lesson:435
QuizItem:455
LessonWithQuizzes:472
DeckWithLessons:480
ScoreBreakdown:490     // gap_match / fsrs_due / avg_quality / display_order_rank — slice 6.6
RankedDeck:497         // deck / score / rank / matched_gaps / score_breakdown — slice 6.6 / 6.7
RankedDecksResponse:505 // user_id / persona / cold_start / lookback_days / recent_gap_count / ranked_at / decks / lessons:null — slice 6.7 (mirrors app/schemas/ranker.py)
QuizReviewRequest:519
QuizReviewResponse:527
```

### Admin write-shape interfaces (`index.ts:542-618`, slice 6.4b-2)

| Type | Lines | Purpose |
|------|-------|---------|
| `EditClassification` | 542 | `'minor' | 'substantive'` literal — mirrors BE `_is_substantive_change` |
| `AdminDeckStatusFilter` | 544 | `'active' | 'archived' | 'all'` |
| `AdminLessonStatusFilter` | 545-550 | `'active' | 'drafts' | 'published' | 'archived' | 'all'` |
| `AdminQuizItemStatusFilter` | 551 | `'active' | 'retired' | 'all'` |
| `DeckCreateRequest` | 553 | mirror `app/schemas/deck.py::DeckCreateRequest:61` |
| `DeckUpdateRequest` | 563 | mirror `DeckUpdateRequest:73` |
| `LessonCreateRequest` | 573 | mirror `app/schemas/lesson.py::LessonCreateRequest:72` |
| `LessonUpdateRequest` | 582 | mirror `LessonUpdateRequest:88`; carries `edit_classification` |
| `LessonUpdateResponse` | 594 | extends `Lesson` with `version_type_applied` + retired-quiz-item summary |
| `QuizItemCreateRequest` | 601 | mirror `app/schemas/quiz_item.py::QuizItemCreateRequest:117` |
| `QuizItemUpdateRequest` | 610 | mirror `QuizItemUpdateRequest:142`; carries `edit_classification` |

### Backend analytics-event schemas (slice 6.0)

`app/schemas/analytics_event.py:13-58` declares 3 Pydantic v2 schemas: `QuizReviewEventCreate:13`, `LessonViewEventCreate:33`, `LessonViewEventRequest:47`. **Not** mirrored to FE TS: the dual-write payload is FE-thin (`recordLessonView` accepts an inline `{deck_id: string; version: number; session_id?: string}` per slice 6.0 D-7).

### Phase 6 ranker schemas (slice 6.6)

`app/schemas/ranker.py:21-76` declares 4 schemas: `ScoreBreakdown:21`, `RankedDeck:34`, `RankedLesson:46` (forward-compat for hypothetical 6.6b — always None in v1 per D-5), `RankedDecksResponse:62`. FE mirror at `src/types/index.ts:490-514` (slice 6.7 — drops `RankedLesson` since FE doesn't render it).

### Phase 6 dashboard schemas (slice 6.8, `0968a13`)

`app/schemas/dashboard.py:19-160` declares 10 Pydantic v2 schemas:

```ts
CardsDueByState:19      // new / learning / review / relearning ints
CardsDueSection:28      // due_today / due_next_7_days / due_breakdown_by_state / total_quiz_items_in_progress
DailyRetentionPoint:45  // date (ISO YYYY-MM-DD, user-local D-6) / sample_size / recall_rate (null when sample==0)
RetentionSection:60     // sample_size / overall_recall_rate / overall_lapse_rate / daily_retention[]
DeckMastery:77          // deck_id / deck_slug / deck_title / total_quiz_items_visible / quiz_items_with_progress / quiz_items_mastered / mastery_pct
DeckMasterySection:95   // decks[]
StreakSection:104       // current_streak / longest_streak / last_active_date / freezes_available / total_xp
RecentReview:120        // quiz_item_id / lesson_id / lesson_title / deck_slug / rating / fsrs_state_after / reviewed_at
ReviewHistorySection:136// window_days / total_in_window / recent_reviews[]
DashboardResponse:147   // user_id / persona / plan / is_cold_start / retention_window_days / generated_at + 5 section payloads
```

FE mirror at `src/types/index.ts:624-702` — field-for-field per slice 6.8 D-3 single-envelope contract. Recall-rate semantics per D-5 (`rating IN (3,4)` Good+Easy); mastery threshold per D-8 (`state == 'review' AND reps >= 3`); cap per D-9 (`MAX_RECENT_REVIEWS = 20`).

### Persona / auth types (`src/context/AuthContext.tsx`)

`Persona = 'career_climber' | 'interview_prepper' | 'team_lead' | null`. Defined in AuthContext; consumed across pages + widgets.

### Home-state types (`src/types/homeState.ts`, 28 lines)

Spec #40 priority-slot types. Unchanged.

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

No components found behind `{false && …}` guards or dormant feature flags at HEAD `4c4d88f`. Background-job framework absent — cron architecture decision pending at B-078 🟦 (Phase 6 LD G2 leans Railway cron for slice 6.14 daily Pro digest).

---

## Section 10 — Skills inventory

### Tracked skills (`.agent/skills/*.md`, 22 files)

| File | Description |
|------|-------------|
| admin-panel.md | Card CRUD, bulk import, AI-assisted card generation (Phase 3) |
| analytics.md | PostHog event catalog (frontend + backend), funnels, conventions |
| ats-card-bridge.md | Maps ATS scan skill gaps to study cards |
| ats-scanner.md | ATS resume scanning, scoring, keyword extraction, bullet rewriting, auto-tracker |
| **backend.md** | **NEW (B-073 cohort item 1, `84060b3`).** Service-layer conventions, route mounting, audit dependency chains, dual-write best-effort wrapper, CI invocation pattern. |
| card-extraction.md | JSX → PostgreSQL card extraction pipeline |
| content-pipeline.md | End-to-end content pipeline — extraction, AI generation, admin CRUD, bulk import |
| **curriculum.md** | **NEW (B-075, `49fc7e7`; closes E-028).** Phase 6 domain skill — deck/lesson/quiz_item conventions, persona/tier visibility, FSRS quiz-item progress, ranker pipeline, seed-corpus loader, dual-write hooks. |
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

**Skill-inventory gap surfaced this regen:** none new. The two flagged in prior regens (`backend.md`, `curriculum.md`) are now both authored and tracked. SOP-4 close-loop (per CLAUDE.md amendment in `b468025`): no auto-file fires this slice.

---

## Section 11 — Drift flags (AGENTS.md / master-doc vs code)

Re-verified at HEAD `4c4d88f`. Items 22 + 23 from prior regen reconciled below; new item 24 added.

1. **AGENTS.md legacy-routes paths use underscores; decorators use hyphens.** `app/api/routes/cover_letter.py:22` decorates `/cover-letter`; AGENTS.md row says `/api/cover_letter`. Same for `/api/interview` → `/api/interview-prep`. **Status: still drifted.**

2. **AGENTS.md Routes table lists `/api/v1/onboarding` and `/api/v1/payments` as v1 routers, but the files live in the legacy folder** (`app/api/routes/onboarding.py`, `app/api/routes/payments.py`). Mounted at `/api/v1` via `main.py:169-170`. **Status: still drifted.**

3. **AGENTS.md Models table User row still lists `target_company`, `target_date`** (line 270). Disk: `interview_target_company` (String(100)), `interview_target_date` (Date). Migration `02bf7265b387` did the rename. **Status: still drifted; bumped urgency by E-042 (interview_target_date deprecating in favor of `tracker_applications_v2.interview_date`).**

4. **AGENTS.md Routes table references `/api/v1/mission` (singular)** (line 213). Decorators are plural `/missions/create`, `/missions/active`, `/missions/daily`, `/missions/complete-day` (`mission.py:52,84,130,167`). `[S35-flag]`. **Status: still drifted.**

5. **AGENTS.md says `Category` has `source` column.** True, but it also has `tags` JSONB column (migration `d16ca29a5d08`). AGENTS.md doesn't mention it. **Status: still drifted.**

6. **AGENTS.md Models table references `UsageLimit`** (line 276). No `UsageLimit` model file or class on disk. Limits are enforced via `usage_service.py::PLAN_LIMITS` dict, not a DB table. **Status: still drifted (phantom).**

7. **Email-preferences route path mismatch.** `email_prefs.py:66,79` mounts `/email-preferences`; FE calls `/api/v1/email-preferences`. AGENTS.md table line 212 says `/api/v1/email-prefs`. **Status: still drifted.**

8. **`study-engine.md` skill file has no `description:` frontmatter.** Other 21 skill files have one. `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md` flags as critical. **Status: still drifted.**

9. **Tracker auto-save JD dedupe documented as locked but not implemented.** `tracker_applications_v2` has no `jd_hash` column (§2 verified); `tracker_service_v2.py` does not import `hash_jd`; only `interview_storage_service.py` consumes `text_hash.hash_jd`. `[5.17-follow]`. **Status: still drifted.** D-020 in SESSION-STATE tracks resolution shape (bundle into E-043 ATS re-scan loop).

10. **Four legacy `/api/*` routers still mounted alongside v1 counterparts.** `analyze` / `rewrite` / `cover_letter` / `interview` in `main.py:129-132`. v1 equivalents are *re-exports* of legacy router objects, so deprecating legacy mounts requires moving handlers first. **Status: still drifted.**

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

23. ~~**Slice 6.5 spec describes pending filter additions to `quiz_item_study_service` + `lesson_service` (B-072).**~~ ✅ RESOLVED 2026-04-28 by `930a6a2` (slice 6.5 implementation shipped — closes B-072). Spec #06 §6.1 + §6.2 read-time invariants are now on disk in `quiz_item_study_service.py` + `lesson_service.py`. **Status: resolved (next CR pass should verify on-disk filter shapes match spec text — deferred to next regen since B-072 is closed and code-side changes are in §4 service signatures).**

24. **NEW — Pro-path admin-analytics still invisible.** `usage_service.py::check_and_increment` short-circuits on `max_uses == -1` BEFORE reaching `log_usage` (line ~151-152); `admin_analytics_service.py:53-54` maps `rewrite` / `cover_letter` → reasoning tier but the input table stays empty for Pro/admin callers. Same shape as D-021c open drift. Spec #58 §12 errata recorded the overclaim; no fix has shipped. **Status: NEW — surfaced via cross-ref to D-021c. No BACKLOG row pre-allocated.** Close shape: either (i) docs slice amends spec #58 §12 to strike the "retroactively surfaces" claim, or (ii) impl slice moves `log_usage` to fire for every authed request (broad blast radius).

25. **NEW — CLAUDE.md uncommitted Q1-Q4 + "This file is working if" additions in working tree.** Pre-authored content from another slice (preserve-and-coexist per D-019). `git diff CLAUDE.md` shows +42 lines: Q1 Simplicity / Q2 Surgical / Q3 State assumptions / Q4 Verifiable goal Code Quality section + self-check block + revision-history entry. Not staged in this regen. **Status: NEW — info-only. JC #1 of this slice; resolution belongs to whoever owns the in-flight CLAUDE.md edits.**

---

## Section 12 — Open questions for Dhamo

1. `components/onboarding/GuidedTour.tsx` has zero imports. Is this (A) dead code safe to delete, or (B) a scaffold for a future onboarding tour spec? *(carried)*
2. `components/rewrite/ResumePDFTemplate.tsx` has zero imports and PDF generation is inline in `Rewrite.tsx`. Delete in next cleanup slice — yes/no? *(carried)*
3. Is `UsageLimit` supposed to exist as a DB-backed model, or is the AGENTS.md Models table row stale? *(carried)*
4. ~~`AdminPanel` (`/admin`) has no route-level admin guard~~ ✅ RESOLVED by E-040 (`1148354`, spec #54). `<AdminGate>` wraps `/admin` and `/admin/analytics`. *(resolved — drop next regen if no follow-up)*
5. `study-engine.md` skill file is missing `description:` frontmatter — backfill to match the other 21 skills? *(carried)*
6. `ai_service.py` duplicates `gpt_service.py` verbatim and is consumed only by an enterprise-tier endpoint. Safe to delete now, or wait per `[S47-defer]`? *(carried)*
7. Legacy mounts `/api/analyze`, `/api/rewrite`, `/api/cover-letter`, `/api/interview-prep` — known external caller, or purely FE-migration holdover? *(carried)*
8. Three untracked skill directories (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`). Source/intent unknown. (a) Commit, (b) `.gitignore`, (c) delete? `SKILL.md` (uppercase) doesn't match SkillForge convention. *(carried)*
9. E-042 deprecates `users.interview_target_company` and `users.interview_target_date` in favor of `tracker_applications_v2.interview_date` (BE shipped 2026-04-23 per `9543aa466524` / `eb59d4fc1f7e`). FE consumers (CountdownWidget, MissionDateGate) still read user-level fields. Phase-6 cleanup intent confirmed, or accelerate? *(carried)*

The four Phase 6 product decisions chat sometimes references (cron arch G2, file storage H1, events sink I1, `card_quality_signals` J2) live in **SESSION-STATE Phase 6 locked-decisions block**, not here. G2 cron decision is also tracked at B-078 🟦 awaiting re-evaluation when 6.13.5 closes.

---

## Section 13 — Specs inventory

Walked `docs/specs/**/*.md` — **90 spec files across 7 phases** (+1 since `4c4d88f`: phase-6 +1 — `09-fsrs-dashboard.md`).

### Per-phase counts
| Phase | Files | With explicit Status line | No status field |
|-------|-------|---------------------------|-----------------|
| phase-0 | 6 | 6 | 0 |
| phase-1 | 13 | 6 | 7 |
| phase-2 | 8 | 7 | 1 |
| phase-3 | 11 | 8 | 3 |
| phase-4 | 6 | 6 | 0 |
| phase-5 | 36 | 14 | 22 |
| phase-6 | 10 | 10 | 0 |
| **Total** | **90** | **57** | **33** |

### Status legend
`Done` · `Complete` · `Implemented — Spec Backfill Pending (P5-S###)` · `Draft` · `Drafted, not shipped` · `Shipped (spec + impl)` · `Done — Shipped in <sha>` · `Partially Done` · `Planned — Known-Broken` · `Deferred` · `Complete — Spec Backfill Pending`

### Slice absorption log (this regen)

| Slice | Spec | BACKLOG | Closing commit | Notes |
|---|---|---|---|---|
| 6.8 | `09-fsrs-dashboard.md` | B-080 ✅ | `0968a13` | **User-self FSRS dashboard** — `dashboard_service.py` aggregator + `dashboard.py` schemas (10 BE) + `dashboard.py` route (`GET /api/v1/learn/dashboard`) + `pages/Dashboard.tsx` (universal D-2 composition) + 5 components under `components/dashboard/` + `useFsrsDashboard` hook + 10 FE types + `App.tsx` route mount. Reuses `curriculum_visibility` (D-10) + `gamification_service.get_stats` + `email_preferences.timezone` (D-6). Zero migrations, zero new write paths, zero new PostHog payload changes (1 new event `dashboard_viewed` D-11). |
| (process) | (none) | B-081 | `<this-slice>` | This CR regen. Plus context: `7036968` scout-audit slice 6.8/6.14 numbering annotation (closes JC #1 from slice 6.8 spec-author — annotates `docs/audits/phase-6-scout.md` snapshot). |
| (carry) | (prior log) | B-061..B-079 | (see prior CR at `4c4d88f`) | Slices 6.0–6.7 + B-073/B-075/B-076/B-078/B-079 process work absorbed in B-079 full regen. Not re-listed here. |

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
| 57-tracker-level-interview-date.md | (no status field — E-042 BE shipped) |
| 58-legacy-rewrite-router-auth-quota.md | Shipped (spec + impl) — closes B-033 |
| 59-scan-persistence.md | Drafted, not shipped *(actually shipped per B-035 `0b35440`)* |
| 60-analyze-page-preflight-gate.md | (no status field — B-045 closed) |
| 61-home-dashboard-composition-rules.md | Drafted, not shipped *(impl `ecef895` closes B-051)* |
| 62-study-dashboard-source-hint.md | Drafted, not shipped *(impl `df035e1` closes B-052 + B-053)* |
| 63-daily-review-preflight-gate.md | Draft *(impl `20562ea` closes B-059)* |

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
| 07-deck-lesson-ranker.md | **Shipped (spec + impl) — closes B-074. Impl `5011518`.** *(NEW Phase 6 slice 6.6. Spec authored `a1b4bb5` 2026-04-28 + §12 amendment `fb92396` locking D-1..D-16 from §14 OQ-1..OQ-11. Impl ships `app/services/deck_ranker_service.py` + `app/services/curriculum_visibility.py` extraction + `app/api/v1/routes/ranker.py` + `app/schemas/ranker.py` (4 schemas). 4 signals (gap_match 0.55 / fsrs_due 0.25 / avg_quality 0.10 / display_order_rank 0.10 — D-1). Cold-start safe. Zero FE this slice; zero analytics events; zero migrations.)* |
| 08-persona-learn-page.md | **Shipped (spec + impl) — closes B-077. Impl `c6d9274`.** *(Phase 6 slice 6.7. Spec authored `c14b9ca` 2026-04-28 + §12 amendment `0c21223` locking D-1..D-8 from §14 OQ-1..OQ-8. Impl ships `pages/Learn.tsx` (replaces `StudyDashboard.tsx`) with three inline persona-mode functions per D-5 + `components/learn/RankedDeckList.tsx` + `hooks/useRankedDecks.ts` + ranker types `src/types/index.ts:490-514` + `services/api.ts::fetchRankedDecks` + App.tsx mount swap. 3 new analytics events (`learn_page_viewed` / `learn_deck_clicked` / `learn_mode_rendered`) all `useRef`-idempotent. Zero BE files touched.)* |
| 09-fsrs-dashboard.md | **Shipped (spec + impl) — closes B-080. Impl `0968a13`.** *(NEW Phase 6 slice 6.8. Spec authored `6ff39b7` 2026-04-28 + §12 amendment `ab07168` locking D-1..D-14 from §14 OQ-1..OQ-13 + sub-OQ-5b. Impl ships BE `app/services/dashboard_service.py` aggregator + `app/schemas/dashboard.py` (10 schemas) + `app/api/v1/routes/dashboard.py` route mounted at `GET /api/v1/learn/dashboard?retention_window_days=N`; FE `src/pages/Dashboard.tsx` (universal D-2 composition, 5 sections per §8.1 order) + 5 section components under `src/components/dashboard/` (DueToday / Streak / RetentionCurve hand-rolled SVG D-4 / DeckMastery / ReviewHistory) + `useFsrsDashboard` hook + `fetchFsrsDashboard` api helper + 10 dashboard types in `src/types/index.ts` + `/learn/dashboard` route in `App.tsx` + `dashboard_viewed` D-11 useRef once-per-mount event. Reuses `curriculum_visibility` (D-10), `gamification_service.get_stats` (§6.3), `email_preferences.timezone` for D-6 user-local bucketing. Zero migrations, zero new write paths. Tests BE 636 → 651 (+15); FE 395 → 414 (+19). All AC-1..AC-13 green. Profile.tsx unchanged per D-12 coexistence.)* |

### Numbering anomalies / duplicates / gaps

- **phase-3 spec numbering:** `20-onboarding-polish.md`, `20b-design-system-themes.md`, `20c-resume-cover-letter-fix.md` share `20*` slot via letter suffixes. Convention consistent with phase-1 `11a/b/c/d`.
- **phase-4 numbering:** `22-error-monitoring.md` and `23-error-monitoring.md` — two specs with identical title at adjacent numbers; one Done, one Complete. Likely supersession.
- **phase-5 gaps:** `01`, `09–12`, `21–22`, `27`, `34–63` (gaps at 23–26, 28–33, 37, 39). Reserved-but-not-authored slots.
- **phase-5 number `1` reuse:** `01-admin-analytics-early-draft.md` superseded by `38-admin-analytics.md` per same OKR. Consider archiving or marking Superseded.
- **Total spec status hygiene gap:** 33 of 89 specs (37%) have no Status line. Concentration in phase-1 (7), phase-3 (3), phase-5 (22). Phase-6 sweep at `95bb3c5` flipped 6 phase-5 + 3 phase-6 specs to canonical post-ship form. Phase-5 specs #51, #52, #57 remain unflipped despite shipping per BACKLOG. Spec #04 (phase-6 admin-authoring) Status line stale (§11 #19).
- **Status format inconsistency:** `## Status:` (heading-2) vs `**Status:**` (bolded) appear interchangeably. Standardize on heading-2.

---

*End of snapshot. Generated 2026-04-29 at HEAD `<this-slice>` — targeted regen (closes B-081). Sections regenerated: §1 / §3 / §4 / §6 / §7 / §8 / §13. Sections carried forward verbatim: §2 / §5 / §9 / §10 / §11 / §12. Slice absorption: 6.8 (FSRS dashboard, closes B-080) + scout-annotation slice context. Lineage extends `4c4d88f` → 8 commits (1 code-touching `0968a13`, 7 doc/process) → THIS commit. Next regen recommended once another ~10-commit code-touching delta accumulates (LD-1 sharpened threshold) — likely after the next Phase 6 implementation slice (6.9 or 6.10+ ingestion track).*
