# SkillForge — Claude Code Prompts (All Phases)

> **How to use**: Copy-paste each prompt into Claude Code **one at a time**.
> Wait for completion, review output, then proceed.
> Start a **new Claude Code session** at every `--- NEW SESSION ---` marker.
> Each session should stay under 5 slices to avoid context degradation.
>
> **Status key**: ✅ DONE | 🔄 IN PROGRESS | ⬜ NOT STARTED
>
> **Start every session with**:
> `Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.`

---

# ═══════════════════════════════════════════
# PHASE 0: Foundation Surgery + Skeleton Deploy
# ═══════════════════════════════════════════
# Status: ✅ Tasks 0.1–0.3 DONE (PostgreSQL migration)
# Remaining: 0.4 (Auth), 0.5 (Roles), 0.6–0.7 (Deploy + CI/CD), 0.8 (Verify)

## --- NEW SESSION --- Phase 0: Auth + Roles

### P0-S1: Spec — Auth Unification ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-0/01-auth-unification.md. If the spec file is empty or doesn't exist, fill out the spec template with precise Acceptance Criteria, API Contract, and Test Plan for unifying the frontend to use the backend's JWT auth system (Google OAuth → backend issues JWT → frontend stores and sends JWT on all API calls). Do NOT write any code yet. Stop after updating the markdown file so I can review it.
```

### P0-S2: Implement — Auth Unification (Backend) ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-0/01-auth-unification.md.

Implement the backend auth changes:
1. Ensure Google OAuth endpoint exists: POST /api/v1/auth/google — accepts Google ID token, verifies it, creates/finds user, returns JWT access + refresh tokens.
2. Ensure GET /api/v1/auth/me returns the current user from the JWT.
3. Ensure Depends(get_current_user) middleware extracts and validates the JWT from the Authorization header.
4. Write tests in tests/test_auth.py: valid token returns user, expired token returns 401, missing token returns 401.
5. Run: python -m pytest tests/test_auth.py -v

Do NOT touch the frontend yet. Stop after backend tests pass.
```

### P0-S3: Implement — Auth Unification (Frontend) ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-0/01-auth-unification.md.

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

### P0-S4: Spec + Implement — User Roles ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-0/02-user-roles.md. If the spec is empty, fill it out first with AC for: adding a `role` column (default "user"), creating a require_admin() dependency that returns 403 for non-admins, and a test plan. Then implement:

1. Add `role: Mapped[str] = mapped_column(String(20), default="user")` to the User model.
2. Create Alembic migration: alembic revision --autogenerate -m "add role column to users"
3. Apply: alembic upgrade head
4. Create a `require_admin` dependency in app/core/deps.py that checks current_user.role == "admin".
5. Write tests in tests/test_user_roles.py: admin user passes, regular user gets 403.
6. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(auth): add user roles and require_admin — closes spec #02"
```

## --- NEW SESSION --- Phase 0: Deploy + CI/CD

### P0-S5: Spec — Skeleton Deploy ⬜

```
Read AGENTS.md. Read CLAUDE.md. Create docs/specs/phase-0/02a-skeleton-deploy.md with the spec template filled out for:

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

### P0-S6: Implement — Skeleton Deploy (Backend to Railway) ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-0/02a-skeleton-deploy.md.

This is a MANUAL task with Claude Code assistance. Help me:

1. Create a Procfile or railway.toml for the backend:
   - Build command: pip install -r requirements.txt
   - Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   - Release command: alembic upgrade head
2. Update app/core/config.py to handle Railway's DATABASE_URL format (they provide postgresql:// not postgresql+asyncpg://, so we need to replace the scheme).
3. Update CORS settings in app/main.py to read ALLOWED_ORIGINS from env and include the Vercel frontend URL.
4. Create a requirements.txt that includes all production dependencies (no dev deps). Include: anthropic, openai, google-genai for the LLM router.
5. List the environment variables I need to set in Railway's dashboard (reference AGENTS.md env var section for the full list including LLM_FAST_MODEL, LLM_REASONING_MODEL, STRIPE_PRO_PRICE_ID_INR).

Do NOT deploy yet — just prepare the files. Stop so I can review, then I'll deploy manually via Railway dashboard.
```

### P0-S7: Implement — CI/CD Pipeline ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-0/02b-cicd-pipeline.md. If the spec doesn't exist, create it first.

Create .github/workflows/ci.yml with:
1. Trigger: push to main, pull requests
2. Job 1 — backend-tests: PostgreSQL 16 + pgvector service container, install deps (including anthropic openai google-genai), run pytest
3. Job 2 — frontend-tests: install deps, run vitest
4. Job 3 — migration-rollback: run alembic upgrade head → downgrade -1 → upgrade head
5. All jobs use the correct Python 3.13 and Node 20 versions.

Do NOT add auto-deploy steps yet (Railway and Vercel handle that via git push detection).

Commit: git add -A && git commit -m "ci: add GitHub Actions pipeline — closes spec #02b"
```

### P0-S8: Verify Production ⬜

```
Read AGENTS.md. Read CLAUDE.md. This is the final Phase 0 verification.

1. Run the full backend test suite locally: python -m pytest tests/ -v --tb=short
2. Run the full frontend test suite: cd hirelens-frontend && npx vitest run
3. Help me verify the deployed app:
   - curl the production backend /health endpoint
   - Check that the frontend loads on the Vercel URL
   - Verify CORS works: frontend → backend API call
4. Update docs/specs/phase-0/02a-skeleton-deploy.md status to Done.
5. Update SESSION-STATE.md: Phase 0 complete, next = P1-S1.
6. Push to main: git add -A && git commit -m "chore: phase 0 complete — all specs done" && git push

Phase 0 is complete. All ATS features work on PostgreSQL, auth is unified, roles exist, app is deployed, CI/CD is active.
```

---

# ═══════════════════════════════════════════
# PHASE 1: Core Study Engine + ATS Bridge
# ═══════════════════════════════════════════
# 15 tasks including enhancements

## --- NEW SESSION --- Phase 1A: Card Extraction + Embeddings (Tasks 1.1–1.2)

### P1-S1: Spec — Card Extraction ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/card-extraction.md. Create docs/specs/phase-1/03-card-extraction.md with the spec template:

Problem: 177 study cards are hardcoded in JSX files. They need to be in PostgreSQL with embeddings for search and FSRS scheduling.
Solution: Extract cards from JSX, create Card + Category models, seed the database, generate embeddings.

