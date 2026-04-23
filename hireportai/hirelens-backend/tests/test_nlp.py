"""Tests for the NLP service."""
import json
from unittest.mock import patch

import pytest
from app.services.nlp import (
    _detect_seniority,
    _extract_company_name,
    _extract_company_name_llm,
    _extract_company_name_regex,
    calculate_similarity,
    extract_job_requirements,
    extract_skills,
)


SAMPLE_JD = """
Senior Python Engineer

We are looking for a Senior Python Engineer to join our team.

Required:
- 5+ years of Python development
- Experience with FastAPI or Django
- Strong knowledge of PostgreSQL and Redis
- Docker and Kubernetes experience
- CI/CD pipeline management

Preferred:
- AWS certification
- Experience with Kafka or RabbitMQ
"""

SAMPLE_RESUME_TEXT = """
Python Developer with 6 years of experience.
Built REST APIs using FastAPI and Django.
Deployed services with Docker and managed PostgreSQL databases.
Used Git for version control and worked in Agile environment.
"""


def test_extract_skills_from_resume():
    skills = extract_skills(SAMPLE_RESUME_TEXT)
    assert isinstance(skills, list)
    # Should find common skills
    skills_lower = [s.lower() for s in skills]
    assert "python" in skills_lower or "fastapi" in skills_lower


def test_extract_job_requirements():
    reqs = extract_job_requirements(SAMPLE_JD)
    assert "all_skills" in reqs
    assert "required_skills" in reqs
    assert isinstance(reqs["all_skills"], list)


def test_detect_seniority_senior():
    assert _detect_seniority("looking for a senior engineer") == "Senior"


def test_detect_seniority_junior():
    assert _detect_seniority("entry level position") == "Junior"


def test_detect_seniority_manager():
    assert _detect_seniority("engineering manager role") == "Manager"


def test_calculate_similarity_identical():
    score = calculate_similarity("Python developer", "Python developer")
    assert score > 0.9


def test_calculate_similarity_unrelated():
    score = calculate_similarity("Python developer", "Yoga instructor")
    assert score < 0.5


def test_calculate_similarity_partial():
    score = calculate_similarity(
        "Python FastAPI Docker AWS",
        "Python Django PostgreSQL AWS",
    )
    assert 0.1 < score < 1.0


# ── B-021 — regex fallback (now reached only on LLM infra failure) ─────────
#
# B-024 promoted the top-level `_extract_company_name` to an LLM-primary
# orchestrator; the regex path lives on as the fallback for network /
# quota / config failures. These tests now target the regex function
# directly so the fallback path stays covered independently of the LLM
# mock surface.


@pytest.mark.parametrize("jd, expected", [
    # "About X:" pattern
    ("About Acme Robotics: we build warehouse automation.", "Acme Robotics"),
    ("About Stripe — payments infrastructure for the internet.", "Stripe"),
    # "Join X" pattern
    ("Join Acme Robotics as a Staff Engineer.", "Acme Robotics"),
    ("Join the Northwind Traders team in London.", "Northwind Traders"),
    # "X is hiring / looking / seeking"
    ("Acme Robotics is hiring a Staff Software Engineer.", "Acme Robotics"),
    ("Stripe is looking for senior engineers.", "Stripe"),
    ("Northwind Traders is seeking a platform lead.", "Northwind Traders"),
    # "at X." anchor
    ("Staff Software Engineer at Acme Robotics. You'll own reliability.",
     "Acme Robotics"),
    # "Company: X" line
    ("Role: Senior Engineer\nCompany: Acme Robotics\nLocation: SF",
     "Acme Robotics"),
])
def test_extract_company_name_regex_happy(jd, expected):
    """B-021 AC (now targeting the regex fallback directly)."""
    assert _extract_company_name_regex(jd) == expected


@pytest.mark.parametrize("jd", [
    "",
    "   \n\t  ",
    # No company-shaped anchor — should return None, not guess.
    "Senior Python Engineer. Remote. Required: 5+ years Python.",
    # Avoids picking "Python" out of "Python is" (stopword guard).
    "Python is the primary language. Kubernetes experience required.",
])
def test_extract_company_name_regex_returns_none_on_low_confidence(jd):
    """B-021: low-confidence JDs return None so consumers keep their
    'your company' / 'Unknown Company' fallback. Silent misses are
    strictly better than false positives ending up in the prompt."""
    assert _extract_company_name_regex(jd) is None


# ── B-024 — LLM-primary company-name extraction orchestrator ───────────────
#
# Design (three-layer): LLM primary → regex fallback on infra failure →
# existing "your company" / "Unknown Company" consumer fallback on None.
# Precision-first: null > false positive. Layer 2 (manual user entry on
# None) is tracked as follow-up B-025 and is NOT in scope here.
#
# NOTE: we patch `app.services.nlp.generate_for_task` (the imported name
# in this module) rather than `app.core.llm_router.generate_for_task` —
# patching at the use site is the standard vi.mock equivalent for Python.


