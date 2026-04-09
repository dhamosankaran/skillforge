---
description: How to create an Alembic migration
---
## Steps
1. Modify ORM model in `app/models/`
2. Generate migration:
   `alembic revision --autogenerate -m "add feature_name column"`
3. Review the generated file in `alembic/versions/`
4. Check that `downgrade()` reverses everything in `upgrade()`
5. Apply: `alembic upgrade head`
6. Test rollback: `alembic downgrade -1 && alembic upgrade head`
7. Run tests: `python -m pytest tests/ -v`

## Rules
- Always verify the generated migration — autogenerate misses some things
- Hand-author migrations for complex changes (type promotions, data migrations)
- Every migration must have a working downgrade()
