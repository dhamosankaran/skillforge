# SPEC #24: PostHog Dashboards + PaywallModal Tests

## Status: Complete
## Phase: 4
## Branch: main

---

## Problem

The codebase fires 30+ PostHog events across backend and frontend, but there are
no documented funnels, retention metrics, or dashboards. Without these, the
analytics data is being collected but never surfaced for product decisions.

Additionally, the `PaywallModal` component — the primary conversion surface — has
zero test coverage, making it fragile to refactor.

## Solution

### Part A — PostHog Event Inventory & Dashboard Definitions

Document every PostHog event, define actionable funnels, and flag gaps.

### Part B — PaywallModal Frontend Tests

Add Vitest + React Testing Library tests for the PaywallModal component covering
rendering, user interaction, analytics, and API integration.

---

## Part A — PostHog Event Inventory

### Complete Event List (Phases 1-3)

| # | Event | Source | Layer | Properties |
|---|-------|--------|-------|------------|
| 1 | `ats_scanned` | analyze route | BE | score, grade, gaps_found, matched_keywords, missing_keywords |
| 2 | `card_viewed` | CardViewer | FE | card_id, category_id |
| 3 | `card_reviewed` | study_service | BE | card_id, rating, time_spent_ms, fsrs_state, reps, lapses |
| 4 | `quiz_submitted` | QuizPanel | FE | card_id, time_to_reveal_ms |
| 5 | `daily_review_started` | DailyReview | FE | total_due, session_id |
| 6 | `daily_review_completed` | DailyReview | FE | cards_reviewed, session_id |
| 7 | `paywall_hit` | PaywallModal | FE | trigger, category_name, cards_viewed |
| 8 | `checkout_started` | PaywallModal + payment_service | FE+BE | trigger, plan, price_usd / price_id |
| 9 | `payment_completed` | webhook + Pricing page | BE+FE | plan, amount_total, currency / amount_usd, source |
| 10 | `subscription_cancelled` | webhook | BE | plan |
| 11 | `onboarding_started` | Onboarding | FE | scan_id, gap_count |
| 12 | `onboarding_completed` | Onboarding | FE | gaps_shown, cards_clicked |
| 13 | `onboarding_persona_selected` | PersonaPicker | FE | persona |
| 14 | `onboarding_tour_completed` | GuidedTour | FE | — |
| 15 | `onboarding_tour_skipped` | GuidedTour | FE | — |
| 16 | `gap_card_clicked` | Onboarding | FE | gap, category_id |
| 17 | `landing_page_viewed` | LandingPage | FE | — |
| 18 | `cta_clicked` | LandingPage | FE | button (hero, how_it_works, pricing) |
| 19 | `study_dashboard_viewed` | StudyDashboard | FE | category_count, locked_count |
| 20 | `streak_incremented` | gamification_service + GamificationCtx | BE+FE | new_length, previous / previous_length |
| 21 | `streak_broken` | gamification_service | BE | previous_length |
| 22 | `badge_earned` | gamification_service + GamificationCtx | BE+FE | badge_id, badge_name |
| 23 | `xp_awarded` | gamification_service | BE | amount, source_type, total_xp_after |
| 24 | `mission_created` | mission_service + MissionMode | BE+FE | days, categories, total_cards, daily_target / title, target_date |
| 25 | `mission_day_completed` | mission_service + MissionMode | BE+FE | day_number, cards_done, days_remaining / mission_id |
| 26 | `mission_completed` | mission_service + MissionMode | BE+FE | total_days, coverage_pct / mission_id |
| 27 | `card_feedback_submitted` | QuizPanel | FE | card_id, vote, has_comment |
| 28 | `experience_generated` | experience_service + Profile | BE+FE | topic, cards_studied_count |
| 29 | `email_sent` | reminder_service | BE | type, cards_due, streak |
| 30 | `locked_tile_clicked` | StudyDashboard | FE | category_id, category_name |
| 31 | `category_tile_clicked` | StudyDashboard | FE | category_id, category_name |
| 32 | `category_detail_viewed` | CategoryDetail | FE | category_id, category_name |
| 33 | `profile_viewed` | Profile | FE | — |
| 34 | `email_preferences_viewed` | EmailPreferences | FE | — |
| 35 | `email_preferences_saved` | EmailPreferences | FE | daily_reminder / timezone |

### Funnel Definitions

#### 1. Acquisition Funnel
```
landing_page_viewed → cta_clicked → ats_scanned → card_viewed → paywall_hit → payment_completed
```
- **Window:** 14 days
- **Breakdown:** by `cta_clicked.button` to see which CTA converts best
- **Goal:** Measure visitor-to-paid conversion rate

#### 2. Retention Funnel
```
daily_review_started on Day 1 → Day 7 → Day 30
```
- **Cohort:** Users who completed `payment_completed` (Pro users only)
- **Metric:** % returning for daily review at D1, D7, D30
- **Goal:** Measure long-term study habit formation

#### 3. Mission Funnel
```
mission_created → 50% of mission_days completed → mission_completed
```
- **Method:** Compare `mission_day_completed.day_number / mission_created.days`
  to check if user reaches 50% milestone
- **Breakdown:** by `mission_created.categories` count
- **Goal:** Measure mission follow-through rate

### Retention Dashboard Metrics

| Metric | Definition | PostHog Config |
|--------|-----------|---------------|
| DAU | Unique users with any event per day | Trends → unique users → daily |
| WAU | Unique users with any event per 7-day window | Trends → unique users → weekly |
| MAU | Unique users with any event per 30-day window | Trends → unique users → monthly |
| DAU/MAU ratio | DAU ÷ MAU (stickiness) | Formula: A/B with DAU and MAU series |
| Study DAU | Unique users firing `card_reviewed` per day | Trends → `card_reviewed` → unique users → daily |

### Missing Events — None

All 25 expected events from Phases 1-3 are already instrumented.
Additional events (30-35) were added organically during feature development and
provide useful supplementary data for the dashboards above.

---

## Part B — PaywallModal Tests

### Test Cases

| Test | Description |
|------|-------------|
| `renders correct headline for each trigger` | Each `PaywallTrigger` value shows its expected headline |
| `CTA calls createCheckoutSession` | Clicking "Upgrade to Pro" calls the API and redirects |
| `shows loading state on click` | Button shows spinner + "Starting checkout..." text |
| `Not now button closes modal` | Clicking "Not now" calls `onClose` |
| `fires checkout_started event` | CTA click fires PostHog `checkout_started` with correct properties |

### Implementation

- **File:** `src/components/__tests__/PaywallModal.test.tsx`
- **Deps:** `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`
- **Environment:** jsdom (via Vitest config)
- **Mocks:** `@/services/api` (createCheckoutSession), `@/utils/posthog` (capture)

---

## Acceptance Criteria

- [x] AC-1: All PostHog events documented in this spec.
- [x] AC-2: Three funnels defined with window and breakdown settings.
- [x] AC-3: Retention dashboard metrics (DAU, WAU, MAU, DAU/MAU) defined.
- [x] AC-4: No missing events identified — all expected events are instrumented.
- [x] AC-5: PaywallModal test file created with 5 test cases.
- [x] AC-6: `npx vitest run` passes.

## Dependencies

- Spec #10 (PostHog Analytics) — Phase 1, completed.
- Spec #11 (Stripe Integration) — Phase 1, completed.

## Out of Scope

- Actually creating the dashboards in PostHog UI (manual task).
- Session replay configuration.
- Feature flags integration.
