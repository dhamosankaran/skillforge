---
description: Test patterns, fixtures, mocks for SkillForge
---
# Testing Skill
## Overview
Backend: pytest + pytest-asyncio + httpx. Frontend: Vitest + RTL.
## Key Patterns
- Use `seeded_db_session` fixture for integration tests (canonical test data)
- Use `client` fixture for authenticated API tests (Pro user by default)
- Use `client_free_tier` for plan-gating tests
- Use `client_admin` for admin endpoint tests
- Auto-skip if TEST_DATABASE_URL is unreachable (CI without PG doesn't fail)
## Running Tests
- All backend: `cd hirelens-backend && python -m pytest tests/ -v --tb=short`
- Specific file: `python -m pytest tests/test_study_service.py -v`
- CI subset (skips live-LLM integration tests): `python -m pytest tests/ -v --tb=short -m "not integration"`
- Integration only (needs live LLM keys): `python -m pytest tests/ -v -m integration`
- Coverage: **not available** — `pytest-cov` is deliberately not installed. Do not add `--cov` flags without updating `requirements-dev.txt` and getting sign-off (CLAUDE.md rule 13).
- All frontend: `cd hirelens-frontend && npx vitest run`
- Migration rollback: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
