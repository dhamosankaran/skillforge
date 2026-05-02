"""Payments route tests (Spec #11).

All Stripe SDK calls are patched — these tests never hit the network and
do not require ``STRIPE_SECRET_KEY`` to be set. The DB session comes from
the shared ``db_session`` fixture in ``conftest.py`` and rolls back on
teardown, so plan flips are isolated between tests.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
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


async def test_checkout_falls_back_to_geo_when_currency_missing(
    client, test_user, monkeypatch
):
    """Empty body from an Indian IP picks the INR price id via get_pricing()."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.stripe_pro_price_id = "price_usd_test"
    settings.stripe_pro_price_id_inr = "price_inr_test"
    settings.stripe_secret_key = "sk_test_dummy"

    fake_customer = SimpleNamespace(id="cus_geo_fallback")
    fake_session = SimpleNamespace(
        id="cs_geo_fallback",
        url="https://checkout.stripe.com/c/pay/cs_geo_fallback",
    )

    # Patch the geo resolver at the import site in payments.py so the
    # fallback branch is exercised without hitting ip-api.com.
    def _fake_get_pricing(_ip: str) -> dict:
        return {
            "currency": "inr",
            "price": 999,
            "price_display": "\u20b9999/mo",
            "stripe_price_id": "price_inr_test",
        }

    with patch(
        "app.api.routes.payments.get_pricing", side_effect=_fake_get_pricing
    ) as geo_mock, patch(
        "app.services.payment_service.stripe.Customer.create",
        return_value=fake_customer,
    ), patch(
        "app.services.payment_service.stripe.checkout.Session.create",
        return_value=fake_session,
    ) as session_mock:
        # Empty body (no currency field).
        resp = await client.post(
            "/api/v1/payments/checkout",
            headers={**_auth_header(test_user), "X-Forwarded-For": "103.21.244.0"},
        )

    assert resp.status_code == 200, resp.text
    geo_mock.assert_called_once()
    # Stripe line item uses the INR price, not the USD default.
    assert session_mock.call_args.kwargs["line_items"] == [
        {"price": "price_inr_test", "quantity": 1}
    ]


async def test_checkout_respects_client_currency_without_geo_lookup(
    client, test_user, monkeypatch
):
    """Client-provided currency is honoured — no geo lookup happens."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.stripe_pro_price_id = "price_usd_test"
    settings.stripe_pro_price_id_inr = "price_inr_test"
    settings.stripe_secret_key = "sk_test_dummy"

    fake_customer = SimpleNamespace(id="cus_client_override")
    fake_session = SimpleNamespace(
        id="cs_client_override",
        url="https://checkout.stripe.com/c/pay/cs_client_override",
    )

    with patch(
        "app.api.routes.payments.get_pricing"
    ) as geo_mock, patch(
        "app.services.payment_service.stripe.Customer.create",
        return_value=fake_customer,
    ), patch(
        "app.services.payment_service.stripe.checkout.Session.create",
        return_value=fake_session,
    ) as session_mock:
        resp = await client.post(
            "/api/v1/payments/checkout",
            headers=_auth_header(test_user),
            json={"currency": "inr"},
        )

    assert resp.status_code == 200, resp.text
    # Client explicitly asked for INR — the fallback must not run.
    geo_mock.assert_not_called()
    assert session_mock.call_args.kwargs["line_items"] == [
        {"price": "price_inr_test", "quantity": 1}
    ]


# ── F-1 Pro short-circuit (audit 2026-05) ────────────────────────────────────


async def test_checkout_409_when_user_already_active_pro(
    client, test_user, db_session
):
    """Active Pro subscriber gets 409 instead of a second Stripe subscription.

    Audit finding F-1: without this guard, Stripe permits multiple active
    subscriptions per Customer on the same Price, so a Pro user re-clicking
    Upgrade was previously double-charged.
    """
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.plan = "pro"
    sub.status = "active"
    sub.stripe_customer_id = "cus_already_pro"
    sub.stripe_subscription_id = "sub_already_pro"
    await db_session.flush()

    with patch(
        "app.services.payment_service.stripe.Customer.create"
    ) as customer_mock, patch(
        "app.services.payment_service.stripe.checkout.Session.create"
    ) as session_mock:
        resp = await client.post(
            "/api/v1/payments/checkout", headers=_auth_header(test_user)
        )

    assert resp.status_code == 409, resp.text
    assert resp.json() == {"detail": "Already subscribed to Pro plan"}
    # Guard fires before Stripe API touch.
    customer_mock.assert_not_called()
    session_mock.assert_not_called()


async def test_checkout_200_for_free_user_regression(
    client, test_user, db_session, monkeypatch
):
    """Free user still gets 200 + checkout URL — F-1 must not regress baseline."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.stripe_pro_price_id = "price_test_free_path"
    settings.stripe_secret_key = "sk_test_dummy"

    fake_customer = SimpleNamespace(id="cus_free_path")
    fake_session = SimpleNamespace(
        id="cs_free_path",
        url="https://checkout.stripe.com/c/pay/cs_free_path",
    )

    with patch(
        "app.services.payment_service.stripe.Customer.create",
        return_value=fake_customer,
    ), patch(
        "app.services.payment_service.stripe.checkout.Session.create",
        return_value=fake_session,
    ):
        resp = await client.post(
            "/api/v1/payments/checkout", headers=_auth_header(test_user)
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"url": fake_session.url}


