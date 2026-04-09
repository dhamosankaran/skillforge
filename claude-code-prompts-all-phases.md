# SkillForge — Claude Code Prompts (All Phases)

> **How to use**: Copy-paste each prompt into Claude Code **one at a time**.
> Wait for completion, review output, then proceed.
> Start a **new Claude Code session** at every `--- NEW SESSION ---` marker.
> Each session should stay under 5 slices to avoid context degradation.

---

# ═══════════════════════════════════════════
# PHASE 0: Foundation Surgery + Skeleton Deploy
# ═══════════════════════════════════════════
# Status: ✅ Tasks 0.1–0.3 DONE (PostgreSQL migration)
# Remaining: 0.4 (Auth), 0.5 (Roles), 0.6–0.7 (Deploy + CI/CD), 0.8 (Verify)

## --- NEW SESSION --- Phase 0: Auth + Roles

### P0-S1: Spec — Auth Unification

```
Read AGENTS.md. Read docs/specs/phase-0/01-auth-unification.md. If the spec file is empty or doesn't exist, fill out the spec template with precise Acceptance Criteria, API Contract, and Test Plan for unifying the frontend to use the backend's JWT auth system (Google OAuth → backend issues JWT → frontend stores and sends JWT on all API calls). Do NOT write any code yet. Stop after updating the markdown file so I can review it.
```

### P0-S2: Implement — Auth Unification (Backend)

```
Read AGENTS.md. Read docs/specs/phase-0/01-auth-unification.md.

Implement the backend auth changes:
1. Ensure Google OAuth endpoint exists: POST /api/v1/auth/google — accepts Google ID token, verifies it, creates/finds user, returns JWT access + refresh tokens.
2. Ensure GET /api/v1/auth/me returns the current user from the JWT.
3. Ensure Depends(get_current_user) middleware extracts and validates the JWT from the Authorization header.
4. Write tests in tests/test_auth.py: valid token returns user, expired token returns 401, missing token returns 401.
5. Run: python -m pytest tests/test_auth.py -v

Do NOT touch the frontend yet. Stop after backend tests pass.
```

### P0-S3: Implement — Auth Unification (Frontend)

```
Read AGENTS.md. Read docs/specs/phase-0/01-auth-unification.md.

Implement the frontend auth changes:
1. Update the login flow to call POST /api/v1/auth/google with the Google ID token.
2. Store the JWT access token (in memory or localStorage) and refresh token.
3. Update services/api.ts to attach Authorization: Bearer <token> on every API call.
4. Add a useAuth hook or context that exposes: user, isAuthenticated, login, logout.
5. Protect routes that require auth — redirect to login if no token.
6. Test manually: Google login → API call to /auth/me → returns user.

Stop after manual verification works. Commit:
git add -A && git commit -m "feat(auth): unify frontend to use backend JWT — closes spec #01"
```

### P0-S4: Spec + Implement — User Roles

```
Read AGENTS.md. Read docs/specs/phase-0/02-user-roles.md. If the spec is empty, fill it out first with AC for: adding a `role` column (default "user"), creating a require_admin() dependency that returns 403 for non-admins, and a test plan. Then implement:

1. Add `role: Mapped[str] = mapped_column(String(20), default="user")` to the User model.
2. Create Alembic migration: alembic revision --autogenerate -m "add role column to users"
3. Apply: alembic upgrade head
4. Create a `require_admin` dependency in app/core/deps.py that checks current_user.role == "admin".
5. Write tests in tests/test_user_roles.py: admin user passes, regular user gets 403.
6. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(auth): add user roles and require_admin — closes spec #02"
```

## --- NEW SESSION --- Phase 0: Deploy + CI/CD

### P0-S5: Spec — Skeleton Deploy

```
Read AGENTS.md. Create docs/specs/phase-0/02a-skeleton-deploy.md with the spec template filled out for:

Problem: First deploy after 12 weeks of localhost code always breaks (CORS, connection pooling, env vars).
Solution: Deploy a skeleton app to Vercel (FE) + Railway (BE + managed PG) in Phase 0.

Acceptance Criteria:
- AC-1: Backend is deployed to Railway and curl https://<railway-url>/health returns 200.
- AC-2: Frontend is deployed to Vercel and loads in the browser.
- AC-3: Frontend can call the deployed backend API without CORS errors.
- AC-4: Database migrations run on Railway (alembic upgrade head via release command).
- AC-5: Environment variables are set in Railway and Vercel dashboards, not in code.

Include an Edge Cases section covering: Railway free tier sleep, CORS origin mismatch, DATABASE_URL format differences between local asyncpg and Railway.

Do NOT execute any deploy commands yet. Stop after the spec is written.
```

### P0-S6: Implement — Skeleton Deploy (Backend to Railway)

```
Read AGENTS.md. Read docs/specs/phase-0/02a-skeleton-deploy.md.

This is a MANUAL task with Claude Code assistance. Help me:

1. Create a Procfile or railway.toml for the backend:
   - Build command: pip install -r requirements.txt
   - Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   - Release command: alembic upgrade head
2. Update app/core/config.py to handle Railway's DATABASE_URL format (they provide postgresql:// not postgresql+asyncpg://, so we need to replace the scheme).
3. Update CORS settings in app/main.py to read ALLOWED_ORIGINS from env and include the Vercel frontend URL.
4. Create a requirements.txt that includes all production dependencies (no dev deps).
5. List the environment variables I need to set in Railway's dashboard.

Do NOT deploy yet — just prepare the files. Stop so I can review, then I'll deploy manually via Railway dashboard.
```

### P0-S7: Implement — CI/CD Pipeline

