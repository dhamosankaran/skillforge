"""Pydantic v2 response models for HirePort AI API."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ATSScoreBreakdown(BaseModel):
    """Sub-scores contributing to the total ATS score."""

    keyword_match: float
    skills_coverage: float
    formatting_compliance: float
    bullet_strength: float


class SkillGap(BaseModel):
    """A skill required by the job but missing from the resume."""

    skill: str
    category: str  # Technical | Soft | Certification | Tool
    importance: str  # critical | recommended | nice-to-have


class BulletAnalysis(BaseModel):
    """Analysis result for a single resume bullet point."""

    original: str
    score: int  # 0-10
    issues: List[str]
    rewritten: str


class FormattingIssue(BaseModel):
    """An ATS formatting compliance issue found in the resume."""

    issue: str
    severity: str  # critical | warning | info
    fix: str


class KeywordChartData(BaseModel):
    """Data point for the keyword frequency chart."""

    keyword: str
    resume_count: int
    jd_count: int
    matched: bool


class SkillOverlapData(BaseModel):
    """Data point for the skill radar/overlap chart."""

    subject: str
    resume: float
    jd: float


class AnalysisResponse(BaseModel):
    """Full response from the /api/analyze endpoint."""

    ats_score: int
    grade: str
    score_breakdown: ATSScoreBreakdown
    matched_keywords: List[str]
    missing_keywords: List[str]
    skill_gaps: List[SkillGap]
    bullet_analysis: List[BulletAnalysis]
    formatting_issues: List[FormattingIssue]
    job_fit_explanation: str
    top_strengths: List[str]
    top_gaps: List[str]
    keyword_chart_data: List[KeywordChartData]
    skills_overlap_data: List[SkillOverlapData]
    resume_text: str = ""


class RewriteEntry(BaseModel):
    """A single entry within a resume section (job, project, org, etc.)."""

    org: str = ""
    location: str = ""
    date: str = ""
    title: str = ""
    bullets: List[str] = []
    details: List[str] = []


class RewriteSection(BaseModel):
    """A single section of a rewritten resume."""

    title: str
    content: str = ""
    entries: List[RewriteEntry] = []


class RewriteHeader(BaseModel):
    """Resume header with candidate info."""

    name: str = ""
    contact: str = ""


class RewriteResponse(BaseModel):
    """Full rewritten resume response."""

    header: RewriteHeader = RewriteHeader()
    sections: List[RewriteSection]
    full_text: str
    template_type: str = "general"


class CoverLetterResponse(BaseModel):
    """Generated cover letter response."""

    cover_letter: str
    tone: str


class InterviewQuestion(BaseModel):
    """A single interview question with STAR framework answer."""

    question: str
    star_framework: str


class InterviewPrepResponse(BaseModel):
    """Interview prep questions response."""

    questions: List[InterviewQuestion]


class TrackerApplication(BaseModel):
    """A job application in the tracker."""

    id: str
    company: str
    role: str
    date_applied: str
    ats_score: int
    status: str
    created_at: str



class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    code: str
    detail: str
