"""Admin card CRUD service — create, update, delete, list, bulk import."""
import csv
import io
import math
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.schemas.admin_card import (
    AdminCardListResponse,
    AdminCardResponse,
    CardCreateRequest,
    CardImportResponse,
    CardImportRowError,
    CardUpdateRequest,
)

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_MAX_CSV_ROWS = 500
_MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB
_REQUIRED_CSV_HEADERS = {"category_id", "question", "answer", "difficulty"}


def _to_response(card: Card, category_name: str) -> AdminCardResponse:
    return AdminCardResponse(
        id=card.id,
        category_id=card.category_id,
        category_name=category_name,
        question=card.question,
        answer=card.answer,
        difficulty=card.difficulty,
        tags=card.tags or [],
        embedding_status="ready" if card.embedding is not None else "pending",
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


async def _get_category(db: AsyncSession, category_id: str) -> Category:
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"category_id '{category_id}' does not reference an existing category.",
        )
    return cat


async def create_card(
    payload: CardCreateRequest, db: AsyncSession,
) -> AdminCardResponse:
    category = await _get_category(db, payload.category_id)

    card = Card(
        category_id=payload.category_id,
        question=payload.question,
        answer=payload.answer,
        difficulty=payload.difficulty,
        tags=payload.tags,
    )
    db.add(card)
    await db.flush()
    await db.refresh(card)

    return _to_response(card, category.name)


async def update_card(
    card_id: str, payload: CardUpdateRequest, db: AsyncSession,
) -> AdminCardResponse:
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.deleted_at.is_(None))
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    needs_re_embed = False

    if payload.category_id is not None:
        await _get_category(db, payload.category_id)
        card.category_id = payload.category_id
    if payload.question is not None:
        card.question = payload.question
        needs_re_embed = True
    if payload.answer is not None:
        card.answer = payload.answer
        needs_re_embed = True
    if payload.difficulty is not None:
        card.difficulty = payload.difficulty
    if payload.tags is not None:
        card.tags = payload.tags

    if needs_re_embed:
        card.embedding = None

    await db.flush()
    await db.refresh(card)

    cat_result = await db.execute(select(Category).where(Category.id == card.category_id))
    category = cat_result.scalar_one()

    return _to_response(card, category.name)


async def delete_card(card_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.deleted_at.is_(None))
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    # Check for review history
    progress_count = await db.execute(
        select(func.count()).select_from(CardProgress).where(CardProgress.card_id == card_id)
    )
    has_reviews = progress_count.scalar_one() > 0

    if has_reviews:
        card.deleted_at = datetime.now(timezone.utc)
        await db.flush()
    else:
        await db.delete(card)
        await db.flush()


async def list_cards(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 50,
    category_id: str | None = None,
    difficulty: str | None = None,
    tags: str | None = None,
    q: str | None = None,
) -> AdminCardListResponse:
    base = (
        select(Card, Category.name.label("category_name"))
        .join(Category, Category.id == Card.category_id)
        .where(Card.deleted_at.is_(None))
    )

    if category_id:
        base = base.where(Card.category_id == category_id)
    if difficulty:
        base = base.where(Card.difficulty == difficulty)
    if q:
        base = base.where(Card.question.ilike(f"%{q}%"))
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tag_list:
            base = base.where(Card.tags.op("@>")(f'["{tag}"]'))

    # Count total
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    pages = max(1, math.ceil(total / per_page))
    offset = (page - 1) * per_page

    rows = (
        await db.execute(base.order_by(Card.created_at.desc()).offset(offset).limit(per_page))
    ).all()

    cards = [_to_response(row.Card, row.category_name) for row in rows]

    return AdminCardListResponse(
        cards=cards, total=total, page=page, per_page=per_page, pages=pages,
    )


async def bulk_import_csv(
    file_content: bytes, partial: bool, db: AsyncSession,
) -> CardImportResponse:
    if len(file_content) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV file exceeds maximum size of {_MAX_CSV_BYTES // (1024*1024)} MB.",
        )

    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must be UTF-8 encoded.",
        )

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty or has no headers.",
        )

    headers = {h.strip() for h in reader.fieldnames}
    missing = _REQUIRED_CSV_HEADERS - headers
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing required headers: {', '.join(sorted(missing))}",
        )

    rows = list(reader)
    if len(rows) > _MAX_CSV_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV exceeds maximum of {_MAX_CSV_ROWS} rows.",
        )

    # Pre-fetch all valid category IDs
    cat_result = await db.execute(select(Category.id))
    valid_category_ids = {r[0] for r in cat_result.all()}

    errors: list[CardImportRowError] = []
    cards_to_add: list[Card] = []

    for i, row in enumerate(rows, start=2):  # row 1 = header
        row_errors = []
        cat_id = row.get("category_id", "").strip()
        question = row.get("question", "").strip()
        answer = row.get("answer", "").strip()
        diff = row.get("difficulty", "").strip()
        tags_raw = row.get("tags", "").strip()

        if not cat_id or cat_id not in valid_category_ids:
            row_errors.append(f"category_id '{cat_id}' does not reference an existing category")
        if not question:
            row_errors.append("question is required")
        if not answer:
            row_errors.append("answer is required")
        if diff not in _VALID_DIFFICULTIES:
            row_errors.append(f"Invalid difficulty '{diff}' — must be easy, medium, or hard")

        if row_errors:
            errors.append(CardImportRowError(row=i, error="; ".join(row_errors)))
            continue

        tag_list = [t.strip() for t in tags_raw.split(";") if t.strip()] if tags_raw else []

        cards_to_add.append(Card(
            category_id=cat_id,
            question=question,
            answer=answer,
            difficulty=diff,
            tags=tag_list,
        ))

    if errors and not partial:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CardImportResponse(
                created_count=0,
                skipped_count=len(errors),
                errors=errors,
            ).model_dump(),
        )

    db.add_all(cards_to_add)
    await db.flush()

    return CardImportResponse(
        created_count=len(cards_to_add),
        skipped_count=len(errors),
        errors=errors,
    )