Include: data model for cards table and categories table (columns, types, indexes, deleted_at soft-delete column), the extraction script approach, and test plan (count verification, embedding non-null check). Do NOT write code yet.
```

### P1-S2: Card + Category ORM Models ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/03-card-extraction.md. Read .agent/skills/database-schema.md.

1. Create app/models/card.py with Card model: id (str PK), category_id (FK), question (Text), answer (Text), difficulty (String), tags (JSON array), embedding (Vector(1536), nullable), deleted_at (DateTime, nullable, default None), created_at, updated_at.
2. Create app/models/category.py with Category model: id (str PK), name (String), icon (String), color (String), display_order (Integer), source (String, nullable — "foundation" for free-tier), tags (JSON array, for gap mapping).
3. Register both models in app/models/__init__.py.
4. Create Alembic migration: alembic revision --autogenerate -m "add cards and categories tables"
5. Review the generated migration, then apply: alembic upgrade head
6. Test rollback: alembic downgrade -1 && alembic upgrade head
7. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(cards): add Card and Category models + migration"
```

### P1-S3: Card Extraction Script ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/03-card-extraction.md. Read .agent/skills/card-extraction.md.

1. Read the JSX files where cards are currently defined (check hirelens-frontend/src/data/ or wherever they live). List all categories and card counts you find.
2. Create scripts/extract_cards.py that:
   - Parses the JSX/JSON card data
   - Creates Category records
   - Creates Card records with all fields populated
   - Runs as: python scripts/extract_cards.py
3. Run the script against the local database.
4. Verify: psql -d hireport -c "SELECT count(*) FROM cards WHERE deleted_at IS NULL;" → should be 177 (or actual count)
5. Verify: psql -d hireport -c "SELECT name, count(c.id) FROM categories cat JOIN cards c ON c.category_id = cat.id WHERE c.deleted_at IS NULL GROUP BY cat.name;"

Commit: git add -A && git commit -m "feat(cards): extract cards from JSX to PostgreSQL"
```

### P1-S4: Generate Embeddings ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/llm-strategy.md. Read docs/specs/phase-1/03-card-extraction.md.

1. Create app/services/llm_router.py (if it doesn't exist):
   - TaskType enum: FAST, REASONING
   - get_llm_client(task_type) reads LLM_FAST_PROVIDER / LLM_REASONING_PROVIDER from env
   - Supports providers: google (uses GEMINI_API_KEY), anthropic (uses ANTHROPIC_API_KEY), openai (uses OPENAI_API_KEY)
   - Falls back to Google Gemini if provider key not set — log a warning
2. Create scripts/generate_embeddings.py that:
   - Uses the LLM router (FAST task) to generate embeddings
   - Reads all cards without embeddings
   - Generates embedding from question + answer text
   - Updates cards SET embedding = Vector result
3. Run the script.
4. Verify: psql -d hireport -c "SELECT count(*) FROM cards WHERE embedding IS NOT NULL AND deleted_at IS NULL;"
5. Write test: test_all_cards_have_embeddings
6. Run: python -m pytest tests/test_card_extraction.py -v

Commit: git add -A && git commit -m "feat(cards): LLM router + generate embeddings for all cards" && git push
```

## --- NEW SESSION --- Phase 1B: Cards API (Task 1.3)

### P1-S5: Spec — Cards API ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Create docs/specs/phase-1/04-cards-api.md with:

Endpoints:
- GET /api/v1/cards — list all categories with card counts
- GET /api/v1/cards/category/{id} — list cards in a category (exclude deleted_at IS NOT NULL)
- GET /api/v1/cards/{id} — get single card (404 if deleted_at IS NOT NULL)
- GET /api/v1/cards/search?q=query — semantic search using pgvector cosine similarity

For each: request params, response schema, auth requirements, error codes. Include plan gating: free users only see categories where source="foundation". Do NOT write code yet.
```

### P1-S6: Cards API — Schemas + Service ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/04-cards-api.md. Read .agent/skills/database-schema.md.

1. Create app/schemas/card.py with Pydantic response models: CardResponse, CategoryResponse (with card_count), CategoryListResponse, CardSearchResult.
2. Create app/services/card_service.py with async methods: list_categories(user), get_cards_by_category(category_id, user), get_card(card_id), search_cards(query, user).
3. All queries MUST filter WHERE deleted_at IS NULL.
4. For search: use pgvector cosine_distance to find the top 10 most similar cards to the query embedding.
5. For plan gating: if user.plan == "free", filter to only categories where source="foundation".
6. Do NOT create the route yet. Stop so I can review the service logic.
```

### P1-S7: Cards API — Routes + Tests ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/04-cards-api.md.

1. Create app/api/routes/cards.py with the 4 endpoints from the spec.
2. Register the router in app/main.py.
3. Write tests in tests/test_cards_api.py:
   - test_list_categories — returns categories with card_count
   - test_get_cards_by_category — returns non-deleted cards only
   - test_get_card — returns single card; 404 for deleted card
   - test_search_cards — returns relevant results
   - test_requires_auth — 401 without token
   - test_free_user_sees_only_foundation — free user gets filtered categories
   - At least 10 assertions total.
4. Run: python -m pytest tests/test_cards_api.py -v

Commit: git add -A && git commit -m "feat(cards): cards API with search and plan gating — closes spec #04" && git push
```

## --- NEW SESSION --- Phase 1C: FSRS Study Engine (Task 1.4)

### P1-S8: Spec — FSRS Daily Review ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/study-engine.md. Create docs/specs/phase-1/05-fsrs-daily-review.md:

Include: card_progress table schema, FSRS state machine (New → Learning → Review → Relearning), API contract for GET /api/v1/study/daily and POST /api/v1/study/review, and test plan with 5+ unit test cases. Do NOT write code yet.
```

### P1-S9: CardProgress Model + Migration ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/05-fsrs-daily-review.md. Read .agent/skills/database-schema.md.

1. Create app/models/card_progress.py with: id, user_id (FK), card_id (FK), stability (Float), difficulty_fsrs (Float), due_date (DateTime), state (String — new/learning/review/relearning), reps (Integer), lapses (Integer), last_reviewed (DateTime), created_at, updated_at.
2. Create Alembic migration and apply.
3. Test rollback cycle.
4. Run existing tests to verify nothing broke.

