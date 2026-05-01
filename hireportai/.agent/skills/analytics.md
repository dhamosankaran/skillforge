---
description: PostHog event catalog (frontend + backend), funnels, conventions
---
# Analytics Skill

## Overview
PostHog is instrumented from Phase 1 and runs on both tiers:
- **Frontend:** `src/utils/posthog.ts` wraps `posthog-js` with a
  `capture(event, properties)` helper. Initialized in `main.tsx`
  using `VITE_POSTHOG_KEY` + `VITE_POSTHOG_HOST`.
- **Backend:** `app/core/analytics.py` exposes `track(user_id,
  event, properties=None)`. Silent no-op when `POSTHOG_API_KEY` is
  unset so dev/CI stay quiet.

## Conventions
- `snake_case` event names, always.
- Properties are a flat dict of primitives; avoid nested objects.
- Frontend auto-identifies on login via PostHog identify.
- Backend events always pass `user_id` explicitly as the first arg.
- Every user-facing feature **must** fire an event (see CLAUDE.md rule 8).
- Events marked **(DEPRECATED `<slice>`)** stopped firing at the given
  commit but are preserved in this catalog for historical PostHog data
  and dashboard cross-reference. Do not remove — deprecate, don't rename.

## Complete Event Catalog

### Frontend events (`src/**/*.tsx`)

