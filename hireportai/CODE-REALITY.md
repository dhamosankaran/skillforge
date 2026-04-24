# CODE-REALITY — SkillForge / HirePort AI

> **Purpose:** frozen-in-time map of the codebase for off-disk advisors (chat-Claude) to draft accurate prompts. If the header sha below doesn't match `git rev-parse --short HEAD`, regenerate this file.
> **Read-only artifact.** Nothing here authorizes code changes.

---

## Section 1 — Repo metadata

| Field | Value |
|-------|-------|
| Commit sha (short) | `1bf6c3b` (HEAD after B-032 SHA backfill). Targeted updates on this pass for spec #58 / B-033 impl: §1 endpoint count stays the same (6 route bodies changed, no new route); §3 `POST /rewrite`, `POST /rewrite/section`, `POST /cover-letter` (each x 2 mount prefixes = 6 rows) gain `get_current_user` auth + 402 quota branch, `GET /payments/usage` response extends with 6 new fields for rewrite + cover-letter counters; §4 `usage_service.py` (renamed `get_analyze_usage` → `get_usage_snapshot` with back-compat alias; new `_counter_triple` helper; lifetime counters for `rewrite` + `cover_letter`), `paywall_service.py` (hard-wall trigger set expanded from `{scan_limit}` to `{scan_limit, rewrite_limit, cover_letter_limit}`). Prior spec #56 pass touched: `POST /analyze` 402 branch + new `GET /payments/usage` row, `get_analyze_usage` helper, `scan_limit` carve-out. Prior regen snapshots: `7ca2e90` / `806c199` / `96e6096` / `a13c217` / `3cef6c3`. |
| Branch | `main` (24 commits ahead of `origin/main`; not yet pushed — scheduled for push alongside this regen) |
| Generated | 2026-04-23 (body sweep completed: Sections 1-8 + 11-12 audited against HEAD `7ca2e90`. Caught up: E-018a `admin_audit_log` model (§2), E-018b `admin_analytics_service` + routes + `AdminAnalytics.tsx` (§3-4-6-7), E-040 `AdminGate` + `reconcile_admin_role` (§4-6-12), B-001 `/rewrite/section` + `RewriteError` (§3-4), B-014 `SECTION_THINKING_BUDGET` headroom (§4 gpt_service), B-016 `users.home_first_visit_seen_at` (§2) + `POST /users/me/home-first-visit` (§3), B-021 + B-024 `_extract_company_name` LLM-primary orchestrator (§4 nlp.py), B-022 `job_fit_explanation` reasoning tier (§4), B-023 `_extract_candidate_name` all-caps guard (§4), B-027 HomeDashboard `isFirstVisit` snapshot (§7), B-028 UserMenu + Profile account section (§6-7), AdminGate wraps both admin routes closing §12 Q4. Section 9 (dead code) + Section 10 (skills inventory) + Section 11 (drift flags) not re-checked in this pass — treat as potentially stale beyond the known skill-file addition and drift items carried forward below. |
| Backend model files | 19 (`app/models/*.py`, excl. `__init__`, `request_models`, `response_models` — adds `admin_audit_log.py`) |
| Backend service files | 31 top-level (+1 `admin_analytics_service.py`) + 3 under `services/llm/` = 34 |
| Backend router files | 18 v1 (+1 `admin_analytics.py`) + 6 legacy = 24 |
| Backend endpoints (total) | 64+ (new this slice: `GET /api/v1/payments/usage` for spec #56 free-tier scan snapshot; prior additions: `GET /admin/audit`, `GET /admin/analytics/metrics`, `GET /admin/analytics/performance`, `POST /users/me/home-first-visit`). `analyze` / `rewrite` / `cover_letter` / `interview` legacy routers are each mounted at both `/api/*` and `/api/v1/*`, so 5 paths appear twice. |
| Alembic revisions | 22 (adds `508df0110037` B-016, `538fe233b639` E-018a) |
| Frontend pages | 20 (+`AdminAnalytics.tsx`) |
| Frontend components (`.tsx` under `src/components/`, excl. `__tests__`) | 63+ (+`layout/UserMenu.tsx` B-028, +`mission/MissionDateGate.tsx` B-018, +`auth/AdminGate.tsx` E-040; not counted individually — verify on next full regen) |
| Specs on disk (`docs/specs/**/*.md`) | 74 (+spec #38 admin-analytics E-018 umbrella, +spec #54 admin email whitelist E-040) |
| Skill files (`.agent/skills/*.md`) | 20 (`analytics.md` updated 2026-04-23 with `sign_out_clicked`, `admin_analytics_viewed` (live), `admin_analytics_segment_changed`, `admin_role_reconciled` events; `admin-panel.md` expanded for E-018 umbrella; no new skill file) |

---

## Section 2 — Backend models

### `admin_audit_log.py`
**Class:** `AdminAuditLog`  **Table:** `admin_audit_log`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| admin_id | String (FK `users.id` ON DELETE RESTRICT, indexed) | NOT NULL |
| route | String(255) | NOT NULL |
| method | String(10) | NOT NULL |
| query_params | JSONB | NOT NULL, server default `{}` |
| ip_address | String(45) | NOT NULL |
| created_at | DateTime(timezone=True) | NOT NULL, server default `now()` (indexed) |

**Indexes:** `ix_admin_audit_admin_created` on `(admin_id, created_at)`, `ix_admin_audit_route_created` on `(route, created_at)` — serve the two common audit-trail read patterns (per-admin trail, per-endpoint trail) used by `/api/v1/admin/audit`.

**Relationships:** none declared. `admin_id` ON DELETE RESTRICT is a forensic guardrail — a user row with audit history cannot be deleted without first purging audit rows (verified live by the E-018b smoke test).

Purpose: append-only audit trail for every admin-scoped HTTP request. Written fire-and-forget-scheduled-with-request-scoped-flush via `core.deps.audit_admin_request` (router-level dep on `/api/v1/admin/*`). Also written directly by `auth.py::_log_role_reconciliation` on admin role promote/demote events (spec #54 E-040). Spec: `docs/specs/phase-5/38-admin-analytics.md` (AC-9).

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
| home_first_visit_seen_at | DateTime(timezone=True) | nullable, default `None` (B-016; stamped on first `/home` load via idempotent `POST /api/v1/users/me/home-first-visit`; flips greeting copy "Welcome" → "Welcome back". B-027 patched the FE to snapshot on mount so in-mount stamp doesn't flip the rendered copy within a single session) |
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
| `/api/cover-letter` | `app/api/routes/cover_letter.py` | 1 | `get_current_user` *(spec #58 / B-033 — 402 on cap hit, `cover_letter_limit` trigger)* |
| `/api/interview-prep` | `app/api/routes/interview.py` | 1 | `get_current_user_optional` |
| `/api/rewrite` | `app/api/routes/rewrite.py` | 2 | `get_current_user` *(spec #58 / B-033 — 402 on cap hit, shared `"rewrite"` bucket for both `/rewrite` and `/rewrite/section`, `rewrite_limit` trigger)* |
| `/api/v1/onboarding` | `app/api/routes/onboarding.py` *(legacy folder, v1 mount)* | 2 | `get_current_user` |
| `/api/v1/payments` | `app/api/routes/payments.py` *(legacy folder, v1 mount)* | 6 | `get_current_user` (4), none (2) |
| `/api/v1/admin` | `app/api/v1/routes/admin.py` | 9 | `audit_admin_request` (router-level, chains `require_admin`) |
| `/api/v1/admin/analytics` | `app/api/v1/routes/admin_analytics.py` | 2 | `audit_admin_request` (router-level, chains `require_admin`) — spec #38 E-018b slice 2/4 |
| `/api/v1/analyze` | `app/api/v1/routes/analyze.py` | 1 | `get_current_user_optional` |
| `/api/v1/auth` | `app/api/v1/routes/auth.py` | 4 | `get_current_user` (1), none (3) |
| `/api/v1/cards` | `app/api/v1/routes/cards.py` | 4 | `get_current_user` (4) |
| `/api/v1/cover-letter` | `app/api/v1/routes/cover_letter.py` | 1 *(re-exports legacy)* | `get_current_user` *(spec #58)* |
| `/api/v1/email-preferences` | `app/api/v1/routes/email_prefs.py` | 2 | `get_current_user` (2) |
| `/api/v1/feedback` + `/api/v1/admin/feedback` | `app/api/v1/routes/feedback.py` | 3 | `get_current_user` (1), `require_admin` (2) |
| `/api/v1/gamification` | `app/api/v1/routes/gamification.py` | 1 | `get_current_user` |
| `/api/v1/home` | `app/api/v1/routes/home.py` | 1 | `get_current_user` |
| `/api/v1/interview-prep` | `app/api/v1/routes/interview.py` | 1 *(re-exports legacy)* | `get_current_user_optional` |
| `/api/v1/missions/*` | `app/api/v1/routes/mission.py` | 4 | `get_current_user` (4) |
| `/api/v1/progress` | `app/api/v1/routes/progress.py` | 2 | `get_current_user` (2) |
| `/api/v1/resume` | `app/api/v1/routes/resume.py` | 4 | `get_current_user` (3), `require_plan` (1) |
| `/api/v1/rewrite` | `app/api/v1/routes/rewrite.py` | 2 *(re-exports legacy — includes `/rewrite/section`)* | `get_current_user` *(spec #58)* |
| `/api/v1/study` | `app/api/v1/routes/study.py` | 4 | `get_current_user` (4) |
| `/api/v1/tracker` | `app/api/v1/routes/tracker.py` | 4 | `get_current_user` (4) |
| `/api/v1/users` | `app/api/v1/routes/users.py` | 1 | `get_current_user` |

### Flat endpoint table

| Method | Path | Handler | Auth | Tags |
|--------|------|---------|------|------|
| POST | /api/analyze | analyze_resume | get_current_user_optional | Analysis *(spec #56, B-031 — 402 quota branch, see `/api/v1/analyze` row below for full notes)* |
| POST | /api/cover-letter | generate_cover_letter | get_current_user | Cover Letter *(spec #58 / B-033 — 402 `free_tier_limit` / `cover_letter_limit` for free plan; admin + Pro + Enterprise bypass)* |
| POST | /api/interview-prep | generate_interview_prep | get_current_user_optional | Interview Prep |
| POST | /api/rewrite | rewrite_resume | get_current_user | Rewrite *(spec #58 / B-033 — 402 `free_tier_limit` / `rewrite_limit` with `attempted_action='full'` for free plan)* |
| POST | /api/rewrite/section | rewrite_section | get_current_user | Rewrite *(spec #51, B-001 impl — per-section regen. spec #58 / B-033 — shares `"rewrite"` bucket; 402 envelope `attempted_action='section'`)* |
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
| GET | /api/v1/admin/audit | list_admin_audit_log | audit_admin_request → require_admin | v1 Admin *(spec #38 E-018a)* |
| GET | /api/v1/admin/analytics/metrics | metrics_endpoint | audit_admin_request → require_admin | v1 Admin Analytics *(spec #38 E-018b slice 2/4)* |
| GET | /api/v1/admin/analytics/performance | performance_endpoint | audit_admin_request → require_admin | v1 Admin Analytics *(spec #38 E-018b slice 2/4)* |
| POST | /api/v1/analyze | analyze_resume | get_current_user_optional | v1 Analysis *(spec #56, B-031 — 402 branch via `check_and_increment(..., "analyze", window="lifetime")` for authenticated free users; anonymous + Pro + Enterprise + admin bypass; payload shape mirrors `DailyReviewLimitError` / spec #50)* |
| POST | /api/v1/auth/google | google_auth | none | v1 Auth |
| POST | /api/v1/auth/logout | logout | get_current_user | v1 Auth |
| GET | /api/v1/auth/me | get_me | get_current_user | v1 Auth |
| POST | /api/v1/auth/refresh | refresh_access_token | none | v1 Auth |
| GET | /api/v1/cards | list_categories | get_current_user | v1 Cards |
| GET | /api/v1/cards/category/{category_id} | get_category_cards | get_current_user | v1 Cards |
| GET | /api/v1/cards/search | search_cards | get_current_user | v1 Cards |
| GET | /api/v1/cards/{card_id} | get_card | get_current_user | v1 Cards |
| POST | /api/v1/cards/{card_id}/feedback | submit_feedback | get_current_user | v1 Feedback |
| POST | /api/v1/cover-letter | generate_cover_letter | get_current_user | v1 Cover Letter *(spec #58 / B-033)* |
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
| GET | /api/v1/payments/should-show-paywall | should_show_paywall | get_current_user | v1 Payments *(spec #42, P5-S26b-impl-BE — Pro/admin bypass returns `{show: false, attempts_until_next: 0}`; free-user grace via `attempts_since_dismiss` query param, Strategy A; spec #56 LD-4 carve-out — `trigger='scan_limit'` always returns `{show: true, attempts_until_next: 0}` for free users regardless of dismissal history)* |
| GET | /api/v1/payments/usage | get_usage | get_current_user | v1 Payments *(spec #56 / B-031 + spec #58 / B-033 — lifetime usage snapshot; returns flat `{plan, is_admin, scans_{used,remaining,max}, rewrites_{used,remaining,max}, cover_letters_{used,remaining,max}}` with `-1` sentinel for unlimited Pro/Enterprise/admin. Rewrite + cover-letter counters added by spec #58 §5)* |
| POST | /api/v1/payments/webhook | stripe_webhook | none | v1 Payments *(spec #43 idempotency; spec #42 — `customer.subscription.deleted` branch also stamps `user.downgraded_at`)* |
| GET | /api/v1/progress/heatmap | get_heatmap | get_current_user | v1 Progress |
| GET | /api/v1/progress/radar | get_radar | get_current_user | v1 Progress |
| GET | /api/v1/resume/{resume_id} | get_resume | get_current_user | v1 Resume |
| GET | /api/v1/resume/{resume_id}/diff | get_resume_diff | get_current_user | v1 Resume |
| POST | /api/v1/resume/{resume_id}/optimize | optimize_resume | require_plan | v1 Resume |
| POST | /api/v1/resume/upload | upload_resume | get_current_user | v1 Resume |
| POST | /api/v1/rewrite | rewrite_resume | get_current_user | v1 Rewrite *(spec #58 / B-033 — shared `"rewrite"` bucket)* |
| POST | /api/v1/rewrite/section | rewrite_section | get_current_user | v1 Rewrite *(spec #51, B-001 impl — per-section regen. spec #58 / B-033 — shares `"rewrite"` bucket)* |
| GET | /api/v1/study/daily | get_daily_review | get_current_user | v1 Study |
| POST | /api/v1/study/experience | generate_experience | get_current_user | v1 Study |
| GET | /api/v1/study/progress | get_progress | get_current_user | v1 Study |
| POST | /api/v1/study/review | submit_review | get_current_user | v1 Study *(adds 402 branch for `DailyReviewLimitError` per spec #50, P5-S22-WALL-b)* |
| GET | /api/v1/tracker | list_applications | get_current_user | v1 Tracker |
| POST | /api/v1/tracker | create_app | get_current_user | v1 Tracker |
| PATCH | /api/v1/tracker/{app_id} | update_app | get_current_user | v1 Tracker |
| DELETE | /api/v1/tracker/{app_id} | delete_app | get_current_user | v1 Tracker |
| PATCH | /api/v1/users/me/persona | update_persona | get_current_user | v1 Users |
| POST | /api/v1/users/me/home-first-visit | mark_home_first_visit | get_current_user | v1 Users *(B-016; idempotent stamp — flips greeting copy)* |

---

## Section 4 — Backend services

### Top-level `app/services/`

| File | Purpose | Public names | External deps |
|------|---------|--------------|---------------|
| ai_card_service.py | AI card generation service — generates flashcard drafts via LLM. | generate_card_draft | LLM-router |
| ai_service.py | AI service — LLM-powered resume optimization features. Duplicates `gpt_service.py` (see `[S47-defer]`). | generate_job_fit_explanation, generate_resume_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt | LLM-router |
| bullet_analyzer.py | Bullet point analyzer and strength scorer. | score_bullet, identify_issues, rewrite_bullet_locally, analyze_bullets | — |
| card_admin_service.py | Admin card CRUD — create, update, delete, list, bulk import. | create_card, update_card, delete_card, list_cards, bulk_import_csv | — |
| admin_analytics_service.py | Admin analytics aggregations (spec #38 E-018b slice 2/4). Six-OKR metrics with 7d/30d deltas; performance snapshot with LLM spend estimate (Postgres `usage_logs.tokens_consumed` × `llm_router.TIER_PRICE_USD_PER_1M_TOKENS`) and Stripe webhook success rate. `api_latency` + `error_rate_24h_pct` are emitted as deferred placeholders (empty/null + `available: false` markers) pending E-018b-follow / E-018b-follow-errors. Redis-cached 5 min with graceful degradation. | get_metrics_summary, get_performance_summary, CACHE_TTL_SECONDS | Redis |
| card_service.py | Card and category read service with plan-gated access. | list_categories, get_cards_by_category, get_card, search_cards | LLM-direct |
| email_service.py | Thin wrapper around the Resend API for transactional email with retry logic. | send_email, EmailSendError | Resend |
| experience_service.py | AI experience generator — turns study history into resume-ready narratives. | generate_experience | LLM-router |
| formatter_check.py | ATS formatting compliance checker for resume documents. [INFERRED] | check_formatting | — |
| gamification_service.py | XP, streaks, and badges gamification service. | update_streak, reset_streak_if_missed, award_xp, get_stats, BadgeDef, InvalidXPSourceError, StatsView | — |
| gap_detector.py | Skill gap detection service. [INFERRED] | detect_gaps, classify_importance, get_skills_overlap_data | — |
| gap_mapping_service.py | ATS gap → card category mapping service. | map_gaps_to_categories, RecommendedCategory, GapMapping | LLM-direct |
| geo_pricing_service.py | Geo-based pricing showing USD by default, INR for India. | get_pricing | HTTP-external, Redis |
| gpt_service.py | AI resume-optimization features delegating to multi-model LLM router. Post-B-001 (`167b70f`, spec #51): `generate_resume_rewrite` / `generate_resume_rewrite_async` return `Tuple[RewriteResponse, path_str]` where `path_str ∈ {"chunked", "fallback_full"}` is a telemetry hint — see D-014. Per-section regen entry point is `generate_section_rewrite`. `RewriteError` raised on truncation / malformed JSON (caller maps to AC-5 502 envelope). Chunking uses an asyncio semaphore bounded at `PARALLEL_SECTION_LIMIT=4`. Post-B-002 (`825eb0e`, spec #52): `generate_cover_letter` returns the structured `CoverLetterResponse` (spec #52 LD-2 shape); `full_text` is assembled server-side via `_join_cover_letter` — never LLM-sourced. `body_paragraphs` is Pydantic-pinned to `len==3`; validation failures surface as `cover_letter_validation_error` under the AC-5 502 envelope. Post-B-014 (`067c232`): `SECTION_MAX_TOKENS=4000` + `SECTION_THINKING_BUDGET=800` passed to both chunked and per-section endpoints so Gemini 2.5 Pro's thinking pool cannot starve the output pool. Post-B-022 (`fa1871e`): `generate_job_fit_explanation` now routed through the reasoning tier (`JOB_FIT_MAX_TOKENS=3500`, `JOB_FIT_THINKING_BUDGET=800`). Post-B-023 (`79f76b4`): `_extract_candidate_name` rejects pure-uppercase lines (section-header guard) before the token-regex check — prevents `"KEY ACHIEVEMENTS"` / `"WORK EXPERIENCE"` from leaking into the cover-letter signature. | generate_job_fit_explanation, generate_resume_rewrite, generate_resume_rewrite_async, generate_section_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt, RewriteError, _join_cover_letter, _extract_candidate_name, SECTION_MAX_TOKENS, SECTION_THINKING_BUDGET, JOB_FIT_MAX_TOKENS, JOB_FIT_THINKING_BUDGET | LLM-router |
| home_state_service.py | State-aware home dashboard evaluator. | evaluate_state, invalidate | Redis |
| interview_storage_service.py | Interview question set storage + cache-aware generation. | generate_or_get_interview_set, InterviewGenerationResult | LLM-router |
| keywords.py | TF-IDF keyword extraction and matching service. | extract_keywords, match_keywords, get_keyword_chart_data | — |
| mission_service.py | Mission Mode service — time-bound study sprints with FSRS-prioritised cards. | create_mission, get_active_mission, get_mission_daily_cards, complete_mission_day, MissionNotFoundError, MissionConflictError, MissionInvalidError, MissionGoneError | — |
| nlp.py | NLP pipeline using spaCy for entity extraction and skill detection. Post-B-021 (`e7c6d73`) + B-024 (`50e3c3c`): `_extract_company_name` is now a three-layer orchestrator — LLM primary (`company_name_extraction` FAST task, null-on-unclear), regex fallback on LLM infra failure via `_extract_company_name_regex`, aggregator deny-list + 100-char cap on LLM output. `extract_job_requirements` returns `company_name: str \| None` in its dict; two live consumers (cover-letter prompt in `gpt_service.generate_cover_letter`, tracker autopopulate in `api/routes/analyze.py`) pick it up automatically and fall back to "your company" / "Unknown Company" on None. | get_nlp, extract_entities, extract_skills, extract_job_requirements, calculate_similarity, _extract_company_name, _extract_company_name_regex | LLM-router |
| onboarding_checklist_service.py | Interview-Prepper onboarding checklist from telemetry-derived state. | get_checklist, WrongPersonaError | — |
| parser.py | Resume parser supporting PDF and DOCX formats. | parse_pdf, parse_docx, detect_sections, extract_bullets, extract_contact_info | — |
| payment_service.py | Payment service — thin wrapper around Stripe. `_handle_subscription_deleted` also writes `user.downgraded_at` per spec #42 LD-5 (dormant until win-back E-031 activates). | create_checkout_session, create_billing_portal_session, handle_webhook, PaymentError, InvalidSignatureError, UserNotFoundError, NotProSubscriberError | Stripe |
| paywall_service.py | Paywall dismissal service (spec #42). `record_dismissal` with LD-8 60s idempotency per (user_id, trigger); `should_show_paywall` with Pro/admin bypass + Strategy A grace counter via FE-passed `attempts_since_dismiss`. Hard-wall carve-outs (amend spec #42 LD-1 — trigger set is now `{scan_limit, rewrite_limit, cover_letter_limit}`): for any of those three triggers on a free user, always returns `{show: True, attempts_until_next: 0}` regardless of dismissal history. `scan_limit` from spec #56 LD-4; `rewrite_limit` + `cover_letter_limit` added by spec #58 LD-5 (Pro-only features — no legitimate "browse" surface to soften). Win-back eligibility + send are DEFERRED to BACKLOG E-031. | record_dismissal, should_show_paywall, RecordDismissalResult, ShouldShowPaywallResult, GRACE_ATTEMPTS, IDEMPOTENCY_WINDOW_SECONDS | — |
| progress_service.py | Progress analytics service with category radar and activity heatmap. [INFERRED] | get_category_coverage, get_activity_heatmap | — |
| reminder_service.py | Daily email reminder service. | get_users_needing_reminder, build_email_body, build_subject, send_daily_reminders | Resend |
| resume_templates.py | Resume template definitions for AI-powered rewriting. | get_template, get_template_names, auto_select_template | — |
| scorer.py | ATS scoring engine for resume ATS compatibility. [INFERRED] | ATSScorer | — |
| study_service.py | FSRS spaced-repetition study service with server-side scheduling. Also enforces the free-tier daily-card review wall (spec #50) via private `_check_daily_wall` helper — Redis INCR keyed `daily_cards:{user_id}:{YYYY-MM-DD}` in user-local tz, 48h TTL, fail-open on Redis outage; admin + Pro/Enterprise bypass. | get_daily_review, create_progress, review_card, get_progress, CardNotFoundError, CardForbiddenError, DailyReviewLimitError | Redis |
| tracker_service_v2.py | SQLAlchemy-backed job application tracker service (v2). | create_application, find_by_scan_id, get_applications, get_application_by_id, update_application, delete_application | — |
| usage_service.py | Usage tracking + plan-limit enforcement. Per spec #56 / B-031 (2026-04-23): `PLAN_LIMITS["free"]["analyze"] = 1` (lifetime). `check_and_increment` and `check_usage_limit` accept `window: Literal["monthly","lifetime"] = "monthly"` — analyze + rewrite + cover_letter callers pass `"lifetime"` (spec #58 §4.1); interview_prep and resume_optimize keep monthly. Admin bypass via in-helper User role fetch (mirrors paywall_service:168 convention); short-circuits to `allowed=True, limit=-1` before counter check. Return dict extended with `used: int` for the 402 envelope. Per spec #58 / B-033 (2026-04-23): `get_analyze_usage` replaced by `get_usage_snapshot` (back-compat alias retained) — returns the flat extended shape with scan + rewrite + cover-letter counters for `GET /api/v1/payments/usage`. New `_counter_triple(used, max, is_admin)` helper centralizes the `-1` sentinel collapse for admin / unlimited plans. `/rewrite` + `/rewrite/section` share the `"rewrite"` feature key (spec #58 §4.1 Option a) — no separate `section_rewrite` PLAN_LIMITS entry; `/cover-letter` uses its own `"cover_letter"` key. `PLAN_LIMITS["free"]["rewrite"] = 0` and `…["cover_letter"] = 0` are live (no longer dead code — consumed by the route handlers post-B-033). | log_usage, check_usage_limit, check_and_increment, get_usage_summary, get_usage_snapshot, get_analyze_usage (alias), _counter_triple, PLAN_LIMITS, Window | — |
| user_service.py | User CRUD + admin-role reconciliation. Post-E-040 (`1148354`, spec #54): `reconcile_admin_role(user, admin_emails_set) -> (action, prior_role, new_role)` is a pure mutation function that sets `user.role` to `"admin"` if `email.lower() in admin_emails_set` and `"user"` otherwise. Action ∈ `{"promoted", "demoted", "unchanged"}`; caller owns commit / audit / analytics. Invoked from `auth.py::google_auth` on every login — the `unchanged` case doubles as a dashboard heartbeat. | get_or_create_user, get_user_by_id, reconcile_admin_role | — |

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
| 21 | 508df0110037 | add users.home_first_visit_seen_at | 1176cc179bf0 | yes — B-016 |
| 22 | 538fe233b639 | add admin_audit_log | 508df0110037 | yes — E-018a slice 1/4 |

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
| `/admin` | `AdminPanel` (lazy) | AppShell | ProtectedRoute → `AdminGate` (role === 'admin' else 403 view) | — |
| `/admin/analytics` | `AdminAnalytics` (lazy) | AppShell | ProtectedRoute → `AdminGate` | — — spec #38 E-018b slice 2/4 |
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

**TopNav composition (desktop, `md:block`):** left = wordmark `SKILL/FORGE` → `/home`; middle = nav links (`Home` / `Learn` / `Prep` / `Profile` / `Admin` if admin); right = `<UserMenu />` (new component `src/components/layout/UserMenu.tsx`, B-028 2026-04-23) — avatar circle + keyboard-accessible dropdown (aria-haspopup/expanded, role=menu, Escape + click-outside close, focus return on Escape) exposing Profile link + `Sign out` button. Sign-out calls `AuthContext.signOut()` and fires `sign_out_clicked {source: 'topnav_avatar'}` before the redirect-to-`/`. Renders nothing when `user === null`.

**MobileNav composition (`md:hidden`):** five-tab bottom bar (Home/Learn/Prep/Profile/Admin) — **no sign-out surface here**. Mobile users reach sign-out via MobileNav → Profile → Account section (B-028) because the bar is at capacity.

No component is rendered at two distinct routes (redirects don't count). Both `/admin` and `/admin/analytics` are wrapped in `<AdminGate>` (E-040, `1148354`, spec #54) — non-admins see a `ShieldAlert` 403 view with a back-link to `/home`, and the lazy AdminPanel / AdminAnalytics chunks are **not downloaded** for non-admins. This supersedes the earlier "component-level check only" pattern and closes Section 12 Q4.

**Wall-aware components (spec #50, P5-S22-WALL-b):** `src/components/study/QuizPanel.tsx` is the single submit chokepoint for `POST /api/v1/study/review` — consumed by `DailyReview`, `CardViewer`, and `MissionMode`. On a 402 response whose `detail.trigger === 'daily_review'`, it parses the AC-2 payload, opens `PaywallModal` with `trigger="daily_review"`, and fires the `daily_card_wall_hit` PostHog event. No FSRS state is mutated client-side on a walled submit (mirrors backend).

---

## Section 7 — Frontend pages

| File | Default export | Top-level data hooks | API calls | PostHog events |
|------|----------------|----------------------|-----------|----------------|
| AdminPanel.tsx | AdminPanel | — | fetchAdminCards, fetchCategories, createAdminCard, updateAdminCard, deleteAdminCard, generateCardDraft | — |
| AdminAnalytics.tsx | AdminAnalytics | useAuth | fetchAdminAnalyticsMetrics, fetchAdminAnalyticsPerformance | admin_analytics_segment_changed. Sections: Metrics (6 OKR tiles) + Performance (LLM spend, Stripe webhook success, 2 Coming-Soon tiles for deferred fields). Segmented `7d/30d/90d/YTD` control computes `?from=` client-side; `computeFromDate(segment, now)` is exported for tests. Spec #38 E-018b slice 2/4. |
| Analyze.tsx | Analyze | useAnalysis, useUsage | — | — |
| CardViewer.tsx | CardViewer | useCardViewer, useGamification | — | card_viewed |
| CategoryDetail.tsx | CategoryDetail | — | fetchCardsByCategory | category_detail_viewed |
| DailyReview.tsx | DailyReview | useGamification | fetchDailyQueue | daily_review_started, daily_review_completed |
| FirstAction.tsx | FirstAction | useAuth | — | first_action_viewed, first_action_primary_clicked, first_action_secondary_clicked |
| HomeDashboard.tsx | HomeDashboard | useAuth | markHomeFirstVisit *(B-016)* | home_dashboard_viewed. Greeting fork: `isFirstVisit` is **snapshotted on mount** via `useState(() => user.home_first_visit_seen_at == null)` — B-027 fix (`e792bb4`, 2026-04-23) so the post-stamp `updateUser` call does not flip `"Welcome, ${firstName}."` → `"Welcome back, ${firstName}."` within a single mount. Stamp effect still fires (persists server-side). |
| Interview.tsx | Interview | useAnalysisContext, useUsage, useInterview | generateInterviewPrep | interview_questions_regenerated, interview_questions_cached_served |
| LandingPage.tsx | LandingPage | useAuth, usePricing | — | landing_page_viewed, cta_clicked |
| LoginPage.tsx | LoginPage | useAuth | signIn | — |
| MissionMode.tsx | MissionMode | useMission, useGamification | — | mission_created, mission_day_completed, mission_completed |
| Onboarding.tsx | Onboarding | useAnalysisContext | fetchOnboardingRecommendations | onboarding_started, onboarding_completed, gap_card_clicked |
| PersonaPicker.tsx | PersonaPicker | useAuth | updatePersona | persona_picker_shown, persona_selected |
| Pricing.tsx | Pricing | useUsage, usePricing, useSearchParams | createCheckoutSession | checkout_started, payment_completed |
| Profile.tsx | Profile | useAuth *(destructures `signOut`)*, useUsage, useGamification | generateExperience, createBillingPortalSession, api.get, `signOut` *(via `useAuth`; B-028)* | profile_viewed, subscription_portal_opened, experience_generated, `sign_out_clicked {source: 'profile_page'}` *(B-028, 2026-04-23 — fires before `signOut()` because `signOut` redirects to `/`)*. New `<section data-testid="account-section">` near bottom of layout exposes a "Sign out" button for mobile users reaching via MobileNav → Profile. |
| Results.tsx | Results | useAnalysisContext, useUsage | fetchOnboardingRecommendations | job_fit_explanation_viewed, results_tooltip_opened *(via `PanelSection` child — 9-section enum)* |
| Rewrite.tsx | Rewrite | useAnalysisContext, useRewrite, useUsage | rewriteSection *(via `useRewrite.regenerateSection`)* | rewrite_requested, rewrite_section_regenerated *(fired from `useRewrite.ts`); BE also emits `rewrite_succeeded` / `rewrite_failed` with `strategy=chunked\|fallback_full`* |
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
| `RewriteResponse` | `{ header, sections, full_text, template_type }` | 6 *(post-B-001: `sections` now populated end-to-end; was always-empty pre-`167b70f`)* |
| `RewriteSectionResponse` | `{ section_id: string, section: RewriteSection }` *(in `services/api.ts`, not `types/index.ts` — per-section regen return shape)* | 1 |
| `CoverLetterResponse` | `{ date, greeting, signoff, signature, tone, full_text: string, recipient: {name, company: string}, body_paragraphs: string[] (len==3) }` *(post-B-002 spec #52 LD-2 structured shape; supersedes the pre-B-002 `{cover_letter, tone}` shape)* | 5 |
| `CoverLetterRecipient` | `{ name, company: string }` *(new in B-002 — recipient sub-shape of `CoverLetterResponse`)* | — |
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

High-signal output — all verified against the current working tree at `3cef6c3`.

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
4. ~~`AdminPanel` (`/admin`) has no route-level admin guard — just `ProtectedRoute` + `PersonaGate`. Is the in-component role check intentional, or should `/admin` gain an `<AdminGate>` wrapper for parity with the backend's `require_admin` dependency?~~ ✅ **RESOLVED by E-040** (`1148354`, spec #54) — `<AdminGate>` now wraps both `/admin` and `/admin/analytics`; non-admins see a 403 view and lazy chunks are not downloaded.
5. `study-engine.md` skill file is missing `description:` frontmatter — should I backfill it to match the style of the other 19 skills? (Would be a one-line edit.)
6. `ai_service.py` duplicates `gpt_service.py` verbatim and is consumed only by an enterprise-tier endpoint (`/api/v1/resume/{id}/optimize`). Is it safe to delete now, or do you want to wait on a production traffic check per `[S47-defer]`?
7. Legacy mounts `/api/analyze`, `/api/rewrite`, `/api/cover-letter`, `/api/interview-prep` — is there a known external caller relying on these paths, or are they purely FE-migration holdovers that can be dropped once the FE references are swept?

---

*End of snapshot.*
