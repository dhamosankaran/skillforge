"""Regression guards for slice 6.15 / B-102 — `DailyStatus` relocation
from `app.schemas.study` to `app.schemas.daily_status`. Per spec §10.1.

D-1 locks the back-compat re-export in `schemas.study` so old import
paths continue to resolve until spec 16 retires `schemas/study.py`.
"""


def test_daily_status_resolves_at_new_home() -> None:
    from app.schemas.daily_status import DailyStatus

    assert DailyStatus.__name__ == "DailyStatus"


def test_daily_status_back_compat_reexport_from_study() -> None:
    """D-1: `schemas.study` keeps a re-export until spec 16."""
    from app.schemas.daily_status import DailyStatus as canonical
    from app.schemas.study import DailyStatus as via_reexport

    assert via_reexport is canonical


def test_daily_status_quiz_item_import_flipped() -> None:
    """T7.1: `schemas.quiz_item` imports from the new home, not `schemas.study`."""
    import app.schemas.quiz_item as quiz_item_schemas

    assert quiz_item_schemas.DailyStatus.__module__ == "app.schemas.daily_status"


def test_daily_status_field_shape() -> None:
    from app.schemas.daily_status import DailyStatus

    assert set(DailyStatus.model_fields.keys()) == {
        "cards_consumed",
        "cards_limit",
        "can_review",
        "resets_at",
    }