| Event | Source file | Properties |
|-------|-------------|-----------|
| `landing_page_viewed` | `pages/LandingPage.tsx` | — |
| `cta_clicked` | `pages/LandingPage.tsx` | `{button: 'hero' \| 'how_it_works' \| 'pricing'}` |
| `persona_picker_shown` | `pages/PersonaPicker.tsx` | `{is_new_user: boolean}` |
| `persona_selected` | `pages/PersonaPicker.tsx` | `{persona, has_target_date, has_target_company}` |
| `onboarding_started` | `pages/Onboarding.tsx` | `{persona}` |
| `onboarding_completed` | `pages/Onboarding.tsx` | `{persona, cards_count, skill_gaps}` |
| `onboarding_tour_completed` | `components/GuidedTour.tsx` | — |
| `onboarding_tour_skipped` | `components/GuidedTour.tsx` | — |
| `gap_card_clicked` | `pages/Onboarding.tsx` | `{gap_id, gap_name}` |
| `gap_study_clicked` **(DEPRECATED P5-S22b)** | `components/dashboard/MissingSkillsPanel.tsx` | `{gap_name, category_id, user_plan}` — replaced by `missing_skills_cta_clicked` (see below). No longer fires after commit `fd4ca3d`. |
| `paywall_hit` | `components/PaywallModal.tsx`, `pages/Analyze.tsx` | `{trigger, category_name?, cards_viewed?, surface?: 'analyze_page_load', plan?: 'free'}` — `surface` and `plan` are additive optional props introduced by spec #60 / B-045 for the `/prep/analyze` pre-flight gate (fires on gate-card mount, not modal-open). PaywallModal mount path omits `surface` (existing behavior preserved). |
| `optimize_clicked` | `pages/Results.tsx` | `{plan: 'free' \| 'pro'}` — fires on both header "Optimize" and sidebar "AI Rewrite" buttons; free users see the paywall (trigger=`rewrite_limit`), Pro users navigate to `/prep/rewrite` (B-032) |
| `checkout_started` | `components/PaywallModal.tsx` | `{trigger, plan, price, currency}` |
| `payment_completed` | `pages/Pricing.tsx` | `{plan, price, currency, source: 'stripe_checkout_return'}` |
| `theme_changed` | `context/ThemeContext.tsx` | `{from_theme, to_theme}` |
| `study_dashboard_viewed` | `pages/StudyDashboard.tsx` | `{category_count, locked_count}` |
| `category_tile_clicked` | `pages/StudyDashboard.tsx` | `{category_id, category_name}` |
| `locked_tile_clicked` | `pages/StudyDashboard.tsx` | `{category_id, category_name}` |
| `category_detail_viewed` | `pages/CategoryDetail.tsx` | `{category_id, category_name, cards_count}` |
| `card_viewed` | `pages/CardViewer.tsx` | `{card_id, card_number, total_cards}` |
| `quiz_submitted` | `components/study/QuizPanel.tsx` | `{card_id, answer, correct}` |
| `card_feedback_submitted` | `components/study/QuizPanel.tsx` | `{card_id, vote, has_comment}` / `{card_id, vote, comment}` |
| `daily_review_started` | `pages/DailyReview.tsx` | `{cards_due, streak_day}` |
| `daily_review_completed` | `pages/DailyReview.tsx` | `{cards_reviewed, new_best_streak}` |
| `mission_created` | `pages/MissionMode.tsx` | `{interview_date, days_remaining}` |
| `mission_completed` | `pages/MissionMode.tsx` | `{mission_id, total_days, cards_studied}` |
| `mission_day_completed` | `pages/MissionMode.tsx` | `{day, cards_studied, streak_day}` |
| `streak_incremented` | `context/GamificationContext.tsx` | `{streak_day, category_id}` |
| `badge_earned` | `context/GamificationContext.tsx` | `{badge_id, badge_name}` |
| `profile_viewed` | `pages/Profile.tsx` | — |
| `experience_generated` | `pages/Profile.tsx` | `{topic, cards_studied_count}` |
| `subscription_portal_opened` | `pages/Profile.tsx` | — — fires on "Manage subscription" click before the Stripe-portal redirect (P5-S26b, spec #36). |
| `checklist_shown` | `components/home/widgets/InterviewPrepperChecklist.tsx` | `{complete_count, all_complete}` — fires once per mount when the Interview-Prepper checklist renders (P5-S18c, spec #41). |
| `checklist_step_clicked` | `components/home/widgets/InterviewPrepperChecklist.tsx` | `{step_id}` — fires on each step row click (spec #41). |
| `checklist_completed` | `components/home/widgets/InterviewPrepperChecklist.tsx` | `{completed_at}` — fires once when all 5 steps flip to complete (spec #41). |
| `checklist_skipped` | `components/home/widgets/InterviewPrepperChecklist.tsx` | `{complete_count}` — fires on "Skip checklist" click (spec #41). |
| `email_preferences_viewed` | `pages/EmailPreferences.tsx` | — |
| `email_preferences_saved` | `pages/EmailPreferences.tsx` | `{daily_reminder}` / `{timezone}` |
| `nav_clicked` | `components/layout/TopNav.tsx`, `components/layout/MobileNav.tsx` | `{namespace: 'home'\|'learn'\|'prep'\|'profile'\|'admin', from_path, to_path}` |
| `sign_out_clicked` | `components/layout/UserMenu.tsx`, `pages/Profile.tsx` | `{source: 'topnav_avatar' \| 'profile_page'}` — fires before `AuthContext.signOut()` runs so the event still captures even though `signOut` redirects to `/` on completion (B-028). |
| `home_dashboard_viewed` | `pages/HomeDashboard.tsx` | `{persona: 'interview_prepper'\|'career_climber'\|'team_lead'}` — fires once on mount via `useRef` idempotency guard so Strict Mode's double-invoked effect captures once (P5-S18). |
| `home_state_evaluated` | `hooks/useHomeState.ts` | `{persona, states: string[], state_count, cache_hit}` — fires once per resolved fetch; deduped by fingerprint of `persona\|states` so refetch-with-same-result doesn't re-fire (P5-S18c). |
| `home_state_widget_clicked` | `components/home/widgets/{StreakAtRisk,MissionActive,MissionOverdue,ResumeStale,InactiveReturner,FirstSessionDone}Widget.tsx` | `{state, cta}` — fires on the priority-slot widget's CTA click, alongside the route navigation (P5-S18c). Spec #61 §6 amends `ResumeStaleWidget` for free users: `cta: 'paywall'` value added when the widget routes the click to PaywallModal instead of `/prep/analyze` (avoids spec #56 lifetime-cap dead-end). |
| `home_study_gaps_prompt_shown` | `components/home/widgets/StudyGapsPromptWidget.tsx` | `{plan: 'free', persona: 'interview_prepper'\|'career_climber'\|'team_lead'\|null}` — fires once per mount via `useRef` idempotency guard (matches `home_dashboard_viewed` / `paywall_hit` convention) when StudyGapsPromptWidget eligibility resolves true (spec #61 §4 / B-051; closes E-048 fix-half). |
| `home_study_gaps_clicked` | `components/home/widgets/StudyGapsPromptWidget.tsx` | `{plan: 'free', persona, cta: 'primary' \| 'secondary_upgrade'}` — fires on primary CTA click (before navigating to `/learn?source=last_scan`) or secondary CTA click (before opening PaywallModal `trigger='skill_gap_study'`). The `secondary_upgrade` enum value preserves the visual-hierarchy intent in the property name; future hero/inline upgrade CTAs will use distinct enum values without property migration (spec #61 §11 / LD-Q5; B-051). |
| `study_dashboard_source_hint_shown` | `pages/StudyDashboard.tsx` | `{source: 'last_scan', persona, copy_variant: '6A'}` — fires once per StudyDashboard mount via `useRef` idempotency guard when the URL has `?source=last_scan` (matches `home_dashboard_viewed` convention). `copy_variant` records which §6 copy choice the impl shipped (locked to `'6A'` neutral per spec #62 §10 OQ-1; future variants would carry `'6B'` / `'6C'`). Does NOT re-fire on banner dismiss (component-state change). Spec #62 §7 / B-053 closes B-052 (`?source=last_scan` consumer follow-up from spec #61 LD-11). |
| `first_action_viewed` | `pages/FirstAction.tsx` | `{persona}` — fires once per mount via `useRef` idempotency guard; bypassed when the `first_action_seen` localStorage flag is already set (P5-S22, spec #46). |
| `first_action_primary_clicked` | `pages/FirstAction.tsx` | `{persona, cta_route}` — fires on primary CTA click before navigation (spec #46). |
| `first_action_secondary_clicked` | `pages/FirstAction.tsx` | `{persona}` — fires on "Take me to the dashboard instead" click before navigation (spec #46). |
| `interview_target_date_added` | `pages/PersonaPicker.tsx` | `{source: 'onboarding' \| 'persona_edit'}` — fires in PersonaPicker `handleContinue` when `selected === 'interview_prepper'` and a non-empty `targetDate` is being saved (spec #53). **CountdownWidget call site retired in spec #57** — date capture moved to the tracker row editor; see `tracker_interview_date_set`. The PersonaPicker call site is removed in the follow-up UI cleanup slice that strips the Interview-Prepper expansion block (spec #57 §6.1 / §7.2). |
| `interview_target_date_skipped` | `pages/PersonaPicker.tsx` | `{source: 'onboarding'}` — fires in `handleContinue` when `selected === 'interview_prepper'` and `targetDate` is empty. Signals the "broadly prepping, no specific interview" cohort. Never blocks or delays submission (spec #53). **Removed in the follow-up UI cleanup slice** that strips PersonaPicker's date capture (spec #57 §7.2). |
| `countdown_unlock_cta_shown` | `components/mission/MissionDateGate.tsx` | `{surface: 'mission_mode'}` — fires once per mount of the no-date unlock affordance on `/learn/mission` via `useRef` idempotency guard (same convention as `home_dashboard_viewed`, spec #53). **Spec #57 §7.3 preserved-event:** still fires from MissionDateGate; CountdownWidget call site retired (date capture moved to the tracker row editor — see `countdown_widget_rendered` / `countdown_widget_add_date_cta_clicked`). |
| `countdown_unlock_cta_clicked` | `components/mission/MissionDateGate.tsx` | `{surface: 'mission_mode'}` — fires on primary unlock-CTA button click before navigating to `/prep/tracker?new=1` (spec #53 + spec #57 AC-6 amended target). Spec #57 §7.3 preserved-event. |
| `countdown_widget_rendered` | `components/home/widgets/CountdownWidget.tsx` | `{has_date: boolean, days_until?: number}` — fires once per mount via `useRef` idempotency guard. `days_until` is present only when `has_date === true` (spec #57 §7.1). |
| `countdown_widget_add_date_cta_clicked` | `components/home/widgets/CountdownWidget.tsx`, `components/mission/MissionDateGate.tsx` | `{source: 'home' \| 'mission_gate'}` — fires on the "Add your interview date" / "Set a date to start a sprint" CTA before navigating to `/prep/tracker?new=1` (spec #57 §7.1). |
| `tracker_interview_date_set` | `pages/Tracker.tsx` | `{tracker_id: string, days_until: number, source: 'create' \| 'edit'}` — fires when the Tracker row editor successfully writes an `interview_date` via `POST` (`source='create'`) or `PATCH` (`source='edit'`). `days_until` is the integer days between `today` and the saved date (≥ 0). Spec #57 §7.1. The `source='backfill'` enum value is reserved for the BE migration data step (event-name-only mirror; not fired from FE). |
| `tracker_interview_date_cleared` | `pages/Tracker.tsx` | `{tracker_id: string}` — fires when the Tracker row editor PATCHes `interview_date: null` (explicit clear). Spec #57 §7.1. |
| `interview_questions_cached_served` | `pages/Interview.tsx` | `{jd_hash_prefix, generated_at_age_hours}` — fires once per cached set surfaced (deduped by `generated_at`); `jd_hash_prefix` is the first 8 hex chars of the same SHA-256-of-normalized-JD the backend uses for `(user_id, jd_hash)` keying so we can correlate without leaking the JD (5.17b, spec #49). |
| `interview_questions_regenerated` | `pages/Interview.tsx` | `{from_free_tier: bool, remaining_free_quota?: number}` — fires when the user confirms the Regenerate Questions CTA; `remaining_free_quota` only present when a prior 403 has populated `limitInfo` (5.17b, spec #49). |
| `results_tooltip_opened` | `components/dashboard/PanelSection.tsx` (mounted by `pages/Results.tsx`) | `{section: 'ats_score' \| 'score_breakdown' \| 'job_fit' \| 'keywords' \| 'skills_radar' \| 'bullets' \| 'missing_skills' \| 'formatting' \| 'improvements'}` — fires on each open of a section info-icon tooltip on `/prep/results`. Does NOT fire on close; open-count is the signal. `section` is passed by the Results page as a prop to `PanelSection`; if absent (non-Results callers), the event does not fire (P5-S21b, spec #21). |
| `job_fit_explanation_viewed` | `pages/Results.tsx` | `{view_position: 'above_fold'}` — fires once per mount via `useRef` idempotency guard when Analysis Results renders with a loaded `result` (matches `home_dashboard_viewed` / `first_action_viewed` convention). `view_position` is fixed at `"above_fold"` after P5-S20; leaves headroom for a scroll-triggered or below-fold variant without needing a new event name (P5-S20, BACKLOG E-009). |
| `re_analyze_clicked` | `pages/Results.tsx` | `{plan: 'free' \| 'pro'}` — fires on every Re-analyze button click on `/prep/results`, before the plan gate resolves, so both blocked (free → paywall) and allowed (pro → navigate) clicks are counted (spec #55, B-030). |
| `free_scan_cap_hit` | `hooks/useAnalysis.ts` | `{attempted_action: 'initial' \| 'reanalyze', scans_used_at_hit: int}` — fires when a free user's Analyze submit is blocked by the 1-lifetime cap (spec #56 / B-031). Fires on both the client-side pre-gate (`canScan===false`) and the BE 402 response — whichever catches first. `scans_used_at_hit` is the server-authoritative count from the 402 `detail.scans_used` when the event comes from the BE path; from the BE-hydrated `usage.scansUsed` on the client-side pre-gate. `attempted_action` is `'initial'` from `/prep/analyze`; the `'reanalyze'` branch is reserved for future surfaces that also route into `useAnalysis.runAnalysis`. |
| `daily_card_wall_hit` | `components/study/QuizPanel.tsx` (submit-time) + `components/study/DailyReviewWalledView.tsx` (page-load, spec #63 / B-059) | `{resets_at_hours_from_now: int, surface: "daily_review_submit" \| "daily_review_page_load"}` — fires when the daily-card wall surfaces, either as the modal opens on a 402 response (`surface="daily_review_submit"`, spec #50 P5-S22-WALL) or when the pre-flight gate renders the full-page upsell on `/learn/daily` mount (`surface="daily_review_page_load"`, spec #63 / B-059). `resets_at_hours_from_now` is the integer hours between now and the server-provided `resets_at` ISO timestamp, rounded toward zero. Submit-time fires re-open-on-each-modal (matches `paywall_hit` convention in `PaywallModal.tsx:78`); page-load fires once per mount via `useRef` idempotency guard (mirrors `paywall_hit` from spec #60 / B-045). |
| `missing_skills_cta_clicked` | `components/dashboard/MissingSkillsPanel.tsx` | `{plan: 'anonymous'\|'free'\|'pro', skill: string, category_id: string\|null}` — fires on each Missing Skills CTA click on `/prep/results` (spec #22, P5-S22b). `category_id` is the resolved `matching_categories[0].category_id` from the first `GapMapping` whose gap matches the skill case-insensitively with `match_type !== 'none'`, else `null`. Disabled CTAs do not fire. Replaces the deprecated `gap_study_clicked` event (see Deprecated Frontend Events below). |
| `admin_analytics_segment_changed` | `pages/AdminAnalytics.tsx` | `{segment: '7d' \| '30d' \| '90d' \| 'YTD'}` — fires on every segment change of the date-range control at `/admin/analytics`, including the initial default-value mount (so the first-view segment is also captured). Admin-only surface; the backend `admin_analytics_viewed` event captures the API-side counterpart via the `audit_admin_request` side-fire (spec #38 E-018b slice 2/4). |
| `admin_content_quality_viewed` | `pages/admin/AdminContentQuality.tsx` | `{admin_id, window_days, include_archived, internal: true}` — fires once-per-mount via `useRef` idempotency guard when the admin content-quality dashboard renders (Phase 6 slice 6.11, spec #11 D-11 / B-084). Mirrors slice 6.8 D-11 `dashboard_viewed` once-per-mount + slice 6.10 D-13 admin-internal convention. NO BE side-fire extension to `audit_admin_request` — the FE event already carries window/archived params the BE side-fire would not. |
| `scan_rehydrated` | `pages/Results.tsx` | `{scan_id: string}` — fires after `GET /api/v1/analyze/{scan_id}` returns 200 and the hydration effect dispatches `SET_RESULT` (spec #59 §12). Keys the "Last Scan widget → View results" re-entry funnel. `scan_age_days` was scoped in the spec but deferred — requires adding `scan_created_at` to `AnalysisResponse` (spec §17 open question). |
| `scan_rehydrate_failed` | `pages/Results.tsx` | `{scan_id: string, reason: 'legacy' \| 'not_found' \| 'error', http_status: int}` — fires when hydration fails. `reason='legacy'` (410) = scan predates spec #59 persistence; `'not_found'` (404) = unknown or non-owner (LD-4 — never 403); `'error'` = network / 5xx. `http_status=0` for network errors without a response. Pairs with `scan_rehydrated` to measure hydration success rate per entry surface. |

> **P5-S14 note (deprecated_route_hit):** the navigation-restructure spec (`docs/specs/phase-5/12-navigation-restructure.md` §Analytics) also defines a transitional `deprecated_route_hit` event to fire from each `<Navigate>` node in `src/App.tsx`'s redirect block. It is **not currently wired** (P5-S13 landed the redirect block without it). If we want to measure when the old paths stop receiving hits before dropping the block in Phase 6, we need to backfill — out of scope for P5-S14, flagged here as a P5-S13 gap.

#### Deprecated Frontend Events

Preserved for historical PostHog data cross-reference. Source files no longer exist in the repo.

| Event | Source file (deleted) | Properties |
|-------|-----------------------|-----------|
| `persona_changed` **(DEPRECATED P5-S17)** | `components/PersonaPicker.tsx` | `{from, to}` |
| `onboarding_persona_selected` **(DEPRECATED P5-S17)** | `components/PersonaPicker.tsx` | `{persona, mode: 'onboarding'}` |

> **`persona_changed` (DEPRECATED P5-S17, commit b5f42c2 — source component deleted; historical PostHog data preserved. Replaced by `persona_selected`.)**

> **`onboarding_persona_selected` (DEPRECATED P5-S17, commit b5f42c2 — source component deleted; historical PostHog data preserved. Replaced by `persona_selected`. Referenced by `docs/specs/phase-4/24-posthog-dashboards.md` event #13 — update that spec in a separate slice if dashboard is decommissioned.)**

> **`gap_study_clicked` (DEPRECATED P5-S22b, commit `fd4ca3d` — source component (`components/dashboard/MissingSkillsPanel.tsx`) still exists but no longer emits this event. Replaced by `missing_skills_cta_clicked` with a three-state `plan` prop (anonymous / free / pro) per spec #22.)**

### Backend events (`app/**/*.py`)

| Event | Source file | Properties |
|-------|-------------|-----------|
| `ats_scanned` | `app/services/analysis_service.py` (`score_resume_against_jd`) | `{score: int, grade: str, gaps_found: int, matched_keywords: int, missing_keywords: int}` — fires once per scoring call from inside the G-6 helper, so both `/analyze` (file-upload entry) and `/rescan` (text-input entry, B-086b) emit. Payload reconciled to helper's actual emission per spec #63 §16.3 R-3 (B-088 catalog reconciliation). |
| `tracker_auto_created_from_scan` | `app/api/routes/analyze.py` | `{user_id, company, role, matched_skills}` |
| `resume_rewrite_generated` | `app/api/routes/rewrite.py` | `{resume_chars, missing_keywords_count, template_type}` |
| `rewrite_limit_hit` | `app/api/routes/rewrite.py` | `{attempted_action: 'full' \| 'section', plan: 'free', auth_status: 'authed'}` — fires on the 402 path before the `free_tier_limit` envelope is raised for the `rewrite_limit` trigger (spec #58 §8). `attempted_action='full'` from `POST /rewrite`; `'section'` from `POST /rewrite/section`. Both share the `"rewrite"` usage bucket per spec #58 §4.1 Option (a); `attempted_action` preserves funnel granularity without a second PLAN_LIMITS key. |
| `cover_letter_succeeded` | `app/api/routes/cover_letter.py` | `{tone, body_paragraphs_count, model_used}` — fires on 200 after the structured response passes Pydantic validation (spec #52 §9, B-002). |
| `cover_letter_failed` | `app/api/routes/cover_letter.py` | `{error_code, tone}` where `error_code ∈ {cover_letter_truncated, cover_letter_parse_error, cover_letter_validation_error, cover_letter_llm_error}` — fires on the 502 path before the HTTP error is raised (spec #52 §9, B-002). |
| `cover_letter_limit_hit` | `app/api/routes/cover_letter.py` | `{plan: 'free', auth_status: 'authed'}` — fires on the 402 path before the `free_tier_limit` envelope is raised for the `cover_letter_limit` trigger (spec #58 §8). Separate bucket from rewrite; no `attempted_action` (single entry point). |
| `experience_generated` | `app/services/experience_service.py` | `{user_id, word_count}` |
| `card_reviewed` | `app/services/study_service.py` | `{user_id, card_id, rating, ease_factor, interval_days}` |
| `mission_created` | `app/services/mission_service.py` | `{user_id, mission_id, categories, target_date}` |
| `mission_completed` | `app/services/mission_service.py` | `{user_id, mission_id, total_cards, completed_cards, coverage_pct}` |
| `mission_day_completed` | `app/services/mission_service.py` | `{user_id, mission_id, day_number, cards_completed}` |
| `streak_incremented` | `app/services/gamification_service.py` | `{user_id, current_streak}` |
| `streak_broken` | `app/services/gamification_service.py` | `{user_id}` |
| `xp_awarded` | `app/services/gamification_service.py` | `{user_id, xp, source}` |
| `badge_earned` | `app/services/gamification_service.py` | `{user_id, badge_id}` |
| `checkout_started` | `app/services/payment_service.py` | `{user_id, price_id, plan}` |
| `payment_completed` | `app/services/payment_service.py` (webhook) | `{user_id, plan, amount_total, currency}` |
| `subscription_cancelled` | `app/services/payment_service.py` (webhook) | `{user_id, plan}` |
| `registration_blocked` | `app/api/v1/routes/auth.py` | `{ip_hash, existing_accounts}` |
| `admin_role_reconciled` | `app/api/v1/routes/auth.py` | `{email, prior_role, new_role, action: 'promoted'\|'demoted'\|'unchanged'}` — fires on every `POST /api/v1/auth/google` after login-time whitelist reconciliation (spec #54 / E-040). `unchanged` fires too as a heartbeat so dashboards can alert on sudden absence. Promotion and demotion additionally write an `admin_audit_log` row; `unchanged` does not. |
| `admin_card_draft_generated` | `app/api/v1/routes/admin.py` | `{admin_id, category, tokens}` |
| `admin_analytics_viewed` | `app/core/deps.py` (`audit_admin_request`) | `{admin_id, internal: true, path}` — fires from the router-level `audit_admin_request` dep whenever the request path starts with `/api/v1/admin/analytics`. **Live as of E-018b** (Slice 2, 2026-04-23) — first firings come from `GET /api/v1/admin/analytics/metrics` and `/performance`; Slices 3 + 4 extend to `/behavior`, `/signals`, `/themes` (spec #38 AC-8). |
| `admin_deck_created` | `app/services/deck_admin_service.py` | `{admin_id, deck_id, slug, persona_visibility, tier, internal: true}` — fires at end of successful `POST /api/v1/admin/decks` transaction. (Slice 6.4b — B-065.) |
| `admin_deck_updated` | `app/services/deck_admin_service.py` | `{admin_id, deck_id, fields_changed: list[str], persona_visibility_narrowed: bool, internal: true}` — fires at end of successful `PATCH /api/v1/admin/decks/{id}` transaction. (Slice 6.4b — B-065.) |
| `admin_deck_archived` | `app/services/deck_admin_service.py` | `{admin_id, deck_id, slug, internal: true}` — fires only on the NULL → non-NULL transition; idempotent re-archive emits no event. (Slice 6.4b — B-065.) |
| `admin_deck_persona_narrowed` | `app/services/deck_admin_service.py` | `{admin_id, deck_id, removed_personas: list[str], before_count: int, after_count: int, internal: true}` — fires only on the narrowing branch of `PATCH /api/v1/admin/decks/{id}` (one or more personas removed from `decks.persona_visibility`). Per spec #04 §12 D-19. (Slice 6.4b — B-065.) |
| `admin_lesson_created` | `app/services/lesson_admin_service.py` | `{admin_id, lesson_id, deck_id, slug, internal: true}` — end of successful `POST /api/v1/admin/decks/{deck_id}/lessons` transaction. (Slice 6.4b — B-065.) |
| `admin_lesson_updated_minor` | `app/services/lesson_admin_service.py` | `{admin_id, lesson_id, deck_id, version: int, fields_changed: list[str], internal: true}` — fires on the **minor** branch of `PATCH /api/v1/admin/lessons/{id}` only. The substantive branch fires `admin_lesson_substantively_edited` instead. (Slice 6.4b — B-065.) |
| `admin_lesson_substantively_edited` | `app/services/lesson_admin_service.py` | `{admin_id, lesson_id, deck_id, version: int, prior_version: int, quiz_items_retired_count: int, quiz_items_retired_ids: list[str], internal: true}` — fires after the substantive-edit retirement cascade transaction commits. Correlate with the per-row `admin_quiz_item_retired` events via `lesson_id`. (Slice 6.4b — B-065.) |
| `admin_lesson_published` | `app/services/lesson_admin_service.py` | `{admin_id, lesson_id, deck_id, version: int, version_type: str, generated_by_model: str \| null, internal: true}` — fires only on the NULL → non-NULL transition of `published_at`; idempotent re-publish emits no event. (Slice 6.4b — B-065.) |
| `admin_lesson_archived` | `app/services/lesson_admin_service.py` | `{admin_id, lesson_id, deck_id, was_published: bool, internal: true}` — fires only on the NULL → non-NULL transition of `archived_at`. Does NOT cascade-retire quiz_items (slice 6.1 §AC-4). (Slice 6.4b — B-065.) |
| `admin_quiz_item_created` | `app/services/quiz_item_admin_service.py` | `{admin_id, quiz_item_id, lesson_id, question_type, difficulty, internal: true}` — fires at end of successful `POST /api/v1/admin/lessons/{id}/quiz-items` transaction AND on the substantive `PATCH` retire-and-replace path (the new replacement row's emit). (Slice 6.4b — B-065.) |
| `admin_quiz_item_retired` | `app/services/quiz_item_admin_service.py` (direct retire OR cascade from substantive lesson edit OR substantive quiz_item PATCH) + `app/services/lesson_admin_service.py` (lesson-cascade) | `{admin_id, quiz_item_id, lesson_id, superseded_by_id: str \| null, prior_version: int, retire_reason: 'direct' \| 'lesson_substantive_cascade' \| 'quiz_item_substantive_replace', internal: true}` — only fires on the NULL → non-NULL transition of `retired_at`. `retire_reason` is the discriminator for "cascade vs direct" without requiring a JOIN. (Slice 6.4b — B-065.) |
| `email_sent` | `app/services/reminder_service.py` | `{user_id, type, cards_due, streak}` |
| `email_unsubscribed` | `app/api/v1/routes/email_prefs.py` | `{user_id, method}` |
| `email_resubscribed` | `app/api/v1/routes/email_prefs.py` | `{user_id}` |
| `home_state_evaluation_failed` | `app/services/home_state_service.py` | `{user_id, error_code}` — fires when the state evaluator's compute path raises; the API still returns 200 with `states: []` (P5-S18c). |
| `daily_card_submit` | `app/services/study_service.py` (`_check_daily_wall`) | `{plan: 'free'\|'pro'\|'enterprise', count_after: int\|null, was_walled: bool, counter_unavailable: bool}` — fires on every review-submit attempt for free users (spec #50, P5-S22-WALL). `count_after` is the post-INCR Redis value for non-walled submits, `15` (cap) for walled submits, `null` when Redis is down. `was_walled: true` only when the submit returned 402. `counter_unavailable: true` on the fail-open path. Pro/Enterprise bypass Option 2 → event does not fire for them. |
| `ingestion_job_enqueued` | `app/services/ingestion_service.py` (`enqueue_ingestion`) | `{admin_id, job_id, source_content_sha256, target_deck_slug, source_size_bytes, internal: true}` — fires immediately after the `ingestion_jobs` row is INSERT-ed and the RQ job is enqueued (Phase 6 slice 6.10b, spec #10 D-13 / B-083b). Dedupe hits do NOT re-fire — the existing job's response is returned without a second event. `internal: true` keeps the event out of user-facing PostHog dashboards (admin-only surface per G-4). |
| `ingestion_job_completed` | `app/jobs/ingestion_worker.py` (`_emit_completed`) | `{admin_id, job_id, target_deck_id, generated_lesson_ids: list[str], generated_quiz_item_count: int, critique_verdict: 'PASS'\|'NEEDS_REVIEW', duration_seconds: int, internal: true}` — fires from the worker on Stage-3 success after `ingestion_jobs.status='completed'`. `duration_seconds` is wall-clock from worker start to terminal write; `critique_verdict` is preserved verbatim from `CritiqueSchema` (FAIL short-circuits to `ingestion_job_failed` instead). |
| `ingestion_job_failed` | `app/jobs/ingestion_worker.py` (`_emit_failed`) | `{admin_id, job_id, stage: 'gen'\|'critique'\|'persist'\|'enqueue_dedup'\|'unknown', error_class: str, current_attempt: int, duration_seconds: int, internal: true}` — fires on terminal failure across any of: gen/critique retry exhaustion (`error_class='exception'`), critique=FAIL (`stage='critique', error_class='critique_fail'`), Stage-3 slug conflict (`error_class='lesson_slug_conflict'`), Stage-3 edit-classification 409 after retry-once (`error_class='edit_classification_conflict'`), R2 source fetch failure at the worker boundary (`stage='enqueue_dedup'`). Pairs with `ingestion_job_enqueued` for the start/end funnel; one of `_completed` / `_failed` always fires per job. |
| `rescan_initiated` | `app/api/routes/analyze.py` (`rescan_application`) | `{tracker_application_id}` — fires from BE-only after dedupe + paywall pass and immediately before the LLM scoring call. Spec #63 (E-043) §9. |
| `rescan_completed` | `app/api/routes/analyze.py` (`rescan_application`) | `{tracker_application_id, scan_id, jd_hash_prefix, ats_score_before: int\|null, ats_score_after: int, ats_score_delta: int\|null, keyword_match_delta: float\|null, skills_coverage_delta: float\|null, formatting_compliance_delta: float\|null, bullet_strength_delta: float\|null, short_circuited: false}` — fires after the score row + tracker `ats_score` flip succeed. Per-axis deltas are pre-computed BE-side per §12 D-6 / D-12. `short_circuited` is always `false` on this event (the dedupe path fires `rescan_short_circuited` instead). `jd_hash_prefix` is the 8-char prefix of the SHA-256 hash (privacy-friendly, sufficient for analytics joins per spec #63 §16.2 R-2; supersedes original D-12 `jd_hash` full-hash wording — B-088 impl reconciliation). Spec #63 §9 + AC-11. |
| `rescan_short_circuited` | `app/api/routes/analyze.py` (`rescan_application`) | `{tracker_application_id, jd_hash_prefix}` — fires when the `(jd_hash, resume_hash)` pair already has a stored row and the LLM call is skipped (D-2). Counter is NOT consumed on this path. Spec #63 §9. |
| `rescan_failed` | `app/api/routes/analyze.py` (`rescan_application`) | `{tracker_application_id, error_class: 'scoring_error'\|'jd_missing'\|'paywall'\|'not_found'}` — fires immediately before each non-2xx HTTPException raise: 404 (`'not_found'`, tracker not owned / missing), 422 (`'jd_missing'`, pre-migration `jd_text=NULL`), 402 (`'paywall'`, free-tier `analyze` lifetime cap hit), 502 (`'scoring_error'`, LLM pipeline failure). Counter is NOT incremented on any of these paths (request rolls back / never reached the counter). The `'auth'` enum value was deliberately dropped per spec #63 §16.1 R-1 — `Depends(get_current_user)` raises 401 before the route body executes, so no analytics call site is reachable for that path. Enum + multi-path fires landed at B-088 (spec #63 §16.1 R-1). Spec #63 §9 + AC-8. |

#### Deprecated Backend Events

Preserved for historical PostHog data cross-reference. Emission removed but rows stay in the catalog for dashboard / funnel lookups.

| Event | Source file | Properties |
|-------|-------------|-----------|
| `cover_letter_generated` **(DEPRECATED spec #52 slice 2/2)** | `app/api/routes/cover_letter.py` (emission removed) | `{tone, resume_chars, company_name_present}` |

> **`cover_letter_generated` (DEPRECATED spec #52 slice 2/2 — emission removed as part of the B-002 structured-response migration. Historical PostHog data preserved. Replaced by `cover_letter_succeeded` (success) and `cover_letter_failed` (error_code, 502) in the catalog above. Dashboards referencing this event name should be migrated in a separate dashboard-hygiene slice.)**

## Postgres Event Tables (slice 6.0 — dual-write)

Phase 6 ships two append-only Postgres event tables alongside PostHog. PostHog
stays canonical for funnels / retention / product analytics; Postgres is
canonical for SQL-queryable content-quality + FSRS-retention dashboards
(slice 6.13 / 6.13.5 / 6.16). The split exists because spec #38 banned the
PostHog Query API / HogQL inside `/admin/analytics`. Locked decision **I1**.

| Table | Source | Mirrors PostHog event | Write entry point |
|-------|--------|------------------------|--------------------|
| `quiz_review_events` | `app/services/quiz_item_study_service.py:review_quiz_item` (BE dual-write hook at the existing `quiz_item_reviewed` emission site) | `quiz_item_reviewed` | `analytics_event_service.write_quiz_review_event` |
| `lesson_view_events` | `POST /api/v1/lessons/:lesson_id/view-event` (FE caller `services/api.ts:recordLessonView`, fires from `pages/Lesson.tsx` `useEffect` alongside the existing FE `capture('lesson_viewed')`) | `lesson_viewed` | `analytics_event_service.write_lesson_view_event` |

**Append-only invariant (§4.4 + AC-10).** `analytics_event_service` exposes
only `write_*` functions. No UPDATE / DELETE / archive method exists; future
retention ships in a dedicated slice.

**D-7 dual-write failure semantics.** Both the service layer
(`analytics_event_service.write_*`) and each calling site
(`review_quiz_item` + lesson view-event route) wrap the write in
`try/except` so analytics failure NEVER blocks the user request. PostHog
emission shape is unchanged; the Postgres write fails open.

**Cross-refs.** Spec `docs/specs/phase-6/00-analytics-tables.md` §1-§14;
locked decisions §12 D-1..D-10; closes B-069. Spec #38 (HogQL ban) at
`docs/specs/phase-5/38-admin-analytics.md`.

## Key Funnels (Phase 4 dashboards)
1. **Acquisition:** `landing_page_viewed` → `cta_clicked` → sign-in →
   `ats_scanned` → `paywall_hit` → `checkout_started` →
   `payment_completed`.
2. **Retention:** `daily_review_started` day-1 → day-7 → day-30.
3. **Mission:** `mission_created` → `mission_day_completed` ×N →
   `mission_completed`.
4. **Abuse:** `registration_blocked` count per day / per IP range.

## Rules
- Adding a new feature? Pick the event name **before** writing the
  UI, add it to this file, then wire up `capture()`/`track()`.
- Don't rename existing events — dashboards and funnels reference
  them by name. Deprecate, don't rename.
