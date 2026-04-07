"""Google Gemini service for AI-powered resume optimization features."""
import json
from typing import Any, Dict, List, Optional

from app.models.response_models import (
    CoverLetterResponse,
    InterviewPrepResponse,
    InterviewQuestion,
    RewriteEntry,
    RewriteHeader,
    RewriteResponse,
    RewriteSection,
)


def _get_client():
    """Lazy-load the Gemini client."""
    try:
        from google import genai
        from app.config import get_settings
        settings = get_settings()
        if not settings.gemini_api_key:
            return None, None
        client = genai.Client(api_key=settings.gemini_api_key)
        return client, settings.gemini_model
    except Exception:
        return None, None


def _generate(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    json_mode: bool = False,
) -> str:
    """Send a prompt to Gemini and return the response text.

    Args:
        prompt: The full prompt string.
        temperature: Sampling temperature (0.0 - 1.0).
        max_tokens: Maximum output tokens.
        json_mode: Whether to request JSON-formatted output.

    Returns:
        Response text string.

    Raises:
        RuntimeError: If Gemini client is not configured.
    """
    from google.genai import types

    client, model_name = _get_client()
    if client is None:
        raise RuntimeError("Gemini API key not configured")

    config_kwargs: Dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return response.text or ""


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
    template_type: str = "general",
    major: Optional[str] = None,
    missing_keywords: Optional[List[str]] = None,
    missing_skills: Optional[List[str]] = None,
) -> RewriteResponse:
    """Generate an ATS-optimized rewrite of the resume.

    Automatically analyzes the resume content to determine the best structure
    and sections. Returns structured data (header, sections with typed entries)
    so the frontend can render a properly formatted resume.
    """
    resume_text = resume_data.get("full_text", "")[:4000]
    resume_skills = resume_data.get("skills", [])
    jd_skills = ", ".join(jd_requirements.get("all_skills", [])[:30])
    jd_title = jd_requirements.get("job_title", "the role")
    required_skills = ", ".join(jd_requirements.get("required_skills", [])[:20])
    responsibilities = jd_requirements.get("responsibilities", [])[:10]

    # Build gap analysis context for the AI
    missing_kw_str = ", ".join((missing_keywords or [])[:30])
    missing_sk_str = ", ".join((missing_skills or [])[:20])
    resume_sk_str = ", ".join(resume_skills[:30])
    resp_str = "\n".join(f"- {r}" for r in responsibilities) if responsibilities else "N/A"

    prompt = f"""You are an elite ATS optimization expert. Your job is to rewrite this resume so it achieves the HIGHEST POSSIBLE ATS score for the target role.

═══ ATS SCORING SYSTEM (your rewrite will be scored on these exact criteria) ═══

1. KEYWORD MATCH (40% of score):
   The system extracts TF-IDF keywords from the job description and checks if each one appears in the resume text. Every keyword you include directly increases the score.

   MISSING KEYWORDS TO ADD: [{missing_kw_str}]
   ↳ You MUST weave as many of these as possible into bullet points and the skills section. Use the EXACT keyword phrasing where natural.

2. SKILLS COVERAGE (25% of score):
   The system checks how many JD skills appear in the resume's skill list (exact match, case-insensitive).

   SKILLS ALREADY ON RESUME: [{resume_sk_str}]
   MISSING SKILLS TO ADD: [{missing_sk_str}]
   ↳ Add EVERY missing skill that the candidate could plausibly have based on their experience. Put them in the SKILLS section. If they used Python, they likely know pip, virtual environments, etc. If they used React, they likely know HTML, CSS, JavaScript. If they managed a team, they have Leadership, Communication, Project Management. Use your professional judgment to infer adjacent skills from their experience — but NEVER add skills that are completely unrelated to anything in their background.

3. FORMATTING (20% of score):
   Standard ATS-friendly section headings (EDUCATION, EXPERIENCE, SKILLS, etc.), single column, no tables/graphics/special characters. Include contact info in header.

4. BULLET STRENGTH (15% of score):
   Each bullet is scored 0-10 based on:
   - Starts with a strong past-tense ACTION VERB (+3 pts): Achieved, Engineered, Spearheaded, Optimized, Deployed, Reduced, Increased, Led, Built, Automated, Streamlined, Implemented, Designed, Developed, Delivered, Managed, Created, Launched, Integrated, Architected
   - Contains QUANTIFIED METRICS like %, $, numbers (+3 pts): "by 40%", "$50K", "15 team members", "3x improvement"
   - Has 15+ words of specific detail (+2 pts)
   - Contains JD-relevant keywords (+2 pts)
   ↳ EVERY bullet must start with an action verb, include a number/metric, and mention a JD keyword.

═══ JOB CONTEXT ═══

TARGET ROLE: {jd_title}
ALL JD SKILLS: {jd_skills}
REQUIRED SKILLS: {required_skills}
KEY RESPONSIBILITIES:
{resp_str}

═══ SECTION MAPPING ═══

Read the original resume and map its content to these standard sections:
- Education → "EDUCATION"
- Work experience / internships → "EXPERIENCE"
- Leadership roles, clubs, organizations → "LEADERSHIP & COMMUNITY INVOLVEMENT"
- Personal or academic projects → "PROJECTS"
- Research → "RESEARCH EXPERIENCE"
- Teaching / tutoring → "TEACHING EXPERIENCE"
- Volunteer work → "VOLUNTEER EXPERIENCE"
- Awards, honors, scholarships → "HONORS & AWARDS"
- Certifications → "CERTIFICATIONS"
- Skills → "SKILLS"

═══ CRITICAL RULES ═══

1. NEVER FABRICATE: Keep real company names, titles, dates, GPA. Do NOT invent new jobs, projects, or experiences. Only create sections for content that EXISTS in the original.
2. OPTIMIZE WORDING: Reposition and reword existing experience to emphasize relevance to the target role. Frame the SAME work using JD language.
3. INFER REASONABLE METRICS: If the original says "improved performance", you can say "Improved performance by 25%" if the context supports it. If they "led a team", estimate the size from context. Keep inferences realistic.
4. HEADER: Extract REAL name, email, phone, LinkedIn, location. NEVER use placeholders.
5. ORG NAMES: Copy EXACTLY from original resume.
6. ENTRIES vs CONTENT: Experience-type sections use "entries" array. Skills/Honors use "content" string.
7. SKILLS SECTION: Group by category. Include ALL skills from original resume PLUS plausible missing skills. This section alone drives 25% of the score.
8. BULLETS: 2-4 per entry. Every bullet = action verb + what you did + quantified result + JD keyword.
9. REORDER sections to put most relevant experience first (e.g., if applying for a tech role, put EXPERIENCE before LEADERSHIP).
10. FULL_TEXT: Must contain the complete rewritten resume as plain text.

═══ JSON OUTPUT FORMAT ═══

{{
  "header": {{"name": "Full Name", "contact": "phone | email | linkedin | City, State"}},
  "sections": [
    {{"title": "EDUCATION", "content": "", "entries": [{{"org": "University Name, City, State", "date": "May 2024", "title": "Bachelor of Science in Major, GPA: X.XX", "details": ["Relevant Coursework: Course1, Course2, Course3"], "bullets": []}}]}},
    {{"title": "EXPERIENCE", "content": "", "entries": [{{"org": "Company Name", "date": "June 2023 - Present", "title": "Job Title", "details": [], "bullets": ["Engineered automated data pipeline using Python and AWS Lambda, reducing processing time by 40% and saving 15 engineering hours weekly"]}}]}},
    {{"title": "SKILLS", "content": "Programming Languages: Python, Java, JavaScript\\nFrameworks: React, Node.js, FastAPI\\nTools: Git, Docker, AWS, Kubernetes\\nSoft Skills: Leadership, Communication, Agile", "entries": []}}
  ],
  "full_text": "Complete resume as plain text"
}}

═══ ORIGINAL RESUME ═══

{resume_text}"""

    try:
        response_text = _generate(prompt, temperature=0.4, max_tokens=4000, json_mode=True)
        data = json.loads(response_text)

        header = RewriteHeader(
            name=data.get("header", {}).get("name", ""),
            contact=data.get("header", {}).get("contact", ""),
        )

        sections = []
        for s in data.get("sections", []):
            entries = []
            for e in s.get("entries", []):
                entries.append(RewriteEntry(
                    org=e.get("org", ""),
                    location=e.get("location", ""),
                    date=e.get("date", ""),
                    title=e.get("title", ""),
                    bullets=e.get("bullets", []),
                    details=e.get("details", []),
                ))
            sections.append(RewriteSection(
                title=s.get("title", ""),
                content=s.get("content", ""),
                entries=entries,
            ))

        return RewriteResponse(
            header=header,
            sections=sections,
            full_text=data.get("full_text", resume_text),
            template_type=template_type,
        )
    except Exception:
        sections_data = resume_data.get("sections", {})
        sections = [
            RewriteSection(title=k.title(), content=v)
            for k, v in sections_data.items()
        ]
        return RewriteResponse(
            header=RewriteHeader(),
            sections=sections if sections else [RewriteSection(title="Resume", content=resume_text)],
            full_text=resume_text,
            template_type=template_type,
        )


