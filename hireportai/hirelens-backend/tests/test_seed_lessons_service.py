"""Tests for the Phase 6 slice 6.4.5 reference seed loader.

Spec: docs/specs/phase-6/05-seed-lessons.md §6.1, §10.1.

The loader owns its transaction (calls commit / rollback per dry_run);
tests therefore truncate the curriculum tables before and after each
test so committed seed rows don't bleed across tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import select, text, update

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.services.seed_lessons_service import (
    SeedLoadReport,
    SlugMismatchError,
    UnexpectedH2SectionError,
    load_seed_corpus,
)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(loop_scope="session")
async def curriculum_db(db_session):
    """Yield ``db_session`` with curriculum tables truncated before+after.

    The seed loader commits its own work, so the parent rollback-only
    fixture cannot guarantee isolation. Truncating the three curriculum
    tables (CASCADE) before and after each test gives clean state.
    """

    async def _truncate() -> None:
        await db_session.execute(
            text(
                "TRUNCATE TABLE quiz_item_progress, quiz_items, lessons, decks "
                "RESTART IDENTITY CASCADE"
            )
        )
        await db_session.commit()

    await _truncate()
    try:
        yield db_session
    finally:
        await _truncate()


def _write_meta(deck_dir: Path, **fields) -> None:
    payload = {
        "slug": deck_dir.name,
        "title": "Test Deck",
        "description": "Test description.",
        "display_order": 0,
        "persona_visibility": "both",
        "tier": "foundation",
    }
    payload.update(fields)
    yaml_lines = []
    for k, v in payload.items():
        if isinstance(v, str) and "\n" in v:
            yaml_lines.append(f"{k}: |\n  " + v.replace("\n", "\n  "))
        else:
            yaml_lines.append(f"{k}: {v}")
    body = "---\n" + "\n".join(yaml_lines) + "\n---\n"
    (deck_dir / "_meta.md").write_text(body, encoding="utf-8")


def _write_lesson(
    deck_dir: Path,
    slug: str,
    *,
    title: str = "Lesson Title",
    display_order: int = 0,
    concept: str = "Concept body content.",
    production: str = "Production body content.",
    examples: str = "Examples body content.",
    quiz_items: list[dict] | None = None,
) -> None:
    if quiz_items is None:
        quiz_items = [
            {
                "question": f"What is the purpose of {slug}?",
                "answer": f"To teach {slug}.",
                "question_type": "free_text",
                "difficulty": "easy",
                "display_order": 0,
            }
        ]
    fm_lines = [
        f"slug: {slug}",
        f"title: {title}",
        f"display_order: {display_order}",
        "quiz_items:",
    ]
    for q in quiz_items:
        fm_lines.append(f"  - question: {q['question']!r}")
        fm_lines.append(f"    answer: {q['answer']!r}")
        fm_lines.append(f"    question_type: {q['question_type']}")
        if q.get("distractors"):
            fm_lines.append("    distractors:")
            for d in q["distractors"]:
                fm_lines.append(f"      - {d!r}")
        fm_lines.append(f"    difficulty: {q['difficulty']}")
        fm_lines.append(f"    display_order: {q['display_order']}")
    body = (
        "---\n"
        + "\n".join(fm_lines)
        + "\n---\n"
        + f"## Concept\n{concept}\n"
        + f"## Production\n{production}\n"
        + f"## Examples\n{examples}\n"
    )
    (deck_dir / f"{slug}.md").write_text(body, encoding="utf-8")


def _build_minimal_corpus(root: Path) -> None:
    """One deck, two lessons, two quiz_items each. Used by most tests."""
    deck = root / "test-deck"
    deck.mkdir(parents=True)
    _write_meta(deck)
    _write_lesson(
        deck,
        "lesson-one",
        display_order=0,
        quiz_items=[
            {
                "question": "Q1?",
                "answer": "A1.",
                "question_type": "free_text",
                "difficulty": "easy",
                "display_order": 0,
            },
            {
                "question": "Q2 mcq?",
                "answer": "Choice A",
                "question_type": "mcq",
                "distractors": ["Choice B", "Choice C"],
                "difficulty": "medium",
                "display_order": 1,
            },
        ],
    )
    _write_lesson(
        deck,
        "lesson-two",
        display_order=1,
        quiz_items=[
            {
                "question": "Q3 code?",
                "answer": "answer = 42",
                "question_type": "code_completion",
                "difficulty": "hard",
                "display_order": 0,
            }
        ],
    )


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_empty_db_full_insert(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    report = await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    assert isinstance(report, SeedLoadReport)
    assert report.decks.created == 1
    assert report.lessons.created == 2
    assert report.quiz_items.created == 3
    assert report.decks.unchanged == 0
    assert report.lessons.unchanged == 0

    decks = (await curriculum_db.execute(select(Deck))).scalars().all()
    assert len(decks) == 1
    assert decks[0].slug == "test-deck"
    lessons = (await curriculum_db.execute(select(Lesson))).scalars().all()
    assert len(lessons) == 2
    quizzes = (await curriculum_db.execute(select(QuizItem))).scalars().all()
    assert len(quizzes) == 3
    # D-9: lessons pre-published on initial INSERT.
    for lesson in lessons:
        assert lesson.published_at is not None
        assert lesson.version == 1
        assert lesson.version_type == "initial"


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_idempotent_no_diff(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    second = await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    assert second.decks.unchanged == 1
    assert second.lessons.unchanged == 2
    assert second.quiz_items.unchanged == 3
    assert second.decks.updated == 0
    assert second.lessons.updated == 0
    assert second.quiz_items.updated == 0

    lessons = (await curriculum_db.execute(select(Lesson))).scalars().all()
    for lesson in lessons:
        assert lesson.version == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_lesson_diff_minor_edit(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    lesson_path = tmp_path / "test-deck" / "lesson-one.md"
    text_now = lesson_path.read_text(encoding="utf-8")
    text_now = text_now.replace("Concept body content.", "Updated concept text.")
    lesson_path.write_text(text_now, encoding="utf-8")

    second = await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    assert second.lessons.updated == 1
    assert second.lessons.unchanged == 1

    res = await curriculum_db.execute(
        select(Lesson).where(Lesson.slug == "lesson-one")
    )
    lesson = res.scalar_one()
    assert lesson.version == 2
    assert lesson.version_type == "minor_edit"
    assert "Updated concept text." in lesson.concept_md


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_skips_admin_archived_deck(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    await curriculum_db.execute(
        update(Deck).where(Deck.slug == "test-deck").values(archived_at=datetime.now(timezone.utc))
    )
    await curriculum_db.commit()

    second = await load_seed_corpus(curriculum_db, seed_root=tmp_path)
    assert second.decks.skipped_archived == 1
    assert second.decks.updated == 0

    res = await curriculum_db.execute(select(Deck))
    deck = res.scalar_one()
    assert deck.archived_at is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_skips_admin_archived_lesson(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    await curriculum_db.execute(
        update(Lesson)
        .where(Lesson.slug == "lesson-one")
        .values(archived_at=datetime.now(timezone.utc))
    )
    await curriculum_db.commit()

    second = await load_seed_corpus(curriculum_db, seed_root=tmp_path)
    assert second.lessons.skipped_archived == 1
    assert second.lessons.unchanged == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_skips_admin_retired_quiz_item(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    res = await curriculum_db.execute(select(QuizItem).where(QuizItem.question == "Q1?"))
    target = res.scalar_one()
    await curriculum_db.execute(
        update(QuizItem)
        .where(QuizItem.id == target.id)
        .values(retired_at=datetime.now(timezone.utc))
    )
    await curriculum_db.commit()

    second = await load_seed_corpus(curriculum_db, seed_root=tmp_path)
    assert second.quiz_items.skipped_archived == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_quiz_item_question_text_change(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    res = await curriculum_db.execute(select(QuizItem).where(QuizItem.question == "Q3 code?"))
    original = res.scalar_one()
    original_id = original.id

    lesson_path = tmp_path / "test-deck" / "lesson-two.md"
    text_now = lesson_path.read_text(encoding="utf-8")
    text_now = text_now.replace("'Q3 code?'", "'Q3 code edited?'")
    lesson_path.write_text(text_now, encoding="utf-8")

    second = await load_seed_corpus(curriculum_db, seed_root=tmp_path)
    assert second.quiz_items.updated == 1
    assert second.quiz_items.created == 0

    res = await curriculum_db.execute(select(QuizItem).where(QuizItem.id == original_id))
    refreshed = res.scalar_one()
    assert refreshed.question == "Q3 code edited?"


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_validation_error_short_circuits(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)
    meta = (tmp_path / "test-deck" / "_meta.md").read_text(encoding="utf-8")
    meta = meta.replace("persona_visibility: both", "persona_visibility: bogus")
    (tmp_path / "test-deck" / "_meta.md").write_text(meta, encoding="utf-8")

    with pytest.raises(ValidationError):
        await load_seed_corpus(curriculum_db, seed_root=tmp_path)

    decks = (await curriculum_db.execute(select(Deck))).scalars().all()
    assert decks == []


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_dry_run_no_writes(
    curriculum_db, tmp_path: Path
) -> None:
    _build_minimal_corpus(tmp_path)

    report = await load_seed_corpus(curriculum_db, seed_root=tmp_path, dry_run=True)
    assert report.dry_run is True
    assert report.decks.created == 1
    assert report.lessons.created == 2

    decks = (await curriculum_db.execute(select(Deck))).scalars().all()
    assert decks == []
    lessons = (await curriculum_db.execute(select(Lesson))).scalars().all()
    assert lessons == []


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_slug_mismatch_raises(
    curriculum_db, tmp_path: Path
) -> None:
    deck = tmp_path / "deck-a"
    deck.mkdir()
    _write_meta(deck, slug="deck-b")  # mismatches directory name
    _write_lesson(deck, "lesson-one")

    with pytest.raises(SlugMismatchError):
        await load_seed_corpus(curriculum_db, seed_root=tmp_path)


@pytest.mark.asyncio(loop_scope="session")
async def test_load_seed_corpus_unexpected_h2_section_raises(
    curriculum_db, tmp_path: Path
) -> None:
    deck = tmp_path / "deck-x"
    deck.mkdir()
    _write_meta(deck)
    body = dedent(
        """\
        ---
        slug: lesson-bad
        title: Bad Lesson
        display_order: 0
        quiz_items:
          - question: Q?
            answer: A.
            question_type: free_text
            difficulty: easy
            display_order: 0
        ---
        ## Concept
        text
        ## Edge Cases
        oops
        ## Production
        prod
        ## Examples
        ex
        """
    )
    (deck / "lesson-bad.md").write_text(body, encoding="utf-8")

    with pytest.raises(UnexpectedH2SectionError):
        await load_seed_corpus(curriculum_db, seed_root=tmp_path)
