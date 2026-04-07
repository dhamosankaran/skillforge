"""Resume template definitions for AI-powered rewriting.

Three university-style templates, each suited to different career fields.
The AI uses these as structural guides when rewriting a user's resume.
"""

from typing import Any, Dict, List

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "general": {
        "name": "General / STEM",
        "description": "Classic single-column format for STEM, engineering, and general roles.",
        "sections_order": [
            "EDUCATION",
            "EXPERIENCE",
            "PROJECTS",
            "LEADERSHIP & COMMUNITY INVOLVEMENT",
            "SKILLS",
            "HONORS AND AWARDS",
        ],
        "section_guidelines": {
            "EDUCATION": (
                "University name, City, State right-aligned with graduation date (Month Year).\n"
                "Degree line: Bachelor of Science in {major}, GPA X.XX\n"
                "Optional: Certificate or Minor, Relevant Coursework."
            ),
            "EXPERIENCE": (
                "Reverse chronological. Each entry:\n"
                "EMPLOYER, City, State (abbreviated) right-aligned Month Year - Month Year\n"
                "Position Title in italics.\n"
                "Bullet points starting with STRONG action verbs. Describe task/duty, actions, and results.\n"
                "Use X-Y-Z formula: Accomplished [X] as measured by [Y] by doing [Z]."
            ),
            "PROJECTS": (
                "PROJECT NAME right-aligned Month Year.\n"
                "Bullets describing academic or personal projects relevant to the target role.\n"
                "Include results, accomplishments, outcomes, and skills used."
            ),
            "LEADERSHIP & COMMUNITY INVOLVEMENT": (
                "ORGANIZATION, City, State right-aligned Month Year - Month Year.\n"
                "Position Title.\n"
                "Bullets for volunteer work, student orgs, campus engagement."
            ),
            "SKILLS": (
                "Technical/Computer Skills: list with proficiency levels (Proficient, Intermediate, Basic).\n"
                "Languages: with proficiency (Basic, Intermediate, Advanced, Fluent).\n"
                "Certifications: optional."
            ),
            "HONORS AND AWARDS": (
                "Bullet list of honors/awards. Keep concise — name only, no details."
            ),
        },
        "example_header": (
            "BEVO LONGHORN\n"
            "512-123-4567 | bevo.longhorn@utexas.edu | linkedin.com/in/bevolonghorn | Austin, TX"
        ),
    },
    "business": {
        "name": "Business / Non-Technical",
        "description": "Tailored for business, finance, healthcare, marketing, and non-technical roles.",
        "sections_order": [
            "EDUCATION",
            "EXPERIENCE",
            "CAMPUS INVOLVEMENT",
            "SKILLS",
        ],
        "section_guidelines": {
            "EDUCATION": (
                "University name, City, State right-aligned with graduation date (Month Year).\n"
                "Degree line: Bachelor of Science & Arts in {major}, GPA X.XX\n"
                "Optional: Minor(s)."
            ),
            "EXPERIENCE": (
                "Reverse chronological. Each entry:\n"
                "EMPLOYER, City, State right-aligned Month Year - Month Year\n"
                "Position Title in italics.\n"
                "Bullets: lead with action verbs, emphasize collaboration, communication, and quantified impact.\n"
                "Focus on business outcomes: revenue, efficiency, stakeholder engagement, process improvement."
            ),
            "CAMPUS INVOLVEMENT": (
                "ORGANIZATION, City, State right-aligned Month Year - Month Year.\n"
                "Position Title.\n"
                "Bullets for student leadership, recruitment, outreach, event coordination."
            ),
            "SKILLS": (
                "Computer Skills: Microsoft Office suite, analytics tools, CRM systems.\n"
                "Languages: with proficiency level."
            ),
        },
        "example_header": (
            "BAILEY BUSINESS\n"
            "bailey.business@utexas.edu | linkedin.com/in/BaileyBusiness | Austin, TX | (512) 555-5555"
        ),
    },
    "data_science": {
        "name": "Data Science / Technical",
        "description": "Optimized for data science, analytics, research, and technical computing roles.",
        "sections_order": [
            "EDUCATION",
            "TECHNICAL SKILLS",
            "DATA SCIENCE EXPERIENCE",
            "PROJECTS",
            "TEACHING EXPERIENCE",
        ],
        "section_guidelines": {
            "EDUCATION": (
                "University name, City, State right-aligned with graduation date (Month Year).\n"
                "Degree line: Bachelor of Science in {major}, GPA X.XX\n"
                "Optional: Certificate.\n"
                "Relevant Coursework: list 3-5 most relevant courses."
            ),
            "TECHNICAL SKILLS": (
                "Single line or two listing technical skills with proficiency:\n"
                "Proficient in X, Y; Familiar with Z; Exposed to W.\n"
                "Place this section HIGH — right after education — so ATS picks it up immediately."
            ),
            "DATA SCIENCE EXPERIENCE": (
                "Reverse chronological. Each entry:\n"
                "EMPLOYER, City, State right-aligned Month Year - Month Year\n"
                "Position Title.\n"
                "Bullets: emphasize data tools, analytics platforms, quantified findings.\n"
                "Mention specific technologies: Python, R, SQL, Tableau, dashboards, models, datasets."
            ),
            "PROJECTS": (
                "PROJECT NAME - brief description as a single bullet or short paragraph.\n"
                "Emphasize tools used, datasets processed, and outcomes."
            ),
            "TEACHING EXPERIENCE": (
                "DEPARTMENT / INSTITUTION right-aligned Month Year - Month Year.\n"
                "Position Title.\n"
                "Bullets: student counts, collaboration with faculty, curriculum support."
            ),
        },
        "example_header": (
            "DAISUKE DATA SCIENCE\n"
            "daisuke.datascience@utexas.edu | linkedin.com/in/daisukedatascience | Austin, TX | (512) 555-5555"
        ),
    },
}


def get_template(template_type: str) -> Dict[str, Any]:
    """Return the template dict for the given type, defaulting to 'general'."""
    return TEMPLATES.get(template_type, TEMPLATES["general"])


def get_template_names() -> List[Dict[str, str]]:
    """Return list of available template names and descriptions."""
    return [
        {"id": key, "name": val["name"], "description": val["description"]}
        for key, val in TEMPLATES.items()
    ]


def auto_select_template(major: str, job_title: str) -> str:
    """Auto-select the best template based on the user's major and target job.

    Returns one of: 'general', 'business', 'data_science'.
    """
    combined = f"{major} {job_title}".lower()

    data_keywords = {
        "data science", "data analyst", "data engineer", "machine learning",
        "analytics", "bioinformatics", "computational", "statistics",
        "ai ", "artificial intelligence", "deep learning", "nlp",
    }
    business_keywords = {
        "business", "finance", "marketing", "accounting", "management",
        "consulting", "economics", "mba", "entrepreneurship", "supply chain",
        "operations", "human resources", "hr ", "sales", "real estate",
    }

    for kw in data_keywords:
        if kw in combined:
            return "data_science"
    for kw in business_keywords:
        if kw in combined:
            return "business"

    return "general"
