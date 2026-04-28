"""Phase 6 slice 6.4.5 — reference seed lesson loader.

Loads the canonical hand-authored curriculum from
``app/data/decks/seed_lessons/<deck_slug>/{_meta.md, <lesson_slug>.md}``
into the slice 6.1 ``decks`` / ``lessons`` / ``quiz_items`` tables.

Spec: ``docs/specs/phase-6/05-seed-lessons.md`` §1-§14, §12 D-1..D-10.

Public entry point: :func:`load_seed_corpus`.

Design notes (per §12 locks):

- D-2: deck metadata in ``<deck_slug>/_meta.md`` frontmatter only;
  body ignored.
- D-3: lesson body parsed by H2 markers — text before the first H2 OR
  under ``## Concept`` → ``concept_md``; ``## Production`` →
  ``production_md``; ``## Examples`` → ``examples_md``.
- D-5: ``archived_at IS NOT NULL`` (decks/lessons) and
  ``retired_at IS NOT NULL`` (quiz_items) are immutable signals — the
  loader skips those rows on re-load.
- D-6: lesson edits always stamp ``version_type='minor_edit'`` —
  loader-side opt-out from the substantive-edit retire-and-replace
  cascade owned by slice 6.4b's admin PATCH route.
- D-7: quiz_item lookup by ``(lesson_id, sha256(question.strip())[:16])``
  hash; falls back to ``(lesson_id, display_order)`` so question-text
  edits UPDATE in place rather than orphan FSRS history.
- D-9: lessons set ``published_at = func.now()`` on initial INSERT.
- D-10: race-tolerant — natural-key UPSERTs catch ``IntegrityError`` on
  UNIQUE collisions and re-route through the lookup path.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.schemas.deck import DeckCreateRequest
from app.schemas.lesson import LessonCreateRequest
from app.schemas.quiz_item import QuizItemCreateRequest

logger = logging.getLogger(__name__)


# ── Errors ─────────────────────────────────────────────────────────────────


class SeedLoadError(Exception):
    """Base error for the seed loader. Aborts the load."""


class SlugMismatchError(SeedLoadError):
    """Directory/filename does not match the declared frontmatter slug."""


class UnexpectedH2SectionError(SeedLoadError):
    """Lesson body contains an H2 outside Concept/Production/Examples."""


class DuplicateQuestionHashError(SeedLoadError):
    """Two quiz_items in one lesson share identical question text."""


class MissingDeckMetaError(SeedLoadError):
    """A <deck_slug>/ directory has no _meta.md."""


# ── Report shapes ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SeedEntityCounts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_archived: int = 0


@dataclass
class _MutableEntityCounts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_archived: int = 0

    def freeze(self) -> SeedEntityCounts:
        return SeedEntityCounts(
            created=self.created,
            updated=self.updated,
            unchanged=self.unchanged,
            skipped_archived=self.skipped_archived,
        )


@dataclass(frozen=True)
class SeedLoadReport:
    decks: SeedEntityCounts
    lessons: SeedEntityCounts
    quiz_items: SeedEntityCounts
    dry_run: bool
    started_at: datetime
    finished_at: datetime
    seed_root: str


# ── Internal parse types ───────────────────────────────────────────────────


@dataclass(frozen=True)
class _ParsedLesson:
    payload: LessonCreateRequest
    quiz_items: list[QuizItemCreateRequest]
    file: Path


@dataclass(frozen=True)
class _ParsedDeck:
    payload: DeckCreateRequest
    lessons: list[_ParsedLesson]
    directory: Path


_VALID_H2_SECTIONS = {"concept", "production", "examples"}


# ── Body parsing ───────────────────────────────────────────────────────────


def _split_body_into_sections(body: str) -> tuple[str, str, str]:
    """Split a lesson markdown body into (concept, production, examples).

    Body before the first H2 falls under ``concept_md`` unless an explicit
    ``## Concept`` H2 is present (in which case the pre-H2 prose is
    discarded). Per spec §4.3.2, ordering must be Concept → Production →
    Examples; out-of-order H2s would mis-attribute prose, so the loader
    raises ``UnexpectedH2SectionError`` when a non-canonical H2 is seen.

    H2 matching is case-insensitive and trimmed.
    """
    lines = body.splitlines()
    sections: dict[str, list[str]] = {"concept": [], "production": [], "examples": []}

    current = "concept"
    saw_explicit_concept_h2 = False
    pre_h2_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            header = line[3:].strip().lower()
            if header not in _VALID_H2_SECTIONS:
                raise UnexpectedH2SectionError(
                    f"Lesson body contains H2 '## {line[3:].strip()}' — "
                    f"only Concept / Production / Examples are recognized."
                )
            current = header
            if header == "concept":
                saw_explicit_concept_h2 = True
                pre_h2_lines = []
            continue

        if not saw_explicit_concept_h2 and current == "concept" and not any(
            sections[s] for s in sections
        ):
            pre_h2_lines.append(line)
            continue

        sections[current].append(line)

    if not saw_explicit_concept_h2 and pre_h2_lines:
        sections["concept"] = pre_h2_lines

    return (
        "\n".join(sections["concept"]).strip(),
        "\n".join(sections["production"]).strip(),
        "\n".join(sections["examples"]).strip(),
    )


def _question_hash(question: str) -> str:
    """Stable 16-hex-char hash of trimmed question text per D-8."""
    return hashlib.sha256(question.strip().encode("utf-8")).hexdigest()[:16]


# ── File discovery + parsing ───────────────────────────────────────────────


def _parse_deck_directory(deck_dir: Path) -> _ParsedDeck:
    meta_path = deck_dir / "_meta.md"
    if not meta_path.is_file():
        raise MissingDeckMetaError(
            f"Deck directory {deck_dir.name!r} has no _meta.md"
        )

    meta = frontmatter.load(meta_path)
    deck_payload = DeckCreateRequest.model_validate(dict(meta.metadata))
    if deck_payload.slug != deck_dir.name:
        raise SlugMismatchError(
            f"Deck directory '{deck_dir.name}' but _meta.md slug "
            f"'{deck_payload.slug}'"
        )

    lessons: list[_ParsedLesson] = []
    for lesson_path in sorted(deck_dir.glob("*.md")):
        if lesson_path.name == "_meta.md":
            continue
        lessons.append(_parse_lesson_file(lesson_path))

    return _ParsedDeck(payload=deck_payload, lessons=lessons, directory=deck_dir)


def _parse_lesson_file(lesson_path: Path) -> _ParsedLesson:
    parsed = frontmatter.load(lesson_path)
    fm: dict[str, Any] = dict(parsed.metadata)

    raw_quiz_items = fm.pop("quiz_items", [])
    concept_md, production_md, examples_md = _split_body_into_sections(parsed.content)

    lesson_payload_dict = {
        **fm,
        "concept_md": concept_md,
        "production_md": production_md,
        "examples_md": examples_md,
    }
    lesson_payload = LessonCreateRequest.model_validate(lesson_payload_dict)

    expected_slug = lesson_path.stem
    if lesson_payload.slug != expected_slug:
        raise SlugMismatchError(
            f"Lesson file '{lesson_path.name}' but frontmatter slug "
            f"'{lesson_payload.slug}'"
        )

    quiz_payloads: list[QuizItemCreateRequest] = []
    seen_hashes: set[str] = set()
    for raw in raw_quiz_items:
        qpayload = QuizItemCreateRequest.model_validate(raw)
        h = _question_hash(qpayload.question)
        if h in seen_hashes:
            raise DuplicateQuestionHashError(
                f"Lesson '{lesson_path.name}' has duplicate question text "
                f"(hash {h})"
            )
        seen_hashes.add(h)
        quiz_payloads.append(qpayload)

    return _ParsedLesson(
        payload=lesson_payload, quiz_items=quiz_payloads, file=lesson_path
    )


# ── DB UPSERT ──────────────────────────────────────────────────────────────


_DECK_FIELDS = (
    "title",
    "description",
    "display_order",
    "icon",
    "persona_visibility",
    "tier",
)
_LESSON_FIELDS = (
    "title",
    "concept_md",
    "production_md",
    "examples_md",
    "display_order",
)
_QUIZ_FIELDS = (
    "question",
    "answer",
    "question_type",
    "distractors",
    "difficulty",
    "display_order",
)


async def _upsert_deck(
    db: AsyncSession,
    parsed: _ParsedDeck,
    counts: _MutableEntityCounts,
) -> Deck | None:
    """UPSERT one deck. Returns the row, or None if archived (skipped)."""
    res = await db.execute(select(Deck).where(Deck.slug == parsed.payload.slug))
    row = res.scalar_one_or_none()

    if row is None:
        try:
            async with db.begin_nested():
                row = Deck(
                    slug=parsed.payload.slug,
                    title=parsed.payload.title,
                    description=parsed.payload.description,
                    display_order=parsed.payload.display_order,
                    icon=parsed.payload.icon,
                    persona_visibility=parsed.payload.persona_visibility,
                    tier=parsed.payload.tier,
                )
                db.add(row)
                await db.flush()
            counts.created += 1
            return row
        except IntegrityError:
            # D-10: another loader inserted this slug between our SELECT and
            # INSERT. Savepoint already rolled back; re-route through lookup.
            res = await db.execute(
                select(Deck).where(Deck.slug == parsed.payload.slug)
            )
            row = res.scalar_one()

    if row.archived_at is not None:
        counts.skipped_archived += 1
        return None

    if _diff_and_apply(row, parsed.payload, _DECK_FIELDS):
        await db.flush()
        counts.updated += 1
    else:
        counts.unchanged += 1
    return row


async def _upsert_lesson(
    db: AsyncSession,
    deck: Deck,
    parsed: _ParsedLesson,
    counts: _MutableEntityCounts,
) -> Lesson | None:
    res = await db.execute(
        select(Lesson).where(
            Lesson.deck_id == deck.id,
            Lesson.slug == parsed.payload.slug,
        )
    )
    row = res.scalar_one_or_none()

    if row is None:
        try:
            async with db.begin_nested():
                now = datetime.now(timezone.utc)
                row = Lesson(
                    deck_id=deck.id,
                    slug=parsed.payload.slug,
                    title=parsed.payload.title,
                    concept_md=parsed.payload.concept_md,
                    production_md=parsed.payload.production_md,
                    examples_md=parsed.payload.examples_md,
                    display_order=parsed.payload.display_order,
                    version=1,
                    version_type="initial",
                    published_at=now,
                )
                db.add(row)
                await db.flush()
            counts.created += 1
            return row
        except IntegrityError:
            res = await db.execute(
                select(Lesson).where(
                    Lesson.deck_id == deck.id,
                    Lesson.slug == parsed.payload.slug,
                )
            )
            row = res.scalar_one()

    if row.archived_at is not None:
        counts.skipped_archived += 1
        return None

    if _diff_and_apply(row, parsed.payload, _LESSON_FIELDS):
        row.version += 1
        row.version_type = "minor_edit"
        await db.flush()
        counts.updated += 1
    else:
        counts.unchanged += 1
    return row


async def _upsert_quiz_item(
    db: AsyncSession,
    lesson: Lesson,
    parsed: QuizItemCreateRequest,
    counts: _MutableEntityCounts,
    used_ids: set[str],
) -> None:
    res = await db.execute(
        select(QuizItem).where(QuizItem.lesson_id == lesson.id)
    )
    existing = list(res.scalars().all())
    qhash = _question_hash(parsed.question)

    row = next(
        (r for r in existing if _question_hash(r.question) == qhash and r.id not in used_ids),
        None,
    )
    if row is None:
        row = next(
            (
                r
                for r in existing
                if r.display_order == parsed.display_order and r.id not in used_ids
            ),
            None,
        )

    if row is None:
        new_row = QuizItem(
            lesson_id=lesson.id,
            question=parsed.question,
            answer=parsed.answer,
            question_type=parsed.question_type,
            distractors=parsed.distractors,
            difficulty=parsed.difficulty,
            display_order=parsed.display_order,
            version=1,
        )
        db.add(new_row)
        await db.flush()
        used_ids.add(new_row.id)
        counts.created += 1
        return

    used_ids.add(row.id)
    if row.retired_at is not None:
        counts.skipped_archived += 1
        return

    if _diff_and_apply(row, parsed, _QUIZ_FIELDS):
        await db.flush()
        counts.updated += 1
    else:
        counts.unchanged += 1


def _diff_and_apply(row: Any, payload: Any, fields: tuple[str, ...]) -> bool:
    """Compare ``row`` to ``payload`` field-by-field and apply differences.

    Returns True iff any field changed.
    """
    changed = False
    for f in fields:
        new_val = getattr(payload, f)
        old_val = getattr(row, f)
        if old_val != new_val:
            setattr(row, f, new_val)
            changed = True
    return changed


# ── Public entry ───────────────────────────────────────────────────────────


def _default_seed_root() -> Path:
    return Path(app.__file__).resolve().parent / "data" / "decks" / "seed_lessons"


async def load_seed_corpus(
    db: AsyncSession,
    *,
    dry_run: bool = False,
    seed_root: Path | None = None,
) -> SeedLoadReport:
    """Load the seed corpus into the database (idempotent UPSERT).

    See module docstring + spec §6.1 for the full contract.
    """
    started_at = datetime.now(timezone.utc)
    root = seed_root or _default_seed_root()

    deck_counts = _MutableEntityCounts()
    lesson_counts = _MutableEntityCounts()
    quiz_counts = _MutableEntityCounts()

    if not root.is_dir():
        raise SeedLoadError(f"Seed root does not exist: {root}")

    deck_dirs = sorted([p for p in root.iterdir() if p.is_dir()])
    parsed_decks = [_parse_deck_directory(d) for d in deck_dirs]

    try:
        for parsed_deck in parsed_decks:
            deck_row = await _upsert_deck(db, parsed_deck, deck_counts)
            if deck_row is None:
                # Archived — skip the entire subtree per D-5. Lessons inside
                # archived decks are not enumerated.
                continue
            for parsed_lesson in parsed_deck.lessons:
                lesson_row = await _upsert_lesson(
                    db, deck_row, parsed_lesson, lesson_counts
                )
                if lesson_row is None:
                    continue
                used_ids: set[str] = set()
                for qi in parsed_lesson.quiz_items:
                    await _upsert_quiz_item(
                        db, lesson_row, qi, quiz_counts, used_ids
                    )

        if dry_run:
            await db.rollback()
        else:
            await db.commit()
    except (ValidationError, SeedLoadError, IntegrityError):
        await db.rollback()
        raise

    finished_at = datetime.now(timezone.utc)
    return SeedLoadReport(
        decks=deck_counts.freeze(),
        lessons=lesson_counts.freeze(),
        quiz_items=quiz_counts.freeze(),
        dry_run=dry_run,
        started_at=started_at,
        finished_at=finished_at,
        seed_root=str(root),
    )