```
Read AGENTS.md. Read docs/specs/phase-0/02b-cicd-pipeline.md. If the spec doesn't exist, create it first.

Create .github/workflows/ci.yml with:
1. Trigger: push to main, pull requests
2. Job 1 — backend-tests: PostgreSQL 16 + pgvector service container, install deps, run pytest
3. Job 2 — frontend-tests: install deps, run vitest
4. Job 3 — migration-rollback: run alembic upgrade head → downgrade -1 → upgrade head
5. All jobs use the correct Python 3.13 and Node 20 versions.

Do NOT add auto-deploy steps yet (Railway and Vercel handle that via git push detection).

Commit: git add -A && git commit -m "ci: add GitHub Actions pipeline — closes spec #02b"
```

### P0-S8: Verify Production

```
Read AGENTS.md. This is the final Phase 0 verification.

1. Run the full backend test suite locally: python -m pytest tests/ -v --tb=short
2. Run the full frontend test suite: cd hirelens-frontend && npx vitest run
3. Help me verify the deployed app:
   - curl the production backend /health endpoint
   - Check that the frontend loads on the Vercel URL
   - Verify CORS works: frontend → backend API call
4. Update docs/specs/phase-0/02a-skeleton-deploy.md status to Done.
5. Push to main: git add -A && git commit -m "chore: phase 0 complete — all specs done" && git push

Phase 0 is complete. All ATS features work on PostgreSQL, auth is unified, roles exist, app is deployed, CI/CD is active.
```

---

# ═══════════════════════════════════════════
# PHASE 1: Core Study Engine + ATS Bridge
# ═══════════════════════════════════════════
# 12 tasks, ~35 slices across ~7 sessions

## --- NEW SESSION --- Phase 1A: Card Extraction + Embeddings (Tasks 1.1–1.2)

### P1-S1: Spec — Card Extraction

```
Read AGENTS.md. Read .agent/skills/card-extraction.md. Create docs/specs/phase-1/03-card-extraction.md with the spec template:

Problem: 177 study cards are hardcoded in JSX files. They need to be in PostgreSQL with embeddings for search and FSRS scheduling.
Solution: Extract cards from JSX, create Card + Category models, seed the database, generate embeddings.

Include: data model for cards table and categories table (columns, types, indexes), the extraction script approach, and test plan (count verification, embedding non-null check). Do NOT write code yet.
```

### P1-S2: Card + Category ORM Models

```
Read AGENTS.md. Read docs/specs/phase-1/03-card-extraction.md.

1. Create app/models/card.py with Card model: id (str PK), category_id (FK), question (Text), answer (Text), difficulty (String), tags (JSON array), embedding (Vector(1536), nullable), created_at, updated_at.
2. Create app/models/category.py with Category model: id (str PK), name (String), icon (String), color (String), display_order (Integer), source (String, nullable — "foundation" for free-tier).
3. Register both models in app/models/__init__.py so Base.metadata picks them up.
4. Create Alembic migration: alembic revision --autogenerate -m "add cards and categories tables"
5. Review the generated migration, then apply: alembic upgrade head
6. Test rollback: alembic downgrade -1 && alembic upgrade head
7. Run: python -m pytest tests/ -v --tb=short (existing tests still pass)

Do NOT create the extraction script yet. Commit:
git add -A && git commit -m "feat(cards): add Card and Category models + migration"
```

### P1-S3: Card Extraction Script

```
Read AGENTS.md. Read docs/specs/phase-1/03-card-extraction.md. Read .agent/skills/card-extraction.md.

1. Read the JSX files where cards are currently defined (check hirelens-frontend/src/data/ or wherever they live). List all categories and card counts you find.
2. Create scripts/extract_cards.py that:
   - Parses the JSX/JSON card data
   - Creates Category records
   - Creates Card records with all fields populated
   - Runs as: python scripts/extract_cards.py
3. Run the script against the local database.
4. Verify: psql -d hireport -c "SELECT count(*) FROM cards;" → should be 177 (or actual count)
5. Verify: psql -d hireport -c "SELECT name, count(c.id) FROM categories cat JOIN cards c ON c.category_id = cat.id GROUP BY cat.name;"

Commit: git add -A && git commit -m "feat(cards): extract cards from JSX to PostgreSQL"
```

### P1-S4: Generate Embeddings

```
Read AGENTS.md. Read docs/specs/phase-1/03-card-extraction.md.

1. Create scripts/generate_embeddings.py that:
   - Reads all cards from PostgreSQL
   - For each card, generates an embedding from the question + answer text using Gemini (or OpenAI) embedding API
   - Updates the card's embedding column with the Vector(1536) result
   - Runs as: python scripts/generate_embeddings.py
2. Run the script.
3. Verify: psql -d hireport -c "SELECT count(*) FROM cards WHERE embedding IS NOT NULL;" → should match total cards
4. Write a test in tests/test_card_extraction.py: test_all_cards_have_embeddings — connect to DB, assert count of cards with embedding = total count.
5. Run: python -m pytest tests/test_card_extraction.py -v

Commit: git add -A && git commit -m "feat(cards): generate embeddings for all cards" && git push
```

## --- NEW SESSION --- Phase 1B: Cards API (Task 1.3)

### P1-S5: Spec — Cards API

```
Read AGENTS.md. Create docs/specs/phase-1/04-cards-api.md with:

Endpoints:
- GET /api/v1/cards — list all categories with card counts
- GET /api/v1/cards/category/{id} — list cards in a category
- GET /api/v1/cards/{id} — get single card
- GET /api/v1/cards/search?q=query — semantic search using pgvector cosine similarity

For each: request params, response schema, auth requirements, error codes. Include plan gating: free users only see categories where source="foundation". Do NOT write code yet.
```

### P1-S6: Cards API — Pydantic Schemas + Service

