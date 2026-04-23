"""AI service — LLM-powered resume optimization features.

Uses the LLM provider abstraction so the same prompts work with
Gemini, Claude, or any future provider.
"""
import json
import re
from datetime import date
from typing import Any, Dict, List

from app.schemas.responses import (
    CoverLetterResponse,
    InterviewPrepResponse,
    InterviewQuestion,
    RewriteHeader,
    RewriteResponse,
)
from app.core.llm_router import generate_for_task


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


def generate_resume_rewrite(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
) -> RewriteResponse:
    """Generate an ATS-optimized rewrite of the resume.

    Returns the rewritten resume as clean markdown in ``full_text``.
    """
    resume_text = resume_data.get("full_text", "")[:40000]
    jd_title = jd_requirements.get("job_title", "the role")
    missing_keywords = ", ".join(jd_requirements.get("missing_keywords", jd_requirements.get("all_skills", []))[:30])

    prompt = f"""You are an expert resume writer specializing in ATS optimization.
Rewrite the following resume to maximize ATS compatibility for the target role.

Rules:
1. Maintain the EXACT same sections as the original (Summary, Experience, Skills, Education, etc.)
2. Improve bullet points with quantified achievements (numbers, percentages, dollar amounts)
3. Incorporate the missing keywords naturally into relevant sections
4. Use strong action verbs at the start of each bullet
5. Keep the tone professional and confident
6. Output in clean markdown with ## headers for each section, - for bullet points
7. Do NOT add sections that weren't in the original resume
8. Do NOT remove any jobs, education entries, or skills — only improve the language

Missing keywords to incorporate: {missing_keywords}
Target role: {jd_title}

Original resume:
{resume_text}"""

    try:
        markdown = generate_for_task(
            task="resume_rewrite", prompt=prompt, max_tokens=8000, temperature=0.4,
        )
        return RewriteResponse(
            header=RewriteHeader(),
            sections=[],
            full_text=markdown.strip(),
        )
    except Exception:
        return RewriteResponse(
            header=RewriteHeader(),
            sections=[],
            full_text=resume_text,
        )


def generate_cover_letter(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    tone: str = "professional",
) -> CoverLetterResponse:
    """Generate a personalized cover letter in traditional business-letter format."""
    resume_text = resume_data.get("full_text", "")[:20000]
    jd_title = jd_requirements.get("job_title", "this role")
    jd_text = jd_requirements.get("full_text", "")[:10000]
    missing_keywords = ", ".join(jd_requirements.get("missing_keywords", jd_requirements.get("all_skills", []))[:20])
    candidate_name = _extract_candidate_name(resume_text)
    company_name = jd_requirements.get("company_name") or "your company"
    today = date.today().strftime("%B %d, %Y")

    prompt = f"""You are an expert career coach writing a compelling cover letter in traditional business-letter format.

STRICT FORMAT RULES:
- Do NOT use markdown headers (no "##", no "#", no bold section titles).
- Do NOT label sections with words like "Opening", "Why I'm a Fit", "Key Achievement", or "Closing".
- Output plain text with blank lines between blocks.

Exact structure, in this order:

1. Date line: "{today}"
2. Blank line.
3. Recipient block (2 lines):
   Hiring Manager
   {company_name}
4. Blank line.
5. Greeting: "Dear Hiring Manager,"
6. Blank line.
7. Body paragraph 1 — hook: state the role and company by name, express genuine interest, 2–3 sentences.
8. Blank line.
9. Body paragraph 2 — fit: connect 2–3 specific, quantified achievements from the resume to the JD requirements. Incorporate missing keywords naturally.
10. Blank line.
11. Body paragraph 3 — close: reiterate enthusiasm, invite an interview, thank the reader.
12. Blank line.
13. Sign-off line: "Sincerely,"
14. Signature line: "{candidate_name}"

Keep the total length under 400 words. Tone: {tone}.

Candidate resume:
{resume_text}

Job description:
{jd_text}

Missing skills to incorporate if possible:
{missing_keywords}"""

    try:
        cover_letter = generate_for_task(task="cover_letter", prompt=prompt, max_tokens=1500, temperature=0.7)
        return CoverLetterResponse(cover_letter=cover_letter.strip(), tone=tone)
    except Exception:
        return CoverLetterResponse(
            cover_letter=(
                f"{today}\n\n"
                f"Hiring Manager\n{company_name}\n\n"
                f"Dear Hiring Manager,\n\n"
                f"I am writing to express my strong interest in the {jd_title} position at {company_name}. "
                "My background aligns well with the requirements you have outlined, and I am eager to contribute to your team's goals.\n\n"
                "Throughout my career, I have consistently delivered results through technical expertise and a collaborative approach. "
                "I believe my experience maps directly to the needs of this role.\n\n"
                "I would welcome the opportunity to discuss how my skills and experiences align with your team. "
                "Thank you for your time and consideration.\n\n"
                f"Sincerely,\n{candidate_name}"
            ),
            tone=tone,
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

For each question, provide a STAR method answer framework.

Return a JSON object:
{{
  "questions": [
    {{
      "question": "The interview question",
      "star_framework": "Situation: ... | Task: ... | Action: ... | Result: ..."
    }}
  ]
}}

Mix: behavioral (3), technical (4), situational (2), culture fit (1)."""

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
                star_framework="Situation: The project requiring new tech | Task: What you needed to learn | Action: Learning approach | Result: How quickly you became productive",
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


def rewrite_bullets_gpt(bullets: List[str], jd_text: str) -> List[str]:
    """Rewrite resume bullet points for maximum ATS impact."""
    if not bullets:
        return []

    bullets_formatted = "\n".join(f"- {b}" for b in bullets[:10])

    prompt = f"""Rewrite these resume bullet points to maximize ATS compatibility.

ORIGINAL BULLETS:
{bullets_formatted}

JOB CONTEXT: {jd_text[:500]}

Rules:
1. Start each bullet with a strong past-tense action verb
2. Add quantification where naturally implied
3. Use X-Y-Z formula: "Accomplished [X] as measured by [Y], by doing [Z]"
4. Incorporate relevant keywords from job context
5. Keep the same core facts — NEVER fabricate
6. Keep each bullet under 120 characters

Return a JSON object: {{"bullets": ["rewritten bullet 1", "rewritten bullet 2", ...]}}"""

    try:
        response_text = generate_for_task(task="rewrite_bullets", prompt=prompt, json_mode=True, max_tokens=1000, temperature=0.5)
        data = json.loads(response_text)
        return data.get("bullets", bullets)
    except Exception:
        return bullets