async def test_checkout_409_for_admin_who_is_pro(
    client, test_user, db_session
):
    """Admin role does NOT bypass the F-1 guard — admin-Pro re-checkout still 409.

    Admin bypass exists for paywall walls (rate-limit / wall-hit short-
    circuits) but not for double-subscription. An admin who legitimately
    upgraded via Stripe and re-clicks Upgrade should still hit 409 — the
    guard protects against double-charging the admin too.
    """
    test_user.role = "admin"
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.plan = "pro"
    sub.status = "active"
    sub.stripe_customer_id = "cus_admin_pro"
    sub.stripe_subscription_id = "sub_admin_pro"
    await db_session.flush()

    with patch(
        "app.services.payment_service.stripe.checkout.Session.create"
    ) as session_mock:
        resp = await client.post(
            "/api/v1/payments/checkout", headers=_auth_header(test_user)
        )

    assert resp.status_code == 409, resp.text
    assert resp.json() == {"detail": "Already subscribed to Pro plan"}
    session_mock.assert_not_called()


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
        "id": "evt_activates_pro_001",
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
        "id": "evt_cancels_pro_001",
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


async def test_subscription_deleted_sets_downgraded_at(
    client, test_user, db_session
):
    """customer.subscription.deleted stamps user.downgraded_at (spec #42 LD-5)."""
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.plan = "pro"
    sub.status = "active"
    sub.stripe_customer_id = "cus_downgraded_xyz"
    sub.stripe_subscription_id = "sub_downgraded_999"
    await db_session.flush()
    assert test_user.downgraded_at is None

    fake_event = {
        "id": "evt_downgraded_at_001",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_downgraded_999",
                "customer": "cus_downgraded_xyz",
            }
        },
    }

    before = datetime.now(tz=timezone.utc)
    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        return_value=fake_event,
    ):
        resp = await client.post(
            "/api/v1/payments/webhook",
            content=json.dumps(fake_event).encode(),
            headers={"stripe-signature": "t=1,v1=fake"},
        )
    after = datetime.now(tz=timezone.utc)

    assert resp.status_code == 200, resp.text

    # Re-read from the session identity map (no refresh — the handler
    # mutates the ORM object but does not commit, so refresh() would
    # clobber those changes from the unwritten DB row; same pattern as
    # test_webhook_cancels_pro).
    user_after = (
        await db_session.execute(select(User).where(User.id == test_user.id))
    ).scalar_one()
    assert user_after.downgraded_at is not None
    assert before <= user_after.downgraded_at <= after


