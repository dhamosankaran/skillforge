"""Tests for the NLP service."""
import pytest
from app.services.nlp import (
    _detect_seniority,
    _extract_company_name,
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


# ── B-021 — company-name heuristic extraction ─────────────────────────────


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
def test_extract_company_name_happy(jd, expected):
    """B-021 AC: high-precision patterns pick up common JD shapes."""
    assert _extract_company_name(jd) == expected


@pytest.mark.parametrize("jd", [
    "",
    "   \n\t  ",
    # No company-shaped anchor — should return None, not guess.
    "Senior Python Engineer. Remote. Required: 5+ years Python.",
    # Avoids picking "Python" out of "Python is" (stopword guard).
    "Python is the primary language. Kubernetes experience required.",
])
def test_extract_company_name_returns_none_on_low_confidence(jd):
    """B-021: low-confidence JDs return None so consumers keep their
    'your company' / 'Unknown Company' fallback. Silent misses are
    strictly better than false positives ending up in the prompt."""
    assert _extract_company_name(jd) is None


def test_extract_job_requirements_includes_company_name_key():
    """B-021: company_name is always present in the return dict (None if
    extraction missed). Consumers read `.get("company_name")` and the
    shape contract matters for the fallback branch."""
    reqs = extract_job_requirements(SAMPLE_JD)
    assert "company_name" in reqs
    # SAMPLE_JD at the top of this file has no company anchor — expect None.
    assert reqs["company_name"] is None


def test_extract_job_requirements_populates_company_name_when_present():
    """B-021: real JDs with a recognisable shape yield a populated value."""
    jd = (
        "Senior Python Engineer\n\n"
        "Acme Robotics is hiring a Senior Python Engineer to own our "
        "platform reliability.\n"
    )
    reqs = extract_job_requirements(jd)
    assert reqs["company_name"] == "Acme Robotics"
