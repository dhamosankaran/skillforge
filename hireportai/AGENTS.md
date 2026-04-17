# SkillForge — Agent Development Guide

## Project Overview
SkillForge (under HirePort AI) is an AI-powered career acceleration
platform combining ATS scanning, spaced-repetition flashcard learning,
and interview prep. Built with FastAPI + React + PostgreSQL + pgvector.

## Architecture
- Backend: FastAPI (Python 3.13) at `hirelens-backend/`
- Frontend: React 18 + TypeScript + Vite at `hirelens-frontend/`
- Database: PostgreSQL 16 + pgvector
- Cache: Redis 7
- Auth: Google OAuth + JWT (access + refresh tokens)
- LLM: task-tiered router (Gemini default; Anthropic/OpenAI via env)
- Payments: Stripe (USD + INR, geo-routed by IP)
- Analytics: PostHog Cloud
- Email: Resend (transactional)
- Monitoring: Sentry (FE + BE)
- Deploy: Vercel (FE) + Railway (BE + PG + Redis)
- CI/CD: GitHub Actions (push to main → test → deploy)

## Directory Structure
```
hireportai/
├── AGENTS.md                    ← YOU ARE HERE
├── CLAUDE.md                    ← Claude Code project rules
├── .agent/skills/               ← Skill files (one per subsystem)
├── docs/
│   ├── specs/                   ← Feature specifications (by phase)
│   ├── runbooks/                ← Ops runbooks (backup, Stripe go-live, domain)
│   ├── prd.md                   ← Product Requirements Document
│   └── architecture.md          ← System architecture
├── hirelens-backend/
│   ├── app/
│   │   ├── api/routes/          ← Legacy /api/* route handlers
│   │   ├── api/v1/routes/       ← /api/v1/* route handlers
│   │   ├── core/                ← Auth, config, deps, rate limit,
│   │   │                          llm_router, analytics
│   │   ├── models/              ← SQLAlchemy ORM models
│   │   ├── schemas/             ← Pydantic request/response
│   │   ├── services/            ← Business logic
│   │   └── main.py              ← FastAPI app factory
│   ├── tests/                   ← pytest tests
│   ├── alembic/                 ← DB migrations
│   └── scripts/                 ← One-off scripts (migration, seeding)
├── hirelens-frontend/
│   ├── src/
│   │   ├── components/          ← Reusable UI components
│   │   ├── pages/               ← Route pages
│   │   ├── context/             ← React contexts (Auth, Usage,
│   │   │                          Gamification, Theme, Analysis)
│   │   ├── hooks/               ← Custom hooks
│   │   ├── services/            ← API client
│   │   ├── styles/              ← design-tokens.ts + tailwind css
│   │   └── types/               ← TypeScript types
│   └── tests/                   ← Vitest + RTL tests
├── .github/
│   └── workflows/
│       └── ci.yml               ← CI/CD pipeline
└── scripts/                     ← Dev utility scripts
```

## Coding Conventions

### Backend (Python)
- Use `async def` for all route handlers and service methods
- Use Pydantic v2 models for ALL request/response schemas
- Use SQLAlchemy 2.0 style (`Mapped[]`, `mapped_column()`)
- Use `Depends()` for auth, DB sessions, service injection
- Service layer pattern: routes call services, services call DB
- All new tables need Alembic migrations
- FSRS calculations happen server-side ONLY (not in frontend)
- Naming: `snake_case` for files, functions, variables
- Every user-facing feature must fire a PostHog event
- **All LLM calls go through `generate_for_task()`** — never import
  provider SDKs from service code

### Frontend (TypeScript/React)
- Functional components with hooks only (no class components)
- Use `useQuery`/`useMutation` pattern for API calls
- All API calls go through `services/api.ts` with auth headers
- **Theme-aware by default** — use design tokens
  (`bg-bg-base`, `text-text-primary`, etc.), never hardcoded hex
- Framer Motion for all animations
- Mobile-first responsive design
- Naming: `PascalCase` for components, `camelCase` for functions
- PostHog `capture()` on key user actions (scan, view card, pay)

### Testing
- Backend: pytest + pytest-asyncio + httpx (async client)
- Frontend: Vitest + React Testing Library
- Test files mirror source structure
- Every API endpoint needs at least: happy path, auth failure,
  validation error test
