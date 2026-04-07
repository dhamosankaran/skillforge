"""Tests for the NLP service."""
import pytest
from app.services.nlp import (
    _detect_seniority,
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
