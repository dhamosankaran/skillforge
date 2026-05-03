"""Payment service — thin wrapper around Stripe for Spec #11.

Exposes two high-level operations for the /api/v1/payments routes:

- ``create_checkout_session(user_id, db)`` — builds a Stripe Checkout
  Session for the Pro plan and returns its URL.
- ``handle_webhook(payload, signature, db)`` — verifies the Stripe
  signature, then processes ``checkout.session.completed`` and
  ``customer.subscription.deleted`` events, flipping the user's
  subscription plan accordingly.

Billing state (plan, stripe_customer_id, stripe_subscription_id) lives on
the ``Subscription`` model in this codebase — the architecture decision
was made before Spec #11 and is respected here rather than duplicating
those columns onto ``User``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.config import get_settings
from app.models.stripe_event import StripeEvent
from app.models.subscription import Subscription
from app.models.user import User
from app.services import home_state_service

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Base class for payment-layer errors surfaced to the route layer."""


class InvalidSignatureError(PaymentError):
    """Stripe webhook signature did not verify."""


class UserNotFoundError(PaymentError):
    """No user matched the provided ID."""


class NotProSubscriberError(PaymentError):
    """Billing portal can only be opened for an active Pro subscriber.

    Raised when a non-Pro user (or a user without a Stripe customer id)
    attempts to open a portal session. The route layer maps this to 403.
    """


class AlreadyProError(PaymentError):
    """Caller is already an active Pro subscriber on Stripe.

    Raised by ``create_checkout_session`` when the user's Subscription
    row has ``plan == "pro"``, ``status == "active"``, and a
    ``stripe_subscription_id`` set — i.e., a real Stripe-backed Pro
    subscription. Without this guard, re-clicking Upgrade creates a
    second active subscription on the same Stripe Customer (Stripe
    permits multi-sub by default). Admin-manual flips that lack a
    ``stripe_subscription_id`` are intentionally allowed through so
    the admin can complete a real checkout. Mapped to HTTP 409.
    """


def _init_stripe() -> None:
    stripe.api_key = get_settings().stripe_secret_key