Commit: git add -A && git commit -m "feat(study): add card_progress model + migration"
```

### P1-S10: Study Service — FSRS Scheduling ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/05-fsrs-daily-review.md. Read .agent/skills/study-engine.md.

1. Create app/schemas/study.py with: DailyReviewResponse, ReviewRequest, ReviewResponse.
2. Create app/services/study_service.py with:
   - get_daily_review(user_id) — returns up to 5 cards where due_date <= now AND deleted_at IS NULL, ordered by due_date
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

### P1-S11: Study API Routes + Integration Tests ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/05-fsrs-daily-review.md.

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

### P1-S12: Spec — Study Dashboard UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/design-system.md. Create docs/specs/phase-1/06-study-dashboard-ui.md:

UI spec for the Study Dashboard showing all card categories as a grid. Each card shows: category name, icon, card count, progress bar. Free users see locked state on non-foundation categories. Use CSS variables from design system — no hardcoded colors. Include mobile layout, component breakdown, and API calls needed. Do NOT write code yet.
```

### P1-S13: Study Dashboard UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/06-study-dashboard-ui.md. Read .agent/skills/design-system.md.

1. Create src/pages/StudyDashboard.tsx — category grid page.
2. Create src/components/study/CategoryCard.tsx — individual category card.
3. Use useQuery to fetch from GET /api/v1/cards (categories list).
4. Show locked state for non-foundation categories if user is free tier.
5. Add route in App.tsx: /study → StudyDashboard.
6. Add PostHog capture: posthog.capture('study_dashboard_viewed').
7. Use CSS variables for all colors (--bg-primary, --text-primary, etc.)
8. Mobile-first, Framer Motion for card entrance animations.
9. Manual test in browser: all categories visible, counts correct.

Commit: git add -A && git commit -m "feat(ui): study dashboard category grid — closes spec #06"
```

### P1-S14: Spec + Implement — Card Viewer UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/design-system.md. Create docs/specs/phase-1/07-card-viewer-ui.md, then implement:

1. Create src/pages/CardViewer.tsx — single card page with flip animation.
2. Create src/components/study/FlipCard.tsx — front (question) / back (answer) with flip.
3. Add 4-tier tabs on the answer side: Concept, Production, Example, Quiz.
4. Create src/components/study/QuizPanel.tsx — multiple choice or free-form quiz.
5. After quiz submit, call POST /api/v1/study/review with the user's self-rating.
6. Add PostHog captures: card_viewed, quiz_submitted, card_reviewed.
7. Route: /study/card/:id → CardViewer.
8. Use CSS variables — no hardcoded hex colors.
9. Manual test: flip works, quiz submits, rating updates.

Commit: git add -A && git commit -m "feat(ui): card viewer with flip + quiz — closes spec #07"
```

### P1-S15: Daily 5 UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/05-fsrs-daily-review.md.

1. Create src/pages/DailyReview.tsx — shows the FSRS daily queue.
2. Use useQuery to fetch GET /api/v1/study/daily.
3. Show cards one at a time with the CardViewer component.
4. After rating each card, show the next one. Track completed vs total_due.
5. When all done: "All caught up! 🎉" state.
6. Add PostHog captures: daily_review_started, daily_review_completed.
7. Route: /study/daily → DailyReview.
8. Manual test: shows due cards, ratings work, queue empties.

Commit: git add -A && git commit -m "feat(ui): Daily 5 FSRS queue UI" && git push
```

## --- NEW SESSION --- Phase 1E: ATS Bridge + Onboarding + Enhancements (Tasks 1.8–1.15)

### P1-S16: Spec — ATS Card Mapping ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/ats-card-bridge.md. Create docs/specs/phase-1/08-ats-card-mapping.md:

Problem: After ATS scan, user sees gaps but no connection to study cards.
Solution: Map ATS skill gaps to card categories via tag matching (and optionally pgvector similarity).

Include: mapping service API, how gaps map to categories (tag join on category.tags), response schema showing gap → recommended categories, persona picker fields (target_company: str, target_date: date, persona: "interview-prepper" | "career-climber" | "team-lead"), and test plan. Do NOT write code yet.
```

### P1-S17: Gap Mapping Service + Persona API ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/08-ats-card-mapping.md. Read .agent/skills/ats-card-bridge.md.

1. Create app/services/gap_mapping_service.py:
   - map_gaps_to_categories(gaps: list[str]) → returns list of { gap, matching_categories[] }
   - Fallback: if no exact tag match, use pgvector similarity on gap text vs card embeddings
2. Add to User model: target_company (String, nullable), target_date (Date, nullable), persona (String, nullable).
   Create Alembic migration.
3. Create app/api/routes/onboarding.py:
   - GET /api/v1/onboarding/recommendations?scan_id=X — returns gap → category mapping
   - POST /api/v1/onboarding/persona — saves persona, target_company, target_date to user
4. Write tests:
   - test_rag_gap_maps_to_rag_category
   - test_persona_saved_to_user
5. Run: python -m pytest tests/test_gap_mapping.py -v

Commit: git add -A && git commit -m "feat(bridge): ATS gap mapping + persona fields — closes spec #08"
```

### P1-S18: Onboarding Flow UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Create docs/specs/phase-1/09-onboarding-flow.md, then implement:

1. Create src/pages/Onboarding.tsx — shown after ATS scan completes.
2. Step 1 — Persona picker:
   - "I'm preparing for an interview" → show target_company + target_date fields
   - "I want to stay sharp" → direct to Daily 5
   - "I'm exploring for my team" → direct to Browse All
   POST /api/v1/onboarding/persona with selection.
3. Step 2 — Gap display:
   - Shows gaps found: "You're weak in: RAG, System Design"
   - Each gap shows mapped card category with "Start studying" CTA
4. "Skip for now" → full StudyDashboard.
5. Add PostHog captures: onboarding_started, persona_selected, gap_card_clicked, onboarding_completed.
6. Wire: after ATS scan success → redirect to /onboarding?scan_id=X.
7. Manual test: scan → persona picker → gap display → click gap → correct category.

Commit: git add -A && git commit -m "feat(onboarding): persona picker + gap-to-cards flow — closes specs #09" && git push
```

## --- NEW SESSION --- Phase 1F: Security + Analytics + Stripe (Tasks 1.10–1.15)

### P1-S19: IP Registration Blocking + Free Tier Limits ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/security.md. Create docs/specs/phase-1/11c-ip-registration-blocking.md and docs/specs/phase-1/11a-free-tier-limits.md, then implement:

IP Blocking:
1. Create app/services/registration_guard.py:
   - check_ip_limit(ip: str, redis_client) → raises HTTPException(429) if >= 2 registrations in 30 days
   - Redis key: ip_reg:{ip}, incr on each registration, TTL = 2592000 (30 days)
2. Wire into POST /api/v1/auth/google (registration path only).
3. Write tests: test_first_reg_allowed, test_second_reg_allowed, test_third_reg_blocked.

