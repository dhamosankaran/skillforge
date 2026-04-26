# CODE-REALITY — SkillForge / HirePort AI

> **Purpose:** frozen-in-time map of the codebase for off-disk advisors (chat-Claude) to draft accurate prompts. If the header sha below doesn't match `git rev-parse --short HEAD`, regenerate this file.
> **Read-only artifact.** Nothing here authorizes code changes.

---

## Section 1 — Repo metadata

| Field | Value |
|-------|-------|
| Commit sha (short) | `8a0402e` (HEAD after B-059 SHA backfill — daily-review pre-flight wall gate). Full regen this pass — all 13 sections refreshed. Prior regen content at `ce60ea6` was 28 commits stale (`git log ce60ea6..HEAD --oneline \| wc -l = 28`); chat-Claude attempted a targeted-regen first that R19-stopped on prompt-side staleness misreading (the prompt's premise of "4 slices since `ce60ea6`" missed B-051 / B-052+B-053 / E-023 spec / LD-001 amend / B-055 / d19103c env-config — 7+ code-touching slices were unreflected). Full regen escalation re-counts everything once. |
| Branch | `main` (52 commits ahead of `origin/main`; not yet pushed) |
| Generated | 2026-04-26 (full regen, all 13 sections). LD-1 from B-049: full regen, not targeted. LD-2: counts via filesystem enumeration (`find` / `wc`, not estimation). LD-3: ambiguous fields flagged "unknown — flag for next regen" rather than guessed. LD-5: section content replaced, not appended. |
| Backend model files | 19 (`app/models/*.py`, excl. `__init__`, `request_models`, `response_models`) — **unchanged since prior regen** (verified zero delta `git log ce60ea6..HEAD --stat -- hirelens-backend/app/models hirelens-backend/alembic`) |
| Backend service files | 31 functional top-level (in `app/services/`, excl. `__init__.py`) + 3 under `services/llm/` = 34 — **unchanged since prior regen** (B-051/B-059 modified existing files; no new service file added) |
| Backend router files | 18 v1 + 6 legacy = 24 — **unchanged since prior regen** |
| Backend endpoints (total) | 64 — **unchanged since prior regen**. B-059 (`20562ea`) extended `GET /api/v1/study/daily` response shape (added `daily_status: DailyStatus` field) but did NOT add a new route; spec #63 LD-A locked the read-side mirror onto the existing endpoint. (5 legacy `/api/*` paths each appear at both `/api/*` and `/api/v1/*` mount; the v1 mounts for `analyze`, `cover_letter`, `interview`, `rewrite` are **re-exports** of the legacy router objects.) |
| Alembic revisions | 25 (Head = `30bf39fa04f8`) — **unchanged since prior regen**. No new migrations in the 28-commit gap (B-051/B-052/B-053/B-055/B-057/B-059 are all FE/services/specs; only `d19103c` touched BE config and it has no DDL). |
| Frontend pages | 20 — **unchanged since prior regen** (no new page files; HomeDashboard / StudyDashboard / DailyReview / Results modified in-place per B-051 / B-052+B-053 / B-059 / B-055) |
| Frontend components | 67 (excl. `__tests__/*`) — **+2 since prior regen**: `home/widgets/StudyGapsPromptWidget.tsx` (B-051, `ecef895`), `study/DailyReviewWalledView.tsx` (B-059, `20562ea`). `find hirelens-frontend/src/components -name "*.tsx" -not -path "*/__tests__/*" \| wc -l` = 67. |
| Frontend utils (NEW) | `src/utils/wallCountdown.ts` (B-059, `20562ea`) — exports `formatResetsAt(resetsAtIso) → string` + `hoursUntil(resetsAtIso) → number`. Lifted from private `QuizPanel.tsx` so `DailyReviewWalledView` can render the same `Resets in Xh Ym` / `Resets at H:MM AM/PM` copy. Code-org move only; behavior byte-identical. |
| Shared TS types | `src/types/index.ts` (~400 lines, +`DailyStatus` interface and `DailyQueueResponse.daily_status?` optional field per B-059) + `src/types/homeState.ts` (28 lines, unchanged) |
| Skills (tracked) | 20 in `.agent/skills/*.md` — **unchanged since prior regen**. B-051 / B-052+B-053 / B-059 each appended in-place rows to `analytics.md` (`home_study_gaps_clicked`, `home_study_gaps_prompt_shown`, `study_dashboard_source_hint_shown`, plus `daily_card_wall_hit` payload extended with `surface` enum). |
| Skills (untracked, not committed) | 3 directory-style under `.agent/skills/` — `stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/` (each contains `SKILL.md` and optionally `references/`); not in git, source unknown — see §10 |
| Specs | 80 across 6 phases (phase-0=6, phase-1=13, phase-2=8, phase-3=11, phase-4=6, phase-5=36) — see §13. **+4 phase-5 specs since prior regen**: #27 (geo-pricing, `c16f544`), #61 (HomeDashboard composition, `1262c26`), #62 (StudyDashboard `?source` hint, `ffd66f7`), #63 (daily-review pre-flight, `42a236b`). Spec #50 amended in-place at `b8d0c8c` (LD-001 cap 15→10, no AC shape change). |
| Tests | BE **489** (was 472 at prior regen — `+17`: `+3` from `d19103c` env-tunable test_free_tier_limit_config.py, `+5` from B-051 / B-052+B-053 trail not BE-touching, `+9` from B-059 test_study_api.py::TestDailyStatusPreflight); FE **328** (was 280 — `+48`: `+23` B-051, `+5` B-052+B-053, `+3` B-055, `+7` B-057, `+10` B-059). Counts per close-lines; not re-run this slice (R14 exception (a), doc-only). |

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

**Relationships:** none declared. `admin_id` ON DELETE RESTRICT is a forensic guardrail — a user row with audit history cannot be deleted without first purging audit rows.

Purpose: append-only audit trail for every admin-scoped HTTP request. Written via `core.deps.audit_admin_request` (router-level dep on `/api/v1/admin/*`). Also written by `auth.py::_log_role_reconciliation` on admin role promote/demote events (spec #54 E-040). Spec: `docs/specs/phase-5/38-admin-analytics.md`.

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

Purpose: append-only log of user paywall dismissals. Consumed by `paywall_service` (see §4) to drive the per-trigger 3-attempt grace window. Win-back consumption is deferred (BACKLOG E-031). Spec: `docs/specs/phase-5/42-paywall-dismissal.md`.

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
| scan_id | String(36) | nullable, indexed |
| skills_matched | Text | nullable |
| skills_missing | Text | nullable |
| **interview_date** | **Date** | **nullable** *(NEW since prior regen — alembic `9543aa466524`, E-042-impl-BE; partial index `ix_tracker_apps_user_interview_date` on `(user_id, interview_date)`. Backfilled from `users.interview_target_date` via `eb59d4fc1f7e`. FE consumers pending — `home_state_service.get_next_interview` reads this; CountdownWidget + MissionDateGate still read `user.interview_target_date`)* |
| **analysis_payload** | **JSONB** | **nullable, deferred-load** *(NEW since prior regen — alembic `30bf39fa04f8`, B-035 / spec #59; persists the full `AnalysisResponse` JSON for `/prep/results?scan_id=...` hydration. Declared with `sqlalchemy.orm.deferred()` so `GET /tracker` list responses do not inflate. Read via `GET /api/v1/analyze/{scan_id}` 200/410/404 ownership-checked endpoint)* |
| created_at | DateTime | NOT NULL |

**No `jd_hash` column** (see §11 drift flag). **Relationships:** `user → User | None` (back_populates `tracker_applications`).

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
| interview_target_date | Date | nullable *(deprecation pending — E-042 moves the canonical target to `tracker_applications_v2.interview_date`; user-level field stays for read compat until FE migrates per E-042 Phase-6 cleanup)* |
| downgraded_at | DateTime(timezone=True) | nullable, default `None` (set by `customer.subscription.deleted` webhook per spec #42 LD-5; dormant until win-back slice E-031 activates) |
| home_first_visit_seen_at | DateTime(timezone=True) | nullable, default `None` (B-016; stamped on first `/home` load via idempotent `POST /api/v1/users/me/home-first-visit`; flips greeting copy "Welcome" → "Welcome back". B-027 patched the FE to snapshot on mount so in-mount stamp doesn't flip the rendered copy within a single session) |
| created_at | DateTime | NOT NULL |

**Relationships:** `subscription → Subscription` (uselist=False), `resumes → list[Resume]`, `usage_logs → list[UsageLog]`, `tracker_applications → list[TrackerApplicationModel]`.

> `UsageLimit` (plan × feature cap) is referenced in AGENTS.md but **no model file exists** on disk; see §11 drift #6.

---

## Section 3 — Backend routes

Both `/api/*` (legacy) and `/api/v1/*` (authoritative) are mounted in `app/main.py`. Router files define paths directly on decorators (no `APIRouter(prefix=...)`), so the full effective path is `prefix` + decorator path. The v1 mounts for `analyze`, `cover_letter`, `interview`, `rewrite` are **re-export shims** (`from app.api.routes.X import router`), so the same handler appears at both `/api/X` and `/api/v1/X` and any change to the legacy file changes both endpoints.

### Router-file summary

| Effective mount | File | Endpoints | Auth deps observed |
|-----------------|------|-----------|---------------------|
| `/api/analyze` | `app/api/routes/analyze.py` | 2 | `get_current_user_optional` *(new since prior regen: `GET /analyze/{scan_id}` for B-035 scan hydration)* |
| `/api/cover-letter` | `app/api/routes/cover_letter.py` | 1 | `get_current_user` *(spec #58 / B-033 — 402 on cap hit, `cover_letter_limit` trigger)* |
| `/api/interview-prep` | `app/api/routes/interview.py` | 1 | `get_current_user_optional` |
| `/api/rewrite` | `app/api/routes/rewrite.py` | 2 | `get_current_user` *(spec #58 / B-033 — shared `"rewrite"` bucket for `/rewrite` and `/rewrite/section`, `rewrite_limit` trigger)* |
| `/api/v1/onboarding` | `app/api/routes/onboarding.py` *(legacy folder, v1 mount)* | 2 | `get_current_user` |
| `/api/v1/payments` | `app/api/routes/payments.py` *(legacy folder, v1 mount)* | 7 | `get_current_user` (5), none (2) |
| `/api/v1/admin` | `app/api/v1/routes/admin.py` | 9 | `audit_admin_request` (router-level, chains `require_admin`) |
| `/api/v1/admin/analytics` | `app/api/v1/routes/admin_analytics.py` | 2 | `audit_admin_request` (router-level, chains `require_admin`) |
| `/api/v1/analyze` | `app/api/v1/routes/analyze.py` *(re-exports legacy)* | 2 | `get_current_user_optional` |
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
| `/api/v1/rewrite` | `app/api/v1/routes/rewrite.py` | 2 *(re-exports legacy)* | `get_current_user` *(spec #58)* |
| `/api/v1/study` | `app/api/v1/routes/study.py` | 4 | `get_current_user` (4) |
| `/api/v1/tracker` | `app/api/v1/routes/tracker.py` | 4 | `get_current_user` (4) |
| `/api/v1/users` | `app/api/v1/routes/users.py` | 2 | `get_current_user` (2) |

### Flat endpoint table

| Method | Path | Handler | Auth | Tags |
|--------|------|---------|------|------|
| POST | /api/analyze | analyze_resume | get_current_user_optional | Analysis *(spec #56, B-031 — 402 quota branch via `check_and_increment(..., "analyze", window="lifetime")` for authenticated free users; anonymous + Pro + Enterprise + admin bypass)* |
| GET | /api/analyze/{scan_id} | get_analysis_by_id | get_current_user | Analysis *(NEW since prior regen — B-035 / spec #59; ownership-checked, returns 200 / 410 (no payload) / 404 (not owner))* |
| POST | /api/cover-letter | generate_cover_letter | get_current_user | Cover Letter *(spec #58 / B-033 — 402 `free_tier_limit` / `cover_letter_limit` for free plan)* |
| POST | /api/interview-prep | generate_interview_prep | get_current_user_optional | Interview Prep |
| POST | /api/rewrite | rewrite_resume | get_current_user | Rewrite *(spec #58 / B-033 — 402 `free_tier_limit` / `rewrite_limit` with `attempted_action='full'` for free plan)* |
| POST | /api/rewrite/section | rewrite_section | get_current_user | Rewrite *(spec #51, B-001 impl + spec #58 / B-033 — shares `"rewrite"` bucket; 402 envelope `attempted_action='section'`)* |
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
| GET | /api/v1/admin/analytics/metrics | metrics_endpoint | audit_admin_request → require_admin | v1 Admin Analytics *(spec #38 E-018b)* |
| GET | /api/v1/admin/analytics/performance | performance_endpoint | audit_admin_request → require_admin | v1 Admin Analytics *(spec #38 E-018b)* |
| POST | /api/v1/analyze | analyze_resume | get_current_user_optional | v1 Analysis *(re-exports legacy)* |
| GET | /api/v1/analyze/{scan_id} | get_analysis_by_id | get_current_user | v1 Analysis *(re-exports legacy; B-035 / spec #59)* |
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
| POST | /api/v1/payments/paywall-dismiss | paywall_dismiss | get_current_user | v1 Payments *(spec #42, P5-S26b — fires `paywall_dismissed` PostHog on logged=true; LD-8 60s dedup)* |
| GET | /api/v1/payments/should-show-paywall | should_show_paywall | get_current_user | v1 Payments *(spec #42 + spec #56 LD-4 carve-out — `trigger='scan_limit'` always returns `{show: true, attempts_until_next: 0}` for free users)* |
| GET | /api/v1/payments/usage | get_usage | get_current_user | v1 Payments *(spec #56 / B-031 + spec #58 / B-033 — flat `{plan, is_admin, scans_{used,remaining,max}, rewrites_{used,remaining,max}, cover_letters_{used,remaining,max}}` with `-1` sentinel for unlimited)* |
| POST | /api/v1/payments/webhook | stripe_webhook | none | v1 Payments *(spec #43 idempotency; spec #42 — `customer.subscription.deleted` branch stamps `user.downgraded_at`)* |
| GET | /api/v1/progress/heatmap | get_heatmap | get_current_user | v1 Progress |
| GET | /api/v1/progress/radar | get_radar | get_current_user | v1 Progress |
| GET | /api/v1/resume/{resume_id} | get_resume | get_current_user | v1 Resume |
| GET | /api/v1/resume/{resume_id}/diff | get_resume_diff | get_current_user | v1 Resume |
| POST | /api/v1/resume/{resume_id}/optimize | optimize_resume | require_plan | v1 Resume |
| POST | /api/v1/resume/upload | upload_resume | get_current_user | v1 Resume |
| POST | /api/v1/rewrite | rewrite_resume | get_current_user | v1 Rewrite *(spec #58 / B-033 — shared `"rewrite"` bucket)* |
| POST | /api/v1/rewrite/section | rewrite_section | get_current_user | v1 Rewrite *(spec #51, B-001 + spec #58)* |
| GET | /api/v1/study/daily | get_daily_review | get_current_user | v1 Study *(spec #63 / B-059 — response shape extended with `daily_status: DailyStatus {cards_consumed, cards_limit, can_review, resets_at}`. Read-side mirror of the same Redis key `_check_daily_wall` writes on submit. Side-effect-free GET (no INCR), fail-open on Redis outage. Pro / Enterprise / admin → `cards_limit=-1, can_review=true`. `daily_status` is `Optional[DailyStatus]` — only populated when `user is not None`. No new route.)* |
| POST | /api/v1/study/experience | generate_experience | get_current_user | v1 Study |
| GET | /api/v1/study/progress | get_progress | get_current_user | v1 Study |
| POST | /api/v1/study/review | submit_review | get_current_user | v1 Study *(spec #50, P5-S22-WALL-b — 402 `DailyReviewLimitError` for free users at daily cap)* |
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
| ai_service.py | AI service — LLM-powered resume optimization. **Duplicates `gpt_service.py`** (see `[S47-defer]` and §9). Only consumed by `/api/v1/resume/{id}/optimize` enterprise path. | generate_job_fit_explanation, generate_resume_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt | LLM-router |
| bullet_analyzer.py | Bullet point analyzer and strength scorer. | score_bullet, identify_issues, rewrite_bullet_locally, analyze_bullets | — |
| card_admin_service.py | Admin card CRUD — create, update, delete, list, bulk import. | create_card, update_card, delete_card, list_cards, bulk_import_csv | — |
| admin_analytics_service.py | Admin analytics aggregations (spec #38 E-018b). Six-OKR metrics with 7d/30d deltas; performance snapshot with LLM spend estimate (Postgres `usage_logs.tokens_consumed` × `llm_router.TIER_PRICE_USD_PER_1M_TOKENS`) and Stripe webhook success rate. `api_latency` + `error_rate_24h_pct` are deferred placeholders. Redis-cached 5 min with graceful degradation. | get_metrics_summary, get_performance_summary, CACHE_TTL_SECONDS | Redis |
| card_service.py | Card and category read service with plan-gated access. | list_categories, get_cards_by_category, get_card, search_cards | LLM-direct |
| email_service.py | Thin wrapper around the Resend API for transactional email with retry logic. | send_email, EmailSendError | Resend |
| experience_service.py | AI experience generator — turns study history into resume-ready narratives. | generate_experience | LLM-router |
| formatter_check.py | ATS formatting compliance checker for resume documents. | check_formatting | — |
| gamification_service.py | XP, streaks, and badges. | update_streak, reset_streak_if_missed, award_xp, get_stats, BadgeDef, InvalidXPSourceError, StatsView | — |
| gap_detector.py | Skill gap detection. | detect_gaps, classify_importance, get_skills_overlap_data | — |
| gap_mapping_service.py | ATS gap → card category mapping. | map_gaps_to_categories, RecommendedCategory, GapMapping | LLM-direct |
| geo_pricing_service.py | Geo-based pricing showing USD by default, INR for India. | get_pricing | HTTP-external, Redis |
| gpt_service.py | AI resume-optimization features delegating to multi-model LLM router. Post-B-001 (`167b70f`, spec #51): `generate_resume_rewrite` returns `Tuple[RewriteResponse, path_str]` where `path_str ∈ {"chunked", "fallback_full"}` (D-014). Per-section regen via `generate_section_rewrite`. `RewriteError` on truncation / malformed JSON. Chunking uses asyncio semaphore `PARALLEL_SECTION_LIMIT=4`. Post-B-002 (`825eb0e`, spec #52): `generate_cover_letter` returns structured `CoverLetterResponse`; `full_text` assembled server-side via `_join_cover_letter`. `body_paragraphs` Pydantic-pinned to `len==3`. Post-B-014 (`067c232`): `SECTION_MAX_TOKENS=4000` + `SECTION_THINKING_BUDGET=800`. Post-B-022 (`fa1871e`): `generate_job_fit_explanation` routed through reasoning tier (`JOB_FIT_MAX_TOKENS=3500`, `JOB_FIT_THINKING_BUDGET=800`). Post-B-023 (`79f76b4`): `_extract_candidate_name` rejects pure-uppercase lines. | generate_job_fit_explanation, generate_resume_rewrite, generate_resume_rewrite_async, generate_section_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt, RewriteError, _join_cover_letter, _extract_candidate_name, SECTION_MAX_TOKENS, SECTION_THINKING_BUDGET, JOB_FIT_MAX_TOKENS, JOB_FIT_THINKING_BUDGET | LLM-router |
| home_state_service.py | State-aware home dashboard evaluator. Post-E-042-impl-BE: `get_next_interview` reads `tracker_applications_v2.interview_date` (nearest upcoming, partial-index-served); tracker route writers call `home_state_service.invalidate` to bust the Redis cache. | evaluate_state, get_next_interview, invalidate | Redis |
| interview_storage_service.py | Interview question set storage + cache-aware generation. | generate_or_get_interview_set, InterviewGenerationResult | LLM-router |
| keywords.py | TF-IDF keyword extraction and matching. | extract_keywords, match_keywords, get_keyword_chart_data | — |
| mission_service.py | Mission Mode — time-bound study sprints with FSRS-prioritised cards. | create_mission, get_active_mission, get_mission_daily_cards, complete_mission_day, MissionNotFoundError, MissionConflictError, MissionInvalidError, MissionGoneError | — |
| nlp.py | NLP pipeline using spaCy. Post-B-021 (`e7c6d73`) + B-024 (`50e3c3c`): `_extract_company_name` is a three-layer orchestrator — LLM primary (`company_name_extraction` FAST task, null-on-unclear), regex fallback on LLM infra failure, deny-list + 100-char cap. `extract_job_requirements` returns `company_name: str \| None`. | get_nlp, extract_entities, extract_skills, extract_job_requirements, calculate_similarity, _extract_company_name, _extract_company_name_regex | LLM-router |
| onboarding_checklist_service.py | Interview-Prepper onboarding checklist from telemetry-derived state. | get_checklist, WrongPersonaError | — |
| parser.py | Resume parser supporting PDF and DOCX. | parse_pdf, parse_docx, detect_sections, extract_bullets, extract_contact_info | — |
| payment_service.py | Thin wrapper around Stripe. `_handle_subscription_deleted` writes `user.downgraded_at` per spec #42 LD-5. | create_checkout_session, create_billing_portal_session, handle_webhook, PaymentError, InvalidSignatureError, UserNotFoundError, NotProSubscriberError | Stripe |
| paywall_service.py | Paywall dismissal service (spec #42). `record_dismissal` with LD-8 60s idempotency per (user_id, trigger); `should_show_paywall` with Pro/admin bypass + Strategy A grace counter. Hard-wall carve-outs (amend spec #42 LD-1): trigger set is `{scan_limit, rewrite_limit, cover_letter_limit}` — for any of those three on a free user, always returns `{show: True, attempts_until_next: 0}`. Win-back send DEFERRED to E-031. | record_dismissal, should_show_paywall, RecordDismissalResult, ShouldShowPaywallResult, GRACE_ATTEMPTS, IDEMPOTENCY_WINDOW_SECONDS | — |
| progress_service.py | Progress analytics with category radar and activity heatmap. | get_category_coverage, get_activity_heatmap | — |
| reminder_service.py | Daily email reminder service. | get_users_needing_reminder, build_email_body, build_subject, send_daily_reminders | Resend |
| resume_templates.py | Resume template definitions for AI rewriting. | get_template, get_template_names, auto_select_template | — |
| scorer.py | ATS scoring engine. | ATSScorer | — |
| study_service.py | FSRS spaced-repetition study service. Enforces free-tier daily-card review wall (spec #50) via `_check_daily_wall` — Redis INCR keyed `daily_cards:{user_id}:{YYYY-MM-DD}` in user-local tz, 48h TTL, fail-open on Redis outage; admin + Pro/Enterprise bypass. Post-`d19103c`: `_check_daily_wall` replaces the prior `_DAILY_CARD_LIMIT` module constant with a function-local `get_settings().free_daily_review_limit` read so monkeypatched env vars propagate live. Post-B-059 (`20562ea`, spec #63): new `_compute_daily_status(user, db) → DailyStatus` helper performs side-effect-free Redis GET (no INCR) for the pre-flight gate read; `get_daily_review` signature gained kw-only `user: User \| None = None` (default keeps the 6 pre-existing test callers green) and the response now includes `daily_status` when `user is not None`. | get_daily_review, create_progress, review_card, get_progress, _compute_daily_status, CardNotFoundError, CardForbiddenError, DailyReviewLimitError | Redis |
| tracker_service_v2.py | SQLAlchemy-backed job application tracker. `create_application` accepts optional `analysis_payload: dict` kwarg (B-035 / spec #59). | create_application, find_by_scan_id, get_applications, get_application_by_id, update_application, delete_application | — |
| usage_service.py | Usage tracking + plan-limit enforcement. Per spec #56 / B-031: `PLAN_LIMITS["free"]["analyze"] = 1` (lifetime). `check_and_increment` accepts `window: Literal["monthly","lifetime"] = "monthly"` — analyze + rewrite + cover_letter pass `"lifetime"`. Admin bypass via in-helper User role fetch; short-circuits `allowed=True, limit=-1`. Per spec #58 / B-033: `get_analyze_usage` replaced by `get_usage_snapshot` (back-compat alias). New `_counter_triple(used, max, is_admin)` helper centralizes `-1` sentinel. `/rewrite` + `/rewrite/section` share `"rewrite"` feature key (spec #58 §4.1 Option a). Post-`d19103c` (env-tunable testing affordance): `PLAN_LIMITS` dict seeded from `get_settings()` at import; new `_plan_limits(plan)` helper re-reads the two free-cell entries (`analyze`/`lifetime`, `interview_prep`/`monthly`) live so test monkeypatching of settings propagates without rebuilding the dict. Pro/Enterprise rows stay literal. | log_usage, check_usage_limit, check_and_increment, get_usage_summary, get_usage_snapshot, get_analyze_usage (alias), _counter_triple, _plan_limits, PLAN_LIMITS, Window | — |
| user_service.py | User CRUD + admin-role reconciliation. Post-E-040: `reconcile_admin_role(user, admin_emails_set) -> (action, prior_role, new_role)` is a pure mutation. Action ∈ `{"promoted", "demoted", "unchanged"}`. Invoked from `auth.py::google_auth` on every login. | get_or_create_user, get_user_by_id, reconcile_admin_role | — |

### `app/services/llm/` (legacy provider factory — do not extend)

| File | Purpose | Public names | External deps |
|------|---------|--------------|---------------|
| factory.py | LLM provider factory. *(Legacy; Phase-6 cleanup target per Tech Debt.)* | get_llm_provider | — |
| claude_provider.py | Claude LLM provider — wraps Anthropic SDK. | ClaudeProvider | LLM-direct |
| gemini_provider.py | Gemini LLM provider — wraps Google Generative AI SDK. | GeminiProvider | LLM-direct |

---

## Section 5 — Alembic revisions

| # | Short revision | Description | down_revision |
|---|----------------|-------------|---------------|
| 1 | 0001_pg_init | initial postgres schema with pgvector | None |
| 2 | ed902312e4ac | add role column to users | 0001_pg_init |
| 3 | 9bb18657d55d | add cards and categories tables | ed902312e4ac |
| 4 | 638a23f7c9ed | add card_progress table | 9bb18657d55d |
| 5 | fdc5af6f825f | add fsrs_step to card_progress | 638a23f7c9ed |
| 6 | 802d5ba2e219 | add gamification tables | fdc5af6f825f |
| 7 | c9863b51075d | add email_preferences table | 802d5ba2e219 |
| 8 | b1674f79f780 | add cards.deleted_at for soft delete | c9863b51075d |
| 9 | d3a7e2f91c04 | add persona and onboarding_completed to users | b1674f79f780 |
| 10 | e5b2c8d4a1f7 | add card_feedback table | d3a7e2f91c04 |
| 11 | 83a02cb65464 | add stripe_events table for webhook idempotency | e5b2c8d4a1f7 |
| 12 | a4f1d8e73b92 | add missions and mission_days tables | 83a02cb65464 |
| 13 | 74a6fb27a181 | add target_company and target_date to users | a4f1d8e73b92 |
| 14 | f75789e4967f | add registration_logs table | 74a6fb27a181 |
| 15 | e4eab11b8e33 | add scan_id + skills_matched + skills_missing to tracker | f75789e4967f |
| 16 | d16ca29a5d08 | add categories.tags + cards partial index for active rows | e4eab11b8e33 |
| 17 | 59795ca196e9 | add IVFFlat ANN index on cards.embedding | d16ca29a5d08 |
| 18 | 02bf7265b387 | rename users target columns + migrate persona enum values | 59795ca196e9 |
| 19 | f3350dcba3a5 | add interview_question_sets table | 02bf7265b387 |
| 20 | 1176cc179bf0 | add paywall_dismissals and user.downgraded_at | f3350dcba3a5 |
| 21 | 508df0110037 | add users.home_first_visit_seen_at — B-016 | 1176cc179bf0 |
| 22 | 538fe233b639 | add admin_audit_log — E-018a | 508df0110037 |
| 23 | 9543aa466524 | add interview_date to tracker_applications_v2 + partial index — E-042-impl-BE | 538fe233b639 |
| 24 | eb59d4fc1f7e | backfill tracker.interview_date from users.interview_target_date | 9543aa466524 |
| 25 | 30bf39fa04f8 | add analysis_payload (JSONB, deferred) to tracker_applications_v2 — B-035 / spec #59 | eb59d4fc1f7e |

Head = `30bf39fa04f8`. **Delta since prior regen: +3 revisions** (rows 23-25).

---

## Section 6 — Frontend routes (live component graph)

Configured in `src/App.tsx`. Top-level wrappers: `<AppShell>` (always), `<ProtectedRoute>` (auth gate) which wraps `<PersonaGate>` (persona null → `/onboarding/persona`), `<Suspense>` for lazy pages.

| Path | Component | Layout wrapper | Auth / persona guard | Notes |
|------|-----------|----------------|----------------------|-------|
| `/` | `HomeRoute` → `LandingPage` (guest) / `<Navigate to="/home">` (auth) | AppShell (chromeless) | none | — |
| `/login` | `LoginPage` | AppShell (chromeless) | none | — |
| `/pricing` | `Pricing` | AppShell (chromeless for guest, **chrome for authed users**) | none | B-057 (`19326de`) — auth-aware carve-out; authed users hitting paywall flows (StudyDashboard quota → /pricing) keep nav so they can navigate away |
| `/home` | `HomeDashboard` | AppShell | ProtectedRoute → PersonaGate | — |
| `/onboarding` | `Onboarding` | AppShell | ProtectedRoute → PersonaGate | — |
| `/onboarding/persona` | `PersonaPicker` | AppShell (chromeless) | ProtectedRoute (PersonaGate allow-listed) | — |
| `/first-action` | `FirstAction` | AppShell (chromeless) | ProtectedRoute → PersonaGate | — |
| `/learn` | `StudyDashboard` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/daily` | `DailyReview` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/category/:id` | `CategoryDetail` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/card/:id` | `CardViewer` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/mission` | `MissionMode` (lazy) | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep` → `/prep/analyze` | `<Navigate replace>` | AppShell | ProtectedRoute | B-034 fix |
| `/prep/analyze` | `Analyze` | AppShell | ProtectedRoute → PersonaGate | spec #60 / B-045 — pre-flight scan-exhausted gate |
| `/prep/results` | `Results` | AppShell | ProtectedRoute → PersonaGate | B-035 / spec #59 — `?scan_id=` URL hydration |
| `/prep/rewrite` | `Rewrite` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/interview` | `Interview` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/tracker` | `Tracker` | AppShell | ProtectedRoute → PersonaGate | — |
| `/profile` | `Profile` (lazy) | AppShell | ProtectedRoute → PersonaGate | — |
| `/admin` | `AdminPanel` (lazy) | AppShell | ProtectedRoute → `AdminGate` | E-040 |
| `/admin/analytics` | `AdminAnalytics` (lazy) | AppShell | ProtectedRoute → `AdminGate` | spec #38 E-018b |
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

Nav chrome rendered by `AppShell` (`TopNav` desktop, `MobileNav` mobile). Chromeless-by-default paths in `AppShell.CHROMELESS_PATHS`: `/`, `/login`, `/onboarding/persona`, `/first-action`. **Auth-aware carve-out (B-057, `19326de`):** `/pricing` is chromeless when `user === null` (guest) but renders chrome when authed — implemented as `pathname === '/pricing' && user === null` in both `AppShell.tsx` (`useAuth()` import) and `MobileNav.tsx` (its own `HIDDEN_PATHS = ['/', '/login']` set + the same one-line carve-out for `/pricing`). The two carve-outs are duplicated rather than lifted to a shared module — see §11 drift item B-058.

**TopNav composition (desktop, `md:block`):** wordmark `SKILL/FORGE` → `/home`; nav links (`Home` / `Learn` / `Prep` / `Admin` if admin — `Profile` removed in B-029); right = `<UserMenu />` (avatar dropdown — Profile + `Sign out` button; B-028, B-029).

**MobileNav composition (`md:hidden`):** five-tab bottom bar (Home/Learn/Prep/Profile/Admin) — no sign-out surface; mobile users sign out via Profile → Account section.

**Wall-aware components (spec #50 + spec #63):** `src/components/study/QuizPanel.tsx` is the single submit chokepoint for `POST /api/v1/study/review` — consumed by `DailyReview`, `CardViewer`, `MissionMode`. On a 402 with `detail.trigger === 'daily_review'`, opens `PaywallModal trigger="daily_review"` and fires `daily_card_wall_hit { surface: "daily_review_submit" }`. **Pre-flight (B-059, `20562ea`):** `src/components/study/DailyReviewWalledView.tsx` renders full-page upsell on `/learn/daily` mount when `plan==='free' && !isAdmin && daily_status.can_review===false`; fires `daily_card_wall_hit { surface: "daily_review_page_load" }` once per mount via `useRef` guard. `formatResetsAt` / `hoursUntil` lifted from private `QuizPanel.tsx` to `src/utils/wallCountdown.ts` for reuse.

### Component graph (67 components, organized by directory)

| Directory | Components |
|-----------|-----------|
| `auth/` | AdminGate |
| `dashboard/` (Results page sub-components) | ATSScoreGauge, BulletAnalyzer, FormattingIssues, ImprovementSuggestions, JobFitExplanation, KeywordChart, MissingSkillsPanel, PanelSection, ScoreBreakdown, SkillOverlapChart |
| `home/` | DashboardWidget, InterviewDateModal *(B-037 — inline date editor)*, StateAwareWidgets *(B-051 — switched from internal `useHomeState` call to prop-driven, accepts `{persona, data, isLoading, error}` so HomeDashboard's single hook call feeds both this component and §3 composition-suppression flags)* |
| `home/widgets/` (15 widgets) | CountdownWidget *(B-051: gained `suppressedByMissionState` prop — suppressed when state slot fires AND `context.mission_target_date === user.interview_target_date`, per-mission carve-out per spec #61 §3.1)*, FirstSessionDoneWidget, InactiveReturnerWidget, InterviewPrepperChecklist, InterviewTargetWidget *(B-051: `suppressedByMissionState` prop — broader rule, suppressed whenever Mission state slot renders per LD-3)*, LastScanWidget *(B-051: `suppressed` prop — suppressed when StudyGapsPromptWidget eligibility resolves true; scan content rolled into the prompt body, audit #3)*, MissionActiveWidget *(B-051: gained Pro stale-scan footer per spec #61 §6)*, MissionOverdueWidget, ResumeStaleWidget *(B-051: free users now route to `setShowUpgradeModal` / PaywallModal instead of inline upgrade copy)*, StreakAtRiskWidget, StreakWidget, **StudyGapsPromptWidget** *(NEW — B-051, `ecef895`. Renders for `plan==='free' && !isAdmin && has_recent_scan && !has_active_mission`. Primary CTA `/learn?source=last_scan` (LD-1 LOCKED), secondary upgrade CTA opens PaywallModal `trigger='skill_gap_study'`. Fires `home_study_gaps_prompt_shown` on mount + `home_study_gaps_clicked {cta: 'primary'\|'secondary_upgrade'}` on click. Closes audit #3, #4, #5)*, TeamComingSoonWidget, TodaysReviewWidget, WeeklyProgressWidget |
| `layout/` | AppShell *(B-057: added `useAuth` import + `pathname === '/pricing' && user === null` guest-only carve-out alongside `CHROMELESS_PATHS = {'/', '/login', '/onboarding/persona', '/first-action'}`)*, MobileNav *(B-057: same one-line carve-out + `useAuth` import; `HIDDEN_PATHS = {'/', '/login'}`; the duplicated set is tracked at §11 drift item B-058)*, **Navbar** *(orphan; see §9)*, PageWrapper, TopNav, UserMenu |
| `mission/` | Countdown, DailyTarget, MissionDateGate, MissionSetup |
| `onboarding/` | **GuidedTour** *(orphan; see §9)* |
| `profile/` | StreakBadge, XPBar |
| `progress/` | ActivityHeatmap, SkillRadar |
| `rewrite/` | CoverLetterViewer, ResumeEditor, **ResumePDFTemplate** *(orphan; see §9)* |
| `settings/` | EmailPreferences, ThemePicker |
| `study/` | CategoryCard, **DailyReviewWalledView** *(NEW — B-059, `20562ea`. Full-page upsell rendered by `DailyReview.tsx` when free user is at cap. Props-only, no context deps. Locked headline "You've used today's free reviews" + countdown subhead via `formatResetsAt` + Upgrade-to-Pro CTA → `/pricing` (relies on B-057 chrome carve-out, AC-7) + Back-to-home CTA. Mirrors spec #60 / B-045 Analyze pre-flight pattern)*, FlipCard, QuizPanel *(B-059: submit-time `capture('daily_card_wall_hit')` payload now includes `surface: 'daily_review_submit'` per AC-6 regression-pin)*, WallInlineNudge |
| `tracker/` | ApplicationCard, KanbanBoard |
| `ui/` | AnimatedCard, GlowButton, ProgressBar, ScoreBadge, SkeletonLoader, Tooltip, UpgradeModal |
| `upload/` | JDInput, ResumeDropzone |
| `components/` (root) | PaywallModal, PersonaGate |

---

## Section 7 — Frontend pages

| File | Default export | Top-level data hooks | API calls | PostHog events |
|------|----------------|----------------------|-----------|----------------|
| AdminPanel.tsx | AdminPanel | — | fetchAdminCards, fetchCategories, createAdminCard, updateAdminCard, deleteAdminCard, generateCardDraft | — |
| AdminAnalytics.tsx | AdminAnalytics | useAuth | fetchAdminAnalyticsMetrics, fetchAdminAnalyticsPerformance | admin_analytics_segment_changed |
| Analyze.tsx | Analyze | useAnalysis, useUsage | — | paywall_hit *(spec #60 / B-045 — `{trigger: 'scan_limit', surface: 'analyze_page_load', plan: 'free'}` once-on-mount via `useRef` guard when `!canScan && plan==='free' && !isAdmin`)* |
| CardViewer.tsx | CardViewer | useCardViewer, useGamification | — | card_viewed |
| CategoryDetail.tsx | CategoryDetail | — | fetchCardsByCategory | category_detail_viewed |
| DailyReview.tsx | DailyReview | useGamification, useAuth, useUsage | fetchDailyQueue | daily_review_started, daily_review_completed, daily_card_wall_hit *(B-059 — fires once on walled mount via `useRef` guard with `surface: 'daily_review_page_load'`; only when `plan==='free' && !isAdmin && data.daily_status.can_review===false`)*. **Pre-flight gate (B-059, `20562ea`):** if free user is at cap, renders `<DailyReviewWalledView resetsAt={resetsAt} />` in place of queue. Imports `hoursUntil` from `@/utils/wallCountdown`. |
| FirstAction.tsx | FirstAction | useAuth | — | first_action_viewed, first_action_primary_clicked, first_action_secondary_clicked |
| HomeDashboard.tsx | HomeDashboard | useAuth, useUsage, useHomeState *(single call, B-051; was internal to StateAwareWidgets)* | markHomeFirstVisit *(B-016)*, fetchActiveMission, fetchUserApplications | home_dashboard_viewed. Greeting fork: `isFirstVisit` snapshotted on mount via `useState(() => user.home_first_visit_seen_at == null)` (B-027). **Composition refactor (B-051, `ecef895`, spec #61 §3):** single `useHomeState()` call resolves at the page level; derives `topState` + `missionStateActive` + `missionTargetMatchesUser`; passes three suppression flags down to `InterviewPrepperMode` (`countdownSuppressedByMissionState`, `interviewTargetSuppressedByMissionState`, `lastScanSuppressed`). State-slot data flows to `StateAwareWidgets` as a prop (no double-fetch). Free-tier `StudyGapsPromptWidget` mounts on `plan==='free' && !isAdmin` branches; its eligibility predicate (`has_recent_scan && !has_active_mission`) feeds back into `lastScanSuppressed`. CareerClimber + TeamLead modes preserved verbatim. |
| Interview.tsx | Interview | useAnalysisContext, useUsage, useInterview | generateInterviewPrep | interview_questions_regenerated, interview_questions_cached_served |
| LandingPage.tsx | LandingPage | useAuth, usePricing | — | landing_page_viewed, cta_clicked |
| LoginPage.tsx | LoginPage | useAuth | signIn | — |
| MissionMode.tsx | MissionMode | useMission, useGamification | — | mission_created, mission_day_completed, mission_completed |
| Onboarding.tsx | Onboarding | useAnalysisContext | fetchOnboardingRecommendations | onboarding_started, onboarding_completed, gap_card_clicked |
| PersonaPicker.tsx | PersonaPicker | useAuth | updatePersona | persona_picker_shown, persona_selected, interview_target_date_added *(B-018, B-037)* |
| Pricing.tsx | Pricing | useUsage, usePricing, useSearchParams | createCheckoutSession | checkout_started, payment_completed |
| Profile.tsx | Profile | useAuth (incl. signOut), useUsage, useGamification | generateExperience, createBillingPortalSession, api.get | profile_viewed, subscription_portal_opened, experience_generated, sign_out_clicked *(B-028 — `{source: 'profile_page'}`)* |
| Results.tsx | Results | useAnalysisContext, useUsage | fetchOnboardingRecommendations, fetchAnalysisById *(B-035 / spec #59 — URL `?scan_id=` hydration with three-way empty-state)* | job_fit_explanation_viewed, results_tooltip_opened *(via `PanelSection`, 9-section enum)*, scan_rehydrated *(B-035)*. **Layout fix (B-055, `4b7f862`):** added `xl:row-end-5` to `ImprovementSuggestions` grid item (line 482) to distribute its height across rows 3–4 of col-3 instead of inflating row-3 alone. Closes the xl-breakpoint vertical void below Skills Radar / Jump-nav. DOM, ordering test invariants, 9 section IDs, and verbatim spec #21 tooltip copy all unchanged. |
| Rewrite.tsx | Rewrite | useAnalysisContext, useRewrite, useUsage | rewriteSection *(via `useRewrite.regenerateSection`)* | rewrite_requested, rewrite_section_regenerated. BE also emits `rewrite_succeeded` / `rewrite_failed` with `strategy=chunked\|fallback_full`. |
| StudyDashboard.tsx | StudyDashboard | useStudyDashboard, useAuth, useUsage, useGamification, useSearchParams | — | study_dashboard_viewed, locked_tile_clicked, category_tile_clicked, **study_dashboard_source_hint_shown** *(NEW — B-052/B-053, `df035e1`. `{source: 'last_scan', persona, copy_variant: '6A'}` — fires once per mount via `useRef` idempotency when URL has `?source=last_scan`. Param is attribution-only — does NOT filter the category grid; only renders a `motion.div` hero hint between header and "Your Goal" card with a dismiss × button. Component-state dismissal (no sessionStorage). URL preserved (no `setSearchParams`). Locked variant `'6A'` neutral copy per spec #62 §10 OQ-1.)* |
| Tracker.tsx | Tracker | useTracker | — | — |

---

## Section 8 — Frontend shared types

`src/types/index.ts` (391 lines, authoritative for API DTOs) + `src/types/homeState.ts` (28 lines, home dashboard only).

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
| `CoverLetterRecipient` | `{ name, company: string }` | — |
| `CoverLetterResponse` | `{ date, greeting, signoff, signature, tone, full_text: string, recipient: CoverLetterRecipient, body_paragraphs: string[] (len==3) }` | 5 |
| `InterviewQuestion` | `{ question: string, star_framework: string }` | 1 |
| `InterviewPrepResponse` | `{ questions: InterviewQuestion[], cached?, generated_at?, model_used? }` | 3 |
| `ApplicationStatus` | `Applied\|Interview\|Offer\|Rejected` | — |
| `TrackerApplication` | `{ id, company, role, date_applied, status, ats_score, scan_id?, skills_matched?[], skills_missing?[], created_at }` | 6 |
| `Category` | `{ id, name, icon, color, display_order, source: foundation\|premium, card_count, studied_count, locked }` | 16 |
| `Card` | `{ id, category_id, category_name, question, answer, difficulty, tags[], created_at, updated_at }` | 28 |
| `FsrsRating` | `1\|2\|3\|4` | — |
| `ReviewRequest` | `{ card_id, session_id: string, rating: FsrsRating, time_spent_ms? }` | — |
| `ReviewResponse` | `{ card_id, fsrs_state, due_date, stability, difficulty, reps, lapses, scheduled_days }` | — |
| `DailyCard` | `{ card_id, question, answer, category_id, category_name, difficulty, tags[], fsrs_state, due_date, reps, lapses }` | 3 |
| `DailyStatus` *(NEW — B-059)* | `{ cards_consumed: number, cards_limit: number, can_review: boolean, resets_at: string }` — read-side mirror of free-tier daily-card wall counter. `cards_limit === -1` is the unlimited sentinel for Pro / Enterprise / admin (matches `usage_service` / `UsageContext` `-1` convention). FE-canonical name; BE-canonical is `app/schemas/study.py::DailyStatus`. | 1 |
| `DailyQueueResponse` *(B-059 — additive)* | `{ cards: DailyCard[], total_due: number, session_id: string, daily_status?: DailyStatus }` — `daily_status` is optional (only populated by `GET /api/v1/study/daily` when authed; `null`/`undefined` for legacy callers and unauthed paths). | — |
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

> **§13 cross-ref:** `UsageContext` shape (FE state, not API DTO) — `scansRemaining` field DEFERRED per B-047 (gated on pre-existing `UsageContext.tsx` working-tree dirt resolution).

---

## Section 9 — Known-dead or transitional code

| Path | Why flagged | Suggested action |
|------|-------------|------------------|
| `hirelens-frontend/src/components/layout/Navbar.tsx` | `AppShell` only imports `TopNav`/`MobileNav`; no file imports `Navbar`. SESSION-STATE lists as Phase-6 cleanup (B-010). | delete |
| `hirelens-frontend/src/components/onboarding/GuidedTour.tsx` | Only self-reference; no page or component imports it. | delete (or migrate if there's design intent — see §12 Q1) |
| `hirelens-frontend/src/components/rewrite/ResumePDFTemplate.tsx` | Only self-reference. PDF export is generated inline via jsPDF in `Rewrite.tsx`. | delete (see §12 Q2) |
| `hirelens-backend/app/services/ai_service.py` | Duplicates `gpt_service.py` public API verbatim. Only consumed by the enterprise-only `/api/v1/resume/{id}/optimize` path. `[S47-defer]` in SESSION-STATE Deferred Hygiene flags it pending traffic check. | leave (tracked) |
| `hirelens-backend/app/services/llm/` directory (factory.py + claude_provider.py + gemini_provider.py) | Legacy provider abstraction parallel to `app/core/llm_router.py`. Phase-6 consolidation in Tech Debt. May still be imported by a non-router-aware path. | leave (Phase-6) |

No components found behind a `{false && …}` guard or dormant feature flag. Verified against current HEAD.

---

## Section 10 — Skills inventory

### Tracked skills (`.agent/skills/*.md`, 20 files)

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
| study-engine.md | **(frontmatter has no `description:` field — see §11 drift #8; tracked at B-039 audit doc `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md`)** |
| testing.md | Test patterns, fixtures, mocks for SkillForge |

### Untracked skill surfaces (NEW — surfaced this regen via filesystem audit)

Three directory-style skills are **on disk but not tracked in git** (each shows as `??` in `git status`). Source/intent unknown — appeared 2026-04-21 per filesystem mtime, not authored via any documented slice. All three contain a `SKILL.md` file and (in one case) a `references/` subdirectory:

| Path | Files | Status |
|------|-------|--------|
| `.agent/skills/stripe-best-practices/SKILL.md` | + `references/` (6 entries) | UNTRACKED — not in git |
| `.agent/skills/stripe-projects/SKILL.md` | (single file) | UNTRACKED — not in git |
| `.agent/skills/upgrade-stripe/SKILL.md` | (single file) | UNTRACKED — not in git |

Action needed (see §12 NEW Q8): decide whether to (a) commit them as legitimate skills, (b) add to `.gitignore` as out-of-scope external resources, or (c) delete. The `SKILL.md` filename pattern (uppercase) is not the canonical SkillForge convention (lowercase slug) — suggests external provenance.

Skill discovery tooling that walks `.agent/skills/*.md` will **miss** these (they're under sub-directories, not top-level `.md` files). So they are also non-discoverable via the documented Skill loader pattern.

---

## Section 11 — Drift flags (AGENTS.md / master-doc vs code)

High-signal output — all verified against HEAD `8a0402e`. **Reconciled against post-B-048 SOP state:** R3 = "Never skip auth" (auth only); R19 = push-back; R18 retired (merged into R15(c)); SOP-8 = concurrent-session detection (codified `2504d6b`); SOP-9 = no concurrent CC sessions on one tree (added by B-048, `e2714b4`); H1–H4 = chat-Claude ↔ CC handoff section (added by B-048).

1. **AGENTS.md legacy routers table says `/api/cover_letter` (underscore).** `app/api/routes/cover_letter.py:11` decorates `@router.post("/cover-letter", …)` (hyphen). Effective path is `/api/cover-letter`. Same drift: `/api/interview` vs actual `/api/interview-prep`. **Status: still drifted.**

2. **AGENTS.md legacy routers table lists `/api/v1/onboarding` and `/api/v1/payments` as v1 routers, but the files live in the legacy folder.** `from app.api.routes import onboarding, payments` + `include_router(... prefix="/api/v1")` at `app/main.py:147-148`. Files sit in `app/api/routes/` not `app/api/v1/routes/`. **Status: still drifted.**

3. **AGENTS.md Models table User row still lists `target_company`, `target_date`** (line 270). On disk: `interview_target_company` (String(100)) and `interview_target_date` (Date). Migration `02bf7265b387` did the rename. SESSION-STATE Deferred Hygiene S16 retrofit. **Status: still drifted; bumped urgency by E-042 — `interview_target_date` is now also being deprecated in favor of `tracker_applications_v2.interview_date`, so the AGENTS.md row will need a second update once E-042 FE ships.**

4. **AGENTS.md Routes table references `/api/v1/mission` (singular)** (line 213). Actual mount prefix `/api/v1` + decorators `/missions/create`, `/missions/active`, `/missions/daily`, `/missions/complete-day` — plural. Captured as `[S35-flag]`. **Status: still drifted.**

5. **AGENTS.md says `Category` has a `source` column.** True, but it also has a `tags` JSONB column (migration `d16ca29a5d08`). AGENTS.md does not mention `categories.tags`. **Status: still drifted.**

6. **AGENTS.md Models table references `UsageLimit`** (line 276). No `UsageLimit` model file on disk. Usage limits are enforced in `usage_service.py::PLAN_LIMITS` dict logic, not a DB table. **Status: still drifted (phantom).**

7. **Email-preferences route path mismatch.** `app/api/v1/routes/email_prefs.py` uses `/email-preferences`; FE `services/api.ts` calls `/api/v1/email-preferences`. AGENTS.md table line 212 shows `/api/v1/email-prefs`. **Status: still drifted.**

8. **`study-engine.md` skill file has no `description:` frontmatter.** Other 19 skill files have one. Captured in `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md` as critical fix. **Status: still drifted.**

9. **Tracker auto-save JD dedupe documented as locked but not implemented.** `tracker_applications_v2` has no `jd_hash` column (§2 verified); `tracker_service_v2.py` does not import `hash_jd`; `app/utils/text_hash.py::hash_jd` exists but only `interview_storage_service.py` consumes it. Captured as `[5.17-follow] tracker jd_hash dedupe`. **Status: still drifted.**

10. **Four legacy `/api/*` routers still mounted alongside v1 counterparts.** `analyze`, `rewrite`, `cover_letter`, `interview` in `app/main.py:121-124`. The v1 equivalents are *re-exports* of the legacy router objects (see §3), so deprecating the legacy mount requires moving the handlers first. **Status: still drifted.**

11. **NEW post-B-048 — AGENTS.md and skills do not reference R19 / SOP-8 / SOP-9 / H1–H4.** AGENTS.md was not swept during B-048. If AGENTS.md contains references to the retired R18 or the second R3, those are stale; but a quick grep shows AGENTS.md does not currently cite these rule numbers, so this is a "no-stale-citations" finding rather than a drift to fix. **Status: confirmed clean — AGENTS.md is rule-citation-free.**

12. **NEW — three untracked skill directories** (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`) under `.agent/skills/`. See §10 for filesystem detail and §12 NEW Q8. **Status: NEW this regen — surfaced via filesystem walk.**

13. **NEW — N1-SUPPLEMENT → N9 promotion deferred** (per B-048 close-line). 6 callsites flagged in SESSION-STATE Deferred Hygiene Items; will need a sweep slice. **Status: NEW; tracked.**

14. **NEW — spec section header rename `## 12. R15` / `## 13. R15` across 5 spec files** deferred per B-048. TOC anchors; rename silently breaks external cross-refs if any. **Status: NEW; tracked in SESSION-STATE Deferred Hygiene.**

15. **Pre-existing dirty files (long-standing):** `Enhancements.txt`, `hirelens-backend/scripts/wipe_local_user_data.py`, `../.DS_Store`. None bundled into commits per C2/C5. Plus untracked items: `docs/audits/`, `docs/status/E2E-READINESS-2026-04-21.md`, `skills-lock.json`, `.gitattributes`, `.agent/skills/{stripe-*,upgrade-stripe}/`. **Status: long-standing; not blocking.**

16. **NEW (B-058) — duplicated chromeless-paths sets across `AppShell.tsx` + `MobileNav.tsx`.** B-057 (`19326de`) carved out `/pricing` chrome behavior in two places — `AppShell.CHROMELESS_PATHS = {'/', '/login', '/onboarding/persona', '/first-action'}` plus `pathname === '/pricing' && user === null` guest-only carve-out, and `MobileNav.HIDDEN_PATHS = {'/', '/login'}` plus the same one-line `/pricing` guest carve-out. The `MobileNav` set is intentionally narrower (no onboarding/first-action — bottom-bar is not mounted there anyway), but the `/pricing` rule is duplicated. Drift risk: any future change to chromeless-paths policy must be made in two places. **Tracked at BACKLOG B-058** (P3 nav cleanup) — close shape: lift to `src/components/layout/chromeless.ts` exporting `CHROMELESS_PATHS` + `MOBILE_HIDDEN_PATHS` + shared `isChromeless(pathname, user)` helper. **Status: NEW — surfaced via R19 push-back during B-057 impl.**

17. **NEW (`d19103c` + `b8d0c8c`) — three free-tier paywall env vars not yet reflected in AGENTS.md env-vars table.** `d19103c` plumbed: `Settings.free_daily_review_limit` (env `FREE_DAILY_REVIEW_LIMIT`), `Settings.free_lifetime_scan_limit` (default `1`, env `FREE_LIFETIME_SCAN_LIMIT`), `Settings.free_monthly_interview_limit` (default `3`, env `FREE_MONTHLY_INTERVIEW_LIMIT`). `b8d0c8c` (LD-001 cap tightening, Slice B) flipped `free_daily_review_limit` default from `15` → `10` so the in-code default now matches LD-001's amended cap. Flipping any of the three env vars locally hits the corresponding paywall in seconds without burning real quota. `payments.md` skill records the three under "Free Tier Limits" but `AGENTS.md` env-vars table (canonical source per its own header) does not. **Status: NEW — drift only on the AGENTS.md doc surface; no code drift.**

---

## Section 12 — Open questions for Dhamo

1. `components/onboarding/GuidedTour.tsx` has zero imports. Is this (A) dead code safe to delete, or (B) a scaffold you're saving for a future onboarding tour spec? *(carried from prior regen)*
2. `components/rewrite/ResumePDFTemplate.tsx` has zero imports and PDF generation is inline in `Rewrite.tsx`. Delete in next cleanup slice — yes/no? *(carried from prior regen)*
3. Is `UsageLimit` supposed to exist as a DB-backed model, or is the AGENTS.md Models table row stale and should be removed? *(carried from prior regen)*
4. ~~`AdminPanel` (`/admin`) has no route-level admin guard~~ ✅ **RESOLVED by E-040** (`1148354`, spec #54) — `<AdminGate>` wraps both `/admin` and `/admin/analytics`; non-admins see a 403 view and lazy chunks are not downloaded. *(resolved prior regen — kept here for traceability; will drop after one more regen if no follow-up surfaces)*
5. `study-engine.md` skill file is missing `description:` frontmatter — backfill to match the other 19 skills? (One-line edit.) *(carried)*
6. `ai_service.py` duplicates `gpt_service.py` verbatim and is consumed only by an enterprise-tier endpoint (`/api/v1/resume/{id}/optimize`). Safe to delete now, or wait on production traffic check per `[S47-defer]`? *(carried)*
7. Legacy mounts `/api/analyze`, `/api/rewrite`, `/api/cover-letter`, `/api/interview-prep` — known external caller relying on these paths, or purely FE-migration holdovers that can be dropped once FE references are swept? *(carried)*
8. **NEW** — Three untracked skill directories appeared on 2026-04-21 (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`). Source/intent unknown. (a) Commit and treat as legit skills, (b) `.gitignore` as external resources, or (c) delete? Their `SKILL.md` (uppercase) filename does not match SkillForge convention (lowercase slug `name.md`).
9. **NEW** — E-042 deprecates `users.interview_target_company` and `users.interview_target_date` in favor of `tracker_applications_v2.interview_date` (BE shipped 2026-04-23 per `9543aa466524`/`eb59d4fc1f7e`). FE consumers (CountdownWidget, MissionDateGate) still read the user-level fields. Phase-6 cleanup intent confirmed, or accelerate to the next slice?

No status changes from prior regen besides the carry-forward of Q4 ✅. Nothing else flipped to resolved.

---

## Section 13 — Specs inventory

Walked `docs/specs/**/*.md` — **80 spec files across 6 phases** (+4 since prior regen content; all four in phase-5: #27 #61 #62 #63). Status field = `^## Status` line OR `^**Status:**` bolded line at the top of the spec body — both styles are observed on disk; tooling that grepped only `^## Status` would undercount by 3 (specs #61, #62 use the `**Status:**` bolded form). Specs without either form are flagged "no status".

### Per-phase counts
| Phase | Files | With explicit Status line | No status field |
|-------|-------|---------------------------|-----------------|
| phase-0 | 6 | 6 | 0 |
| phase-1 | 13 | 6 | 7 |
| phase-2 | 8 | 7 | 1 |
| phase-3 | 11 | 8 | 3 |
| phase-4 | 6 | 6 | 0 |
| phase-5 | 36 | 14 | 22 |
| **Total** | **80** | **47** | **33** |

**Phase-5 delta since prior regen**: +4 files (#27, #61, #62, #63), +3 with-status (#61 `**Status:**`, #62 `**Status:**`, #63 `## Status:`), +1 no-status (#27 — newly authored, no status header). Hygiene gap unchanged in phase-5: 22/36 specs lack a status line, mostly historical pre-spec-template files (status hygiene was not retroactively applied).

### Status legend (canonical strings observed on disk)
`Done` · `Complete` · `Implemented — Spec Backfill Pending (P5-S###)` · `Draft` · `Drafted, not shipped` · `Shipped (spec + impl)` · `Done — Shipped in <sha>` · `Partially Done` · `Planned — Known-Broken` · `Deferred` · `Complete — Spec Backfill Pending`

### phase-0 (Phase 0 / foundation)
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
| 03-card-extraction.md | Partially Done — gaps to close in P1-S1 |
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
| 20c-resume-cover-letter-fix.md | Planned — Known-Broken, awaiting P5-S9 + P5-S10 |
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
| 25a-custom-domain-golive.md | Complete — Spec Backfill Pending (P4-S4 retrospective) |

### phase-5 (most active phase)
| File | Status |
|------|--------|
| 01-admin-analytics-early-draft.md | Done |
| 09-resume-rewrite-fix.md | (no status field) |
| 10-cover-letter-format-fix.md | (no status field) |
| 11-generate-experience-fix.md | (no status field) |
| 12-navigation-restructure.md | (no status field) |
| 21-analysis-results-improvements.md | Done — Shipped in `1c0817a` (P5-S21b) on 2026-04-19 |
| 22-plan-aware-missing-skills-cta.md | Draft |
| 27-geo-pricing.md | (no status field — NEW since prior regen, authored `c16f544` / E-023; behavior contract + Gap B/D/E fix anchors) |
| 34-persona-picker-and-home.md | (no status field) |
| 35-home-dashboard-and-widgets.md | (no status field) |
| 36-subscription-cancellation.md | (no status field) |
| 38-admin-analytics.md | Draft |
| 40-home-dashboard-state-aware.md | (no status field — but see SESSION-STATE: P5-S18b retrofit flipped to "Done — Backfilled" by 2026-04-19 process note; spec body status field needs a second touch) |
| 41-interview-prepper-checklist.md | (no status field) |
| 42-paywall-dismissal.md | (no status field) |
| 43-stripe-webhook-idempotency.md | (no status field) |
| 44-home-widget-empty-states.md | (no status field) |
| 45-legacy-route-cleanup.md | (no status field) |
| 46-post-persona-first-action.md | (no status field) |
| 47-resume-rewrite-content-preservation.md | (no status field) |
| 48-doc-audit-pattern.md | (no status field) |
| 49-interview-question-storage.md | (no status field) |
| 50-free-tier-daily-card-wall.md | Draft *(amended `b8d0c8c` 2026-04-26 Slice B — LD-001 cap tightening 15→10. Spec body retained `## Status: Draft` with an in-place amendment block at line 13 documenting the cap flip; AC shapes / payload fields / behavior / edge cases UNCHANGED — only the integer literal moves. `daily_card_wall_hit` payload also extended additively by B-059 / `20562ea` with `surface` enum.)* |
| 51-ai-rewrite-section-preservation.md | (no status field — but B-001 closed `688529d` per BACKLOG; spec needs status line) |
| 52-cover-letter-format-enforcement.md | (no status field — but B-002 closed per BACKLOG; spec needs status line) |
| 53-interview-target-optional-fields.md | (no status field — but B-018 shipped `724e5cd`; spec needs status line) |
| 54-admin-email-whitelist.md | Draft |
| 55-reanalyse-paywall-gate.md | Draft |
| 56-free-tier-scan-lifetime-cap.md | Draft |
| 57-tracker-level-interview-date.md | (no status field — E-042 BE shipped 2026-04-23; FE pending; spec needs status line) |
| 58-legacy-rewrite-router-auth-quota.md | Shipped (spec + impl) — closes B-033. Impl half landed 2026-04-23. |
| 59-scan-persistence.md | Drafted, not shipped. *(actually shipped per BACKLOG B-035 closed `0b35440` on 2026-04-24 — spec status line needs update)* |
| 60-analyze-page-preflight-gate.md | (no status field — B-045 closed `3c962d8`; spec needs status line) |
| 61-home-dashboard-composition-rules.md | **Status:** Drafted, not shipped *(NEW — B-051 spec half `1262c26`. Impl shipped `ecef895` 2026-04-25 closing B-051 + E-048 — spec status line not flipped on impl-merge; matches pattern observed elsewhere in §13.)* |
| 62-study-dashboard-source-hint.md | **Status:** Drafted, not shipped *(NEW — B-052 spec half `ffd66f7`. Impl shipped `df035e1` 2026-04-26 closing B-052 + B-053 per spec §10 OQ-5 dual-tracking — spec status line not flipped on impl-merge.)* |
| 63-daily-review-preflight-gate.md | Draft *(NEW — B-059 spec half `42a236b`. Impl shipped `20562ea` 2026-04-26 closing B-059 — spec status line not flipped on impl-merge. Authoring note records the chat-Claude vs disk-reality drift on endpoint name (`/study/daily-queue` cited but disk is `/study/daily`) and `formatResetsAt` reuse claim (cited as importable but was private to QuizPanel — impl had to lift to `wallCountdown.ts`); R19 audit notes preserved in spec body.)* |

### Numbering anomalies / duplicates / gaps

- **phase-3 spec numbering:** `20-onboarding-polish.md`, `20b-design-system-themes.md`, `20c-resume-cover-letter-fix.md` — three specs sharing the `20*` slot via letter suffixes. Convention is consistent with phase-1 `11a/b/c/d`.
- **phase-4 numbering:** `22-error-monitoring.md` and `23-error-monitoring.md` — two specs with the SAME title "error-monitoring" at adjacent numbers. One marked Done, one Complete. Likely supersession or duplicate authoring; needs clarification.
- **phase-5 numbering gaps:** `01`, then `09–12`, then `21–22`, then `27`, then `34–63` (with remaining gaps at 23–26, 28–33, 37, 39). Many gaps suggest reserved-but-not-authored slots; only worth investigating if a citation references a missing number.
- **phase-5 number `1` reuse:** `01-admin-analytics-early-draft.md` (Done) is superseded by `38-admin-analytics.md` (Draft) per the same OKR surface. Consider archiving #01 or marking it `Superseded`.
- **Total spec status hygiene gap:** 33 of 80 specs (41%) have no Status line. Concentration in phase-1 (7), phase-3 (3), phase-5 (22). Recommend a one-slice sweep adding status lines to the phase-5 specs that have shipped (#51, #52, #53, #57, #59, #60, #61, #62, #63 are all known-shipped per BACKLOG yet 6 of those 9 have no/unflipped Status line), dropping the bookkeeping burden of stale Drafts.
- **Spec-body Status format inconsistency:** `## Status:` (heading-2) vs `**Status:**` (bolded paragraph) appear interchangeably; tooling that greps only one form will miscount. Standardize on the heading-2 form to align with template (spec #50, #63 use it; #61, #62 use the bolded form).

---

*End of snapshot. Generated 2026-04-26 at HEAD `8a0402e` — full regen escalated from a targeted-regen attempt that R19-stopped on prompt-side staleness misreading (chat-Claude treated `ce60ea6` as the regen-commit baseline; on disk it is the SHA the regen content **referenced**, with the regen commit itself one parent later at `3f43927`, so 28 commits had landed since). Next regen recommended after E-042 FE ships (will move tracker columns to authoritative read source) or after the next batch of phase-5 specs flip Done.*