def _field(obj, key, default=None):
    """Read a field from a Stripe ``StripeObject`` or a plain dict.

    Stripe SDK v14+ returns ``StripeObject`` from ``construct_event`` —
    it supports bracket access and ``__contains__`` but NOT ``.get(...)``.
    Test fixtures pass plain ``dict`` payloads. This shim unifies both
    so handler code can read optional fields without branching on type.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ── Checkout ────────────────────────────────────────────────────────────────


async def create_checkout_session(
    user_id: str,
    db: AsyncSession,
    *,
    currency: str | None = None,
) -> str:
    """Create a Stripe Checkout Session for the Pro plan.

    Returns the hosted Checkout URL. When *currency* is ``"inr"``, the
    INR Stripe price is used; otherwise the default USD price applies.

    Raises:
        UserNotFoundError — user_id does not exist.
        PaymentError — Stripe pro price ID is not configured, or the
                       Stripe API call fails.
    """
    _init_stripe()
    settings = get_settings()

    if currency == "inr" and settings.stripe_pro_price_id_inr:
        price_id = settings.stripe_pro_price_id_inr
    else:
        price_id = settings.stripe_pro_price_id

    if not price_id:
        raise PaymentError("Stripe pro price ID is not configured")

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise UserNotFoundError(user_id)

    sub = (
        await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one_or_none()

    if (
        sub is not None
        and sub.plan == "pro"
        and sub.status == "active"
        and sub.stripe_subscription_id
    ):
        raise AlreadyProError(user.id)

    customer_id = sub.stripe_customer_id if sub else None
    if not customer_id:
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": user.id},
            )
        except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
            logger.exception("Stripe customer creation failed")
            raise PaymentError(f"Stripe error: {exc}") from exc

        customer_id = customer.id
        if sub:
            sub.stripe_customer_id = customer_id
        else:
            sub = Subscription(
                user_id=user.id,
                plan="free",
                status="active",
                stripe_customer_id=customer_id,
            )
            db.add(sub)
        await db.flush()

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=(
                f"{settings.frontend_url}/pricing?upgrade=success"
                "&session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{settings.frontend_url}/pricing?upgrade=cancel",
            client_reference_id=user.id,
            metadata={"user_id": user.id, "plan": "pro"},
        )
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        logger.exception("Stripe checkout session creation failed")
        raise PaymentError(f"Stripe error: {exc}") from exc

    analytics_track(
        user_id=user.id,
        event="checkout_started",
        properties={"price_id": price_id, "plan": "pro"},
    )
    return session.url


# ── Billing portal ──────────────────────────────────────────────────────────


async def create_billing_portal_session(
    user_id: str,
    db: AsyncSession,
) -> str:
    """Create a Stripe hosted billing portal session for a Pro user.

    Returns the portal URL. The portal lets the user cancel, update
    payment methods, and view invoice history on Stripe's hosted UI.
    Cancellation timing is Stripe's default (at period end).

    Raises:
        UserNotFoundError — user_id does not exist.
        NotProSubscriberError — user is not on the Pro plan, or has no
                                stripe_customer_id (never upgraded).
        PaymentError — Stripe API call failed.
    """
    _init_stripe()
    settings = get_settings()

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise UserNotFoundError(user_id)

    sub = (
        await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one_or_none()

    if sub is None or sub.plan != "pro" or not sub.stripe_customer_id:
        raise NotProSubscriberError(user.id)

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{settings.frontend_url}/profile",
        )
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        logger.exception("Stripe billing portal session creation failed")
        raise PaymentError(f"Stripe error: {exc}") from exc

    return session.url


# ── Webhook ─────────────────────────────────────────────────────────────────


async def handle_webhook(
    payload: bytes,
    signature: str,
    db: AsyncSession,
) -> dict:
    """Verify a Stripe webhook and process supported events.

    Supported events:
    - ``checkout.session.completed`` → flip plan to ``pro``, store
      ``stripe_subscription_id``, fire ``payment_completed`` analytics.
    - ``customer.subscription.updated`` → reconcile
      ``cancel_at_period_end`` / ``current_period_end`` / ``status``
      (audit F-2 + F-4). Plan stays ``pro`` until the later
      ``customer.subscription.deleted`` event arrives.
    - ``customer.subscription.deleted`` → flip plan to ``free``,
      fire ``subscription_cancelled`` analytics.

    Every other event is acknowledged and ignored — Stripe retries on
    non-2xx responses, so silent-ignore is the correct behaviour.

    Raises:
        InvalidSignatureError — signature verification failed.
    """
    _init_stripe()
    secret = get_settings().stripe_webhook_secret

    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except stripe.error.SignatureVerificationError as exc:  # type: ignore[attr-defined]
        raise InvalidSignatureError(str(exc)) from exc
    except ValueError as exc:
        raise InvalidSignatureError(f"Malformed payload: {exc}") from exc

    # NOTE: `event` is a `stripe.Event` (StripeObject) — supports bracket
    # and attribute access, NOT `.get()`. SDK v14+ stopped subclassing dict.
    # Tests mock construct_event with a dict, so `.get()` worked there but
    # crashed in production with `AttributeError: get`.
    event_id = event["id"]
    event_type = event["type"]
    data = event["data"]["object"]

    # Idempotency: skip if this Stripe event was already processed.
    if event_id:
        existing = (
            await db.execute(
                select(StripeEvent).where(StripeEvent.id == event_id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("Duplicate Stripe event %s — skipping", event_id)
            return {"received": True, "event_type": event_type}
        db.add(
            StripeEvent(
                id=event_id,
                event_type=event_type,
                processed_at=datetime.now(tz=None),
            )
        )
        await db.flush()

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)
    else:
        logger.info("Ignoring unhandled Stripe event: %s", event_type)

    return {"received": True, "event_type": event_type}


async def _handle_checkout_completed(data, db: AsyncSession) -> None:
    """Activate Pro for the user referenced by the Checkout Session.

    ``data`` may be a Stripe ``StripeObject`` (production) or a plain
    ``dict`` (test fixtures). Use ``_field`` for safe optional reads.
    """
    metadata = _field(data, "metadata") or {}
    user_id = _field(data, "client_reference_id") or _field(metadata, "user_id")
    customer_id = _field(data, "customer")
    stripe_sub_id = _field(data, "subscription")

    sub = await _find_subscription(db, user_id=user_id, customer_id=customer_id)
    if sub is None:
        logger.warning(
            "checkout.session.completed: no subscription row for "
            "user_id=%s customer_id=%s",
            user_id,
            customer_id,
        )
        return

    sub.plan = "pro"
    sub.status = "active"
    if customer_id:
        sub.stripe_customer_id = customer_id
    if stripe_sub_id:
        sub.stripe_subscription_id = stripe_sub_id

    analytics_track(
        user_id=sub.user_id,
        event="payment_completed",
        properties={
            "plan": "pro",
            "amount_total": _field(data, "amount_total"),
            "currency": _field(data, "currency"),
        },
    )
    home_state_service.invalidate(sub.user_id)


async def _handle_subscription_updated(data, db: AsyncSession) -> None:
    """Reconcile Subscription row with a Stripe ``customer.subscription.updated``.

    Closes audit F-2 (event was silently ignored) + F-4 (``current_period_end``
    only got cleared, never set). The Stripe billing portal cancels by sending
    this event with ``cancel_at_period_end=true`` + the period-end timestamp,
    so the user retains Pro until the period actually ends and the FE can
    render "Pro plan — Cancels <date>".

    Field-level reconciliation only — ``plan`` stays ``pro`` until the
    later ``customer.subscription.deleted`` event flips it to free.
    """
    stripe_sub_id = _field(data, "id")
    customer_id = _field(data, "customer")

    sub = await _find_subscription_by_stripe_ids(
        db,
        stripe_sub_id=stripe_sub_id,
        customer_id=customer_id,
    )
    if sub is None:
        logger.warning(
            "customer.subscription.updated: no subscription row for "
            "stripe_sub_id=%s customer_id=%s",
            stripe_sub_id,
            customer_id,
        )
        return

    sub.cancel_at_period_end = bool(_field(data, "cancel_at_period_end") or False)

    period_end = _field(data, "current_period_end")
    if period_end is not None:
        sub.current_period_end = datetime.fromtimestamp(int(period_end), tz=timezone.utc).replace(tzinfo=None)

    stripe_status = _field(data, "status")
    if stripe_status:
        sub.status = stripe_status

    home_state_service.invalidate(sub.user_id)


async def _handle_subscription_deleted(data, db: AsyncSession) -> None:
    """Revert to Free when a Stripe subscription is fully cancelled."""
    customer_id = _field(data, "customer")
    sub = await _find_subscription(db, user_id=None, customer_id=customer_id)
    if sub is None:
        logger.warning(
            "customer.subscription.deleted: no subscription row for "
            "customer_id=%s",
            customer_id,
        )
        return

    sub.plan = "free"
    sub.status = "canceled"
    sub.stripe_subscription_id = None
    sub.current_period_end = None
    sub.cancel_at_period_end = False

    # Churn timestamp (spec #42 LD-5) — dormant until the deferred win-back
    # slice reads it. Written here because after-the-fact backfill is
    # impossible once live downgrades start happening.
    user = (
        await db.execute(select(User).where(User.id == sub.user_id))
    ).scalar_one_or_none()
    if user is not None:
        user.downgraded_at = datetime.now(tz=timezone.utc)

    analytics_track(
        user_id=sub.user_id,
        event="subscription_cancelled",
        properties={"plan": "free"},
    )
    home_state_service.invalidate(sub.user_id)


async def _find_subscription(
    db: AsyncSession,
    *,
    user_id: str | None,
    customer_id: str | None,
) -> Subscription | None:
    """Look up a Subscription by user_id first, then by stripe_customer_id."""
    if user_id:
        sub = (
            await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
        ).scalar_one_or_none()
        if sub is not None:
            return sub
    if customer_id:
        return (
            await db.execute(
                select(Subscription).where(
                    Subscription.stripe_customer_id == customer_id
                )
            )
        ).scalar_one_or_none()
    return None


async def _find_subscription_by_stripe_ids(
    db: AsyncSession,
    *,
    stripe_sub_id: str | None,
    customer_id: str | None,
) -> Subscription | None:
    """Look up a Subscription by stripe_subscription_id, then customer_id.

    ``customer.subscription.*`` events identify the subscription by its
    Stripe id rather than our user id, so the lookup order differs from
    ``_find_subscription``.
    """
    if stripe_sub_id:
        sub = (
            await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_sub_id
                )
            )
        ).scalar_one_or_none()
        if sub is not None:
            return sub
    if customer_id:
        return (
            await db.execute(
                select(Subscription).where(
                    Subscription.stripe_customer_id == customer_id
                )
            )
        ).scalar_one_or_none()
    return None
