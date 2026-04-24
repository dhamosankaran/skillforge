"""Spec #52 (B-002) — cover letter format enforcement, backend tests.

Slice 1 covers: AC-1, AC-2, AC-3, AC-4a, AC-5, AC-7.
Slice 2 adds:   AC-4b (integration_llm marker), telemetry (spec §9).

Live-LLM AC-4b is gated behind `@pytest.mark.integration_llm` and only
runs locally with a GEMINI_API_KEY. CI deselects it via the marker set.
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes.cover_letter import router as cover_letter_router
from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.responses import CoverLetterRecipient, CoverLetterResponse
from app.services.gpt_service import (
    CoverLetterError,
    _CoverLetterCore,
    _extract_candidate_name,
    _join_cover_letter,
    generate_cover_letter,
)


class _FakeUser:
    """Minimal stand-in for app.models.user.User — the cover-letter route
    only reads `id` off the Depends(get_current_user) return value."""
    id = "test-user-id"


async def _fake_user():
    return _FakeUser()


async def _fake_db():
    # The route's `check_and_increment` is patched to a no-op via
    # `_bypass_quota()` below, so the db session it gets is never queried.
    yield None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_LLM_PAYLOAD = {
    "date": "April 21, 2026",
    "recipient": {"name": "Hiring Manager", "company": "Acme Robotics"},
    "greeting": "Dear Hiring Manager,",
    "body_paragraphs": [
        "I am writing to apply for the Staff Software Engineer role at Acme Robotics. "
        "Your focus on reliability at scale resonates with my decade of work on async pipelines.",
        "In my most recent role I led a 40% reduction in P50 latency by redesigning our "
        "async pipeline. I also mentored four engineers through the senior ladder.",
        "I would welcome the chance to discuss how my experience maps to your roadmap. "
        "Thank you for your time and consideration.",
    ],
    "signoff": "Sincerely,",
    "signature": "Jordan Doe",
}


def _resume(marker: str = "ZZZ-UNIQUE-MARKER") -> str:
    return (
        "Jordan Doe\n"
        "jordan@example.com | (555) 123-4567 | San Francisco, CA\n\n"
        "Summary\n"
        f"Senior software engineer. {marker}. "
        + ("Shipped resilient distributed systems. " * 80)
    )[:5000]


def _jd() -> dict:
    return {
        "job_title": "Staff Software Engineer",
        "full_text": "We're hiring at Acme Robotics for a staff role leading platform.",
        "company_name": "Acme Robotics",
        "all_skills": ["python", "kubernetes"],
        "missing_keywords": ["python", "kubernetes"],
    }


def _fake_llm(payload: dict):
    """Return a side_effect that records the call and emits JSON text."""
    captured: dict = {}

    def side_effect(*, task, prompt, **kwargs):
        captured["task"] = task
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return json.dumps(payload)

    return side_effect, captured


def _app_with_cover_letter_route() -> FastAPI:
    """Mini-app exercising the cover-letter route in isolation.

    Spec #58 added `Depends(get_current_user)` + quota enforcement; these
    route-format tests exercise the 200 / 502 / validation paths downstream
    of the gate, so we override both dependencies with fakes and stub
    `check_and_increment` via the `_bypass_quota` context manager at each
    call site.
    """
    app = FastAPI()
    app.include_router(cover_letter_router, prefix="/api")
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_db] = _fake_db
    return app


@pytest.fixture(autouse=True)
def _bypass_quota():
    """Stub the spec #58 quota gate so format / 502 tests reach the service
    layer. Real quota behavior is covered by `tests/test_rewrite_quota.py`."""
    async def _allowed(*args, **kwargs):
        return {
            "allowed": True,
            "used": 0,
            "remaining": -1,
            "limit": -1,
            "plan": "pro",
        }

    with patch(
        "app.api.routes.cover_letter.check_and_increment",
        side_effect=_allowed,
    ):
        yield


# ---------------------------------------------------------------------------
# AC-1 — all 8 canonical blocks present, in order, in full_text
# ---------------------------------------------------------------------------

def test_ac1_all_eight_blocks_present_in_order():
    """AC-1: date, recipient.name ('Hiring Manager' literal), recipient.company,
    greeting, 3 body_paragraphs, signoff, signature all populated; full_text
    serializes them in order."""
    side_effect, _ = _fake_llm(VALID_LLM_PAYLOAD)
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=side_effect,
    ):
        result = generate_cover_letter(
            {"full_text": _resume()}, _jd(), tone="professional"
        )

    assert isinstance(result, CoverLetterResponse)
    assert result.date == "April 21, 2026"
    assert result.recipient.name == "Hiring Manager"
    assert result.recipient.company == "Acme Robotics"
    assert result.greeting == "Dear Hiring Manager,"
    assert len(result.body_paragraphs) == 3
    assert result.signoff == "Sincerely,"
    assert result.signature == "Jordan Doe"
    assert result.tone == "professional"
    assert result.full_text  # populated

    # Block order: date → recipient → greeting → body[0..2] → signoff → signature.
    full = result.full_text
    idx_date = full.index(result.date)
    idx_company = full.index(result.recipient.company)
    idx_greet = full.index(result.greeting)
    idx_b0 = full.index(result.body_paragraphs[0])
    idx_b1 = full.index(result.body_paragraphs[1])
    idx_b2 = full.index(result.body_paragraphs[2])
    idx_signoff = full.index(result.signoff)
    idx_sig = full.rindex(result.signature)
    assert idx_date < idx_company < idx_greet < idx_b0 < idx_b1 < idx_b2 < idx_signoff < idx_sig


# ---------------------------------------------------------------------------
# AC-2 — Pydantic rejects body_paragraphs length != 3
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_paragraphs", [
    [],
    ["only one"],
    ["one", "two"],
    ["one", "two", "three", "four"],
])
def test_ac2_body_paragraphs_length_rejected_by_pydantic(bad_paragraphs):
    """AC-2: the LD-2 shape locks body_paragraphs to exactly 3. Pydantic
    rejects 0/1/2/4 at construction time. The service catches
    ValidationError and raises cover_letter_validation_error (covered in
    test_ac5_validation_error_returns_502)."""
    with pytest.raises(ValidationError):
        CoverLetterResponse(
            date="April 21, 2026",
            recipient=CoverLetterRecipient(name="Hiring Manager", company="Acme"),
            greeting="Dear Hiring Manager,",
            body_paragraphs=bad_paragraphs,
            signoff="Sincerely,",
            signature="Jordan Doe",
            tone="professional",
            full_text="irrelevant",
        )


# ---------------------------------------------------------------------------
# AC-3 — full_text matches canonical join byte-for-byte
# ---------------------------------------------------------------------------

def test_ac3_full_text_join_format_byte_for_byte():
    """AC-3: full_text equals the canonical server-side join:
        {date}

        Hiring Manager
        {recipient.company}

        {greeting}

        {body[0]}

        {body[1]}

        {body[2]}

        {signoff}
        {signature}
    Blank lines between blocks; signoff → signature single-newline.
    """
    core = _CoverLetterCore(
        date="April 21, 2026",
        recipient=CoverLetterRecipient(name="Hiring Manager", company="Acme Robotics"),
        greeting="Dear Hiring Manager,",
        body_paragraphs=["HOOK BLOCK.", "FIT BLOCK.", "CLOSE BLOCK."],
        signoff="Sincerely,",
        signature="Jordan Doe",
    )
    expected = (
        "April 21, 2026\n\n"
        "Hiring Manager\nAcme Robotics\n\n"
        "Dear Hiring Manager,\n\n"
        "HOOK BLOCK.\n\n"
        "FIT BLOCK.\n\n"
        "CLOSE BLOCK.\n\n"
        "Sincerely,\nJordan Doe"
    )
    assert _join_cover_letter(core) == expected


# ---------------------------------------------------------------------------
# AC-4a — tone flows verbatim into the prompt (3 spec tones)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tone", ["professional", "confident", "conversational"])
def test_ac4a_tone_parameter_reaches_prompt(tone):
    """AC-4a: the tone value passed in the request appears verbatim
    (`Tone: {tone}`) inside the prompt handed to the LLM router. Mock-only."""
    side_effect, captured = _fake_llm(VALID_LLM_PAYLOAD)
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=side_effect,
    ):
        generate_cover_letter({"full_text": _resume()}, _jd(), tone=tone)

    assert captured["task"] == "cover_letter"
    assert f"Tone: {tone}" in captured["prompt"]


# ── B-021 — company_name from jd_requirements reaches the prompt ──────────


@pytest.mark.parametrize("tone", ["professional", "confident", "conversational"])
def test_b021_company_name_flows_from_jd_requirements_into_prompt(tone):
    """B-021: when jd_requirements has a company_name, the cover-letter
    prompt uses it (not the "your company" fallback). Tone-agnostic —
    the bug was reported as tone-specific but the root cause spans all
    three tones."""
    side_effect, captured = _fake_llm(VALID_LLM_PAYLOAD)
    jd = {**_jd(), "company_name": "Acme Robotics"}
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=side_effect,
    ):
        generate_cover_letter({"full_text": _resume()}, jd, tone=tone)

    prompt = captured["prompt"]
    assert "\"company\" must be \"Acme Robotics\"" in prompt
    # Regression guard: fallback must not appear once a real name is set.
    assert "\"company\" must be \"your company\"" not in prompt


def test_b021_company_name_missing_falls_back_to_placeholder():
    """B-021: when jd_requirements omits company_name, the fallback
    "your company" stays intact (silent-miss behaviour of the heuristic
    extractor in nlp.py is benign at this call site)."""
    side_effect, captured = _fake_llm(VALID_LLM_PAYLOAD)
    jd = {**_jd()}
    jd.pop("company_name", None)
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=side_effect,
    ):
        generate_cover_letter({"full_text": _resume()}, jd, tone="conversational")

    assert "\"company\" must be \"your company\"" in captured["prompt"]


# ---------------------------------------------------------------------------
# AC-5 — four failure modes → 502 with spec envelope
# ---------------------------------------------------------------------------

def _post_cover_letter(client: TestClient) -> "object":
    return client.post(
        "/api/cover-letter",
        json={
            "resume_text": _resume(),
            "job_description": (
                "Acme Robotics is hiring a Staff Software Engineer to lead platform. "
                "We want Python, Kubernetes, and distributed systems experience."
            ),
            "tone": "professional",
        },
    )


def test_ac5_truncated_empty_response_returns_502():
    """AC-5: empty LLM output (finish_reason MAX_TOKENS or safety block)
    surfaces as cover_letter_truncated under the spec envelope."""
    app = _app_with_cover_letter_route()
    with patch(
        "app.services.gpt_service.generate_for_task",
        return_value="   \n",  # whitespace only
    ):
        response = _post_cover_letter(TestClient(app))
    assert response.status_code == 502
    body = response.json()
    assert body["detail"]["error"] == "cover_letter_truncated"
    assert "message" in body["detail"]
    assert body["detail"]["retry_hint"] == "retry"


def test_ac5_malformed_json_returns_502():
    """AC-5: non-JSON LLM output surfaces as cover_letter_parse_error."""
    app = _app_with_cover_letter_route()
    with patch(
        "app.services.gpt_service.generate_for_task",
        return_value="this is not JSON { oops",
    ):
        response = _post_cover_letter(TestClient(app))
    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "cover_letter_parse_error"


def test_ac5_validation_error_returns_502():
    """AC-5: JSON with body_paragraphs length != 3 fails Pydantic, surfaces
    as cover_letter_validation_error."""
    app = _app_with_cover_letter_route()
    bad_payload = {**VALID_LLM_PAYLOAD, "body_paragraphs": ["only", "two"]}
    with patch(
        "app.services.gpt_service.generate_for_task",
        return_value=json.dumps(bad_payload),
    ):
        response = _post_cover_letter(TestClient(app))
    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "cover_letter_validation_error"


def test_ac5_llm_exception_returns_502():
    """AC-5: upstream router/provider exception surfaces as
    cover_letter_llm_error (not a 500, not a silent fallback)."""
    app = _app_with_cover_letter_route()
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=RuntimeError("gemini upstream 503"),
    ):
        response = _post_cover_letter(TestClient(app))
    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "cover_letter_llm_error"


# ---------------------------------------------------------------------------
# AC-7 — thinking_budget=2000 on the router call
# ---------------------------------------------------------------------------

def test_ac7_thinking_budget_2000_applied():
    """AC-7: generate_for_task is invoked with thinking_budget=2000 per
    spec #52 LD-5 (cheap insurance against Gemini 2.5 Pro's thinking pool
    starving the output pool)."""
    side_effect, captured = _fake_llm(VALID_LLM_PAYLOAD)
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=side_effect,
    ):
        generate_cover_letter({"full_text": _resume()}, _jd(), tone="professional")

    assert captured["kwargs"].get("thinking_budget") == 2000
    assert captured["kwargs"].get("json_mode") is True


# ---------------------------------------------------------------------------
# Telemetry (spec #52 §9) — cover_letter_succeeded / cover_letter_failed
# ---------------------------------------------------------------------------

def test_telemetry_succeeded_fires_with_spec_payload():
    """Spec §9: cover_letter_succeeded fires on 200 with
    {tone, body_paragraphs_count, model_used}. The legacy
    cover_letter_generated event is no longer emitted."""
    app = _app_with_cover_letter_route()
    with patch(
        "app.services.gpt_service.generate_for_task",
        return_value=json.dumps(VALID_LLM_PAYLOAD),
    ), patch("app.api.routes.cover_letter.analytics_track") as tracked:
        response = _post_cover_letter(TestClient(app))

    assert response.status_code == 200
    events = [call.kwargs["event"] for call in tracked.call_args_list]
    assert "cover_letter_succeeded" in events
    assert "cover_letter_generated" not in events

    succeeded = next(
        c for c in tracked.call_args_list if c.kwargs["event"] == "cover_letter_succeeded"
    )
    props = succeeded.kwargs["properties"]
    assert props["tone"] == "professional"
    assert props["body_paragraphs_count"] == 3
    assert isinstance(props["model_used"], str) and props["model_used"]


@pytest.mark.parametrize("fake, expected_code", [
    ("   \n", "cover_letter_truncated"),
    ("not json {", "cover_letter_parse_error"),
    (json.dumps({**VALID_LLM_PAYLOAD, "body_paragraphs": ["only", "two"]}),
     "cover_letter_validation_error"),
])
def test_telemetry_failed_fires_with_error_code(fake, expected_code):
    """Spec §9: cover_letter_failed fires on 502 paths with {error_code, tone}."""
    app = _app_with_cover_letter_route()
    with patch(
        "app.services.gpt_service.generate_for_task",
        return_value=fake,
    ), patch("app.api.routes.cover_letter.analytics_track") as tracked:
        response = _post_cover_letter(TestClient(app))

    assert response.status_code == 502
    failed = [c for c in tracked.call_args_list if c.kwargs["event"] == "cover_letter_failed"]
    assert len(failed) == 1
    props = failed[0].kwargs["properties"]
    assert props["error_code"] == expected_code
    assert props["tone"] == "professional"


def test_telemetry_failed_fires_on_llm_exception():
    """Spec §9: llm_error path also fires cover_letter_failed."""
    app = _app_with_cover_letter_route()
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=RuntimeError("gemini upstream 503"),
    ), patch("app.api.routes.cover_letter.analytics_track") as tracked:
        response = _post_cover_letter(TestClient(app))

    assert response.status_code == 502
    failed = [c for c in tracked.call_args_list if c.kwargs["event"] == "cover_letter_failed"]
    assert len(failed) == 1
    assert failed[0].kwargs["properties"]["error_code"] == "cover_letter_llm_error"


# ---------------------------------------------------------------------------
# AC-4b — live-LLM tone differentiation, integration_llm marker
# ---------------------------------------------------------------------------

# ── B-023 — candidate-name extractor rejects all-caps section headers ──
#
# Observed artifact (2026-04-22): cover-letter output rendered "KEY
# ACHIEVEMENTS" after "Sincerely," — `_extract_candidate_name` walked the
# first 10 resume lines, didn't find the candidate's name, and returned a
# section header because `^[A-Z][A-Za-z.'-]+$` happily accepts all-caps
# tokens. The header got interpolated into the prompt as the signature
# field, the LLM dutifully echoed it, and `_join_cover_letter` rendered
# it unchanged. Fix: skip pure-uppercase lines before the token-regex
# check. Human names capitalize the first letter per token, not every
# letter — a legitimate candidate-name line is never pure-uppercase.


@pytest.mark.parametrize("name", [
    "Jordan Doe",
    "Dhamo Sankaran",
    "Mary-Kate O'Neill",
    "Alice Johnson",
    "Dr. Alice Johnson",
    "Jean-Luc Picard",
])
def test_b023_extract_candidate_name_accepts_real_mixed_case_names(name):
    """Positives: real human names still resolve to the line verbatim."""
    resume = f"{name}\nalice@example.com | (555) 123-4567\n\nSummary\n..."
    assert _extract_candidate_name(resume) == name


@pytest.mark.parametrize("header", [
    "KEY ACHIEVEMENTS",
    "PROFESSIONAL SUMMARY",
    "WORK EXPERIENCE",
    "EDUCATION",
])
def test_b023_extract_candidate_name_rejects_all_caps_section_headers(header):
    """Negatives: all-caps resume section headers must not be returned as
    the candidate's name. Before B-023, "KEY ACHIEVEMENTS" would leak into
    the cover-letter signature slot and render "Sincerely,\\nKEY ACHIEVEMENTS".
    After the guard, the fallback "The Applicant" stands.
    """
    # Header at the top with no real name anywhere in the first 10 lines.
    resume = f"{header}\n- Led platform reliability initiative\n- Reduced P50 by 40%"
    assert _extract_candidate_name(resume) == "The Applicant"


def test_b023_extract_candidate_name_skips_header_finds_real_name_below():
    """Defense-in-depth: when a section header precedes the real name in
    the first 10 lines, the helper skips the header and returns the name.
    """
    resume = (
        "PROFESSIONAL SUMMARY\n"
        "Alice Johnson\n"
        "alice@example.com\n"
    )
    assert _extract_candidate_name(resume) == "Alice Johnson"


def test_b023_extract_candidate_name_blank_resume_falls_back():
    """Fallback: empty or no-match resume text yields "The Applicant"."""
    assert _extract_candidate_name("") == "The Applicant"
    assert _extract_candidate_name("   \n\t  \n") == "The Applicant"


@pytest.mark.integration_llm
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY required for live-LLM AC-4b test",
)
def test_ac4b_live_llm_returns_structured_cover_letter():
    """AC-4b: real Gemini call returns a structurally-valid cover letter
    (all 8 blocks populated, body_paragraphs length 3, tone echoed). Run
    locally pre-merge with `pytest -m integration_llm`. Deselected in CI
    via `-m "not integration and not integration_llm"` in the default
    invocation per spec §8.1 marker registration.

    Full tone-differentiation via Jaccard word-overlap is deferred to a
    follow-up slice so the marker surface lands green on local runs
    regardless of cross-tone API cost.
    """
    resume = (
        "Jordan Doe\n"
        "jordan@example.com | (555) 123-4567 | San Francisco, CA\n\n"
        "Summary\nSenior platform engineer with a decade of distributed-systems work.\n\n"
        "Experience\nStaff Engineer at Example Corp — led async pipeline redesign, "
        "40% P50 latency reduction, mentored 4 engineers to senior.\n"
    )
    jd_req = {
        "job_title": "Staff Software Engineer",
        "full_text": (
            "Acme Robotics is hiring a Staff Software Engineer to lead platform "
            "reliability. Python, Kubernetes, async systems experience required."
        ),
        "company_name": "Acme Robotics",
        "all_skills": ["python", "kubernetes"],
        "missing_keywords": ["python", "kubernetes"],
    }

    result = generate_cover_letter(
        {"full_text": resume}, jd_req, tone="professional"
    )
    assert isinstance(result, CoverLetterResponse)
    assert result.date
    assert result.recipient.name == "Hiring Manager"
    assert result.recipient.company
    assert result.greeting
    assert len(result.body_paragraphs) == 3
    assert all(p.strip() for p in result.body_paragraphs)
    assert result.signoff
    assert result.signature
    assert result.tone == "professional"
    assert result.full_text
