"""AI service — LLM-powered resume optimization features.

Uses the LLM provider abstraction so the same prompts work with
Gemini, Claude, or any future provider.
"""
import json
from typing import Any, Dict, List

from app.schemas.responses import (
    CoverLetterResponse,
    InterviewPrepResponse,
    InterviewQuestion,
    RewriteResponse,
    RewriteSection,
)
from app.services.llm.factory import get_llm_provider


def _generate(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    json_mode: bool = False,
) -> str:
    """Send a prompt to the active LLM provider."""
    provider = get_llm_provider()
    return provider.generate(prompt, temperature, max_tokens, json_mode)


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
        response_text = _generate(prompt, temperature=0.6, max_tokens=800, json_mode=True)
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


def generate_resume_rewrite(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
) -> RewriteResponse:
    """Generate an ATS-optimized rewrite of the resume."""
    resume_text = resume_data.get("full_text", "")[:4000]
    jd_skills = ", ".join(jd_requirements.get("all_skills", [])[:30])
    jd_title = jd_requirements.get("job_title", "the role")
    required_skills = ", ".join(jd_requirements.get("required_skills", [])[:20])

    prompt = f"""You are a professional resume writer and ATS optimization specialist.
Your task is to rewrite the candidate's resume so it passes ATS screening for the target role.

CRITICAL RULES:
1. PRESERVE THE EXACT FORMAT: Keep the same section order, headings, company names, job titles, dates, and layout.
2. ONLY REWRITE BULLET POINTS AND SUMMARIES: Improve language, keyword density, and impact. Do NOT change headings, company names, titles, education entries, or dates.
3. USE STRONG ACTION VERBS: Start each bullet with a powerful past-tense action verb.
4. ADD QUANTIFICATION: Use the X-Y-Z formula: "Accomplished [X] as measured by [Y], by doing [Z]".
5. INCORPORATE TARGET KEYWORDS NATURALLY: Weave in required skills where they genuinely apply.
6. NEVER FABRICATE: Do not invent experiences, skills, or achievements not in the original.
7. ATS-FRIENDLY FORMATTING: Use standard headings. Avoid tables, columns, or special characters.
8. SKILLS SECTION: List all relevant technologies from the original resume and job description.

ORIGINAL RESUME:
---
{resume_text}
---

TARGET ROLE: {jd_title}
REQUIRED SKILLS: {required_skills}
ALL JD KEYWORDS: {jd_skills}

Return a JSON object:
{{
  "sections": [
    {{"title": "<exact section heading from original>", "content": "<optimized content>"}},
    ...
  ],
  "full_text": "Complete rewritten resume as a single string, preserving original format with optimized bullets"
}}"""

    try:
        response_text = _generate(prompt, temperature=0.4, max_tokens=3500, json_mode=True)
        data = json.loads(response_text)
        sections = [
            RewriteSection(title=s["title"], content=s["content"])
            for s in data.get("sections", [])
        ]
        return RewriteResponse(
            sections=sections,
            full_text=data.get("full_text", resume_text),
        )
    except Exception:
        sections_data = resume_data.get("sections", {})
        sections = [
            RewriteSection(title=k.title(), content=v)
            for k, v in sections_data.items()
        ]
        return RewriteResponse(
            sections=sections if sections else [RewriteSection(title="Resume", content=resume_text)],
            full_text=resume_text,
        )


def generate_cover_letter(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    tone: str = "professional",
) -> CoverLetterResponse:
    """Generate a personalized cover letter."""
    resume_text = resume_data.get("full_text", "")[:2500]
    jd_title = jd_requirements.get("job_title", "this role")
    required_skills = ", ".join(jd_requirements.get("required_skills", [])[:15])
    all_skills = ", ".join(jd_requirements.get("all_skills", [])[:20])

    tone_instructions = {
        "professional": "formal and polished, using professional business language",
        "confident": "assertive and direct, highlighting achievements boldly without arrogance",
        "conversational": "warm and personable, showing personality while remaining professional",
    }
    tone_desc = tone_instructions.get(tone, tone_instructions["professional"])

    prompt = f"""You are a professional career coach and hiring manager.
Write a high-quality cover letter that follows the correct modern format.

CANDIDATE BACKGROUND:
---
{resume_text}
---

TARGET ROLE: {jd_title}
REQUIRED SKILLS: {required_skills}
JD KEYWORDS: {all_skills}
TONE: {tone_desc}

Follow this EXACT structure:

1. GREETING: "Dear Hiring Manager,"
2. OPENING PARAGRAPH: State the role, briefly introduce the candidate, express enthusiasm.
3. MIDDLE PARAGRAPH(S) (1-2 paragraphs): Highlight key experiences, relevant skills, measurable results.
4. COMPANY FIT PARAGRAPH: Why this role/company, how goals align, specific value the candidate brings.
5. CLOSING PARAGRAPH: Express enthusiasm, thank the reader, invite further discussion.
6. SIGN-OFF: "Sincerely," "[Candidate Name from resume]"

GUIDELINES:
- Tone: {tone_desc}
- Length: 250-400 words
- No generic phrases like "I am a hard worker"
- No [brackets] or placeholders
- Only reference experiences from the resume
- Extract the candidate's actual name from the resume for the sign-off

Return only the cover letter text."""

    try:
        cover_letter = _generate(prompt, temperature=0.7, max_tokens=900)
        return CoverLetterResponse(cover_letter=cover_letter.strip(), tone=tone)
    except Exception:
        return CoverLetterResponse(
            cover_letter=(
                f"Dear Hiring Manager,\n\nI am writing to express my strong interest in the {jd_title} position. "
                f"My background aligns well with the requirements you have outlined, particularly in {required_skills[:100]}. "
                "I am eager to bring my expertise to your team and contribute meaningfully to your organization's goals.\n\n"
                "Throughout my career, I have consistently delivered results through my technical expertise and collaborative approach. "
                "I would welcome the opportunity to further discuss how my skills and experiences align with your team's goals. "
                "Thank you for your time and consideration.\n\nSincerely,\nThe Applicant"
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
        response_text = _generate(prompt, temperature=0.7, max_tokens=2000, json_mode=True)
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
        response_text = _generate(prompt, temperature=0.5, max_tokens=1000, json_mode=True)
        data = json.loads(response_text)
        return data.get("bullets", bullets)
    except Exception:
        return bullets