```
Read AGENTS.md. Read docs/specs/phase-1/04-cards-api.md.

1. Create app/schemas/card.py with Pydantic response models: CardResponse, CategoryResponse (with card_count), CategoryListResponse, CardSearchResult.
2. Create app/services/card_service.py with async methods: list_categories(user), get_cards_by_category(category_id, user), get_card(card_id), search_cards(query, user).
3. For search: use pgvector cosine_distance to find the top 10 most similar cards to the query embedding.
4. For plan gating: if user.plan == "free", filter to only categories where source="foundation".
5. Do NOT create the route yet. Do NOT write tests yet. Stop so I can review the service logic.
```

### P1-S7: Cards API — Routes + Tests

```
Read AGENTS.md. Read docs/specs/phase-1/04-cards-api.md.

1. Create app/api/routes/cards.py with the 4 endpoints from the spec.
2. Register the router in app/main.py.
3. Write tests in tests/test_cards_api.py:
   - test_list_categories — returns categories with card_count
   - test_get_cards_by_category — returns cards
   - test_get_card — returns single card
   - test_search_cards — returns relevant results
   - test_requires_auth — 401 without token
   - test_free_user_sees_only_foundation — free user gets filtered categories
   - At least 10 assertions total.
4. Run: python -m pytest tests/test_cards_api.py -v
5. Fix until all pass. Apply 3-strike rule.

Commit: git add -A && git commit -m "feat(cards): cards API with search and plan gating — closes spec #04" && git push
```

## --- NEW SESSION --- Phase 1C: FSRS Study Engine (Task 1.4)

### P1-S8: Spec — FSRS Daily Review

```
Read AGENTS.md. Read .agent/skills/study-engine.md. Create docs/specs/phase-1/05-fsrs-daily-review.md using the FSRS Daily Review example spec from the playbook as a starting point, but make it precise to our actual models and API.

Include: card_progress table schema, FSRS state machine (New → Learning → Review → Relearning), API contract for GET /api/v1/study/daily and POST /api/v1/study/review, and test plan with 5+ unit test cases. Do NOT write code yet.
```

### P1-S9: CardProgress Model + Migration

```
Read AGENTS.md. Read docs/specs/phase-1/05-fsrs-daily-review.md.

1. Create app/models/card_progress.py with: id, user_id (FK), card_id (FK), stability (Float), difficulty_fsrs (Float), due_date (DateTime), state (String — new/learning/review/relearning), reps (Integer), lapses (Integer), last_reviewed (DateTime), created_at, updated_at.
2. Create Alembic migration and apply.
3. Test rollback cycle.
4. Run existing tests to verify nothing broke.

Commit: git add -A && git commit -m "feat(study): add card_progress model + migration"
```

### P1-S10: Study Service — FSRS Scheduling

```
Read AGENTS.md. Read docs/specs/phase-1/05-fsrs-daily-review.md. Read .agent/skills/study-engine.md.

1. Create app/schemas/study.py with: DailyReviewResponse, ReviewRequest, ReviewResponse.
2. Create app/services/study_service.py with:
   - get_daily_review(user_id) — returns up to 5 cards where due_date <= now, ordered by due_date
   - review_card(user_id, card_id, rating) — uses py-fsrs to calculate next due_date, stability, difficulty, state
   - create_progress(user_id, card_id) — creates initial card_progress record
3. Write 5+ unit tests in tests/test_study_service.py:
   - test_good_rating_increases_interval
   - test_again_rating_resets_to_today
   - test_daily_five_returns_max_five
   - test_daily_returns_empty_when_nothing_due
   - test_free_user_sees_only_foundation_cards
4. Run: python -m pytest tests/test_study_service.py -v

Commit: git add -A && git commit -m "feat(study): FSRS study service with scheduling"
```

### P1-S11: Study API Routes + Integration Tests

```
Read AGENTS.md. Read docs/specs/phase-1/05-fsrs-daily-review.md.

1. Create app/api/routes/study.py with:
   - GET /api/v1/study/daily — calls study_service.get_daily_review
   - POST /api/v1/study/review — calls study_service.review_card
   - GET /api/v1/study/progress — returns overall study stats
2. Register in main.py.
3. Write integration tests in tests/test_study_api.py:
   - test_get_daily_review — returns cards
   - test_review_card — updates schedule
   - test_requires_auth — 401
   - test_review_nonexistent_card — 404
4. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(study): study API routes — closes spec #05" && git push
```

## --- NEW SESSION --- Phase 1D: Study UI (Tasks 1.5–1.7)

### P1-S12: Spec — Study Dashboard UI

```
Read AGENTS.md. Create docs/specs/phase-1/06-study-dashboard-ui.md with:

UI spec for the Study Dashboard page showing all card categories as a grid. Each card shows: category name, icon, card count, progress bar (cards studied / total). Free users see locked state on non-foundation categories. Include mobile layout (single column), component breakdown, and API calls needed. Do NOT write code yet.
```

### P1-S13: Study Dashboard UI

```
Read AGENTS.md. Read docs/specs/phase-1/06-study-dashboard-ui.md.

1. Create src/pages/StudyDashboard.tsx — category grid page.
2. Create src/components/study/CategoryCard.tsx — individual category card.
3. Use useQuery to fetch from GET /api/v1/cards (categories list).
4. Show locked state for non-foundation categories if user is free tier.
5. Add route in App.tsx: /study → StudyDashboard.
6. Add PostHog capture: posthog.capture('study_dashboard_viewed').
7. Dark mode, mobile-first, Framer Motion for card entrance animations.
8. Manual test in browser: all categories visible, counts correct.

Commit: git add -A && git commit -m "feat(ui): study dashboard category grid — closes spec #06"
```

