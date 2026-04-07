"""Billing endpoints — Stripe Checkout, webhooks, subscription management."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.stripe_service import (
    cancel_subscription,
    create_billing_portal_session,
    create_checkout_session,
    handle_webhook_event,
)
from app.services.usage_service import get_usage_summary

router = APIRouter()


class CreateCheckoutRequest(BaseModel):
    plan: str  # "pro" or "enterprise"


class CheckoutResponse(BaseModel):
    url: str


@router.post("/billing/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout(
    body: CreateCheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session and return the redirect URL."""
    try:
        url = await create_checkout_session(user, body.plan, db)
        return CheckoutResponse(url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Stripe webhook events.

    Stripe signs each event — we verify the signature before processing.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        result = await handle_webhook_event(payload, sig_header, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/billing/subscription")
async def get_subscription_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current subscription plan, status, and usage summary."""
    from sqlalchemy import select
    from app.models.subscription import Subscription

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    usage = await get_usage_summary(user.id, db)

    return {
        "plan": sub.plan if sub else "free",
        "status": sub.status if sub else "active",
        "current_period_end": str(sub.current_period_end) if sub and sub.current_period_end else None,
        "stripe_customer_id": sub.stripe_customer_id if sub else None,
        "usage": usage,
    }


@router.post("/billing/cancel")
async def cancel_sub(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current subscription at end of billing period."""
    try:
        result = await cancel_subscription(user, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/billing/portal")
async def billing_portal(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a URL to the Stripe Customer Portal for self-service billing management."""
    try:
        url = await create_billing_portal_session(user, db)
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
