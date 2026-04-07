"""Stripe integration service — checkout, webhooks, billing portal."""
from datetime import datetime, timezone
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User


def _init_stripe():
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key


async def create_checkout_session(user: User, plan: str, db: AsyncSession) -> str:
    """Create a Stripe Checkout session and return the URL.

    If the user already has a stripe_customer_id, reuse it.
    """
    _init_stripe()
    settings = get_settings()

    price_map = {
        "pro": settings.stripe_pro_price_id,
        "enterprise": settings.stripe_enterprise_price_id,
    }
    price_id = price_map.get(plan)
    if not price_id:
        raise ValueError(f"Invalid plan: {plan}. Must be 'pro' or 'enterprise'.")

    # Get or create Stripe customer
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    customer_id = sub.stripe_customer_id if sub else None

    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": user.id},
        )
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

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/payment/cancel",
        metadata={"user_id": user.id, "plan": plan},
    )
    return session.url


async def create_billing_portal_session(user: User, db: AsyncSession) -> str:
    """Create a Stripe Customer Portal session URL."""
    _init_stripe()
    settings = get_settings()

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    if not sub or not sub.stripe_customer_id:
        raise ValueError("No Stripe customer found for this user.")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{settings.frontend_url}/pricing",
    )
    return session.url


async def handle_webhook_event(
    payload: bytes,
    sig_header: str,
    db: AsyncSession,
) -> dict:
    """Process a Stripe webhook event.

    Handles: checkout.session.completed, invoice.payment_succeeded,
    invoice.payment_failed, customer.subscription.deleted.
    """
    _init_stripe()
    settings = get_settings()

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type == "invoice.payment_succeeded":
        await _handle_payment_succeeded(data, db)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)

    return {"event_type": event_type, "status": "processed"}


async def cancel_subscription(user: User, db: AsyncSession) -> dict:
    """Cancel the user's Stripe subscription at period end."""
    _init_stripe()

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    if not sub or not sub.stripe_subscription_id:
        raise ValueError("No active subscription found.")

    stripe.Subscription.modify(
        sub.stripe_subscription_id,
        cancel_at_period_end=True,
    )

    sub.status = "canceled"
    return {
        "message": "Subscription will be canceled at end of billing period",
        "current_period_end": str(sub.current_period_end),
    }


# --- Internal webhook handlers ---

async def _handle_checkout_completed(data: dict, db: AsyncSession):
    """Activate subscription after successful checkout."""
    customer_id = data.get("customer")
    stripe_sub_id = data.get("subscription")
    plan = data.get("metadata", {}).get("plan", "pro")

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.plan = plan
        sub.status = "active"
        sub.stripe_subscription_id = stripe_sub_id

        # Fetch subscription details for period_end
        if stripe_sub_id:
            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
            sub.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=timezone.utc
            )


async def _handle_payment_succeeded(data: dict, db: AsyncSession):
    """Record payment and extend subscription period."""
    customer_id = data.get("customer")
    payment_intent_id = data.get("payment_intent")
    amount = data.get("amount_paid", 0)
    currency = data.get("currency", "usd")

    # Find subscription by customer
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    # Record payment (skip if already recorded — idempotency)
    if payment_intent_id:
        existing = await db.execute(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
        )
        if existing.scalar_one_or_none() is None:
            payment = Payment(
                user_id=sub.user_id,
                stripe_payment_intent_id=payment_intent_id,
                amount=amount,
                currency=currency,
                status="succeeded",
            )
            db.add(payment)

    # Update period_end from the subscription
    stripe_sub_id = data.get("subscription")
    if stripe_sub_id:
        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
        sub.current_period_end = datetime.fromtimestamp(
            stripe_sub.current_period_end, tz=timezone.utc
        )
        sub.status = "active"


async def _handle_payment_failed(data: dict, db: AsyncSession):
    """Mark subscription as past_due when payment fails."""
    customer_id = data.get("customer")
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "past_due"


async def _handle_subscription_deleted(data: dict, db: AsyncSession):
    """Revert to free plan when subscription is deleted."""
    customer_id = data.get("customer")
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.plan = "free"
        sub.status = "canceled"
        sub.stripe_subscription_id = None
        sub.current_period_end = None
