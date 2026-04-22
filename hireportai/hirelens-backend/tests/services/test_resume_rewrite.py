"""Regression tests for the resume rewrite service.

Historical bugs these tests guard against:
- P5-S9: a `[:4000]` slice on the input dropped the tail sections (Education,
  Certifications) before the prompt was built.
- Spec #47: preservation-contract wording in the prompt was the line of defense
  against the LLM silently summarising the resume.
- Spec #51 / B-001: the service used a single free-form markdown call that was
  truncated by Gemini 2.5 Pro's thinking-budget contention. The service now
  splits the resume into detected sections and calls the LLM once per section
  with a bounded token budget (Option B chunking). Tests AC-1 through AC-5
  in this file correspond to spec #51 §4.

Content-based assertions check that every org name / section survives the
trip from fixture → union-of-per-section-prompts. Preservation-contract
assertions check the spec #51 prompt clauses.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.services.gpt_service import (
    SECTION_MAX_TOKENS,
    SECTION_THINKING_BUDGET,
    RewriteError,
    generate_resume_rewrite,
    generate_section_rewrite,
)


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


# ═══════════════════════════════════════════════════════════════════════════
# Spec #51 AC-1 through AC-5 — section preservation regression coverage
# ═══════════════════════════════════════════════════════════════════════════


def _faithful_section_mock():
    """Mock that echoes the section title from the prompt into the response.

    The per-section prompt embeds `Section title (return verbatim): {title}`;
    we extract and echo it so the response is consistent with the request.
    This simulates an LLM that faithfully preserves the title (the behavior
    AC-1/AC-2 depend on — the service cannot manufacture title drift on its
    own, but can drop sections if chunking misbehaves).
    """
    import re as _re

    def fake(*, task, prompt, **kwargs):
        m = _re.search(r"Section title \(return verbatim\): (.+)", prompt)
        title = m.group(1).strip() if m else "Unknown"
        return json.dumps({
            "title": title,
            "content": f"Rewritten {title.lower()} content.",
            "entries": [],
        })

    return fake


def _resume_with_sections(section_titles: list[str]) -> str:
    """Build a plain-text resume with a contact header and the given sections."""
    blocks = [
        "Jane Doe",
        "jane@example.com | 555-1234 | https://janedoe.dev",
        "",
    ]
    for title in section_titles:
        blocks.append(title)
        blocks.append(f"Placeholder content for the {title.lower()} section.")
        blocks.append("")
    return "\n".join(blocks)


def test_ac1_3page_resume_preserves_6_sections_in_order():
    """AC-1 — 3-page resume with 6 sections, all present in order."""
    resume_text = _resume_with_sections(
        ["Summary", "Experience", "Education", "Skills", "Projects"]
    )
    # Pad to ~3-page length
    resume_text += "\n" + ("Filler content. " * 400)

    resume_data = {"full_text": resume_text, "skills": [], "sections": {}}
    jd_requirements = {"job_title": "Staff Engineer", "all_skills": ["python"]}

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=_faithful_section_mock(),
    ):
        result, path = generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
        )

    assert path == "chunked", f"Expected chunked path; got {path}"
    titles = [s.title for s in result.sections]
    assert titles == ["Contact", "Summary", "Experience", "Education", "Skills", "Projects"], (
        f"Section order/set mismatch. Expected Contact + 5 ordered body sections; "
        f"got {titles}"
    )
    for section in result.sections:
        assert section.title, "Every section must have a title"
    assert result.full_text, "full_text must be assembled for copy-to-clipboard"


def test_ac2_2page_resume_preserves_exact_section_set():
    """AC-2 — 2-page resume with 4 sections, no additions, no drops."""
    resume_text = _resume_with_sections(["Summary", "Experience", "Skills"])

    resume_data = {"full_text": resume_text, "skills": [], "sections": {}}
    jd_requirements = {"job_title": "Engineer", "all_skills": []}

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=_faithful_section_mock(),
    ):
        result, path = generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
        )

    assert path == "chunked"
    titles = [s.title for s in result.sections]
    assert titles == ["Contact", "Summary", "Experience", "Skills"], (
        f"Expected exactly Contact + 3 body sections in order. Got {titles}. "
        "If 'Education' appeared, the service hallucinated a section — AC-2 guards "
        "against that regression."
    )
    assert "Education" not in titles, (
        "AC-2: service must not inject sections that weren't in the original resume"
    )
    assert "Projects" not in titles


def test_ac3_4page_resume_no_truncation():
    """AC-3 — 4-page senior-engineer resume (>=10k chars) fully preserved.

    The token-budget regression AC: under the old contract, a 4-page resume
    hit Gemini 2.5 Pro's thinking-budget contention and output was truncated
    mid-section. Under chunked output, each section call has its own bounded
    budget and there is no shared pool.
    """
    resume_text = _build_12k_resume()
    assert len(resume_text) >= 10_000, (
        f"AC-3 requires a >=10k-char fixture; got {len(resume_text)}"
    )

    resume_data = {"full_text": resume_text, "skills": [], "sections": {}}
    jd_requirements = {"job_title": "Staff Engineer", "all_skills": ["python"]}

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=_faithful_section_mock(),
    ):
        result, path = generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
        )

    assert path == "chunked", "Long resumes must use the chunked path, not fallback"

    # Contact + 5 body sections from _build_12k_resume.
    titles_lower = [s.title.lower() for s in result.sections]
    for expected in ["contact", "summary", "experience", "skills", "education", "certifications"]:
        assert expected in titles_lower, (
            f"Expected {expected!r} to appear in output sections; got {titles_lower}. "
            "Likely regression: chunking dropped a section or the splitter "
            "failed to detect it."
        )
    # Every rewritten body section has non-empty content — no truncation.
    body_sections = [s for s in result.sections if s.title.lower() != "contact"]
    for section in body_sections:
        assert section.content, (
            f"Body section {section.title!r} came back with empty content. "
            "This is the B-001 truncation regression."
        )


def test_ac5_truncated_llm_response_raises_rewrite_error():
    """AC-5 — empty LLM response surfaces as RewriteError (→ 502 at route)."""
    resume_text = _resume_with_sections(["Summary", "Experience"])
    resume_data = {"full_text": resume_text, "skills": [], "sections": {}}
    jd_requirements = {"job_title": "Engineer", "all_skills": []}

    def fake_empty(*, task, prompt, **kwargs):
        return ""

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_empty,
    ):
        with pytest.raises(RewriteError) as exc_info:
            generate_resume_rewrite(
                resume_data=resume_data,
                jd_requirements=jd_requirements,
                template_type="general",
            )
    assert exc_info.value.error_code == "rewrite_truncated"
    assert exc_info.value.retry_hint in {"retry", "reduce_input", "contact_support"}


def test_ac5_malformed_json_raises_rewrite_error():
    """AC-5 — malformed JSON response surfaces as RewriteError parse code."""
    resume_text = _resume_with_sections(["Summary", "Experience"])
    resume_data = {"full_text": resume_text, "skills": [], "sections": {}}
    jd_requirements = {"job_title": "Engineer", "all_skills": []}

    def fake_bad_json(*, task, prompt, **kwargs):
        return "not valid json at all {{{{{"

    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake_bad_json,
    ):
        with pytest.raises(RewriteError) as exc_info:
            generate_resume_rewrite(
                resume_data=resume_data,
                jd_requirements=jd_requirements,
                template_type="general",
            )
    assert exc_info.value.error_code == "rewrite_parse_error"


# ═══════════════════════════════════════════════════════════════════════════
# B-014 regression — section-rewrite paths must pin a thinking_budget cap
# ═══════════════════════════════════════════════════════════════════════════
#
# The B-001 fix (spec #51 LD-4 Option B) bounded per-section max_tokens but
# forgot to pin thinking_budget on the two section-path callers. On Gemini
# 2.5 Pro the reasoning tier then consumed the entire output pool on internal
# thinking (thoughts_token_count≈SECTION_MAX_TOKENS, FinishReason.MAX_TOKENS,
# empty text → RewriteError → 502). Fixed 2026-04-21. Tests below guard the
# call signature so a future refactor cannot silently drop the cap.


def test_b014_section_path_passes_thinking_budget():
    """Every chunked `resume_rewrite_section` call must supply `thinking_budget`
    so Gemini 2.5 Pro's reasoning tier cannot starve the section output pool.
    """
    resume_text = _resume_with_sections(["Summary", "Experience", "Skills"])
    resume_data = {"full_text": resume_text, "skills": [], "sections": {}}
    jd_requirements = {"job_title": "Engineer", "all_skills": []}

    captured, fake = _capture_all_prompts()
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake,
    ):
        _, path = generate_resume_rewrite(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type="general",
        )

    assert path == "chunked", f"Expected chunked path; got {path}"
    assert captured, "Expected at least one section call to be captured"
    for call in captured:
        assert call["task"] == "resume_rewrite_section"
        assert "thinking_budget" in call, (
            "B-014 regression: section-rewrite call is missing `thinking_budget` "
            "kwarg. Without it, Gemini 2.5 Pro's thinking pool can consume all "
            f"{SECTION_MAX_TOKENS} output tokens and return empty text. "
            "See docs/status/E2E-BUG-DIAGNOSIS-2026-04-21.md §Bug (a)."
        )
        assert call["thinking_budget"] == SECTION_THINKING_BUDGET, (
            f"Section call used thinking_budget={call['thinking_budget']!r}; "
            f"expected {SECTION_THINKING_BUDGET}. Drift may silently widen the "
            "regression window."
        )
        # And the output ceiling must leave headroom beyond the thinking cap.
        assert call["max_tokens"] > SECTION_THINKING_BUDGET, (
            f"max_tokens={call['max_tokens']} ≤ thinking_budget="
            f"{SECTION_THINKING_BUDGET}. Output pool has no room left for the "
            "actual rewrite after thinking is done."
        )


def test_b014_section_endpoint_passes_thinking_budget():
    """`generate_section_rewrite` (the per-section regen endpoint in
    `POST /api/v1/rewrite/section`) must pin `thinking_budget` for the same
    reason as the chunked path — same LLM task, same failure mode.
    """
    import asyncio

    captured, fake = _capture_all_prompts()
    with patch(
        "app.services.gpt_service.generate_for_task",
        side_effect=fake,
    ):
        asyncio.run(
            generate_section_rewrite(
                section_id="sec-1",
                section_title="Experience",
                section_text="Acme Corp — Engineer (2020-2024)",
                jd_text="Staff Engineer",
            )
        )

    assert len(captured) == 1, f"Expected one section call; got {len(captured)}"
    call = captured[0]
    assert call["task"] == "resume_rewrite_section"
    assert "thinking_budget" in call, (
        "B-014 regression: /rewrite/section endpoint missing thinking_budget."
    )
    assert call["thinking_budget"] == SECTION_THINKING_BUDGET
    assert call["max_tokens"] == SECTION_MAX_TOKENS


def test_b014_section_max_tokens_has_headroom_above_thinking_budget():
    """Defence-in-depth constant-level check: SECTION_MAX_TOKENS must stay
    comfortably above SECTION_THINKING_BUDGET so output never starves even if
    the model uses the full thinking allowance.
    """
    # Output pool ≥ 2× thinking budget — a section rewrite is typically 500-
    # 2000 tokens of JSON content; the cap should carry that comfortably.
    assert SECTION_MAX_TOKENS >= SECTION_THINKING_BUDGET * 2, (
        f"SECTION_MAX_TOKENS={SECTION_MAX_TOKENS} is too close to "
        f"SECTION_THINKING_BUDGET={SECTION_THINKING_BUDGET}. Leave >=2× headroom "
        "so a section rewrite cannot hit MAX_TOKENS on realistic content."
    )