### P1-S14: Spec + Implement — Card Viewer UI

```
Read AGENTS.md. Create docs/specs/phase-1/07-card-viewer-ui.md, then implement:

1. Create src/pages/CardViewer.tsx — single card page with flip animation.
2. Create src/components/study/FlipCard.tsx — front (question) / back (answer) with flip.
3. Add 4-tier tabs on the answer side: Concept, Production, Example, Quiz.
4. Create src/components/study/QuizPanel.tsx — multiple choice or free-form quiz.
5. After quiz submit, call POST /api/v1/study/review with the user's self-rating.
6. Add PostHog captures: card_viewed, quiz_submitted, card_reviewed.
7. Route: /study/card/:id → CardViewer.
8. Manual test: flip works, quiz submits, rating updates.

Commit: git add -A && git commit -m "feat(ui): card viewer with flip + quiz — closes spec #07"
```

### P1-S15: Daily 5 UI

```
Read AGENTS.md. Read docs/specs/phase-1/05-fsrs-daily-review.md.

1. Create src/pages/DailyReview.tsx — shows the FSRS daily queue.
2. Use useQuery to fetch GET /api/v1/study/daily.
3. Show cards one at a time with the CardViewer component.
4. After rating each card, show the next one. Track completed vs total_due.
5. When all done: "All caught up! 🎉" state.
6. When nothing due: show the same "All caught up!" message.
7. Add PostHog captures: daily_review_started, daily_review_completed.
8. Route: /study/daily → DailyReview.
9. Manual test: shows due cards, ratings work, queue empties.

Commit: git add -A && git commit -m "feat(ui): Daily 5 FSRS queue UI" && git push
```

## --- NEW SESSION --- Phase 1E: ATS Bridge + Onboarding (Tasks 1.8–1.9)

### P1-S16: Spec — ATS Card Mapping

```
Read AGENTS.md. Read .agent/skills/ats-card-bridge.md. Create docs/specs/phase-1/08-ats-card-mapping.md:

Problem: After ATS scan, user sees gaps but no connection to study cards.
Solution: Map ATS skill gaps to card categories via tag matching (and optionally pgvector similarity).

Include: mapping service API, how gaps map to categories (tag join), response schema showing gap → recommended categories, and test plan. Do NOT write code yet.
```

### P1-S17: Gap Mapping Service + API

```
Read AGENTS.md. Read docs/specs/phase-1/08-ats-card-mapping.md. Read .agent/skills/ats-card-bridge.md.

1. Create app/services/gap_mapping_service.py:
   - map_gaps_to_categories(gaps: list[str]) → returns list of { gap, matching_categories[] }
   - Logic: for each gap tag, find categories where the gap tag is in the category's tags or card tags
   - Fallback: if no exact tag match, use pgvector similarity on the gap text vs card embeddings
2. Create app/api/routes/onboarding.py:
   - GET /api/v1/onboarding/recommendations?scan_id=X — returns gap → category mapping
3. Write tests in tests/test_gap_mapping.py:
   - test_rag_gap_maps_to_rag_category
   - test_unknown_gap_returns_empty_or_fallback
   - test_multiple_gaps_return_multiple_categories
4. Run: python -m pytest tests/test_gap_mapping.py -v

Commit: git add -A && git commit -m "feat(bridge): ATS gap to card category mapping — closes spec #08"
```

### P1-S18: Onboarding Flow UI

```
Read AGENTS.md. Create docs/specs/phase-1/09-onboarding-flow.md, then implement:

1. Create src/pages/Onboarding.tsx — shown after ATS scan completes.
2. Shows: "Your ATS score: 72. We found gaps in:" → list of gaps.
3. Each gap shows the mapped card category with a "Start studying" CTA.
4. Clicking a gap → navigates to StudyDashboard filtered to that category.
5. "Skip for now" button → goes to full StudyDashboard.
6. Add PostHog captures: onboarding_started, gap_card_clicked, onboarding_completed.
7. Wire it up: after ATS scan success → redirect to /onboarding?scan_id=X.
8. Manual test: scan resume → see gaps → click gap → lands on correct category.

Commit: git add -A && git commit -m "feat(onboarding): post-ATS scan gap-to-cards flow — closes spec #09" && git push
```

## --- NEW SESSION --- Phase 1F: Analytics + Stripe + Gating (Tasks 1.10–1.12)

### P1-S19: PostHog Setup

```
Read AGENTS.md. Read .agent/skills/analytics.md. Create docs/specs/phase-1/10-posthog-analytics.md, then implement:

1. Backend: pip install posthog. Create app/core/analytics.py with a PostHog client initialized from POSTHOG_API_KEY env var. Export a track(user_id, event, properties) function.
2. Frontend: npm install posthog-js. Initialize PostHog in main.tsx or App.tsx with VITE_POSTHOG_KEY.
3. Add captures to existing features:
   - Backend: ats_scanned (in tracker service), card_reviewed (in study service)
   - Frontend: card_viewed (CardViewer), paywall_hit (when free user blocked), study_dashboard_viewed
4. Verify: open PostHog dashboard → events are flowing in.
5. Do NOT write extensive tests for analytics — just verify events appear.

Commit: git add -A && git commit -m "feat(analytics): PostHog instrumentation — closes spec #10"
```

### P1-S20: Spec — Stripe Integration

```
Read AGENTS.md. Read .agent/skills/payments.md. Create docs/specs/phase-1/11-stripe-integration.md:

Include: Stripe Checkout Session flow, webhook handling (checkout.session.completed, customer.subscription.deleted), updating user.plan, PaywallModal component, and test plan (mock Stripe API). Do NOT write code yet.
```

### P1-S21: Stripe Backend

