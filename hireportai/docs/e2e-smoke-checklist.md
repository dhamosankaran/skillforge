# E2E Smoke Checklist — SkillForge Pre-Launch Walkthrough

> **Purpose:** manual end-to-end walkthrough covering the Lens (scan) → Forge (study) → Mission (interview + re-scan) → Pro (Stripe) → Admin loop. Run before each production deploy that touches more than one engine.
> **Format:** PASS/FAIL checkboxes per step. Capture failures with screenshots + console output.

---

## Prerequisites

### Required env vars

**Backend** (`hirelens-backend/.env`):
- `DATABASE_URL` — `postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport`
- `REDIS_URL` — `redis://localhost:6379`
- `JWT_SECRET_KEY` — non-default value
- `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET`
- `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` per `LLM_FAST_PROVIDER` / `LLM_REASONING_PROVIDER`)
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` + `STRIPE_PRO_PRICE_ID` (+ `STRIPE_PRO_PRICE_ID_INR` for INR geo path) + `STRIPE_ENTERPRISE_PRICE_ID`
- `RESEND_API_KEY` + `RESEND_FROM_ADDRESS`
- `POSTHOG_API_KEY` + `POSTHOG_HOST`
- `ADMIN_EMAILS` — comma-separated Google emails granted admin on login
- `FREE_DAILY_REVIEW_LIMIT=10` + `FREE_LIFETIME_SCAN_LIMIT=1` + `FREE_MONTHLY_INTERVIEW_LIMIT=3` (prod-default values)

**Frontend** (`hirelens-frontend/.env.local`):
- `VITE_API_BASE_URL` — backend URL
- `VITE_GOOGLE_CLIENT_ID` (public)
- `VITE_POSTHOG_KEY` + `VITE_POSTHOG_HOST`
- `VITE_STRIPE_KEY` (publishable)

### Local dev setup

1. `brew services start postgresql@16 redis`
2. `cd hirelens-backend && source venv/bin/activate && alembic upgrade head`
3. `python -m app.scripts.seed_phase6` (seeds 12 reference decks × 2 lessons)
4. `uvicorn app.main:app --reload --port 8000`
5. `cd hirelens-frontend && npm run dev -- --port 5199`

### Test users

- **Free user:** sign in with a non-admin Google account; verify `users.role = 'user'`, `subscription.plan = 'free'`.
- **Admin user:** sign in with an email listed in `ADMIN_EMAILS`; verify `users.role = 'admin'` after login.
- **Pro user:** complete Stripe checkout via Step 16 below; verify `subscription.plan = 'pro'` post-webhook.

---

## Lens (scan)

- [ ] **1. Google OAuth login (new user → onboarding flow).** Open `/`, click "Sign in with Google", complete OAuth. New user lands on `/onboarding` (then `/onboarding/persona`). Verify `users` row created with `onboarding_completed = false`; `registration_logs` row created.

- [ ] **2. Upload resume + paste JD → scan completes → results page renders.** Navigate to `/prep/analyze`, drop a PDF resume, paste a real JD ≥200 chars, click Analyze. Verify request succeeds in <30s; redirect to `/prep/results?scan_id=…`; `tracker_applications_v2` row created with `jd_text` + `jd_hash` populated.

- [ ] **3. Results show ATS score + section scores + keyword analysis.** Verify Results page renders ATS score (0–100), 4 section scores (keyword_match / skills_coverage / formatting_compliance / bullet_strength), Job Fit Explanation, Missing Skills panel, Matched/Missing keyword chips, Bullet Analysis cards.

- [ ] **4. LoopFrame renders on Results page (spec #64 surface).** Verify the 4-step strip ("Scanned / Studying / Re-scan / Interview") renders ABOVE the dashboard grid (not as 12th grid child). Step 1 shows "done"; later steps reflect current state. Mobile: vertical stack at <md breakpoint. PostHog `loop_frame_rendered` fires once on mount.

---

## Forge (study)

- [ ] **5. PersonaPicker → select career_climber → home redirects.** From `/onboarding/persona`, select Career-Climber. Optionally fill target role + target quarter (spec #67 §8.1). Click Continue. Verify `/auth/me` shows `persona = 'career_climber'`; navigate to `/first-action` (or `/home` if `first_action_seen` already set).

- [ ] **6. Home renders HomeStatusHero + TodaysReviewWidget.** On `/home`, verify the one-line status hero (spec #65) renders between greeting and widget grid: `${streak}-day streak. ${dueCount} cards due today.` for CC. TodaysReviewWidget shows due-card count. PostHog `home_status_hero_rendered` fires.

- [ ] **7. Learn page shows ranked decks (slice 6.7 surface).** Navigate to `/learn`. CC mode renders the persona-aware learn page; ranked decks list shows ≥4 decks with score breakdowns. Click a deck → navigates to `/learn/deck/:id` showing lesson list.

- [ ] **8. Open a deck → study a card → FSRS rating submits.** From a deck detail page, click into a lesson at `/learn/lesson/:id`. Open a quiz item, answer, submit a rating (Again/Hard/Good/Easy). Verify `quiz_item_progress` row updated; `quiz_review_events` row written; FSRS state advances.

- [ ] **9. Complete 5 cards → TodaysReviewWidget flips to "Done for today".** Submit ratings for 5 distinct cards. Return to `/home`. Verify TodaysReviewWidget switches to its done state; `gamification_stats.current_streak` increments if first review of the UTC day.

- [ ] **10. Dashboard (/learn/dashboard) renders retention + mastery sections.** Navigate to `/learn/dashboard`. Verify all 5 sections render: Cards Due, Retention curve (SVG), Deck Mastery, Streak, Recent Reviews. Cold-start state (zero history) renders gracefully via `is_cold_start: true` flag.

---

## Mission (interview + re-scan)

- [ ] **11. Switch to interview_prepper persona.** From `/profile` or `/onboarding/persona?return_to=/home`, switch persona to interview_prepper. Set `interview_target_company` + `interview_target_date` on a tracker row.

- [ ] **12. Countdown widget renders with interview target.** On `/home` (IP mode), verify CountdownWidget shows `${company} interview in ${days}d`. AppShell `<LoopProgressStrip>` renders below TopNav (spec #66) when `next_interview != null`.

- [ ] **13. Trigger re-scan from tracker → score delta widget renders.** Navigate to `/prep/tracker?focus={tracker_id}&action=rescan`. Trigger re-scan with updated resume text. Verify `POST /api/v1/analyze/rescan` returns 200; `tracker_application_scores` row written; `<ScoreDeltaWidget>` renders inline-expand under focused row showing before→after + 4 per-axis deltas + days-between.

- [ ] **14. Score history endpoint returns chronological entries.** Hit `GET /api/v1/tracker/{app_id}/scores` directly. Verify response is `{tracker_application_id, history[], delta}` with history oldest-first; `delta` is null when `len(history) < 2`.

---

## Pro tier (Stripe)

- [ ] **15. Free user hits daily card wall at 10 reviews.** As a free user, submit FSRS ratings for 10 distinct cards in one UTC day. On the 11th attempt, verify `<DailyReviewWalledView>` renders or `<WallInlineNudge>` blocks the card; `daily_status.can_review` is false; `paywall_hit{trigger: 'daily_card_wall'}` event fires.

- [ ] **16. Pricing page → Stripe checkout redirect works.** Navigate to `/pricing`, click Upgrade → verify redirect to `checkout.stripe.com`. Complete a test card payment (`4242 4242 4242 4242`). Post-checkout returns to `/pricing?upgrade=success`.

- [ ] **17. Post-checkout → user role flips to "pro".** Verify webhook `customer.subscription.created` succeeded (200 in Stripe Dashboard or `stripe_events` table). `subscription.plan = 'pro'`, `status = 'active'`. `/auth/me` returns `subscription.cancel_at_period_end = false`.

- [ ] **18. Cancel flow → cancel-pending UI renders on Profile + Pricing.** Open Stripe billing portal via Profile → Manage subscription. Cancel subscription. Verify webhook `customer.subscription.updated` fires + `cancel_at_period_end = true` written. Profile renders "Cancels {date}" + "Reactivate Pro" button. Pricing Pro tile swaps to "Cancels {date}" + "Reactivate" CTA.

- [ ] **19. Pro digest opt-out toggle works in email preferences.** From Profile → Email Preferences (Pro-gated), toggle "Daily Pro Digest" off. Verify `email_preferences.daily_digest_opt_out = true`. Run `python -m app.scripts.send_pro_digest --dry-run` and verify the user is excluded from the candidate set.

---

## Admin

- [ ] **20. Admin user sees /admin routes (cards/decks/lessons/analytics).** Sign in with an `ADMIN_EMAILS` account. Navigate to `/admin`. Verify AdminLayout renders + sidebar shows: Cards, Decks, Lessons, Quiz Items, Analytics, Content Quality. Each route returns 200 + populates table data. Audit dependency writes a row to `admin_audit_log` per request.

- [ ] **21. AI ingestion pipeline → paste markdown → lesson + quiz items created.** From `/admin/decks/:deckId`, open the AI Ingestion panel. Paste a ≥500-char markdown source (e.g. a tech-blog post). Submit. Verify `ingestion_jobs` row created with `status = 'queued'`; RQ worker picks up the job; status progresses `queued → running → completed`; new lesson + ≥3 quiz items appear under the deck. Critique signals written to `card_quality_signals` (signal_source='critique').

---

## Privacy / safety spot-checks

- [ ] **22. Career-intent aggregate digest below threshold suppresses block.** As a CC user with target role + quarter set, run `python -m app.scripts.send_pro_digest --dry-run` when fewer than 10 cohort users share the same `(target_role, target_quarter)` bucket. Verify `aggregate_intent_block` is `None` in the composer output; rendered digest contains no peer-comparison copy. (Spec #67 §11 AC-X.)

- [ ] **23. Persona switch preserves career intent.** As a CC user with intent set, switch to interview_prepper via `/onboarding/persona?return_to=/home`, then back to career_climber. Verify `user_career_intents.superseded_at IS NULL` row still present (spec #67 §12 D-5 — no auto-supersede on persona PATCH).

---

## Sign-off

| Engine | Total | PASS | FAIL | Notes |
|---|---|---|---|---|
| Lens | 4 | | | |
| Forge | 6 | | | |
| Mission | 4 | | | |
| Pro | 5 | | | |
| Admin | 2 | | | |
| Safety | 2 | | | |
| **Total** | **23** | | | |

**Walked-through by:** ______________  **Date:** ______________  **Build SHA:** ______________
