---
description: Database migration conventions, Alembic patterns, and schema change rules
---

# Database Migration Skill

## Overview
All schema changes go through Alembic migrations. Never use raw
CREATE TABLE or ALTER TABLE in application code. This skill covers
the conventions, gotchas, and patterns for SkillForge migrations.

## Rules
1. **Every model change needs a migration.** No exceptions.
2. **Always test rollback.** Every migration: upgrade → downgrade → upgrade.
3. **Hand-author complex migrations.** Autogenerate works for simple adds, but
   type promotions (VARCHAR→UUID, DateTime→TIMESTAMPTZ) and data migrations
   must be hand-authored.
4. **One migration per feature.** Don't batch unrelated schema changes.
5. **Never edit a migration that's been pushed to main.** Create a new one instead.

## Workflow
```bash
# 1. Modify ORM model in app/models/
# 2. Generate migration
cd hirelens-backend && source venv/bin/activate
alembic revision --autogenerate -m "add feature_name column"

# 3. Review the generated file in alembic/versions/
#    - Check upgrade() creates what you expect
#    - Check downgrade() reverses everything
#    - Check for missing indexes

# 4. Apply
alembic upgrade head

# 5. Test rollback
alembic downgrade -1
alembic upgrade head

# 6. Run tests
python -m pytest tests/ -v --tb=short
```

## Common Patterns

### Adding a column
```python
def upgrade():
    op.add_column('users', sa.Column('plan', sa.String(20), nullable=False, server_default='free'))

def downgrade():
    op.drop_column('users', 'plan')
```

### Adding a table
```python
def upgrade():
    op.create_table('card_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('card_id', sa.String(36), sa.ForeignKey('cards.id'), nullable=False),
        # ... more columns
        sa.UniqueConstraint('user_id', 'card_id'),
    )

def downgrade():
    op.drop_table('card_progress')
```

### Adding pgvector column
```python
def upgrade():
    # Ensure extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.add_column('cards', sa.Column('embedding', Vector(1536), nullable=True))

def downgrade():
    op.drop_column('cards', 'embedding')
```

## Gotchas
- **Autogenerate misses**: custom types (Vector), CHECK constraints, partial indexes.
  Always review the generated file.
- **Railway release command**: `alembic upgrade head` runs before the app starts.
  If migration fails, deploy rolls back.
- **Test DB uses create_all, not migrations**: tests use Base.metadata.create_all()
  for speed. This means a migration bug won't show up in tests — always test
  rollback separately.
- **Deferred type promotions**: id columns are VARCHAR(36) not native UUID,
  DateTime is timezone-naive. Both are intentional deferrals documented in
  the Phase 0 migration. A future spec will handle the promotion.

## Key Files
- `alembic.ini` — config (reads DATABASE_URL from env via env.py)
- `alembic/env.py` — migration environment (async engine, imports all models)
- `alembic/versions/` — migration files (ordered by revision ID)
- `app/models/base.py` — Base declarative class