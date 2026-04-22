"""AI-powered resume optimization features (legacy routes).

Now delegates to the multi-model LLM router instead of calling Gemini directly.
"""
import asyncio
import json
import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

from app.core.llm_router import generate_for_task
from app.models.response_models import (
    CoverLetterRecipient,
    CoverLetterResponse,
    InterviewPrepResponse,
    InterviewQuestion,
    RewriteEntry,
    RewriteHeader,
    RewriteResponse,
    RewriteSection,
)
from app.services.parser import SECTION_PATTERNS, extract_contact_info

logger = logging.getLogger(__name__)


class RewriteError(Exception):
    """Structured rewrite error for AC-5 envelope.

    Raised by the rewrite service when the LLM response is empty, truncated,
    or malformed. Route handlers translate this to HTTP 502 with a JSON body
    of {error, message, retry_hint} (spec #51 §4 AC-5).
    """

    def __init__(self, error_code: str, message: str, retry_hint: str):
        self.error_code = error_code
        self.message = message
        self.retry_hint = retry_hint
        super().__init__(message)


class CoverLetterError(Exception):
    """Structured cover-letter error for spec #52 AC-5 envelope.

    Raised by the cover-letter service when the LLM call fails, returns an
    empty/truncated response, emits malformed JSON, or returns a payload
    that fails the LD-2 Pydantic shape (e.g., body_paragraphs length != 3).
    Route handlers translate this to HTTP 502 with the spec-#52 §LD-6 body:
        {"detail": {"error": <code>, "message": <str>, "retry_hint": <str>}}

    Error codes (spec #52 LD-6): cover_letter_truncated |
    cover_letter_parse_error | cover_letter_validation_error |
    cover_letter_llm_error.
    """

    def __init__(self, error_code: str, message: str, retry_hint: str):
        self.error_code = error_code
        self.message = message
        self.retry_hint = retry_hint
        super().__init__(message)


# Token budgets (spec #51 LD-4). Option B primary: per-section bounded budget.
# Option A fallback: full-document with high ceiling + thinking-budget cap so
# Gemini 2.5 Pro's thinking pool cannot starve the output pool.
#
# B-014 (2026-04-21) fix: the section path was missing its own thinking_budget
# cap, so the reasoning tier could consume the entire SECTION_MAX_TOKENS pool
# on internal thinking (FinishReason.MAX_TOKENS with thoughts_token_count≈cap,
# empty output). Section calls now pin `thinking_budget=SECTION_THINKING_BUDGET`
# and the output ceiling is raised to give a stable margin after the cap.
SECTION_MAX_TOKENS = 4000
SECTION_THINKING_BUDGET = 800
FULL_REWRITE_FALLBACK_MAX_TOKENS = 16000
FULL_REWRITE_THINKING_BUDGET = 2000
PARALLEL_SECTION_LIMIT = 4
REWRITE_INPUT_CEILING = 40000  # unchanged from pre-P5-S9 cap

# Cover-letter budgets (spec #52 §7). 400-word target + JSON key overhead.
# `thinking_budget` mirrors spec #51 LD-4 fallback insurance (AC-7).
COVER_LETTER_MAX_TOKENS = 2500
COVER_LETTER_THINKING_BUDGET = 2000


class _CoverLetterCore(BaseModel):
    """Internal parse target for the LLM's cover-letter JSON response.

    Holds the 7 structured fields the model emits (no `full_text`, no `tone`
    — those are server-side concerns). `body_paragraphs` is length-locked
    to exactly 3 so the hook / fit / close structure fails Pydantic
    validation if the LLM drifts.
    """

    date: str
    recipient: CoverLetterRecipient
    greeting: str
    body_paragraphs: List[str] = Field(..., min_length=3, max_length=3)
    signoff: str
    signature: str


def _join_cover_letter(core: "_CoverLetterCore") -> str:
    """Assemble the canonical full-text business letter per spec #52 AC-3.

    Blank lines between blocks; signoff → signature is a single newline per
    business-letter convention. `recipient.name` is always the literal
    'Hiring Manager' in V1 and is NOT surfaced as a separate line — the
    recipient block is the literal 'Hiring Manager' line followed by
    `recipient.company`. Used by both the service and the AC-3 test so the
    expected byte-for-byte format lives in exactly one place.
    """
    body = "\n\n".join(core.body_paragraphs)
    return (
        f"{core.date}\n\n"
        f"Hiring Manager\n{core.recipient.company}\n\n"
        f"{core.greeting}\n\n"
        f"{body}\n\n"
        f"{core.signoff}\n{core.signature}"
    )


