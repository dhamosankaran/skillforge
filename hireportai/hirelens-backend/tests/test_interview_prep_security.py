"""E-037 — auth hardening + per-IP rate limit on Pro-tier LLM endpoints.

Closes the interview-prep half of E-037 (rewrite + cover-letter halves
were closed by B-033 / spec #58). Anonymous callers used to fall through
`get_current_user_optional` and reach Pro-tier Gemini without a quota
check; this slice flips to hard auth (`get_current_user`) so the
existing monthly cap inside `interview_storage_service` always fires.

Also exercises the slowapi `10/minute` per-route rate-limit decorator
wired across the four Pro-tier LLM endpoints (rewrite, rewrite/section,
cover-letter, interview-prep). Pattern mirrors `tests/test_rate_limit.py`:
re-enable the limiter inside a scoped fixture, clear in-memory counters
before and after.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.response_models import (
    CoverLetterRecipient,
    CoverLetterResponse,
    RewriteResponse,
    RewriteSection,
)
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.responses import InterviewPrepResponse, InterviewQuestion

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _interview_body() -> dict:
    return {
        "resume_text": "John Doe\nSoftware Engineer\n" + "x" * 200,
        "job_description": (
            "Senior Python engineer. 5+ years FastAPI and distributed systems."
        ),
    }


def _fake_interview_result() -> InterviewPrepResponse:
    return InterviewPrepResponse(
        questions=[
            InterviewQuestion(
                question="Tell me about a system you scaled.",
                star_framework="S: ... T: ... A: ... R: ...",
            ),
        ],
    )


def _clear_rate_limit_storage() -> None:
    if hasattr(limiter, "_storage"):
        storage = limiter._storage
        for attr in ("storage", "expirations", "events"):
            bucket = getattr(storage, attr, None)
            if bucket is not None and hasattr(bucket, "clear"):
                bucket.clear()


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


@pytest_asyncio.fixture(loop_scope="session")
async def rl_client(db_session):
    """HTTP client with rate limiting enabled and DB session override.

    `Depends(get_current_user)` resolves before slowapi's limit wrapper
    runs, so anonymous calls short-circuit to 401 without bumping the
    counter. The rate-limit tests therefore need authenticated requests
    — which requires the same db override the regular `client` fixture
    uses.
    """
    _clear_rate_limit_storage()
    limiter.enabled = True

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
        limiter.enabled = False
        _clear_rate_limit_storage()


async def _seed_user(db_session, *, plan: str = "free", role: str = "user") -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Interview Prep Security Test",
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


# ── Auth hardening ──────────────────────────────────────────────────────


async def test_interview_prep_v1_anonymous_returns_401(client):
    """E-037 — `/api/v1/interview-prep` rejects anonymous callers."""
    resp = await client.post("/api/v1/interview-prep", json=_interview_body())
    assert resp.status_code == 401


async def test_interview_prep_legacy_anonymous_returns_401(client):
    """E-037 — legacy `/api/interview-prep` rejects anonymous callers
    (router is re-mounted; same handler, both surfaces enforce auth)."""
    resp = await client.post("/api/interview-prep", json=_interview_body())
    assert resp.status_code == 401


async def test_interview_prep_free_user_under_cap_returns_200(client, db_session):
    """Free user with no prior usage passes the monthly quota gate and
    reaches the LLM (mocked) on the cache-miss path."""
    user = await _seed_user(db_session, plan="free")
    fake = _fake_interview_result()
    with patch(
        "app.services.gpt_service.generate_interview_questions",
        new=MagicMock(return_value=fake),
    ):
        resp = await client.post(
            "/api/v1/interview-prep",
            headers=_auth(user),
            json=_interview_body(),
        )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["cached"] is False
    assert len(body["questions"]) == 1


async def test_interview_prep_pro_user_returns_200(client, db_session):
    """Pro user passes quota (unlimited) and reaches the LLM on cache miss."""
    user = await _seed_user(db_session, plan="pro")
    fake = _fake_interview_result()
    with patch(
        "app.services.gpt_service.generate_interview_questions",
        new=MagicMock(return_value=fake),
    ):
        resp = await client.post(
            "/api/v1/interview-prep",
            headers=_auth(user),
            json=_interview_body(),
        )
    assert resp.status_code == 200, resp.json()


# ── Rate-limit defense-in-depth ────────────────────────────────────────


async def test_interview_prep_rate_limited_after_10_requests(rl_client, db_session):
    """11th authed request to `/api/v1/interview-prep` returns 429.

    Uses a Pro user so the per-user monthly quota does not gate any
    request; slowapi's `10/minute` limit fires on the 11th. The auth
    dependency resolves before the limit wrapper runs (FastAPI Depends
    order), so unauthed calls short-circuit to 401 without bumping the
    counter — defense-in-depth here protects against a single
    compromised account, not anonymous abuse.
    """
    user = await _seed_user(db_session, plan="pro")
    headers = _auth(user)
    payload = _interview_body()
    fake = _fake_interview_result()
    with patch(
        "app.services.gpt_service.generate_interview_questions",
        new=MagicMock(return_value=fake),
    ):
        for i in range(10):
            resp = await rl_client.post(
                "/api/v1/interview-prep", headers=headers, json=payload
            )
            assert resp.status_code != 429, (
                f"Hit rate limit too early on request {i + 1}"
            )
        resp = await rl_client.post(
            "/api/v1/interview-prep", headers=headers, json=payload
        )
    assert resp.status_code == 429


async def test_rewrite_rate_limited_after_10_requests(rl_client, db_session):
    """E-037 — 11th authed request to `/api/v1/rewrite` returns 429."""
    user = await _seed_user(db_session, plan="pro")
    headers = _auth(user)
    payload = {
        "resume_text": "John Doe\nSoftware Engineer\n" + "x" * 200,
        "job_description": (
            "Senior Python engineer. 5+ years FastAPI and distributed systems."
        ),
    }
    fake = RewriteResponse(
        sections=[
            RewriteSection(title="Experience", content="Shipped.", entries=[])
        ],
        full_text="Shipped.",
    )
    with patch(
        "app.services.gpt_service.generate_resume_rewrite_async",
        new=AsyncMock(return_value=(fake, "chunked")),
    ):
        for i in range(10):
            resp = await rl_client.post(
                "/api/v1/rewrite", headers=headers, json=payload
            )
            assert resp.status_code != 429, (
                f"Hit rate limit too early on request {i + 1}"
            )
        resp = await rl_client.post(
            "/api/v1/rewrite", headers=headers, json=payload
        )
    assert resp.status_code == 429


async def test_cover_letter_rate_limited_after_10_requests(rl_client, db_session):
    """E-037 — 11th authed request to `/api/v1/cover-letter` returns 429."""
    user = await _seed_user(db_session, plan="pro")
    headers = _auth(user)
    payload = {
        "resume_text": "John Doe\nSoftware Engineer\n" + "x" * 200,
        "job_description": (
            "Senior Python engineer. 5+ years FastAPI and distributed systems."
        ),
        "tone": "professional",
    }
    fake = CoverLetterResponse(
        date="2026-05-03",
        recipient=CoverLetterRecipient(name="Hiring Manager", company="Acme"),
        greeting="Dear Hiring Manager,",
        body_paragraphs=["P1.", "P2.", "P3."],
        signoff="Sincerely,",
        signature="John Doe",
        tone="professional",
        full_text="Body.",
    )
    with patch(
        "app.api.routes.cover_letter.gpt_cover_letter",
        new=MagicMock(return_value=fake),
    ):
        for i in range(10):
            resp = await rl_client.post(
                "/api/v1/cover-letter", headers=headers, json=payload
            )
            assert resp.status_code != 429, (
                f"Hit rate limit too early on request {i + 1}"
            )
        resp = await rl_client.post(
            "/api/v1/cover-letter", headers=headers, json=payload
        )
    assert resp.status_code == 429
