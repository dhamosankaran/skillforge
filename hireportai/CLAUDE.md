# SkillForge (HirePort AI) — Claude Code Guide

## Quick Reference
- Backend: `cd hirelens-backend && source venv/bin/activate`
- Frontend: `cd hirelens-frontend`
- Tests (BE): `python -m pytest tests/ -v --tb=short`
- Tests (FE): `npx vitest run`
- DB migrate: `alembic upgrade head`
- Start BE: `uvicorn app.main:app --reload --port 8000`
- Start FE: `npm run dev -- --port 5199`

## MUST-READ Before Any Task
1. Read `AGENTS.md` for project conventions
2. Read the relevant spec in `docs/specs/`
3. Read the relevant skill file in `.agent/skills/`

## Rules
1. **Test first**: Write tests before implementation
2. **One thing at a time**: Each commit = one feature slice
3. **Never skip auth**: All new routes need `Depends(get_current_user)`
4. **FSRS is server-side only**: Never put scheduling logic in frontend
5. **Pydantic for everything**: All API I/O uses Pydantic schemas
6. **Alembic for all schema changes**: Never use `CREATE TABLE` directly
7. **No console.log in production**: Use proper logging
8. **Track everything**: Every user-facing feature fires a PostHog event
9. **Deploy is automatic**: Push to main = production deploy. Never do manual deploys.
10. **🚨 AI Loop Breaker (3-Strike Rule)**: If a test fails 3 times
    in a row, **STOP IMMEDIATELY**. Print the exact error, explain
    your hypothesis, list 2-3 possible fixes, and wait for human
    intervention.
11. **LLM calls go through the router**: Use
    `generate_for_task(task=..., ...)` from `app/core/llm_router.py`
    for every LLM call. Never call `get_llm_provider()` directly and
    never import a provider SDK from service code. See
    `.agent/skills/llm-strategy.md`.
12. **Style with design tokens**: Every color / spacing / shadow in
    frontend code must come from the design tokens
    (`src/styles/design-tokens.ts`) via Tailwind utilities like
    `bg-bg-surface`, `text-text-primary`, `border-border-accent`.
    **Never hardcode a hex value.** See
    `.agent/skills/design-system.md`.

## How to Add a Feature
1. Check spec exists in `docs/specs/`
2. Create/update backend models in `app/models/`
3. Create Alembic migration: `alembic revision --autogenerate -m "description"`
4. Apply: `alembic upgrade head`
5. Create Pydantic schemas in `app/schemas/`
6. Write tests in `tests/`
7. Implement service in `app/services/`
   - **If LLM-powered:** pick the tier (fast vs reasoning), add the
     task name to `app/core/llm_router.py` if new, then call
     `generate_for_task(task="...", ...)`
8. **Add a PostHog event** — name it in snake_case, pick frontend vs
   backend, and add it to `.agent/skills/analytics.md` so the
   catalog stays current
9. Create API route in `app/api/routes/` or `app/api/v1/routes/`
10. Register route in `app/main.py`
11. Run: `python -m pytest tests/ -v`
12. Implement frontend (page → component → hook → API client)
    - **Style with theme tokens only** — no hardcoded colors
13. Add PostHog `capture()` on user interactions
14. Run: `npx vitest run`
15. Push to main (CI/CD auto-deploys)

## Environment
- Python 3.13, Node 20, PostgreSQL 16 + pgvector, Redis 7
- Backend: FastAPI, SQLAlchemy 2.0 async, py-fsrs, google-genai
- Frontend: React 18, TypeScript 5, Vite 5, Tailwind, Framer Motion
- Analytics: PostHog (instrumented from Phase 1)
- Email: Resend (from Phase 2)
- Deploy: Vercel + Railway (continuous from Phase 0)
- DB URL: `postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport`