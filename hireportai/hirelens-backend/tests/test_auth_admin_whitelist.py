"""Admin email whitelist tests (spec #54 / E-040).

Covers login-time role reconciliation against the ``ADMIN_EMAILS`` env
var: promote whitelisted users, demote stale admins removed from the
list, emit ``admin_role_reconciled`` analytics on every login, write
``admin_audit_log`` rows only when the role actually changes.
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import app
from app.models.admin_audit_log import AdminAuditLog
from app.models.user import User
from app.services.user_service import reconcile_admin_role

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture
def override_admin_emails():
    """Context-manager factory that overrides ``settings.admin_emails_set``.

    Clears the ``get_settings`` lru cache, stubs a fresh Settings with
    the requested ``admin_emails`` env value, and restores on teardown.
    """
    originals: list = []

    def _override(value: str):
        get_settings.cache_clear()
        patched = Settings()
        object.__setattr__(patched, "admin_emails", value)
        from app.core import config as config_mod

        original = config_mod.get_settings
        originals.append(original)

        def _patched_get_settings():
            return patched

        config_mod.get_settings = _patched_get_settings  # type: ignore[assignment]

        from app.api.v1.routes import auth as auth_mod

        auth_mod.get_settings = _patched_get_settings  # type: ignore[assignment]
        return patched

    yield _override

    from app.core import config as config_mod
    from app.api.v1.routes import auth as auth_mod

    if originals:
        config_mod.get_settings = originals[0]  # type: ignore[assignment]
        auth_mod.get_settings = originals[0]  # type: ignore[assignment]
    get_settings.cache_clear()


def _google_user(**overrides) -> dict:
    base = {
        "google_id": f"g-{uuid.uuid4()}",
        "email": f"{uuid.uuid4()}@example.com",
        "name": "Test User",
        "avatar_url": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Pure-function unit tests: reconcile_admin_role
# ---------------------------------------------------------------------------


async def test_reconcile_promotes_whitelisted_user():
    user = User(
        id=str(uuid.uuid4()),
        google_id="g1",
        email="new-admin@example.com",
        name="N",
        role="user",
    )
    action, prior, new = reconcile_admin_role(
        user, frozenset({"new-admin@example.com"})
    )
    assert action == "promoted"
    assert prior == "user"
    assert new == "admin"
    assert user.role == "admin"


async def test_reconcile_demotes_stale_admin():
    user = User(
        id=str(uuid.uuid4()),
        google_id="g2",
        email="ex-admin@example.com",
        name="E",
        role="admin",
    )
    action, prior, new = reconcile_admin_role(user, frozenset())
    assert action == "demoted"
    assert prior == "admin"
    assert new == "user"
    assert user.role == "user"


async def test_reconcile_unchanged_for_already_correct_role():
    user = User(
        id=str(uuid.uuid4()),
        google_id="g3",
        email="regular@example.com",
        name="R",
        role="user",
    )
    action, prior, new = reconcile_admin_role(user, frozenset())
    assert action == "unchanged"
    assert prior == "user"
    assert new == "user"
    assert user.role == "user"


async def test_reconcile_case_insensitive_match():
    user = User(
        id=str(uuid.uuid4()),
        google_id="g4",
        email="Foo@Bar.com",
        name="F",
        role="user",
    )
    # Whitelist stores lowercased strings; the caller (config.admin_emails_set)
    # is responsible for lowercasing; reconcile_admin_role lowercases the
    # user's email on the match side.
    action, *_ = reconcile_admin_role(user, frozenset({"foo@bar.com"}))
    assert action == "promoted"
    assert user.role == "admin"


# ---------------------------------------------------------------------------
# Settings parsing tests
# ---------------------------------------------------------------------------


async def test_admin_emails_set_parses_comma_list_with_whitespace_and_case():
    s = Settings()
    object.__setattr__(s, "admin_emails", " A@B.com , c@d.com ,,")
    assert s.admin_emails_set == frozenset({"a@b.com", "c@d.com"})


async def test_admin_emails_set_empty_env_is_empty_frozenset():
    s = Settings()
    object.__setattr__(s, "admin_emails", "")
    assert s.admin_emails_set == frozenset()


# ---------------------------------------------------------------------------
# Integration: POST /api/v1/auth/google + reconciliation side effects
# ---------------------------------------------------------------------------


async def test_login_whitelisted_email_promotes_to_admin(
    client, db_session, override_admin_emails
):
    override_admin_emails("promoted@example.com")
    user_info = _google_user(email="promoted@example.com")
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ), patch("app.api.v1.routes.auth.analytics_track") as mock_track:
        resp = await client.post(
            "/api/v1/auth/google", json={"credential": "x"}
        )
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"
    row = (
        await db_session.execute(
            select(User).where(User.email == "promoted@example.com")
        )
    ).scalar_one()
    assert row.role == "admin"
    assert any(
        call.kwargs.get("event") == "admin_role_reconciled"
        and call.kwargs.get("properties", {}).get("action") == "promoted"
        for call in mock_track.call_args_list
    )


async def test_login_non_whitelisted_demotes_stale_admin(
    client, db_session, override_admin_emails
):
    override_admin_emails("someone-else@example.com")
    user_info = _google_user(email="stale-admin@example.com")
    # Seed a user already marked admin in DB.
    db_session.add(
        User(
            id=str(uuid.uuid4()),
            google_id=user_info["google_id"],
            email="stale-admin@example.com",
            name="S",
            role="admin",
        )
    )
    await db_session.flush()
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        resp = await client.post(
            "/api/v1/auth/google", json={"credential": "x"}
        )
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "user"
    row = (
        await db_session.execute(
            select(User).where(User.email == "stale-admin@example.com")
        )
    ).scalar_one()
    assert row.role == "user"


async def test_empty_admin_emails_demotes_all(
    client, db_session, override_admin_emails
):
    override_admin_emails("")
    user_info = _google_user(email="no-longer-admin@example.com")
    db_session.add(
        User(
            id=str(uuid.uuid4()),
            google_id=user_info["google_id"],
            email="no-longer-admin@example.com",
            name="N",
            role="admin",
        )
    )
    await db_session.flush()
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        resp = await client.post(
            "/api/v1/auth/google", json={"credential": "x"}
        )
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "user"


async def test_unchanged_role_writes_no_audit_row(
    client, db_session, override_admin_emails
):
    override_admin_emails("")
    user_info = _google_user(email="regular@example.com")
    audit_before = (
        await db_session.execute(select(AdminAuditLog))
    ).scalars().all()
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        await client.post("/api/v1/auth/google", json={"credential": "x"})
    audit_after = (
        await db_session.execute(select(AdminAuditLog))
    ).scalars().all()
    assert len(audit_after) == len(audit_before)


async def test_audit_row_written_on_promotion(
    client, db_session, override_admin_emails
):
    override_admin_emails("auditable@example.com")
    user_info = _google_user(email="auditable@example.com")
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ):
        await client.post("/api/v1/auth/google", json={"credential": "x"})
    user = (
        await db_session.execute(
            select(User).where(User.email == "auditable@example.com")
        )
    ).scalar_one()
    audit = (
        await db_session.execute(
            select(AdminAuditLog).where(AdminAuditLog.admin_id == user.id)
        )
    ).scalars().all()
    assert len(audit) == 1
    row = audit[0]
    assert row.route == "/api/v1/auth/google"
    assert row.method == "POST"
    assert row.query_params["action"] == "promoted"
    assert row.query_params["prior_role"] == "user"
    assert row.query_params["new_role"] == "admin"


async def test_admin_role_reconciled_event_fires_on_every_login(
    client, db_session, override_admin_emails
):
    override_admin_emails("")
    user_info = _google_user(email="heartbeat@example.com")
    with patch(
        "app.api.v1.routes.auth.verify_google_token",
        new=AsyncMock(return_value=user_info),
    ), patch("app.api.v1.routes.auth.analytics_track") as mock_track:
        await client.post("/api/v1/auth/google", json={"credential": "x"})
    events = [
        call
        for call in mock_track.call_args_list
        if call.kwargs.get("event") == "admin_role_reconciled"
    ]
    assert len(events) == 1
    props = events[0].kwargs["properties"]
    assert props["action"] in ("promoted", "demoted", "unchanged")
    assert props["email"] == "heartbeat@example.com"
    assert "prior_role" in props
    assert "new_role" in props
