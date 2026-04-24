"""Spec #56 AC-2 / AC-5 — 402 response contract on /api/v1/analyze.

Dedicated file so the quota surface is testable without pulling in the
full analyze-pipeline mocks; we exercise the `check_and_increment` gate
by seeding a prior usage_logs row and asserting the 402 fires before any
parsing / LLM work kicks in.
"""
from __future__ import annotations

import io
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _seed_user(db_session, *, plan: str = "free", role: str = "user") -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Analyze Quota Test",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Subscription(user_id=user.id, plan=plan, status="active"))
    await db_session.flush()
    await db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    tok = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {tok}"}


def _fake_pdf() -> io.BytesIO:
    # Not a real parseable PDF, but the quota gate fires before the parser
    # ever sees the bytes. We only need to pass the minimum-size validator
    # (>= 100 bytes). The 402 path is asserted before parse_pdf() runs.
    return io.BytesIO(b"%PDF-1.4\n" + b"x" * 200)


def _form(filename: str = "resume.pdf") -> dict:
    files = {
        "resume_file": (filename, _fake_pdf(), "application/pdf"),
    }
    data = {
        "job_description": (
            "We are hiring a senior engineer with experience in Python, FastAPI, "
            "and distributed systems. Must have 5+ years building scalable backend "
            "services and a track record of shipping to production."
        ),
    }
    return {"files": files, "data": data}


async def test_free_user_with_prior_scan_gets_402_with_spec50_shape(client, db_session):
    """AC-2 — free user with 1 prior analyze row is walled with the spec #50
    envelope shape (error / trigger / plan + counter fields)."""
    user = await _seed_user(db_session, plan="free")
    db_session.add(UsageLog(user_id=user.id, feature_used="analyze", tokens_consumed=0))
    await db_session.flush()

    resp = await client.post(
        "/api/v1/analyze",
        headers=_auth(user),
        **_form(),
    )
    assert resp.status_code == 402
    body = resp.json()
    detail = body["detail"]
    assert detail["error"] == "free_tier_limit"
    assert detail["trigger"] == "scan_limit"
    assert detail["scans_used"] == 1
    assert detail["scans_limit"] == 1
    assert detail["plan"] == "free"


async def test_admin_bypasses_cap(client, db_session):
    """AC-4 — admin bypass clears the quota gate regardless of plan.

    Admin still flows through to the parser, which will fail on our fake
    PDF with a 422. The test asserts we got PAST the 402 gate — anything
    other than 402 is proof enough that the bypass worked; we don't need
    a real parseable PDF for that.
    """
    user = await _seed_user(db_session, plan="free", role="admin")
    db_session.add(UsageLog(user_id=user.id, feature_used="analyze", tokens_consumed=0))
    await db_session.flush()

    resp = await client.post(
        "/api/v1/analyze",
        headers=_auth(user),
        **_form(),
    )
    assert resp.status_code != 402, (
        f"admin bypass failed — got 402: {resp.json()}"
    )
