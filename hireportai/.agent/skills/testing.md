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
- With coverage: `python -m pytest tests/ --cov=app --cov-report=term-missing`
- All frontend: `cd hirelens-frontend && npx vitest run`
- Migration rollback: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
