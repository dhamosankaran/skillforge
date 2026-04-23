"""User CRUD service."""
from typing import FrozenSet, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.subscription import Subscription


# Role reconciliation action names (spec #54 §AC-6, §AC-7).
_ACTION_PROMOTED = "promoted"
_ACTION_DEMOTED = "demoted"
_ACTION_UNCHANGED = "unchanged"


def reconcile_admin_role(
    user: User, admin_emails_set: FrozenSet[str]
) -> Tuple[str, str, str]:
    """Reconcile ``user.role`` against the admin whitelist.

    Pure mutation on the passed-in User; caller owns commit, audit, and
    analytics. Returns ``(action, prior_role, new_role)`` where
    ``action`` is one of ``"promoted"``, ``"demoted"``, or
    ``"unchanged"``. Match on ``user.email.lower()`` so the whitelist is
    case-insensitive (spec #54 §AC-4).
    """
    prior_role = user.role
    desired_role = "admin" if user.email.lower() in admin_emails_set else "user"

    if prior_role == desired_role:
        return _ACTION_UNCHANGED, prior_role, desired_role

    user.role = desired_role
    action = _ACTION_PROMOTED if desired_role == "admin" else _ACTION_DEMOTED
    return action, prior_role, desired_role


async def get_or_create_user(
    google_id: str,
    email: str,
    name: str,
    avatar_url: Optional[str],
    db: AsyncSession,
) -> tuple[User, bool]:
    """Find an existing user by google_id or create a new one.

    Also ensures a default free subscription exists for new users.

    Returns a tuple of ``(user, is_new)`` — ``is_new`` is True when the
    user was just created in this call.
    """
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is not None:
        # Update mutable fields on login
        user.name = name
        if avatar_url:
            user.avatar_url = avatar_url
        return user, False

    # Create new user
    user = User(google_id=google_id, email=email, name=name, avatar_url=avatar_url)
    db.add(user)
    await db.flush()  # Assigns user.id

    # Create default free subscription
    sub = Subscription(user_id=user.id, plan="free", status="active")
    db.add(sub)

    return user, True


async def get_user_by_id(user_id: str, db: AsyncSession) -> Optional[User]:
    """Fetch a user by primary key."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
