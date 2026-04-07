"""Resume upload and optimization endpoints."""
import difflib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_plan
from app.db.session import get_db
from app.models.resume_model import Resume
from app.models.user import User
from app.services.nlp import extract_job_requirements, extract_skills
from app.services.parser import parse_docx, parse_pdf
from app.services.usage_service import check_usage_limit, log_usage

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/resume/upload")
async def upload_resume(
    resume_file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a resume, storing the extracted text in the database."""
    filename = resume_file.filename or ""
    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files accepted.")

    file_bytes = await resume_file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 5 MB limit.")
    if len(file_bytes) < 100:
        raise HTTPException(status_code=400, detail="File appears empty or corrupted.")

    try:
        if filename.endswith(".pdf"):
            resume_data = parse_pdf(file_bytes)
        else:
            resume_data = parse_docx(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    resume_text = resume_data.get("full_text", "")
    if len(resume_text) < 50:
        raise HTTPException(status_code=422, detail="Could not extract text from resume.")

    resume = Resume(
        user_id=user.id,
        original_content=resume_text,
        template_type=filename.rsplit(".", 1)[-1],
    )
    db.add(resume)
    await db.flush()

    return {
        "id": resume.id,
        "original_content_length": len(resume_text),
        "template_type": resume.template_type,
        "created_at": str(resume.created_at),
    }


@router.post("/resume/{resume_id}/optimize")
async def optimize_resume(
    resume_id: str,
    job_description: str = Form(..., description="Job description text"),
    user: User = Depends(require_plan("enterprise")),
    db: AsyncSession = Depends(get_db),
):
    """Run LLM-powered ATS optimization on a stored resume.

    Requires enterprise plan. Logs token consumption.
    """
    # Check usage limit
    allowed = await check_usage_limit(user.id, "resume_optimize", db)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Resume optimization limit reached for your plan this month.",
        )

    # Fetch resume
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    # Build resume_data and jd_requirements
    resume_data = {
        "full_text": resume.original_content,
        "skills": extract_skills(resume.original_content),
        "sections": {},
    }
    jd_requirements = extract_job_requirements(job_description)

    # Run optimization via the AI service
    from app.services.ai_service import generate_resume_rewrite
    rewrite_result = generate_resume_rewrite(resume_data, jd_requirements)

    # Store optimized content
    resume.optimized_content = rewrite_result.full_text

    # Log usage (estimate tokens: ~4 tokens per word for input + output)
    estimated_tokens = len(resume.original_content.split()) * 4 + len(rewrite_result.full_text.split()) * 4
    await log_usage(user.id, "resume_optimize", estimated_tokens, db)

    return {
        "id": resume.id,
        "sections": [s.model_dump() for s in rewrite_result.sections],
        "full_text": rewrite_result.full_text,
    }


@router.get("/resume/{resume_id}")
async def get_resume(
    resume_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a saved resume with original and optimized content."""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    return {
        "id": resume.id,
        "original_content": resume.original_content,
        "optimized_content": resume.optimized_content,
        "template_type": resume.template_type,
        "created_at": str(resume.created_at),
        "updated_at": str(resume.updated_at),
    }


@router.get("/resume/{resume_id}/diff")
async def get_resume_diff(
    resume_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Show a unified diff between original and optimized resume content."""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if not resume.optimized_content:
        raise HTTPException(status_code=404, detail="No optimized version available yet.")

    diff_lines = list(difflib.unified_diff(
        resume.original_content.splitlines(keepends=True),
        resume.optimized_content.splitlines(keepends=True),
        fromfile="original",
        tofile="optimized",
    ))

    return {
        "id": resume.id,
        "diff": "".join(diff_lines),
        "original_length": len(resume.original_content),
        "optimized_length": len(resume.optimized_content),
    }
