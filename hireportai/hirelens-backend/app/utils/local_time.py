"""Local-time arithmetic helpers shared across services.

Lifted from `study_service` + `quiz_item_study_service` in slice 6.15
/ B-102 (per spec §12 D-2 + D-3) so both services consume one
canonical implementation. Pure date/tz arithmetic — no DB or service
dependency.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


def next_local_midnight(now_utc: datetime, tz: ZoneInfo) -> datetime:
    """Next user-local midnight as a tz-aware datetime in the user's tz.

    Used by daily-review wall reset (study_service / quiz_item_study_service)
    to compute when the per-day card-review counter resets.
    """
    local_now = now_utc.astimezone(tz)
    tomorrow = (local_now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, time(0, 0, 0), tzinfo=tz)
