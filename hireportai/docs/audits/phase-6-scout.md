# Phase 6 Scout Audit

**HEAD SHA at audit time:** `83dd03b` (post-B-060 SHA backfill — full CODE-REALITY regen at `8a0402e`)
**Generated:** 2026-04-26 22:29 UTC
**Working tree at audit time:** clean except long-standing pre-existing dirty
files (`../.DS_Store`, `Enhancements.txt`,
`hirelens-backend/scripts/wipe_local_user_data.py`) and untracked items
(`docs/audits/`, `docs/status/E2E-READINESS-2026-04-21.md`,
`skills-lock.json`, `.gitattributes`, `.agent/skills/{stripe-best-practices,
stripe-projects, upgrade-stripe}/`).
**Mode:** audit-only (no code changes, no spec authoring, no schema migrations,
no BACKLOG row creation).

> **R17 watermark check (slice-start):** highest in-use BACKLOG ID on disk is
> `B-060` (per `grep -oE "B-0[0-9]+" BACKLOG.md | sort -u | tail -1`). The
> prompt cited B-052 from memory; surfaced as memory-vs-disk drift but
> immaterial here because this slice does not file a new BACKLOG row.

> **`docs/specs/phase-6/` does NOT exist on disk.** `ls docs/specs/` returns
> `phase-0..phase-5` only. Logged as Recommendation R-1 below; do not create
> in this slice.

---

## Section 1 — Existing study engine

### 1.1 Card / category / FSRS data model (BE)

| Table | File | Columns of interest |
|-------|------|---------------------|
| `categories` | `app/models/category.py` | `id` UUID PK, `name` unique, `icon`, `color`, `display_order`, `source` (`foundation` / `premium` — drives free-tier gate), `tags` JSONB (powers ATS-gap → category mapping). |
| `cards` | `app/models/card.py` | `id` UUID PK, `category_id` FK, `question` Text, `answer` Text, `difficulty` String(10), `tags` JSON, `embedding` Vector(1536), `deleted_at` (soft-delete). |
| `card_progress` | `app/models/card_progress.py` | Unique `(user_id, card_id)`. FSRS fields: `state` (new/learning/review/relearning), `stability`, `difficulty_fsrs`, `elapsed_days`, `scheduled_days`, `reps`, `lapses`, `fsrs_step`, `last_reviewed`, `due_date`. |
| `card_feedback` | `app/models/card_feedback.py` | `user_id`, `card_id`, `vote` (`up` / `down`), `comment` (free text). |

The current schema is **flat: cards belong directly to a category. No `deck`,
`lesson`, `lesson_card`, or `quiz_item` tables exist on disk** — verified by
`grep -rn "decks\|Deck\b\|lesson_id\|quiz_item" hirelens-backend/app
--include="*.py"` returning no hits other than the audit-scoped grep itself.

This is a load-bearing finding: **Phase 6's locked decision to drop the
existing decks/lessons/cards model is greenfield work, not a migration**, even
though the prompt phrases it as "drop existing" — there is nothing to drop on
the deck/lesson side; only the existing flat `cards`/`categories` schema gets
retired.

### 1.2 FSRS implementation

- Library: `fsrs>=6.3.1` (confirmed in `requirements.txt:18`), imported as
  `from fsrs import Card as FsrsCard, Rating, Scheduler, State` —
  `app/services/study_service.py:27`.
- Scheduler is a module-level singleton (`_scheduler = Scheduler()`,
  `study_service.py:48`); stateless, safe to share.
- State mapping in `_STATE_TO_FSRS` / `_FSRS_TO_STATE`
  (`study_service.py:52-57`). Our `"new"` is a synthetic pre-FSRS state — a
  fresh `FsrsCard` is constructed on first review (`_build_fsrs_card` lines
  63-80).
- Per-card scheduling lives in `review_card` and `_apply_fsrs_result`;
  `last_reviewed`, `due_date`, `elapsed_days`, `scheduled_days` are written
  back into `CardProgress` (lines 83-104). All scheduling is server-side; FE
  receives only `due_date`, `fsrs_state`, and metadata (R4 enforced).
- Daily 5 query: `study_service.get_daily_review` selects overdue rows
  (`due_date <= now`) ordered ASC, then fills with unreviewed cards up to
  `_DAILY_GOAL = 5`. Free users are filtered to `categories.source =
  'foundation'` via `_is_free(user)` in `app/api/v1/routes/study.py:34-45`.

### 1.3 Free-tier daily-card wall (B-019/B-031/B-059, spec #50, LD-001)

Today the free tier has **two layers** stacked on the FSRS queue, both worth
keeping in mind for Phase 6's persona-aware Learn page:

1. **Foundation gate** — `_is_free(user)` filters category access to
   `source='foundation'`.
2. **Daily review wall** — `study_service._check_daily_wall`
   (`study_service.py:175-260`) increments a Redis key
   `daily_cards:{user_id}:{YYYY-MM-DD}` (user-local tz via
   `EmailPreference.timezone`) with 48 h TTL. Cap is read live from
   `Settings.free_daily_review_limit` (env-tunable; **default `10` since
   LD-001 amendment 2026-04-26 — was 15**). Exceeds → `DailyReviewLimitError`
   → 402 with `{error, trigger:'daily_review', cards_consumed, cards_limit,
   resets_at, plan}`.