- Coverage target: 80%+

### Git Conventions
- Branch: `feature/<phase>-<number>-<name>`
- Commit: `type(scope): description`
- PR = 1 spec = 1 deployable unit
- Every merge to main auto-deploys via CI/CD

### Deployment
- Every push to main runs: lint → test → deploy
- Backend deploys to Railway, frontend to Vercel
- Database migrations run automatically via release command
- Environment variables live in Railway/Vercel dashboards, NOT in code

## Environment Variables

Canonical source: `hirelens-backend/app/core/config.py` (`Settings`)
and `hirelens-frontend/.env.example`. Phase annotation shows when a
variable was introduced.

### Backend

| Variable | Purpose | Default | Phase |
|----------|---------|---------|-------|
| `DATABASE_URL` | Async Postgres URL (`postgresql+asyncpg://…`) | local dev url | 0 |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` | 0 |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | localhost FE ports | 0 |
| `MAX_UPLOAD_SIZE_MB` | Request body cap in MB | `5` | 0 |
| `GOOGLE_CLIENT_ID` | Google OAuth client id | — | 0 |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | — | 0 |
| `JWT_SECRET_KEY` | Symmetric JWT signing key | `change-me-in-production` | 0 |
| `JWT_ALGORITHM` | JWT alg | `HS256` | 0 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` | 0 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` | 0 |
| `FRONTEND_URL` | Used for Stripe success/cancel redirects | `http://localhost:5199` | 0 |
| `GEMINI_API_KEY` | Default LLM provider key | — | 0 |
| `GEMINI_MODEL` | Legacy single-model var | `gemini-2.0-flash` | 0 |
| `LLM_PROVIDER` | Legacy single-provider var | `gemini` | 0 |
| `LLM_FAST_PROVIDER` | Router: provider for fast tier | `gemini` | 3 |
| `LLM_FAST_MODEL` | Router: model for fast tier | `gemini-2.0-flash` | 3 |
| `LLM_REASONING_PROVIDER` | Router: provider for reasoning tier | `gemini` | 3 |
| `LLM_REASONING_MODEL` | Router: model for reasoning tier | `gemini-2.5-pro` | 3 |
| `ANTHROPIC_API_KEY` | Required only if a tier uses Anthropic | — | 3 |
| `CLAUDE_MODEL` | Legacy Anthropic model name | `claude-sonnet-4-20250514` | 3 |
| `OPENAI_API_KEY` | Required only if a tier uses OpenAI | — | 3 |
| `POSTHOG_API_KEY` | Backend PostHog ingestion | — | 1 |
| `POSTHOG_HOST` | PostHog region URL | `https://us.i.posthog.com` | 1 |
| `STRIPE_SECRET_KEY` | Stripe server key | — | 1 |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature secret | — | 1 |
| `STRIPE_PRO_PRICE_ID` | USD monthly Pro price id | — | 1 |
| `STRIPE_PRO_PRICE_ID_INR` | INR monthly Pro price id | — | 3 |
| `STRIPE_ENTERPRISE_PRICE_ID` | Enterprise price id | — | 1 |
| `RESEND_API_KEY` | Transactional email provider | — | 2 |
| `RESEND_FROM_ADDRESS` | From address for reminder emails | `reminders@skillforge.app` | 2 |
| `SENTRY_DSN` | Backend Sentry DSN | — | 4 |

### Frontend (`VITE_*`)

| Variable | Purpose | Phase |
|----------|---------|-------|
| `VITE_API_BASE_URL` | Backend base URL | 0 |
| `VITE_GOOGLE_CLIENT_ID` | OAuth client id (public) | 0 |
| `VITE_POSTHOG_KEY` | PostHog project key (public) | 1 |
| `VITE_POSTHOG_HOST` | PostHog ingestion host | 1 |
| `VITE_STRIPE_KEY` | Stripe publishable key | 1 |
| `VITE_SENTRY_DSN` | Frontend Sentry DSN | 4 |

## Routes Table

### Backend — routers registered in `app/main.py`

Both a legacy `/api/*` surface and the `/api/v1/*` surface are
mounted; v1 is authoritative for new work.

