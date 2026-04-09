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
- LLM: Google Gemini (via google-genai SDK)
- Payments: Stripe
- Analytics: PostHog Cloud
- Email: SendGrid or Resend (transactional)
- Deploy: Vercel (FE) + Railway (BE + PG + Redis)
- CI/CD: GitHub Actions (push to main → test → deploy)

## Directory Structure
hireportai/
├── AGENTS.md                    ← YOU ARE HERE
├── CLAUDE.md                    ← Claude Code project rules
├── docs/
│   ├── specs/                   ← Feature specifications (by phase)
│   ├── prd.md                   ← Product Requirements Document
│   └── architecture.md          ← System architecture
├── hirelens-backend/
│   ├── app/
│   │   ├── api/routes/          ← API route handlers
│   │   ├── core/                ← Auth, config, deps
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
│   │   ├── context/             ← React contexts
│   │   ├── hooks/               ← Custom hooks
│   │   ├── services/            ← API client
│   │   └── types/               ← TypeScript types
│   └── tests/                   ← Vitest + RTL tests
├── .github/
│   └── workflows/
│       └── ci.yml               ← CI/CD pipeline
└── scripts/                     ← Dev utility scripts

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

### Frontend (TypeScript/React)
- Functional components with hooks only (no class components)
- Use `useQuery`/`useMutation` pattern for API calls
- All API calls go through `services/api.ts` with auth headers
- Dark mode by default (#0A0A0B base, brand gradients)
- Framer Motion for all animations
- Mobile-first responsive design
- Naming: `PascalCase` for components, `camelCase` for functions
- PostHog `capture()` on key user actions (scan, view card, pay)

### Testing
- Backend: pytest + pytest-asyncio + httpx (async client)
- Frontend: Vitest + React Testing Library
- Test files mirror source structure: `app/services/foo.py` →
  `tests/test_foo.py`
- Every API endpoint needs at least: happy path, auth failure,
  validation error test
- Coverage target: 80%+

### Git Conventions
- Branch: `feature/<phase>-<number>-<name>`
  (e.g., `feature/p1-05-fsrs-daily-review`)
- Commit: `type(scope): description`
  (e.g., `feat(study): add FSRS daily review endpoint`)
- PR = 1 spec = 1 deployable unit
- Every merge to main auto-deploys via CI/CD

### Deployment
- Every push to main runs: lint → test → deploy
- Backend deploys to Railway (auto-deploy on push)
- Frontend deploys to Vercel (auto-deploy on push)
- Database migrations run automatically via release command
- Stripe webhooks use the production URL (set in Phase 0)
- Environment variables live in Railway/Vercel dashboards, NOT in code

## Key Decisions Log
- Auth: Google OAuth + JWT (NOT Clerk — migrating later for B2B)
- FSRS: py-fsrs library, server-side only
- LLM: Gemini 2.5 Pro for reasoning, Flash for speed tasks
- Storage: R2 for files (zero egress), PostgreSQL for data
- Analytics: PostHog Cloud (free tier), instrumented from Phase 1
- Email: SendGrid or Resend for transactional (daily reminders, Phase 2)
- Deploy: Vercel + Railway from Phase 0, not deferred to launch
- No Docker for dev — use local PostgreSQL + Redis via Homebrew