Free Tier Limits:
4. Create app/services/plan_limits.py:
   - check_interview_question_limit(user_id, redis_client) → raises HTTPException(403, "free_limit_reached") if >= 3 interview Q this month
   - Redis key: interview_q:{user_id}:{YYYY-MM}, TTL = end of month
5. Wire into the interview Q endpoint.
6. Run: python -m pytest tests/test_security.py -v

Commit: git add -A && git commit -m "feat(security): IP registration blocking + free tier interview limits"
```

### P1-S20: Tracker Auto-Populate + PostHog Setup ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/analytics.md. Read .agent/skills/ats-scanner.md.

Tracker auto-populate:
1. Create docs/specs/phase-1/11b-tracker-autopopulate.md.
2. After ATS scan completes, if job title + company are extractable from resume:
   auto-create a tracker entry (status=applied, source=ats_scan, company, role).
3. Add to app/services/tracker_service.py: create_from_scan(user_id, scan_result).
4. Write test: test_tracker_entry_created_after_scan.

PostHog setup:
5. Backend: pip install posthog. Create app/core/analytics.py with track(user_id, event, properties).
6. Frontend: npm install posthog-js. Initialize in main.tsx with VITE_POSTHOG_KEY.
7. Add captures to existing features: ats_scanned, card_reviewed, card_viewed, paywall_hit.
8. Verify events appear in PostHog dashboard.

Commit: git add -A && git commit -m "feat: tracker auto-populate + PostHog analytics — closes spec #10"
```

### P1-S21: Spec — Stripe + Geo Pricing ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/payments.md. Read .agent/skills/geo-pricing.md. Create docs/specs/phase-1/11-stripe-integration.md:

Include: Stripe Checkout Session flow with geo-pricing (USD for most users, INR for Indian IPs), webhook handling (checkout.session.completed, customer.subscription.deleted), updating user.plan, PaywallModal component, and test plan. Also specify: STRIPE_PRO_PRICE_ID (USD $49/mo) and STRIPE_PRO_PRICE_ID_INR (₹999/mo). Do NOT write code yet.
```

### P1-S22: Stripe Backend + Geo Detection ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/11-stripe-integration.md. Read .agent/skills/payments.md. Read .agent/skills/geo-pricing.md.

1. Create app/services/geo_service.py:
   - get_country(ip: str) → returns country code using ip-api.com (free, no key needed)
2. Create app/services/payment_service.py:
   - create_checkout_session(user_id, request) → detects country, uses STRIPE_PRO_PRICE_ID_INR if "IN", else STRIPE_PRO_PRICE_ID
   - handle_webhook(payload, signature) → processes checkout.session.completed, customer.subscription.deleted
   - Idempotency: check Redis for processed evt_{id} before processing. Set Redis key with 24h TTL.
3. Create app/api/routes/payments.py:
   - POST /api/v1/payments/checkout
   - POST /api/v1/payments/webhook (no auth, Stripe signature verification)
4. Add stripe_customer_id and plan fields to User model if not present. Migration.
5. Write tests (mock Stripe + mock geo service):
   - test_indian_ip_gets_inr_price
   - test_non_indian_gets_usd_price
   - test_webhook_activates_pro
   - test_webhook_idempotency (same event twice → processed only once)
6. Run: python -m pytest tests/test_payments.py -v

Commit: git add -A && git commit -m "feat(payments): Stripe + geo-pricing + idempotency — closes spec #11"
```

### P1-S23: Stripe Frontend + Phase 1 Final Verification ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-1/11-stripe-integration.md.

1. Create src/components/PaywallModal.tsx — shown when free user hits limit.
2. Show correct price based on user's detected region (fetch from backend or show both USD/INR).
3. "Upgrade to Pro" button → calls POST /api/v1/payments/checkout → redirects to Stripe.
4. Add gating: if user.plan == "free" and card not foundation → PaywallModal.
5. Add PostHog captures: paywall_hit, checkout_started, payment_completed (on return).
6. Manual test: free user → hit limit → see paywall.

Phase 1 final check:
7. Run full backend tests: python -m pytest tests/ -v --tb=short
8. Run full frontend tests: npx vitest run
9. Verify complete journey manually on localhost and production.
10. Verify PostHog: ats_scanned, card_viewed, paywall_hit, onboarding_started events appear.
11. Update SESSION-STATE.md: Phase 1 complete, next = P2-S1.
12. Push: git push

Commit: git add -A && git commit -m "chore: phase 1 complete — all specs done" && git push
```

---

# ═══════════════════════════════════════════
# PHASE 2: Retention + Conversion Engine
# ═══════════════════════════════════════════

## --- NEW SESSION --- Phase 2A: Gamification (Tasks 2.1–2.3)

### P2-S1: Spec — Streaks + XP + Badges ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/gamification.md. Create docs/specs/phase-2/12-streaks-xp-badges.md:

Include: gamification_stats table (user_id, current_streak, longest_streak, total_xp, last_active_date), badge definitions, XP award rules, streak rules (increment on daily activity, reset on miss, freeze for Pro), API contract for GET /api/v1/gamification/stats. Do NOT write code yet.
```

### P2-S2: Gamification Models + Service ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-2/12-streaks-xp-badges.md. Read .agent/skills/gamification.md.

1. Create app/models/gamification.py: GamificationStats, Badge, UserBadge models.
2. Create Alembic migration and apply.
3. Create app/services/gamification_service.py:
   - award_xp(user_id, amount, source)
   - update_streak(user_id)
   - get_stats(user_id)
4. Write tests in tests/test_gamification.py:
   - test_xp_awarded_correctly
   - test_streak_increments_on_daily_activity
   - test_streak_resets_on_missed_day
   - test_badge_earned_at_threshold
5. Run: python -m pytest tests/test_gamification.py -v

Commit: git add -A && git commit -m "feat(gamification): streaks, XP, badges service"
```

### P2-S3: Wire Gamification + Gamification UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-2/12-streaks-xp-badges.md. Read .agent/skills/design-system.md.

Wire into study flow:
1. In study_service.review_card(): call gamification_service.award_xp(user_id, 10, "review") and update_streak(user_id).
2. When daily review completed: award 50 XP bonus.
3. Create API: GET /api/v1/gamification/stats.
4. Update study tests to verify XP is awarded.
5. Run: python -m pytest tests/ -v --tb=short

Gamification UI:
6. Create src/components/profile/StreakBadge.tsx — streak + flame icon in header. Use CSS variables.
7. Create src/components/profile/XPBar.tsx — XP progress bar.
8. Create src/pages/Profile.tsx — full stats view.
9. Add StreakBadge to navbar.
10. Add PostHog captures: streak_incremented, badge_earned.

Commit: git add -A && git commit -m "feat(gamification): wire + UI — closes spec #12" && git push
```

