"""Authentication endpoints — Google OAuth + JWT."""
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_google_token,
)
from app.db.session import get_db
from app.models.registration_log import RegistrationLog
from app.models.user import User
from app.services.user_service import get_or_create_user

_MAX_REGISTRATIONS_PER_IP = 2
_REGISTRATION_WINDOW_DAYS = 30

router = APIRouter()


def _user_dict(user: User) -> dict:
    """Serialise a User row into the standard JSON shape."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "persona": user.persona,
        "onboarding_completed": user.onboarding_completed,
        "interview_target_company": user.interview_target_company,
        "interview_target_date": (
            user.interview_target_date.isoformat()
            if user.interview_target_date
            else None
        ),
    }


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


# --- Helpers ---

def _client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For (production) or request.client."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


# --- Endpoints ---

@router.post("/auth/google", response_model=TokenResponse)
@limiter.limit("10/minute")
async def google_auth(request: Request, body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Validate a Google ID token, upsert user, and return JWT pair."""
    google_info = await verify_google_token(body.credential)
    if google_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    # Check if user already exists (existing users are never blocked)
    existing = (
        await db.execute(
            select(User).where(User.google_id == google_info["google_id"])
        )
    ).scalar_one_or_none()

    ip = _client_ip(request)

    # IP-based registration limit — only when creating a NEW account
    if existing is None:
        cutoff = datetime.now() - timedelta(days=_REGISTRATION_WINDOW_DAYS)
        result = await db.execute(
            select(func.count())
            .select_from(RegistrationLog)
            .where(
                RegistrationLog.ip_address == ip,
                RegistrationLog.created_at >= cutoff,
            )
        )
        recent_count = result.scalar_one()

        if recent_count >= _MAX_REGISTRATIONS_PER_IP:
            ip_hash = hashlib.sha256(ip.encode()).hexdigest()
            analytics_track(
                user_id="system",
                event="registration_blocked",
                properties={
                    "ip_hash": ip_hash,
                    "existing_accounts": recent_count,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": "Account limit reached for this network. Contact support if this is an error.",
                    "code": "IP_LIMIT_REACHED",
                },
            )

    user, is_new = await get_or_create_user(
        google_id=google_info["google_id"],
        email=google_info["email"],
        name=google_info["name"],
        avatar_url=google_info.get("avatar_url"),
        db=db,
    )

    if is_new:
        db.add(RegistrationLog(
            user_id=user.id,
            ip_address=ip,
            google_email=google_info["email"],
        ))

    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_dict(user),
    )


@router.post("/auth/refresh", response_model=RefreshResponse)
@limiter.limit("10/minute")
async def refresh_access_token(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("10/minute")
async def logout(request: Request, user: User = Depends(get_current_user)):
    """Logout endpoint (stateless — client should discard tokens)."""
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
@limiter.limit("10/minute")
async def get_me(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the current authenticated user's profile and subscription."""
    from app.models.subscription import Subscription
    from sqlalchemy import select

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    data = _user_dict(user)
    data["created_at"] = str(user.created_at)
    data["subscription"] = {
        "plan": sub.plan if sub else "free",
        "status": sub.status if sub else "active",
        "current_period_end": str(sub.current_period_end) if sub and sub.current_period_end else None,
    }
    return data