| Prefix | Router file | Notes |
|--------|-------------|-------|
| `/api/analyze` | `app/api/routes/analyze.py` | Legacy ATS scan |
| `/api/rewrite` | `app/api/routes/rewrite.py` | Legacy bullet rewrite |
| `/api/cover_letter` | `app/api/routes/cover_letter.py` | Legacy |
| `/api/interview` | `app/api/routes/interview.py` | Legacy |
| `/api/tracker` | `app/api/routes/tracker.py` | Legacy |
| `/api/v1/auth` | `app/api/v1/routes/auth.py` | Google OAuth + JWT + IP blocking |
| `/api/v1/admin` | `app/api/v1/routes/admin.py` | Admin card CRUD + card draft AI |
| `/api/v1/analyze` | `app/api/v1/routes/analyze.py` | ATS scan + auto tracker |
| `/api/v1/rewrite` | `app/api/v1/routes/rewrite.py` | Resume/bullet rewrite |
| `/api/v1/cover_letter` | `app/api/v1/routes/cover_letter.py` | Cover letters |
| `/api/v1/interview` | `app/api/v1/routes/interview.py` | Interview questions (capped) |
| `/api/v1/tracker` | `app/api/v1/routes/tracker.py` | Application tracker |
| `/api/v1/resume` | `app/api/v1/routes/resume.py` | Resume storage |
| `/api/v1/cards` | `app/api/v1/routes/cards.py` | User-facing card reads |
| `/api/v1/study` | `app/api/v1/routes/study.py` | FSRS daily review |
| `/api/v1/gamification` | `app/api/v1/routes/gamification.py` | Streaks, XP, badges |
| `/api/v1/email-prefs` | `app/api/v1/routes/email_prefs.py` | Email preferences + unsubscribe |
| `/api/v1/mission` | `app/api/v1/routes/mission.py` | Mission Mode |
| `/api/v1/progress` | `app/api/v1/routes/progress.py` | Radar + heatmap |
| `/api/v1/feedback` | `app/api/v1/routes/feedback.py` | NPS + card feedback |
| `/api/v1/onboarding` | `app/api/v1/routes/onboarding.py` | Persona + goals |
| `/api/v1/payments` | `app/api/v1/routes/payments.py` | Checkout, webhook, pricing |

### Frontend — routes in `src/App.tsx`

| Path | Component | Access |
|------|-----------|--------|
| `/` | `LandingPage` | Public |
| `/login` | `LoginPage` | Public |
| `/pricing` | `Pricing` | Public |
| `/analyze` | `Analyze` | Protected |
| `/results` | `Results` | Protected |
| `/rewrite` | `Rewrite` | Protected |
| `/tracker` | `Tracker` | Protected |
| `/interview` | `Interview` | Protected |
| `/onboarding` | `Onboarding` | Protected |
| `/study` | `StudyDashboard` | Protected |
| `/study/daily` | `DailyReview` | Protected |
| `/study/category/:id` | `CategoryDetail` | Protected |
| `/study/card/:id` | `CardViewer` | Protected |
| `/mission` | `MissionMode` | Protected (lazy) |
| `/profile` | `Profile` | Protected (lazy) |
| `/admin` | `AdminPanel` | Protected (admin only, lazy) |
| `*` | redirect to `/` | Catch-all |

## Middleware
Stack order in `app/main.py`:

1. **Sentry** — initialized if `SENTRY_DSN` is set
   (`traces_sample_rate=0.1`).
2. **CORS** — `CORSMiddleware` built from `Settings.allowed_origins_list`,
   `allow_credentials=True`, all methods/headers.
3. **Rate limiting** — `slowapi` limiter keyed on
   `get_remote_address`. Global default **100 req/min**; overrides
   **10 req/min** for `/auth/*` and **5 req/min** for
   `POST /admin/cards/generate`. See the
   [security skill](.agent/skills/security.md).
4. **Request size limit** — custom middleware rejecting requests
   larger than `MAX_UPLOAD_SIZE_MB` (default 5 MB) with HTTP 413.

## Models

All under `app/models/`. Column notes list PK + high-signal columns.

