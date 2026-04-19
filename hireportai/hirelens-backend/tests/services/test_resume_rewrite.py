"""Regression test for P5-S9: the resume rewrite service must send the FULL
resume (all sections, all org names) to the LLM — no char truncation.

Historical bug (pre-P5-S9): a `[:4000]` slice on the input dropped the tail
sections (Education, Certifications) before the prompt was built. This test
fails the moment anyone reintroduces that cap.
"""
from __future__ import annotations

from unittest.mock import patch

from app.services.gpt_service import generate_resume_rewrite


# ── Fixture: ~12k-char synthetic resume covering every common section ──
ORGS = [
    "Acme Robotics",
    "Globex Corporation",
    "Initech Systems",
]

SECTION_HEADINGS = [
    "## Summary",
    "## Experience",
    "## Skills",
    "## Education",
    "## Certifications",
]


def _build_12k_resume() -> str:
    # Realistic-ish padding so we clear the old 4k cap by a wide margin
    # and land around 12k characters.
    bullet_pad = (
        "Delivered measurable business impact through cross-functional "
        "collaboration, automated pipelines, and continuous improvement "
        "practices across a distributed team of senior engineers. "
    ) * 6  # ~1100 chars per bullet

    experience_block = "\n\n".join(
        f"### {org} — Senior Engineer ({2016 + i}–{2019 + i})\n"
        f"- {bullet_pad}\n"
        f"- {bullet_pad}\n"
        f"- {bullet_pad}\n"
        for i, org in enumerate(ORGS)
    )

    resume = (
        "## Summary\n"
        "Seasoned software engineer with a decade of experience delivering "
        "platform, ML, and developer-productivity products at scale. "
        + ("Proven track record of shipping reliably in ambiguous, fast-moving "
           "environments. ") * 6
        + "\n\n"
        "## Experience\n"
        f"{experience_block}\n\n"
        "## Skills\n"
        + ", ".join(
            ["Python", "TypeScript", "React", "FastAPI", "PostgreSQL",
             "pgvector", "Redis", "Docker", "Kubernetes", "GCP", "AWS",
             "LLM applications", "distributed systems"] * 3
        ) + "\n\n"
        "## Education\n"
        "### State University — B.S. Computer Science (2012–2016)\n"
        + ("Graduated with honors; coursework included algorithms, "
           "distributed systems, and machine learning. ") * 8
        + "\n\n"
        "## Certifications\n"
        "- AWS Certified Solutions Architect — Professional (2023)\n"
        "- Google Professional Machine Learning Engineer (2024)\n"
        + ("Ongoing continuing education in applied cryptography and "
           "cloud security. ") * 6
    )
    return resume


def test_full_resume_reaches_llm_prompt():
    """Every section heading and every org name must appear in the prompt
    passed to `generate_for_task`."""
    resume_text = _build_12k_resume()
    assert len(resume_text) >= 10_000, (
        f"Fixture must be >=10k chars to exercise the regression; got "
        f"{len(resume_text)}"
    )

    resume_data = {"full_text": resume_text, "skills": [], "sections": {}}
    jd_requirements = {
        "job_title": "Staff Software Engineer",
        "all_skills": ["python", "kubernetes", "llm"],
    }

    captured = {}

    def fake_generate(*, task, prompt, **kwargs):
        captured["task"] = task
        captured["prompt"] = prompt
        captured["max_tokens"] = kwargs.get("max_tokens")
        return "## Summary\nRewritten.\n\n## Experience\n..."

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_generate,
    ):
        generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
            missing_keywords=["python", "kubernetes"],
            missing_skills=["llm"],
        )

    assert captured["task"] == "resume_rewrite"

    prompt = captured["prompt"]

    # Every section heading must survive the trip from fixture → prompt.
    for heading in SECTION_HEADINGS:
        assert heading in prompt, (
            f"Section heading {heading!r} missing from LLM prompt. "
            "Likely regression: input resume_text was truncated."
        )

    # Every org name must survive too.
    for org in ORGS:
        assert org in prompt, (
            f"Org name {org!r} missing from LLM prompt. Likely regression: "
            "input resume_text was truncated before building the prompt."
        )

    # And max_tokens must not regress below the 8k cap restored in P5-S9.
    assert captured["max_tokens"] is None or captured["max_tokens"] >= 8000, (
        f"max_tokens={captured['max_tokens']} is below the P5-S9 floor of 8000."
    )


# ── Spec #47 AC-2: the prompt's preservation contract must survive refactors ──
#
# Rules 1, 7, and 8 of the resume-rewrite prompt tell the LLM to keep every
# section, add nothing, and remove nothing. Dropping any of them is how the
# v2.1 "missing original content" bug would silently come back — the input
# would reach the model intact (AC-1) but the model would be free to summarise.
PRESERVATION_CLAUSES = (
    "Maintain the EXACT same sections as the original",
    "Do NOT add sections that weren't in the original resume",
    "Do NOT remove any jobs, education entries, or skills",
)


def test_prompt_includes_preservation_rules():
    """Every preservation clause from spec #47 §2.3 must appear in the prompt."""
    resume_data = {
        "full_text": "## Summary\nShort resume.\n\n## Experience\nAcme — Engineer\n",
        "skills": [],
        "sections": {},
    }
    jd_requirements = {"job_title": "Engineer", "all_skills": []}

    captured = {}

    def fake_generate(*, task, prompt, **kwargs):
        captured["prompt"] = prompt
        return "## Summary\nRewritten."

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_generate,
    ):
        generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
        )

    prompt = captured["prompt"]
    for clause in PRESERVATION_CLAUSES:
        assert clause in prompt, (
            f"Preservation clause missing from rewrite prompt: {clause!r}. "
            "Dropping this rule risks reintroducing the v2.1 "
            "'missing original content' regression. See spec #47 AC-2."
        )
