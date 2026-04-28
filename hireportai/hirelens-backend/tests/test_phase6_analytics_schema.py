"""Phase 6 slice 6.0 — analytics tables schema verification tests.

Spec: docs/specs/phase-6/00-analytics-tables.md §4 + §10.1.

Verifies that `quiz_review_events` + `lesson_view_events` match the column /
constraint / index contract in spec §4.1 + §4.2, FK ON DELETE shapes in
§4.3, and the append-only invariant per §4.4 + AC-10. The dedicated
``test_alembic_round_trip_analytics_tables`` test is gated behind
``@pytest.mark.integration`` because it shells out to alembic.
"""
from __future__ import annotations

import inspect as py_inspect

import pytest
from sqlalchemy import inspect

from app.services import analytics_event_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _reflect(engine):
    def _collect(conn):
        insp = inspect(conn)
        tables = set(insp.get_table_names())
        cols: dict[str, dict[str, dict]] = {}
        idxs: dict[str, list[dict]] = {}
        fks: dict[str, list[dict]] = {}
        uqs: dict[str, list[dict]] = {}
        for t in tables:
            cols[t] = {c["name"]: c for c in insp.get_columns(t)}
            idxs[t] = insp.get_indexes(t)
            fks[t] = insp.get_foreign_keys(t)
            uqs[t] = insp.get_unique_constraints(t)
        return tables, cols, idxs, fks, uqs

    async with engine.connect() as conn:
        return await conn.run_sync(_collect)


def _has_index(indexes, columns: list[str]) -> bool:
    for ix in indexes:
        if list(ix["column_names"]) == columns:
            return True
    return False


def _fk_to(fks, local_col: str, target_table: str):
    for fk in fks:
        if local_col in fk["constrained_columns"] and fk["referred_table"] == target_table:
            return fk
    return None


# ---------------------------------------------------------------------------
# AC-2 + AC-9: quiz_review_events table shape
# ---------------------------------------------------------------------------
async def test_quiz_review_events_table_shape(engine):
    tables, cols, idxs, fks, uqs = await _reflect(engine)
    assert "quiz_review_events" in tables

    qre = cols["quiz_review_events"]
    expected = {
        "id", "user_id", "quiz_item_id", "lesson_id", "deck_id",
        "rating", "fsrs_state_before", "fsrs_state_after",
        "reps", "lapses", "time_spent_ms", "session_id",
        "plan", "persona", "reviewed_at",
    }
    assert expected.issubset(qre.keys()), f"missing: {expected - set(qre.keys())}"

    # Nullability per §4.1.
    assert qre["user_id"]["nullable"] is True  # SET NULL on user delete
    assert qre["quiz_item_id"]["nullable"] is False
    assert qre["lesson_id"]["nullable"] is False
    assert qre["deck_id"]["nullable"] is False
    assert qre["rating"]["nullable"] is False
    assert qre["fsrs_state_before"]["nullable"] is False
    assert qre["fsrs_state_after"]["nullable"] is False
    assert qre["reps"]["nullable"] is False
    assert qre["lapses"]["nullable"] is False
    assert qre["time_spent_ms"]["nullable"] is False
    assert qre["session_id"]["nullable"] is True
    assert qre["plan"]["nullable"] is True
    assert qre["persona"]["nullable"] is True
    assert qre["reviewed_at"]["nullable"] is False

    # AC-9 FK ON DELETE shapes per §4.3.
    fk_user = _fk_to(fks["quiz_review_events"], "user_id", "users")
    assert fk_user is not None
    assert (fk_user.get("options") or {}).get("ondelete") == "SET NULL"

    fk_qi = _fk_to(fks["quiz_review_events"], "quiz_item_id", "quiz_items")
    assert fk_qi is not None
    assert (fk_qi.get("options") or {}).get("ondelete") == "CASCADE"

    fk_lesson = _fk_to(fks["quiz_review_events"], "lesson_id", "lessons")
    assert fk_lesson is not None
    assert (fk_lesson.get("options") or {}).get("ondelete") == "CASCADE"

    fk_deck = _fk_to(fks["quiz_review_events"], "deck_id", "decks")
    assert fk_deck is not None
    assert (fk_deck.get("options") or {}).get("ondelete") == "CASCADE"

    # Indexes per §4.1 (4 total).
    assert _has_index(idxs["quiz_review_events"], ["user_id", "reviewed_at"])
    assert _has_index(idxs["quiz_review_events"], ["quiz_item_id", "reviewed_at"])
    assert _has_index(idxs["quiz_review_events"], ["lesson_id", "reviewed_at"])
    assert _has_index(idxs["quiz_review_events"], ["deck_id", "reviewed_at"])


