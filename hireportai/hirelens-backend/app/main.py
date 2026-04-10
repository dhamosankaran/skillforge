"""HirePort AI — FastAPI application entry point."""
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    analyze,
    cover_letter,
    interview,
    onboarding,
    payments,
    rewrite,
    tracker,
)
from app.api.v1.routes import (
    admin as v1_admin,
    analyze as v1_analyze,
    auth as v1_auth,
    cards as v1_cards,
    cover_letter as v1_cover_letter,
    email_prefs as v1_email_prefs,
    feedback as v1_feedback,
    gamification as v1_gamification,
    interview as v1_interview,
    mission as v1_mission,
    progress as v1_progress,
    resume as v1_resume,
    rewrite as v1_rewrite,
    study as v1_study,
    tracker as v1_tracker,
)
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    # Schema is managed by Alembic migrations (`alembic upgrade head`).
    yield
    # Cleanup on shutdown (nothing needed currently)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1,
        )

    app = FastAPI(
        title="HirePort AI",
        description="AI-powered resume intelligence platform — ATS scoring, keyword analysis, and resume optimization.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request size limit middleware
    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next) -> Response:
        """Reject requests that exceed the configured upload size limit."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_upload_size_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Payload too large",
                    "code": "FILE_TOO_LARGE",
                    "detail": f"Maximum upload size is {settings.max_upload_size_mb}MB.",
                },
            )
        return await call_next(request)

    # Global exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "detail": str(exc),
            },
        )

    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Check that the API is running."""
        return {"status": "healthy", "service": "hireport-ai"}

    # Legacy routers — /api/* (kept for backward compat)
    app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
    app.include_router(rewrite.router, prefix="/api", tags=["Rewrite"])
    app.include_router(cover_letter.router, prefix="/api", tags=["Cover Letter"])
    app.include_router(interview.router, prefix="/api", tags=["Interview Prep"])
    app.include_router(tracker.router, prefix="/api", tags=["Tracker"])

    # v1 routers — /api/v1/*
    app.include_router(v1_auth.router, prefix="/api/v1", tags=["v1 Auth"])
    app.include_router(v1_admin.router, prefix="/api/v1", tags=["v1 Admin"])
    app.include_router(v1_analyze.router, prefix="/api/v1", tags=["v1 Analysis"])
    app.include_router(v1_rewrite.router, prefix="/api/v1", tags=["v1 Rewrite"])
    app.include_router(v1_cover_letter.router, prefix="/api/v1", tags=["v1 Cover Letter"])
    app.include_router(v1_interview.router, prefix="/api/v1", tags=["v1 Interview Prep"])
    app.include_router(v1_tracker.router, prefix="/api/v1", tags=["v1 Tracker"])
    app.include_router(v1_resume.router, prefix="/api/v1", tags=["v1 Resume"])
    app.include_router(v1_cards.router, prefix="/api/v1", tags=["v1 Cards"])
    app.include_router(v1_study.router, prefix="/api/v1", tags=["v1 Study"])
    app.include_router(v1_gamification.router, prefix="/api/v1", tags=["v1 Gamification"])
    app.include_router(v1_email_prefs.router, prefix="/api/v1", tags=["v1 Email Preferences"])
    app.include_router(v1_mission.router, prefix="/api/v1", tags=["v1 Mission"])
    app.include_router(v1_progress.router, prefix="/api/v1", tags=["v1 Progress"])
    app.include_router(v1_feedback.router, prefix="/api/v1", tags=["v1 Feedback"])
    app.include_router(onboarding.router, prefix="/api/v1", tags=["v1 Onboarding"])
    app.include_router(payments.router, prefix="/api/v1", tags=["v1 Payments"])

    return app


app = create_app()
