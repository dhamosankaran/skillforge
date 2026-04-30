"""RQ worker entry point for the ingestion pipeline (Phase 6 slice 6.10b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §6.2 + §4.2 + §4.3
+ §12 D-4 / D-5 / D-6 / D-7 / D-13 / D-15.

`run_ingestion(job_id)` is the public entry point invoked by RQ. The
worker runs a synchronous async loop because the slice-6.4b admin
services (`lesson_admin_service.create_lesson` etc.) are async — RQ
itself is sync, so we drive a fresh event loop per job via
`asyncio.run`.

Three stages:
    1. Gemini reasoning-tier `lesson_gen` (tier-default; no
       `provider_override`).
    2. Anthropic `ingestion_critique` (`provider_override='anthropic'`
       per D-4).
    3. Persist via `deck_admin_service.create_deck` /
       `lesson_admin_service.create_lesson` /
       `quiz_item_admin_service.create_quiz_item` per G-5 single
       source of truth. Drafts only — `published_at` stays NULL.

Per-step retry per D-6: 3 attempts with backoff `[5, 15, 45]` seconds
between tries. `EditClassificationConflictError` triggers a single
re-attempt with the corrected `claimed` classification per AC-10.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.analytics import track as analytics_track
from app.core.config import get_settings
from app.core.llm_router import generate_for_task
from app.models.deck import Deck
from app.models.ingestion_job import IngestionJob
from app.schemas.deck import DeckCreateRequest
from app.schemas.ingestion import CritiqueSchema, GeneratedQuizItem, LessonGenSchema
from app.schemas.lesson import LessonCreateRequest
from app.schemas.quiz_item import QuizItemCreateRequest
from app.services import (
    deck_admin_service,
    lesson_admin_service,
    quiz_item_admin_service,
)
from app.services.admin_errors import (
    DeckSlugConflictError,
    EditClassificationConflictError,
    LessonSlugConflictError,
)
from app.services.ingestion_service import (
    INGESTION_BACKOFF_SCHEDULE,
    INGESTION_MAX_ATTEMPTS,
    critique_r2_key,
    draft_r2_key,
)
from app.services.object_storage_service import ObjectStorageService, get_storage
from app.services.prompt_template_service import load_prompt

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── Worker-private DB session factory ───────────────────────────────────────
#
# RQ workers run outside FastAPI's request scope, so the request-scoped
# `get_db` dependency is unusable here. We build a fresh sessionmaker per
# worker process and reuse it across jobs.
_worker_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _worker_session_factory
    if _worker_session_factory is None:
        settings = get_settings()
        engine = create_async_engine(
            settings.async_database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=4,
        )
        _worker_session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
    return _worker_session_factory


# ── Retry helper (per-step, observable in `current_attempt` per §4.3) ──────
async def _with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    on_attempt: Callable[[int], Awaitable[None]],
    backoff: list[int] = INGESTION_BACKOFF_SCHEDULE,
    max_attempts: int = INGESTION_MAX_ATTEMPTS,
) -> T:
    """Run `fn` up to `max_attempts` times, sleeping `backoff[i]` between tries.

    `on_attempt(attempt_number)` is called BEFORE each invocation so the
    job row's `current_attempt` column reflects in-flight progress for
    admin observability.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        await on_attempt(attempt)
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001 — retry covers all exceptions
            last_exc = exc
            logger.warning(
                "ingestion stage attempt %d/%d failed: %s", attempt, max_attempts, exc,
            )
            if attempt < max_attempts:
                # Use the per-attempt backoff (or the last entry if attempts
                # outrun the schedule — small list, defensive bounds).
                idx = min(attempt - 1, len(backoff) - 1)
                await asyncio.sleep(backoff[idx])
    assert last_exc is not None
    raise last_exc