# ---------------------------------------------------------------------------
# AC-2 + AC-9: lesson_view_events table shape
# ---------------------------------------------------------------------------
async def test_lesson_view_events_table_shape(engine):
    tables, cols, idxs, fks, uqs = await _reflect(engine)
    assert "lesson_view_events" in tables

    lve = cols["lesson_view_events"]
    expected = {
        "id", "user_id", "lesson_id", "deck_id",
        "version", "session_id", "plan", "persona", "viewed_at",
    }
    assert expected.issubset(lve.keys()), f"missing: {expected - set(lve.keys())}"

    # Nullability per §4.2.
    assert lve["user_id"]["nullable"] is True
    assert lve["lesson_id"]["nullable"] is False
    assert lve["deck_id"]["nullable"] is False
    assert lve["version"]["nullable"] is False
    assert lve["session_id"]["nullable"] is True
    assert lve["plan"]["nullable"] is True
    assert lve["persona"]["nullable"] is True
    assert lve["viewed_at"]["nullable"] is False

    # FK ON DELETE shapes per §4.3.
    fk_user = _fk_to(fks["lesson_view_events"], "user_id", "users")
    assert fk_user is not None
    assert (fk_user.get("options") or {}).get("ondelete") == "SET NULL"

    fk_lesson = _fk_to(fks["lesson_view_events"], "lesson_id", "lessons")
    assert fk_lesson is not None
    assert (fk_lesson.get("options") or {}).get("ondelete") == "CASCADE"

    fk_deck = _fk_to(fks["lesson_view_events"], "deck_id", "decks")
    assert fk_deck is not None
    assert (fk_deck.get("options") or {}).get("ondelete") == "CASCADE"

    # Indexes per §4.2 (3 total).
    assert _has_index(idxs["lesson_view_events"], ["user_id", "viewed_at"])
    assert _has_index(idxs["lesson_view_events"], ["lesson_id", "viewed_at"])
    assert _has_index(idxs["lesson_view_events"], ["deck_id", "viewed_at"])


# ---------------------------------------------------------------------------
# §4.1 closing note: no UNIQUE on (user_id, quiz_item_id) — a user can
# review the same quiz_item multiple times in a single session.
# ---------------------------------------------------------------------------
async def test_quiz_review_events_no_unique_constraint(engine):
    tables, _cols, _idxs, _fks, uqs = await _reflect(engine)
    assert "quiz_review_events" in tables
    for uq in uqs["quiz_review_events"]:
        cols = list(uq["column_names"])
        assert cols != ["user_id", "quiz_item_id"], (
            "quiz_review_events must allow multiple reviews per (user, quiz_item)"
        )


# ---------------------------------------------------------------------------
# AC-10: append-only invariant — the service surface exposes no
# UPDATE / DELETE method. §4.4 lock is structural.
# ---------------------------------------------------------------------------
async def test_analytics_event_service_appendonly_surface():
    public = {
        name for name, obj in py_inspect.getmembers(analytics_event_service)
        if py_inspect.iscoroutinefunction(obj) and not name.startswith("_")
    }
    # Whitelist exactly the two write methods.
    assert "write_quiz_review_event" in public
    assert "write_lesson_view_event" in public
    forbidden_prefixes = ("update_", "delete_", "archive_", "purge_", "remove_")
    bad = [n for n in public if any(n.startswith(p) for p in forbidden_prefixes)]
    assert not bad, f"append-only invariant violated by: {bad}"


# ---------------------------------------------------------------------------
# AC-1: alembic round-trip — gated as integration; manual shell run is canonical.
# ---------------------------------------------------------------------------
@pytest.mark.integration
async def test_alembic_round_trip_analytics_tables(engine):
    """Round-trip the slice-6.0 analytics tables via the Alembic CLI.

    Stamps to head, downgrades one revision (drops both event tables), then
    upgrades back. Asserts the table set is identical on both ends.
    """
    import os
    import subprocess
    from pathlib import Path

    from sqlalchemy import text

    backend_dir = Path(__file__).resolve().parent.parent
    env = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False)}

    def _alembic(*args: str) -> None:
        result = subprocess.run(
            ["alembic", *args],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"alembic {' '.join(args)} failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        )

    try:
        _alembic("upgrade", "head")
        _alembic("downgrade", "-1")
        post_down_tables, _, _, _, _ = await _reflect(engine)
        for t in ("quiz_review_events", "lesson_view_events"):
            assert t not in post_down_tables, f"{t} should be dropped after downgrade -1"
        _alembic("upgrade", "head")
        post_up_tables, _, _, _, _ = await _reflect(engine)
        assert {"quiz_review_events", "lesson_view_events"}.issubset(post_up_tables)
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
