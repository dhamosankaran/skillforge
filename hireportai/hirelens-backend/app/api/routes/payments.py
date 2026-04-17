"""Payments route — Stripe Checkout + webhook (Spec #11).

Mounted at ``/api/v1/payments`` from ``app/main.py``.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.geo_pricing_service import get_pricing
from app.services.payment_service import (
    InvalidSignatureError,
    PaymentError,
    UserNotFoundError,
    create_checkout_session,
    handle_webhook,
)

router = APIRouter()


class CheckoutRequest(BaseModel):
    currency: Optional[str] = None


class CheckoutResponse(BaseModel):
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