# ── Stage helpers ───────────────────────────────────────────────────────────
async def _generate_lesson(source_md: str, deck_context: str) -> LessonGenSchema:
    """Stage 1 — Gemini reasoning-tier gen (D-4 — no provider override)."""
    template = load_prompt("lesson_gen")
    prompt = template.format(source_markdown=source_md, deck_context=deck_context)
    raw = generate_for_task(
        task="lesson_gen",
        prompt=prompt,
        json_mode=True,
        response_schema=LessonGenSchema,
        thinking_budget=2000,
    )
    return LessonGenSchema.model_validate_json(raw)


async def _critique_lesson(
    draft: LessonGenSchema, source_md: str
) -> CritiqueSchema:
    """Stage 2 — Anthropic critique via `provider_override='anthropic'` (D-4)."""
    template = load_prompt("ingestion_critique")
    prompt = template.format(
        generated_lesson_json=draft.model_dump_json(),
        source_markdown=source_md,
    )
    raw = generate_for_task(
        task="lesson_gen",  # tier-routed; provider_override is the cross-model dispatch
        prompt=prompt,
        json_mode=True,
        response_schema=CritiqueSchema,
        provider_override="anthropic",
    )
    return CritiqueSchema.model_validate_json(raw)


async def _resolve_or_create_deck(
    *,
    job: IngestionJob,
    target_slug: str,
    db: AsyncSession,
    admin_id: str,
) -> str:
    """Return a deck_id for `target_slug`. Creates a draft deck if missing.

    Per G-5 single source of truth: all writes go through
    `deck_admin_service.create_deck`. Slug-based UPSERT per D-5 — when an
    existing deck matches, return its id; otherwise create one with the
    LLM-supplied slug.
    """
    result = await db.execute(select(Deck).where(Deck.slug == target_slug))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing.id

    # Create a minimal deck. Title falls back to slug-derived; admin can
    # rename via the existing slice 6.4b PATCH endpoint.
    payload = DeckCreateRequest(
        slug=target_slug,
        title=target_slug.replace("-", " ").title(),
        description=f"Ingested deck — created from job {job.id}.",
        persona_visibility="both",
        tier="premium",
    )
    try:
        deck = await deck_admin_service.create_deck(payload, db, admin_id)
    except DeckSlugConflictError:
        # Race — another writer just created the deck. Re-fetch.
        result = await db.execute(select(Deck).where(Deck.slug == target_slug))
        deck_row = result.scalar_one()
        return deck_row.id
    return deck.id


def _lesson_payload(gen: LessonGenSchema) -> LessonCreateRequest:
    return LessonCreateRequest(
        slug=gen.lesson_slug,
        title=gen.title,
        concept_md=gen.concept_md,
        production_md=gen.production_md,
        examples_md=gen.examples_md,
        display_order=0,
    )


def _quiz_item_payload(item: GeneratedQuizItem) -> QuizItemCreateRequest:
    """Map LLM-shaped quiz to admin write shape.

    LLM emits `question_type ∈ {recall, application}`; the on-disk
    `QuizQuestionType` is `{mcq, free_text, code_completion}`. Map
    `recall` / `application` → `free_text` (the catch-all admin shape
    that supports prose answers without distractors). MCQ + code-
    completion stay admin-curated in v1 — out of scope for the gen
    prompt per spec §13.
    """
    return QuizItemCreateRequest(
        question=item.question,
        answer=item.answer,
        question_type="free_text",
        difficulty=item.difficulty,
        display_order=0,
    )


async def _persist_drafts(
    *,
    job: IngestionJob,
    gen: LessonGenSchema,
    db: AsyncSession,
) -> tuple[str, list[str]]:
    """Stage 3 — write through slice 6.4b admin services per G-5.

    Returns `(lesson_id, quiz_item_ids)`. `published_at` stays NULL on the
    new lesson per G-6 + D-7 (drafts only).
    """
    admin_id = job.created_by_user_id or ""
    deck_id = await _resolve_or_create_deck(
        job=job, target_slug=gen.target_deck_slug, db=db, admin_id=admin_id
    )

    # Slug-based UPSERT per D-5 — surfacing `LessonSlugConflictError`
    # against the same lesson_slug under the same deck means re-ingest of
    # edited source. v1 raises so the job fails terminally; future slice
    # routes to substantive-edit cascade via lesson_admin_service.update.
    lesson = await lesson_admin_service.create_lesson(
        deck_id, _lesson_payload(gen), db, admin_id
    )

    quiz_item_ids: list[str] = []
    for item in gen.quiz_items:
        qi = await quiz_item_admin_service.create_quiz_item(
            lesson.id, _quiz_item_payload(item), db, admin_id
        )
        quiz_item_ids.append(qi.id)

    job.target_deck_id = deck_id
    job.generated_lesson_ids = [lesson.id]
    job.generated_quiz_item_count = len(quiz_item_ids)
    return lesson.id, quiz_item_ids