```
Read AGENTS.md. Read docs/specs/phase-1/11-stripe-integration.md. Read .agent/skills/payments.md.

1. Create app/services/payment_service.py:
   - create_checkout_session(user_id) → returns Stripe Checkout Session URL
   - handle_webhook(payload, signature) → processes checkout.session.completed, customer.subscription.deleted
2. Create app/api/routes/payments.py:
   - POST /api/v1/payments/checkout — creates session, returns URL
   - POST /api/v1/payments/webhook — Stripe webhook handler (no auth, uses Stripe signature verification)
3. Add `stripe_customer_id` and `plan` fields to User model if not present. Migration.
4. Write tests in tests/test_payments.py:
   - test_create_checkout_session (mock Stripe)
   - test_webhook_activates_pro (mock webhook payload)
   - test_webhook_cancels_pro
   - test_requires_auth_for_checkout
5. Run: python -m pytest tests/test_payments.py -v

Commit: git add -A && git commit -m "feat(payments): Stripe checkout + webhook — closes spec #11"
```

### P1-S22: Stripe Frontend + Free Tier Gating

```
Read AGENTS.md. Read docs/specs/phase-1/11-stripe-integration.md.

1. Create src/components/PaywallModal.tsx — shown when free user tries to access non-foundation content.
2. "Upgrade to Pro — $49/mo" button → calls POST /api/v1/payments/checkout → redirects to Stripe.
3. Add gating logic: in StudyDashboard and CardViewer, if user.plan == "free" and card is not foundation → show PaywallModal.
4. Add PostHog captures: paywall_hit, checkout_started, payment_completed (on return from Stripe).
5. Manual test: log in as free user → browse → hit limit → see paywall → click upgrade.
6. Run: npx vitest run

Commit: git add -A && git commit -m "feat(payments): paywall modal + free tier gating" && git push
```

### P1-S23: Phase 1 Final Verification

```
Read AGENTS.md.

Phase 1 final check:
1. Run full backend test suite: python -m pytest tests/ -v --tb=short
2. Run full frontend test suite: npx vitest run
3. Verify the complete user journey manually on localhost:
   - Sign in → ATS scan → see gaps → onboarding → click gap → category
   - Browse cards → flip → quiz → rate → Daily 5 queue
   - Free user: hit 15-card wall → see PaywallModal
4. Verify PostHog: check that ats_scanned, card_viewed, paywall_hit events appear in dashboard.
5. Push to main (CI/CD deploys): git push
6. Verify production URL: same journey works on deployed app.
7. Update all Phase 1 spec statuses to Done.

Commit: git add -A && git commit -m "chore: phase 1 complete — all specs done" && git push
```

---

# ═══════════════════════════════════════════
# PHASE 2: Retention + Conversion Engine
# ═══════════════════════════════════════════

## --- NEW SESSION --- Phase 2A: Gamification (Tasks 2.1–2.3)

### P2-S1: Spec — Streaks + XP + Badges

```
Read AGENTS.md. Read .agent/skills/gamification.md. Create docs/specs/phase-2/12-streaks-xp-badges.md:

Include: gamification_stats table (user_id, current_streak, longest_streak, total_xp, last_active_date), badge definitions (list of badges and earn conditions), XP award rules (10 per review, 25 per quiz, 50 per daily complete), streak rules (increment on daily activity, reset on miss, freeze for Pro), API contract for GET /api/v1/gamification/stats and POST /api/v1/gamification/award-xp. Do NOT write code yet.
```

### P2-S2: Gamification Models + Service

```
Read AGENTS.md. Read docs/specs/phase-2/12-streaks-xp-badges.md. Read .agent/skills/gamification.md.

1. Create app/models/gamification.py: GamificationStats model, Badge model, UserBadge model.
2. Create Alembic migration and apply.
3. Create app/services/gamification_service.py:
   - award_xp(user_id, amount, source) — adds XP, checks badge thresholds
   - update_streak(user_id) — increments streak if active today, resets if missed
   - get_stats(user_id) — returns current stats
4. Write tests in tests/test_gamification.py:
   - test_xp_awarded_correctly
   - test_streak_increments_on_daily_activity
   - test_streak_resets_on_missed_day
   - test_badge_earned_at_threshold
5. Run: python -m pytest tests/test_gamification.py -v

Commit: git add -A && git commit -m "feat(gamification): streaks, XP, badges service"
```

### P2-S3: Wire Gamification into Study Flow

```
Read AGENTS.md. Read docs/specs/phase-2/12-streaks-xp-badges.md.

1. In study_service.review_card(): after recording the review, call gamification_service.award_xp(user_id, 10, "review").
2. When daily review is completed (all 5 rated): award 50 XP bonus.
3. After any review: call gamification_service.update_streak(user_id).
4. Create API route: GET /api/v1/gamification/stats.
5. Update existing study tests to verify XP is awarded.
6. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(gamification): wire XP and streaks into study flow"
```

### P2-S4: Gamification UI

```
Read AGENTS.md. Read docs/specs/phase-2/12-streaks-xp-badges.md.

1. Create src/components/profile/StreakBadge.tsx — shows current streak + flame icon in header.
2. Create src/components/profile/XPBar.tsx — progress bar showing XP toward next level.
3. Create src/pages/Profile.tsx — shows all stats: streak, XP, badges earned, study history.
4. Add StreakBadge to the main layout/navbar so it's always visible.
5. Add PostHog captures: streak_incremented, badge_earned.
6. Route: /profile → Profile.
7. Manual test: complete a review → streak badge updates → XP bar fills.

Commit: git add -A && git commit -m "feat(ui): gamification UI — streaks, XP, badges — closes spec #12" && git push
```

