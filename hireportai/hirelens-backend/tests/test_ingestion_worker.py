"""Ingestion worker tests (Phase 6 slice 6.10b — B-083b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §10.2 + §11
AC-7 / AC-8 / AC-9 / AC-10 / AC-13 / AC-19.

Mocks: `generate_for_task` (per-stage) + `ObjectStorageService.put_object`
+ `get_object`. Uses real DB + real slice 6.4b admin services per
mock-strategy in the prompt body (§10.2 single-source-of-truth rule).

The worker's `run_ingestion(job_id)` is sync; we call the inner async
helper `_run_ingestion_async` directly so each test runs inside the
shared session-loop fixture without spawning a fresh `asyncio.run` loop.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Helpers ────────────────────────────────────────────────────────────────
SAMPLE_SOURCE_BYTES = b"# Source markdown\n\nSome ingestable lesson content.\n"


def _gen_payload(*, slug: str = "ingest-quiz") -> LessonGenSchema:
    return LessonGenSchema(
        target_deck_slug="ingest-deck",
        lesson_slug=slug,
        title="Sample Generated Lesson",
        concept_md="## Concept\n\nGenerated concept body.",
        production_md="## Production\n\nGenerated production body.",
        examples_md="## Examples\n\nGenerated examples body.",
        quiz_items=[
            GeneratedQuizItem(
                question="Q1?", answer="A1", question_type="recall", difficulty="easy"
            ),
            GeneratedQuizItem(
                question="Q2?",
                answer="A2",
                question_type="application",
                difficulty="medium",
            ),
        ],
    )


def _critique_pass() -> CritiqueSchema:
    return CritiqueSchema(
        verdict="PASS",
        dimensions=[
            CritiqueDimension(name="accuracy", score=5, rationale="ok"),
            CritiqueDimension(name="clarity", score=5, rationale="ok"),
            CritiqueDimension(name="completeness", score=4, rationale="ok"),
            CritiqueDimension(name="cohesion", score=5, rationale="ok"),
        ],
        rationale="overall PASS",
    )


def _critique_fail() -> CritiqueSchema:
    return CritiqueSchema(
        verdict="FAIL",
        dimensions=[
            CritiqueDimension(name="accuracy", score=1, rationale="hallucinated"),
        ],
        rationale="critical hallucination — reject",
    )


async def _create_admin(db) -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"admin-{uuid.uuid4()}@worker-test.com",
        name="Worker Test Admin",
        role="admin",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_job(db, admin: User) -> IngestionJob:
    job = IngestionJob(
        id=str(uuid.uuid4()),
        status="pending",
        source_format="markdown",
        source_content_sha256="0" * 64,
        source_r2_key=f"ingestion/{uuid.uuid4()}/source.md",
        created_by_user_id=admin.id,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


def _make_storage_mock() -> MagicMock:
    storage = MagicMock()
    storage.put_object = MagicMock(return_value="s3://bucket/key")
    storage.get_object = MagicMock(return_value=SAMPLE_SOURCE_BYTES)
    return storage


def _patch_session_factory(db_session):
    """Force the worker to reuse the test's `db_session` instead of opening
    a fresh worker session.

    `_run_ingestion_async` does `async with factory() as db: …`. We make
    the factory return an async-context-manager whose `__aenter__` yields
    the test session and whose `__aexit__` is a no-op. The worker's
    `db.commit()` calls would normally land data permanently in the test
    DB; we shim `commit` to `flush` so the writes are visible inside the
    test but get rolled back by the `db_session` fixture teardown.
    """
    original_commit = db_session.commit

    async def _flush_only():
        await db_session.flush()

    db_session.commit = _flush_only  # restored below

    class _CM:
        async def __aenter__(self_inner):
            return db_session

        async def __aexit__(self_inner, *_a):
            db_session.commit = original_commit
            return False

    factory = MagicMock(return_value=_CM())
    return patch.object(ingestion_worker, "_get_session_factory", return_value=factory)


# ── AC-9 + AC-13 — happy path ──────────────────────────────────────────────
async def test_happy_path_generates_drafts_and_marks_completed(db_session):
    admin = await _create_admin(db_session)
    job = await _create_job(db_session, admin)
    storage = _make_storage_mock()
    captured_events: list[tuple[str, str, dict]] = []

    def _track(user_id, event, properties=None):
        captured_events.append((user_id, event, properties or {}))

    gen = _gen_payload()
    crit = _critique_pass()

    def _fake_generate(task, **kwargs):
        if "provider_override" in kwargs and kwargs.get("provider_override") == "anthropic":
            return crit.model_dump_json()
        return gen.model_dump_json()

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
        patch.object(ingestion_worker, "analytics_track", side_effect=_track),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    # Re-fetch to pick up worker writes.
    await db_session.refresh(job)
    assert job.status == "completed"
    assert job.critique_verdict == "PASS"
    assert job.generated_quiz_item_count == 2
    assert job.target_deck_id is not None
    assert job.draft_r2_key is not None
    assert job.critique_r2_key is not None

    # Lesson + quiz items landed via slice 6.4b admin services as drafts
    # (`published_at IS NULL` per G-6 + D-7).
    deck = (
        await db_session.execute(select(Deck).where(Deck.id == job.target_deck_id))
    ).scalar_one()
    assert deck.slug == gen.target_deck_slug
    lessons = (
        await db_session.execute(select(Lesson).where(Lesson.deck_id == deck.id))
    ).scalars().all()
    assert len(lessons) == 1
    assert lessons[0].published_at is None  # drafts only
    quiz_items = (
        await db_session.execute(
            select(QuizItem).where(QuizItem.lesson_id == lessons[0].id)
        )
    ).scalars().all()
    assert len(quiz_items) == 2

    # `ingestion_job_completed` event fired with internal: true.
    completed_events = [
        evt for _u, name, evt in captured_events if name == "ingestion_job_completed"
    ]
    assert len(completed_events) == 1
    assert completed_events[0]["internal"] is True
    assert completed_events[0]["job_id"] == job.id


# ── AC-8 — critique=FAIL short-circuits Stage 3 ────────────────────────────
async def test_critique_fail_marks_failed_without_persisting_lesson(db_session):
    admin = await _create_admin(db_session)
    job = await _create_job(db_session, admin)
    storage = _make_storage_mock()
    captured_events: list[tuple[str, str, dict]] = []

    def _fake_generate(task, **kwargs):
        if kwargs.get("provider_override") == "anthropic":
            return _critique_fail().model_dump_json()
        return _gen_payload().model_dump_json()

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
        patch.object(
            ingestion_worker,
            "analytics_track",
            side_effect=lambda u, e, p=None: captured_events.append((u, e, p or {})),
        ),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    await db_session.refresh(job)
    assert job.status == "failed"
    assert job.critique_verdict == "FAIL"
    assert "FAIL" in (job.error_message or "")

    # No lesson rows landed.
    lessons = (await db_session.execute(select(Lesson))).scalars().all()
    assert all(lesson.deck_id != (job.target_deck_id or "") for lesson in lessons) or not lessons

    failed_events = [
        evt for _u, name, evt in captured_events if name == "ingestion_job_failed"
    ]
    assert len(failed_events) == 1
    assert failed_events[0]["stage"] == "critique"
    assert failed_events[0]["error_class"] == "critique_fail"


# ── AC-7 — gen-stage exhausted retry budget ────────────────────────────────
async def test_gen_stage_failure_after_three_attempts_marks_failed(db_session):
    admin = await _create_admin(db_session)
    job = await _create_job(db_session, admin)
    storage = _make_storage_mock()
    captured_events: list[tuple[str, str, dict]] = []

    call_count = {"n": 0}

    def _fake_generate(task, **kwargs):
        call_count["n"] += 1
        raise RuntimeError("simulated Gemini 5xx")

    # No real sleeps — patch asyncio.sleep with an async no-op.
    async def _no_sleep(_seconds):
        return None

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
        patch.object(ingestion_worker.asyncio, "sleep", new=_no_sleep),
        patch.object(
            ingestion_worker,
            "analytics_track",
            side_effect=lambda u, e, p=None: captured_events.append((u, e, p or {})),
        ),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    await db_session.refresh(job)
    assert job.status == "failed"
    assert call_count["n"] == 3  # three attempts, then terminal
    assert "gen stage exhausted" in (job.error_message or "")
    failed_events = [
        evt for _u, name, evt in captured_events if name == "ingestion_job_failed"
    ]
    assert len(failed_events) == 1
    assert failed_events[0]["stage"] == "gen"


# ── AC-7 (critique branch) — critique-stage exhausted ──────────────────────
async def test_critique_stage_failure_after_three_attempts_marks_failed(db_session):
    admin = await _create_admin(db_session)
    job = await _create_job(db_session, admin)
    storage = _make_storage_mock()

    critique_calls = {"n": 0}

    def _fake_generate(task, **kwargs):
        if kwargs.get("provider_override") == "anthropic":
            critique_calls["n"] += 1
            raise RuntimeError("simulated Anthropic 5xx")
        return _gen_payload().model_dump_json()

    async def _no_sleep(_seconds):
        return None

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
        patch.object(ingestion_worker.asyncio, "sleep", new=_no_sleep),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    await db_session.refresh(job)
    assert job.status == "failed"
    assert critique_calls["n"] == 3
    assert "critique stage exhausted" in (job.error_message or "")


# ── AC-7 — invalid-JSON output retried like a 5xx ──────────────────────────
async def test_invalid_gen_json_retried_three_times_then_fails(db_session):
    admin = await _create_admin(db_session)
    job = await _create_job(db_session, admin)
    storage = _make_storage_mock()

    call_count = {"n": 0}

    def _fake_generate(task, **kwargs):
        call_count["n"] += 1
        return "{not-json}"

    async def _no_sleep(_seconds):
        return None

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
        patch.object(ingestion_worker.asyncio, "sleep", new=_no_sleep),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    await db_session.refresh(job)
    assert job.status == "failed"
    assert call_count["n"] == 3


# ── AC-19 — terminal state is exactly one of {completed, failed} ───────────
async def test_terminal_state_is_completed_on_happy_path(db_session):
    admin = await _create_admin(db_session)
    job = await _create_job(db_session, admin)
    storage = _make_storage_mock()

    gen = _gen_payload(slug="terminal-quiz")

    def _fake_generate(task, **kwargs):
        if kwargs.get("provider_override") == "anthropic":
            return _critique_pass().model_dump_json()
        return gen.model_dump_json()

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    await db_session.refresh(job)
    assert job.status in {"completed", "failed"}
    assert job.status == "completed"
    assert job.completed_at is not None


# ── AC-13 — admin attribution flows through to admin_audit_log via service
# calls. Verified by emitted analytics events carrying admin_id == job.created_by.
async def test_admin_attribution_threads_through_to_admin_lesson_event(db_session):
    admin = await _create_admin(db_session)
    job = await _create_job(db_session, admin)
    storage = _make_storage_mock()

    captured: list[tuple[str, str, dict]] = []
    real_track = AsyncMock()

    def _fake_generate(task, **kwargs):
        if kwargs.get("provider_override") == "anthropic":
            return _critique_pass().model_dump_json()
        return _gen_payload(slug="attr-quiz").model_dump_json()

    # Mirror the lesson_admin_service track call site so we can verify the
    # admin_id lands on the cascade events.
    def _spy_track(user_id, event, properties=None):
        captured.append((user_id, event, properties or {}))

    with (
        _patch_session_factory(db_session),
        patch.object(ingestion_worker, "get_storage", return_value=storage),
        patch.object(
            ingestion_worker, "generate_for_task", side_effect=_fake_generate
        ),
        patch("app.services.lesson_admin_service.analytics_track", side_effect=_spy_track),
        patch("app.services.quiz_item_admin_service.analytics_track", side_effect=_spy_track),
        patch("app.services.deck_admin_service.analytics_track", side_effect=_spy_track),
    ):
        await ingestion_worker._run_ingestion_async(job.id)

    # All admin-side events must carry the orchestrating admin's user_id.
    assert all(uid == admin.id for uid, _e, _p in captured)
    # At least one admin_lesson_created event fired against this admin.
    lesson_events = [p for _u, e, p in captured if e == "admin_lesson_created"]
    assert len(lesson_events) == 1
    assert lesson_events[0]["admin_id"] == admin.id


# Use json import so it isn't pruned — the fake generators return JSON
# strings serialized via Pydantic, but several future test additions will
# build payloads inline; keep it imported for stability.
_ = json