async def test_subscription_deleted_existing_logic_still_works(
    client, test_user, db_session
):
    """Regression guard: plan/status/stripe_subscription_id downgrade path
    is unchanged by the downgraded_at wire-up."""
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.plan = "pro"
    sub.status = "active"
    sub.stripe_customer_id = "cus_regression"
    sub.stripe_subscription_id = "sub_regression"
    await db_session.flush()

    fake_event = {
        "id": "evt_deleted_regression_001",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {"id": "sub_regression", "customer": "cus_regression"}
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
    assert resp.status_code == 200

    sub_after = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    assert sub_after.plan == "free"
    assert sub_after.status == "canceled"
    assert sub_after.stripe_subscription_id is None
    assert sub_after.current_period_end is None


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


async def test_handler_exception_rolls_back_stripe_event_row(
    test_user, db_session
):
    """Dispatch failure rolls back the stripe_events row; retry runs cleanly.

    Spec #43 AC-4. Invariant under test: if the event dispatcher raises
    after the idempotency row has been flushed but before the transaction
    commits, the row must be rolled back along with any partial mutation.
    A subsequent delivery of the same ``event.id`` must be processed as
    a first delivery (not silently skipped as a duplicate from the failed
    attempt).

    This test invokes ``payment_service.handle_webhook`` directly rather
    than through the HTTP client, and wraps the failing call in a
    SAVEPOINT (``begin_nested``) to mirror what ``app.db.session.get_db``
    does in production — ``except Exception: await session.rollback()``
    — without tearing down the shared ``db_session`` fixture state.
    """
    # Seed a customer_id on the test user's subscription so the real
    # dispatcher (second call) can locate the subscription by customer.
    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.stripe_customer_id = "cus_rollback_abc"
    await db_session.flush()

    event_id = "evt_rollback_test_001"
    fake_event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": test_user.id,
                "customer": "cus_rollback_abc",
                "subscription": "sub_rollback_123",
                "amount_total": 4900,
                "currency": "usd",
                "metadata": {"user_id": test_user.id, "plan": "pro"},
            }
        },
    }
    payload = json.dumps(fake_event).encode()
    signature = "t=1,v1=fake"

    from app.services import payment_service

    class DispatchFailure(RuntimeError):
        pass

    # First delivery: force the dispatcher to raise mid-transaction.
    # The SAVEPOINT here is the test-environment equivalent of the
    # per-request transaction boundary in production's get_db.
    savepoint = await db_session.begin_nested()
    try:
        with patch(
            "app.services.payment_service.stripe.Webhook.construct_event",
            return_value=fake_event,
        ), patch(
            "app.services.payment_service._handle_checkout_completed",
            new=AsyncMock(side_effect=DispatchFailure("simulated dispatch failure")),
        ):
            with pytest.raises(DispatchFailure):
                await payment_service.handle_webhook(
                    payload, signature, db_session
                )
    finally:
        await savepoint.rollback()

    # The idempotency row must not have survived the failed transaction.
    rows_after_failure = (
        await db_session.execute(
            select(StripeEvent).where(StripeEvent.id == event_id)
        )
    ).scalars().all()
    assert rows_after_failure == []

    # Second delivery of the same event.id: no patch on the dispatcher,
    # it runs normally. The handler must NOT short-circuit as a duplicate.
    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        return_value=fake_event,
    ):
        result = await payment_service.handle_webhook(
            payload, signature, db_session
        )

    assert result == {
        "received": True,
        "event_type": "checkout.session.completed",
    }

    # Exactly one idempotency row exists now — from the successful retry.
    rows_after_success = (
        await db_session.execute(
            select(StripeEvent).where(StripeEvent.id == event_id)
        )
    ).scalars().all()
    assert len(rows_after_success) == 1

    # And the dispatcher actually ran — the plan flipped to pro.
    sub_after = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    assert sub_after.plan == "pro"


# ── POST /payments/portal (Spec #36) ────────────────────────────────────────


async def test_create_portal_session_for_pro_user(client, test_user, db_session):
    """Pro user gets a Stripe-hosted billing portal URL back."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.stripe_secret_key = "sk_test_dummy"
    settings.frontend_url = "https://app.example.com"

    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.plan = "pro"
    sub.status = "active"
    sub.stripe_customer_id = "cus_portal_abc"
    await db_session.flush()

    fake_session = SimpleNamespace(
        id="bps_test_xyz",
        url="https://billing.stripe.com/p/session/bps_test_xyz",
    )

    with patch(
        "app.services.payment_service.stripe.billing_portal.Session.create",
        return_value=fake_session,
    ) as portal_mock:
        resp = await client.post(
            "/api/v1/payments/portal", headers=_auth_header(test_user)
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"url": fake_session.url}

    portal_mock.assert_called_once()
    kwargs = portal_mock.call_args.kwargs
    assert kwargs["customer"] == "cus_portal_abc"
    assert kwargs["return_url"] == "https://app.example.com/profile"


async def test_portal_session_403_for_free_user(client, test_user, db_session):
    """Free user (no stripe_customer_id) is rejected with 403."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.stripe_secret_key = "sk_test_dummy"

    # test_user fixture already seeds plan='free' with no customer_id.
    # No Stripe API calls should be made — patch to assert no-call.
    with patch(
        "app.services.payment_service.stripe.billing_portal.Session.create",
    ) as portal_mock:
        resp = await client.post(
            "/api/v1/payments/portal", headers=_auth_header(test_user)
        )

    assert resp.status_code == 403, resp.text
    portal_mock.assert_not_called()


