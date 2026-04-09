---
description: PostHog events, funnels, dashboards, tracking conventions
---
# Analytics Skill
## Overview
PostHog is instrumented from Phase 1. Every user-facing feature
fires events. Phase 4 builds dashboards and funnels on top.
## Setup
- Frontend: PostHog JS snippet in index.html (or React provider)
- Backend: posthog-python library for server-side events
## Event Naming Convention
- Use snake_case: `card_reviewed`, NOT `CardReviewed`
- Include relevant properties as a dict
- Always include `user_id` (auto from PostHog identify)
## Core Events (Phase 1)
- `user_signed_up` — { auth_provider }
- `ats_scanned` — { score, gaps_found }
- `card_viewed` — { card_id, category }
- `card_reviewed` — { card_id, rating, time_spent_ms }
- `paywall_hit` — { cards_viewed, trigger }
- `payment_completed` — { amount, plan }
## Phase 2+ Events
- `streak_incremented`, `streak_broken`
- `mission_created`, `mission_completed`
- `email_sent`, `email_clicked`
## Key Funnels (build in Phase 4)
1. Acquisition: Sign up → ATS scan → View card → Paywall → Pay
2. Retention: Day 1 → Day 7 → Day 30 return rate
3. Mission: Create mission → 50% complete → 100% complete