# ── Stage-status writer ─────────────────────────────────────────────────────
async def _set_status(
    db: AsyncSession,
    job: IngestionJob,
    status: str,
    *,
    attempt: Optional[int] = None,
    error: Optional[str] = None,
    critique_verdict: Optional[str] = None,
) -> None:
    job.status = status
    if attempt is not None:
        job.current_attempt = attempt
    if error is not None:
        job.error_message = error
    if critique_verdict is not None:
        job.critique_verdict = critique_verdict
    if status in ("completed", "failed"):
        job.completed_at = datetime.now(timezone.utc)
    elif job.started_at is None and status != "pending":
        job.started_at = datetime.now(timezone.utc)
    await db.flush()


# ── Async job runner ────────────────────────────────────────────────────────
async def _run_ingestion_async(job_id: str) -> None:
    """Drive one ingestion job to terminal state. Public entry point per `run_ingestion`."""
    factory = _get_session_factory()
    storage = get_storage()
    started_at = time.monotonic()

    async with factory() as db:
        result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            logger.warning("ingestion job %s not found in DB", job_id)
            return

        admin_id = job.created_by_user_id or ""

        # ── Fetch source markdown from R2.
        try:
            await _set_status(db, job, "running", attempt=0)
            await db.commit()
            source_md = (
                await asyncio.to_thread(storage.get_object, job.source_r2_key)
            ).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            await _terminal_failure(
                db, job, stage="enqueue_dedup", error=f"source fetch failed: {exc}",
                admin_id=admin_id, started_at=started_at,
            )
            return

        deck_context = job.target_deck_slug or "(orchestrator may propose a new deck)"

        # ── Stage 1 — gen.
        try:
            async def _on_gen_attempt(attempt: int) -> None:
                await _set_status(db, job, "generating", attempt=attempt)
                await db.commit()

            gen: LessonGenSchema = await _with_retry(
                lambda: _generate_lesson(source_md, deck_context),
                on_attempt=_on_gen_attempt,
            )
        except Exception as exc:  # noqa: BLE001
            await _terminal_failure(
                db, job, stage="gen", error=f"gen stage exhausted: {exc}",
                admin_id=admin_id, started_at=started_at,
            )
            return

        # Persist gen artifact to R2.
        try:
            gen_key = draft_r2_key(job.id)
            await asyncio.to_thread(
                storage.put_object,
                gen_key,
                gen.model_dump_json().encode("utf-8"),
                "application/json",
            )
            job.draft_r2_key = gen_key
            await db.flush()
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("draft R2 upload failed (non-fatal): %s", exc)

        # ── Stage 2 — critique.
        try:
            async def _on_critique_attempt(attempt: int) -> None:
                await _set_status(db, job, "critiquing", attempt=attempt)
                await db.commit()

            critique: CritiqueSchema = await _with_retry(
                lambda: _critique_lesson(gen, source_md),
                on_attempt=_on_critique_attempt,
            )
        except Exception as exc:  # noqa: BLE001
            await _terminal_failure(
                db, job, stage="critique", error=f"critique stage exhausted: {exc}",
                admin_id=admin_id, started_at=started_at,
            )
            return

        # Persist critique artifact to R2 + record verdict on the job row.
        try:
            crit_key = critique_r2_key(job.id)
            await asyncio.to_thread(
                storage.put_object,
                crit_key,
                critique.model_dump_json().encode("utf-8"),
                "application/json",
            )
            job.critique_r2_key = crit_key
            await db.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("critique R2 upload failed (non-fatal): %s", exc)

        # FAIL verdict short-circuits Stage 3 per §4.3 + AC-8.
        if critique.verdict == "FAIL":
            await _set_status(
                db,
                job,
                "failed",
                error=f"critique FAIL: {critique.rationale}",
                critique_verdict="FAIL",
            )
            await db.commit()
            await _emit_failed(
                admin_id=admin_id,
                job=job,
                stage="critique",
                error_class="critique_fail",
                started_at=started_at,
            )
            return

        job.critique_verdict = critique.verdict
        await db.flush()

        # ── Stage 3 — persist drafts.
        try:
            async def _on_persist_attempt(attempt: int) -> None:
                await _set_status(db, job, "publishing", attempt=attempt)
                await db.commit()

            await _on_persist_attempt(1)
            try:
                await _persist_drafts(job=job, gen=gen, db=db)
            except EditClassificationConflictError:
                # AC-10 — retry once with corrected `claimed`. The
                # create_lesson path doesn't carry a classification field
                # (it always inserts version=1), so a 409 here means a
                # downstream PATCH was attempted; future-slice scope when
                # we wire substantive-edit re-ingest. v1 surfaces the
                # retry signal but treats a second 409 as terminal.
                logger.info("ingestion: edit classification conflict — retry once")
                await _persist_drafts(job=job, gen=gen, db=db)
        except LessonSlugConflictError as exc:
            await db.rollback()
            await _terminal_failure(
                db, job, stage="persist", error=f"lesson slug conflict: {exc}",
                admin_id=admin_id, started_at=started_at, error_class="lesson_slug_conflict",
            )
            return
        except EditClassificationConflictError as exc:
            await db.rollback()
            await _terminal_failure(
                db, job, stage="persist", error=f"edit classification: {exc}",
                admin_id=admin_id, started_at=started_at, error_class="edit_classification_conflict",
            )
            return
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            await _terminal_failure(
                db, job, stage="persist", error=f"persist failed: {exc}",
                admin_id=admin_id, started_at=started_at,
            )
            return

        # ── Success.
        await _set_status(db, job, "completed")
        await db.commit()
        await db.refresh(job)
        await _emit_completed(admin_id=admin_id, job=job, started_at=started_at)