async def test_portal_session_401_for_unauth(client):
    """Unauthenticated requests are rejected with 401, no Stripe call."""
    with patch(
        "app.services.payment_service.stripe.billing_portal.Session.create",
    ) as portal_mock:
        resp = await client.post("/api/v1/payments/portal")

    assert resp.status_code == 401
    portal_mock.assert_not_called()


async def test_webhook_handles_real_stripe_event_object(
    client, test_user, db_session
):
    """Regression: production receives a `stripe.Event` (StripeObject), not a dict.

    Before this test, every webhook test mocked `construct_event` with a
    bare ``dict`` and `.get()` worked. Production receives a real
    `stripe.Event` from the SDK — `event.get("id", "")` raises
    ``AttributeError: get`` because StripeObject (Stripe SDK v14+) is no
    longer a dict subclass. Every live webhook 500'd silently while every
    test passed; the gap is closed by exercising `stripe.Event.construct_from`
    on the same code path the SDK uses internally.

    The handler must use bracket access (``event["id"]``), not `.get`.
    """
    import stripe

    sub = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    sub.stripe_customer_id = "cus_real_event_obj"
    await db_session.flush()

    raw_event = {
        "id": "evt_real_object_001",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "object": "checkout.session",
                "id": "cs_test_real",
                "client_reference_id": test_user.id,
                "customer": "cus_real_event_obj",
                "subscription": "sub_real_event_obj",
                "amount_total": 4900,
                "currency": "usd",
                "metadata": {"user_id": test_user.id, "plan": "pro"},
            }
        },
    }
    # Build the same shape the Stripe SDK returns from construct_event —
    # NOT a plain dict. construct_from is the SDK's internal hydrator.
    stripe_event = stripe.Event.construct_from(raw_event, "sk_test_dummy")

    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        return_value=stripe_event,
    ):
        resp = await client.post(
            "/api/v1/payments/webhook",
            content=json.dumps(raw_event).encode(),
            headers={"stripe-signature": "t=1,v1=fake"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["received"] is True
    assert body["event_type"] == "checkout.session.completed"

    sub_after = (
        await db_session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    assert sub_after.plan == "pro"
    assert sub_after.stripe_subscription_id == "sub_real_event_obj"


async def test_webhook_handles_unhandled_event_type_with_real_object(
    client, test_user, db_session
):
    """Regression: the silent-ignore branch must also work with a real Event.

    Before the bracket-access fix, even unhandled event types (`invoice.paid`,
    `invoice.finalized`, `invoice_payment.paid`) 500'd because the crash was
    on `event.get("id", "")` BEFORE the dispatcher branch. This test asserts
    that an unhandled event type now returns 200 and writes an idempotency
    row, matching production behavior under the live SDK.
    """
    import stripe

    raw_event = {
        "id": "evt_real_object_unhandled_001",
        "object": "event",
        "type": "invoice.finalized",
        "data": {
            "object": {
                "object": "invoice",
                "id": "in_test_unhandled",
                "customer": "cus_test_unhandled",
            }
        },
    }
    stripe_event = stripe.Event.construct_from(raw_event, "sk_test_dummy")

    with patch(
        "app.services.payment_service.stripe.Webhook.construct_event",
        return_value=stripe_event,
    ):
        resp = await client.post(
            "/api/v1/payments/webhook",
            content=json.dumps(raw_event).encode(),
            headers={"stripe-signature": "t=1,v1=fake"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["event_type"] == "invoice.finalized"

    # Idempotency row must persist even for unhandled types.
    row = (
        await db_session.execute(
            select(StripeEvent).where(StripeEvent.id == "evt_real_object_unhandled_001")
        )
    ).scalar_one_or_none()
    assert row is not None
    assert row.event_type == "invoice.finalized"


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
