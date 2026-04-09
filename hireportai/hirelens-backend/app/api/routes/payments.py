"""Payments route — Stripe Checkout + webhook (Spec #11).

Mounted at ``/api/v1/payments`` from ``app/main.py``.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.payment_service import (
    InvalidSignatureError,
    PaymentError,
    UserNotFoundError,
    create_checkout_session,
    handle_webhook,
)

router = APIRouter()


class CheckoutResponse(BaseModel):
    url: str


@router.post("/payments/checkout", response_model=CheckoutResponse)
async def create_checkout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session for the Pro plan and return the URL."""
    try:
        url = await create_checkout_session(user.id, db)
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
