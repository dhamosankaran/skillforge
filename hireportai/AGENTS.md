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

## Directory Structure
```
hireportai/
├── AGENTS.md                    ← YOU ARE HERE
├── CLAUDE.md                    ← Claude Code project rules
├── docs/
│   ├── specs/                   ← Feature specifications
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
│   └── scripts/                 ← One-off scripts
├── hirelens-frontend/
│   ├── src/
│   │   ├── components/          ← Reusable UI components
│   │   ├── pages/               ← Route pages
│   │   ├── context/             ← React contexts
│   │   ├── hooks/               ← Custom hooks
│   │   ├── services/            ← API client
│   │   └── types/               ← TypeScript types
│   └── tests/                   ← Vitest + RTL tests
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

### Frontend (TypeScript/React)
- Functional components with hooks only (no class components)
- Use `useQuery`/`useMutation` pattern for API calls
- All API calls go through `services/api.ts` with auth headers
- Dark mode by default (#0A0A0B base, brand gradients)
- Framer Motion for all animations
- Mobile-first responsive design
- Naming: `PascalCase` for components, `camelCase` for functions

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

## Key Decisions Log
- Auth: Google OAuth + JWT (NOT Clerk — migrating later for B2B)
- FSRS: py-fsrs library, server-side only
- LLM: Gemini 2.5 Pro for reasoning, Flash for speed tasks
- Storage: R2 for files (zero egress), PostgreSQL for data
- Analytics: PostHog Cloud (free tier)
- No Docker for dev — use local PostgreSQL + Redis via Homebrew
