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
| `gap_study_clicked` | `components/MissingSkillsPanel.tsx` | `{skill_id, category_name}` |
| `paywall_hit` | `components/PaywallModal.tsx` | `{trigger, category_name?, cards_viewed?}` |
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
| `email_preferences_viewed` | `pages/EmailPreferences.tsx` | — |
| `email_preferences_saved` | `pages/EmailPreferences.tsx` | `{daily_reminder}` / `{timezone}` |
| `nav_clicked` | `components/layout/TopNav.tsx`, `components/layout/MobileNav.tsx` | `{namespace: 'home'\|'learn'\|'prep'\|'profile'\|'admin', from_path, to_path}` |

> **P5-S14 note (deprecated_route_hit):** the navigation-restructure spec (`docs/specs/phase-5/12-navigation-restructure.md` §Analytics) also defines a transitional `deprecated_route_hit` event to fire from each `<Navigate>` node in `src/App.tsx`'s redirect block. It is **not currently wired** (P5-S13 landed the redirect block without it). If we want to measure when the old paths stop receiving hits before dropping the block in Phase 6, we need to backfill — out of scope for P5-S14, flagged here as a P5-S13 gap.

#### Deprecated Frontend Events

Preserved for historical PostHog data cross-reference. Source files no longer exist in the repo.

| Event | Source file (deleted) | Properties |
|-------|-----------------------|-----------|
| `persona_changed` **(DEPRECATED P5-S17)** | `components/PersonaPicker.tsx` | `{from, to}` |
| `onboarding_persona_selected` **(DEPRECATED P5-S17)** | `components/PersonaPicker.tsx` | `{persona, mode: 'onboarding'}` |

> **`persona_changed` (DEPRECATED P5-S17, commit b5f42c2 — source component deleted; historical PostHog data preserved. Replaced by `persona_selected`.)**

> **`onboarding_persona_selected` (DEPRECATED P5-S17, commit b5f42c2 — source component deleted; historical PostHog data preserved. Replaced by `persona_selected`. Referenced by `docs/specs/phase-4/24-posthog-dashboards.md` event #13 — update that spec in a separate slice if dashboard is decommissioned.)**

### Backend events (`app/**/*.py`)

| Event | Source file | Properties |
|-------|-------------|-----------|
| `ats_scanned` | `app/api/routes/analyze.py` | `{user_id, scan_id, resume_id, job_description_length}` |
| `tracker_auto_created_from_scan` | `app/api/routes/analyze.py` | `{user_id, company, role, matched_skills}` |
| `resume_rewrite_generated` | `app/api/routes/rewrite.py` | `{resume_chars, missing_keywords_count, template_type}` |
| `cover_letter_generated` | `app/api/routes/cover_letter.py` | `{tone, resume_chars, company_name_present}` |
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
| `admin_card_draft_generated` | `app/api/v1/routes/admin.py` | `{admin_id, category, tokens}` |
| `email_sent` | `app/services/reminder_service.py` | `{user_id, type, cards_due, streak}` |
| `email_unsubscribed` | `app/api/v1/routes/email_prefs.py` | `{user_id, method}` |
| `email_resubscribed` | `app/api/v1/routes/email_prefs.py` | `{user_id}` |

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