### P2-S4: Skill Radar + Heatmap ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/design-system.md. Create docs/specs/phase-2/13-skill-radar-heatmap.md, then implement:

1. Backend: GET /api/v1/study/radar — returns per-category coverage (cards_studied / total_cards for each category).
2. Frontend: Create src/components/profile/SkillRadar.tsx using recharts RadarChart. Use CSS variables for colors.
3. Create src/components/profile/ActivityHeatmap.tsx — GitHub-style heatmap of review activity.
4. Add both to Profile page.
5. Manual test: study cards → radar shows coverage → heatmap shows today's activity.

Commit: git add -A && git commit -m "feat(ui): skill radar + activity heatmap — closes spec #13"
```

## --- NEW SESSION --- Phase 2B: Mission Mode (Task 2.4–2.5)

### P2-S5: Spec + Implement — Mission Mode Backend ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/mission-mode.md. Create docs/specs/phase-2/14-mission-mode.md, then implement:

1. Create app/models/mission.py: Mission (id, user_id, target_date, category_ids JSON, daily_target, created_at, completed_at nullable).
2. Migration.
3. Create app/services/mission_service.py:
   - create_mission(user_id, target_date, category_ids) → calculates daily_target = total_cards / days_remaining
   - get_active_mission(user_id) → returns mission with countdown + today's cards
   - complete_mission_day(user_id) → marks day done, awards 75 XP
4. Create app/api/routes/mission.py: POST /api/v1/mission, GET /api/v1/mission/active.
5. Write tests: test_mission_created, test_daily_target_calculated, test_countdown_correct.
6. Run: python -m pytest tests/test_mission.py -v

Commit: git add -A && git commit -m "feat(mission): Mission Mode backend — closes spec #14"
```

### P2-S6: Mission Mode UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-2/14-mission-mode.md. Read .agent/skills/design-system.md.

1. Create src/pages/MissionMode.tsx — mission creation + active mission view.
2. Create src/components/mission/Countdown.tsx — "12 days left" countdown with urgency styling.
3. Create src/components/mission/DailyTarget.tsx — "8 cards today" progress tracker.
4. Mission creation form: target_company (pre-filled from persona if set), target_date, category picker.
5. Add PostHog captures: mission_created, mission_day_completed.
6. Route: /mission → MissionMode.
7. Manual test: create mission → see countdown → cards load → day marked done.

Commit: git add -A && git commit -m "feat(ui): Mission Mode UI" && git push
```

## --- NEW SESSION --- Phase 2C: Daily Email + Phase 2 Final

### P2-S7: Spec + Implement — Daily Email ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/notifications.md. Create docs/specs/phase-2/15-daily-email.md, then implement:

1. pip install resend (add to requirements.txt).
2. Create app/models/email_preference.py: user_id, daily_reminder (bool, default True), timezone (String, default "UTC").
3. Migration.
4. Create app/services/email_service.py: send_email(to, subject, html_body) using Resend API (RESEND_API_KEY env var).
5. Create app/services/reminder_service.py:
   - get_users_needing_reminder() — users with due cards AND daily_reminder=True
   - send_daily_reminders() — count due cards + streak per user, send email
6. Create app/templates/daily_reminder.html — simple email template.
7. Create app/api/routes/email_prefs.py: GET + PUT /api/v1/email-preferences.
8. Write tests (mock Resend): test_reminder_sent, test_no_reminder_for_opted_out_user.
9. Run: python -m pytest tests/test_email.py -v

Commit: git add -A && git commit -m "feat(email): daily reminder + preferences — closes specs #15, #16"
```

### P2-S8: Email Preferences UI + Phase 2 Final ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/design-system.md.

1. Create src/components/settings/EmailPreferences.tsx — toggle for daily reminders + timezone picker. Use CSS variables.
2. Add to Profile/Settings page.
3. Manual test: toggle off → verify no email sent.

Phase 2 final check:
4. Run full test suites: python -m pytest tests/ -v && npx vitest run
5. Verify manually: study → streak → XP → radar → mission → daily email.
6. Update SESSION-STATE.md: Phase 2 complete, next = P3-S1.
7. Push to main: git push

Commit: git add -A && git commit -m "chore: phase 2 complete — all specs done" && git push
```

---

# ═══════════════════════════════════════════
# PHASE 3: Content Pipeline + Marketing
# ═══════════════════════════════════════════

## --- NEW SESSION --- Phase 3A: Admin Panel + Design System (Tasks 3.1–3.2, 3.7)

### P3-S1: Spec — Admin Card CRUD + Soft Delete ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/admin-panel.md. Read .agent/skills/security.md. Create docs/specs/phase-3/17-admin-card-crud.md:

Include: all CRUD endpoints (POST/PUT /api/v1/admin/cards, DELETE uses soft-delete setting deleted_at = now()), bulk CSV import endpoint, require_admin on all routes, request/response schemas, and test plan. Emphasize: DELETE endpoint sets deleted_at, never removes the row. Do NOT write code yet.
```

### P3-S2: Admin CRUD Backend + Soft Delete ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read docs/specs/phase-3/17-admin-card-crud.md. Read .agent/skills/admin-panel.md.

1. Create app/services/card_admin_service.py: create_card, update_card, soft_delete_card (sets deleted_at = datetime.utcnow()), bulk_import_csv.
2. Create app/api/routes/admin.py with all CRUD endpoints. Every route uses Depends(require_admin).
3. Write tests in tests/test_admin_api.py:
   - test_admin_can_create_card
   - test_admin_can_update_card
   - test_admin_soft_delete_sets_deleted_at (row still exists, deleted_at is set)
   - test_deleted_card_not_returned_in_cards_api
   - test_non_admin_gets_403
   - test_bulk_import
4. Run: python -m pytest tests/test_admin_api.py -v