3. **Read-side mirror** — `_compute_daily_status`
   (`study_service.py:283-330`) is a side-effect-free `Redis.GET` that the
   `GET /api/v1/study/daily` route includes in its response as
   `daily_status: DailyStatus`. Powers the pre-flight `DailyReviewWalledView`
   on `/learn/daily` (B-059, spec #63).

Pro / Enterprise / admin bypass via early return in `_check_daily_wall`. Fail-
open on Redis outage (logs and lets the review through; `daily_card_submit`
PostHog event records `counter_unavailable: true`).

### 1.4 Card review UX — live FE component graph

Card-shape consumers (the literal `Card` interface from `src/types/index.ts:148`):

```
hirelens-frontend/src/hooks/useCardViewer.ts:3:  import type { Card } from '@/types'
```

Single direct import. (Other "Card" filenames — `CategoryCard`,
`ApplicationCard`, `AnimatedCard`, `FlipCard` — are unrelated UI primitives.)

`DailyCard` is the wire shape returned by `GET /api/v1/study/daily` and is
distinct from `Card` (`types/index.ts:181-193`). Consumers:

- `pages/DailyReview.tsx` — daily-queue page; pre-flight wall via
  `DailyReviewWalledView`; submits via `QuizPanel`.
- `pages/CardViewer.tsx` — single-card viewer (`/learn/card/:id`).
- `components/study/QuizPanel.tsx` — single submit chokepoint for
  `POST /api/v1/study/review`. Used by `DailyReview`, `CardViewer`,
  `MissionMode`. On 402 with `detail.trigger === 'daily_review'`, opens
  `PaywallModal` and fires `daily_card_wall_hit
  {surface:'daily_review_submit'}`.
- `components/study/FlipCard.tsx` — front/back flip primitive.
- `components/study/DailyReviewWalledView.tsx` — full-page upsell; reads
  `daily_status.resets_at` for countdown copy, no other backend deps.
- `components/study/WallInlineNudge.tsx` — inline nudge surface (older,
  pre-pre-flight pattern).
- `components/study/CategoryCard.tsx` — tile on `StudyDashboard`.

`StudyDashboard.tsx` is the deck-list-equivalent today. It renders categories
returned by `GET /api/v1/cards` and surfaces persona-aware copy + the
`?source=last_scan` hero hint (B-052/B-053, spec #62).

> **Confirmation:** the StudyDashboard "P5-S16 runtime breakage" called out
> in the prompt was closed by **B-007** (commit `2c01cc7`, 2026-04-18) — the
> `PERSONA_CONFIG` undefined-for-snake_case-persona bug was the breakage; on
> disk today `StudyDashboard.tsx:213-241` reads snake_case persona values
> directly with no PERSONA_CONFIG indirection. Live and stable.

### 1.5 Persona filtering on the Learn page

There is **no Lens-driven ranking on `/learn` today**. `StudyDashboard.tsx`
branches by `user.persona` at lines 213-241 for a header copy variant only;
the category grid itself is rendered uniformly from the
`/api/v1/cards` response. The Phase 6 persona-aware Learn behavior
(Climber free pick / Interview Prepper Lens-ranked) is greenfield.

### 1.6 Admin role infrastructure — already present

- `users.role` is `String(20) NOT NULL DEFAULT 'user'`
  (`app/models/user.py:17-19`). Three values observed: `user`, `admin`. No
  `admin` user table; admin is a role flag (matches `.agent/skills/admin-panel.md`).
- BE gate: `app/core/deps.py:91-101` — `require_admin` chains
  `get_current_user` → 403 if `user.role != 'admin'`.
- `audit_admin_request` (`deps.py:104-143`) wraps every
  `/api/v1/admin/*` route, writes `admin_audit_log` rows via
  `BackgroundTasks` and side-fires `admin_analytics_viewed` PostHog when path
  starts with `/api/v1/admin/analytics` (E-018a/E-018b).
- FE gate: `src/components/auth/AdminGate.tsx` (E-040) wraps `/admin` and
  `/admin/analytics` routes (`App.tsx:102-103`).
- Login-time reconciliation: `auth.py::google_auth` calls
  `user_service.reconcile_admin_role(user, admin_emails_set)` against
  `Settings.admin_emails` (env `ADMIN_EMAILS`, comma-separated, fail-closed
  on empty); fires `admin_role_reconciled` PostHog (E-040, spec #54).
- Admin promotion outside the email whitelist is direct DB UPDATE today (no
  promotion UI).

**Phase-6 takeaway:** the admin role + audit-logging skeleton is mature
enough to host the slice 6.4 admin authoring UI without re-platforming.

---

## Section 2 — Lens (ATS scanner) integration surface

### 2.1 Scan result model + retention

- Scan endpoint: `POST /api/analyze` (and `/api/v1/analyze` re-export shim).
  Returns `AnalysisResponse` (defined in `app/models/response_models.py`,
  schema mirrored on FE at `src/types/index.ts:AnalysisResponse`).
- **Persistence (B-035 / spec #59 / `30bf39fa04f8` migration):**
  `tracker_applications_v2.analysis_payload` is a `JSONB NULL` column with
  `sqlalchemy.orm.deferred()` so list endpoints don't inflate. Holds the full
  `AnalysisResponse.model_dump(mode="json")`. Read via
  `GET /api/v1/analyze/{scan_id}` — 404 unknown / cross-user (LD-4 — never
  403), 410 `legacy_scan_pre_persistence` for NULL payload, 200 owner.
- **Retention:** unbounded today — no TTL, no cleanup job, no row deletion.
  Tied to the lifetime of the tracker application row (which itself has no
  retention policy beyond user-initiated DELETE via
  `/api/v1/tracker/{app_id}`).
- Tracker linkage: `tracker_applications_v2.scan_id` indexed; auto-populated
  via `tracker_service_v2.create_application` from inside `analyze.py:253-275`.

### 2.2 Required-skills extraction from JD

`app/services/nlp.py::extract_job_requirements` (`nlp.py:114-191`) returns:

```python
{
    "required_skills": list[str],     # canonical skill names from taxonomy
    "preferred_skills": list[str],
    "all_skills":      list[str],     # union of req + pref
    "job_title":       str,
    "seniority_level": "Junior" | "Mid-level" | "Senior" | "Manager",
    "responsibilities": list[str],
    "company_name":    str | None,    # B-024 three-layer (LLM → regex → null)
}
```

- **Format:** flat string lists (canonical skill names from `app/utils/skill_taxonomy.py`).
- **Confidence scores:** none. Required-vs-preferred is pure regex section
  splitting (`required_section`/`preferred_section` greedy match, lines
  136-150). Defaults to "required" when not in the preferred section
  (line 162-163).
- **Canonicalization:** every match goes through
  `skill_taxonomy.find_skill()` for canonical-form lookup; categories are
  `Technical | Tool | Soft | Certification` (see `gap_detector.py:97-103`).

### 2.3 Resume-side skill extraction

Same module (`nlp.py:78-111`), `extract_skills(text)`. Two methods stacked:

1. Direct taxonomy match against `ALL_SKILLS_LOWER` keys (case-insensitive,
   word-boundary regex).
2. spaCy NER for `ORG`/`PRODUCT`/`WORK_OF_ART` entities, run through
   `find_skill()` for canonical mapping.

Returns `sorted list[str]`. **No confidence scores; no proficiency levels;
no years-of-experience.** Just presence/absence.

### 2.4 Lens → other-domain integration today

There is **no public service helper that exposes Lens results to non-Analyze
domains**. Specifically:

- `tracker_applications_v2.skills_matched` and `skills_missing` are
  comma-joined Text columns (`app/models/tracker.py`), not structured.
- The `analysis_payload` JSONB on `tracker_applications_v2` is owner-gated
  by `get_scan_by_id`. There is no aggregated view ("most-recent scan per
  user", "all my missing skills") — every consumer must call
  `GET /api/v1/analyze/{scan_id}` and parse JSON.
- `app/services/gap_mapping_service.py::map_gaps_to_categories` consumes
  scan output (skill gap list) and maps to study categories via
  `categories.tags` JSONB join + pgvector cosine similarity fallback.
  Live consumer: `/api/v1/onboarding/recommendations` only.
- `home_state_service.py` reads
  `most_recent_scan = tracker.created_at DESC LIMIT 1`, returns
  `last_scan_date` to drive the state-aware home dashboard. Does NOT expose
  the scan's skill gaps.

**Phase-6 implication for slice 6.6 (Lens-ranked deck/card ordering for
Interview Prepper):** the ranker will need a new service helper. Two options
that fall out of the audit:

- (A) **Aggregated read** — `get_recent_skill_gaps(user_id, lookback_days,
  limit) → list[SkillGap]`. Lighter; can be built without schema changes by
  iterating recent `tracker_applications_v2` rows that have
  `analysis_payload` and unioning the `skill_gaps` field. Cost concern:
  N rows × JSONB unmarshal per ranker call.
- (B) **Materialized table** — denormalize `user_skill_gap` rows on scan
  write. Faster reads, but adds schema work and a backfill story. Phase 6
  scope already loaded.

Locked decision is silent on this — flagged in §Recommendations R-2.

### 2.5 Cold-start state

A Pro user with no Lens scan looks like:

- `tracker_applications_v2`: zero rows for that `user_id`.
- `home_state_service` returns `last_scan_date: null`,
  `home_state_service.get_next_interview` returns None.
- `/api/v1/onboarding/recommendations` returns `{scan_id: null, results: []}`.
- No "default Lens result" exists in code — there is no synthesized empty
  state. Callers that need ranking must handle the null case.

For Phase 6 slice 6.6, this means the Lens-ranker spec must explicitly
define cold-start behavior for Interview Prepper Pro users (probably:
fall back to Study Board "all decks" view per the locked decision).

---

## Section 3 — Persona model

### 3.1 Persona storage + enum

- BE: `users.persona` is `String(30) NULLABLE`
  (`app/models/user.py:20`). Migration `02bf7265b387` (Phase 5)
  renamed/migrated values to snake_case.
- FE canonical type:
  `src/context/AuthContext.tsx:25 — type Persona = 'interview_prepper' |
  'career_climber' | 'team_lead'`. **24 files import this type** (per
  CODE-REALITY §8). Three snake_case values; null = persona-not-set
  (PersonaGate redirects to `/onboarding/persona`).
- Pydantic schema: `app/schemas/user.py::PersonaUpdateRequest` (referenced
  by `users.py::update_persona`).

### 3.2 Persona-driven branching in FE — live component graph

| Component | Branch | Purpose |
|-----------|--------|---------|
| `pages/HomeDashboard.tsx:213-235` | `interview_prepper` / `career_climber` / `team_lead` | Renders three different "modes" — `InterviewPrepperMode`, `CareerClimberMode`, `TeamLeadMode`. Spec #61 composition rules. |
| `pages/StudyDashboard.tsx:192,216-241` | All three | Header copy variants (target_company, target_date countdown phrasing). |
| `pages/PersonaPicker.tsx:67,75` | `interview_prepper` | `return_to` URL-param honored only when persona is/was Interview Prepper. |
| `pages/MissionMode.tsx:388` | `interview_prepper` | `MissionDateGate` only mounts for Interview Prepper. |
| `pages/FirstAction.tsx:27,30,85,112` | All three | Per-persona CTA + headline. |
| `components/PersonaGate.tsx:11` | `null` | Redirects persona-null users to `/onboarding/persona`. |
| `components/home/widgets/InterviewPrepperChecklist.tsx:55` | `interview_prepper` | Mounts only for IP; spec #41. |
| `components/mission/MissionDateGate.tsx:5` | `interview_prepper` | No-date gate. |
| `hooks/useOnboardingChecklist.ts:14,26` | `interview_prepper` | Skip-fetch when not IP. |

**No `team_lead` "mode" UI exists beyond a placeholder** — `TeamLeadMode`
mounts but renders mostly the `TeamComingSoonWidget`. This is documented
intent, not a bug.

### 3.3 PATCH /api/v1/users/me/persona

Confirmed at `app/api/v1/routes/users.py:74-105`. Signature:

```
PATCH /api/v1/users/me/persona
Body: PersonaUpdateRequest {
  persona: PersonaEnum,
  interview_target_date: date | null,
  interview_target_company: str | null,
}
Auth: Depends(get_current_user)
Rate limit: 10/min (slowapi)
Returns: full _user_dict(user) (so FE can updateUser() with the freshest copy)
```

Side effects:

- First-time persona set flips `onboarding_completed = True` (line 93-94).
- Dual-writes `interview_target_date` to most-recent active tracker row
  (spec #57 §2.3 — find-and-seed, never overwrites).
- Invalidates home-state Redis cache via `home_state_service.invalidate`.

The endpoint shape is healthy for Phase 6 — no changes needed unless slice
6.x adds persona-scoped fields.

---

## Section 4 — Payments / Pro gating

### 4.1 Pro status at request time

Two distinct paths, both used in production:

| Surface | Mechanism | File / line |
|---------|-----------|-------------|
| Generic plan-min check | `Depends(require_plan("pro"))` factory (returns a closure that re-loads `Subscription` per request) | `app/core/deps.py:189-220` |
| Inline plan check | `_is_free(user)` in service code reads `user.subscription` (loaded via `selectin` in `get_current_user`) | `app/services/study_service.py`, `app/services/card_service.py:35-48`, `app/api/v1/routes/study.py:34-45` |
| Quota-based check | `usage_service.check_and_increment(...)` — short-circuits Pro/Enterprise/admin to `allowed=True, limit=-1` | `app/services/usage_service.py:156-220` |
| Paywall dismissal | `paywall_service.should_show_paywall()` — Pro/admin always returns `{show:false}` | `app/services/paywall_service.py` |

**No middleware-level Pro gate.** Each route opts in via the dep or calls a
service that does the check. This is correct for SkillForge: most routes are
free-allowed with quota gates.

### 4.2 FE entitlement

`src/context/UsageContext.tsx` is the canonical FE gate:

- `useUsage()` exposes `canScan`, `canUsePro`, `canUsePremium`,
  `checkAndPromptUpgrade()`, `setShowUpgradeModal`.
- Plan derivation: `canUsePro = plan==='pro' || plan==='enterprise' ||
  isAdmin` (`UsageContext.tsx:131`).
- `usage` is hydrated from `GET /api/v1/payments/usage` per the
  `useEffect → refreshUsage()` pattern (lines 152-154); cached in
  `localStorage` under `skillforge_usage` (display-cache only; BE is
  authoritative on every quota gate).
- 8 paywall triggers shipped today (`PaywallModal.tsx:21-29`):
  `scan_limit | card_limit | locked_category | daily_review |
  interview_limit | skill_gap_study | rewrite_limit | cover_letter_limit`.
  **Phase 6 will likely add `lesson_limit` / `quiz_attempt_limit` / `digest_pro_only`** —
  the modal headline/subline tables (lines 38-66) are easy to extend.

### 4.3 Pages/routes gated today

Direct route gates: `/admin` and `/admin/analytics` (AdminGate, role-based,
not plan-based). All other gating is feature-level (per-action) inside
pages. Example: Rewrite uses `useRewrite` + `useUsage`; Analyze uses
`useAnalysis` + `useUsage`; pre-flight gates land via `Analyze.tsx:87,169`
+ `DailyReview.tsx:47-...` patterns.

### 4.4 "Query all Pro users" path for slice 6.14 (daily digest)

The cleanest path: query `Subscription` directly.

```python
SELECT user_id FROM subscriptions
 WHERE plan IN ('pro', 'enterprise')
   AND status = 'active'
```

Joined to `email_preferences` for opt-in. **Admin role is orthogonal** —
admins on the free plan are not Pro for billing purposes. Slice 6.14 should
key on `subscriptions.plan IN ('pro','enterprise') AND status='active'` (not
on `users.role`).

There is no helper service today that returns "all Pro users". `usage_service._get_plan_and_role`
is per-user. Slice 6.14 can either (a) add a query-helper to a new
`digest_service.py`, or (b) inline the SQL in the cron entry point.

### 4.5 Free-tier env-tunable caps (testing affordance, `d19103c` + `b8d0c8c`)

Three Settings flags live for local QA without burning real quota:

| Flag | Default | Effect |
|------|---------|--------|
| `FREE_DAILY_REVIEW_LIMIT` | `10` (post-LD-001 amendment 2026-04-26) | Spec #50 wall cap. |
| `FREE_LIFETIME_SCAN_LIMIT` | `1` | Spec #56 lifetime ATS cap. |
| `FREE_MONTHLY_INTERVIEW_LIMIT` | `3` | Interview-prep monthly cap. |

These are not yet documented in `AGENTS.md`'s env vars table (CODE-REALITY
§11 drift #17). For Phase 6 specs that introduce new free-tier caps
(e.g. lesson views per day for Climber free pick), follow the same pattern:
`Settings.free_*` → `_plan_limits()` re-read live → env-tunable in tests.

---

## Section 5 — Email infrastructure (Resend)

### 5.1 Resend integration

`app/services/email_service.py` is a **single-function wrapper** around
`resend.Emails.send`:

- Entry point: `async def send_email(to, subject, html_body) -> str | None`.
- Retries: 3 attempts on 429/5xx with exponential backoff (`_BACKOFF_BASE=1s`,
  doubled per attempt).
- Silent no-op when `RESEND_API_KEY` is unset (logs warning, returns None).
  Confirmed at lines 36-39.
- `EmailSendError` raised on permanent 4xx (non-429) errors.
- From address: `RESEND_FROM_ADDRESS` env (default
  `reminders@skillforge.app`).

**No template management** — templates are a single file on disk
(`app/templates/daily_reminder.html`) read via `_TEMPLATE_DIR.read_text()` in
`reminder_service.py:30-33`. Substitution is naïve string `.replace("{{key}}",
val)` (lines 45-52). No Jinja, no template versioning, no MJML.

### 5.2 Existing transactional emails

**Exactly one email type today:** the daily reminder. Triggered by
`reminder_service.send_daily_reminders(db)` (lines 122-155). No login
emails, no payment receipts (Stripe handles those), no welcome emails, no
admin alerts.

The cron / scheduler that calls `send_daily_reminders` is **not visible
in the repo** — no `app/cron.py`, no `scheduler.py`, no Railway scheduled
job in `railway.toml`. (CODE-REALITY does not list a cron entry point
either.) This is a phase-6 scout finding: **the daily reminder service
is shipped but its trigger is opaque to the repo** — likely a Railway
scheduled job configured outside source. Slice 6.14 must surface this
either by inheriting the same external scheduler or by introducing one
(e.g. an APScheduler / FastAPI startup task).

### 5.3 Notification preferences on User

Stored in `email_preferences` (`app/models/email_preference.py`):

| Column | Type | Default |
|--------|------|---------|
| `user_id` | PK FK users.id | — |
| `daily_reminder` | Boolean | `True` |
| `timezone` | String(50) | `"UTC"` |
| `unsubscribe_token` | String(64) unique | `secrets.token_hex(32)` |
| `created_at` / `updated_at` | DateTime | `now()` |

Single per-feature opt-out flag (`daily_reminder`). No per-feature granular
prefs. **Phase 6 slice 6.14 (Pro daily digest) will need a second
opt-out flag** — likely `daily_digest: Boolean DEFAULT True` on the same
table — plus a UI surface (today's `pages/EmailPreferences.tsx` is a single
checkbox with a timezone picker).

Endpoints:
`GET/PUT /api/v1/email-preferences` (`app/api/v1/routes/email_prefs.py`) — currently
exposes only `daily_reminder` and `timezone`. Adding `daily_digest` is
additive.

### 5.4 `email_log` / `email_sent` table

**No `email_log` table exists.** Verified by
`grep -rn "email_log" hirelens-backend/app` — no model file, no migration,
no service writes. The only durable email record is the PostHog
`email_sent` event fired in `reminder_service.py:141-149` after a
successful Resend send.

**Phase 6 slice 6.14 implication:** if the Pro daily digest needs (a) a
delivery audit trail, (b) per-user dedup ("don't send the same digest
twice"), or (c) a "view your last digest" surface, the slice needs to add
the table. Spec it explicitly. Today's reminders rely on the cron firing
exactly once per user per day; there's no idempotency record.

---

## Section 6 — Analytics infrastructure

### 6.1 PostHog wiring

**Both tiers wired.**

- BE: `app/core/analytics.py` — `track(user_id, event, properties=None)`.
  Lazy client construction via `Posthog(project_api_key, host)`. Silent
  no-op when `POSTHOG_API_KEY` unset (lines 39-44). Distinct-id falls back
  to `"anonymous"` for `user_id is None` events.
- FE: `src/utils/posthog.ts` — `capture(event, properties?)` wrapper around
  `posthog-js@^1.366.0`. Init in module-init body when `VITE_POSTHOG_KEY`
  set; `capture_pageview: false`, `autocapture: false`, manual events
  only. Persistence: `localStorage`.
- Identify-on-login: handled by PostHog auto on the FE side; explicit
  identify in `LoginPage`/`AuthContext` not present in skim, likely relying
  on PostHog's auto-identify with the access-token bearer's distinct id.

### 6.2 Event taxonomy

Catalog: `.agent/skills/analytics.md` (170+ events documented). Conventions:

- `snake_case` event names exclusively.
- Flat property dicts (no nesting).
- Backend events always pass `user_id` first; frontend events implicit via
  PostHog identify.
- Deprecation pattern: keep the row in the catalog with `**(DEPRECATED
  <slice>)**` header; never rename — replace.
- Idempotency guards via `useRef` for once-per-mount events
  (`home_dashboard_viewed`, `paywall_hit`, `study_dashboard_source_hint_shown`).

**No internal event registry / type system** — the catalog is markdown,
checked manually. Adding an event today is "wire `track()`/`capture()` +
update `analytics.md`". For Phase 6's "every spec must include events
emitted" requirement, this is acceptable but loose; consider tightening
in a future hardening slice.

### 6.3 Internal analytics tables in PG

The audit found these analytics-adjacent tables already on disk:

| Table | Source | Purpose |
|-------|--------|---------|
| `usage_logs` | spec #11a / Phase 1 | Per (user, feature, timestamp) row; powers `check_and_increment` and `admin_analytics_service.get_performance_summary`. |
| `paywall_dismissals` | spec #42 | Per-trigger dismissal log, drives 60s LD-8 dedup and Strategy A grace counter. |
| `card_feedback` | Phase 3 spec #21 | User thumbs up/down + free-text comment per card. |
| `card_progress` | Phase 1 | FSRS state, indirectly powers retention analytics (`admin_analytics_service` reads `last_reviewed`). |
| `gamification_stats` | Phase 2 | Streaks + XP. Read by admin metrics. |
| `admin_audit_log` | spec #38 E-018a | Append-only admin request trail. |
| `stripe_events` | spec #43 | Webhook idempotency + payment attribution. |

**No `review_events` or `study_sessions` table exists.** Verified by
`grep -rn "review_events\|study_sessions" hirelens-backend/app
--include="*.py"` returning zero hits. Spec #50's `daily_card_submit`
PostHog event is the only per-review record; nothing in PG.

**Phase 6 slice 6.0 (analytics-as-foundation) implication:** the prompt
calls for a per-quiz-item review event store. PostHog is the wire today
(via `card_reviewed` BE event from `study_service.py` and `quiz_submitted`
FE event from `QuizPanel.tsx`). If slice 6.0 wants Postgres-backed event
storage (e.g. for the FSRS retention dashboard in slice 6.16), it has to
add the table — spec it as `quiz_review_events` or similar. Tradeoff: dual
storage costs vs simpler FE → BE → admin-dashboard funnel.

### 6.4 Existing dashboards

- `/admin/analytics` (`pages/AdminAnalytics.tsx`, 278 lines) — six-OKR
  metrics + performance snapshot, with 7d/30d/90d/YTD segments. Backend:
  `admin_analytics_service.get_metrics_summary` +
  `get_performance_summary`. Postgres-only; PostHog Query API explicitly
  out-of-scope per spec #38 Slice 2 (`schemas/admin_analytics.py:5,67`).
- No user-facing dashboards. `/profile` shows streak/XP via
  `<StreakBadge>` + `<XPBar>` and an `ActivityHeatmap`/`SkillRadar` on
  `/prep/results` and `/profile`. None aggregate Lens scans or quizzes.

**Phase 6 slice 6.16 implication:** the FSRS retention dashboard is greenfield.
The auth gate (admin or user-self?), the data source (Postgres aggregates
or PostHog HogQL), and the dashboard surface (admin-only initially? or
user-self?) all need locking before the spec drafts. See R-3.

---

## Section 7 — Admin / authoring infrastructure

### 7.1 Admin UI today

`pages/AdminPanel.tsx` (868 lines, single file) is the **only admin authoring
surface**. It manages cards: list, create, edit (including AI-assisted
draft generation), delete, bulk CSV import. It is a single-page tabbed
layout, not a multi-route admin section.

`pages/AdminAnalytics.tsx` (278 lines, separate route) handles analytics.

There is no UI for:
- Categories (read-only via the `cards` admin endpoints; no rename/reorder
  surface).
- Users (view, promote, demote).
- Email previews / digest scheduling.
- Lessons / decks / quiz items (none of these concepts exist in the schema).

**Phase 6 slice 6.4 (admin authoring UI) implication:** AdminPanel.tsx is
already a single 868-line file. Adding deck/lesson/quiz_item CRUD inside
it would push past 1500 lines — almost certainly worth splitting into a
multi-route admin shell from the start. See R-4.

### 7.2 Content upload + file storage

**No object storage today.** Verified by:
- `requirements.txt` has no `boto3`, no `aiobotocore`, no `cloudflare`.
- `grep -rn "boto3\|S3\|R2\|put_object" hirelens-backend/app
  --include="*.py"` returns only string-literal matches in
  `skill_taxonomy.py` (the literal "S3" as an AWS-skill name).
- No `app/services/storage_service.py` or equivalent.

Files (resume PDFs/DOCX) are streamed in via `UploadFile`, parsed in-memory
via pdfplumber/python-docx, and **never persisted to disk or object
storage**. The parsed text goes into the `resumes` table (`Text` column) and
the file bytes are dropped at the end of the request.

`AGENTS.md` line 326-327 says "R2 for files (zero egress)" but this is
**aspirational**; no R2 / S3 binding exists. Document drift; not blocking
Phase 6 unless a slice needs durable file storage.

**Phase 6 slice 6.10 (ingestion pipeline) implication:** if the ingestion
pipeline needs to ingest Markdown/JSON content from external sources, R2/S3
binding (or a simpler file-on-disk pattern in `app/data/`) becomes a slice
prerequisite. Lock that decision in the spec.

### 7.3 Background job system

**Only `fastapi.BackgroundTasks`** (used in `core/deps.py:7,106` for
`audit_admin_request` writes and `_fire_admin_analytics_viewed`). No
Celery, no RQ, no Dramatiq, no Huey, no APScheduler — verified via
`requirements.txt` skim and grep.

`BackgroundTasks` runs in the same Python process as the request handler
**after the response returns** but inside the same async event loop. It
cannot survive process restart, cannot be retried by the framework, and
cannot fan out across workers.

**Phase 6 slice 6.10 (Gemini generate + cross-model critique) implication:**
the current ingestion pipeline pattern is "synchronous LLM call inside
the request handler" — see `ai_card_service.generate_card_draft`. For a
cross-model critique flow (slow, multi-step, retry-prone) this will not
scale. Slice 6.10 needs to either:

- (A) Pick a job queue. Recommended: keep it simple with **Redis-backed RQ**
  or **APScheduler** rather than full Celery — Redis is already a hard dep
  for the daily-card wall counter.
- (B) Make every ingestion call lock-step synchronous and accept the
  request-time latency. Acceptable only if generation + critique fits in
  ~60s end-to-end, which is unlikely for two cross-model passes.

This is genuinely a Phase 6 unblocker. See R-5.

### 7.4 Daily reminder cron — lives outside the repo

Reiterating the §5.2 finding: the entry point for the daily reminder is
`reminder_service.send_daily_reminders(db)` but **no in-repo trigger**. Most
likely a Railway scheduled job configured in the dashboard. Phase 6 slice
6.14 either inherits this pattern (config-only, opaque to the repo) or
introduces an in-repo scheduler. The Pro digest is daily, so cadence
matches.

---

## Section 8 — AI / generation infrastructure

### 8.1 LLM call surface

The router lives at `app/core/llm_router.py`. Public API:

```python
from app.core.llm_router import generate_for_task

text = generate_for_task(
    task="resume_rewrite",
    prompt=...,
    system_prompt=...,
    json_mode=False,
    max_tokens=4096,
    temperature=0.7,
    thinking_budget=...,  # optional, Gemini reasoning-tier only
)
```

Tier dispatch:
- `FAST_TASKS` frozenset (12 task names): `ats_keyword_extraction`,
  `card_draft`, `quiz_generation`, `gap_mapping`, `rewrite_bullets`,
  `experience_narrative`, `company_name_extraction`, plus a few internal
  ones.
- `REASONING_TASKS`: `resume_rewrite`, `resume_rewrite_section`,
  `cover_letter`, `interview_questions`, `job_fit_explanation`.
- Unknown task names default to fast.

Provider dispatch via env vars:
`LLM_FAST_PROVIDER`/`LLM_FAST_MODEL`/`LLM_REASONING_PROVIDER`/`LLM_REASONING_MODEL`,
defaulting to Gemini Flash + Gemini 2.5 Pro. Code-side handlers exist for
`gemini`, `anthropic`, `openai` (`google-genai`, `anthropic`, `openai`
SDKs all in `requirements.txt`).

`R11` (in CLAUDE.md) and `.agent/skills/llm-strategy.md` enforce: **never
import provider SDKs from service code; always go through
`generate_for_task()`**. There's a legacy `app/services/llm/` (factory.py +
claude_provider.py + gemini_provider.py) parallel-track abstraction, but
it's earmarked for Phase 6 cleanup (CODE-REALITY §9 — flagged "do not
extend"; consumed only by `/api/v1/resume/{id}/optimize` enterprise path
via `ai_service.py`'s duplicate of `gpt_service.py`).

### 8.2 Cross-model critique today

**No cross-model critique pattern exists in code.** Verified by grepping
the router and service files — all callers pass a single task name and
get a single response. The cross-model concept (Gemini generates, Claude
or OpenAI critiques) is greenfield for slice 6.10.

The router can support it without code changes today: a critique caller
simply hardcodes the second provider via env override of
`LLM_REASONING_PROVIDER` for one call site. Better long-term: extend
`generate_for_task` with a `provider_override: str | None = None` param
so a single ingestion job can call Gemini for generation and Anthropic for
critique without flipping the global env var. Recommended in R-6.

### 8.3 Prompt management

**Prompts are inlined in service code.** Examples:
- `gpt_service.py:_build_cover_letter_prompt`
- `nlp.py::_extract_company_name_llm` — prompt as f-string at lines
  273-300.
- `experience_service.py` — prompt template in service body.

No version control of prompts beyond git. No prompt-template registry. No
A/B harness. Adding one is straightforward (e.g. `app/prompts/<task>.txt`
+ `Path(...).read_text()` loader) but is greenfield work for any Phase 6
slice that wants critique-prompt iteration.

### 8.4 Eval harness

**None.** No `tests/integration_llm/` evaluating prompt outputs against
golden sets; the only LLM-touching tests are unit tests with mocks
(`@pytest.mark.integration` is the marker that gates real-LLM tests but
the suite running under it is small — `tests/services/test_resume_rewrite.py`
and similar live-call asserts).

R13 in CLAUDE.md says coverage (`pytest-cov`) is deliberately not
installed. Phase 6 slice 6.10 will likely want a "critique outputs match
expected dimension/severity" check — mock-based or golden-based — but
this is greenfield.

---

## Section 9 — Frontend foundations

### 9.1 Component library + tokens

- `tailwindcss@^3.4.1` (`package.json`).
- Design tokens at `src/styles/design-tokens.ts` with three themes
  (`dark` / `light` / `midnight-blue`); `applyInitialTheme()` runs in
  `main.tsx` pre-render to avoid theme flash.
- Tailwind utilities are tied to CSS vars via the `rgb(varName)` helper
  in `tailwind.config.ts` so `bg-bg-base` / `text-text-primary` /
  `border-border-accent` are theme-aware. `bg-accent-primary/40` works
  because the var holds an RGB triple.
- No headless UI library — primitives are hand-rolled in `components/ui/`
  (AnimatedCard, GlowButton, ProgressBar, ScoreBadge, SkeletonLoader,
  Tooltip, UpgradeModal — 7 primitives total).
- R12 forbids hardcoded hex; spec #21 / B-026 hardened the theme system
  with `color-scheme` per-theme.

### 9.2 Routing + auth guards

- `react-router-dom@^6.22.0`.
- `App.tsx:63-124` defines the full route table.
- Wrappers (in nesting order from outermost):
  - `<AppShell>` — handles chrome (TopNav / MobileNav) with
    `CHROMELESS_PATHS` + auth-aware `/pricing` carve-out (B-057, B-058).
  - `<ProtectedRoute>` — auth gate; redirects unauth → `/`.
  - `<PersonaGate>` — persona-null → `/onboarding/persona`.
  - `<Suspense fallback={<LazyFallback />}>` — for lazy pages (`Profile`,
    `MissionMode`, `AdminPanel`, `AdminAnalytics`).
  - `<AdminGate>` — additional wrap on `/admin` and `/admin/analytics`
    (E-040).
- Transitional redirects (P5-S13 fallout, drop in Phase 6 cleanup):
  `/analyze | /results | /rewrite | /interview | /tracker | /study | /study/daily |
  /study/category/:id | /study/card/:id | /mission` → namespaced
  equivalents (`App.tsx:106-115`). Telemetry on the `<Navigate>` redirects
  is missing (B-008 🔴).

### 9.3 State management

- **TanStack Query: not installed.** `package.json` has no
  `@tanstack/react-query` entry; grep confirms zero usage in code.
- **Zustand: installed (`^4.5.0`) but not used.** No `create()` calls
  in code paths. Vestigial dep.
- **React Context + hooks** is the canonical pattern:
  - `AuthContext` (`AuthProvider` + `useAuth`) — auth state, `user`,
    `signIn`, `signOut`, `updateUser`.
  - `UsageContext` — plan, scan/rewrite/cover-letter/interview-prep
    counters, paywall modal state.
  - `AnalysisContext` — current scan + reducer (`AnalysisAction`
    discriminated union).
  - `GamificationContext` — streak/XP/badges fetcher.
  - `ThemeContext` — theme switching.
- Hooks under `src/hooks/` — 11 hooks, each owning a fetch + reducer
  pattern (e.g. `useStudyDashboard`, `useCardViewer`, `usePricing`).
- No global cache layer; each hook re-fetches on mount. This is fine
  today (small surface) but the Phase 6 Learn page with persona-aware
  ranked content + multi-call hydration would benefit from TanStack
  Query. Lock the decision in the slice 6.x spec rather than in flight.

### 9.4 Form handling

- `react-hook-form@^7.50.1` is installed but **not consumed anywhere in
  src/**. Verified by `grep -rn "react-hook-form" hirelens-frontend/src`
  returning no hits.
- Forms today are uncontrolled / native HTML (e.g. `PersonaPicker`,
  `EmailPreferences`, `MissionSetup`).
- Phase 6 slice 6.4 (admin authoring UI) will be the first heavy form
  surface. Either adopt `react-hook-form` (already a dep, save the
  install) or stick with native + `useState` per field. Spec it.

---

## Cross-cutting findings

1. **No background-job system.** `BackgroundTasks` is the only async
   primitive. Slice 6.10 (cross-model ingestion) and 6.14 (daily Pro
   digest) both need a real scheduler. Same decision unblocks both.

2. **No object storage.** R2/S3 referenced in AGENTS.md but never
   wired. Resume bytes are processed in-memory and discarded. If Phase 6
   ingestion requires durable file storage (Markdown source-of-truth for
   lessons, generated quiz_item JSON, etc.), spec it explicitly.

3. **Greenfield ground truth, not a migration.** No `decks`, `lessons`,
   `lesson_card`, `quiz_item`, `card_quality_signals`, or
   `review_events`/`study_sessions` tables exist on disk. Phase 6's "drop
   existing decks/lessons/cards" is misleading wording — there is nothing
   to drop on the deck/lesson side; only the existing flat
   `cards`/`categories` schema gets retired (which IS load-bearing in
   the study engine, FSRS, gap mapping, and admin CRUD).

4. **Daily reminder cron lives outside the repo.** No in-repo scheduler;
   `send_daily_reminders` is presumably a Railway scheduled job. Phase 6
   slice 6.14 must explicitly choose: inherit-config-only or in-repo
   scheduler.

5. **No prompt registry, no eval harness.** Prompts are inlined in
   service code. Slice 6.10's quality-driven generation will iterate on
   prompts; budget for a thin prompt-template loader and at least a
   golden-set check upfront.

6. **Persona model is healthy.** snake_case enum stable across 24
   files; `PATCH /api/v1/users/me/persona` shape is good; `PersonaGate`
   handles the null branch. No Phase 6 work needed unless a slice adds
   persona-scoped fields.

7. **Admin role + audit-log skeleton is mature** but the AdminPanel
   page is already 868 lines as a single file. Slice 6.4 should split
   into a multi-route admin shell (`/admin/decks`, `/admin/lessons`,
   `/admin/quiz-items`, `/admin/critique-runs`, etc.) rather than
   bolting more tabs onto a monolith.

8. **No middleware-level Pro gate.** Each route opts in via
   `Depends(require_plan(...))` or service-level `_is_free`/`check_and_increment`.
   This is correct and expected to scale to Phase 6's new gates
   (`lesson_limit`, `quiz_attempt_limit`, `digest_pro_only` etc.).

9. **PostHog is wired both tiers; analytics catalog is markdown-only.**
   Acceptable; the "every spec includes events emitted" requirement is
   honored by appending to `.agent/skills/analytics.md` per slice. No
   tooling to enforce.

10. **AGENTS.md drift accumulator is real.** CODE-REALITY §11 lists 17
    drift items today. Most are documentation-side, none block Phase 6
    spec drafting, but they do mean a chat-Claude prompt drafted off
    AGENTS.md can name a wrong path or a phantom column. Continue
    grounding spec audits in CODE-REALITY (per R16).

11. **Lens has no per-user aggregated read.** `analysis_payload` is
    scan-scoped; "give me this user's most recent skill gaps" is N+1
    today. Slice 6.6 (Lens-ranked deck/card ordering) needs a helper.

12. **Three untracked skill directories**
    (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`)
    have been on disk since 2026-04-21 but are not in git. Source
    unknown. CODE-REALITY §10 + §12 Q8 have an open question for Dhamo.
    Not Phase-6-blocking, but worth resolving alongside any new
    `.agent/skills/` work.

---

## Slice-by-slice reality check (19 Phase 6 slices)

> Numbering follows the prompt's "6.0 through 6.16" framing (with
> implied gaps to reach 19 total). For each slice I report what
> foundation exists vs what must be built, plus any dependency the
> original plan looks like it missed.

> **⚠️ Numbering drift since this audit (`5b0aa23`, 2026-04-26):**
> Phase 6 was re-sequenced post-scout. On-disk reality (see
> `SESSION-STATE.md` Phase 6 specs block + BACKLOG B-078 / B-080) is
> the authoritative slice→spec mapping. Notable changes:
>
> - **Slice 6.8** now = user-self FSRS dashboard (spec
>   `docs/specs/phase-6/09-fsrs-dashboard.md`, shipped `0968a13` /
>   B-080 ✅). The "Pro-only daily digest emails" framing in this
>   audit's slice 6.8 entry below has moved to slice 6.14.
> - **Slice 6.14** now = daily Pro digest + cron architecture
>   decision (B-078 🟦, gated on pre-launch readiness — consolidates
>   this audit's slice 6.8 *and* slice 6.14 framings into one
>   forward-filed row). Spec #14 not yet authored; the cron
>   architecture decision (in-repo scheduler / Railway cron config /
>   external scheduler) must land before spec-author begins. Phase 6
>   locked decision **G2** currently leans Railway cron, but B-078
>   exists to surface the alternatives at activation time.
>
> Other slice numbering (6.0–6.7, 6.9–6.13.5, 6.15, 6.16) unchanged.
> Treat the slice-by-slice block below as historical scout context;
> consult SESSION-STATE + spec dir for current state.

**Slice 6.0 — analytics-as-foundation event taxonomy.** Foundation:
PostHog wired both tiers, catalog file in `.agent/skills/analytics.md`,
catalog conventions enforced by R8 + R12. Build: pick whether quiz/lesson
events go PostHog-only (current pattern) or also into a Postgres event
store; the latter unlocks slice 6.16's retention dashboard without
a HogQL dep, but adds a table and a write path. **Dependency missed:**
this slice MUST land before slice 6.10's ingestion (so generation events
are captured from day 1) AND before slice 6.4's admin UI (so admin
authoring events are namespaced consistently).

**Slice 6.1 — greenfield deck/lesson/quiz_item schema.** Foundation:
Alembic + SQLAlchemy 2.0 + pgvector mature. `categories.tags` JSONB and
`paywall_dismissals` partial-index patterns are good models. Build: net-new
tables. The 12 locked decks become seed data via either (a) Alembic data
migration, (b) `scripts/seed_phase6_decks.py`, or (c) a one-time admin
import. No in-repo seed-data convention today; lock it. **Dependency
missed:** slice 6.0 events table (if chosen) might want to FK on
`quiz_item_id`, so the FK target needs to exist first — slice 6.1 → 6.0
ordering, not the other way around.

**Slice 6.2 — FSRS binding to quiz_item only (not lesson).** Foundation:
`card_progress` already binds `(user_id, card_id)` via FSRS. Direct
analog: `(user_id, quiz_item_id)` with the same column shape. Build:
new `quiz_item_progress` table (or refactor `card_progress` into
`quiz_item_progress`, dropping the legacy `cards` foreign key). The
locked decision "substantive lesson edits don't reset FSRS state;
substantive quiz_item edits retire the old quiz_item and create a new
one" matches the existing pattern of soft-delete via `deleted_at` —
extend.

**Slice 6.3 — lesson-card UX.** Foundation: `FlipCard`, `QuizPanel`,
`DailyReview` patterns are mature. Build: net-new lesson-page
component (concept_md / production_md / examples_md / quiz panel),
plus the four-section layout. **Dependency missed:** slice 6.4 (admin
authoring UI) probably wants to ship before 6.3 so there's content to
render; or 6.3 ships against fixture data first.

**Slice 6.4 — admin authoring UI for decks / lessons / quiz_items.**
Foundation: `pages/AdminPanel.tsx` exists; `Depends(require_admin)` +
`audit_admin_request` are mature. Build: AdminPanel.tsx is already 868
lines — strongly recommend splitting into a multi-route shell BEFORE
adding deck/lesson surface. `react-hook-form` is installed but unused;
this is the slice to start consuming it. **Dependency missed:** slice
6.1 schema must land first.

**Slice 6.5 — three-layer quality system: cross-model critique
pre-publish + admin spot-check + user thumbs feedback, all stored in
`card_quality_signals` keyed by `(lesson_id, signal_source, dimension)`.**
Foundation: `card_feedback` table is the user-thumbs analog (today scoped
to `card_id`; quality-signal table needs `lesson_id` and a wider key).
Build: net-new table; new BE endpoint for admin spot-check; new ingestion
critique writer. **Dependency missed:** the locked decision says signals
are keyed by `(lesson_id, signal_source, dimension)` but `quiz_item`-level
critique is more granular than lesson-level — confirm intent before spec
drafting; either critique aggregates to lesson, or the key needs to
include `quiz_item_id` for the AI-critique branch.

**Slice 6.6 — Lens-ranked deck/card ordering for Interview Prepper.**
Foundation: `nlp.extract_job_requirements` returns structured skills;
`gap_mapping_service` already maps gaps to categories; `gap_detector`
classifies importance. Build: ranker that joins user's most-recent N
scans → skill-gap-set → quiz_item / lesson scoring. **Dependency
missed:** there's no aggregated "this user's recent skill gaps" service
helper. Spec it explicitly. Cold-start for Pro-no-scan users falls
back to Study Board per locked decision — confirm.

**Slice 6.7 — Climber persona free pick / Interview Prepper Lens-ranked
+ Study Board fallback.** Foundation: persona model healthy; HomeDashboard
already branches three ways; StudyDashboard already reads `?source=last_scan`
via spec #62. Build: new Learn-page composition that mounts ranker output
for Interview Prepper + free-grid for Climber. Reuses
`StudyDashboard.tsx` patterns.

**Slice 6.8 — Pro-only daily digest emails.**
*(See top-of-section drift notice — slice 6.8 is now FSRS dashboard
[B-080 ✅, spec `docs/specs/phase-6/09-fsrs-dashboard.md`]; this
entry's framing applies to current slice 6.14 [B-078 🟦].)*
Foundation:
Resend wrapper + `reminder_service` pattern. Build: digest assembly
(top quiz_items due, retention summary, persona-tailored), Pro-user
selector query, opt-out flag, dedup via `email_log` (NEW TABLE — see
§5.4). **Dependency missed:** in-repo cron entry point. Either inherit
the same Railway-config-only path as `send_daily_reminders` or introduce
a scheduler — and that's a separate decision than the digest itself.

**Slice 6.9 — Edit-classification rule (>15% char delta on
concept_md/production_md/examples_md OR any quiz_item question/answer
change = substantive).** Foundation: none — this is pure logic. Build: a
`classify_lesson_edit(old, new)` pure function + DB trigger or service
hook. The locked decision is precise; spec it as a single deterministic
function with explicit boundary tests.

**Slice 6.10 — AI ingestion pipeline (Gemini generate, cross-model
critique).** Foundation: `llm_router.generate_for_task` mature; admin
patterns mature; rate limits via slowapi mature. Build: ingestion
orchestrator (multi-step, retry-prone), provider override for the
critique pass, prompt-template registry (probably new), durable
job storage. **Dependency missed:** background-job system —
`BackgroundTasks` is not enough. This is a hard prereq, not a
nice-to-have.

**Slice 6.11 — FSRS retention dashboard (admin or user-self).**
Foundation: `pages/AdminAnalytics.tsx` Postgres-aggregate pattern; the
six-OKR + 7d/30d delta machinery in `admin_analytics_service.py` is
ready to copy. Build: retention metrics (recall rate, lapse rate per
deck, time-to-due percentiles). **Dependency missed:** if events go
PostHog-only (slice 6.0 decision), this dashboard needs HogQL — which
spec #38 explicitly forbade. Lock the events-table-vs-PostHog decision
before drafting this slice.

**Slice 6.12 — persona-aware Learn page composition.** Subsumes much of
slice 6.7's logic; consider folding 6.7 + 6.12 into one slice unless
there's reason to ship Climber free-pick first.

**Slice 6.13 — Pro daily digest opt-out + email_log.** Already covered
under 6.8. May be a separate slice for surface-area reasons (email-prefs
UI + table + dedup) — fine.

**Slice 6.14 — daily digest cron entry point.**
*(See top-of-section drift notice — slice 6.14 is now daily Pro
digest + cron architecture decision [B-078 🟦, spec #14 unauthored];
this entry's framing is consolidated into the same current slice
6.14, which absorbed the scout's slice 6.8 daily-digest framing.)*
Same as 6.8's missed
dependency. Either pull this earlier (foundation) or roll into 6.8.

**Slice 6.15 — Phase-6 cleanup (drop legacy `/api/*` mounts,
`navbar.tsx`, `GuidedTour.tsx`, `ResumePDFTemplate.tsx`,
`ai_service.py`, `app/services/llm/`, transitional `<Navigate>` block,
`users.interview_target_*` columns post-E-042 FE, etc.).** Foundation:
all of these are individually tracked (B-010, CODE-REALITY §9, §11).
Build: low-risk deletes plus telemetry-driven decisions on the
transitional redirects (B-008 ungated today). Recommend doing this
LAST.

**Slice 6.16 — FSRS retention dashboard finalization.** Same as 6.11.

**Slices not numbered above (6.x extras to reach 19):** likely some
combination of analytics-event additions per slice, edit-history
table, content-versioning, deck-card cover image upload (which surfaces
the no-object-storage finding), or per-deck pricing tiers. Without the
exact 19-slice list, I can't audit each individually — see Open
Questions.

---

## Recommendations for spec drafting

**R-1.** Create `docs/specs/phase-6/` as part of the first Phase 6
spec-author slice (NOT this audit slice). The first spec authored should
be slice 6.1 (schema) so subsequent specs can cross-ref live tables.

**R-2.** Lock the "Lens → recent-skill-gaps" service-helper shape
BEFORE slice 6.6 spec. Two options sketched in §2.4 (aggregated
read vs materialized table). Default to (A) aggregated read for
simpler write-side; revisit if read latency becomes a problem post-launch.

**R-3.** Lock the slice-6.0 "events go PostHog-only or also Postgres?"
decision BEFORE specs 6.0 and 6.16 draft. The retention-dashboard slice
depends on it. Recommendation: dual-write (PostHog for funnels,
Postgres `quiz_review_events` for the dashboard), trading storage cost
for HogQL avoidance.

**R-4.** Slice 6.4 (admin authoring UI) should start with a refactor
half: split `AdminPanel.tsx` into a multi-route admin shell at
`/admin/cards`, `/admin/decks`, `/admin/lessons`, `/admin/quiz-items`,
`/admin/critique-runs`. Adding 4+ tabs to an 868-line file is debt-by-design.

**R-5.** Slice 6.10 (ingestion) MUST be preceded by a
background-job-system selection slice. Recommendation: **RQ on Redis**
(Redis is already a hard dep). Alternative: **APScheduler** if we want
to keep everything in-process. Either is significantly less surgery
than full Celery.

**R-6.** For cross-model critique (slice 6.10): extend
`generate_for_task` with `provider_override: str | None = None` so a
single ingestion job can call Gemini for generation and Claude for
critique without flipping the global `LLM_REASONING_PROVIDER` env var.
Today's pattern would force a hot env-var swap mid-job, which is
fragile.

**R-7.** Phase-6 specs should follow the existing template (`docs/specs/phase-N/NN-name.md`)
and use the heading-2 `## Status:` form (not the bolded
`**Status:**`) per CODE-REALITY §13's standardization recommendation.

**R-8.** Slice 6.15 (cleanup) should run LAST and consume telemetry
from B-008's `deprecated_route_hit` event (also a Phase-6 cleanup
target). Order: ship the telemetry, soak for at least one full release
cycle, then drop the redirects.

**R-9.** For slice 6.5 (three-layer quality), confirm whether
`card_quality_signals` keys on `lesson_id` exclusively (locked decision
text) or if AI-critique signals at the quiz_item level need a
`quiz_item_id` discriminator. Lesson-level critique aggregation is
weaker but the locked decision is explicit. Defer to Dhamo before
spec drafts.

**R-10.** Lock the file-storage decision (R2 vs S3 vs no-storage) early
in Phase 6. If the 12 locked decks ship with seed Markdown files, those
can live in `app/data/decks/` for v0; longer term, ingestion-job
artifacts (generated lesson Markdown, critique reports) want durable
storage.

---

## Open questions for Dhamo

**Q1.** **Is Phase 6's `card_quality_signals` keyed on `lesson_id`
only, or does it need `quiz_item_id` for AI-critique granularity?**
Locked decision says lesson_id; cross-model critique fits more naturally
at the quiz_item level. Resolve before slice 6.5 spec.

**Q2.** **Where do quiz/review events live for the slice 6.16 retention
dashboard — PostHog only, Postgres only, or both?** Spec #38 banned
the PostHog Query API for `/admin/analytics`; if 6.16 reuses that
constraint, Postgres is forced. If 6.16 can use HogQL, no new table
needed. Resolve before slice 6.0 spec.

**Q3.** **Background-job system: RQ, APScheduler, or in-process
`BackgroundTasks` only?** Affects slices 6.8, 6.10, 6.14. Recommend RQ.

**Q4.** **Does file storage land in Phase 6 (R2/S3) or stay in-memory
+ on-disk under `app/data/`?** Affects ingestion artifacts and any
seed-Markdown deck content.

**Q5.** **Is the daily Pro digest scheduled via the same external
Railway cron as `send_daily_reminders`, or does Phase 6 introduce an
in-repo scheduler?** Affects slice 6.14 spec scope.

**Q6.** **Slice 6.7 (Climber free pick / IP Lens-ranked) and slice 6.12
(persona-aware Learn page composition) read like the same slice. Should
they be merged, or is there a sequencing reason (e.g. Climber free-pick
ships first behind a flag)?**

**Q7.** **Cold-start behavior for an Interview Prepper Pro user with no
Lens scan: does the Learn page render the Study Board (locked decision
fallback) or surface a "scan first" prompt?** Implicit but not stated.

**Q8.** **Seed data for the 12 locked decks: Alembic data migration,
admin bulk-import CSV, or a one-time `scripts/seed_phase6_decks.py`?**
No in-repo seed convention exists today.

**Q9.** **R17 watermark — the prompt cited B-052 from memory; on disk
the highest BACKLOG ID is B-060.** Does this affect any other recently-drafted
prompts that pre-allocated post-B-052 IDs? Not blocking this slice (audit-only)
but worth a sweep.

**Q10.** **`docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md` exists
on disk but is not committed to git** (it's in the same untracked set
as this new file will be in pre-commit). Is the prior audit
intentionally untracked, or was the commit deferred? This audit will
be committed as part of this slice; the prior audit's commit status
is Dhamo's call.

---

*End of audit. Generated 2026-04-26 22:29 UTC at HEAD `83dd03b`. All file
path references verified against disk at audit time. No code changes,
no spec authoring, no schema migrations, no BACKLOG row creation
performed in this slice.*
