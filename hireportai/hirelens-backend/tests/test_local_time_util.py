"""Regression guards for slice 6.15 / B-102 — `next_local_midnight`
extraction from `study_service` + `quiz_item_study_service` into
`app.utils.local_time`. Per spec §10.1.

D-2 + D-3 lock: helper lives at `app.utils.local_time` (new file) with
the leading-underscore stripped from the public name.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def test_next_local_midnight_utc() -> None:
    from app.utils.local_time import next_local_midnight

    now = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
    result = next_local_midnight(now, ZoneInfo("UTC"))

    assert result == datetime(2026, 5, 3, 0, 0, 0, tzinfo=ZoneInfo("UTC"))


def test_next_local_midnight_la_crosses_local_day_only() -> None:
    """11pm UTC on 2026-05-02 is 4pm Pacific → next local midnight is
    2026-05-03 00:00 Pacific (still on PDT in May → UTC-07:00)."""
    from app.utils.local_time import next_local_midnight

    now = datetime(2026, 5, 2, 23, 0, 0, tzinfo=timezone.utc)
    la = ZoneInfo("America/Los_Angeles")
    result = next_local_midnight(now, la)

    assert result == datetime(2026, 5, 3, 0, 0, 0, tzinfo=la)


def test_both_services_import_shared_helper() -> None:
    """T7.2 / AC-5: both services consume the public symbol from the
    shared util; neither defines the legacy `_next_local_midnight`
    locally anymore."""
    from app.services import quiz_item_study_service, study_service
    from app.utils.local_time import next_local_midnight

    assert study_service.next_local_midnight is next_local_midnight
    assert quiz_item_study_service.next_local_midnight is next_local_midnight
    assert not hasattr(study_service, "_next_local_midnight")
    assert not hasattr(quiz_item_study_service, "_next_local_midnight")