## --- NEW SESSION --- Phase 2B: Skill Radar + Heatmap (Task 2.3)

### P2-S5: Spec + Implement — Skill Radar + Heatmap

```
Read AGENTS.md. Create docs/specs/phase-2/13-skill-radar-heatmap.md, then implement:

Backend:
1. Create app/services/progress_service.py:
   - get_category_coverage(user_id) → returns { category, total_cards, studied, mastery_pct } for each category
   - get_activity_heatmap(user_id, days=90) → returns { date, review_count }[] for the last 90 days
2. Create API routes: GET /api/v1/progress/radar, GET /api/v1/progress/heatmap
3. Write tests: test_radar_returns_all_categories, test_heatmap_shows_activity_days

Frontend:
4. Create src/components/progress/SkillRadar.tsx — radar/spider chart using recharts showing category mastery.
5. Create src/components/progress/ActivityHeatmap.tsx — GitHub-style contribution heatmap.
6. Add both to the Profile page.
7. Manual test: study some cards → radar shows coverage → heatmap shows today's activity.

Commit: git add -A && git commit -m "feat(progress): skill radar + activity heatmap — closes spec #13" && git push
```

## --- NEW SESSION --- Phase 2C: Mission Mode (Tasks 2.4–2.5)

### P2-S6: Spec — Mission Mode

```
Read AGENTS.md. Read .agent/skills/mission-mode.md. Create docs/specs/phase-2/14-mission-mode.md:

Include: missions table (user_id, target_date, category_ids, daily_target, status, created_at), mission_days table (mission_id, day_number, cards_target, cards_completed, date), API contract for CRUD + daily pull, and the scheduling algorithm (total_cards / days_remaining = daily_target, FSRS-prioritized within selected categories). Do NOT write code yet.
```

### P2-S7: Mission Mode Backend

```
Read AGENTS.md. Read docs/specs/phase-2/14-mission-mode.md. Read .agent/skills/mission-mode.md.

1. Create models: Mission, MissionDay. Migration.
2. Create app/services/mission_service.py:
   - create_mission(user_id, target_date, category_ids) — calculates daily targets
   - get_active_mission(user_id) — returns current mission with countdown
   - get_mission_daily_cards(user_id) — returns today's card set (FSRS-prioritized from mission categories)
   - complete_mission_day(user_id) — marks day done, awards XP
3. Create app/api/routes/mission.py: POST /create, GET /active, GET /daily, POST /complete-day
4. Write tests in tests/test_mission.py:
   - test_create_mission_calculates_daily_target
   - test_daily_cards_from_mission_categories
   - test_countdown_decrements
   - test_mission_complete
5. Run: python -m pytest tests/test_mission.py -v

Commit: git add -A && git commit -m "feat(mission): Mission Mode backend service — closes spec #14"
```

### P2-S8: Mission Mode UI

```
Read AGENTS.md. Read docs/specs/phase-2/14-mission-mode.md.

1. Create src/pages/MissionMode.tsx — main mission page.
2. Create src/components/mission/MissionSetup.tsx — form: select categories, pick target date.
3. Create src/components/mission/Countdown.tsx — "12 days left" with progress ring.
4. Create src/components/mission/DailyTarget.tsx — "8 cards today" with progress bar.
5. Mission daily cards use the same CardViewer component.
6. When all daily cards done → celebration state + XP bonus.
7. Add PostHog captures: mission_created, mission_day_completed, mission_completed.
8. Route: /mission → MissionMode.
9. Manual test: create mission → see countdown → study daily cards → day completes.

Commit: git add -A && git commit -m "feat(ui): Mission Mode UI — closes spec #14" && git push
```

## --- NEW SESSION --- Phase 2D: Daily Email (Tasks 2.6–2.7)

### P2-S9: Spec — Daily Email

```
Read AGENTS.md. Read .agent/skills/notifications.md. Create docs/specs/phase-2/15-daily-email.md:

Include: email_preferences table (user_id, daily_reminder: bool, frequency, timezone), Resend API integration, email template (cards due + streak), cron/scheduled task approach, and test plan (mock email send). Also create docs/specs/phase-2/16-email-preferences.md for the opt-out API. Do NOT write code yet.
```

### P2-S10: Email Service + Preferences Backend

```
Read AGENTS.md. Read docs/specs/phase-2/15-daily-email.md. Read .agent/skills/notifications.md.

1. pip install resend (add to requirements.txt)
2. Create app/models/email_preference.py: user_id, daily_reminder (bool, default True), timezone (String, default "UTC").
3. Migration.
4. Create app/services/email_service.py: send_email(to, subject, html_body) using Resend API.
5. Create app/services/reminder_service.py:
   - get_users_needing_reminder() — users with due cards AND daily_reminder=True
   - send_daily_reminders() — for each user, count due cards + streak, send email
6. Create app/api/routes/email_prefs.py: GET + PUT /api/v1/email-preferences
7. Create app/templates/daily_reminder.html — simple email template.
8. Write tests (mock Resend):
   - test_reminder_sent_to_opted_in_user
   - test_no_reminder_for_opted_out_user
   - test_email_contains_card_count_and_streak
9. Run: python -m pytest tests/test_email.py -v

Commit: git add -A && git commit -m "feat(email): daily reminder service + preferences — closes specs #15, #16"
```

### P2-S11: Email Preferences UI + Phase 2 Final Verification

```
Read AGENTS.md.

1. Create src/components/settings/EmailPreferences.tsx — toggle for daily reminders + timezone picker.
2. Add to Profile/Settings page.
3. Manual test: toggle off → verify (in test) no email sent.

Then Phase 2 final check:
4. Run full test suites: python -m pytest tests/ -v && npx vitest run
5. Verify manually:
   - Study cards → streak increments → XP awards
   - Skill radar shows coverage → heatmap shows activity
   - Create mission → countdown → daily targets → complete day
   - Email preferences toggle works
6. Push to main: git push
7. Verify on production URL.
8. Update all Phase 2 spec statuses to Done.

Commit: git add -A && git commit -m "chore: phase 2 complete — all specs done" && git push
```