| Model | Table | Key columns |
|-------|-------|-------------|
| `User` | `users` | `id`, `google_id` unique, `email` unique, `name`, `role`, `persona`, `onboarding_completed`, `target_company`, `target_date` |
| `Subscription` | `subscriptions` | `user_id` unique FK, `plan` (free/pro/enterprise), `status`, `stripe_customer_id`, `stripe_subscription_id`, `current_period_end` |
| `Payment` | `payments` | `user_id`, `stripe_payment_intent_id` unique, `amount`, `currency`, `status` |
| `RegistrationLog` | `registration_logs` | `user_id`, `ip_address` indexed, `google_email`, `created_at` |
| `StripeEvent` | `stripe_events` | `id` PK (Stripe evt id), `event_type`, `processed_at` |
| `UsageLog` | `usage_logs` | `user_id` indexed, `feature_used`, `tokens_consumed`, `created_at` indexed |
| `UsageLimit` | `usage_limits` | plan × feature → cap per period |
| `Resume` | `resumes` | `user_id`, `original_content`, `optimized_content`, `template_type`, `embedding` pgvector(1536) |
| `Card` | `cards` | `category_id` FK, `question`, `answer`, `difficulty`, `tags` JSON, `embedding` pgvector(1536), `deleted_at` |
| `CardProgress` | `card_progress` | `user_id` × `card_id` unique; FSRS fields `state`, `stability`, `difficulty_fsrs`, `due_date`, `reps`, `lapses` |
| `Category` | `categories` | `name` unique, `icon`, `color`, `display_order`, `source` |
| `Mission` | `missions` | `user_id`, `title`, `target_date`, `daily_target`, `status` |
| `MissionDay` | `mission_days` | `mission_id`, `day_number`, `date`, `cards_target`, `cards_completed` |
| `GamificationStats` | `gamification_stats` | `user_id` PK, `current_streak`, `longest_streak`, `total_xp`, `last_active_date`, `freezes_available` |
| `Badge` | `badges` | `id` PK, `name`, `description`, `threshold_type`, `threshold_value` |
| `UserBadge` | `user_badges` | `user_id` × `badge_id` unique, `earned_at` |
| `EmailPreference` | `email_preferences` | `user_id` PK, `daily_reminder`, `timezone`, `unsubscribe_token` unique |
| `CardFeedback` | `card_feedback` | `user_id`, `card_id`, `vote` (up/down), `comment` |
| `TrackerApplicationModel` | `tracker_applications_v2` | `user_id` nullable, `company`, `role`, `date_applied`, `ats_score`, `status`, `scan_id`, `skills_matched`, `skills_missing` |

## LLM Router (canonical path + API)

The LLM router lives at **`app/core/llm_router.py`** (not `app/services/`)
with the call shape:

```python
from app.core.llm_router import generate_for_task

text = generate_for_task(
    task="resume_rewrite",   # classified into FAST_TASKS / REASONING_TASKS frozensets
    prompt=...,
    system_prompt=...,       # optional
    json_mode=False,
    max_tokens=4096,
    temperature=0.7,
)
```

Task classification is by name (string), not a TaskType enum. Unknown
tasks default to the **fast** tier. Provider dispatch is module-level
(`_call_gemini` / `_call_anthropic` / `_call_openai`) chosen from
`LLM_FAST_PROVIDER` / `LLM_REASONING_PROVIDER` env vars.

**Do not import `app/services/llm/factory.py`** (`get_llm_provider()`) —
that's a legacy provider abstraction that predates the router. It will be
consolidated in Phase 6 cleanup. Route all new LLM calls through
`generate_for_task()`.

## Key Decisions Log
- Auth: Google OAuth + JWT (NOT Clerk — migrating later for B2B)
- FSRS: py-fsrs library, server-side only
- LLM: task-tiered router at `app/core/llm_router.py` — fast tier for
  extraction/drafting, reasoning tier for long-form. Default provider
  Gemini; providers swappable per tier via env vars. See LLM Router
  section above.
- Storage: R2 for files (zero egress), PostgreSQL for data
- Analytics: PostHog Cloud (free tier), instrumented from Phase 1
- Email: Resend for transactional (daily reminders, Phase 2)
- Deploy: Vercel + Railway from Phase 0, not deferred to launch
- No Docker for dev — use local PostgreSQL + Redis via Homebrew
- Pricing: geo-routed by IP (INR for India, USD otherwise)
- Theming: 3 themes via design tokens + CSS variables; runtime switch
