"""TF-IDF keyword extraction and matching service."""
import re
from typing import Any, Dict, List, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.utils.text_cleaner import lowercase_and_strip

# Words to exclude from keyword extraction
EXTRA_STOP_WORDS = {
    "experience", "work", "years", "year", "looking", "seeking", "opportunity",
    "company", "team", "strong", "good", "excellent", "great", "ability",
    "knowledge", "understanding", "familiarity", "willing", "demonstrated",
    "proven", "established", "history", "background", "including", "using",
    "related", "relevant", "required", "preferred", "nice", "bonus", "plus",
    "also", "well", "etc", "etc.", "e.g", "i.e", "ie", "eg",
}


def extract_keywords(text: str, n: int = 50) -> List[Tuple[str, float]]:
    """Extract top N keywords from text using TF-IDF.

    Args:
        text: Input text to extract keywords from.
        n: Maximum number of keywords to return.

    Returns:
        List of (keyword, tfidf_score) tuples sorted by score descending.
    """
    if not text or len(text.strip()) < 10:
        return []

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=500,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]

        # Create keyword-score pairs
        keyword_scores: List[Tuple[str, float]] = []
        for word, score in zip(feature_names, scores):
            if score > 0 and word not in EXTRA_STOP_WORDS and len(word) > 2:
                # Filter purely numeric tokens
                if not re.match(r"^\d+$", word):
                    keyword_scores.append((word, float(score)))

        # Sort by score descending
        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        return keyword_scores[:n]

    except Exception:
        # Fallback: simple word frequency
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9\+\#\.]*\b", text.lower())
        freq: Dict[str, int] = {}
        for word in words:
            if word not in EXTRA_STOP_WORDS and len(word) > 2:
                freq[word] = freq.get(word, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [(w, float(c)) for w, c in sorted_words[:n]]


def match_keywords(
    resume_text: str,
    jd_text: str,
    jd_skills: List[str],
    n_keywords: int = 40,
) -> Dict[str, Any]:
    """Match keywords between resume and job description.

    Args:
        resume_text: Plain text of the resume.
        jd_text: Plain text of the job description.
        jd_skills: Skills already extracted from JD.
        n_keywords: Number of JD keywords to consider.

    Returns:
        Dictionary with matched, missing, and frequency data.
    """
    # Extract keywords from JD
    jd_keywords_scored = extract_keywords(jd_text, n=n_keywords)
    jd_keywords_set: Set[str] = {kw.lower() for kw, _ in jd_keywords_scored}

    # Add JD skills to the keyword set
    for skill in jd_skills:
        jd_keywords_set.add(skill.lower())

    # Build resume keyword set
    resume_keywords_scored = extract_keywords(resume_text, n=n_keywords * 2)
    resume_keywords_set: Set[str] = {kw.lower() for kw, _ in resume_keywords_scored}

    # Also do a direct substring search for skills
    resume_lower = resume_text.lower()

    matched: List[str] = []
    missing: List[str] = []
    frequency_data: List[Dict[str, Any]] = []

    for kw, jd_score in jd_keywords_scored:
        kw_lower = kw.lower()
        # Check if keyword appears in resume — try multiple strategies
        # 1. Exact match in TF-IDF extracted keywords
        # 2. Word-boundary regex search in full resume text
        # 3. Substring containment for multi-word terms (e.g. "data analysis")
        # 4. Check each word of multi-word keywords individually
        in_resume = (
            kw_lower in resume_keywords_set
            or re.search(r"\b" + re.escape(kw_lower) + r"\b", resume_lower) is not None
        )
        # For multi-word keywords, check if all individual words appear nearby
        if not in_resume and " " in kw_lower:
            parts = kw_lower.split()
            in_resume = all(
                re.search(r"\b" + re.escape(p) + r"\b", resume_lower) is not None
                for p in parts if len(p) > 2
            )

        resume_count = sum(
            1 for _ in re.finditer(r"\b" + re.escape(kw_lower) + r"\b", resume_lower)
        )
        jd_count = sum(
            1 for _ in re.finditer(r"\b" + re.escape(kw_lower) + r"\b", jd_text.lower())
        )

        frequency_data.append({
            "keyword": kw,
            "resume_count": resume_count,
            "jd_count": jd_count,
            "matched": in_resume,
            "tfidf_score": jd_score,
        })

        if in_resume:
            matched.append(kw)
        else:
            missing.append(kw)

    return {
        "matched": matched,
        "missing": missing,
        "frequency_data": frequency_data,
        "jd_keywords": [kw for kw, _ in jd_keywords_scored],
    }


def get_keyword_chart_data(
    frequency_data: List[Dict[str, Any]],
    max_items: int = 20,
) -> List[Dict[str, Any]]:
    """Format keyword frequency data for the frontend chart.

    Args:
        frequency_data: List of keyword frequency dicts from match_keywords.
        max_items: Maximum number of items to include in chart.

    Returns:
        List of dicts formatted for Recharts BarChart.
    """
    # Sort by JD count (most important JD keywords first)
    sorted_data = sorted(frequency_data, key=lambda x: x["jd_count"], reverse=True)
    return [
        {
            "keyword": item["keyword"],
            "resume_count": item["resume_count"],
            "jd_count": item["jd_count"],
            "matched": item["matched"],
        }
        for item in sorted_data[:max_items]
    ]