---

# ═══════════════════════════════════════════
# PHASE 3: Content Pipeline + Marketing
# ═══════════════════════════════════════════

## --- NEW SESSION --- Phase 3A: Admin Panel (Tasks 3.1–3.2)

### P3-S1: Spec — Admin Card CRUD

```
Read AGENTS.md. Read .agent/skills/admin-panel.md. Create docs/specs/phase-3/17-admin-card-crud.md:

Include: all CRUD endpoints (POST/PUT/DELETE /api/v1/admin/cards), bulk CSV import endpoint, require_admin on all routes, request/response schemas, and test plan. Do NOT write code yet.
```

### P3-S2: Admin CRUD Backend

```
Read AGENTS.md. Read docs/specs/phase-3/17-admin-card-crud.md. Read .agent/skills/admin-panel.md.

1. Create app/services/card_admin_service.py: create_card, update_card, delete_card, bulk_import_csv.
2. Create app/api/routes/admin.py with all CRUD endpoints. Every route uses Depends(require_admin).
3. Write tests in tests/test_admin_api.py:
   - test_admin_can_create_card
   - test_admin_can_update_card
   - test_admin_can_delete_card
   - test_non_admin_gets_403
   - test_bulk_import
4. Run: python -m pytest tests/test_admin_api.py -v

Commit: git add -A && git commit -m "feat(admin): card CRUD API — closes spec #17"
```

### P3-S3: AI Card Generation

```
Read AGENTS.md. Create docs/specs/phase-3/18-ai-card-generation.md, then implement:

1. Create app/services/ai_card_service.py:
   - generate_card_draft(topic, difficulty) → uses Gemini to generate question, answer, tags
   - Returns a CardDraft (not saved — admin reviews before publish)
2. Create POST /api/v1/admin/cards/generate — admin-only, returns draft.
3. Write tests: test_generates_valid_card_structure (mock Gemini response).
4. Run tests.

Commit: git add -A && git commit -m "feat(admin): AI card generation — closes spec #18"
```

### P3-S4: Admin Panel UI

```
Read AGENTS.md.

1. Create src/pages/AdminPanel.tsx — card management dashboard (admin-only route).
2. Table of all cards with edit/delete buttons.
3. Create card form (manual or AI-assisted).
4. Bulk CSV upload with drag-and-drop.
5. AI generate button: enter topic → see draft → approve/edit → save.
6. Route: /admin → AdminPanel (redirect non-admins to home).
7. Manual test: create card, edit card, delete card, AI generate, bulk import.

Commit: git add -A && git commit -m "feat(ui): admin panel UI" && git push
```

## --- NEW SESSION --- Phase 3B: Landing Page + Polish (Tasks 3.3–3.6)

### P3-S5: Landing Page

```
Read AGENTS.md. Create docs/specs/phase-3/19-landing-page.md, then implement:

1. Create src/pages/LandingPage.tsx — marketing landing page:
   - Hero: "Ace your next engineering interview" + CTA
   - How it works: Scan → Study → Ace (3-step visual)
   - Pricing: Free tier vs Pro ($49/mo)
   - Social proof placeholder
   - Footer with links
2. Mobile-responsive, dark mode, fast load.
3. CTA buttons → /login (for sign up) or /study (if already logged in).
4. Add PostHog captures: landing_page_viewed, cta_clicked.
5. Route: / → LandingPage (when not logged in).
6. Manual test: looks good on desktop + mobile.

Commit: git add -A && git commit -m "feat(marketing): landing page — closes spec #19"
```

### P3-S6: Onboarding Polish

```
Read AGENTS.md. Create docs/specs/phase-3/20-onboarding-polish.md, then implement:

1. Add persona picker to the onboarding flow:
   - "I'm preparing for an interview" → recommend Mission Mode
   - "I want to stay sharp" → recommend Daily 5
   - "I'm exploring for my team" → recommend Browse All
2. Add a brief guided tour (3-4 tooltip steps) on first login.
3. Store onboarding_completed flag on user to not show again.
4. Manual test: new user → persona picker → guided tour → lands on right page.

Commit: git add -A && git commit -m "feat(onboarding): persona picker + guided tour — closes spec #20"
```

### P3-S7: My Experience + Feedback + Phase 3 Final

```
Read AGENTS.md.

Implement Task 3.5 — "My Experience" AI generation:
1. Create app/services/experience_service.py: generate_experience(user_id, topic) — uses study history + Gemini to create a personalized "experience" narrative the user can reference.
2. Create POST /api/v1/study/experience — generates and returns.
3. Frontend: add "Generate My Experience" button on Profile page.

Implement Task 3.6 — Per-card feedback:
4. Create app/models/card_feedback.py: user_id, card_id, rating (1-5), comment, created_at.
5. Create POST /api/v1/cards/{id}/feedback + GET /api/v1/admin/feedback.
6. Frontend: add thumbs up/down + optional comment after card review.

Then Phase 3 final check:
7. Run full test suites.
8. Verify admin panel, landing page, onboarding, feedback all work on production.
9. Update all Phase 3 spec statuses to Done.

Commit: git add -A && git commit -m "chore: phase 3 complete — all specs done" && git push
```

---

# ═══════════════════════════════════════════
# PHASE 4: Hardening + Observability
# ═══════════════════════════════════════════

## --- NEW SESSION --- Phase 4A: Monitoring + Performance

