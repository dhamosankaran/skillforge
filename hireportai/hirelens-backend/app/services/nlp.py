"""NLP pipeline using spaCy for entity extraction and skill detection."""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.llm_router import generate_for_task
from app.utils.skill_taxonomy import ALL_SKILLS_LOWER, find_skill

logger = logging.getLogger(__name__)

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

    # B-021: heuristic company-name extraction. Returns None on low
    # confidence; downstream callers keep their existing placeholder
    # fallback ("your company" / "Unknown Company") for that case.
    company_name = _extract_company_name(jd_text)

    return {
        "required_skills": sorted(set(required_skills)),
        "preferred_skills": sorted(set(preferred_skills)),
        "all_skills": sorted(set(skills)),
        "job_title": job_title,
        "seniority_level": seniority,
        "responsibilities": responsibilities,
        "company_name": company_name,
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


# Between-word whitespace is single-line only (no newlines); the regex
# otherwise backtracks across blank lines and absorbs a preceding headline
# like "Senior Python Engineer\n\nAcme Robotics is hiring" into one match.
_COMPANY_TOKEN = r"([A-Z][A-Za-z0-9&'\.\-]*(?:[ \t]+[A-Z][A-Za-z0-9&'\.\-]+){0,4})"

# High-precision patterns only. Each captures a Title-Case company token of
# 1-5 words. The extractor returns the first match; consumers fall back to
# the "your company" / "Unknown Company" placeholder when None is returned.
_COMPANY_PATTERNS: List[re.Pattern[str]] = [
    # "About Acme Robotics:" / "About Acme Robotics —"
    re.compile(rf"\bAbout\s+{_COMPANY_TOKEN}\s*[:\-\—]"),
    # "Join Acme Robotics" / "Join the Acme Robotics team"
    re.compile(rf"\bJoin\s+(?:the\s+)?{_COMPANY_TOKEN}\s+(?:team|as|in)\b"),
    # "Acme Robotics is hiring" / "Acme Robotics is looking"
    re.compile(rf"\b{_COMPANY_TOKEN}\s+is\s+(?:hiring|looking\s+for|seeking)\b"),
    # "at Acme Robotics." / "at Acme Robotics,"  — position-at-company anchor
    re.compile(rf"\bat\s+{_COMPANY_TOKEN}(?=[\.,\n]|\s+(?:we|you|our|is))"),
    # "Company: Acme Robotics" on its own line
    re.compile(rf"^\s*Company\s*[:\-]\s*{_COMPANY_TOKEN}\s*$", re.MULTILINE),
]

# Common prose tokens that pass the Title-Case regex but aren't companies.
# Pre-match guard keeps false positives out of the consumer fallback ladder.
_COMPANY_STOPWORDS: Set[str] = {
    "we", "you", "our", "the", "this", "that", "your", "their", "its",
    "scale", "scaling", "python", "kubernetes", "terraform", "postgres",
    "hiring", "seeking", "looking",
}


# B-024: aggregator job-board names that sometimes appear more prominently in
# a JD than the hiring company. Server-side deny-list is a backstop — the LLM
# prompt already instructs against returning these. Both halves catch real
# failures; keep this set short and obvious (user: "deny-list only, STOP if
# it gets more complex").
_AGGREGATOR_DENY: Set[str] = {
    "linkedin", "indeed", "glassdoor", "monster", "ziprecruiter",
    "careerbuilder", "dice", "wellfound", "angellist", "simplyhired",
}


_LLM_COMPANY_PROMPT = """You are extracting the hiring company name from a job description.

Return a JSON object with EXACTLY one key:
{{"company_name": "<string>"}} OR {{"company_name": null}}

Rules:
- Return the hiring COMPANY (the employer posting this job).
- If the company name is not clearly stated in the JD, return null.
- Do NOT return the ROLE TITLE (e.g., "Senior Engineer", "Executive Director").
- Do NOT return the team / department / organization-within-company.
- Do NOT return aggregator or job-board names (LinkedIn, Indeed, Glassdoor, Monster, ZipRecruiter, etc.).
- Return the company verbatim as it appears, preserving capitalization and punctuation.
- Do not add commentary, markdown, or additional keys.

Job description:
{jd_text}
"""


def _extract_company_name_llm(jd_text: str) -> Optional[str]:
    """Call the LLM to extract the hiring-company name from a JD (B-024).

    Returns a plausible string, or None if the LLM judged the JD
    ambiguous or returned an aggregator / empty value. Raises on
    network / quota / config failure — the orchestrator catches
    that and falls back to the regex path.
    """
    prompt = _LLM_COMPANY_PROMPT.format(jd_text=jd_text[:8000])
    response_text = generate_for_task(
        task="company_name_extraction",
        prompt=prompt,
        json_mode=True,
        max_tokens=200,
        temperature=0.2,
    )
    if not response_text or not response_text.strip():
        return None
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Malformed LLM output = low confidence; do NOT fall back to regex —
        # that's reserved for genuine infrastructure failures. Per user:
        # "null is valid data, not error." Parse-fail is effectively null.
        logger.warning("company_name LLM returned non-JSON: %r", response_text[:200])
        return None
    candidate = data.get("company_name") if isinstance(data, dict) else None
    if not isinstance(candidate, str):
        return None
    candidate = candidate.strip()
    if not candidate:
        return None
    # Server-side deny-list backstop — prompt already instructs against these.
    if candidate.lower() in _AGGREGATOR_DENY:
        logger.info("company_name rejected by aggregator deny-list: %r", candidate)
        return None
    return candidate[:100]


def _extract_company_name_regex(jd_text: str) -> Optional[str]:
    """High-precision regex fallback for company-name extraction (B-021).

    Preserved as the fallback path for B-024's LLM orchestrator: used only
    when the LLM call itself raises (network / quota / config). LLM
    returning `None` is valid data — that result passes through and does
    NOT trigger this fallback. Returns None on low confidence so consumer
    fallbacks ("your company" / "Unknown Company") stay intact.
    """
    if not jd_text or not jd_text.strip():
        return None
    for pattern in _COMPANY_PATTERNS:
        match = pattern.search(jd_text)
        if match:
            candidate = match.group(1).strip().rstrip(",.:;—-")
            if not candidate:
                continue
            if candidate.lower() in _COMPANY_STOPWORDS:
                continue
            # First token alone ("Scale", "Python") is a stopword-prone
            # false-positive signal; require ≥2 tokens OR length ≥4 chars.
            if len(candidate.split()) == 1 and len(candidate) < 4:
                continue
            return candidate[:100]
    return None


def _extract_company_name(jd_text: str) -> Optional[str]:
    """Extract the hiring-company name from a JD (B-024 — LLM primary).

    Design: LLM primary (Flash) + regex fallback + existing
    "your company" / "Unknown Company" consumer fallback. Three layers,
    precision-first: null > false positive. Layer 2 (manual user entry
    when extraction returns None) is tracked as B-025 and is out of
    scope here.

    - LLM raises (network / quota / config) → fall back to regex.
    - LLM returns None (valid "unclear" judgment) → return None; consumers
      keep their placeholder. We do NOT re-try the regex — null is
      data, not an error.
    - LLM returns a string → deny-list backstop, length cap, return.

    Role-title rejection is enforced in the LLM prompt rather than
    server-side, keeping the validator to a simple aggregator deny-list
    (user: "STOP if validator gets more complex than a deny-list").
    """
    if not jd_text or not jd_text.strip():
        return None
    try:
        return _extract_company_name_llm(jd_text)
    except Exception as exc:
        logger.warning(
            "company_name LLM call failed (%s); falling back to regex", exc
        )
        return _extract_company_name_regex(jd_text)


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
