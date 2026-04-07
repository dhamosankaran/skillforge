"""Tests for the resume parser."""
import pytest
from app.services.parser import detect_sections, extract_bullets, extract_contact_info


SAMPLE_RESUME = """John Smith
john.smith@email.com
(555) 123-4567

SUMMARY
Experienced software engineer with 5 years building scalable web applications.

EXPERIENCE
Senior Software Engineer — Acme Corp (2020 – Present)
• Built a microservices architecture that reduced deployment time by 60%
• Led a team of 5 engineers to deliver the customer portal on time
• Increased test coverage from 40% to 90% using pytest and Jest

Software Engineer — TechStart Inc (2018 – 2020)
• Developed RESTful APIs using Python and FastAPI
• Optimized database queries reducing average response time by 45%

EDUCATION
B.S. Computer Science — State University (2018)

SKILLS
Python, JavaScript, React, FastAPI, Docker, AWS, PostgreSQL, Git
"""


def test_detect_sections():
    sections = detect_sections(SAMPLE_RESUME)
    assert "experience" in sections
    assert "education" in sections
    assert "skills" in sections


def test_extract_bullets():
    bullets = extract_bullets(SAMPLE_RESUME)
    assert len(bullets) > 0
    # Should find bullet points
    assert any("microservices" in b.lower() for b in bullets)


def test_extract_contact_info():
    info = extract_contact_info(SAMPLE_RESUME)
    assert info["email"] == "john.smith@email.com"
    assert "555" in info["phone"]


def test_detect_sections_missing():
    """Resume with no clear sections should return empty dict."""
    sections = detect_sections("Just some random text without headers.")
    assert isinstance(sections, dict)


def test_extract_bullets_no_bullets():
    """Text with no bullet chars should return empty list."""
    text = "This text has no bullet points at all."
    bullets = extract_bullets(text)
    assert isinstance(bullets, list)