def generate_cover_letter(
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any],
    tone: str = "professional",
) -> CoverLetterResponse:
    """Generate a personalized cover letter following a professional format."""
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

    prompt = f"""You are a professional career coach. Write a cover letter following this EXACT template format.

CANDIDATE RESUME:
---
{resume_text}
---

TARGET ROLE: {jd_title}
REQUIRED SKILLS: {required_skills}
JD KEYWORDS: {all_skills}
TONE: {tone_desc}

OUTPUT THIS EXACT FORMAT (fill in real data, no placeholders or brackets):

[Candidate's Full Name]
[City, State] | [Phone] | [Email] | [LinkedIn URL]

[Today's Date written as: Month Day, Year]

Dear Hiring Manager,

[INTRO PARAGRAPH - 3-4 sentences: Who you are, what role you're applying for, why you're excited about this specific position. If relevant, mention your major/degree and how it connects to the role.]

[MIDDLE PARAGRAPH - 4-5 sentences: Highlight 2-3 specific experiences from your resume with concrete examples. Show how your transferable and technical skills match the job requirements. Use specific numbers/metrics where possible. Do NOT copy resume bullets verbatim — expand on them.]

[CLOSING PARAGRAPH - 2-3 sentences: Summarize your qualifications, reiterate interest in the role, express enthusiasm about contributing to the team. Thank them for considering your application.]

Respectfully yours,

[Candidate's Full Name]

RULES:
- Extract the candidate's REAL name, contact info from the resume. NO placeholders.
- Tone: {tone_desc}
- Length: 250-350 words (body only, not counting header/sign-off)
- No generic filler ("I am a hard worker", "I am passionate")
- Only reference real experiences from the resume
- Make it specific to the target role and required skills
- End with "Respectfully yours," followed by the candidate's name"""

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
                "I have developed strong competencies that directly align with the skills your team is seeking, and I am confident "
                "these experiences position me well for this opportunity.\n\n"
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
        response_text = _generate(prompt, temperature=0.5, max_tokens=1000, json_mode=True)
        data = json.loads(response_text)
        return data.get("bullets", bullets)
    except Exception:
        return bullets
