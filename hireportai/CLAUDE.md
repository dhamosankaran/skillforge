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
7. **No console.log in production**: Use proper logging (backend: `logger`, frontend: remove before commit)
8. **🚨 AI Loop Breaker (3-Strike Rule)**: If a test fails 3 times in a row during the RED-GREEN-REFACTOR cycle, **STOP IMMEDIATELY**. Do NOT attempt another fix. Instead: (a) print the exact error message, (b) explain what you think is wrong, (c) list 2-3 hypotheses for the root cause, and (d) wait for human intervention. This prevents burning API tokens and prevents "fix cascades" where each attempt introduces a new bug.

## How to Add a Feature
1. Check spec exists in `docs/specs/`
2. Create/update backend models in `app/models/`
3. Create Alembic migration: `alembic revision --autogenerate -m "description"`
4. Apply: `alembic upgrade head`
5. Create Pydantic schemas in `app/schemas/`
6. Write tests in `tests/`
7. Implement service in `app/services/`
8. Create API route in `app/api/routes/`
9. Register route in `app/main.py`
10. Run: `python -m pytest tests/ -v`
11. Implement frontend (page → component → hook → API client)
12. Run: `npx vitest run`

## Environment
- Python 3.13, Node 20, PostgreSQL 16 + pgvector, Redis 7
- Backend: FastAPI, SQLAlchemy 2.0 async, py-fsrs, google-genai
- Frontend: React 18, TypeScript 5, Vite 5, Tailwind, Framer Motion
- DB URL: `postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport`
