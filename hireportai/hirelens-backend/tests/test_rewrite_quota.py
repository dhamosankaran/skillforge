"""Spec #58 — HTTP contract tests for /rewrite, /rewrite/section, /cover-letter.

Covers AC-1..AC-7 (auth + quota envelope shape) without invoking the
actual LLM path. The 402 gate fires before any LLM work; the Pro / admin
path is asserted by `status != 402` since the downstream GPT service is
unavailable under test (no API key). We patch `generate_for_task` at the
Pro-path test sites to exercise the 200 contract cleanly.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.response_models import (
    CoverLetterResponse,
    CoverLetterRecipient,
    RewriteResponse,
    RewriteSection,
)
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
        name="Rewrite Quota Test",
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


def _rewrite_body() -> dict:
    return {
        "resume_text": "John Doe\nSoftware Engineer\n" + "x" * 200,
        "job_description": (
            "Senior Python engineer. 5+ years FastAPI and distributed systems."
        ),
    }


def _section_body() -> dict:
    return {
        "section_id": "sec-0",
        "section_title": "Experience",
        "section_text": "Built things. Shipped to production.",
        "jd_text": "Senior Python engineer at a fast-moving startup.",
    }


def _cover_letter_body() -> dict:
    return {
        "resume_text": "John Doe\nSoftware Engineer\n" + "x" * 200,
        "job_description": "Senior Python engineer role with FastAPI experience.",
        "tone": "professional",
    }


def _fake_rewrite_result() -> RewriteResponse:
    section = RewriteSection(
        title="Experience",
        content="Shipped production Python services.",
        entries=[],
    )
    return RewriteResponse(
        sections=[section],
        full_text="Shipped production Python services.",
    )


def _fake_cover_letter_result() -> CoverLetterResponse:
    return CoverLetterResponse(
        date="2026-04-23",
        recipient=CoverLetterRecipient(name="Hiring Manager", company="Acme Inc"),
        greeting="Dear Hiring Manager,",
        body_paragraphs=["Paragraph one.", "Paragraph two.", "Paragraph three."],
        signoff="Sincerely,",
        signature="John Doe",
        tone="professional",
        full_text="Cover letter body.",
    )


# ── /rewrite ────────────────────────────────────────────────────────────


async def test_rewrite_anonymous_returns_401(client):
    resp = await client.post("/api/v1/rewrite", json=_rewrite_body())
    assert resp.status_code == 401


async def test_rewrite_free_user_returns_402_with_spec58_envelope(
    client, db_session
):
    user = await _seed_user(db_session, plan="free")
    resp = await client.post(
        "/api/v1/rewrite", headers=_auth(user), json=_rewrite_body()
    )
    assert resp.status_code == 402
    detail = resp.json()["detail"]
    assert detail["error"] == "free_tier_limit"
    assert detail["trigger"] == "rewrite_limit"
    assert detail["feature"] == "rewrite"
    assert detail["attempted_action"] == "full"
    assert detail["plan"] == "free"

    # 402 path must not write a usage row (allowed=False path skips log_usage).
    rows = (
        await db_session.execute(
            __import__("sqlalchemy").select(UsageLog).where(
                UsageLog.user_id == user.id, UsageLog.feature_used == "rewrite"
            )
        )
    ).scalars().all()
    assert rows == []


async def test_rewrite_pro_user_returns_200(client, db_session):
    """Pro user passes the quota gate and reaches the service layer.

    Note: `check_and_increment` short-circuits on `max_uses == -1` BEFORE
    calling `log_usage` (usage_service.py:151-152, shipped by B-031 for
    `analyze` — same code path applies here). Pro users therefore do NOT
    write `usage_logs` rows. This is inconsistent with spec §12's claim
    that post-impl `log_usage` firing "retroactively surfaces the spend
    in the admin cost dashboard" — the Pro-path log call does not
    actually happen. Tracked as drift for Dhamo / follow-up spec errata
    slice (see SESSION-STATE.md D-021 note).
    """
    user = await _seed_user(db_session, plan="pro")

    fake = _fake_rewrite_result()
    with patch(
        "app.services.gpt_service.generate_resume_rewrite_async",
        new=AsyncMock(return_value=(fake, "chunked")),
    ):
        resp = await client.post(
            "/api/v1/rewrite", headers=_auth(user), json=_rewrite_body()
        )

    assert resp.status_code == 200, resp.json()


async def test_rewrite_admin_bypasses_cap(client, db_session):
    """Admin on free plan: admin bypass in check_and_increment returns
    allowed=True without logging. Resource runs through to the LLM."""
    user = await _seed_user(db_session, plan="free", role="admin")
    fake = _fake_rewrite_result()
    with patch(
        "app.services.gpt_service.generate_resume_rewrite_async",
        new=AsyncMock(return_value=(fake, "chunked")),
    ):
        resp = await client.post(
            "/api/v1/rewrite", headers=_auth(user), json=_rewrite_body()
        )
    assert resp.status_code == 200, resp.json()


# ── /rewrite/section (shared bucket per spec #58 §4.1 Option a) ─────────


async def test_section_rewrite_anonymous_returns_401(client):
    resp = await client.post("/api/v1/rewrite/section", json=_section_body())
    assert resp.status_code == 401


async def test_section_rewrite_free_user_hits_shared_rewrite_bucket(
    client, db_session
):
    """Free user hitting `/rewrite/section` is walled against the same
    `"rewrite"` bucket — `attempted_action='section'` on the envelope."""
    user = await _seed_user(db_session, plan="free")
    resp = await client.post(
        "/api/v1/rewrite/section", headers=_auth(user), json=_section_body()
    )
    assert resp.status_code == 402
    detail = resp.json()["detail"]
    assert detail["trigger"] == "rewrite_limit"
    assert detail["feature"] == "rewrite"
    assert detail["attempted_action"] == "section"
    assert detail["plan"] == "free"


async def test_section_rewrite_pro_user_returns_200(client, db_session):
    user = await _seed_user(db_session, plan="pro")
    section = RewriteSection(
        title="Experience",
        content="Regenerated content.",
        entries=[],
    )
    with patch(
        "app.services.gpt_service.generate_section_rewrite",
        new=AsyncMock(return_value=section),
    ):
        resp = await client.post(
            "/api/v1/rewrite/section",
            headers=_auth(user),
            json=_section_body(),
        )
    assert resp.status_code == 200, resp.json()


# ── /cover-letter ──────────────────────────────────────────────────────


async def test_cover_letter_anonymous_returns_401(client):
    resp = await client.post("/api/v1/cover-letter", json=_cover_letter_body())
    assert resp.status_code == 401


async def test_cover_letter_free_user_returns_402_with_cover_letter_trigger(
    client, db_session
):
    user = await _seed_user(db_session, plan="free")
    resp = await client.post(
        "/api/v1/cover-letter", headers=_auth(user), json=_cover_letter_body()
    )
    assert resp.status_code == 402
    detail = resp.json()["detail"]
    assert detail["error"] == "free_tier_limit"
    assert detail["trigger"] == "cover_letter_limit"
    assert detail["feature"] == "cover_letter"
    assert detail["plan"] == "free"


async def test_cover_letter_pro_user_returns_200(client, db_session):
    user = await _seed_user(db_session, plan="pro")
    fake = _fake_cover_letter_result()
    # The route calls gpt_service.generate_cover_letter (sync); patch it.
    with patch(
        "app.api.routes.cover_letter.gpt_cover_letter",
        new=MagicMock(return_value=fake),
    ):
        resp = await client.post(
            "/api/v1/cover-letter",
            headers=_auth(user),
            json=_cover_letter_body(),
        )
    assert resp.status_code == 200, resp.json()


async def test_cover_letter_admin_bypasses_cap(client, db_session):
    user = await _seed_user(db_session, plan="free", role="admin")
    fake = _fake_cover_letter_result()
    with patch(
        "app.api.routes.cover_letter.gpt_cover_letter",
        new=MagicMock(return_value=fake),
    ):
        resp = await client.post(
            "/api/v1/cover-letter",
            headers=_auth(user),
            json=_cover_letter_body(),
        )
    assert resp.status_code == 200, resp.json()
