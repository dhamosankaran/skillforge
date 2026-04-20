# CODE-REALITY — SkillForge / HirePort AI

> **Purpose:** frozen-in-time map of the codebase for off-disk advisors (chat-Claude) to draft accurate prompts. If the header sha below doesn't match `git rev-parse --short HEAD`, regenerate this file.
> **Read-only artifact.** Nothing here authorizes code changes.

---

## Section 1 — Repo metadata

| Field | Value |
|-------|-------|
| Commit sha (short) | `dda860a` |
| Branch | `main` (17 ahead of `origin/main`) |
| Generated | 2026-04-20 (pre-P5-S26b-impl-FE refresh: Sections 1-5 updated for the backend additions in `7cb2221` — `paywall_dismissal` model, `users.downgraded_at` column, two new `/payments/*` endpoints, `paywall_service.py`, migration `1176cc179bf0`. Sections 6-12 untouched since no frontend code has landed in this slice yet.) |
| Backend model files | 18 (`app/models/*.py`, excl. `__init__`, `request_models`, `response_models`) |
| Backend service files | 30 top-level + 3 under `services/llm/` = 33 |
| Backend router files | 17 v1 + 6 legacy = 23 |
| Backend endpoints (total) | 58 (54 unique decorators; `analyze` / `rewrite` / `cover_letter` / `interview` legacy routers are each mounted at both `/api/*` and `/api/v1/*`, so 4 paths appear twice) |
| Alembic revisions | 20 |
| Frontend pages | 19 |
| Frontend components (`.tsx` under `src/components/`, excl. `__tests__`) | 60 |
| Specs on disk (`docs/specs/**/*.md`) | 70 |
| Skill files (`.agent/skills/*.md`) | 20 |

---

## Section 2 — Backend models

### `base.py`
**Mixins only:** `TimestampMixin` (`created_at`, `updated_at` via `func.now()` + `onupdate`), `UUIDPrimaryKeyMixin` (`id` UUID default `uuid.uuid4()`). No models.

### `card.py`
**Class:** `Card`  **Table:** `cards`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| category_id | String (FK `categories.id`) | NOT NULL |
| question | Text | NOT NULL |
| answer | Text | NOT NULL |
| difficulty | String(10) | NOT NULL |
| tags | JSON | NOT NULL, default: `[]` |
| embedding | Vector(1536) | nullable |
| deleted_at | DateTime | nullable (soft-delete) |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `category → Category` (back_populates `cards`).

### `card_feedback.py`
**Class:** `CardFeedback`  **Table:** `card_feedback`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| card_id | String (FK `cards.id`) | NOT NULL |
| vote | String(4) | NOT NULL |
| comment | Text | nullable |
| created_at | DateTime | NOT NULL |

**Relationships:** `user → User`, `card → Card`.

### `card_progress.py`
**Class:** `CardProgress`  **Table:** `card_progress`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| card_id | String (FK `cards.id`) | NOT NULL |
| state | String(20) | NOT NULL, default: `"new"` |
| stability | Float | NOT NULL, default: `0.0` |
| difficulty_fsrs | Float | NOT NULL, default: `0.0` |
| elapsed_days | Float | NOT NULL, default: `0.0` |
| scheduled_days | Float | NOT NULL, default: `0.0` |
| reps | Integer | NOT NULL, default: `0` |
| lapses | Integer | NOT NULL, default: `0` |
| fsrs_step | Integer | nullable |
| last_reviewed | DateTime | nullable |
| due_date | DateTime | NOT NULL, default: `now()` |
| created_at / updated_at | DateTime | NOT NULL |

**Unique:** `(user_id, card_id)`. **Relationships:** `user → User`, `card → Card`.

### `category.py`
**Class:** `Category`  **Table:** `categories`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| name | String(100) unique | NOT NULL |
| icon | String(10) | NOT NULL |
| color | String(30) | NOT NULL |
| display_order | Integer | NOT NULL, default: `0` |
| source | String(50) | nullable (`foundation` / `premium`) |
| tags | JSONB | NOT NULL, default: `[]` |

**Relationships:** `cards → list[Card]` (back_populates `category`).

### `email_preference.py`
**Class:** `EmailPreference`  **Table:** `email_preferences`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| user_id | String (PK, FK `users.id`) | NOT NULL |
| daily_reminder | Boolean | NOT NULL, default: `True` |
| timezone | String(50) | NOT NULL, default: `"UTC"` |
| unsubscribe_token | String(64) unique | NOT NULL, default: `secrets.token_hex(32)` |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User`.

### `gamification.py`
Three models in one module.

**`GamificationStats`  Table:** `gamification_stats`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| user_id | String (PK, FK `users.id`) | NOT NULL |
| current_streak | Integer | NOT NULL, default: `0` |
| longest_streak | Integer | NOT NULL, default: `0` |
| total_xp | Integer | NOT NULL, default: `0` |
| last_active_date | Date | nullable |
| freezes_available | Integer | NOT NULL, default: `0` |
| freeze_week_start | Date | nullable |
| created_at / updated_at | DateTime | NOT NULL |

**`Badge`  Table:** `badges`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | String(64) (PK) | — |
| name | String(128) | NOT NULL |
| description | String(512) | NOT NULL |
| threshold_type | String(32) | NOT NULL |
| threshold_value | Integer | NOT NULL, default: `0` |
| created_at | DateTime | NOT NULL |

**`UserBadge`  Table:** `user_badges`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| badge_id | String (FK `badges.id`) | NOT NULL |
| earned_at | DateTime | NOT NULL, default: `now()` |

**Unique:** `(user_id, badge_id)`. **Relationships:** `UserBadge.badge → Badge`.

### `interview_question_set.py`
**Class:** `InterviewQuestionSet`  **Table:** `interview_question_sets`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| jd_hash | String(64) | NOT NULL |
| jd_text | Text | NOT NULL |
| questions | JSONB | NOT NULL |
| generated_at | DateTime | NOT NULL, default: `now()` |
| model_used | String(50) | nullable |

**Unique:** `(user_id, jd_hash)`.

### `mission.py`
Two models + one secondary table (`mission_categories`).

**`Mission`  Table:** `missions`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| title | String(200) | NOT NULL |
| target_date | Date | NOT NULL |
| daily_target | Integer | NOT NULL |
| status | String(20) | NOT NULL, default: `"active"` |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User`, `categories → list[Category]` (secondary `mission_categories`), `days → list[MissionDay]` (back_populates `mission`).

