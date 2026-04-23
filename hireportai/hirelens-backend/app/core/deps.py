"""FastAPI dependencies for authentication and authorization."""
import logging
import uuid
from typing import Optional

import sentry_sdk
from fastapi import BackgroundTasks, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

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


async def audit_admin_request(
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Audit log for every admin-scoped HTTP request (spec #38 E-018a).

    Chains `require_admin` so the 401/403 gate runs first (unauth and
    non-admin requests never reach the audit path by design — we audit
    authorized admin activity, not rejected attempts).

    The audit row is scheduled via `BackgroundTasks` so the route handler
    returns the response first; the write then flushes on the same
    request-scoped session and commits as part of the request transaction
    via `get_db`'s teardown. Consequence: if the handler raises, the
    audit row is rolled back with it, keeping audit rows consistent with
    committed state.

    Side-fires `admin_analytics_viewed` when the request path starts with
    `/api/v1/admin/analytics` so every analytics endpoint is observed
    without each one having to remember to call `track()`. In Slice 1
    the analytics routes do not exist yet, so this emitter is dormant;
    Slice 2 (E-018b) lands the first `/admin/analytics/*` route and the
    event starts firing for real.
    """
    path = request.url.path
    method = request.method
    ip = request.client.host if request.client else "unknown"
    query = dict(request.query_params) if request.query_params else {}
    admin_id = user.id

    background_tasks.add_task(
        _write_admin_audit_log, db, admin_id, path, method, query, ip
    )

    if path.startswith("/api/v1/admin/analytics"):
        background_tasks.add_task(_fire_admin_analytics_viewed, admin_id, path)

    return user


async def _write_admin_audit_log(
    db: AsyncSession,
    admin_id: str,
    route: str,
    method: str,
    query_params: dict,
    ip_address: str,
) -> None:
    """Persist a row to `admin_audit_log` on the request-scoped session.

    Flushes only — `get_db` commits on request teardown. Never raises;
    audit is best-effort and must not break the user-facing response.
    """
    # Local import avoids pulling the model graph when deps.py is imported
    # in contexts that don't exercise the admin router.
    from app.models.admin_audit_log import AdminAuditLog

    try:
        entry = AdminAuditLog(
            id=str(uuid.uuid4()),
            admin_id=admin_id,
            route=route,
            method=method,
            query_params=query_params,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin audit log write failed: %s", exc)


def _fire_admin_analytics_viewed(admin_id: str, path: str) -> None:
    """Emit `admin_analytics_viewed` PostHog event. Silent on failure."""
    from app.core.analytics import track

    track(
        admin_id,
        "admin_analytics_viewed",
        {"admin_id": admin_id, "internal": True, "path": path},
    )


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
