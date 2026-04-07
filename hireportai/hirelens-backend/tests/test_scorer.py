"""Tests for the ATS scoring engine."""
import pytest
from app.services.scorer import ATSScorer


@pytest.fixture
def scorer():
    return ATSScorer()


def test_perfect_score(scorer):
    """A resume that matches all keywords and has no issues should score ~100."""
    keywords = ["Python", "React", "Docker", "AWS"]
    result = scorer.score(
        matched_keywords=keywords,
        jd_keywords=keywords,
        resume_skills=keywords,
        jd_skills=keywords,
        formatting_issues=[],
        bullets=[{"score": 10} for _ in range(5)],
    )
    assert result["total"] >= 90
    assert result["grade"] in ("A", "A-")


def test_zero_keyword_match(scorer):
    """A resume with no keyword matches should score low."""
    result = scorer.score(
        matched_keywords=[],
        jd_keywords=["Python", "AWS", "Docker"],
        resume_skills=[],
        jd_skills=["Python", "AWS", "Docker"],
        formatting_issues=[],
        bullets=[{"score": 5} for _ in range(3)],
    )
    assert result["total"] < 50


def test_critical_formatting_penalty(scorer):
    """Critical formatting issues should significantly reduce score."""
    result = scorer.score(
        matched_keywords=["Python", "AWS"],
        jd_keywords=["Python", "AWS", "Docker"],
        resume_skills=["Python", "AWS"],
        jd_skills=["Python", "AWS", "Docker"],
        formatting_issues=[
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "warning"},
        ],
        bullets=[{"score": 7} for _ in range(5)],
    )
    # Formatting score should be penalized (2 critical @ -8 each + 1 warning @ -3 = -19 => 81)
    assert result["breakdown"]["formatting_compliance"] <= 81
    assert result["breakdown"]["formatting_compliance"] < 100


def test_grade_boundaries(scorer):
    """Grade assignment should follow letter grade boundaries."""
    assert scorer._to_grade(95) == "A"
    assert scorer._to_grade(85) == "B"
    assert scorer._to_grade(75) == "C"
    assert scorer._to_grade(65) == "D"
    assert scorer._to_grade(50) == "F"


def test_partial_keyword_match(scorer):
    """Partial keyword matches should produce proportional scores."""
    jd_kw = ["Python", "AWS", "Docker", "Kubernetes", "CI/CD"]
    matched = ["Python", "AWS"]
    result = scorer.score(
        matched_keywords=matched,
        jd_keywords=jd_kw,
        resume_skills=matched,
        jd_skills=jd_kw,
        formatting_issues=[],
        bullets=[{"score": 6} for _ in range(4)],
    )
    assert 30 <= result["total"] <= 70


def test_empty_bullets_fallback(scorer):
    """No bullets should use neutral fallback score."""
    result = scorer.score(
        matched_keywords=["Python"],
        jd_keywords=["Python"],
        resume_skills=["Python"],
        jd_skills=["Python"],
        formatting_issues=[],
        bullets=[],
    )
    assert result["total"] > 0
    assert "breakdown" in result