Commit: git add -A && git commit -m "feat(admin): card CRUD with soft-delete — closes spec #17"
```

### P3-S3: Design System + ThemePicker ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/design-system.md. Create docs/specs/phase-3/20b-design-system-themes.md, then implement:

1. Create src/styles/themes.css with CSS variable definitions for 3 themes:
   - data-theme="dark" (default): #0A0A0B base
   - data-theme="light": #FFFFFF base
   - data-theme="midnight": #050508 base, high-contrast neon accents
2. Create src/hooks/useTheme.ts:
   - Reads from localStorage key "skillforge-theme"
   - Applies via document.documentElement.setAttribute('data-theme', theme)
3. Create src/components/settings/ThemePicker.tsx — 3-option picker with preview swatches.
4. Add ThemePicker to Settings/Profile page.
5. Audit ALL existing components — replace hardcoded hex colors with CSS variables.
6. Manual test: switch themes → UI updates immediately → persists on reload.

Commit: git add -A && git commit -m "feat(ui): design system 3 themes + ThemePicker — closes spec #20b"
```

### P3-S4: AI Card Generation ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/llm-strategy.md. Create docs/specs/phase-3/18-ai-card-generation.md, then implement:

1. Create app/services/ai_card_service.py:
   - generate_card_draft(topic, difficulty) → uses LLM router (FAST task) to generate question, answer, tags
   - Returns a CardDraft (not saved — admin reviews before publish)
2. Create POST /api/v1/admin/cards/generate — admin-only, returns draft.
3. Write tests: test_generates_valid_card_structure (mock LLM router response).
4. Run tests.

Commit: git add -A && git commit -m "feat(admin): AI card generation — closes spec #18"
```

### P3-S5: Admin Panel UI ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/design-system.md.

1. Create src/pages/AdminPanel.tsx — card management dashboard (admin-only route). Use CSS variables.
2. Table of all cards (including soft-deleted, with visual indicator). Edit/restore/hard-archive buttons.
3. Create card form (manual or AI-assisted).
4. Bulk CSV upload with drag-and-drop.
5. AI generate button: enter topic → see draft → approve/edit → save.
6. Route: /admin → AdminPanel (redirect non-admins to home).
7. Manual test: create card, edit card, soft-delete, AI generate, bulk import.

Commit: git add -A && git commit -m "feat(ui): admin panel UI" && git push
```

## --- NEW SESSION --- Phase 3B: Landing Page + Polish + Resume Fix (Tasks 3.3–3.6, 3.8)

### P3-S6: Landing Page ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/design-system.md. Create docs/specs/phase-3/19-landing-page.md, then implement:

1. Create src/pages/LandingPage.tsx — marketing landing page. Use CSS variables, ThemePicker available.
2. Hero: "Ace your next engineering interview" + CTA "Scan Your Resume Free".
3. How it works: Scan → Study → Ace (3-step visual).
4. Pricing: Free tier (ATS scan + 15 cards) vs Pro ($49/mo USD / ₹999/mo INR).
5. Social proof placeholder.
6. Footer: © 2025 SkillForge. All rights reserved.
7. CTA buttons → /login (sign up) or /study (if logged in).
8. Add PostHog captures: landing_page_viewed, cta_clicked.
9. Route: / → LandingPage (when not logged in).
10. Mobile-responsive, loads fast.

Commit: git add -A && git commit -m "feat(marketing): landing page — closes spec #19"
```

### P3-S7: Onboarding Polish + Resume + Cover Letter Fix ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/ats-scanner.md. Read .agent/skills/llm-strategy.md.

Onboarding polish (Task 3.4):
1. Create docs/specs/phase-3/20-onboarding-polish.md.
2. Add guided tour (3-4 tooltip steps) on first login.
3. Store onboarding_completed flag on user (migration if needed).
4. Ensure persona picker (target_company + target_date) pre-fills from Phase 1 data.
5. Manual test: new user → guided tour → lands on right page.

Resume rewrite + cover letter fix (Task 3.8):
6. Create docs/specs/phase-3/20c-resume-cover-letter-fix.md.
7. Audit current resume rewrite — identify where it regresses formatting.
8. Fix: use LLM router (REASONING task) for resume rewrite.
9. Cover letter: ensure output is clean plain text with no markdown artifacts (no **, no ##).
10. Write tests (mock LLM): test_rewritten_resume_has_no_markdown_artifacts, test_cover_letter_clean_text.
11. Manual test: rewrite a resume → score should be >= original.

Commit: git add -A && git commit -m "feat: onboarding polish + resume/cover letter fixes — closes specs #20, #20c"
```

### P3-S8: My Experience + Feedback + Phase 3 Final ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/llm-strategy.md. Read .agent/skills/experience-gen.md.

My Experience AI generation (Task 3.5):
1. Create docs/specs/phase-3/20a-my-experience.md.
2. Create app/services/experience_service.py: generate_experience(user_id, topic) — uses study history + LLM router (REASONING task) to create a personalized narrative.
3. Create POST /api/v1/study/experience.
4. Frontend: add "Generate My Experience" button on Profile page.
5. Write test (mock LLM router): test_generates_experience_with_study_history.

Per-card feedback (Task 3.6):
6. Create app/models/card_feedback.py: user_id, card_id, rating (1-5), comment, created_at.
7. Create POST /api/v1/cards/{id}/feedback + GET /api/v1/admin/feedback.
8. Frontend: thumbs up/down + optional comment after card review.

Phase 3 final check:
9. Run full test suites.
10. Verify: admin panel, landing page, themes, onboarding, feedback, experience all work in production.
11. Update SESSION-STATE.md: Phase 3 complete, next = P4-S1.
12. Push: git push

Commit: git add -A && git commit -m "chore: phase 3 complete — all specs done" && git push
```

---

# ═══════════════════════════════════════════
# PHASE 4: Hardening + Observability
# ═══════════════════════════════════════════

## --- NEW SESSION --- Phase 4A: Monitoring + Performance + Go-Live

### P4-S1: Sentry Error Monitoring ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Create docs/specs/phase-4/22-error-monitoring.md, then implement:

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

### P4-S2: PostHog Dashboards + Webhook Idempotency Audit ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/analytics.md. Read .agent/skills/security.md. Create docs/specs/phase-4/23-posthog-dashboards.md.

PostHog dashboards:
1. List all PostHog events that should be flowing by now (all phases).
2. Verify events are actually firing — check PostHog live events dashboard.
3. Define and build 3 funnels:
   - Acquisition: sign_up → ats_scanned → card_viewed → paywall_hit → payment_completed
   - Retention: daily_review_started Day 1 → Day 7 → Day 30
   - Mission: mission_created → 50% days → mission_completed
4. Document any missing events and add them.

Webhook idempotency audit:
5. Verify that Stripe webhook idempotency (Redis deduplication) is working.
6. Create docs/specs/phase-4/24a-webhook-idempotency.md with test plan.
7. Write test: test_duplicate_stripe_event_not_processed_twice.

Commit: git add -A && git commit -m "feat(analytics): PostHog dashboards + idempotency audit" && git push
```

