"""ATS scoring engine for HirePort AI."""
from typing import Any, Dict, List

from app.models.response_models import ATSScoreBreakdown, AnalysisResponse


class ATSScorer:
    """Scores a resume against a job description for ATS compatibility.

    Scoring breakdown:
        - Keyword Match: 40% of total score
        - Skills Coverage: 25% of total score
        - Formatting Compliance: 20% of total score
        - Bullet Strength: 15% of total score
    """

    KEYWORD_WEIGHT: float = 0.40
    SKILLS_WEIGHT: float = 0.25
    FORMAT_WEIGHT: float = 0.20
    BULLET_WEIGHT: float = 0.15

    FORMATTING_PENALTIES: Dict[str, int] = {
        "tables_detected": -8,
        "images_detected": -8,
        "multi_column_layout": -6,
        "missing_contact_section": -5,
        "missing_skills_section": -4,
        "unusual_section_headers": -3,
        "non_standard_date_format": -2,
    }

    def score(
        self,
        matched_keywords: List[str],
        jd_keywords: List[str],
        resume_skills: List[str],
        jd_skills: List[str],
        formatting_issues: List[Dict[str, Any]],
        bullets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate the full ATS score.

        Args:
            matched_keywords: Keywords present in both resume and JD.
            jd_keywords: All keywords extracted from the JD.
            resume_skills: Skills found in the resume.
            jd_skills: Skills required by the JD.
            formatting_issues: List of formatting issue dicts with severity.
            bullets: List of bullet analysis dicts with score field.

        Returns:
            Dictionary with total score, grade, and breakdown sub-scores.
        """
        keyword_score = self._score_keywords(matched_keywords, jd_keywords)
        skills_score = self._score_skills(resume_skills, jd_skills)
        format_score = self._score_formatting(formatting_issues)
        bullet_score = self._score_bullets(bullets)

        # Normalize each sub-score to 0-100
        total = (
            keyword_score * self.KEYWORD_WEIGHT
            + skills_score * self.SKILLS_WEIGHT
            + format_score * self.FORMAT_WEIGHT
            + bullet_score * self.BULLET_WEIGHT
        )

        total = max(0.0, min(100.0, total))

        return {
            "total": round(total),
            "grade": self._to_grade(total),
            "breakdown": {
                "keyword_match": round(keyword_score),
                "skills_coverage": round(skills_score),
                "formatting_compliance": round(format_score),
                "bullet_strength": round(bullet_score),
            },
        }

    def _score_keywords(
        self, matched_keywords: List[str], jd_keywords: List[str]
    ) -> float:
        """Score keyword match quality (returns 0-100)."""
        if not jd_keywords:
            return 75.0  # Neutral score if no JD keywords extracted
        ratio = len(matched_keywords) / len(jd_keywords)
        return min(100.0, ratio * 100.0)

    def _score_skills(
        self, resume_skills: List[str], jd_skills: List[str]
    ) -> float:
        """Score skills coverage (returns 0-100)."""
        if not jd_skills:
            return 75.0
        resume_skills_lower = {s.lower() for s in resume_skills}

        # Also build a set of normalized aliases for fuzzy matching
        resume_aliases: set = set()
        for s in resume_skills_lower:
            resume_aliases.add(s)
            # Strip common suffixes: "react.js" → "react", "node.js" → "node"
            resume_aliases.add(s.replace(".js", "").replace(".ts", ""))
            # Add with suffix: "react" → "react.js"
            resume_aliases.add(s + ".js")
            # Common expansions
            resume_aliases.add(s.replace("postgres", "postgresql"))
            resume_aliases.add(s.replace("postgresql", "postgres"))
            resume_aliases.add(s.replace("k8s", "kubernetes"))
            resume_aliases.add(s.replace("kubernetes", "k8s"))

        matched = 0
        for s in jd_skills:
            s_lower = s.lower()
            s_stripped = s_lower.replace(".js", "").replace(".ts", "")
            if s_lower in resume_aliases or s_stripped in resume_aliases:
                matched += 1

        ratio = matched / len(jd_skills)
        return min(100.0, ratio * 100.0)

    def _score_formatting(
        self, formatting_issues: List[Dict[str, Any]]
    ) -> float:
        """Score formatting compliance (returns 0-100)."""
        score = 100.0
        for issue in formatting_issues:
            severity = issue.get("severity", "info")
            if severity == "critical":
                score -= 8
            elif severity == "warning":
                score -= 3
            else:
                score -= 1
        return max(0.0, score)

    def _score_bullets(self, bullets: List[Dict[str, Any]]) -> float:
        """Score bullet point quality (returns 0-100)."""
        if not bullets:
            return 60.0  # Neutral if no bullets found
        scores = [b.get("score", 5) for b in bullets]
        avg = sum(scores) / len(scores)
        # Normalize from 0-10 scale to 0-100
        return min(100.0, (avg / 10.0) * 100.0)

    def _to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 93:
            return "A"
        elif score >= 90:
            return "A-"
        elif score >= 87:
            return "B+"
        elif score >= 83:
            return "B"
        elif score >= 80:
            return "B-"
        elif score >= 77:
            return "C+"
        elif score >= 73:
            return "C"
        elif score >= 70:
            return "C-"
        elif score >= 67:
            return "D+"
        elif score >= 60:
            return "D"
        else:
            return "F"