**`MissionDay`  Table:** `mission_days`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| mission_id | String (FK `missions.id`) | NOT NULL |
| day_number | Integer | NOT NULL |
| date | Date | NOT NULL |
| cards_target | Integer | NOT NULL |
| cards_completed | Integer | NOT NULL, default: `0` |

**Unique:** `(mission_id, day_number)`, `(mission_id, date)`.

### `payment.py`
**Class:** `Payment`  **Table:** `payments`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| stripe_payment_intent_id | String(255) unique | NOT NULL |
| amount | Integer | NOT NULL |
| currency | String(3) | NOT NULL, default: `"usd"` |
| status | String(30) | NOT NULL |
| created_at | DateTime | NOT NULL |

### `paywall_dismissal.py`
**Class:** `PaywallDismissal`  **Table:** `paywall_dismissals`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id` ON DELETE CASCADE) | NOT NULL |
| trigger | String(64) | NOT NULL |
| dismissed_at | DateTime(timezone=True) | NOT NULL, server default `now()` |
| action_count_at_dismissal | Integer | nullable (telemetry only) |

**Indexes:** `ix_paywall_dismissals_user_trigger_time` on `(user_id, trigger, dismissed_at)` — serves the 60s LD-8 dedup read and the "dismissal exists?" check inside `paywall_service.should_show_paywall`.

**Relationships:** none (no back_populates — `User` does not expose a `dismissals` collection; the table is read/written exclusively through `paywall_service`).

Purpose: append-only log of user paywall dismissals. Consumed by `paywall_service` (see Section 4) to drive the per-trigger 3-attempt grace window. Win-back consumption is deferred (BACKLOG E-031). Spec: `docs/specs/phase-5/42-paywall-dismissal.md`.

### `registration_log.py`
**Class:** `RegistrationLog`  **Table:** `registration_logs`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| ip_address | String(45) | NOT NULL (indexed) |
| google_email | String(320) | NOT NULL |
| created_at | DateTime | NOT NULL (indexed) |

### `resume_model.py`
**Class:** `Resume`  **Table:** `resumes`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| original_content | Text | NOT NULL |
| optimized_content | Text | nullable |
| template_type | String(50) | nullable |
| embedding | Vector(1536) | nullable |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User` (back_populates `resumes`).

### `stripe_event.py`
**Class:** `StripeEvent`  **Table:** `stripe_events`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | String(255) (PK — Stripe `evt_…` id) | — |
| event_type | String(100) | NOT NULL |
| processed_at | DateTime | NOT NULL |
| created_at | DateTime | NOT NULL |