### P4-S3: Performance + Rate Limiting ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/security.md. Create docs/specs/phase-4/24-performance-hardening.md, then implement:

1. Verify rate limiting is in place (should be from Phase 1 security work):
   - 100 req/min per IP (global)
   - 10 req/min for auth endpoints
   - 5 req/min for ATS scan per user
   - Return 429 when exceeded
2. Write test: test_rate_limit_returns_429 (if not already present).
3. Run Lighthouse audit on the frontend:
   - Target: > 90 performance score, < 2s TTFB, < 3s LCP
4. Suggest specific fixes for any Lighthouse issues.
5. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(security): rate limiting audit + performance hardening — closes spec #24"
```

### P4-S4: Backup + Custom Domain + Stripe Go-Live ⬜

```
Read AGENTS.md. Read CLAUDE.md.

1. Document backup/restore procedure for Railway PostgreSQL.
2. Help me configure the custom domain (theskillsforge.dev):
   - DNS settings in domain registrar
   - SSL (Railway/Vercel handle automatically)
   - Update ALLOWED_ORIGINS with new domain
   - Update Stripe webhook URL to new domain
   - Update Google OAuth redirect URIs to new domain
3. Stripe go-live checklist:
   - Switch from sk_test_ to sk_live_ in Railway env vars
   - Switch from pk_test_ to pk_live_ in Vercel env vars
   - Verify STRIPE_PRO_PRICE_ID and STRIPE_PRO_PRICE_ID_INR are live price IDs
   - Test real payment with a real card (can refund immediately)
4. Verify: curl https://theskillsforge.dev/health → 200

Phase 4 final check:
5. Run all tests.
6. Verify Sentry captures errors.
7. Verify PostHog dashboards populated.
8. Verify rate limiting works.
9. Update SESSION-STATE.md: ALL PHASES COMPLETE 🚀.

Commit: git add -A && git commit -m "chore: phase 4 complete — production ready 🚀" && git push
```

---

# ═══════════════════════════════════════════
# ENHANCEMENT PROMPTS
# (Post-playbook features — run if not yet built)
# ═══════════════════════════════════════════

> Run these in a dedicated session if the feature hasn't been built yet.
> Check SESSION-STATE.md to see which are done.

### ENH-1: LLM Multi-Model Router ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/llm-strategy.md. Create docs/specs/phase-1/11d-llm-router.md, then implement:

1. Create app/services/llm_router.py:
   - class TaskType(Enum): FAST, REASONING
   - get_llm_client(task_type: TaskType) → returns appropriate client
   - Reads LLM_FAST_PROVIDER and LLM_REASONING_PROVIDER from env
   - google → uses google-genai SDK + GEMINI_API_KEY
   - anthropic → uses anthropic SDK + ANTHROPIC_API_KEY
   - openai → uses openai SDK + OPENAI_API_KEY
   - Falls back to google/Gemini if provider key not set; log a warning
2. Update app/core/config.py to load: LLM_FAST_MODEL, LLM_FAST_PROVIDER, LLM_REASONING_MODEL, LLM_REASONING_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY.
3. Refactor all existing LLM calls to use llm_router instead of calling Gemini directly.
4. Write tests: test_fast_uses_configured_provider, test_fallback_to_gemini, test_reasoning_uses_configured_provider.
5. Run: python -m pytest tests/test_llm_router.py -v

Commit: git add -A && git commit -m "feat(llm): multi-model router fast/reasoning — closes spec #11d"
```

### ENH-2: Geo-Based Pricing ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/geo-pricing.md. Read .agent/skills/payments.md.

1. Create app/services/geo_service.py: get_country(ip) using ip-api.com (free, no API key needed).
2. Update app/services/payment_service.py → create_checkout_session():
   - Extract IP from request headers (X-Forwarded-For or request.client.host)
   - Call geo_service.get_country(ip)
   - If "IN" → use STRIPE_PRO_PRICE_ID_INR
   - Else → use STRIPE_PRO_PRICE_ID
3. Update app/core/config.py to load STRIPE_PRO_PRICE_ID_INR.
4. Write tests (mock geo service):
   - test_indian_ip_gets_inr_price
   - test_us_ip_gets_usd_price
   - test_geo_failure_falls_back_to_usd
5. Update frontend PaywallModal to show both prices or the correct detected price.
6. Run: python -m pytest tests/test_geo_pricing.py -v

Commit: git add -A && git commit -m "feat(payments): geo-based pricing USD/INR"
```

### ENH-3: IP Registration Blocking ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/security.md.

1. Create app/services/registration_guard.py:
   - check_ip_limit(ip: str, redis_client) → raises HTTPException(429, "registration_limit_reached") if >= 2 regs in 30 days
   - Redis key: "ip_reg:{ip}" with INCR; TTL = 2592000 (30 days)
   - On first registration: SET with TTL. On subsequent: INCR (TTL preserved).
2. Wire into the registration path of POST /api/v1/auth/google — only on user creation, not login.
3. Write tests:
   - test_first_registration_allowed
   - test_second_registration_allowed
   - test_third_registration_blocked_429
   - test_login_not_affected_by_ip_limit
4. Run: python -m pytest tests/test_registration_guard.py -v

Commit: git add -A && git commit -m "feat(security): IP registration blocking max 2 per 30 days"
```

### ENH-4: Card Soft-Delete Migration ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/security.md. Read .agent/skills/database-schema.md.

1. Add to Card model: deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
2. Generate migration: alembic revision --autogenerate -m "add deleted_at to cards"
3. Test rollback cycle.
4. Update ALL card queries in card_service.py, study_service.py, gap_mapping_service.py to add: WHERE deleted_at IS NULL
5. Update admin soft_delete_card() in card_admin_service.py to SET deleted_at = datetime.utcnow() instead of DELETE.
6. Write tests:
   - test_deleted_card_not_returned_in_api
   - test_deleted_card_not_in_daily_review
   - test_admin_soft_delete_preserves_row
7. Run: python -m pytest tests/ -v --tb=short

Commit: git add -A && git commit -m "feat(db): card soft-delete via deleted_at column"
```

### ENH-5: Design System + ThemePicker ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/design-system.md.

1. Create src/styles/themes.css with CSS variables for 3 themes (dark/light/midnight).
2. Create src/hooks/useTheme.ts — localStorage persistence + :root data-theme attribute.
3. Create src/components/settings/ThemePicker.tsx — 3-option picker.
4. Add ThemePicker to Profile/Settings page.
5. Audit ALL components — replace hardcoded hex colors with CSS variables.
   Run: grep -r "#[0-9A-Fa-f]\{6\}" src/ --include="*.tsx" --include="*.ts" --include="*.css"
   Fix every match.
6. Manual test: switch all 3 themes → UI updates → persists on reload.

Commit: git add -A && git commit -m "feat(ui): design system 3 themes + ThemePicker"
```

