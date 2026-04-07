"""Authentication endpoints — Google OAuth + JWT."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_google_token,
)
from app.db.session import get_db
from app.models.user import User
from app.services.user_service import get_or_create_user

router = APIRouter()


# --- Request / response schemas ---

class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token from the frontend


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Endpoints ---

@router.post("/auth/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Validate a Google ID token, upsert user, and return JWT pair."""
    google_info = await verify_google_token(body.credential)
    if google_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    user = await get_or_create_user(
        google_id=google_info["google_id"],
        email=google_info["email"],
        name=google_info["name"],
        avatar_url=google_info.get("avatar_url"),
        db=db,
    )

    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
        },
    )


@router.post("/auth/refresh", response_model=RefreshResponse)
async def refresh_access_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    token_data = {"sub": payload["sub"], "email": payload.get("email", "")}
    return RefreshResponse(access_token=create_access_token(token_data))


@router.post("/auth/logout", status_code=200)
async def logout(user: User = Depends(get_current_user)):
    """Logout endpoint (stateless — client should discard tokens)."""
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the current authenticated user's profile and subscription."""
    from app.models.subscription import Subscription
    from sqlalchemy import select

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "created_at": str(user.created_at),
        "subscription": {
            "plan": sub.plan if sub else "free",
            "status": sub.status if sub else "active",
            "current_period_end": str(sub.current_period_end) if sub and sub.current_period_end else None,
        },
    }
