"""Bullet point analyzer and strength scorer."""
import re
from typing import List

from app.models.response_models import BulletAnalysis

# Strong action verbs for resume bullets
IMPACT_VERBS: List[str] = [
    "Achieved", "Accelerated", "Architected", "Automated", "Built", "Championed",
    "Collaborated", "Consolidated", "Contributed", "Created", "Cut", "Decreased",
    "Defined", "Delivered", "Deployed", "Designed", "Developed", "Directed",
    "Drove", "Eliminated", "Enabled", "Engineered", "Enhanced", "Established",
    "Executed", "Expanded", "Generated", "Grew", "Identified", "Implemented",
    "Improved", "Increased", "Initiated", "Integrated", "Launched", "Led",
    "Managed", "Mentored", "Modernized", "Negotiated", "Optimized", "Orchestrated",
    "Overhauled", "Owned", "Partnered", "Pioneered", "Planned", "Reduced",
    "Refactored", "Released", "Replaced", "Resolved", "Scaled", "Shaped",
    "Simplified", "Spearheaded", "Streamlined", "Transformed", "Trained",
    "Upgraded", "Utilized",
]

IMPACT_VERBS_LOWER = {v.lower() for v in IMPACT_VERBS}

# Patterns indicating quantified achievements
METRIC_PATTERNS = [
    r"\d+%",
    r"\$\d+",
    r"\d+x\b",
    r"\d+\s*(million|billion|thousand|k)\b",
    r"\d+\s*(users|customers|clients|team members|engineers|people)",
    r"\d+\s*(hours|days|weeks|months)",
    r"reduced by \d+",
    r"increased by \d+",
    r"saved \d+",
    r"generated \d+",
]

METRIC_RE = re.compile("|".join(METRIC_PATTERNS), re.IGNORECASE)


def score_bullet(bullet: str, jd_text: str = "") -> int:
    """Score a resume bullet point on quality (0-10).

    Scoring criteria:
        - Starts with impact verb: +3 points
        - Contains quantified metric: +3 points
        - Has sufficient length/specificity: +2 points
        - Relevant to JD (if provided): +2 points

    Args:
        bullet: The bullet point text.
        jd_text: Optional job description for relevance check.

    Returns:
        Score from 0 to 10.
    """
    score = 0
    first_word = bullet.strip().split()[0].lower().rstrip(".,;:") if bullet.strip() else ""

    # Check for impact verb
    if first_word in IMPACT_VERBS_LOWER:
        score += 3
    elif any(bullet.lower().startswith(v.lower()) for v in IMPACT_VERBS):
        score += 2

    # Check for metrics
    if METRIC_RE.search(bullet):
        score += 3

    # Length / specificity check
    word_count = len(bullet.split())
    if word_count >= 15:
        score += 2
    elif word_count >= 8:
        score += 1

    # JD relevance (basic keyword overlap)
    if jd_text:
        jd_words = set(jd_text.lower().split())
        bullet_words = set(bullet.lower().split())
        overlap = bullet_words & jd_words
        if len(overlap) >= 3:
            score += 2
        elif len(overlap) >= 1:
            score += 1

    return min(10, score)


def identify_issues(bullet: str) -> List[str]:
    """Identify specific weaknesses in a resume bullet point.

    Args:
        bullet: The bullet point text.

    Returns:
        List of issue description strings.
    """
    issues: List[str] = []
    first_word = bullet.strip().split()[0].lower().rstrip(".,;:") if bullet.strip() else ""

    if first_word not in IMPACT_VERBS_LOWER:
        issues.append("Does not start with a strong action verb")

    if not METRIC_RE.search(bullet):
        issues.append("No quantified metrics or measurable impact")

    word_count = len(bullet.split())
    if word_count < 8:
        issues.append("Too brief — add more context and specificity")
    elif word_count > 40:
        issues.append("Too long — consider splitting or condensing")

    if re.search(r"\b(responsible for|worked on|helped with|assisted in)\b", bullet, re.IGNORECASE):
        issues.append("Passive phrasing detected — use direct action verbs")

    return issues


def rewrite_bullet_locally(bullet: str) -> str:
    """Generate a locally-improved version of a bullet point without GPT.

    Uses template-based improvements based on detected issues.

    Args:
        bullet: The original bullet point text.

    Returns:
        Improved bullet point string.
    """
    rewritten = bullet.strip()

    # Replace weak openers
    weak_starts = {
        r"^responsible for\s+": "Led ",
        r"^helped (to\s+)?": "Contributed to ",
        r"^worked on\s+": "Developed ",
        r"^assisted (in\s+)?": "Supported ",
        r"^was involved in\s+": "Participated in ",
        r"^part of\s+": "Collaborated on ",
    }
    for pattern, replacement in weak_starts.items():
        rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)

    # If no metric exists, append a suggestion placeholder
    if not METRIC_RE.search(rewritten):
        rewritten = rewritten.rstrip(".") + ", resulting in measurable improvement"

    # Ensure starts with capital
    if rewritten:
        rewritten = rewritten[0].upper() + rewritten[1:]

    return rewritten


def analyze_bullets(bullets: List[str], jd_text: str = "") -> List[BulletAnalysis]:
    """Analyze all resume bullet points.

    Args:
        bullets: List of bullet point strings from the resume.
        jd_text: Job description text for relevance scoring.

    Returns:
        List of BulletAnalysis objects.
    """
    analyses: List[BulletAnalysis] = []
    for bullet in bullets[:20]:  # Cap at 20 bullets for performance
        if not bullet.strip():
            continue
        s = score_bullet(bullet, jd_text)
        issues = identify_issues(bullet)
        rewritten = rewrite_bullet_locally(bullet) if s < 7 else bullet
        analyses.append(
            BulletAnalysis(
                original=bullet,
                score=s,
                issues=issues,
                rewritten=rewritten,
            )
        )
    return analyses