### ENH-6: Free Tier Interview Question Limit ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/security.md.

1. Create app/services/plan_limits.py:
   - check_interview_question_limit(user_id: str, redis_client) → void
   - Tracks monthly count in Redis: key = "interview_q:{user_id}:{YYYY-MM}"
   - TTL = seconds until end of current month (calculate dynamically)
   - Raises HTTPException(403, detail={"code": "free_limit_reached", "limit_type": "interview_questions", "limit": 3})
2. Wire into the interview Q generation endpoint (wherever interview questions are generated).
3. Write tests:
   - test_first_three_questions_allowed
   - test_fourth_question_blocked_403
   - test_pro_user_not_limited
   - test_limit_resets_next_month (mock datetime)
4. Run: python -m pytest tests/test_plan_limits.py -v

Commit: git add -A && git commit -m "feat(security): free tier 3 interview Q/month limit"
```

### ENH-7: Tracker Auto-Populate from ATS Scan ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/ats-scanner.md.

1. Read the current ATS scan result schema. Identify what fields contain job title + company name.
2. Create or update app/services/tracker_service.py:
   - create_from_scan(user_id: str, scan_result: dict) → creates a tracker entry if company/role extractable
   - Entry fields: user_id, company (from scan), role (from scan), status="applied", source="ats_scan", created_at
3. Call create_from_scan after a successful ATS scan in the tracker service or scanner endpoint.
4. Write tests:
   - test_tracker_entry_created_after_scan_with_company
   - test_no_entry_if_company_not_found
5. Run: python -m pytest tests/test_tracker.py -v

Commit: git add -A && git commit -m "feat(tracker): auto-populate from ATS scan results"
```

### ENH-8: Resume Rewrite + Cover Letter Fix ⬜

```
Read AGENTS.md. Read CLAUDE.md. Read .agent/skills/ats-scanner.md. Read .agent/skills/llm-strategy.md.

1. Audit the current resume rewrite endpoint — find where formatting regressions occur.
2. Ensure resume rewrite uses LLM router (REASONING task) not a hardcoded Gemini call.
3. Fix resume rewrite prompt: output must be clean text, no markdown, no extra blank lines.
4. Fix cover letter formatting:
   - Output must be clean plain text
   - No **bold**, no ## headers, no markdown artifacts
   - Properly spaced paragraphs
   - Add a post-processing step to strip any remaining markdown if LLM still produces it
5. Write tests (mock LLM):
   - test_rewritten_resume_has_no_markdown_artifacts
   - test_cover_letter_clean_plain_text
   - test_rewrite_score_not_lower_than_original (use a fixture resume)
6. Run: python -m pytest tests/test_ats_rewrite.py -v

Commit: git add -A && git commit -m "fix(ats): resume rewrite + cover letter formatting — uses LLM router"
```

---

# ═══════════════════════════════════════════
# REFERENCE: Session Strategy
# ═══════════════════════════════════════════

| Session | Slices | Phase | Focus | Status |
|---------|--------|-------|-------|--------|
| P0-Auth | S1–S4 | 0 | Auth unification + user roles | ⬜ |
| P0-Deploy | S5–S8 | 0 | Skeleton deploy + CI/CD + verify | ⬜ |
| P1A | S1–S4 | 1 | Card extraction + embeddings + LLM router | ⬜ |
| P1B | S5–S7 | 1 | Cards API | ⬜ |
| P1C | S8–S11 | 1 | FSRS study engine | ⬜ |
| P1D | S12–S15 | 1 | Study UI (dashboard, viewer, daily) | ⬜ |
| P1E | S16–S18 | 1 | ATS bridge + persona picker + onboarding | ⬜ |
| P1F | S19–S23 | 1 | Security + analytics + Stripe geo-pricing + verify | ⬜ |
| P2A | S1–S4 | 2 | Gamification + skill radar | ⬜ |
| P2B | S5–S6 | 2 | Mission Mode | ⬜ |
| P2C | S7–S8 | 2 | Daily email + verify | ⬜ |
| P3A | S1–S5 | 3 | Admin CRUD + soft-delete + design system + AI gen | ⬜ |
| P3B | S6–S8 | 3 | Landing page + polish + resume fix + experience + feedback | ⬜ |
| P4A | S1–S4 | 4 | Monitoring + perf + go-live | ⬜ |
| ENH | E1–E8 | — | Post-playbook enhancements (if not done inline) | ⬜ |

**Total: ~15 sessions, ~60 slices across 15 weeks.**

---

# ═══════════════════════════════════════════
# REFERENCE: Contingency Prompts
# ═══════════════════════════════════════════

**If Claude Code drifts or gets confused:**
```
Stop. Re-read docs/specs/phase-N/NN-feature.md. Focus only on [specific AC]. Do not touch any other files.
```

**If a test fails 3+ times (3-Strike Rule):**
```
Stop. Do not attempt another fix. Print the exact error, explain your hypothesis for the root cause, and list 2-3 possible fixes. Wait for me to decide.
```

**If you need to verify DB state:**
```
Connect to the hireport database with psql and run: \dt to list tables, \d cards to verify deleted_at column exists, \dx to list extensions. Show me the output.
```

**If LLM router fallback triggers:**
```
Check app/services/llm_router.py. Print which provider is being used for FAST and REASONING tasks. Check that ANTHROPIC_API_KEY or OPENAI_API_KEY are set in .env if you want non-Gemini providers. The fallback to Gemini is expected if keys are not set.
```

**If you need to verify production:**
```
curl -s https://theskillsforge.dev/health and show me the response. Then curl one API endpoint to verify data is flowing.
```

**If a slice is taking too long (>15 min of Claude thinking):**
```
Stop. You're overcomplicating this. Break the current task into 2 smaller pieces. Tell me what those pieces are, and I'll tell you which one to do first.
```

**If you need to reset after a bad session:**
```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. List the files you changed in the last session (git diff --stat). Run the full test suite. Tell me what's broken and what's working.
```

**Start-of-session ritual (copy this every time):**
```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Summarize:
1. What phase and slice are we on?
2. Any known issues from last session?
3. Run: git log --oneline -5

Then continue with: [next slice prompt from this file]
```
