"""ATS formatting compliance checker."""
import re
from typing import Any, Dict, List

from app.models.response_models import FormattingIssue

# Standard ATS-friendly section headers
STANDARD_HEADERS = {
    "summary", "objective", "profile", "about",
    "experience", "work experience", "employment", "professional experience",
    "education", "academic",
    "skills", "technical skills", "core competencies",
    "projects", "certifications", "awards", "publications", "languages",
    "volunteer", "interests", "references",
}

# Date format patterns that ATS systems handle well
GOOD_DATE_PATTERNS = [
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[.\s]+\d{4}\b",
    r"\b\d{1,2}/\d{4}\b",
    r"\b\d{4}\s*[-–]\s*\d{4}\b",
    r"\b\d{4}\s*[-–]\s*(Present|Current|Now)\b",
]

BAD_DATE_PATTERNS = [
    r"\b\d{1,2}-\d{1,2}-\d{2,4}\b",  # e.g. 01-15-2022
    r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b",  # e.g. 01.15.2022
]

GOOD_DATE_RE = re.compile("|".join(GOOD_DATE_PATTERNS), re.IGNORECASE)
BAD_DATE_RE = re.compile("|".join(BAD_DATE_PATTERNS))


def check_formatting(
    resume_data: Dict[str, Any],
    formatting_hints: Dict[str, bool],
) -> List[FormattingIssue]:
    """Check resume for ATS formatting compliance issues.

    Args:
        resume_data: Parsed resume data including full_text and sections.
        formatting_hints: Hints from parser about tables, images, columns.

    Returns:
        List of FormattingIssue objects sorted by severity.
    """
    issues: List[FormattingIssue] = []
    full_text = resume_data.get("full_text", "")
    sections = resume_data.get("sections", {})

    # Check for tables
    if formatting_hints.get("has_tables"):
        issues.append(FormattingIssue(
            issue="Tables detected in resume",
            severity="critical",
            fix="Replace tables with plain text using consistent spacing and alignment. Most ATS systems cannot parse table content.",
        ))

    # Check for images
    if formatting_hints.get("has_images"):
        issues.append(FormattingIssue(
            issue="Images or graphics detected",
            severity="critical",
            fix="Remove all images, photos, logos, and graphical elements. ATS systems ignore image content entirely.",
        ))

    # Check for multi-column layout
    if formatting_hints.get("multi_column"):
        issues.append(FormattingIssue(
            issue="Multi-column layout detected",
            severity="critical",
            fix="Convert to a single-column layout. ATS systems read left-to-right, top-to-bottom and may scramble multi-column content.",
        ))

    # Check for missing contact section
    contact_info = resume_data.get("contact_info", {})
    if not contact_info.get("email"):
        issues.append(FormattingIssue(
            issue="No email address found",
            severity="critical",
            fix="Add your email address clearly in the header/contact section.",
        ))

    if not contact_info.get("phone"):
        issues.append(FormattingIssue(
            issue="No phone number found",
            severity="warning",
            fix="Add your phone number to the contact section.",
        ))

    # Check for missing skills section
    if "skills" not in sections:
        issues.append(FormattingIssue(
            issue="No dedicated Skills section found",
            severity="critical",
            fix="Add a clearly labeled 'Skills' or 'Technical Skills' section. ATS systems use this to match your skills to job requirements.",
        ))

    # Check for missing experience section
    if "experience" not in sections:
        issues.append(FormattingIssue(
            issue="No Work Experience section found",
            severity="critical",
            fix="Add a clearly labeled 'Experience' or 'Work Experience' section.",
        ))

    # Check for non-standard date formats
    if full_text:
        has_good_dates = GOOD_DATE_RE.search(full_text)
        has_bad_dates = BAD_DATE_RE.search(full_text)
        if has_bad_dates and not has_good_dates:
            issues.append(FormattingIssue(
                issue="Non-standard date format detected",
                severity="warning",
                fix="Use standard date formats like 'January 2022 – Present' or 'Jan 2022 – Mar 2024' for better ATS parsing.",
            ))

    # Check section header clarity
    section_text_lower = full_text.lower()
    detected_headers = list(sections.keys())
    if len(detected_headers) < 2:
        issues.append(FormattingIssue(
            issue="Few or no standard section headers detected",
            severity="warning",
            fix="Use clear, standard section headers such as 'Experience', 'Education', 'Skills'. Avoid creative labels like 'My Journey'.",
        ))

    # Check for special characters in headers (common PDF artifact)
    unusual_char_pattern = re.compile(r"[^\w\s\-\.\,\:\(\)\/\&\%\@\#\!\?]")
    if unusual_char_pattern.search(full_text[:500]):
        issues.append(FormattingIssue(
            issue="Special or unusual characters detected",
            severity="info",
            fix="Ensure your resume uses standard fonts and characters. Special symbols may not parse correctly in all ATS systems.",
        ))

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: severity_order.get(i.severity, 2))

    return issues
