"""Pydantic v2 schema for the free-tier daily-review wall (spec #63 / B-059).

Lifted from `app.schemas.study` in slice 6.15 / B-102 to clear the
spec #02 §6.2 weak-coupling flag (`schemas.quiz_item` re-importing from
`schemas.study`). Spec 16 retires `schemas.study` itself; until then,
that module keeps a back-compat re-export per slice 6.15 §12 D-1.
"""
from datetime import datetime

from pydantic import BaseModel


class DailyStatus(BaseModel):
    """Free-tier daily-review wall state (spec #63 / B-059).

    Read-side mirror of the same Redis counter `_check_daily_wall` writes
    on submit. Side-effect-free — the queue handler never INCRs.

    `cards_limit == -1` is the unlimited sentinel for Pro / Enterprise /
    admin (matches the `-1` convention from `usage_service` /
    `UsageContext`). `can_review` is the gate `DailyReview.tsx` reads to
    decide whether to render the pre-flight upsell.
    """

    cards_consumed: int
    cards_limit: int
    can_review: bool
    resets_at: datetime
