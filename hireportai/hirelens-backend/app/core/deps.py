"""FastAPI dependencies for authentication and authorization."""
from typing import Optional

import sentry_sdk
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def verify_content_length(content_length: int = Header(default=0)) -> None:
    """Verify request size is within the configured limit."""
    settings = get_settings()
    if content_length > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that extracts and validates the JWT, returning the User.

    Raises 401 if token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    sentry_sdk.set_user({"id": user.id, "email": user.email})
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401 for anonymous requests."""
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that restricts access to admin users only.

    Raises 403 if the authenticated user's role is not 'admin'.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


def require_plan(minimum: str):
    """Dependency factory that checks the user's subscription plan.

    Usage: Depends(require_plan("pro")) or Depends(require_plan("enterprise"))
    """
    plan_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
    min_level = plan_hierarchy.get(minimum, 0)

    async def _check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        # Lazy import to avoid circular dependency
        from app.models.subscription import Subscription

        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        sub = result.scalar_one_or_none()

        user_plan = sub.plan if sub else "free"
        user_level = plan_hierarchy.get(user_plan, 0)

        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires the {minimum} plan or higher. "
                       f"Your current plan: {user_plan}.",
            )
        return user

    return _check
