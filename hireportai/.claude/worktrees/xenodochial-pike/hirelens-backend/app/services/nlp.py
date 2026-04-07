"""NLP pipeline using spaCy for entity extraction and skill detection."""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.skill_taxonomy import ALL_SKILLS_LOWER, find_skill

# Lazy-load spaCy model to avoid startup overhead.
# _nlp is set to False (not None) when spaCy is unavailable so we only
# attempt the import once instead of re-trying on every request.
_nlp = None
_SPACY_AVAILABLE: bool | None = None  # None = untested yet


def get_nlp():
    """Lazy-load the spaCy model.

    Returns the spaCy Language object, or None if spaCy is unavailable
    (e.g. Python 3.14 where spaCy's Pydantic v1 internals crash).
    All callers must handle a None return value.
    """
    global _nlp, _SPACY_AVAILABLE

    if _SPACY_AVAILABLE is False:
        return None

    if _nlp is not None:
        return _nlp

    try:
        import spacy  # noqa: PLC0415
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            _nlp = spacy.blank("en")
        _SPACY_AVAILABLE = True
        return _nlp
    except Exception:
        # spaCy not compatible with this Python version — degrade gracefully.
        _SPACY_AVAILABLE = False
        return None


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities from text using spaCy NER.

    Args:
        text: Input text to process.

    Returns:
        Dictionary mapping entity labels to lists of entity strings.
    """
    nlp = get_nlp()
    if nlp is None:
        return {}
    # Process in chunks to avoid memory issues with long texts
    max_chars = 100000
    doc = nlp(text[:max_chars])

    entities: Dict[str, List[str]] = {}
    for ent in doc.ents:
        label = ent.label_
        if label not in entities:
            entities[label] = []
        if ent.text not in entities[label]:
            entities[label].append(ent.text)

    return entities


def extract_skills(text: str) -> List[str]:
    """Extract skills mentioned in text using taxonomy matching and NLP.

    Args:
        text: Input text to scan for skills.

    Returns:
        List of identified skill names (canonical form).
    """
    found_skills: Set[str] = set()

    # Method 1: Direct taxonomy matching (case-insensitive)
    text_lower = text.lower()
    for skill_lower, skill_canonical in ALL_SKILLS_LOWER.items():
        # Use word boundary matching
        pattern = r"\b" + re.escape(skill_lower) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.add(skill_canonical)

    # Method 2: spaCy NER for ORG/PRODUCT entities that might be tools
    try:
        nlp = get_nlp()
        if nlp is None:
            raise RuntimeError("spaCy unavailable")
        doc = nlp(text[:50000])
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT", "WORK_OF_ART"):
                canonical = find_skill(ent.text)
                if canonical:
                    found_skills.add(canonical)
    except Exception:
        pass

    return sorted(found_skills)


def extract_job_requirements(jd_text: str) -> Dict[str, Any]:
    """Parse a job description to extract structured requirements.

    Args:
        jd_text: Raw job description text.

    Returns:
        Dictionary with required_skills, preferred_skills, job_title,
        seniority_level, and responsibilities.
    """
    skills = extract_skills(jd_text)
    jd_lower = jd_text.lower()

    # Classify required vs preferred based on context
    required_skills: List[str] = []
    preferred_skills: List[str] = []

    # Split into sections around "required" and "preferred/nice-to-have"
    required_section = ""
    preferred_section = ""

    req_match = re.search(
        r"(required|must have|must-have|required qualifications?)(.*?)"
        r"(?=preferred|nice.to.have|bonus|plus|desired|$)",
        jd_lower,
        re.DOTALL,
    )
    pref_match = re.search(
        r"(preferred|nice.to.have|bonus|plus|desired)(.*?)$",
        jd_lower,
        re.DOTALL,
    )

    if req_match:
        required_section = req_match.group(2)
    if pref_match:
        preferred_section = pref_match.group(2)

    for skill in skills:
        skill_lower = skill.lower()
        in_required = re.search(r"\b" + re.escape(skill_lower) + r"\b", required_section)
        in_preferred = re.search(r"\b" + re.escape(skill_lower) + r"\b", preferred_section)

        if in_required:
            required_skills.append(skill)
        elif in_preferred:
            preferred_skills.append(skill)
        else:
            # Default to required if not clearly in preferred section
            required_skills.append(skill)

    # Extract job title (usually in first few lines)
    first_lines = jd_text.strip().split("\n")[:5]
    job_title = first_lines[0].strip() if first_lines else "Software Engineer"
    # Truncate if too long
    if len(job_title) > 100:
        job_title = job_title[:100]

    # Detect seniority
    seniority = _detect_seniority(jd_lower)

    # Extract responsibilities (lines with action verbs)
    responsibilities = _extract_responsibilities(jd_text)

    return {
        "required_skills": sorted(set(required_skills)),
        "preferred_skills": sorted(set(preferred_skills)),
        "all_skills": sorted(set(skills)),
        "job_title": job_title,
        "seniority_level": seniority,
        "responsibilities": responsibilities,
    }


def _detect_seniority(jd_lower: str) -> str:
    """Detect job seniority level from job description text."""
    if any(w in jd_lower for w in ("senior", "sr.", "lead", "principal", "staff")):
        return "Senior"
    elif any(w in jd_lower for w in ("junior", "jr.", "entry level", "entry-level", "associate")):
        return "Junior"
    elif any(w in jd_lower for w in ("manager", "director", "vp ", "vice president", "head of")):
        return "Manager"
    else:
        return "Mid-level"


def _extract_responsibilities(text: str) -> List[str]:
    """Extract responsibility bullet points from job description."""
    responsibilities: List[str] = []
    lines = text.split("\n")

    action_verb_pattern = re.compile(
        r"^[\•\-\*\>\◦\▪\▸\►\◼\●\·\○\—\–]?\s*"
        r"(Design|Develop|Build|Implement|Lead|Manage|Create|Maintain|"
        r"Collaborate|Work|Own|Drive|Define|Architect|Optimize|Support|"
        r"Analyze|Deliver|Ensure|Establish|Write|Review|Debug|Deploy|"
        r"Monitor|Scale|Integrate|Partner|Contribute|Shape|Improve)",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) > 20 and action_verb_pattern.match(stripped):
            responsibilities.append(stripped)

    return responsibilities[:20]


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate cosine similarity between two texts using TF-IDF.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Cosine similarity score between 0.0 and 1.0.
    """
    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=1000,
            ngram_range=(1, 2),
        )
        matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return float(similarity)
    except Exception:
        return 0.0
