"""Payments route — Stripe Checkout + webhook (Spec #11) + paywall
dismissal (Spec #42).

Mounted at ``/api/v1/payments`` from ``app/main.py``.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import paywall_service
from app.services.geo_pricing_service import get_pricing
from app.services.usage_service import get_analyze_usage
from app.services.payment_service import (
    InvalidSignatureError,
    NotProSubscriberError,
    PaymentError,
    UserNotFoundError,
    create_billing_portal_session,
    create_checkout_session,
    handle_webhook,
)

router = APIRouter()


class CheckoutRequest(BaseModel):
    currency: Optional[str] = None


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class PricingResponse(BaseModel):
    currency: str
    price: int
    price_display: str
    stripe_price_id: str


def _client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For (production) or request.client."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


@router.get("/payments/pricing", response_model=PricingResponse)
async def get_pricing_endpoint(request: Request) -> PricingResponse:
    """Return geo-based pricing for the calling client's IP."""
    ip = _client_ip(request)
    pricing = get_pricing(ip)
    return PricingResponse(**pricing)


@router.post("/payments/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: Request,
    body: Optional[CheckoutRequest] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session for the Pro plan and return the URL."""
    currency = body.currency if body else None
    # Server-side geo fallback: if the client didn't tell us which currency
    # to bill in, resolve it from the caller's IP. Keeps Indian users from
    # being mis-priced when a future caller forgets to pass the currency.
    if not currency:
        currency = get_pricing(_client_ip(request))["currency"]
    try:
        url = await create_checkout_session(user.id, db, currency=currency)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except PaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        )
    return CheckoutResponse(url=url)


@router.post("/payments/portal", response_model=PortalResponse)
async def create_portal(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalResponse:
    """Create a Stripe hosted billing portal session for the Pro user."""
    try:
        url = await create_billing_portal_session(user.id, db)
    except NotProSubscriberError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing portal is only available to Pro subscribers",
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except PaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        )
    return PortalResponse(url=url)


class PaywallDismissRequest(BaseModel):
    trigger: str = Field(..., min_length=1, max_length=64)
    action_count_at_dismissal: Optional[int] = Field(default=None, ge=0)


class PaywallDismissResponse(BaseModel):
    logged: bool
    dismissal_id: str
    dismissals_in_window: int


class ShouldShowPaywallResponse(BaseModel):
    show: bool
    attempts_until_next: int


class UsageResponse(BaseModel):
    plan: str
    scans_used: int
    scans_remaining: int
    max_scans: int
    is_admin: bool


@router.post("/payments/paywall-dismiss", response_model=PaywallDismissResponse)
async def paywall_dismiss(
    body: PaywallDismissRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaywallDismissResponse:
    """Log a paywall dismissal (spec #42).

    Idempotent within a 60-second window per (user_id, trigger) per LD-8.
    Fires ``paywall_dismissed`` PostHog event on successful log. Win-back
    is deferred — this endpoint does not send email.
    """
    result = await paywall_service.record_dismissal(
        db,
        user_id=user.id,
        trigger=body.trigger,
        action_count=body.action_count_at_dismissal,
    )

    if result["logged"]:
        analytics_track(
            user_id=user.id,
            event="paywall_dismissed",
            properties={
                "trigger": body.trigger,
                "dismissals_in_window": result["dismissals_in_window"],
                "action_count_at_dismissal": body.action_count_at_dismissal,
            },
        )

    return PaywallDismissResponse(**result)


@router.get(
    "/payments/should-show-paywall",
    response_model=ShouldShowPaywallResponse,
)
async def should_show_paywall(
    trigger: str = Query(..., min_length=1, max_length=64),
    attempts_since_dismiss: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShouldShowPaywallResponse:
    """Decide modal-vs-inline-nudge for the given (user, trigger).

    Pro / Enterprise / admin always receive ``show=false``. Free users
    with a prior dismissal receive ``show=false`` until their frontend-
    tracked ``attempts_since_dismiss`` reaches 3 (LD-3 grace).
    """
    result = await paywall_service.should_show_paywall(
        db,
        user=user,
        trigger=trigger,
        attempts_since_dismiss=attempts_since_dismiss,
    )
    return ShouldShowPaywallResponse(**result)


@router.get("/payments/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Lifetime `analyze` usage snapshot for the caller (spec #56 §4.3).

    FE hydrates `UsageContext` from this endpoint on mount and after each
    successful scan. `-1` sentinel on `scans_remaining` / `max_scans`
    signals unlimited (Pro / Enterprise / admin bypass). `is_admin` is an
    orthogonal flag so the FE can render admin UX without conflating role
    with plan.
    """
    result = await get_analyze_usage(user.id, db)
    return UsageResponse(**result)


@router.post("/payments/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stripe webhook receiver.

    No auth — Stripe signs the payload and we verify the signature
    inside ``handle_webhook``. Raw request body is required: never wrap
    this endpoint's input in a Pydantic model.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        return await handle_webhook(payload, signature, db)
    except InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature",
        )