JPMORGAN_JD = (
    "JPMorgan Chase & Co.\n"
    "Job Title: Executive Director – Agentic AI Strategy & Firmwide Data\n"
    "Location: Plano, TX / New York, NY / Jersey City, NJ (Hybrid)\n"
    "Organization: Global Technology / Chief Data Office (CDO)\n"
    "Role Summary\n"
    "As an Executive Director at JPMorgan Chase & Co., you will be at the "
    "forefront of the firm's 'AI-first' evolution.\n"
)


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_positive_jpmorgan(mock_gen):
    """Primary path: LLM returns the hiring company verbatim."""
    mock_gen.return_value = json.dumps({"company_name": "JPMorgan Chase & Co."})
    assert _extract_company_name(JPMORGAN_JD) == "JPMorgan Chase & Co."
    # Sanity: the task name is the one we registered in the fast tier.
    call_kwargs = mock_gen.call_args.kwargs
    assert call_kwargs["task"] == "company_name_extraction"
    assert call_kwargs["json_mode"] is True


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_null_returns_none_without_regex_fallback(mock_gen):
    """LLM returning null is VALID DATA ("unclear"), not an error — the
    orchestrator must NOT fall through to the regex path. Consumers see
    their "your company" placeholder, which is the approved worst case
    per the precision-first trade-off.

    The JD below would have matched the regex ("Acme Robotics is hiring");
    we're asserting the regex is deliberately NOT reached when the LLM
    said null.
    """
    mock_gen.return_value = json.dumps({"company_name": None})
    jd = "Acme Robotics is hiring a Senior Engineer. Remote-friendly."
    assert _extract_company_name(jd) is None


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_aggregator_rejected(mock_gen):
    """Server-side deny-list backstop: even if the LLM ignores its prompt
    instructions and returns an aggregator name, we reject it.
    """
    mock_gen.return_value = json.dumps({"company_name": "LinkedIn"})
    assert _extract_company_name("some JD text") is None


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_aggregator_case_insensitive(mock_gen):
    """Deny-list match is case-insensitive — "INDEED" / "indeed" both reject."""
    mock_gen.return_value = json.dumps({"company_name": "INDEED"})
    assert _extract_company_name("some JD text") is None


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_empty_string_returns_none(mock_gen):
    """Empty or whitespace-only LLM output is treated as None."""
    mock_gen.return_value = json.dumps({"company_name": "   "})
    assert _extract_company_name("some JD text") is None


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_malformed_json_returns_none(mock_gen):
    """Malformed LLM output is low-confidence, NOT an infra failure —
    treat as None rather than falling back to regex. Parse-fail is
    effectively the same class as LLM-returns-null.
    """
    mock_gen.return_value = "not valid json {{"
    # Regex would match this JD, but orchestrator should still return None
    # because the LLM was reachable — it just returned garbage.
    jd = "Acme Robotics is hiring a Senior Engineer."
    assert _extract_company_name(jd) is None


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_infra_failure_falls_back_to_regex(mock_gen):
    """Network / quota / config failures raise from generate_for_task.
    Orchestrator catches, logs, and uses the regex fallback — the
    pre-B-024 behavior, preserved so transient LLM outages don't
    silently degrade all scans.
    """
    mock_gen.side_effect = RuntimeError("GEMINI_API_KEY not configured")
    jd = "Acme Robotics is hiring a Senior Engineer."
    assert _extract_company_name(jd) == "Acme Robotics"


@patch("app.services.nlp.generate_for_task")
def test_b024_llm_infra_failure_then_regex_miss_returns_none(mock_gen):
    """Infra failure + regex also misses → None. Consumers keep their
    placeholder. Worst case under precision-first policy.
    """
    mock_gen.side_effect = RuntimeError("network down")
    # No regex-matchable anchor in this JD.
    jd = "Senior Python Engineer. Remote. Required: 5+ years Python."
    assert _extract_company_name(jd) is None


@patch("app.services.nlp.generate_for_task")
def test_b024_empty_jd_short_circuits_before_llm(mock_gen):
    """Empty-string / whitespace JDs skip the LLM call entirely — no
    point paying tokens for a null-in null-out round-trip.
    """
    assert _extract_company_name("") is None
    assert _extract_company_name("   \n\t  ") is None
    mock_gen.assert_not_called()


@patch("app.services.nlp.generate_for_task")
def test_b024_long_company_name_gets_truncated(mock_gen):
    """Length cap at 100 chars (same as regex path) — defensive, since
    LLM output is free-form.
    """
    long_name = "A" * 200
    mock_gen.return_value = json.dumps({"company_name": long_name})
    result = _extract_company_name("some JD text")
    assert result is not None
    assert len(result) == 100


# ── End-to-end: extract_job_requirements still returns company_name key ────


@patch("app.services.nlp.generate_for_task")
def test_extract_job_requirements_includes_company_name_key(mock_gen):
    """B-021 shape contract preserved: `company_name` key always present
    in the return dict (None if extraction missed). Consumers read
    `.get("company_name")` and depend on that contract.
    """
    mock_gen.return_value = json.dumps({"company_name": None})
    reqs = extract_job_requirements(SAMPLE_JD)
    assert "company_name" in reqs
    assert reqs["company_name"] is None


@patch("app.services.nlp.generate_for_task")
def test_extract_job_requirements_populates_company_name_when_llm_positive(mock_gen):
    """B-024: real JDs yield a populated value via the LLM path."""
    mock_gen.return_value = json.dumps({"company_name": "Acme Robotics"})
    jd = (
        "Senior Python Engineer\n\n"
        "Acme Robotics is hiring a Senior Python Engineer to own our "
        "platform reliability.\n"
    )
    reqs = extract_job_requirements(jd)
    assert reqs["company_name"] == "Acme Robotics"
