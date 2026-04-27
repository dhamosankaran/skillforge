"""Phase 6 slice 6.1 — foundation schema verification tests.

Spec: docs/specs/phase-6/01-foundation-schema.md §8.

Verifies that the four foundation tables (`decks`, `lessons`, `quiz_items`,
`quiz_item_progress`) match the column / constraint / index contract spelled
out in spec §4, and that legacy `cards` / `categories` / `card_progress` /
`card_feedback` remain intact (AC-7) — drop is deferred to slice 6.15.

The schema-shape tests run via the standard `engine` fixture which builds the
schema via ``Base.metadata.create_all``. The dedicated ``test_alembic_round_trip``
test is gated behind ``@pytest.mark.integration`` because it needs to invoke
Alembic against a freshly-stamped database; the manual shell-side round-trip
(``alembic upgrade head → downgrade -1 → upgrade head``) is the canonical
AC-1 verification.
"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _reflect(engine):
    """Return (tables, columns_by_table, indexes_by_table, fks_by_table, uniques_by_table)."""

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


def _has_unique(uniques, columns: list[str], name: str | None = None) -> bool:
    for uq in uniques:
        if list(uq["column_names"]) == columns:
            if name is None or uq.get("name") == name:
                return True
    return False


def _fk_to(fks, local_col: str, target_table: str, target_col: str = "id"):
    for fk in fks:
        if local_col in fk["constrained_columns"] and fk["referred_table"] == target_table:
            return fk
    return None


# ---------------------------------------------------------------------------
# AC-2: decks table shape
# ---------------------------------------------------------------------------
async def test_decks_table_shape(engine):
    tables, cols, idxs, fks, uqs = await _reflect(engine)
    assert "decks" in tables

    deck_cols = cols["decks"]
    expected = {
        "id", "slug", "title", "description", "display_order", "icon",
        "persona_visibility", "tier",
        "created_at", "updated_at", "archived_at",
    }
    assert expected.issubset(deck_cols.keys())

    # Nullability — id PK is non-null; archived_at + icon are nullable.
    assert deck_cols["slug"]["nullable"] is False
    assert deck_cols["title"]["nullable"] is False
    assert deck_cols["description"]["nullable"] is False
    assert deck_cols["icon"]["nullable"] is True
    assert deck_cols["archived_at"]["nullable"] is True
    assert deck_cols["persona_visibility"]["nullable"] is False
    assert deck_cols["tier"]["nullable"] is False

    # AC-3: UNIQUE on slug.
    assert _has_unique(uqs["decks"], ["slug"]) or any(
        ix.get("unique") and list(ix["column_names"]) == ["slug"] for ix in idxs["decks"]
    )

    # Composite index for the persona-visibility / display_order Learn-page query.
    assert _has_index(idxs["decks"], ["persona_visibility", "display_order"])


# ---------------------------------------------------------------------------
# AC-2 + AC-3 + AC-5: lessons table shape
# ---------------------------------------------------------------------------
async def test_lessons_table_shape(engine):
    tables, cols, idxs, fks, uqs = await _reflect(engine)
    assert "lessons" in tables

    lesson_cols = cols["lessons"]
    expected = {
        "id", "deck_id", "slug", "title",
        "concept_md", "production_md", "examples_md",
        "display_order", "version", "version_type",
        "published_at", "generated_by_model",
        "source_content_id", "quality_score",
        "created_at", "updated_at", "archived_at",
    }
    assert expected.issubset(lesson_cols.keys())

    # Required content columns — concept/production/examples are NOT NULL.
    assert lesson_cols["concept_md"]["nullable"] is False
    assert lesson_cols["production_md"]["nullable"] is False
    assert lesson_cols["examples_md"]["nullable"] is False
    # Quality + provenance + scheduling are nullable.
    assert lesson_cols["published_at"]["nullable"] is True
    assert lesson_cols["generated_by_model"]["nullable"] is True
    assert lesson_cols["source_content_id"]["nullable"] is True
    assert lesson_cols["quality_score"]["nullable"] is True
    assert lesson_cols["archived_at"]["nullable"] is True

    # AC-3: composite UNIQUE on (deck_id, slug).
    assert _has_unique(uqs["lessons"], ["deck_id", "slug"], "uq_lessons_deck_slug")

    # FK to decks ON DELETE RESTRICT.
    fk = _fk_to(fks["lessons"], "deck_id", "decks")
    assert fk is not None
    assert (fk.get("options") or {}).get("ondelete") == "RESTRICT"

    # AC-5: source_content_id has NO FK constraint at this revision.
    assert _fk_to(fks["lessons"], "source_content_id", "source_content") is None

    # Indexes — partial WHERE clauses are reflected by sqlalchemy in the index dict.
    assert _has_index(idxs["lessons"], ["deck_id", "display_order"])
    assert _has_index(idxs["lessons"], ["published_at"])
    assert _has_index(idxs["lessons"], ["deck_id", "archived_at"])
    assert _has_index(idxs["lessons"], ["source_content_id"])


# ---------------------------------------------------------------------------
# AC-2 + AC-4: quiz_items table shape (incl. self-referential FK)
# ---------------------------------------------------------------------------
async def test_quiz_items_table_shape(engine):
    tables, cols, idxs, fks, uqs = await _reflect(engine)
    assert "quiz_items" in tables

    qi_cols = cols["quiz_items"]
    expected = {
        "id", "lesson_id", "question", "answer", "question_type",
        "distractors", "difficulty", "display_order", "version",
        "superseded_by_id", "retired_at", "generated_by_model",
        "created_at", "updated_at",
    }
    assert expected.issubset(qi_cols.keys())

    assert qi_cols["question"]["nullable"] is False
    assert qi_cols["answer"]["nullable"] is False
    assert qi_cols["distractors"]["nullable"] is True
    assert qi_cols["superseded_by_id"]["nullable"] is True
    assert qi_cols["retired_at"]["nullable"] is True

    # FK to lessons ON DELETE CASCADE.
    fk_lesson = _fk_to(fks["quiz_items"], "lesson_id", "lessons")
    assert fk_lesson is not None
    assert (fk_lesson.get("options") or {}).get("ondelete") == "CASCADE"

    # AC-4: self-referential FK on superseded_by_id with ON DELETE SET NULL.
    fk_self = _fk_to(fks["quiz_items"], "superseded_by_id", "quiz_items")
    assert fk_self is not None
    assert (fk_self.get("options") or {}).get("ondelete") == "SET NULL"

    # Indexes.
    assert _has_index(idxs["quiz_items"], ["lesson_id", "display_order"])
    assert _has_index(idxs["quiz_items"], ["superseded_by_id"])


# ---------------------------------------------------------------------------
# AC-2 + AC-3: quiz_item_progress table shape
# ---------------------------------------------------------------------------
async def test_quiz_item_progress_table_shape(engine):
    tables, cols, idxs, fks, uqs = await _reflect(engine)
    assert "quiz_item_progress" in tables

    qip_cols = cols["quiz_item_progress"]
    expected = {
        "id", "user_id", "quiz_item_id", "state",
        "stability", "difficulty_fsrs", "elapsed_days", "scheduled_days",
        "reps", "lapses", "fsrs_step", "last_reviewed",
        "due_date", "created_at", "updated_at",
    }
    assert expected.issubset(qip_cols.keys())

    # D-1: due_date NOT NULL with server_default.
    assert qip_cols["due_date"]["nullable"] is False
    assert qip_cols["fsrs_step"]["nullable"] is True
    assert qip_cols["last_reviewed"]["nullable"] is True

    # AC-3: UNIQUE (user_id, quiz_item_id) named uq_quiz_item_progress_user_quiz.
    assert _has_unique(
        uqs["quiz_item_progress"],
        ["user_id", "quiz_item_id"],
        "uq_quiz_item_progress_user_quiz",
    )

    # FKs both ON DELETE CASCADE.
    fk_user = _fk_to(fks["quiz_item_progress"], "user_id", "users")
    assert fk_user is not None
    assert (fk_user.get("options") or {}).get("ondelete") == "CASCADE"
    fk_qi = _fk_to(fks["quiz_item_progress"], "quiz_item_id", "quiz_items")
    assert fk_qi is not None
    assert (fk_qi.get("options") or {}).get("ondelete") == "CASCADE"

    # Daily-review primary index.
    assert _has_index(idxs["quiz_item_progress"], ["user_id", "due_date"])


# ---------------------------------------------------------------------------
# AC-6: quiz_item_progress mirrors card_progress modulo FK swap
# ---------------------------------------------------------------------------
async def test_quiz_item_progress_mirrors_card_progress(engine):
    tables, cols, _idxs, _fks, _uqs = await _reflect(engine)
    assert "card_progress" in tables and "quiz_item_progress" in tables

    cp = cols["card_progress"]
    qip = cols["quiz_item_progress"]

    # Skip the table-specific FK columns: card_progress.card_id ↔ quiz_item_progress.quiz_item_id.
    skip_cp = {"card_id"}
    skip_qip = {"quiz_item_id"}

    cp_columns = set(cp.keys()) - skip_cp
    qip_columns = set(qip.keys()) - skip_qip
    missing_in_qip = cp_columns - qip_columns
    assert not missing_in_qip, f"quiz_item_progress is missing {missing_in_qip} from card_progress"

    # For every shared column, type and nullability must match.
    mismatches: list[str] = []
    for name in cp_columns & qip_columns:
        cp_type = repr(cp[name]["type"])
        qip_type = repr(qip[name]["type"])
        if cp_type != qip_type:
            mismatches.append(f"{name}: card_progress={cp_type} vs quiz_item_progress={qip_type}")
        if cp[name]["nullable"] != qip[name]["nullable"]:
            mismatches.append(
                f"{name}: nullable card_progress={cp[name]['nullable']} vs "
                f"quiz_item_progress={qip[name]['nullable']}"
            )
    assert not mismatches, "card_progress / quiz_item_progress drift: " + "; ".join(mismatches)


# ---------------------------------------------------------------------------
# AC-7: legacy tables intact
# ---------------------------------------------------------------------------
async def test_legacy_tables_intact(engine):
    tables, _cols, _idxs, _fks, _uqs = await _reflect(engine)
    legacy = {"cards", "categories", "card_progress", "card_feedback"}
    missing = legacy - tables
    assert not missing, f"Slice 6.1 must NOT drop legacy tables; missing: {missing}"


# ---------------------------------------------------------------------------
# AC-1: alembic round-trip — gated as integration; manual shell run is canonical
# ---------------------------------------------------------------------------
@pytest.mark.integration
async def test_alembic_round_trip(engine):
    """Round-trip the four phase 6 tables via the Alembic CLI (subprocess).

    Stamps the test DB to head, downgrades one revision (drops the four
    phase 6 tables), then upgrades back — asserts the table set is identical
    on both ends. Subprocess invocation avoids nested-event-loop conflicts
    between pytest-asyncio and Alembic's `asyncio.run(...)` in env.py.

    Marker-gated because it mutates the shared test DB; the canonical AC-1
    check is the shell round-trip documented in `db-migration.md`.
    """
    import os
    import subprocess
    from pathlib import Path

    from sqlalchemy import text

    backend_dir = Path(__file__).resolve().parent.parent
    # env.py uses async_engine_from_config — keep the +asyncpg driver.
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
        _alembic("stamp", "57951e9f4cdc")
        _alembic("downgrade", "-1")
        post_down_tables, _, _, _, _ = await _reflect(engine)
        for t in ("decks", "lessons", "quiz_items", "quiz_item_progress"):
            assert t not in post_down_tables, f"{t} should be dropped after downgrade -1"
        _alembic("upgrade", "head")
        post_up_tables, _, _, _, _ = await _reflect(engine)
        assert {"decks", "lessons", "quiz_items", "quiz_item_progress"}.issubset(post_up_tables)
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
