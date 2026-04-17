"""Regression tests for P5-S10: cover letter must be emitted in traditional
business-letter format — no ## headers, explicit "Dear" greeting, explicit
"Sincerely" sign-off, the selected tone wired into the prompt, and the full
(untruncated) resume reaching the LLM.
"""
from __future__ import annotations

from unittest.mock import patch

from app.services.gpt_service import generate_cover_letter


UNIQUE_RESUME_MARKER = "ZZZ-UNIQUE-RESUME-MARKER-9f3e"


def _build_resume(chars_target: int = 12_000) -> str:
    base = (
        "Jordan Doe\n"
        "jordan@example.com | (555) 123-4567 | San Francisco, CA\n\n"
        "## Summary\n"
        "Senior software engineer with a decade of experience shipping "
        "resilient distributed systems. "
        f"{UNIQUE_RESUME_MARKER} "
    )
    filler = (
        "Led cross-functional initiatives that moved key reliability and "
        "productivity metrics by double-digit percentages while mentoring "
        "mid-career engineers. "
    )
    # Pad up to target length
    padded = base + (filler * ((chars_target // len(filler)) + 1))
    return padded[:chars_target]


def _jd_requirements() -> dict:
    return {
        "job_title": "Staff Software Engineer",
        "full_text": "We're hiring at Acme Robotics for a staff role leading platform.",
        "company_name": "Acme Robotics",
        "all_skills": ["python", "kubernetes"],
        "missing_keywords": ["python", "kubernetes"],
    }


def test_cover_letter_prompt_enforces_business_letter_format():
    """The prompt sent to the LLM must forbid markdown headers, include the
    greeting/sign-off tokens, carry the selected tone, and contain the full
    resume text uncut."""
    resume_text = _build_resume(12_000)
    resume_data = {"full_text": resume_text}
    jd = _jd_requirements()

    captured = {}

    def fake_generate(*, task, prompt, **kwargs):
        captured["task"] = task
        captured["prompt"] = prompt
        captured["max_tokens"] = kwargs.get("max_tokens")
        return "unused — assertions are on the prompt"

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_generate,
    ):
        generate_cover_letter(resume_data, jd, tone="conversational")

    assert captured["task"] == "cover_letter"
    prompt = captured["prompt"]

    # (a) No-headers rule must be explicit in the prompt.
    assert "Do NOT use markdown headers" in prompt, (
        "Prompt must forbid ## headers; this is the P5-S10 regression guard."
    )
    # And the old labels must be named as things to avoid.
    for forbidden_label in ("Opening", "Why I'm a Fit", "Key Achievement", "Closing"):
        assert forbidden_label in prompt, (
            f"Prompt should explicitly instruct the LLM NOT to label "
            f"sections with {forbidden_label!r}."
        )

    # (b) Greeting token.
    assert "Dear Hiring Manager," in prompt

    # (c) Sign-off token.
    assert "Sincerely," in prompt

    # (d) Selected tone wired into the prompt.
    assert "Tone: conversational." in prompt, (
        "The user-selected `tone` arg must flow into the prompt, not be "
        "silently overridden by a hardcoded default."
    )

    # (e) Full resume reaches the LLM — no truncation of the marker that
    # lives early in the resume, and also the 12k fixture did not get
    # clipped to the old 2500-char cap.
    assert UNIQUE_RESUME_MARKER in prompt
    assert len(resume_text) >= 10_000
    # The prompt contains the resume; therefore must be at least as long as
    # the resume.
    assert len(prompt) >= len(resume_text)

    # Output headroom must stay at the P5-S10 floor.
    assert captured["max_tokens"] is None or captured["max_tokens"] >= 1500


def test_cover_letter_passes_through_well_formed_llm_response_verbatim():
    """When the LLM returns a clean business letter, the service must return
    that string on `cover_letter` with only whitespace stripped — no server-
    side re-parsing."""
    well_formed = (
        "April 17, 2026\n\n"
        "Hiring Manager\nAcme Robotics\n\n"
        "Dear Hiring Manager,\n\n"
        "I am writing to apply for the Staff Software Engineer role at Acme. "
        "Your focus on reliability at scale resonates with my work.\n\n"
        "In my most recent role I led a 40% reduction in P50 latency by "
        "redesigning our async pipeline, and mentored four engineers to "
        "senior.\n\n"
        "I would welcome the chance to discuss how my experience maps to "
        "your roadmap. Thank you for your time and consideration.\n\n"
        "Sincerely,\nJordan Doe"
    )

    with patch(
        "app.services.gpt_service.generate_for_task",
        return_value=well_formed + "   \n",  # trailing whitespace must be stripped
    ):
        result = generate_cover_letter(
            {"full_text": _build_resume(12_000)},
            _jd_requirements(),
            tone="professional",
        )

    assert result.cover_letter == well_formed  # exact verbatim, just stripped
    assert result.tone == "professional"
    assert "##" not in result.cover_letter
    assert "Dear " in result.cover_letter
    assert "Sincerely," in result.cover_letter