def _extract_candidate_name(resume_text: str) -> str:
    """Best-effort candidate name from the first non-empty line of the resume.

    Accepts 2–4 Title-Case tokens with no digits, email, or colon. Falls back
    to "The Applicant" so the signature always renders something.
    """
    for raw in resume_text.splitlines()[:10]:
        line = raw.strip()
        if not line or "@" in line or ":" in line or any(c.isdigit() for c in line):
            continue
        tokens = line.split()
        if 2 <= len(tokens) <= 4 and all(re.match(r"^[A-Z][A-Za-z.'-]+$", t) for t in tokens):
            return line
    return "The Applicant"


def generate_job_fit_explanation(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    ats_score: int,
    matched_keywords: List[str],
    missing_keywords: List[str],
) -> Dict[str, Any]:
    """Generate a natural language job fit explanation."""
    prompt = f"""You are an expert career coach and ATS specialist. Analyze how well a candidate's resume matches a job description and provide a clear, honest assessment.

Resume Skills: {', '.join(resume_data.get('skills', [])[:20])}
Resume Sections: {list(resume_data.get('sections', {}).keys())}
JD Required Skills: {', '.join(jd_requirements.get('required_skills', [])[:20])}
JD Title: {jd_requirements.get('job_title', 'N/A')}
ATS Score: {ats_score}/100
Matched Keywords: {', '.join(matched_keywords[:15])}
Missing Keywords: {', '.join(missing_keywords[:15])}

Respond with a JSON object containing:
1. "explanation": A 2-3 sentence honest assessment of fit (150-200 words)
2. "top_strengths": Array of exactly 3 specific strengths as short strings
3. "top_gaps": Array of exactly 3 specific gaps/improvements as short strings
4. "improvement_plan": A 3-step 30-day action plan as array of strings

Be specific, direct, and constructive. Focus on actionable insights."""

    try:
        response_text = generate_for_task(task="ats_keyword_extraction", prompt=prompt, json_mode=True, max_tokens=800, temperature=0.6)
        data = json.loads(response_text)
        return {
            "explanation": data.get("explanation", ""),
            "top_strengths": data.get("top_strengths", [])[:3],
            "top_gaps": data.get("top_gaps", [])[:3],
            "improvement_plan": data.get("improvement_plan", []),
        }
    except Exception:
        return {
            "explanation": (
                f"Your resume shows {ats_score}% ATS compatibility with this role. "
                f"You matched {len(matched_keywords)} key terms but are missing {len(missing_keywords)} "
                "important keywords. Focus on incorporating the missing skills into your experience descriptions."
            ),
            "top_strengths": matched_keywords[:3] if matched_keywords else ["Technical background", "Relevant experience", "Education"],
            "top_gaps": missing_keywords[:3] if missing_keywords else ["Keyword optimization needed"],
            "improvement_plan": [
                "Add missing keywords naturally into your experience bullets",
                "Quantify your achievements with specific metrics",
                "Ensure your skills section covers all required technologies",
            ],
        }


_MARKDOWN_HEADING_PREFIX = re.compile(r"^#{1,6}\s+")


