"""User CRUD service."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.subscription import Subscription


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
