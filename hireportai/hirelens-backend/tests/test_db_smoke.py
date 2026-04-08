"""Smoke tests against a live PostgreSQL + pgvector database.

Skipped automatically when ``TEST_DATABASE_URL`` is unreachable (see
``conftest.py``).
"""
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.models.subscription import Subscription
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_pgvector_extension_present(db_session):
    result = await db_session.execute(
        sa.text("SELECT extname FROM pg_extension WHERE extname='vector'")
    )
    rows = result.fetchall()
    assert len(rows) == 1


async def test_user_insert_roundtrip(db_session):
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    fetched = await db_session.get(User, user.id)
    assert fetched is not None
    assert fetched.email == user.email


async def test_subscription_fk_enforced(db_session):
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),  # bogus — no matching users row
        plan="free",
        status="active",
    )
    db_session.add(sub)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_vector_roundtrip(db_session):
    await db_session.execute(
        sa.text("CREATE TEMP TABLE tmp_vec (id int, embedding vector(3))")
    )
    await db_session.execute(
        sa.text("INSERT INTO tmp_vec (id, embedding) VALUES (1, '[1.0,2.0,3.0]')")
    )
    result = await db_session.execute(
        sa.text("SELECT embedding::text FROM tmp_vec WHERE id=1")
    )
    value = result.scalar_one()
    assert value == "[1,2,3]"
