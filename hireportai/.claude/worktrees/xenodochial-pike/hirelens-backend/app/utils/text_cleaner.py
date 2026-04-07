"""Text normalization and cleaning utilities."""
import re
import unicodedata
from typing import List


def normalize_whitespace(text: str) -> str:
    """Replace multiple whitespace characters with a single space."""
    return re.sub(r"\s+", " ", text).strip()


def clean_unicode(text: str) -> str:
    """Normalize unicode characters to their closest ASCII equivalents."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def remove_special_chars(text: str, keep_punctuation: bool = True) -> str:
    """Remove non-printable and special characters from text."""
    if keep_punctuation:
        # Keep letters, digits, common punctuation, and whitespace
        cleaned = re.sub(r"[^\w\s\.,;:!?@\-\+\(\)/&%#$]", " ", text)
    else:
        cleaned = re.sub(r"[^\w\s]", " ", text)
    return normalize_whitespace(cleaned)


def clean_resume_text(text: str) -> str:
    """Apply full cleaning pipeline for resume text."""
    text = clean_unicode(text)
    # Remove lines with only special characters (common in PDF extraction artifacts)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) > 1:
            # Keep lines that have at least some alphabetic content
            if re.search(r"[a-zA-Z]", stripped):
                cleaned_lines.append(stripped)
    text = "\n".join(cleaned_lines)
    return text


def extract_email(text: str) -> str:
    """Extract the first email address found in text."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    """Extract the first phone number found in text."""
    pattern = r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def extract_urls(text: str) -> List[str]:
    """Extract all URLs found in text."""
    pattern = r"https?://[^\s]+"
    return re.findall(pattern, text)


def tokenize_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence tokenizer
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def lowercase_and_strip(text: str) -> str:
    """Lowercase and strip a string."""
    return text.lower().strip()


def remove_bullets(text: str) -> str:
    """Remove common bullet point characters from text."""
    return re.sub(r"^[\•\-\*\>\◦\▪\▸\►\◼\●\·\○]\s*", "", text, flags=re.MULTILINE)
