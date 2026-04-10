"""Payments route tests (Spec #11).

All Stripe SDK calls are patched — these tests never hit the network and
do not require ``STRIPE_SECRET_KEY`` to be set. The DB session comes from
the shared ``db_session`` fixture in ``conftest.py`` and rolls back on
teardown, so plan flips are isolated between tests.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.stripe_event import StripeEvent
from app.models.subscription import Subscription
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    """HTTP client with the test DB session injected into FastAPI."""
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
async def test_user(db_session) -> User:
    """Insert a User + free Subscription row for the test."""
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Pay Test User",
    )
    db_session.add(user)
    await db_session.flush()

    sub = Subscription(user_id=user.id, plan="free", status="active")
    db_session.add(sub)
    await db_session.flush()
    return user


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


# ── POST /payments/checkout ─────────────────────────────────────────────────


async def test_create_checkout_session(client, test_user, monkeypatch):
    """Happy path — endpoint returns the URL from the mocked Checkout Session.

    Mocks both ``stripe.Customer.create`` (first-time customer) and
    ``stripe.checkout.Session.create``.
    """
    monkeypatch.setenv("STRIPE_PRO_PRICE_ID", "price_test_123")
    # Settings is cached; patch the attribute directly.
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.stripe_pro_price_id = "price_test_123"
    settings.stripe_secret_key = "sk_test_dummy"

    fake_customer = SimpleNamespace(id="cus_test_abc")
    fake_session = SimpleNamespace(
        id="cs_test_xyz",
        url="https://checkout.stripe.com/c/pay/cs_test_xyz",
    )

    with patch(
        "app.services.payment_service.stripe.Customer.create",
        return_value=fake_customer,
    ) as customer_mock, patch(
        "app.services.payment_service.stripe.checkout.Session.create",
        return_value=fake_session,
    ) as session_mock:
        resp = await client.post(
            "/api/v1/payments/checkout", headers=_auth_header(test_user)
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"url": fake_session.url}

    customer_mock.assert_called_once()
    session_mock.assert_called_once()
    kwargs = session_mock.call_args.kwargs
    assert kwargs["customer"] == "cus_test_abc"
    assert kwargs["mode"] == "subscription"
    assert kwargs["line_items"] == [{"price": "price_test_123", "quantity": 1}]
    assert kwargs["client_reference_id"] == test_user.id


async def test_requires_auth_for_checkout(client):
    """Unauthenticated requests are rejected with 401."""
    resp = await client.post("/api/v1/payments/checkout")
    assert resp.status_code == 401


# ── POST /payments/webhook ──────────────────────────────────────────────────


async def test_webhook_activates_pro(client, test_user, db_session):
    """A signed checkout.session.completed event flips the user to Pro."""
    # Seed the stripe_customer_id so _find_subscription can also fall back
    # on it, though client_reference_id (user_id) is the primary key.
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.stripe_customer_id = "cus_test_abc"
    await db_session.flush()

    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": test_user.id,
                "customer": "cus_test_abc",
                "subscription": "sub_test_123",
                "amount_total": 4900,
                "currency": "usd",
                "metadata": {"user_id": test_user.id, "plan": "pro"},
            }
        },
    }

    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        return_value=fake_event,
    ):
        resp = await client.post(
            "/api/v1/payments/webhook",
            content=json.dumps(fake_event).encode(),
            headers={"stripe-signature": "t=1,v1=fake"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["received"] is True
    assert body["event_type"] == "checkout.session.completed"

    # Re-read from the session identity map (no refresh — the handler
    # mutates the ORM object but does not commit, so refresh() would
    # clobber those changes from the unwritten DB row).
    sub_after = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    assert sub_after.plan == "pro"
    assert sub_after.status == "active"
    assert sub_after.stripe_subscription_id == "sub_test_123"


async def test_webhook_cancels_pro(client, test_user, db_session):
    """customer.subscription.deleted flips the user back to Free."""
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.plan = "pro"
    sub.status = "active"
    sub.stripe_customer_id = "cus_cancel_abc"
    sub.stripe_subscription_id = "sub_cancel_123"
    await db_session.flush()

    fake_event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_cancel_123",
                "customer": "cus_cancel_abc",
            }
        },
    }

    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        return_value=fake_event,
    ):
        resp = await client.post(
            "/api/v1/payments/webhook",
            content=json.dumps(fake_event).encode(),
            headers={"stripe-signature": "t=1,v1=fake"},
        )

    assert resp.status_code == 200, resp.text

    sub_after = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    assert sub_after.plan == "free"
    assert sub_after.status == "canceled"
    assert sub_after.stripe_subscription_id is None


async def test_duplicate_webhook_is_idempotent(client, test_user, db_session):
    """Sending the same Stripe event twice only changes user.plan once."""
    # Ensure user starts on free plan.
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.plan = "free"
    sub.status = "active"
    sub.stripe_customer_id = "cus_idem_abc"
    sub.stripe_subscription_id = None
    await db_session.flush()

    fake_event = {
        "id": "evt_idempotent_test_001",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": test_user.id,
                "customer": "cus_idem_abc",
                "subscription": "sub_idem_123",
                "amount_total": 4900,
                "currency": "usd",
                "metadata": {"user_id": test_user.id, "plan": "pro"},
            }
        },
    }
    payload = json.dumps(fake_event).encode()
    headers = {"stripe-signature": "t=1,v1=fake"}

    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        return_value=fake_event,
    ):
        # First delivery — should process and flip to pro.
        resp1 = await client.post(
            "/api/v1/payments/webhook", content=payload, headers=headers
        )
        assert resp1.status_code == 200

        # Second delivery — duplicate, should be a no-op.
        resp2 = await client.post(
            "/api/v1/payments/webhook", content=payload, headers=headers
        )
        assert resp2.status_code == 200

    # Plan should be pro (set once, not toggled or errored).
    sub_after = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    assert sub_after.plan == "pro"

    # Only one StripeEvent row for that event ID.
    event_rows = (
        await db_session.execute(
            select(StripeEvent).where(StripeEvent.id == "evt_idempotent_test_001")
        )
    ).scalars().all()
    assert len(event_rows) == 1


async def test_webhook_rejects_invalid_signature(client):
    """A signature verification failure returns 400 and does not mutate state."""
    import stripe

    def _raise(*_args, **_kwargs):
        raise stripe.error.SignatureVerificationError("bad sig", "sig_header")

    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        side_effect=_raise,
    ):
        resp = await client.post(
            "/api/v1/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=nope"},
        )

    assert resp.status_code == 400
