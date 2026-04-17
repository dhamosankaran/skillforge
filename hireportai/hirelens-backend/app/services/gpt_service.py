"""AI-powered resume optimization features (legacy routes).

Now delegates to the multi-model LLM router instead of calling Gemini directly.
"""
import json
from typing import Any, Dict, List, Optional

from app.core.llm_router import generate_for_task
from app.models.response_models import (
    CoverLetterResponse,
    InterviewPrepResponse,
    InterviewQuestion,
    RewriteHeader,
    RewriteResponse,
)


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


def generate_resume_rewrite(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    template_type: str = "general",
    major: Optional[str] = None,
    missing_keywords: Optional[List[str]] = None,
    missing_skills: Optional[List[str]] = None,
) -> RewriteResponse:
    """Generate an ATS-optimized rewrite of the resume.

    Returns the rewritten resume as clean markdown in ``full_text``.
    """
    resume_text = resume_data.get("full_text", "")[:40000]
    jd_title = jd_requirements.get("job_title", "the role")
    missing_kw_str = ", ".join((missing_keywords or jd_requirements.get("all_skills", []))[:30])

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

Missing keywords to incorporate: {missing_kw_str}
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
            template_type=template_type,
        )
    except Exception:
        return RewriteResponse(
            header=RewriteHeader(),
            sections=[],
            full_text=resume_text,
            template_type=template_type,
        )


def generate_cover_letter(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    tone: str = "professional",
) -> CoverLetterResponse:
    """Generate a personalized cover letter in markdown."""
    resume_text = resume_data.get("full_text", "")[:2500]
    jd_title = jd_requirements.get("job_title", "this role")
    jd_text = jd_requirements.get("full_text", "")[:1500]
    missing_keywords = ", ".join(jd_requirements.get("missing_keywords", jd_requirements.get("all_skills", []))[:20])

    prompt = f"""You are an expert career coach writing a compelling cover letter.
Write a cover letter for the candidate applying to the target role.

Structure it as:

## Opening
Hook the reader with enthusiasm for the specific company and role. 2-3 sentences.

## Why I'm a Fit
Connect 3-4 of the candidate's strongest skills and experiences to the job requirements. Use specific examples from their resume.

## Key Achievement
One specific, quantified accomplishment that demonstrates impact relevant to this role.

## Closing
Express enthusiasm, request an interview, professional sign-off.

Keep it under 400 words. Tone: confident, specific, not generic.
Output in clean markdown.

Candidate resume:
{resume_text}

Job description:
{jd_text}

Missing skills to address if possible:
{missing_keywords}"""

    try:
        cover_letter = generate_for_task(task="cover_letter", prompt=prompt, max_tokens=900, temperature=0.7)
        return CoverLetterResponse(cover_letter=cover_letter.strip(), tone=tone)
    except Exception:
        return CoverLetterResponse(
            cover_letter=(
                f"Dear Hiring Manager,\n\nI am writing to express my strong interest in the {jd_title} position. "
                "My background aligns well with the requirements you have outlined. "
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
