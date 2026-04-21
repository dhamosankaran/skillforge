"""Regression tests for the resume rewrite service.

Historical bugs these tests guard against:
- P5-S9: a `[:4000]` slice on the input dropped the tail sections (Education,
  Certifications) before the prompt was built.
- Spec #47: preservation-contract wording in the prompt was the line of defense
  against the LLM silently summarising the resume.
- Spec #51 / B-001: the service used a single free-form markdown call that was
  truncated by Gemini 2.5 Pro's thinking-budget contention. The service now
  splits the resume into detected sections and calls the LLM once per section
  with a bounded token budget (Option B chunking).

Content-based assertions check that every org name / section survives the
trip from fixture → union-of-per-section-prompts. Preservation-contract
assertions check the spec #51 prompt clauses.
"""
from __future__ import annotations

import json
from unittest.mock import patch

from app.services.gpt_service import generate_resume_rewrite


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
    bullet_pad = (
        "Delivered measurable business impact through cross-functional "
        "collaboration, automated pipelines, and continuous improvement "
        "practices across a distributed team of senior engineers. "
    ) * 6

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


def _capture_all_prompts() -> tuple[list[dict], callable]:
    """Capture every generate_for_task call in order. Returns (captured_list,
    fake_fn) where captured_list is mutated in place as calls happen."""
    captured: list[dict] = []

    def fake_generate(*, task, prompt, **kwargs):
        captured.append({"task": task, "prompt": prompt, **kwargs})
        return json.dumps({
            "title": "Stub",
            "content": "Rewritten content.",
            "entries": [],
        })

    return captured, fake_generate


def test_full_resume_reaches_llm_prompts():
    """Every section heading and every org name must appear in the union of
    prompts passed to `generate_for_task` across the chunked per-section
    calls. Guards against P5-S9's input-truncation regression."""
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

    captured, fake = _capture_all_prompts()
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake,
    ):
        result, path = generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
            missing_keywords=["python", "kubernetes"],
            missing_skills=["llm"],
        )

    # Spec #51 LD-4 Option B: chunked path is the primary route.
    assert path == "chunked", f"Expected chunked path for a 5-section resume; got {path!r}"
    assert all(c["task"] == "resume_rewrite_section" for c in captured), (
        f"Every chunked call must route to task=resume_rewrite_section; got tasks "
        f"{[c['task'] for c in captured]}"
    )

    # Every section heading text must appear in at least one per-section prompt.
    all_prompts = "\n\n".join(c["prompt"] for c in captured)
    for heading in SECTION_HEADINGS:
        bare = heading.removeprefix("## ")
        assert bare in all_prompts, (
            f"Section heading {bare!r} missing from any per-section prompt. "
            "Input resume_text was truncated or section detection regressed."
        )

    for org in ORGS:
        assert org in all_prompts, (
            f"Org name {org!r} missing from any per-section prompt. "
            "Input resume_text was truncated before chunking."
        )

    # Spec #51 LD-4: per-section max_tokens is bounded well below any thinking
    # budget contention. The floor is the chunked-section constant.
    for c in captured:
        assert c.get("max_tokens", 0) >= 1000, (
            f"max_tokens={c.get('max_tokens')} is below the per-section floor; "
            "chunking only works if each call has enough headroom."
        )

    # And the structured response must now have populated sections (LD-5).
    assert len(result.sections) >= 5, (
        f"Expected >=5 sections in response; got {len(result.sections)}"
    )


# ── Spec #51 preservation contract (§6 prompt wording) ──
# The per-section prompts tell the LLM to preserve facts, never fabricate, and
# keep the title verbatim. Dropping any of these clauses reopens the door to
# the B-001 "summary instead of rewrite" failure mode.
PRESERVATION_CLAUSES = (
    "Preserve every fact",
    "Do NOT fabricate",
    "Do NOT rename the section",
)


def test_prompt_includes_preservation_rules():
    """Every preservation clause from spec #51 §6.2 must appear in the section
    rewrite prompt. Inherited and updated from spec #47 AC-2."""
    resume_data = {
        "full_text": (
            "Jane Doe\njane@example.com\n\n"
            "## Summary\nShort resume.\n\n"
            "## Experience\nAcme — Engineer\n"
        ),
        "skills": [],
        "sections": {},
    }
    jd_requirements = {"job_title": "Engineer", "all_skills": []}

    captured, fake = _capture_all_prompts()
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake,
    ):
        generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
        )

    all_prompts = "\n\n".join(c["prompt"] for c in captured)
    for clause in PRESERVATION_CLAUSES:
        assert clause in all_prompts, (
            f"Preservation clause missing from rewrite prompts: {clause!r}. "
            "Dropping this rule risks reintroducing the B-001 "
            "'summary instead of full rewrite' regression. See spec #51 §6.2."
        )
