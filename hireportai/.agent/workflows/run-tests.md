---
description: How to run all tests
---
## Backend
```bash
cd hirelens-backend && source venv/bin/activate
python -m pytest tests/ -v --tb=short          # All tests
python -m pytest tests/test_foo.py -v          # Single file
python -m pytest tests/ --cov=app              # With coverage
```
## Frontend
```bash
cd hirelens-frontend
npx vitest run                                 # All tests
npx vitest run --coverage                      # With coverage
```
## Migration Rollback
```bash
cd hirelens-backend
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```
