"""End-to-end ingestion pipeline integration test (Phase 6 slice 6.10b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §10.4 + §11
AC-9 / AC-19.

Marker-gated per R13: `@pytest.mark.integration`. CI runs
`-m "not integration"` so these tests are deselected by default.

The integration suite mocks the LLM responses (the cost of routing
~3 minutes of live LLM calls per test run is too high for the gen+
critique + R2 round-trip — the marker semantics keep this test in the
integration suite because it still exercises the worker → DB → admin-
service stack end-to-end against the real Postgres test DB).
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.jobs import ingestion_worker
from app.models.deck import Deck
from app.models.ingestion_job import IngestionJob
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.user import User
from app.schemas.ingestion import (
    CritiqueDimension,
    CritiqueSchema,
    GeneratedQuizItem,
    LessonGenSchema,
)
from app.services import ingestion_service
from app.schemas.ingestion import IngestionJobCreateRequest

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.integration,
]


def _make_storage_mock() -> MagicMock:
    storage = MagicMock()
    storage.put_object = MagicMock(return_value="s3://bucket/key")
    storage.get_object = MagicMock(
        return_value=b"# Source\n\nIntegration test source body."
    )
    return storage


def _make_queue_mock() -> MagicMock:
    queue = MagicMock()
    queue.enqueue = MagicMock()
    return queue


def _gen() -> LessonGenSchema:
    return LessonGenSchema(
        target_deck_slug="integ-deck",
        lesson_slug="integ-lesson",
        title="Integration Lesson",
        concept_md="Integration concept body — long enough to land cleanly.",
        production_md="Integration production body — also long enough.",
        examples_md="Integration examples body — final section, also long.",
        quiz_items=[
            GeneratedQuizItem(
                question="Q?", answer="A", question_type="recall", difficulty="medium"
            ),
        ],
    )


def _critique() -> CritiqueSchema:
    return CritiqueSchema(
        verdict="PASS",
        dimensions=[
            CritiqueDimension(name="accuracy", score=5, rationale="ok"),
        ],
        rationale="integration PASS",
    )


def _patch_session_factory(db_session):
    """Reuse the test's `db_session` and shim `commit` to `flush` so the
    fixture rollback teardown can undo the worker's writes (otherwise
    repeated runs leak rows between tests / across files)."""
    original_commit = db_session.commit

    async def _flush_only():
        await db_session.flush()

    db_session.commit = _flush_only

    class _CM:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_a):
            db_session.commit = original_commit
            return False

    factory = MagicMock(return_value=_CM())
    return patch.object(ingestion_worker, "_get_session_factory", return_value=factory)


async def _create_admin(db) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"admin-{uuid.uuid4()}@integ-ingest.com",
        name="Integration Admin",
        role="admin",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def test_enqueue_to_completion_round_trip_lands_drafts(db_session):
    """Enqueue → worker → drafts on disk; lesson `published_at IS NULL`."""
    admin = await _create_admin(db_session)
    storage = _make_storage_mock()
    queue = _make_queue_mock()

    payload = IngestionJobCreateRequest(
        source_text="# Source\n\n"
        + ("Integration test source body that is sufficiently long. " * 5),
        target_deck_slug="integ-deck",
    )
    response = await ingestion_service.enqueue_ingestion(
        payload, db_session, admin=admin, storage=storage, queue=queue,
    )

    assert response.status == "pending"
    assert queue.enqueue.call_count == 1

    def _fake_generate(task, **kwargs):
        if kwargs.get("provider_override") == "anthropic":
            return _critique().model_dump_json()
        return _gen().model_dump_json()

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
    ):
        await ingestion_worker._run_ingestion_async(response.job_id)

    job = (
        await db_session.execute(
            select(IngestionJob).where(IngestionJob.id == response.job_id)
        )
    ).scalar_one()
    assert job.status == "completed"
    assert job.critique_verdict == "PASS"
    assert job.completed_at is not None

    deck = (
        await db_session.execute(select(Deck).where(Deck.slug == "integ-deck"))
    ).scalar_one()
    lessons = (
        await db_session.execute(select(Lesson).where(Lesson.deck_id == deck.id))
    ).scalars().all()
    assert len(lessons) == 1
    assert lessons[0].published_at is None  # drafts only per G-6 + D-7
    quiz_items = (
        await db_session.execute(
            select(QuizItem).where(QuizItem.lesson_id == lessons[0].id)
        )
    ).scalars().all()
    assert len(quiz_items) == 1


async def test_cross_model_dispatch_routes_critique_to_anthropic(db_session):
    """Stage 2 critique must arrive with `provider_override='anthropic'`."""
    admin = await _create_admin(db_session)
    storage = _make_storage_mock()

    job = IngestionJob(
        id=str(uuid.uuid4()),
        status="pending",
        source_format="markdown",
        source_content_sha256="0" * 64,
        source_r2_key=f"ingestion/{uuid.uuid4()}/source.md",
        created_by_user_id=admin.id,
    )
    db_session.add(job)
    await db_session.flush()

    captured: list[dict] = []

    def _fake_generate(task, **kwargs):
        captured.append({"task": task, "provider_override": kwargs.get("provider_override")})
        if kwargs.get("provider_override") == "anthropic":
            return _critique().model_dump_json()
        return _gen().model_dump_json()

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    # Stage 1 must NOT pass provider_override; Stage 2 must.
    assert any(c["provider_override"] is None for c in captured), captured
    assert any(c["provider_override"] == "anthropic" for c in captured), captured