### `subscription.py`
**Class:** `Subscription`  **Table:** `subscriptions`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) unique | NOT NULL |
| plan | String(20) | NOT NULL, default: `"free"` |
| status | String(20) | NOT NULL, default: `"active"` |
| stripe_customer_id | String(255) unique | nullable |
| stripe_subscription_id | String(255) unique | nullable |
| current_period_end | DateTime | nullable |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User` (uselist=False).

### `tracker.py`
**Class:** `TrackerApplicationModel`  **Table:** `tracker_applications_v2`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | nullable |
| company | String(200) | NOT NULL |
| role | String(200) | NOT NULL |
| date_applied | String(20) | NOT NULL |
| ats_score | Integer | NOT NULL, default: `0` |
| status | String(20) | NOT NULL, default: `"Applied"` |
| scan_id | String(36) | nullable |
| skills_matched | Text | nullable |
| skills_missing | Text | nullable |
| created_at | DateTime | NOT NULL |

**No `jd_hash` column** (see Drift flag below). **Relationships:** `user → User` (back_populates `tracker_applications`).

### `usage_log.py`
**Class:** `UsageLog`  **Table:** `usage_logs`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL (indexed) |
| feature_used | String(100) | NOT NULL |
| tokens_consumed | Integer | NOT NULL, default: `0` |
| created_at | DateTime | NOT NULL (indexed) |

**Relationships:** `user → User` (back_populates `usage_logs`).

### `user.py`
**Class:** `User`  **Table:** `users`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| google_id | String(255) unique | NOT NULL |
| email | String(320) unique | NOT NULL |
| name | String(255) | NOT NULL |
| avatar_url | String(2048) | nullable |
| role | String(20) | NOT NULL, default: `"user"` |
| persona | String(30) | nullable (3-value enum in code) |
| onboarding_completed | Boolean | NOT NULL, default: `False` |
| interview_target_company | String(100) | nullable |
| interview_target_date | Date | nullable |
| downgraded_at | DateTime(timezone=True) | nullable, default `None` (set by `customer.subscription.deleted` webhook per spec #42 LD-5; dormant until win-back slice E-031 activates) |
| created_at | DateTime | NOT NULL |

**Relationships:** `subscription → Subscription` (uselist=False), `resumes → list[Resume]`, `usage_logs → list[UsageLog]`, `tracker_applications → list[TrackerApplicationModel]`.

> `UsageLimit` (plan × feature cap) is referenced in AGENTS.md but **no model file exists** on disk; see Section 11.

---

## Section 3 — Backend routes

Both `/api/*` (legacy) and `/api/v1/*` (authoritative) are mounted in `app/main.py`. Router files define paths directly on decorators (no `APIRouter(prefix=...)`), so the full effective path is `prefix` + decorator path.

### Router-file summary

| Effective mount | File | Endpoints | Auth deps observed |
|-----------------|------|-----------|---------------------|
| `/api/analyze` | `app/api/routes/analyze.py` | 1 | `get_current_user_optional` |
| `/api/cover-letter` | `app/api/routes/cover_letter.py` | 1 | none |
| `/api/interview-prep` | `app/api/routes/interview.py` | 1 | `get_current_user_optional` |
| `/api/rewrite` | `app/api/routes/rewrite.py` | 1 | none |
| `/api/v1/onboarding` | `app/api/routes/onboarding.py` *(legacy folder, v1 mount)* | 2 | `get_current_user` |
| `/api/v1/payments` | `app/api/routes/payments.py` *(legacy folder, v1 mount)* | 6 | `get_current_user` (4), none (2) |
| `/api/v1/admin` | `app/api/v1/routes/admin.py` | 8 | `require_admin` (8) |
| `/api/v1/analyze` | `app/api/v1/routes/analyze.py` | 1 | `get_current_user_optional` |
| `/api/v1/auth` | `app/api/v1/routes/auth.py` | 4 | `get_current_user` (1), none (3) |
| `/api/v1/cards` | `app/api/v1/routes/cards.py` | 4 | `get_current_user` (4) |
| `/api/v1/cover-letter` | `app/api/v1/routes/cover_letter.py` | 1 *(re-exports legacy)* | none |
| `/api/v1/email-preferences` | `app/api/v1/routes/email_prefs.py` | 2 | `get_current_user` (2) |
| `/api/v1/feedback` + `/api/v1/admin/feedback` | `app/api/v1/routes/feedback.py` | 3 | `get_current_user` (1), `require_admin` (2) |
| `/api/v1/gamification` | `app/api/v1/routes/gamification.py` | 1 | `get_current_user` |
| `/api/v1/home` | `app/api/v1/routes/home.py` | 1 | `get_current_user` |
| `/api/v1/interview-prep` | `app/api/v1/routes/interview.py` | 1 *(re-exports legacy)* | `get_current_user_optional` |
| `/api/v1/missions/*` | `app/api/v1/routes/mission.py` | 4 | `get_current_user` (4) |
| `/api/v1/progress` | `app/api/v1/routes/progress.py` | 2 | `get_current_user` (2) |
| `/api/v1/resume` | `app/api/v1/routes/resume.py` | 4 | `get_current_user` (3), `require_plan` (1) |
| `/api/v1/rewrite` | `app/api/v1/routes/rewrite.py` | 1 *(re-exports legacy)* | none |
| `/api/v1/study` | `app/api/v1/routes/study.py` | 4 | `get_current_user` (4) |
| `/api/v1/tracker` | `app/api/v1/routes/tracker.py` | 4 | `get_current_user` (4) |
| `/api/v1/users` | `app/api/v1/routes/users.py` | 1 | `get_current_user` |

### Flat endpoint table

| Method | Path | Handler | Auth | Tags |
|--------|------|---------|------|------|
| POST | /api/analyze | analyze_resume | get_current_user_optional | Analysis |
| POST | /api/cover-letter | generate_cover_letter | none | Cover Letter |
| POST | /api/interview-prep | generate_interview_prep | get_current_user_optional | Interview Prep |
| POST | /api/rewrite | rewrite_resume | none | Rewrite |
| GET | /api/v1/admin/cards | list_cards | require_admin | v1 Admin |
| POST | /api/v1/admin/cards | create_card | require_admin | v1 Admin |
| PUT | /api/v1/admin/cards/{card_id} | update_card | require_admin | v1 Admin |
| DELETE | /api/v1/admin/cards/{card_id} | delete_card | require_admin | v1 Admin |
| POST | /api/v1/admin/cards/generate | generate_card | require_admin | v1 Admin |
| POST | /api/v1/admin/cards/import | import_cards | require_admin | v1 Admin |
| GET | /api/v1/admin/feedback | list_feedback | require_admin | v1 Feedback |
| GET | /api/v1/admin/feedback/summary | feedback_summary | require_admin | v1 Feedback |
| GET | /api/v1/admin/ping | admin_ping | require_admin | v1 Admin |
| GET | /api/v1/admin/registration-logs | list_registration_logs | require_admin | v1 Admin |
| POST | /api/v1/analyze | analyze_resume | get_current_user_optional | v1 Analysis |
| POST | /api/v1/auth/google | google_auth | none | v1 Auth |
| POST | /api/v1/auth/logout | logout | get_current_user | v1 Auth |
| GET | /api/v1/auth/me | get_me | get_current_user | v1 Auth |
| POST | /api/v1/auth/refresh | refresh_access_token | none | v1 Auth |
| GET | /api/v1/cards | list_categories | get_current_user | v1 Cards |
| GET | /api/v1/cards/category/{category_id} | get_category_cards | get_current_user | v1 Cards |
| GET | /api/v1/cards/search | search_cards | get_current_user | v1 Cards |
| GET | /api/v1/cards/{card_id} | get_card | get_current_user | v1 Cards |
| POST | /api/v1/cards/{card_id}/feedback | submit_feedback | get_current_user | v1 Feedback |
| POST | /api/v1/cover-letter | generate_cover_letter | none | v1 Cover Letter |
| GET | /api/v1/email-preferences | get_email_preferences | get_current_user | v1 Email Preferences |
| PUT | /api/v1/email-preferences | update_email_preferences | get_current_user | v1 Email Preferences |
| GET | /api/v1/gamification/stats | get_gamification_stats | get_current_user | v1 Gamification |
| GET | /api/v1/home/state | get_home_state | get_current_user | v1 Home |
| POST | /api/v1/interview-prep | generate_interview_prep | get_current_user_optional | v1 Interview Prep |
| POST | /api/v1/missions/complete-day | complete_day | get_current_user | v1 Mission |
| POST | /api/v1/missions/create | create_mission | get_current_user | v1 Mission |
| GET | /api/v1/missions/active | get_active_mission | get_current_user | v1 Mission |
| GET | /api/v1/missions/daily | get_daily_cards | get_current_user | v1 Mission |
| GET | /api/v1/onboarding/checklist | get_checklist_endpoint | get_current_user | v1 Onboarding |
| GET | /api/v1/onboarding/recommendations | get_recommendations | get_current_user | v1 Onboarding |
| POST | /api/v1/payments/checkout | create_checkout | get_current_user | v1 Payments |
| GET | /api/v1/payments/pricing | get_pricing_endpoint | none | v1 Payments |
| POST | /api/v1/payments/portal | create_portal | get_current_user | v1 Payments |
| POST | /api/v1/payments/paywall-dismiss | paywall_dismiss | get_current_user | v1 Payments *(spec #42, P5-S26b-impl-BE — fires `paywall_dismissed` PostHog on logged=true; LD-8 60s dedup)* |
| GET | /api/v1/payments/should-show-paywall | should_show_paywall | get_current_user | v1 Payments *(spec #42, P5-S26b-impl-BE — Pro/admin bypass returns `{show: false, attempts_until_next: 0}`; free-user grace via `attempts_since_dismiss` query param, Strategy A)* |
| POST | /api/v1/payments/webhook | stripe_webhook | none | v1 Payments *(spec #43 idempotency; spec #42 — `customer.subscription.deleted` branch also stamps `user.downgraded_at`)* |
| GET | /api/v1/progress/heatmap | get_heatmap | get_current_user | v1 Progress |
| GET | /api/v1/progress/radar | get_radar | get_current_user | v1 Progress |
| GET | /api/v1/resume/{resume_id} | get_resume | get_current_user | v1 Resume |
| GET | /api/v1/resume/{resume_id}/diff | get_resume_diff | get_current_user | v1 Resume |
| POST | /api/v1/resume/{resume_id}/optimize | optimize_resume | require_plan | v1 Resume |
| POST | /api/v1/resume/upload | upload_resume | get_current_user | v1 Resume |
| POST | /api/v1/rewrite | rewrite_resume | none | v1 Rewrite |
| GET | /api/v1/study/daily | get_daily_review | get_current_user | v1 Study |
| POST | /api/v1/study/experience | generate_experience | get_current_user | v1 Study |
| GET | /api/v1/study/progress | get_progress | get_current_user | v1 Study |
| POST | /api/v1/study/review | submit_review | get_current_user | v1 Study *(adds 402 branch for `DailyReviewLimitError` per spec #50, P5-S22-WALL-b)* |
| GET | /api/v1/tracker | list_applications | get_current_user | v1 Tracker |
| POST | /api/v1/tracker | create_app | get_current_user | v1 Tracker |
| PATCH | /api/v1/tracker/{app_id} | update_app | get_current_user | v1 Tracker |
| DELETE | /api/v1/tracker/{app_id} | delete_app | get_current_user | v1 Tracker |
| PATCH | /api/v1/users/me/persona | update_persona | get_current_user | v1 Users |

---

## Section 4 — Backend services

### Top-level `app/services/`

| File | Purpose | Public names | External deps |
|------|---------|--------------|---------------|
| ai_card_service.py | AI card generation service — generates flashcard drafts via LLM. | generate_card_draft | LLM-router |
| ai_service.py | AI service — LLM-powered resume optimization features. Duplicates `gpt_service.py` (see `[S47-defer]`). | generate_job_fit_explanation, generate_resume_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt | LLM-router |
| bullet_analyzer.py | Bullet point analyzer and strength scorer. | score_bullet, identify_issues, rewrite_bullet_locally, analyze_bullets | — |
| card_admin_service.py | Admin card CRUD — create, update, delete, list, bulk import. | create_card, update_card, delete_card, list_cards, bulk_import_csv | — |
| card_service.py | Card and category read service with plan-gated access. | list_categories, get_cards_by_category, get_card, search_cards | LLM-direct |
| email_service.py | Thin wrapper around the Resend API for transactional email with retry logic. | send_email, EmailSendError | Resend |
| experience_service.py | AI experience generator — turns study history into resume-ready narratives. | generate_experience | LLM-router |
| formatter_check.py | ATS formatting compliance checker for resume documents. [INFERRED] | check_formatting | — |
| gamification_service.py | XP, streaks, and badges gamification service. | update_streak, reset_streak_if_missed, award_xp, get_stats, BadgeDef, InvalidXPSourceError, StatsView | — |
| gap_detector.py | Skill gap detection service. [INFERRED] | detect_gaps, classify_importance, get_skills_overlap_data | — |
| gap_mapping_service.py | ATS gap → card category mapping service. | map_gaps_to_categories, RecommendedCategory, GapMapping | LLM-direct |
| geo_pricing_service.py | Geo-based pricing showing USD by default, INR for India. | get_pricing | HTTP-external, Redis |
| gpt_service.py | AI resume-optimization features delegating to multi-model LLM router. | generate_job_fit_explanation, generate_resume_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt | LLM-router |
| home_state_service.py | State-aware home dashboard evaluator. | evaluate_state, invalidate | Redis |
| interview_storage_service.py | Interview question set storage + cache-aware generation. | generate_or_get_interview_set, InterviewGenerationResult | LLM-router |
| keywords.py | TF-IDF keyword extraction and matching service. | extract_keywords, match_keywords, get_keyword_chart_data | — |
| mission_service.py | Mission Mode service — time-bound study sprints with FSRS-prioritised cards. | create_mission, get_active_mission, get_mission_daily_cards, complete_mission_day, MissionNotFoundError, MissionConflictError, MissionInvalidError, MissionGoneError | — |
| nlp.py | NLP pipeline using spaCy for entity extraction and skill detection. | get_nlp, extract_entities, extract_skills, extract_job_requirements, calculate_similarity | — |
| onboarding_checklist_service.py | Interview-Prepper onboarding checklist from telemetry-derived state. | get_checklist, WrongPersonaError | — |
| parser.py | Resume parser supporting PDF and DOCX formats. | parse_pdf, parse_docx, detect_sections, extract_bullets, extract_contact_info | — |
| payment_service.py | Payment service — thin wrapper around Stripe. `_handle_subscription_deleted` also writes `user.downgraded_at` per spec #42 LD-5 (dormant until win-back E-031 activates). | create_checkout_session, create_billing_portal_session, handle_webhook, PaymentError, InvalidSignatureError, UserNotFoundError, NotProSubscriberError | Stripe |
| paywall_service.py | Paywall dismissal service (spec #42). `record_dismissal` with LD-8 60s idempotency per (user_id, trigger); `should_show_paywall` with Pro/admin bypass + Strategy A grace counter via FE-passed `attempts_since_dismiss`. Win-back eligibility + send are DEFERRED to BACKLOG E-031 (🟦 back-burner). | record_dismissal, should_show_paywall, RecordDismissalResult, ShouldShowPaywallResult, GRACE_ATTEMPTS, IDEMPOTENCY_WINDOW_SECONDS | — |
| progress_service.py | Progress analytics service with category radar and activity heatmap. [INFERRED] | get_category_coverage, get_activity_heatmap | — |
| reminder_service.py | Daily email reminder service. | get_users_needing_reminder, build_email_body, build_subject, send_daily_reminders | Resend |
| resume_templates.py | Resume template definitions for AI-powered rewriting. | get_template, get_template_names, auto_select_template | — |
| scorer.py | ATS scoring engine for resume ATS compatibility. [INFERRED] | ATSScorer | — |
| study_service.py | FSRS spaced-repetition study service with server-side scheduling. Also enforces the free-tier daily-card review wall (spec #50) via private `_check_daily_wall` helper — Redis INCR keyed `daily_cards:{user_id}:{YYYY-MM-DD}` in user-local tz, 48h TTL, fail-open on Redis outage; admin + Pro/Enterprise bypass. | get_daily_review, create_progress, review_card, get_progress, CardNotFoundError, CardForbiddenError, DailyReviewLimitError | Redis |
| tracker_service_v2.py | SQLAlchemy-backed job application tracker service (v2). | create_application, find_by_scan_id, get_applications, get_application_by_id, update_application, delete_application | — |
| usage_service.py | Usage tracking and plan limit enforcement. [INFERRED] | log_usage, check_usage_limit, check_and_increment, get_usage_summary | — |
| user_service.py | User CRUD service. [INFERRED] | get_or_create_user, get_user_by_id | — |

### `app/services/llm/` (legacy provider factory — do not extend)

| File | Purpose | Public names | External deps |
|------|---------|--------------|---------------|
| factory.py | LLM provider factory — returns the configured provider instance. *(Legacy; Phase-6 cleanup target per Tech Debt.)* | get_llm_provider | — |
| claude_provider.py | Claude LLM provider — wraps the Anthropic SDK. | ClaudeProvider | LLM-direct |
| gemini_provider.py | Gemini LLM provider — wraps the Google Generative AI SDK. | GeminiProvider | LLM-direct |

---

## Section 5 — Alembic revisions

| # | Short revision | Description | down_revision | downgrade() has ops? |
|---|----------------|-------------|---------------|----------------------|
| 1 | 0001_pg_init | initial postgres schema with pgvector | None | yes |
| 2 | ed902312e4ac | add role column to users | 0001_pg_init | yes |
| 3 | 9bb18657d55d | add cards and categories tables | ed902312e4ac | yes |
| 4 | 638a23f7c9ed | add card_progress table | 9bb18657d55d | yes |
| 5 | fdc5af6f825f | add fsrs_step to card_progress | 638a23f7c9ed | yes |
| 6 | 802d5ba2e219 | add gamification tables | fdc5af6f825f | yes |
| 7 | c9863b51075d | add email_preferences table | 802d5ba2e219 | yes |
| 8 | b1674f79f780 | add cards deleted_at for soft delete | c9863b51075d | yes |
| 9 | d3a7e2f91c04 | add persona and onboarding_completed to users | b1674f79f780 | yes |
| 10 | e5b2c8d4a1f7 | add card_feedback table | d3a7e2f91c04 | yes |
| 11 | 83a02cb65464 | add stripe_events table for webhook idempotency | e5b2c8d4a1f7 | yes |
| 12 | a4f1d8e73b92 | add missions and mission_days tables | 83a02cb65464 | yes |
| 13 | 74a6fb27a181 | add target_company and target_date to users | a4f1d8e73b92 | yes |
| 14 | f75789e4967f | add registration_logs table | 74a6fb27a181 | yes |
| 15 | e4eab11b8e33 | add scan_id + skills_matched + skills_missing to tracker | f75789e4967f | yes |
| 16 | d16ca29a5d08 | add categories.tags + cards partial index for active rows | e4eab11b8e33 | yes |
| 17 | 59795ca196e9 | add IVFFlat ANN index on cards.embedding | d16ca29a5d08 | yes |
| 18 | 02bf7265b387 | rename users target columns + migrate persona enum values | 59795ca196e9 | yes |
| 19 | f3350dcba3a5 | add interview_question_sets table | 02bf7265b387 | yes |
| 20 | 1176cc179bf0 | add paywall_dismissals and user.downgraded_at | f3350dcba3a5 | yes |

Head = `1176cc179bf0`.

---

## Section 6 — Frontend routes (live component graph)

Configured in `src/App.tsx`. Top-level wrappers: `<AppShell>` (always), `<ProtectedRoute>` (auth gate) which wraps `<PersonaGate>` (persona null → `/onboarding/persona`), `<Suspense>` for lazy pages.

| Path | Component | Layout wrapper | Auth / persona guard | Duplicate? |
|------|-----------|----------------|----------------------|------------|
| `/` | `HomeRoute` → `LandingPage` (guest) / `<Navigate to="/home">` (auth) | AppShell (chromeless) | none | — |
| `/login` | `LoginPage` | AppShell (chromeless) | none | — |
| `/pricing` | `Pricing` | AppShell (chromeless) | none | — |
| `/home` | `HomeDashboard` | AppShell | ProtectedRoute → PersonaGate | — |
| `/onboarding` | `Onboarding` | AppShell | ProtectedRoute → PersonaGate | — |
| `/onboarding/persona` | `PersonaPicker` | AppShell (chromeless) | ProtectedRoute (PersonaGate allow-listed) | — |
| `/first-action` | `FirstAction` | AppShell (chromeless) | ProtectedRoute → PersonaGate | — |
| `/learn` | `StudyDashboard` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/daily` | `DailyReview` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/category/:id` | `CategoryDetail` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/card/:id` | `CardViewer` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/mission` | `MissionMode` (lazy) | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/analyze` | `Analyze` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/results` | `Results` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/rewrite` | `Rewrite` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/interview` | `Interview` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/tracker` | `Tracker` | AppShell | ProtectedRoute → PersonaGate | — |
| `/profile` | `Profile` (lazy) | AppShell | ProtectedRoute → PersonaGate | — |
| `/admin` | `AdminPanel` (lazy) | AppShell | ProtectedRoute → PersonaGate *(no admin-role gate at route level — component-level check)* | — |
| `/analyze` → `/prep/analyze` | `<Navigate replace>` | AppShell | none | transitional |
| `/results` → `/prep/results` | `<Navigate replace>` | AppShell | none | transitional |
| `/rewrite` → `/prep/rewrite` | `<Navigate replace>` | AppShell | none | transitional |
| `/interview` → `/prep/interview` | `<Navigate replace>` | AppShell | none | transitional |
| `/tracker` → `/prep/tracker` | `<Navigate replace>` | AppShell | none | transitional |
| `/study` → `/learn` | `<Navigate replace>` | AppShell | none | transitional |
| `/study/daily` → `/learn/daily` | `<Navigate replace>` | AppShell | none | transitional |
| `/study/category/:id` → `/learn/category/:id` | `RedirectWithParam` | AppShell | none | transitional |
| `/study/card/:id` → `/learn/card/:id` | `RedirectWithParam` | AppShell | none | transitional |
| `/mission` → `/learn/mission` | `<Navigate replace>` | AppShell | none | transitional |
| `*` | `<Navigate to="/" replace>` | AppShell | none | catch-all |

Nav chrome rendered by `AppShell` (`TopNav` desktop, `MobileNav` mobile). Chromeless paths: `/`, `/login`, `/pricing`, `/onboarding/persona`, `/first-action`.

No component is rendered at two distinct routes (redirects don't count). `AdminPanel` has no route-level `require_admin`-equivalent guard — relies on in-component check.

**Wall-aware components (spec #50, P5-S22-WALL-b):** `src/components/study/QuizPanel.tsx` is the single submit chokepoint for `POST /api/v1/study/review` — consumed by `DailyReview`, `CardViewer`, and `MissionMode`. On a 402 response whose `detail.trigger === 'daily_review'`, it parses the AC-2 payload, opens `PaywallModal` with `trigger="daily_review"`, and fires the `daily_card_wall_hit` PostHog event. No FSRS state is mutated client-side on a walled submit (mirrors backend).

---

## Section 7 — Frontend pages

| File | Default export | Top-level data hooks | API calls | PostHog events |
|------|----------------|----------------------|-----------|----------------|
| AdminPanel.tsx | AdminPanel | — | fetchAdminCards, fetchCategories, createAdminCard, updateAdminCard, deleteAdminCard, generateCardDraft | — |
| Analyze.tsx | Analyze | useAnalysis, useUsage | — | — |
| CardViewer.tsx | CardViewer | useCardViewer, useGamification | — | card_viewed |
| CategoryDetail.tsx | CategoryDetail | — | fetchCardsByCategory | category_detail_viewed |
| DailyReview.tsx | DailyReview | useGamification | fetchDailyQueue | daily_review_started, daily_review_completed |
| FirstAction.tsx | FirstAction | useAuth | — | first_action_viewed, first_action_primary_clicked, first_action_secondary_clicked |
| HomeDashboard.tsx | HomeDashboard | useAuth | — | home_dashboard_viewed |
| Interview.tsx | Interview | useAnalysisContext, useUsage, useInterview | generateInterviewPrep | interview_questions_regenerated, interview_questions_cached_served |
| LandingPage.tsx | LandingPage | useAuth, usePricing | — | landing_page_viewed, cta_clicked |
| LoginPage.tsx | LoginPage | useAuth | signIn | — |
| MissionMode.tsx | MissionMode | useMission, useGamification | — | mission_created, mission_day_completed, mission_completed |
| Onboarding.tsx | Onboarding | useAnalysisContext | fetchOnboardingRecommendations | onboarding_started, onboarding_completed, gap_card_clicked |
| PersonaPicker.tsx | PersonaPicker | useAuth | updatePersona | persona_picker_shown, persona_selected |
| Pricing.tsx | Pricing | useUsage, usePricing, useSearchParams | createCheckoutSession | checkout_started, payment_completed |
| Profile.tsx | Profile | useAuth, useUsage, useGamification | generateExperience, createBillingPortalSession, api.get | profile_viewed, subscription_portal_opened, experience_generated |
| Results.tsx | Results | useAnalysisContext, useUsage | fetchOnboardingRecommendations | job_fit_explanation_viewed, results_tooltip_opened *(via `PanelSection` child — 9-section enum)* |
| Rewrite.tsx | Rewrite | useAnalysisContext, useRewrite, useUsage | — | — |
| StudyDashboard.tsx | StudyDashboard | useStudyDashboard, useAuth, useUsage, useGamification | — | study_dashboard_viewed, locked_tile_clicked, category_tile_clicked |
| Tracker.tsx | Tracker | useTracker | — | — |

---

## Section 8 — Frontend shared types

`src/types/index.ts` (authoritative for API DTOs) + `src/types/homeState.ts` (home dashboard only).

| Type | Shape (compact) | Import count |
|------|-----------------|--------------|
| `ATSScoreBreakdown` | `{ keyword_match, skills_coverage, formatting_compliance, bullet_strength: number }` | 2 |
| `SkillGap` | `{ skill: string, category: Technical\|Soft\|Certification\|Tool, importance: critical\|recommended\|nice-to-have }` | 3 |
| `BulletAnalysis` | `{ original, rewritten: string, score: number, issues: string[] }` | — |
| `FormattingIssue` | `{ issue: string, severity: critical\|warning\|info, fix: string }` | — |
| `KeywordChartData` | `{ keyword: string, resume_count, jd_count: number, matched: boolean }` | — |
| `SkillOverlapData` | `{ subject: string, resume, jd: number }` | — |
| `AnalysisResponse` | `{ scan_id?, ats_score, grade, score_breakdown, matched_keywords, missing_keywords, skill_gaps, bullet_analysis, formatting_issues, job_fit_explanation, top_strengths, top_gaps, keyword_chart_data, skills_overlap_data, resume_text? }` | 2 |
| `RewriteEntry` | `{ org, location, date, title: string, bullets, details: string[] }` | — |
| `RewriteSection` | `{ title, content: string, entries: RewriteEntry[] }` | — |
| `RewriteHeader` | `{ name, contact: string }` | — |
| `RewriteResponse` | `{ header, sections, full_text, template_type }` | 6 |
| `CoverLetterResponse` | `{ cover_letter: string, tone: string }` | 5 |
| `InterviewQuestion` | `{ question: string, star_framework: string }` | 1 |
| `InterviewPrepResponse` | `{ questions: InterviewQuestion[], cached?, generated_at?, model_used? }` | 3 |
| `ApplicationStatus` | `Applied\|Interview\|Offer\|Rejected` | — |
| `TrackerApplication` | `{ id, company, role, date_applied, status, ats_score, scan_id?, skills_matched?[], skills_missing?[], created_at }` | 6 |
| `Category` | `{ id, name, icon, color, display_order, source: foundation\|premium, card_count, studied_count, locked }` | 16 |
| `Card` | `{ id, category_id, category_name, question, answer, difficulty: easy\|medium\|hard, tags[], created_at, updated_at }` | 28 |
| `FsrsRating` | `1\|2\|3\|4` | — |
| `ReviewRequest` | `{ card_id, session_id: string, rating: FsrsRating, time_spent_ms? }` | — |
| `ReviewResponse` | `{ card_id, fsrs_state, due_date, stability, difficulty, reps, lapses, scheduled_days }` | — |
| `DailyCard` | `{ card_id, question, answer, category_id, category_name, difficulty, tags[], fsrs_state, due_date, reps, lapses }` | 3 |
| `DailyQueueResponse` | `{ cards: DailyCard[], total_due: number, session_id: string }` | — |
| `MissionDayView` | `{ day_number, date, cards_target, cards_completed }` | — |
| `MissionResponse` | `{ id, title, target_date, category_ids[], daily_target, total_cards, days_remaining, status: active\|completed\|abandoned, progress_pct, created_at }` | 3 |
| `MissionDetailResponse` | `MissionResponse + { days: MissionDayView[] }` | — |
| `MissionDailyCard` | `{ id, question, answer, category, difficulty }` | — |
| `MissionDailyResponse` | `{ mission_id, day_number, date, cards_target, cards_completed, cards[] }` | — |
| `MissionDayCompleteResponse` | `{ mission_id, day_number, cards_completed, cards_target, xp_awarded, mission_status }` | — |
| `MissionCreateRequest` | `{ title, target_date: string, category_ids: string[] }` | — |
| `RecommendedCategory` | `{ category_id, name, icon, color, matched_card_count, similarity_score\|null }` | — |
| `GapMapping` | `{ gap, match_type: tag\|semantic\|none, matching_categories: RecommendedCategory[] }` | — |
| `OnboardingRecommendationsResponse` | `{ scan_id\|null, results: GapMapping[] }` | — |
| `BadgeView` | `{ badge_id, name, earned_at }` | — |
| `GamificationStats` | `{ user_id, current_streak, longest_streak, total_xp, last_active_date\|null, freezes_available, badges[] }` | 3 |
| `EmailPreference` | `{ user_id, daily_reminder, timezone }` | 4 |
| `EmailPreferenceUpdate` | `{ daily_reminder?, timezone? }` | — |
| `AdminCard` | `{ id, category_id, category_name, question, answer, difficulty, tags[], embedding_status: pending\|ready, created_at, updated_at }` | 3 |
| `AdminCardListResponse` | `{ cards, total, page, per_page, pages }` | — |
| `AdminCardCreateRequest` | `{ category_id, question, answer, difficulty, tags }` | — |
| `AdminCardUpdateRequest` | `Partial<AdminCardCreateRequest>` | — |
| `CardDraft` | `{ question, answer, difficulty, tags }` | 3 |
| `CardImportResponse` | `{ created_count, skipped_count, errors[] }` | — |
| `AnalysisState` | `{ isLoading, error, result, resumeFile, jobDescription }` | — |
| `AnalysisAction` | discriminated union (6 action types) | — |

### Persona / auth types (defined in `src/context/AuthContext.tsx` — not in `types/`)

| Type | Shape | Notes |
|------|-------|-------|
| `Persona` | `'interview_prepper' \| 'career_climber' \| 'team_lead'` | imported by 24 files |
| `AuthUser` | `{ id, email, name, avatar_url\|null, role: user\|admin, persona: Persona\|null, onboarding_completed, interview_target_company?, interview_target_date? }` | direct import count 2; widely consumed indirectly via `useAuth()` |

### Home-state types (`src/types/homeState.ts`)

| Type | Shape |
|------|-------|
| `HomeStateName` | `'mission_overdue' \| 'streak_at_risk' \| 'mission_active' \| 'resume_stale' \| 'inactive_returner' \| 'first_session_done'` |
| `HomeStateContext` | `{ current_streak, last_review_at\|null, active_mission_id\|null, mission_target_date\|null, last_scan_date\|null, plan: free\|pro\|enterprise, last_activity_at\|null }` |
| `HomeStateResponse` | `{ persona, states: HomeStateName[], context: HomeStateContext }` |

---

## Section 9 — Known-dead or transitional code

| Path | Why flagged | Suggested action |
|------|-------------|------------------|
| `hirelens-frontend/src/components/layout/Navbar.tsx` | `AppShell` only imports `TopNav`/`MobileNav`; no file imports `Navbar` (verified with grep). SESSION-STATE already lists as Phase-6 cleanup candidate. | delete |
| `hirelens-frontend/src/components/onboarding/GuidedTour.tsx` | Only self-reference; no page or component imports it. | delete (or migrate if there's a design intent chat-Claude knows about) |
| `hirelens-frontend/src/components/rewrite/ResumePDFTemplate.tsx` | Only self-reference. SESSION-STATE history says PDF export is generated inline via jsPDF. | delete |
| `hirelens-backend/app/services/ai_service.py` | Duplicates `gpt_service.py` public API verbatim. `[S47-defer]` in SESSION-STATE Deferred Hygiene flags it for deletion pending confirmation that the `/api/v1/resume/{id}/optimize` enterprise path has no live traffic. | leave for now (tracked) |
| `hirelens-backend/app/services/llm/factory.py` + `claude_provider.py` + `gemini_provider.py` | Legacy provider abstraction parallel to `app/core/llm_router.py`. Flagged as Phase-6 consolidation in Tech Debt. Not dead — may still be imported by a non-router-aware path. | leave for now (Phase-6) |

No components found behind a `{false && …}` guard or dormant feature flag.

---

## Section 10 — Skills inventory

| File | Description |
|------|-------------|
| admin-panel.md | Card CRUD, bulk import, AI-assisted card generation (Phase 3) |
| analytics.md | PostHog event catalog (frontend + backend), funnels, conventions |
| ats-card-bridge.md | Maps ATS scan skill gaps to study cards, powers onboarding flow |
| ats-scanner.md | ATS resume scanning, scoring, keyword extraction, bullet rewriting, auto-tracker |
| card-extraction.md | JSX → PostgreSQL card extraction pipeline |
| content-pipeline.md | End-to-end content pipeline — card extraction, AI generation, admin CRUD, bulk import |
| database-schema.md | Living reference of all database tables, columns, types, indexes, and relationships |
| db-migration.md | Database migration conventions, Alembic patterns, and schema change rules |
| design-system.md | Theme tokens, multi-theme switching, Tailwind integration, no-flash init |
| experience-gen.md | "My Experience" AI generation — personalized study narratives based on user's learning history |
| gamification.md | Streaks, XP, badges, skill radar, activity heatmap |
| geo-pricing.md | IP-based geo pricing (INR vs USD) with Redis caching and Stripe price ID routing |
| home.md | State-aware home dashboard — priority slot, state evaluator, Redis cache, invalidation |
| llm-strategy.md | LLM task tiering, provider routing, and the generate_for_task() interface |
| mission-mode.md | Interview sprint — countdown timer, daily targets, focused card set |
| notifications.md | Daily email reminders, email preferences, SendGrid/Resend integration |
| payments.md | Stripe checkout, webhooks, plan gating, free tier limits, geo pricing, usage caps |
| security.md | Auth hardening, rate limiting, CORS, request size, webhook idempotency, abuse prevention |
| study-engine.md | **(frontmatter has no `description:` field — see Drift flags)** |
| testing.md | Test patterns, fixtures, mocks for SkillForge |

---

## Section 11 — Drift flags (AGENTS.md / master-doc vs code)

High-signal output — all verified against the current working tree at `f09be80`.

1. **AGENTS.md legacy routers table says `/api/cover_letter` (underscore).**  `hirelens-backend/app/api/routes/cover_letter.py:11` decorates `@router.post("/cover-letter", …)` (hyphen). Effective production path is `/api/cover-letter`. Same class of drift on `/api/interview` vs actual `/api/interview-prep` (`interview.py:17`).

2. **AGENTS.md legacy routers table lists `/api/v1/onboarding` and `/api/v1/payments` as v1 routers, but their files live in the legacy folder.**  `from app.api.routes import onboarding, payments` + `include_router(... prefix="/api/v1")` at `app/main.py:15-22, 143-144`. The files sit in `app/api/routes/` not `app/api/v1/routes/`. The fix is either a file move or a docs note; the table as-written implies they're in the v1 folder.

3. **AGENTS.md Models table User row (lines 243-244) still lists `target_company`, `target_date`.**  Already captured in SESSION-STATE Deferred Hygiene as an S16 retrofit. On disk (`app/models/user.py`) the columns are `interview_target_company` (String(100)) and `interview_target_date` (Date). Migration `02bf7265b387` did the rename.

4. **AGENTS.md Routes table references `/api/v1/mission` (singular).**  Actual mount prefix in `main.py:140` is `/api/v1`, and the decorators are `/missions/create`, `/missions/active`, `/missions/daily`, `/missions/complete-day` — plural. Already captured as `[S35-flag]`; still present.

5. **AGENTS.md says `Category` has a `source` column.** True, but it also has a `tags` JSONB column (migration `d16ca29a5d08`). AGENTS.md does not mention `categories.tags`.

6. **AGENTS.md Models table references `UsageLimit`.**  There is no `UsageLimit` model file on disk (`app/models/` contains no such file). Either the model lives inline in another module, was never created, or was removed. Usage limits appear to be enforced in `usage_service.py` logic rather than a DB table.

7. **Email-preferences route path mismatch.**  Confirmed already in SESSION-STATE Tech Debt. `app/api/v1/routes/email_prefs.py` decorators use `/email-preferences`; FE `services/api.ts:333,340` calls `/api/v1/email-preferences`. Both ends currently agree on `/email-preferences` on the wire, but the AGENTS.md table at line 186 shows `/api/v1/email-prefs`.

8. **`study-engine.md` skill file has no `description:` frontmatter field.**  All other 19 skill files have one; this one has only a top-of-file `# Study Engine Skill` heading. Skill-discovery tools that key off the description may silently skip it.

9. **Tracker auto-save JD dedupe is documented as locked but not implemented.**  Already captured in SESSION-STATE Locked Decisions (Auto-save scan to tracker) and `[5.17-follow] tracker jd_hash dedupe`. Verified here: `tracker_applications_v2` has no `jd_hash` column (Section 2); `tracker_service_v2.py` does not import `hash_jd`; `app/utils/text_hash.py::hash_jd` exists but only `interview_storage_service.py` consumes it.

10. **Four legacy `/api/*` routers still mounted alongside v1 counterparts.**  `analyze`, `rewrite`, `cover_letter`, `interview` in `app/main.py:120-123`. Already captured as `[5.17-follow] flat /api/* legacy-route cleanup`. The v1 equivalents for `cover_letter`, `rewrite`, and `interview` are *re-exports* of the legacy routers (no decorators in the v1 files), so deprecating the legacy mount would require moving the handlers first.

---

## Section 12 — Open questions for Dhamo

1. `components/onboarding/GuidedTour.tsx` has zero imports. Is this (A) dead code safe to delete, or (B) a scaffold you're saving for a future onboarding tour spec?
2. `components/rewrite/ResumePDFTemplate.tsx` has zero imports and PDF generation is inline in `Rewrite.tsx`. Delete in next cleanup slice — yes/no?
3. Is `UsageLimit` supposed to exist as a DB-backed model, or is the AGENTS.md Models table row stale and should be removed?
4. `AdminPanel` (`/admin`) has no route-level admin guard — just `ProtectedRoute` + `PersonaGate`. Is the in-component role check intentional, or should `/admin` gain an `<AdminGate>` wrapper for parity with the backend's `require_admin` dependency?
5. `study-engine.md` skill file is missing `description:` frontmatter — should I backfill it to match the style of the other 19 skills? (Would be a one-line edit.)
6. `ai_service.py` duplicates `gpt_service.py` verbatim and is consumed only by an enterprise-tier endpoint (`/api/v1/resume/{id}/optimize`). Is it safe to delete now, or do you want to wait on a production traffic check per `[S47-defer]`?
7. Legacy mounts `/api/analyze`, `/api/rewrite`, `/api/cover-letter`, `/api/interview-prep` — is there a known external caller relying on these paths, or are they purely FE-migration holdovers that can be dropped once the FE references are swept?

---

*End of snapshot.*