def _split_into_ordered_sections(resume_text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Split a resume into (header_text, [(section_title, section_content), ...]).

    The header is the text before any detected section boundary (typically the
    name + contact block). The section list preserves original file order.
    Titles are returned cleaned of markdown heading markers but otherwise
    verbatim from the resume, preserving the candidate's voice (spec #51 LD-1).
    """
    lines = resume_text.split("\n")
    header_lines: List[str] = []
    sections_ordered: List[Tuple[str, List[str]]] = []
    current_title: Optional[str] = None
    current_content: List[str] = []

    def _flush() -> None:
        nonlocal current_title, current_content
        if current_title is not None:
            sections_ordered.append((current_title, list(current_content)))
        current_content = []

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            if current_title is not None:
                current_content.append("")
            elif header_lines:
                header_lines.append("")
            continue

        # Accept markdown-heading syntax (## Summary) AND plain-text headers
        # (Summary). Production flow feeds plain text from the parser; the
        # Rewrite page also accepts pasted markdown from the FE composer.
        cleaned = _MARKDOWN_HEADING_PREFIX.sub("", stripped).strip()
        detected_key: Optional[str] = None
        for key, pattern in SECTION_PATTERNS.items():
            if re.match(pattern, cleaned):
                detected_key = key
                break

        if detected_key is not None:
            _flush()
            current_title = cleaned
        else:
            if current_title is None:
                header_lines.append(stripped)
            else:
                current_content.append(stripped)

    _flush()

    header_text = "\n".join(header_lines).strip()
    sections = [(title, "\n".join(body).strip()) for title, body in sections_ordered]
    return header_text, sections


def _parse_entries(raw: Any) -> List[RewriteEntry]:
    """Coerce an LLM-supplied entries array into RewriteEntry instances.

    The LLM may return entries as an array of objects or skip the field
    entirely. Unknown keys are ignored; missing fields default to empty.
    """
    if not isinstance(raw, list):
        return []
    entries: List[RewriteEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entries.append(
            RewriteEntry(
                org=str(item.get("org", "")),
                location=str(item.get("location", "")),
                date=str(item.get("date", "")),
                title=str(item.get("title", "")),
                bullets=[str(b) for b in item.get("bullets", []) if isinstance(b, (str, int, float))],
                details=[str(d) for d in item.get("details", []) if isinstance(d, (str, int, float))],
            )
        )
    return entries


def _section_to_markdown(section: RewriteSection) -> str:
    """Render a RewriteSection back to markdown for full_text assembly."""
    parts = [f"## {section.title}"]
    if section.content:
        parts.append(section.content)
    for entry in section.entries:
        header_bits = [b for b in (entry.title, entry.org, entry.location, entry.date) if b]
        if header_bits:
            parts.append("**" + " — ".join(header_bits) + "**")
        for bullet in entry.bullets:
            parts.append(f"- {bullet}")
        for detail in entry.details:
            parts.append(detail)
    return "\n\n".join(parts)


def _section_rewrite_prompt(
    section_title: str,
    section_content: str,
    jd_title: str,
    missing_keywords_str: str,
) -> str:
    return (
        f"You are an ATS optimization expert rewriting one section of a resume.\n\n"
        f"STRICT RULES:\n"
        f"- Preserve every fact: employer names, dates, metrics, skill names, entries.\n"
        f"- Do NOT fabricate achievements, metrics, or dates.\n"
        f"- Do NOT rename the section; keep the title verbatim.\n"
        f"- Improve: action verbs, quantified impact, keyword incorporation where relevant.\n\n"
        f"Target role: {jd_title}\n"
        f"Keywords to incorporate if relevant to THIS section: {missing_keywords_str}\n\n"
        f"Section title (return verbatim): {section_title}\n"
        f"Section content:\n{section_content}\n\n"
        f"Return JSON ONLY with this schema:\n"
        f'{{"title": "{section_title}", "content": "plain-text or markdown rewrite of the section", '
        f'"entries": [{{"org": "...", "location": "...", "date": "...", "title": "...", '
        f'"bullets": ["..."], "details": ["..."]}}]}}\n\n'
        f"If the section is prose (summary, profile), return content only and entries: [].\n"
        f"If the section is entry-based (experience, education, projects), populate entries."
    )


def _full_rewrite_prompt(
    resume_text: str,
    jd_title: str,
    missing_keywords_str: str,
) -> str:
    return (
        f"You are an ATS optimization expert rewriting a full resume.\n\n"
        f"STRICT RULES:\n"
        f"- Preserve EVERY section in the original order.\n"
        f"- Do NOT add sections not in the original.\n"
        f"- Do NOT remove any section, job, education entry, or skill.\n"
        f"- Preserve all facts: employer names, dates, metrics, skill names.\n"
        f"- Do NOT fabricate achievements.\n\n"
        f"Target role: {jd_title}\n"
        f"Missing keywords to incorporate: {missing_keywords_str}\n\n"
        f"Original resume:\n{resume_text}\n\n"
        f"Return JSON ONLY with this schema:\n"
        f'{{"header": {{"name": "...", "contact": "..."}}, '
        f'"sections": [{{"title": "...", "content": "...", '
        f'"entries": [{{"org": "...", "location": "...", "date": "...", '
        f'"title": "...", "bullets": ["..."], "details": ["..."]}}]}}]}}'
    )


def _parse_section_json(text: str, expected_title: str) -> RewriteSection:
    """Parse one section's JSON response; raise RewriteError on failure."""
    if not text or not text.strip():
        raise RewriteError(
            "rewrite_truncated",
            f"LLM returned empty response for section '{expected_title}'. "
            "The model likely hit its output cap (MAX_TOKENS).",
            "retry",
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RewriteError(
            "rewrite_parse_error",
            f"LLM response for section '{expected_title}' was not valid JSON: {exc}",
            "retry",
        ) from exc

    if not isinstance(data, dict):
        raise RewriteError(
            "rewrite_parse_error",
            f"LLM response for section '{expected_title}' was not a JSON object",
            "retry",
        )

    returned_title = str(data.get("title", "")).strip() or expected_title
    return RewriteSection(
        title=returned_title,
        content=str(data.get("content", "")),
        entries=_parse_entries(data.get("entries")),
    )


async def _rewrite_one_section(
    sem: asyncio.Semaphore,
    section_title: str,
    section_content: str,
    jd_title: str,
    missing_keywords_str: str,
) -> RewriteSection:
    """Rewrite a single section with bounded concurrency and token budget."""
    async with sem:
        prompt = _section_rewrite_prompt(
            section_title, section_content, jd_title, missing_keywords_str
        )
        text = await asyncio.to_thread(
            generate_for_task,
            task="resume_rewrite_section",
            prompt=prompt,
            json_mode=True,
            max_tokens=SECTION_MAX_TOKENS,
            temperature=0.4,
            thinking_budget=SECTION_THINKING_BUDGET,
        )
        return _parse_section_json(text, expected_title=section_title)


def _build_contact_section(header_text: str) -> RewriteSection:
    """Build a Contact section from the pre-section header block.

    We do not rewrite contact info — names, emails, and phone numbers are
    facts, not prose. Passing them to an LLM invites hallucination.
    """
    contact = extract_contact_info(header_text) if header_text else {
        "name": "", "email": "", "phone": "", "urls": ""
    }
    content_bits = []
    if contact.get("name"):
        content_bits.append(contact["name"])
    contact_line = " | ".join(
        c for c in (contact.get("email"), contact.get("phone"), contact.get("urls")) if c
    )
    if contact_line:
        content_bits.append(contact_line)
    # If the simple extractor missed things, keep the raw header text.
    if not content_bits and header_text:
        content_bits.append(header_text)
    return RewriteSection(
        title="Contact",
        content="\n".join(content_bits),
        entries=[],
    )


async def _generate_resume_rewrite_async(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    template_type: str,
    missing_keywords: Optional[List[str]],
) -> Tuple[RewriteResponse, str]:
    """Async structured rewrite. Returns (response, path) where path is
    'chunked' (Option B primary) or 'fallback_full' (Option A safety net).

    Spec #51 LD-4:
      - Chunked path: one LLM call per detected section, parallelized.
      - Fallback: single full-document call with high ceiling + Gemini
        thinking-budget cap, used when sectioning cannot proceed.
    """
    resume_text = resume_data.get("full_text", "")[:REWRITE_INPUT_CEILING]
    jd_title = jd_requirements.get("job_title", "the role")
    missing_kw_str = ", ".join(
        (missing_keywords or jd_requirements.get("all_skills", []))[:30]
    )

    header_text, ordered_sections = _split_into_ordered_sections(resume_text)

    # Option B primary: chunk per detected section.
    if len(ordered_sections) >= 2:
        sem = asyncio.Semaphore(PARALLEL_SECTION_LIMIT)
        tasks = [
            _rewrite_one_section(sem, title, content, jd_title, missing_kw_str)
            for title, content in ordered_sections
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        rewritten_sections: List[RewriteSection] = []
        for item in results:
            if isinstance(item, RewriteError):
                raise item
            if isinstance(item, Exception):
                raise RewriteError(
                    "rewrite_llm_error",
                    f"Section rewrite failed: {item}",
                    "retry",
                ) from item
            rewritten_sections.append(item)

        contact_section = _build_contact_section(header_text)
        contact_info = extract_contact_info(header_text)
        all_sections = [contact_section, *rewritten_sections]
        full_text = "\n\n".join(_section_to_markdown(s) for s in all_sections).strip()

        return (
            RewriteResponse(
                header=RewriteHeader(
                    name=contact_info.get("name", ""),
                    contact=" | ".join(
                        c for c in (
                            contact_info.get("email", ""),
                            contact_info.get("phone", ""),
                            contact_info.get("urls", ""),
                        ) if c
                    ),
                ),
                sections=all_sections,
                full_text=full_text,
                template_type=template_type,
            ),
            "chunked",
        )

    # Option A fallback: single call with thinking-budget cap.
    prompt = _full_rewrite_prompt(resume_text, jd_title, missing_kw_str)
    text = await asyncio.to_thread(
        generate_for_task,
        task="resume_rewrite",
        prompt=prompt,
        json_mode=True,
        max_tokens=FULL_REWRITE_FALLBACK_MAX_TOKENS,
        temperature=0.4,
        thinking_budget=FULL_REWRITE_THINKING_BUDGET,
    )

    if not text or not text.strip():
        raise RewriteError(
            "rewrite_truncated",
            "LLM returned empty response (likely hit output cap or safety block).",
            "retry",
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RewriteError(
            "rewrite_parse_error",
            f"LLM response was not valid JSON: {exc}",
            "retry",
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("sections"), list):
        raise RewriteError(
            "rewrite_parse_error",
            "LLM response missing 'sections' array",
            "retry",
        )

    header_data = data.get("header") or {}
    header = RewriteHeader(
        name=str(header_data.get("name", "")),
        contact=str(header_data.get("contact", "")),
    )
    sections: List[RewriteSection] = []
    for item in data["sections"]:
        if not isinstance(item, dict):
            continue
        sections.append(
            RewriteSection(
                title=str(item.get("title", "Section")),
                content=str(item.get("content", "")),
                entries=_parse_entries(item.get("entries")),
            )
        )
    full_text = "\n\n".join(_section_to_markdown(s) for s in sections).strip()
    return (
        RewriteResponse(
            header=header,
            sections=sections,
            full_text=full_text,
            template_type=template_type,
        ),
        "fallback_full",
    )


def generate_resume_rewrite(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    template_type: str = "general",
    major: Optional[str] = None,
    missing_keywords: Optional[List[str]] = None,
    missing_skills: Optional[List[str]] = None,
) -> Tuple[RewriteResponse, str]:
    """Generate an ATS-optimized structured rewrite of the resume (spec #51).

    Returns (RewriteResponse, path) where path is 'chunked' or 'fallback_full'.
    The 2-tuple return is the contract for callers that want to log which
    path was taken; the route handler in particular emits this as a PostHog
    property on `rewrite_succeeded`.

    Raises RewriteError on empty/truncated/malformed LLM responses (AC-5).
    """
    return asyncio.run(
        _generate_resume_rewrite_async(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            template_type=template_type,
            missing_keywords=missing_keywords,
        )
    )


async def generate_resume_rewrite_async(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    template_type: str = "general",
    major: Optional[str] = None,
    missing_keywords: Optional[List[str]] = None,
    missing_skills: Optional[List[str]] = None,
) -> Tuple[RewriteResponse, str]:
    """Async variant — use from async route handlers. See generate_resume_rewrite."""
    return await _generate_resume_rewrite_async(
        resume_data=resume_data,
        jd_requirements=jd_requirements,
        template_type=template_type,
        missing_keywords=missing_keywords,
    )


async def generate_section_rewrite(
    section_id: str,
    section_title: str,
    section_text: str,
    jd_text: str,
    missing_keywords: Optional[List[str]] = None,
) -> RewriteSection:
    """Rewrite a single section for per-section regenerate endpoint (spec #51 §6.2).

    Uses the same reasoning tier as the full rewrite (LD-6) but with a
    bounded per-call token budget — cheap and fast because input is one
    section, not a full resume.
    """
    jd_title = "the target role"
    # Try to extract a title line from the JD for better prompting.
    first_line = next((ln.strip() for ln in jd_text.splitlines() if ln.strip()), "")
    if first_line and len(first_line) < 120:
        jd_title = first_line
    missing_kw_str = ", ".join((missing_keywords or [])[:30])
    prompt = _section_rewrite_prompt(
        section_title=section_title,
        section_content=section_text,
        jd_title=jd_title,
        missing_keywords_str=missing_kw_str,
    )
    text = await asyncio.to_thread(
        generate_for_task,
        task="resume_rewrite_section",
        prompt=prompt,
        json_mode=True,
        max_tokens=SECTION_MAX_TOKENS,
        temperature=0.4,
        thinking_budget=SECTION_THINKING_BUDGET,
    )
    return _parse_section_json(text, expected_title=section_title)


def generate_cover_letter(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    tone: str = "professional",
) -> CoverLetterResponse:
    """Generate a structured cover letter (spec #52 LD-2).

    The LLM is prompted to return JSON with the 7 block-level fields;
    `full_text` is assembled server-side via `_join_cover_letter` so the
    FE never sees a free-form string that drifts from the structured blocks.

    Raises `CoverLetterError` on any failure mode (LLM exception, empty /
    truncated response, malformed JSON, Pydantic validation fail against
    the LD-2 shape). The route handler translates this to HTTP 502 with
    the spec #52 §LD-6 envelope. There is no silent fallback — a failed
    generation surfaces visibly, per spec §10.
    """
    resume_text = resume_data.get("full_text", "")[:20000]
    jd_text = jd_requirements.get("full_text", "")[:10000]
    missing_keywords = ", ".join(
        jd_requirements.get("missing_keywords", jd_requirements.get("all_skills", []))[:20]
    )
    candidate_name = _extract_candidate_name(resume_text)
    company_name = jd_requirements.get("company_name") or "your company"
    today = date.today().strftime("%B %d, %Y")

    prompt = f"""You are an expert career coach writing a compelling cover letter in traditional business-letter format.

Return a JSON object with EXACTLY these fields:
- "date": string — the letter date. Use: "{today}"
- "recipient": object with keys "name" (string) and "company" (string).
    - "name" must be "Hiring Manager".
    - "company" must be "{company_name}".
- "greeting": string — e.g. "Dear Hiring Manager,"
- "body_paragraphs": array of EXACTLY 3 strings (no more, no fewer):
    - [0] hook: state the role and company by name, express genuine interest, 2–3 sentences.
    - [1] fit: connect 2–3 specific, quantified achievements from the resume to the JD requirements. Incorporate the missing keywords naturally where they fit.
    - [2] close: reiterate enthusiasm, invite an interview, thank the reader.
- "signoff": string — e.g. "Sincerely,"
- "signature": string — the candidate's name. Use: "{candidate_name}"

Constraints:
- Keep the total letter under 400 words across all three body paragraphs.
- Tone: {tone}.
- Do not include any other keys. Do not wrap the response in additional objects.

Candidate resume:
{resume_text}

Job description:
{jd_text}

Missing skills to incorporate if possible:
{missing_keywords}"""

    try:
        text = generate_for_task(
            task="cover_letter",
            prompt=prompt,
            json_mode=True,
            max_tokens=COVER_LETTER_MAX_TOKENS,
            temperature=0.7,
            thinking_budget=COVER_LETTER_THINKING_BUDGET,
        )
    except Exception as exc:
        raise CoverLetterError(
            "cover_letter_llm_error",
            f"Cover letter LLM call failed: {exc}",
            "retry",
        ) from exc

    if not text or not text.strip():
        raise CoverLetterError(
            "cover_letter_truncated",
            "LLM returned an empty response (likely hit output cap or safety block).",
            "retry",
        )

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CoverLetterError(
            "cover_letter_parse_error",
            f"LLM response was not valid JSON: {exc}",
            "retry",
        ) from exc

    if not isinstance(data, dict):
        raise CoverLetterError(
            "cover_letter_parse_error",
            "LLM response was not a JSON object",
            "retry",
        )

    try:
        core = _CoverLetterCore.model_validate(data)
    except ValidationError as exc:
        raise CoverLetterError(
            "cover_letter_validation_error",
            f"Cover letter LLM response failed structural validation: {exc}",
            "retry",
        ) from exc

    return CoverLetterResponse(
        date=core.date,
        recipient=core.recipient,
        greeting=core.greeting,
        body_paragraphs=list(core.body_paragraphs),
        signoff=core.signoff,
        signature=core.signature,
        tone=tone,
        full_text=_join_cover_letter(core),
    )


def generate_interview_questions(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
) -> InterviewPrepResponse:
    """Generate likely interview questions with STAR method frameworks."""
    resume_text = resume_data.get("full_text", "")[:1500]
    jd_title = jd_requirements.get("job_title", "this role")
    required_skills = ", ".join(jd_requirements.get("required_skills", [])[:10])

    prompt = f"""Generate 10 likely interview questions for a candidate applying for the role of {jd_title}.
The role requires: {required_skills}
Candidate background: {resume_text[:800]}

For each question, provide a STAR method answer framework (guidance on what to cover, not a full answer).

Return a JSON object:
{{
  "questions": [
    {{
      "question": "The interview question",
      "star_framework": "Situation: ... | Task: ... | Action: ... | Result: ..."
    }}
  ]
}}

Mix: behavioral (3), technical (4), situational (2), culture fit (1).
Make questions specific to the role and candidate's background."""

    try:
        response_text = generate_for_task(task="interview_questions", prompt=prompt, json_mode=True, max_tokens=2000, temperature=0.7)
        data = json.loads(response_text)
        questions = [
            InterviewQuestion(question=q["question"], star_framework=q["star_framework"])
            for q in data.get("questions", [])[:10]
        ]
        return InterviewPrepResponse(questions=questions)
    except Exception:
        default_questions = [
            InterviewQuestion(
                question=f"Tell me about your experience with {required_skills.split(',')[0].strip() if required_skills else 'your main technical stack'}.",
                star_framework="Situation: Describe a specific project | Task: Your role and the challenge | Action: Technologies used and decisions made | Result: Impact and learnings",
            ),
            InterviewQuestion(
                question="Describe a time you had to learn a new technology quickly.",
                star_framework="Situation: The project requiring new tech | Task: What you needed to learn | Action: Learning approach and resources | Result: How quickly you became productive",
            ),
            InterviewQuestion(
                question="Tell me about your most challenging technical project.",
                star_framework="Situation: Project complexity and constraints | Task: Your specific responsibilities | Action: Problem-solving approach | Result: Outcome and impact",
            ),
            InterviewQuestion(
                question="How do you handle disagreements with team members about technical decisions?",
                star_framework="Situation: A specific disagreement | Task: Finding the right solution | Action: Communication and compromise | Result: Team outcome",
            ),
            InterviewQuestion(
                question="Where do you see yourself in 5 years?",
                star_framework="Focus on growth in this field, leadership aspirations, and alignment with company mission",
            ),
        ]
        return InterviewPrepResponse(questions=default_questions)


def rewrite_bullets_gpt(
    bullets: List[str],
    jd_text: str,
) -> List[str]:
    """Use Gemini to rewrite resume bullet points for maximum ATS impact."""
    if not bullets:
        return []

    bullets_formatted = "\n".join(f"- {b}" for b in bullets[:10])

    prompt = f"""Rewrite these resume bullet points to maximize ATS compatibility and hiring manager appeal.

ORIGINAL BULLETS:
{bullets_formatted}

JOB CONTEXT: {jd_text[:500]}

Rules:
1. Start each bullet with a strong past-tense action verb
2. Add quantification where naturally implied (%, $, team sizes, timeframes)
3. Use X-Y-Z formula: "Accomplished [X] as measured by [Y], by doing [Z]"
4. Incorporate relevant keywords from job context where they genuinely apply
5. Keep the same core facts — NEVER fabricate achievements or metrics
6. Keep each bullet under 120 characters for ATS compatibility

Return a JSON object: {{"bullets": ["rewritten bullet 1", "rewritten bullet 2", ...]}}"""

    try:
        response_text = generate_for_task(task="rewrite_bullets", prompt=prompt, json_mode=True, max_tokens=1000, temperature=0.5)
        data = json.loads(response_text)
        return data.get("bullets", bullets)
    except Exception:
        return bullets