async def _terminal_failure(
    db: AsyncSession,
    job: IngestionJob,
    *,
    stage: str,
    error: str,
    admin_id: str,
    started_at: float,
    error_class: str = "exception",
) -> None:
    await _set_status(db, job, "failed", error=error)
    await db.commit()
    await _emit_failed(
        admin_id=admin_id, job=job, stage=stage, error_class=error_class,
        started_at=started_at,
    )


def _duration_seconds(started_at: float) -> int:
    return max(0, int(time.monotonic() - started_at))


async def _emit_completed(*, admin_id: str, job: IngestionJob, started_at: float) -> None:
    analytics_track(
        admin_id,
        "ingestion_job_completed",
        {
            "admin_id": admin_id,
            "job_id": job.id,
            "target_deck_id": job.target_deck_id,
            "generated_lesson_ids": list(job.generated_lesson_ids or []),
            "generated_quiz_item_count": job.generated_quiz_item_count,
            "critique_verdict": job.critique_verdict,
            "duration_seconds": _duration_seconds(started_at),
            "internal": True,
        },
    )


async def _emit_failed(
    *,
    admin_id: str,
    job: IngestionJob,
    stage: str,
    error_class: str,
    started_at: float,
) -> None:
    analytics_track(
        admin_id,
        "ingestion_job_failed",
        {
            "admin_id": admin_id,
            "job_id": job.id,
            "stage": stage,
            "error_class": error_class,
            "current_attempt": job.current_attempt,
            "duration_seconds": _duration_seconds(started_at),
            "internal": True,
        },
    )


# ── RQ entry point ──────────────────────────────────────────────────────────
def run_ingestion(job_id: str) -> None:
    """Sync entry point invoked by `rq worker ingestion`."""
    asyncio.run(_run_ingestion_async(job_id))