### P4-S1: Sentry Error Monitoring

```
Read AGENTS.md. Create docs/specs/phase-4/22-error-monitoring.md, then implement:

Backend:
1. pip install sentry-sdk[fastapi] (add to requirements.txt)
2. Initialize Sentry in app/main.py with SENTRY_DSN from env.
3. Verify: raise a test exception → appears in Sentry dashboard.

Frontend:
4. npm install @sentry/react
5. Initialize in main.tsx with VITE_SENTRY_DSN.
6. Add ErrorBoundary component.
7. Verify: trigger a frontend error → appears in Sentry.

Commit: git add -A && git commit -m "feat(monitoring): Sentry error tracking — closes spec #22"
```

### P4-S2: PostHog Dashboards

```
Read AGENTS.md. Read .agent/skills/analytics.md. Create docs/specs/phase-4/23-posthog-dashboards.md.

This is mostly manual PostHog configuration. Help me:
1. List all the PostHog events we should have by now (from all phases).
2. Define 3 funnels to build in PostHog:
   - Acquisition: sign_up → ats_scanned → card_viewed → paywall_hit → payment_completed
   - Retention: daily_review_started on Day 1 → Day 7 → Day 30
   - Mission: mission_created → 50% days complete → mission_completed
3. Define a retention dashboard: DAU, WAU, MAU, DAU/MAU ratio.
4. Verify all expected events are actually flowing by checking PostHog live events.
5. Document any missing events and add them.

Commit: git add -A && git commit -m "feat(analytics): PostHog dashboards documented — closes spec #23" && git push
```

### P4-S3: Performance + Rate Limiting

```
Read AGENTS.md. Create docs/specs/phase-4/24-performance-hardening.md, then implement:

1. Add rate limiting middleware to FastAPI:
   - pip install slowapi
   - 100 requests/minute per user for API endpoints
   - 10 requests/minute for auth endpoints
   - Return 429 Too Many Requests when exceeded
2. Write test: test_rate_limit_returns_429
3. Run Lighthouse audit on the frontend (help me interpret results):
   - Target: > 90 performance score
   - Target: < 2s TTFB, < 3s LCP
4. If Lighthouse flags issues, suggest specific fixes.
5. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(security): rate limiting + performance audit — closes spec #24"
```

### P4-S4: Backup + Custom Domain + Final

```
Read AGENTS.md.

1. Document the backup/restore procedure for Railway PostgreSQL:
   - How to create a backup
   - How to restore from backup
   - Write a test script that creates a backup and verifies it
2. Help me configure the custom domain:
   - DNS settings for skillforge.app (or whatever domain)
   - SSL certificate (Railway/Vercel handle this automatically)
   - Update CORS origins, Stripe webhook URL, Google OAuth redirect
3. Verify: curl https://skillforge.app/health → 200

Then final Phase 4 check:
4. Run all tests.
5. Verify Sentry captures errors.
6. Verify PostHog dashboards are populated.
7. Verify rate limiting works.
8. Update all Phase 4 spec statuses to Done.

Commit: git add -A && git commit -m "chore: phase 4 complete — production ready 🚀" && git push
```

---

# ═══════════════════════════════════════════
# REFERENCE: Session Strategy
# ═══════════════════════════════════════════

| Session | Slices | Phase | Focus |
|---------|--------|-------|-------|
| P0-Auth | S1–S4 | 0 | Auth unification + user roles |
| P0-Deploy | S5–S8 | 0 | Skeleton deploy + CI/CD + verify |
| P1A | S1–S4 | 1 | Card extraction + embeddings |
| P1B | S5–S7 | 1 | Cards API |
| P1C | S8–S11 | 1 | FSRS study engine |
| P1D | S12–S15 | 1 | Study UI (dashboard, viewer, daily) |
| P1E | S16–S18 | 1 | ATS bridge + onboarding |
| P1F | S19–S23 | 1 | Analytics + Stripe + gating + verify |
| P2A | S1–S4 | 2 | Gamification (streaks, XP, badges) |
| P2B | S5 | 2 | Skill radar + heatmap |
| P2C | S6–S8 | 2 | Mission Mode |
| P2D | S9–S11 | 2 | Daily email + verify |
| P3A | S1–S4 | 3 | Admin panel + AI card gen |
| P3B | S5–S7 | 3 | Landing page + polish + verify |
| P4A | S1–S4 | 4 | Monitoring + perf + final |

**Total: ~15 sessions, ~55 slices across 15 weeks.**

---

# ═══════════════════════════════════════════
# REFERENCE: Contingency Prompts
# ═══════════════════════════════════════════

**If Claude Code drifts or gets confused:**
```
Stop. Re-read docs/specs/phase-N/NN-feature.md. Focus only on [specific AC]. Do not touch any other files.
```

**If a test fails 3+ times:**
```
Stop. Do not attempt another fix. Print the exact error, explain your hypothesis for the root cause, and list 2-3 possible fixes. Wait for me to decide.
```

**If you need to verify DB state:**
```
Connect to the hireport database with psql and run: \dt to list tables, \d table_name to describe a specific table, \dx to list extensions. Show me the output.
```

**If you need to verify production:**
```
curl -s https://yourdomain.com/health and show me the response. Then curl one API endpoint to verify data is flowing.
```

**If a slice is taking too long (>15 min of Claude thinking):**
```
Stop. You're overcomplicating this. Break the current task into 2 smaller pieces. Tell me what those pieces are, and I'll tell you which one to do first.
```

**If you need to reset after a bad session:**
```
Read AGENTS.md. Read CLAUDE.md. List the files you changed in the last session. Run git diff --stat to show me what's modified. Run the full test suite. Tell me what's broken and what's working.
```
