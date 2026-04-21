"""Spec #52 (B-002) — cover letter format enforcement, backend slice 1/2.

Covers acceptance criteria from the spec's §4:
  AC-1  all 8 canonical blocks present, in order, inside full_text
  AC-2  Pydantic rejects body_paragraphs of length != 3
  AC-3  full_text equals the canonical server-side join, byte-for-byte
  AC-4a tone value flows verbatim into the LLM prompt (mocked)
  AC-5  four failure modes each raise CoverLetterError and surface
        through the route as HTTP 502 with the spec §LD-6 envelope
  AC-7  generate_for_task is invoked with thinking_budget=2000

Slice 1 is backend-only. FE consumer migration and AC-4b (live-LLM tone
differentiation behind @pytest.mark.integration_llm) land in slice 2.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes.cover_letter import router as cover_letter_router
from app.schemas.responses import CoverLetterRecipient, CoverLetterResponse
from app.services.gpt_service import (
    CoverLetterError,
    _CoverLetterCore,
    _join_cover_letter,
    generate_cover_letter,
)


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
    app = FastAPI()
    app.include_router(cover_letter_router, prefix="/api")
    return app


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
