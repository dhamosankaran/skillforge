# Phase 5 — Spec #63: ATS Re-Scan Loop per Tracker Application

> **Status:** Drafted, not shipped — files **B-086** at status 🔴 for the impl slice. Spec authored 2026-04-30 at `<this-slice>` (E-043 parent feature row carries forward; this slice authors the spec + forward-files the impl row, mirroring slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 spec-author + forward-file precedent).
> **Closes drift D-020** at impl-merge time (Q1 lock — bundled `jd_hash` + `jd_text` migration). See §1.3 + §7.
> **Mode:** 4 (spec-author + forward-file impl row). R14 default — net-new feature with data-model surface + new endpoint + new FE component.

---

## §1 Problem

Today, the `scan → study → re-scan → improve` PRD loop is broken at the third arrow. A user scans their resume against a JD, studies their gaps, and then has no first-class "re-scan THIS specific application against my improved resume" surface. The only path back is to re-submit resume + JD as a fresh scan via `POST /api/analyze` — which produces a brand-new `tracker_applications_v2` row, severs continuity with the original tracker entry, and gives the user no quantitative signal that their study time actually moved the needle.

The result: the loop's improvement signal is invisible. Users who study diligently can't see their score climb on the application that motivated the studying.

### §1.1 — Audit findings (Step 1, numbered for §12-amendment cross-ref)

1. **`tracker_applications_v2` schema (post-E-042)** — `interview_date` (Date, nullable, partial index `ix_tracker_apps_user_interview_date`) is on disk via `9543aa466524` + `eb59d4fc1f7e` backfill (E-042 BE half). Existing columns include `id` UUID PK, `user_id` (nullable FK), `company` (String(200)), `role` (String(200)), `date_applied` (String(20)), `ats_score` (Integer, default 0 — note `int` not `Numeric`, see #4), `status` (String(20)), `scan_id` (String(36) nullable, indexed), `skills_matched`/`skills_missing` (Text nullable), `analysis_payload` (JSONB nullable, deferred). **`jd_hash` is NOT on disk; `jd_text` is NOT on disk** — both greenfield migration targets. **No `interview_company` column** — `next_interview` envelope (E-042) derives company from the existing `tracker_applications_v2.company` row.

2. **Analyze route entry point** — `POST /api/analyze` decorator at `app/api/routes/analyze.py:52` (`analyze_resume`); double-mounted at `/api/v1/analyze` via `app/api/v1/routes/analyze.py` thin re-export. **GET fetch endpoint** at `:289` (`get_scan_analysis(scan_id, ...)`). Generates `scan_id = str(uuid.uuid4())` at `:216`, persists into `tracker_applications_v2.scan_id` via `tracker_service_v2.create_application` if no existing row matches (`find_by_scan_id` at `:113`).

3. **Scoring code path is in-route, not service-extracted** — `analyze_resume` (`app/api/routes/analyze.py:52-289`) inlines orchestration: file parsing (PDF/DOCX) → NLP → keyword extraction → ATS scoring (`ATSScorer` from `app/services/scorer.py`) → skill-gap detection → bullet analysis → formatting check → optional GPT explanation → tracker-row write. **No `analysis_service.py` exists.** The new `/rescan` endpoint cannot reuse the route handler verbatim — its inputs differ (no file upload; pre-stored `jd_text` + supplied `resume_text`). **Audit-driven goal G-6 surfaces here:** extract a service helper `analysis_service.score_resume_against_jd(resume_text: str, jd_text: str, *, prior_scan_id: Optional[str] = None) -> AnalysisResponse` from the route handler so both `/analyze` and `/rescan` call the same scoring pipeline.

4. **`AnalysisResponse` shape (`app/schemas/responses.py:59-76`)** — verified field-by-field. **JC #1 (audit-driven schema correction):** disk shape diverges from the prompt-predicted Q2 schema column names. On disk:
   - `ats_score: int` (NOT `overall_score: Numeric(5,2)`)
   - `grade: str`
   - `score_breakdown: ATSScoreBreakdown` with sub-fields `keyword_match: float` / `skills_coverage: float` / `formatting_compliance: float` / `bullet_strength: float` (NOT `keyword_score / skills_score / format_score / bullets_score`)
   - Plus arrays: `matched_keywords`, `missing_keywords`, `skill_gaps`, `bullet_analysis`, `formatting_issues`, etc.
   
   Q2 lock preserved (per-axis breakdown → 4 axis columns); only column NAMES align with disk reality. See §5.

5. **Free-tier scan lifetime cap (B-031 / spec #56)** — `usage_service.check_and_increment(user_id, "analyze", db, window="lifetime")` at `analyze.py:71`. Pro/admin short-circuit on `max_uses == -1` at `usage_service.py:147`. Anonymous (`current_user is None`) bypasses entirely. **Pre-locked decision (G-7):** `/rescan` consumes from the same `"analyze"` counter via the same call shape. No new counter; no policy split.

6. **Re-Analyze paywall gate (spec #55 / B-030)** — FE `PaywallTrigger` enum at `components/PaywallModal.tsx:21-22` includes `'scan_limit'`. BE handler at `paywall_service.py:180`: `if trigger in {"scan_limit", "rewrite_limit", "cover_letter_limit"}`. **Pre-locked decision (G-7):** `/rescan` reuses `'scan_limit'` trigger on the 402 envelope. One paywall surface for all scoring operations.

7. **Tracker row read service** — `tracker_service_v2.get_application_by_id` at `app/services/tracker_service_v2.py:145`. Confirms row exists + belongs to `user_id`. Companion helpers `get_scan_by_id:89` / `find_by_scan_id:113` for scan-id-keyed lookups. The `/rescan` endpoint calls `get_application_by_id(tracker_id, user_id, db)` to verify ownership before scoring.

8. **Tracker row detail FE surface** — `pages/Tracker.tsx` mounts a list view + an inline focused-row editor block (lines ~125-200) gated by the `?focus={tracker_id}` URL param. Spec #57 §6.3 established this pattern. **OQ-D pre-lock confirmed by audit:** `<ScoreDeltaWidget>` mounts INSIDE the focused-row block (inline expand), not as a separate route. No new route required.

9. **Home dashboard composition (spec #61 / `HomeDashboard.tsx`)** — `interview_prepper` persona's widget matrix (per spec #61 composition rules). `CountdownWidget` is the canonical anchor for the next interview surface; `StudyGapsPromptWidget` is `career_climber`-only — no slot conflict. **OQ-E pre-lock confirmed by audit:** `<HomeScoreDeltaWidget>` (the home variant) mounts immediately below `CountdownWidget` in the `interview_prepper` matrix when `next_interview != null` AND that tracker row has ≥ 2 score history entries. Cold-start (only-1-score-row) shows nothing — no widget render rather than empty state, per spec #61 minimalism.

10. **PostHog scan event surface** — `.agent/skills/analytics.md` catalog has `paywall_hit{trigger}` (line 41), `optimize_clicked` (line 42). **No existing `scan_completed` / `scan_started` / `analyze_completed` events on disk.** This spec adds 4 net-new events: `rescan_initiated`, `rescan_completed`, `rescan_failed`, `rescan_short_circuited`. The orthogonal "no completion event for fresh `/analyze`" gap is not in scope here.

11. **Score-delta math site** — `AnalysisResponse.score_breakdown` already exposes per-axis floats; `ats_score` is int. Per-axis deltas are computable from any two `AnalysisResponse` shapes. **OQ-F pre-lock confirmed by audit:** BE computes deltas in `ScoreDeltaResponse` envelope (single source of truth); the FE widget renders pre-computed values without re-doing the math.

12. **Spec #59 `?scan_id` rehydration** — re-scan creates a NEW scan tied to the same tracker row. The existing scan_id on the tracker row remains the "before" anchor; the rescan mints a fresh `scan_id = str(uuid.uuid4())` (mirroring `analyze.py:216`) and writes it into a new `tracker_application_scores` row. Both rows persist into score history. The FE rehydration pattern is reused: `useScoreHistory(tracker_id)` hits a GET endpoint that returns the score-history array; FE renders before/after using array items by index.

13. **`home_state_service.get_next_interview`** (`app/services/home_state_service.py:196-232`) returns `NextInterview(date, company, tracker_id)` per `app/schemas/home.py:20-38`. **`tracker_id` is already in the envelope** — the FE `<HomeScoreDeltaWidget>` can route to the correct tracker row directly with no service-side changes. G-5 plumbing is pre-shipped via E-042.

14. **Alembic head** — `c4e21d8a7f12` (Phase 6 slice 6.10a `ingestion_jobs` table; CR §5 verified). New migration's `down_revision = "c4e21d8a7f12"`.

15. **FE `TrackerApplication` type** — `src/types/index.ts:117-130` carries `interview_date?: string | null` (E-042) plus standard fields. `<ScoreDeltaWidget>` consumes the existing type without extension; the `tracker_application_scores` history is a separate type added in §8.

### §1.2 — Why this matters

The PRD's value proposition is "scan → study → re-scan → improve." We've shipped the first three: the user can scan (ATS analysis), study (FSRS quiz items + Phase 6 lesson curriculum), and re-scan (anonymous fresh `/analyze`). What's missing is the **continuity**: a user who studied for a Stripe interview should be able to point at their Stripe tracker row and see "you went from 67 → 84 in two weeks." Without that surface, the loop's most motivating signal — quantitative improvement on a specific high-stakes target — is invisible.

The home dashboard variant (G-5) extends the same signal to the user's most-imminent interview. Per E-042, `homeState.context.next_interview` already routes the user toward "Stripe in 7 days." This spec lets that surface also say "you've improved 23 points on this application since you first scanned it."

### §1.3 — D-020 closure context (Q1 LOCKED)

Drift D-020 has been open since 2026-04-23 (~7 days at slice-author time). The drift: `tracker_applications_v2` was documented to carry a `jd_hash` column for stable JD-fingerprinting (re-scan continuity), but no column ever shipped — neither `jd_hash` nor `jd_text`. Callers rely on `(user_id, scan_id)` uniqueness today.

**Per Dhamo decision Q1 = (a) bundle:** this spec's impl migration adds BOTH `jd_hash: str | null` AND `jd_text: text | null` to `tracker_applications_v2` in a SINGLE Alembic migration (see §7). They are complementary:
- `jd_text` is the source of truth for re-scoring at re-scan time (we can't re-score against a JD we don't have).
- `jd_hash` is the dedupe key for the OQ-B short-circuit ("did the JD change since last scan?") and provides a stable fingerprint independent of whitespace / encoding noise in `jd_text`.

D-020 closes ✅ at impl-merge of B-086 (the forward-filed impl row). The §7 migration callout block records the closure as an explicit line item so the §12-amendment slice and the impl slice both see the cross-ref.

---

## §2 Goals

**Pre-locked (G-1..G-5 from chat-Claude prompt; G-6..G-7 audit-driven, surfaced at §1.1 #3 and §1.1 #5/#6):**

- **G-1** First-class re-scan endpoint per tracker application: `POST /api/v1/analyze/rescan`. Eliminates the "re-upload everything as a fresh scan" UX for users iterating on a specific application.
- **G-2** Score history per application persisted in a new `tracker_application_scores` table (Q2 LOCKED — denormalized event-shape table, NOT JSONB on `tracker_applications_v2`). Cross-user analytics surface ("how much do users improve on average?") becomes a clean DB query.
- **G-3** D-020 resolution — `jd_hash` + `jd_text` migration bundled (Q1 LOCKED — single Alembic migration; see §1.3 + §7).
- **G-4** Before/after `<ScoreDeltaWidget>` on the tracker row detail (inline-expand mount per audit #8).
- **G-5** Home-dashboard `interview_prepper` persona variant of the widget showing improvement on the user's nearest upcoming interview application (per E-042's `next_interview` envelope; routing already in place per audit #13).
- **G-6** *(audit-driven)* Extract `analysis_service.score_resume_against_jd()` helper from the in-line `analyze_resume` route handler so the new `/rescan` endpoint reuses the scoring pipeline cleanly. Refactor scope is single-direction (no behavior change to `/analyze`).
- **G-7** *(audit-driven)* Reuse spec #56's `"analyze"` lifetime counter and the existing `'scan_limit'` paywall trigger for `/rescan`. No new counter, no new trigger; one scoring-operation gating contract for the whole product.

---

## §3 Non-goals

- Multi-target rescore (rescore against MULTIPLE saved JDs at once). Out — UX surface unclear, batched LLM cost meaningful, no current user signal asking for it.
- LLM-driven coaching narrative generated alongside the score delta ("here's what you improved in your bullets"). Out — prompt-design is a meaningful surface; spec it separately when there's user demand.
- "What-if" scoring (predict score against a hypothetical resume edit before saving). Out — speculative; existing `Rewrite` flow already gives directional signal.
- Score history visualization beyond the simple before/after delta widget (sparkline, full chart, axis-by-axis trend lines). Out — v1 is a single delta widget; chart UX is a follow-up.
- Fresh-scan completion event (`scan_completed`). Orthogonal gap surfaced at audit #10; addressed separately.
- Backfill of `jd_text` / `jd_hash` for tracker rows that pre-date this migration. Out — those rows have no stored JD to backfill from. They'll show the "JD not stored — re-scan unavailable" empty state per OQ-I.
- Admin-side aggregate analytics page ("avg score improvement per persona"). Out — `tracker_application_scores` table makes the query trivial when we want it; no UI in v1.
- Pagination / infinite scroll on score history. Out — typical history is < 5 entries per tracker row; max bound ~20 in practice.
- Cron-triggered automatic re-scoring. Out — every re-scan is user-initiated.
- Re-scan against a JOB POSTING URL (vs the stored `jd_text`). Out — same domain as the multi-format ingestion gap (slice 6.10 D-1); won't ship until that lands.
- Cross-user score comparison ("you scored higher than 40% of applicants"). Out — privacy + signal-quality concerns.

---

## §4 Architecture

### §4.1 Component graph

```
┌──────────────────────┐    POST /api/v1/analyze/rescan
│  pages/Tracker.tsx   │────────────────────────────────┐
│   (focused-row UI)   │  {tracker_application_id,      │
└──────────┬───────────┘   resume_text}                 │
           │ inline mount                               │
           ▼                                            │
┌──────────────────────┐    GET /api/v1/tracker/        │
│ ScoreDeltaWidget.tsx │    {id}/scores                 │
│  (history fetch)     │────────────────────────────────┤
└──────────┬───────────┘                                │
           │ delta render                               │
           ▼                                            │
       useScoreHistory                                  │
           │                                            ▼
           ▼                            ┌─────────────────────────────┐
                                        │ analyze.py::POST /rescan    │
                                        │  (route handler)            │
                                        └────────────┬────────────────┘
                                                     │
                  ┌──────────────────────────────────┤
                  │                                  │
                  ▼                                  ▼
       ┌──────────────────────────┐    ┌────────────────────────────┐
       │ tracker_service_v2       │    │ analysis_service           │
       │ .get_application_by_id   │    │ .score_resume_against_jd   │
       │ (auth + jd_text fetch)   │    │  (G-6 extraction)          │
       └──────────────────────────┘    └────────────┬───────────────┘
                                                    │
                                                    ▼
                                       ┌────────────────────────────┐
                                       │ tracker_application_score_ │
                                       │ service.write_score_row    │
                                       │  (history INSERT)          │
                                       └────────────────────────────┘
```

Home variant: `HomeDashboard.tsx` → `<HomeScoreDeltaWidget>` (interview_prepper-only, mounted below `CountdownWidget`) → `useScoreHistory(homeState.context.next_interview.tracker_id)`.

### §4.2 Data flow — re-scan → score-write → delta render

1. **User triggers re-scan** in the focused-row block on `/prep/tracker?focus={tracker_id}`. Click handler reads the in-memory user `resume_text` (already loaded post-rewrite or post-resume-upload) and POSTs to `/api/v1/analyze/rescan` with `{tracker_application_id, resume_text}`.
2. **Route handler** (`analyze.py::rescan_application`) calls `tracker_service_v2.get_application_by_id` → enforces ownership; reads `tracker_applications_v2.jd_text` + `jd_hash` for the row.
3. **Resume-text fingerprinting** via `hash_jd(resume_text)` (existing helper at `app/utils/text_hash.py`). Combined with row's `jd_hash`, builds a `(jd_hash, resume_hash)` dedupe key.
4. **Short-circuit check** (OQ-B pre-lock): if a `tracker_application_scores` row exists where `jd_hash == row.jd_hash` AND `resume_hash == hash_jd(resume_text)`, fire `rescan_short_circuited{tracker_application_id}` and return the existing scores envelope without re-running the LLM pipeline. Mirrors spec #49's `?force_regenerate` interview-prep dedupe pattern.
5. **Free-tier counter** — `usage_service.check_and_increment(user_id, "analyze", window="lifetime")`. On 402: raise `DailyReviewLimitError`-shaped 402 with `trigger='scan_limit'` (G-7 reuse).
6. **Score** — `analysis_service.score_resume_against_jd(resume_text, jd_text, prior_scan_id=row.scan_id)` returns `AnalysisResponse`. Generates a fresh `scan_id = str(uuid.uuid4())`.
7. **Persist** — `tracker_application_score_service.write_score_row(tracker_application_id, response, scan_id, jd_hash, resume_hash, db)` INSERTs a new `tracker_application_scores` row with the per-axis breakdown.
8. **Update tracker row** — `tracker_applications_v2.ats_score` flips to the new `ats_score` (latest score wins; history preserved in `tracker_application_scores`). `scan_id` does NOT update (the original scan stays the canonical entry-point anchor).
9. **Fire event** `rescan_completed{tracker_application_id, jd_hash_prefix, ats_score_before, ats_score_after, delta}`.
10. **FE refetch** — `useScoreHistory(tracker_application_id)` invalidates on success; widget re-renders with the new history tail.
11. **Render delta** — widget reads the last two history rows; computes overall delta + per-axis deltas; renders inline. If history has only 1 entry: render "First scan baseline" copy; no delta arrow.

### §4.3 Failure modes

- **Tracker row not found / not owned by user** — 404 with `{detail: 'Application not found'}`. No row read leaks across users (G-1 invariant).
- **`jd_text` is NULL on the tracker row** — 422 with `{detail: 'JD not stored on this application — re-scan unavailable. Please run a fresh scan.'}` (OQ-I pre-lock). Pre-migration rows fall here permanently; post-migration rows always carry `jd_text` because the create path writes it (see §6.1 backend write hook).
- **Free-tier counter exhausted** — 402 with `{error, trigger: 'scan_limit', counter, plan}` envelope (FE axios interceptor unwraps identically to fresh-scan 402 per spec #50 LD-2 mirror).
- **Scoring pipeline failure (LLM 502 / parse error)** — 502 with `{detail: 'Scoring failed; please try again'}`. No score row written; no counter increment (counter increments only on success per `check_and_increment` post-write semantics — verify in §11 audit during impl). `rescan_failed{tracker_application_id, error_class}` event fired.
- **Concurrent re-scan from same user on same tracker row** — slowapi default rate limit (100/min) + the application is a fast operation; treated as benign. If a second request arrives mid-flight, the second short-circuit will likely match the first request's row write. No special concurrency lock.
- **Partial-write rollback** — score INSERT + tracker_apps `ats_score` UPDATE are wrapped in a single transaction. If either fails, both roll back. No `tracker_application_scores` row without a corresponding `ats_score` flip; no orphan scores.

### §4.4 Cross-cutting composition rules

- **Tracker domain event-shape table convention** (JC #2 reflective): `tracker_application_scores` is the FIRST denormalized event-shape table in the tracker domain. It mirrors the slice 6.0 (`quiz_review_events` / `lesson_view_events`) convention — denormalized FK to `users` (D-7 best-effort write was for analytics; here it's for query performance — same shape). Future tracker-domain analytics tables should follow this template.
- **Score history is append-only.** No UPDATE/DELETE on `tracker_application_scores` from application code. Soft-deletion via row-level `deleted_at` is NOT in scope; if a tracker row is deleted, `ON DELETE CASCADE` on the FK clears history too (no orphans).
- **Re-scan is a refinement, not a fork** — the tracker row's `scan_id` does NOT change. Original `scan_id` remains the canonical "first scan" anchor for spec #59 rehydration. Re-scan history is read via `tracker_application_scores`, not via `scans` lookups.

---

## §5 Schemas

### §5.1 — Request schema

```python
# app/schemas/rescan.py (NEW)
from pydantic import BaseModel, Field

class RescanRequest(BaseModel):
    """POST /api/v1/analyze/rescan request body."""
    tracker_application_id: str = Field(..., description="UUID of tracker_applications_v2 row to re-score")
    resume_text: str = Field(..., min_length=200, max_length=50_000)
```

`min_length=200` mirrors fresh-scan's effective minimum (resume parsing rejects shorter); `max_length=50_000` is the existing scan body cap from `analyze.py`.

### §5.2 — Response schemas

The re-scan endpoint returns `AnalysisResponse` (existing — `app/schemas/responses.py:59-76`). No envelope extension. Field-by-field shape per audit #4:

```python
class AnalysisResponse(BaseModel):
    scan_id: str = ""
    ats_score: int                      # disk: int (NOT Numeric(5,2))
    grade: str
    score_breakdown: ATSScoreBreakdown  # per-axis floats
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

class ATSScoreBreakdown(BaseModel):
    keyword_match: float
    skills_coverage: float
    formatting_compliance: float
    bullet_strength: float
```

The score-history GET endpoint returns:

```python
# app/schemas/rescan.py (NEW, same module)
from datetime import datetime
from typing import List, Optional

class ScoreHistoryEntry(BaseModel):
    """One row of tracker_application_scores."""
    id: str
    scan_id: Optional[str]            # NULL if scan row was deleted (FK ON DELETE SET NULL)
    overall_score: int                 # mirrors AnalysisResponse.ats_score
    keyword_match_score: float
    skills_coverage_score: float
    formatting_compliance_score: float
    bullet_strength_score: float
    scanned_at: datetime               # tz-aware

class ScoreHistoryResponse(BaseModel):
    """GET /api/v1/tracker/{id}/scores response."""
    tracker_application_id: str
    history: List[ScoreHistoryEntry]   # chronological, oldest-first
    delta: Optional["ScoreDelta"]      # null when len(history) < 2

class ScoreDelta(BaseModel):
    """Pre-computed delta between latest two history rows (BE-side per OQ-F)."""
    overall_delta: int                  # latest.overall_score - prev.overall_score
    keyword_match_delta: float
    skills_coverage_delta: float
    formatting_compliance_delta: float
    bullet_strength_delta: float
    days_between: int                   # integer days from prev.scanned_at to latest.scanned_at
```

### §5.3 — `tracker_application_scores` ORM model (Q2 LOCKED)

Table name: `tracker_application_scores` (snake_case plural, mirrors `tracker_applications_v2` neighbor convention).

```python
# app/models/tracker_application_score.py (NEW)
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    DateTime, Float, ForeignKey, Index, Integer, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TrackerApplicationScore(Base):
    """Score history per tracker application (E-043 / spec #63 / B-086)."""

    __tablename__ = "tracker_application_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    tracker_application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tracker_applications_v2.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Denormalized for admin analytics (cross-user "avg improvement" queries)
    # — mirrors quiz_review_events.user_id D-1 precedent (slice 6.0).
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ON DELETE SET NULL — preserve score history if scan row is later deleted.
    # Mirrors B-035 P5-S59 scan_persistence pattern.
    scan_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("scans.id", ondelete="SET NULL"),  # 'scans' table per spec #59
        nullable=True,
    )

    # Mirrors AnalysisResponse field shapes per audit #4.
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    keyword_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    skills_coverage_score: Mapped[float] = mapped_column(Float, nullable=False)
    formatting_compliance_score: Mapped[float] = mapped_column(Float, nullable=False)
    bullet_strength_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Dedupe keys for OQ-B short-circuit. NOT FKs — they're hash strings, not row refs.
    jd_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resume_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        # Chronological history fetch per tracker row (widget read).
        Index("ix_tas_tracker_app_scanned_at", "tracker_application_id", "scanned_at"),
        # Admin analytics "avg score improvement" queries.
        Index("ix_tas_user_scanned_at", "user_id", "scanned_at"),
        # OQ-B dedupe lookup.
        Index("ix_tas_dedupe_lookup", "tracker_application_id", "jd_hash", "resume_hash"),
    )
```

Field-name divergence from prompt-Q2 lock is JC #1: prompt predicted `keyword_score / skills_score / format_score / bullets_score`; disk shape (audit #4) is `keyword_match / skills_coverage / formatting_compliance / bullet_strength`. The columns suffix `_score` to distinguish from the inner sub-axis name; mirrors disk truth.

### §5.4 — `tracker_applications_v2` column additions (Q1 LOCKED)

Two new nullable columns on the existing table:

```python
# app/models/tracker.py (MODIFY existing TrackerApplicationModel)
jd_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
jd_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
```

`jd_hash` carries `index=True` for OQ-B dedupe lookups + future cross-row JD-fingerprint queries. `jd_text` is NOT indexed (full-text body, not a lookup key). Both nullable for backward compat with existing rows.

---

## §6 Backend

### §6.1 — `analysis_service.py` (NEW, G-6)

Extracted from `app/api/routes/analyze.py:52-289` route handler. Pure scoring helper:

```python
# app/services/analysis_service.py (NEW)
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.responses import AnalysisResponse


async def score_resume_against_jd(
    resume_text: str,
    jd_text: str,
    db: AsyncSession,
    *,
    user_id: Optional[str] = None,
    prior_scan_id: Optional[str] = None,
    run_rewrite: bool = False,
    run_cover_letter: bool = False,
) -> AnalysisResponse:
    """Score resume against JD; return full AnalysisResponse with fresh scan_id.

    Extracts the core scoring pipeline from analyze.py route handler so both
    /analyze (file-upload entry) and /rescan (text-input entry) call the
    same code path. analyze.py route now wraps file parsing → calls this
    helper → forwards response.

    G-6 audit-driven extraction. Single-direction refactor — no behavior
    change to /analyze. Test plan §10 covers regression invariants.
    """
```

Internal: same orchestration as the existing route handler — `extract_job_requirements` → `extract_skills` → `match_keywords` → `ATSScorer` → `detect_gaps` → `analyze_bullets` → `check_formatting` → optional GPT explanation. The route handler `analyze_resume` is reduced to: parse file → call `score_resume_against_jd(resume_text, job_description, ...)` → forward response.

**Tracker-row write hook** (so post-migration rows always carry `jd_text`): the existing `analyze_resume` route's `tracker_service_v2.create_application` call site (~line 240+) extends the create payload with `jd_text=job_description` and `jd_hash=hash_jd(job_description)`. New tracker rows always have both columns populated.

### §6.2 — `POST /api/v1/analyze/rescan` route

```python
# app/api/routes/analyze.py (EXTEND existing router)
@router.post("/analyze/rescan", response_model=AnalysisResponse)
async def rescan_application(
    request: RescanRequest,
    current_user: User = Depends(get_current_user),  # auth required (NOT optional)
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Re-score an existing tracker application against an updated resume."""
    # 1. Fetch + verify ownership
    row = await tracker_service_v2.get_application_by_id(
        request.tracker_application_id, current_user.id, db,
    )
    if row is None:
        raise HTTPException(404, "Application not found")

    if row.jd_text is None:
        raise HTTPException(
            422,
            "JD not stored on this application — re-scan unavailable. "
            "Please run a fresh scan.",
        )

    # 2. Compute hashes
    resume_hash = hash_jd(request.resume_text)
    jd_hash = row.jd_hash or hash_jd(row.jd_text)  # row.jd_hash always set post-migration

    # 3. Short-circuit per OQ-B
    existing = await tracker_application_score_service.find_by_dedupe(
        request.tracker_application_id, jd_hash, resume_hash, db,
    )
    if existing is not None:
        analytics_track(current_user.id, "rescan_short_circuited", {
            "tracker_application_id": request.tracker_application_id,
            "jd_hash_prefix": jd_hash[:8],
        })
        return _row_to_analysis_response(existing)

    # 4. Counter (G-7 reuse)
    usage = await check_and_increment(
        current_user.id, "analyze", db, window="lifetime",
    )
    if usage["limit_hit"]:
        raise HTTPException(402, detail={
            "error": "scan_limit_reached",
            "trigger": "scan_limit",
            ...,  # mirrors spec #50 envelope
        })

    # 5. Score
    analytics_track(current_user.id, "rescan_initiated", {
        "tracker_application_id": request.tracker_application_id,
    })
    response = await analysis_service.score_resume_against_jd(
        request.resume_text, row.jd_text, db,
        user_id=current_user.id, prior_scan_id=row.scan_id,
    )

    # 6. Persist + tracker update (transactional)
    score_row = await tracker_application_score_service.write_score_row(
        tracker_application_id=request.tracker_application_id,
        user_id=current_user.id,
        response=response,
        scan_id=response.scan_id,
        jd_hash=jd_hash,
        resume_hash=resume_hash,
        db=db,
    )
    row.ats_score = response.ats_score
    await db.commit()

    # 7. Fire completion event
    prior_score = await tracker_application_score_service.get_prior_overall_score(
        request.tracker_application_id, before=score_row.scanned_at, db=db,
    )
    analytics_track(current_user.id, "rescan_completed", {
        "tracker_application_id": request.tracker_application_id,
        "jd_hash_prefix": jd_hash[:8],
        "ats_score_before": prior_score,
        "ats_score_after": response.ats_score,
        "delta": (response.ats_score - prior_score) if prior_score is not None else None,
    })

    return response
```

### §6.3 — `tracker_application_score_service.py` (NEW)

Public surface:
- `write_score_row(...) -> TrackerApplicationScore` — INSERT one history row. Called from /rescan route + (optionally) from fresh-scan route to backfill the first history entry.
- `find_by_dedupe(tracker_application_id, jd_hash, resume_hash, db) -> Optional[TrackerApplicationScore]` — OQ-B short-circuit lookup.
- `get_score_history(tracker_application_id, user_id, db) -> List[TrackerApplicationScore]` — chronological, oldest-first; enforces ownership via `user_id`.
- `compute_delta(history: List[TrackerApplicationScore]) -> Optional[ScoreDelta]` — pure helper; returns `None` if `len(history) < 2`.
- `get_prior_overall_score(tracker_application_id, before: datetime, db) -> Optional[int]` — for `rescan_completed` payload.

### §6.4 — `GET /api/v1/tracker/{id}/scores` route

Mounted under existing tracker router (`app/api/v1/routes/tracker.py`):

```python
@router.get("/tracker/{app_id}/scores", response_model=ScoreHistoryResponse)
async def get_score_history(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoreHistoryResponse:
    history = await tracker_application_score_service.get_score_history(
        app_id, current_user.id, db,
    )
    delta = tracker_application_score_service.compute_delta(history)
    return ScoreHistoryResponse(
        tracker_application_id=app_id,
        history=[_to_history_entry(r) for r in history],
        delta=delta,
    )
```

### §6.5 — Performance envelope

Re-scan is the same shape as fresh-scan minus file parsing (file parsing is O(KB), negligible). LLM call dominates (~3-8s p50). No caching beyond OQ-B dedupe.

Score history GET is one indexed query against `tracker_application_scores` (≤ ~20 rows per tracker app). p50 < 50ms.

---

## §7 Migrations

**Single Alembic migration** bundling Q1 (D-020 closure) + Q2 (new table). One migration, one down_revision chain step:

```python
# alembic/versions/<sha>_phase5_tracker_rescan_loop.py (NEW)
"""Phase 5 E-043 / spec #63 — tracker re-scan loop schema.

D-020 CLOSURE: adds jd_hash + jd_text columns to tracker_applications_v2
in the same migration as the new tracker_application_scores table per
Dhamo Q1 lock (bundled, not standalone).

Revision ID: <new>
Down-revision: c4e21d8a7f12  (Phase 6 slice 6.10a ingestion_jobs)
"""
revision = "<new>"
down_revision = "c4e21d8a7f12"


def upgrade() -> None:
    # ── Q1 LOCK (D-020 closure) ──────────────────────────────────────────────
    # Add jd_text + jd_hash to tracker_applications_v2.
    op.add_column(
        "tracker_applications_v2",
        sa.Column("jd_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "tracker_applications_v2",
        sa.Column("jd_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_tracker_apps_jd_hash",
        "tracker_applications_v2",
        ["jd_hash"],
    )
    # OQ-J author-hint: backfill jd_hash for any rows where jd_text was
    # populated via mid-migration application code. v1 ships with both
    # columns NULL on existing rows; backfill is a future-row concern.

    # ── Q2 LOCK (new table) ──────────────────────────────────────────────────
    op.create_table(
        "tracker_application_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tracker_application_id", sa.String(36),
            sa.ForeignKey("tracker_applications_v2.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scan_id", sa.String(36),
            sa.ForeignKey("scans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("overall_score", sa.Integer, nullable=False),
        sa.Column("keyword_match_score", sa.Float, nullable=False),
        sa.Column("skills_coverage_score", sa.Float, nullable=False),
        sa.Column("formatting_compliance_score", sa.Float, nullable=False),
        sa.Column("bullet_strength_score", sa.Float, nullable=False),
        sa.Column("jd_hash", sa.String(64), nullable=False),
        sa.Column("resume_hash", sa.String(64), nullable=False),
        sa.Column(
            "scanned_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_tas_tracker_app_scanned_at",
        "tracker_application_scores",
        ["tracker_application_id", "scanned_at"],
    )
    op.create_index(
        "ix_tas_user_scanned_at",
        "tracker_application_scores",
        ["user_id", "scanned_at"],
    )
    op.create_index(
        "ix_tas_dedupe_lookup",
        "tracker_application_scores",
        ["tracker_application_id", "jd_hash", "resume_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_tas_dedupe_lookup", table_name="tracker_application_scores")
    op.drop_index("ix_tas_user_scanned_at", table_name="tracker_application_scores")
    op.drop_index("ix_tas_tracker_app_scanned_at", table_name="tracker_application_scores")
    op.drop_table("tracker_application_scores")
    op.drop_index("ix_tracker_apps_jd_hash", table_name="tracker_applications_v2")
    op.drop_column("tracker_applications_v2", "jd_hash")
    op.drop_column("tracker_applications_v2", "jd_text")
```

**D-020 closure line item:** the `op.add_column("tracker_applications_v2", "jd_hash")` step is the explicit closure of drift D-020. Impl slice's commit message must reference it.

**Round-trip test** at AC-12: `alembic upgrade head → downgrade -1 → upgrade head` clean.

---

## §8 Frontend

### §8.1 — `<ScoreDeltaWidget>` component (NEW, tracker variant)

Mount: inside the focused-row block in `pages/Tracker.tsx` (audit #8 — inline expand pattern).

```tsx
// src/components/tracker/ScoreDeltaWidget.tsx (NEW)
interface ScoreDeltaWidgetProps {
  trackerApplicationId: string
  onRescanInitiate: () => void  // parent handles in-memory resume_text
  rescanInFlight: boolean
}

// Renders:
//   - empty state ("Re-scan to see how you've improved") when no resume_text loaded
//   - first-scan baseline ("First scan baseline — re-scan to see improvement") when len(history)===1
//   - delta block (overall before/after/delta + 4 per-axis deltas) when len(history)>=2
//   - rescan-trigger button (disabled while in-flight)
```

### §8.2 — `<HomeScoreDeltaWidget>` component (NEW, home variant)

Mount: `pages/HomeDashboard.tsx` `interview_prepper` block, immediately below `CountdownWidget` (audit #9 — `next_interview` envelope routes via `homeState.context.next_interview.tracker_id`).

Render gate: `next_interview != null && history.length >= 2`. Cold-start (only-1-history-row) hides the widget entirely (no empty state on the home dashboard — minimalism per spec #61).

### §8.3 — `useScoreHistory` hook

```tsx
// src/hooks/useScoreHistory.ts (NEW)
export function useScoreHistory(trackerApplicationId: string | null) {
  return useQuery({
    queryKey: ['scoreHistory', trackerApplicationId],
    queryFn: () => fetchScoreHistory(trackerApplicationId!),
    enabled: trackerApplicationId !== null,
    staleTime: 60_000,
  })
}
```

### §8.4 — `services/api.ts` helpers

```tsx
// src/services/api.ts (EXTEND)
export const fetchScoreHistory = (trackerId: string) =>
  client.get<ScoreHistoryResponse>(`/api/v1/tracker/${trackerId}/scores`)
    .then(r => r.data)

export const triggerRescan = (trackerId: string, resumeText: string) =>
  client.post<AnalysisResponse>('/api/v1/analyze/rescan', {
    tracker_application_id: trackerId, resume_text: resumeText,
  }).then(r => r.data)
```

### §8.5 — Type additions in `src/types/index.ts`

```ts
export interface ScoreHistoryEntry {
  id: string
  scan_id: string | null
  overall_score: number
  keyword_match_score: number
  skills_coverage_score: number
  formatting_compliance_score: number
  bullet_strength_score: number
  scanned_at: string  // ISO8601
}

export interface ScoreDelta {
  overall_delta: number
  keyword_match_delta: number
  skills_coverage_delta: number
  formatting_compliance_delta: number
  bullet_strength_delta: number
  days_between: number
}

export interface ScoreHistoryResponse {
  tracker_application_id: string
  history: ScoreHistoryEntry[]
  delta: ScoreDelta | null
}
```

### §8.6 — `pages/Tracker.tsx` integration

Inside the focused-row block (existing post-spec #57): add `<ScoreDeltaWidget trackerApplicationId={focusedRow.id} ... />` below the interview-date editor div. Resume-text source: existing `useResume()` hook value (already loaded for current user). When unavailable: widget renders empty state with CTA to upload resume on `/profile`.

### §8.7 — `pages/HomeDashboard.tsx` integration

Inside `interview_prepper` persona switch case: mount `<HomeScoreDeltaWidget trackerId={homeState.context.next_interview?.tracker_id} />` below `<CountdownWidget />`. Component self-gates render via the history fetch — no widget when conditions unmet.

---

## §9 Analytics

Four net-new events appended to `.agent/skills/analytics.md`:

| Event | Source | Payload |
|---|---|---|
| `rescan_initiated` | BE `app/api/routes/analyze.py::rescan_application` | `{tracker_application_id}` |
| `rescan_completed` | BE | `{tracker_application_id, jd_hash_prefix, ats_score_before: int\|null, ats_score_after: int, delta: int\|null}` |
| `rescan_failed` | BE | `{tracker_application_id, error_class: 'scoring_error'\|'jd_missing'\|'auth'\|'paywall'\|'not_found'}` |
| `rescan_short_circuited` | BE | `{tracker_application_id, jd_hash_prefix}` |

OQ-L pre-lock confirmed: `rescan_completed` includes `ats_score_before` / `ats_score_after` / `delta` for analytics depth (mirrors `optimize_clicked` enrichment style). FE does NOT fire its own `rescan_*` events; BE-side capture per spec #50 / spec #57 backend-event precedent.

No new `internal: true` flag — these are user-facing events (admin-funnel + product-funnel both legitimate).

---

## §10 Test plan

### §10.1 — Backend (~+18..+24 BE)

- `tests/services/test_analysis_service.py` (~5) — G-6 extraction regression; same input → same `AnalysisResponse` as current route handler.
- `tests/services/test_tracker_application_score_service.py` (~6) — write_score_row / find_by_dedupe / get_score_history / compute_delta / get_prior_overall_score / ownership enforcement.
- `tests/test_rescan_route.py` (~9-12) — AC-1..AC-13 (auth required, ownership 404, missing jd_text 422, short-circuit, paywall 402, happy path, history persists, ats_score updates, delta event payload, rescan_failed on scoring error, transactional rollback, audit `admin_audit_log` row NOT written for non-admin route).
- `tests/test_score_history_route.py` (~3) — auth, ownership, empty-history shape.
- `tests/test_tracker_rescan_migration.py` (~1, `@pytest.mark.integration`-gated per R13) — alembic round-trip per AC-12.

### §10.2 — Frontend (~+10..+15 FE)

- `tests/components/tracker/ScoreDeltaWidget.test.tsx` (~6) — empty state / first-scan baseline / 2-row delta / per-axis delta render / rescan CTA disabled in-flight / error toast on 402.
- `tests/hooks/useScoreHistory.test.ts` (~2) — query key invalidation + null trackerId disabled.
- `tests/pages/Tracker.rescan.test.tsx` (~3) — focused-row mount; rescan trigger fires `triggerRescan`; success refetches history.
- `tests/components/home/HomeScoreDeltaWidget.test.tsx` (~3) — interview_prepper-only mount; cold-start hides; 2-row delta render.

### §10.3 — Integration

LLM-backed integration test under `tests/integration_llm/test_rescan_pipeline.py` (~2, `@pytest.mark.integration`-gated): real-scoring round-trip, live LLM call, score-row persistence verified.

Total estimated test envelope: **+18..+24 BE + +10..+15 FE + +3 integration**.

---

## §11 Acceptance criteria

- **AC-1** Unauthed `POST /api/v1/analyze/rescan` → 401.
- **AC-2** Authed POST against tracker row owned by another user → 404 (no row leak).
- **AC-3** Authed POST against tracker row with `jd_text=NULL` → 422 with explicit copy.
- **AC-4** Authed happy path → 200 + `AnalysisResponse` + 1 `tracker_application_scores` INSERT + `tracker_applications_v2.ats_score` UPDATE.
- **AC-5** OQ-B short-circuit: 2nd POST with same `(jd_hash, resume_hash)` → returns existing scores (no LLM call); fires `rescan_short_circuited`.
- **AC-6** Free-tier user at `FREE_LIFETIME_SCAN_LIMIT` → 402 with `trigger: 'scan_limit'`.
- **AC-7** Pro/admin user → unlimited (counter short-circuits at `max_uses == -1`).
- **AC-8** Scoring failure → 502 + `rescan_failed{error_class}` + counter NOT incremented + score row NOT written.
- **AC-9** `tracker_applications_v2.scan_id` does NOT change across rescans (audit #12 invariant).
- **AC-10** `GET /api/v1/tracker/{id}/scores` (auth, ownership) → 200 + chronological history + delta (null if len < 2).
- **AC-11** `rescan_completed` payload includes `ats_score_before` / `ats_score_after` / `delta` (OQ-L pre-lock).
- **AC-12** Alembic migration round-trip `upgrade head → downgrade -1 → upgrade head` clean (D-020 closure verifiable on disk: `\d+ tracker_applications_v2` shows `jd_hash` + `jd_text` columns post-upgrade; absent post-downgrade).
- **AC-13** Inline `<ScoreDeltaWidget>` mounts on `/prep/tracker?focus={id}` block; renders 1-of-3 states (empty / baseline / delta) by history length.
- **AC-14** `<HomeScoreDeltaWidget>` mounts on `/home` for `interview_prepper` persona iff `next_interview != null && history.length >= 2`; otherwise zero render (no empty state).
- **AC-15** D-020 column-presence assertion: `\d tracker_applications_v2` post-migration shows BOTH `jd_text` AND `jd_hash` columns + index `ix_tracker_apps_jd_hash` (Q1 LOCKED bundle verifiable).
- **AC-16** `tracker_application_scores` row write per re-scan: AC-4 + an explicit per-axis assertion that all 4 axis fields land non-null.
- **AC-17** Fresh `/analyze` route (post-G-6 extraction) is byte-identical in `AnalysisResponse` shape to pre-extraction (regression invariant).

---

## §12 Decisions

*(EMPTY at spec-author. Locks via §12 amendment slice mirroring slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 §12 amendment pattern at `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` / `0c21223` / `ab07168` / `be7d59a` / `d9bfcfc`. Author hints in §14 are advisory; amendment slice locks D-1..D-N from §14 OQ-A..OQ-L.)*

---

## §13 Out of scope

See §3 non-goals + these deferred-to-impl-or-later items:

- Pagination on score history (capped ~20 in practice).
- Cron/automatic re-scoring.
- Re-scan against a fresh JD URL (multi-format ingest dependency on slice 6.10's PDF/URL track).
- LLM-driven coaching narrative alongside delta.
- Sparkline / multi-row chart visualization.
- Admin aggregate analytics page (table makes the query trivial when wanted).
- Backfill of `jd_text` / `jd_hash` for existing tracker rows (no source data).
- `scan_completed` event for fresh `/analyze` (orthogonal gap, audit #10).
- Per-axis-only re-scan (rescore one axis at a time).
- Cross-application comparison ("which of my tracker rows has the highest score?").

---

## §14 Open questions

- **OQ-A** Free-tier counter contract — does `/rescan` consume from the same `"analyze"` lifetime counter as fresh scans, or have its own?
  *Author hint:* same counter. Re-scan IS still a scoring operation against an LLM call; minimizing counter sprawl is cleaner UX. Pre-locked at G-7.

- **OQ-B** No-change short-circuit — if `(jd_hash, resume_hash)` matches an existing `tracker_application_scores` row, should we short-circuit and return existing scores, or always re-score?
  *Author hint:* short-circuit; fire `rescan_short_circuited`. Mirrors spec #49 interview-prep dedupe via `?force_regenerate`. Saves LLM cost when user clicks "rescan" without actually changing the resume.

- **OQ-C** Score history pagination — return all rows or paginate?
  *Author hint:* return all. Bounded ~20/tracker in practice; can paginate later if needed.

- **OQ-D** ScoreDeltaWidget mount — separate page (`/prep/tracker/:id/scores`) or inline expand?
  *Author hint:* inline expand inside the existing focused-row block (audit #8 confirmed pattern). No new route.

- **OQ-E** Home dashboard variant slot — which composition cell?
  *Author hint:* `interview_prepper × next_interview != null × history.length >= 2`, mounted directly below `CountdownWidget`. Cold-start (history < 2) renders nothing, not an empty state — minimalism per spec #61.

- **OQ-F** Per-axis delta computation site — BE in `ScoreDeltaResponse` envelope or FE math?
  *Author hint:* BE — single source of truth. Widget renders pre-computed deltas.

- **OQ-G** `tracker_application_scores.user_id` denormalization — accept FK redundancy for query perf?
  *Author hint:* yes; mirrors `quiz_review_events.user_id` precedent (slice 6.0 D-1). Admin analytics queries don't want to join through `tracker_applications_v2`.

- **OQ-H** Rate limit on `/rescan` — same as `/analyze` (slowapi default 100/min) or stricter?
  *Author hint:* same as `/analyze`. Re-scan isn't more expensive than scan; counter (G-7) already gates abuse for free users.

- **OQ-I** Error semantics for `jd_text=NULL` — what's the FE-facing copy + status code?
  *Author hint:* 422 with `'JD not stored on this application — re-scan unavailable. Please run a fresh scan.'`. Pre-migration rows fall here permanently; backfill is out of scope.

- **OQ-J** D-020 `jd_hash` backfill at migration time — should `hash_jd(jd_text)` run on existing rows in the upgrade step?
  *Author hint:* no — existing rows have `jd_text=NULL`, so there's nothing to backfill from. Future rows always have both populated via the create-path write hook (§6.1).

- **OQ-K** PaywallTrigger reuse — `'rescan_attempt'` (new) or `'scan_limit'` (existing)?
  *Author hint:* `'scan_limit'` reuse (G-7). One paywall surface for all scoring operations.

- **OQ-L** `rescan_completed` event payload depth — include score deltas or just IDs?
  *Author hint:* include `ats_score_before` / `ats_score_after` / `delta`. Analytics depth matters for the funnel; mirrors `optimize_clicked` enrichment style.

---

## §15 Implementation forward-link

**Forward-files: B-086 🔴** for the impl slice. Per spec-author + forward-file precedent (slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11), B-086 is the impl-row that closes on impl-merge per R15(c).

**Predicted file inventory:**
- NEW (8): `app/services/analysis_service.py`, `app/services/tracker_application_score_service.py`, `app/models/tracker_application_score.py`, `app/schemas/rescan.py`, `alembic/versions/<sha>_phase5_tracker_rescan_loop.py`, `src/components/tracker/ScoreDeltaWidget.tsx`, `src/components/home/widgets/HomeScoreDeltaWidget.tsx`, `src/hooks/useScoreHistory.ts`
- MODIFIED (~10): `app/api/routes/analyze.py` (G-6 extraction + new /rescan handler), `app/api/v1/routes/tracker.py` (new GET /scores), `app/models/tracker.py` (add jd_text + jd_hash + relationship), `app/models/__init__.py` (re-export), `app/services/tracker_service_v2.py` (jd_text/jd_hash on create payload), `src/services/api.ts` (2 new helpers), `src/types/index.ts` (3 new interfaces), `src/pages/Tracker.tsx` (mount widget), `src/pages/HomeDashboard.tsx` (mount home variant), `.agent/skills/analytics.md` (4 events).

**Test envelope:** +18..+24 BE + +10..+15 FE + +3 integration (per §10).

**R16 audit predictions for impl slice:**
- BE caller graph: `analyze_resume` route + every fresh-scan caller verifies G-6 extraction is byte-identical (regression invariant AC-17).
- FE component graph: `Tracker.tsx` + `HomeDashboard.tsx` mounts; resume-text source via existing `useResume()` hook (verify on-disk during impl).
- Analytics catalog zero-collision pre-slice on `rescan_*` event names (audit #10 confirmed).
- LLM router task name: `score_resume_against_jd` reuses existing `analyze`-tier task names; no new task added.
- Migration head chain: `c4e21d8a7f12 → <new>` (audit #14).

**Dependencies (verified on-disk Step 1):**
- ✅ E-042 shipped at `b13f410` (FE migration) — `homeState.context.next_interview.tracker_id` is in the envelope (audit #13). G-5 plumbing pre-shipped.
- ✅ Spec #57 shipped (tracker-row inline editor pattern). G-4 mount surface available (audit #8).
- Spec #59 (`?scan_id` rehydration) — referenced for read-side history pattern; not a hard dependency.
- Spec #55 / B-030 (Re-Analyze paywall gate) — `/rescan` inherits gating contract via G-7.
- B-031 (free-tier scan lifetime cap) — `/rescan` consumes from same counter via G-7.
- Spec #49 (interview question storage) — referenced for OQ-B short-circuit pattern (`?force_regenerate` + JD-hash-keyed cache).
- Existing `hash_jd` helper at `app/utils/text_hash.py` (audit #5).
- Existing `Depends(get_current_user)` chain on `/api/v1/*` routes.
- Phase 6 slice 6.10a alembic head `c4e21d8a7f12` (audit #14).

**§12-amendment slice gate:** §12 starts EMPTY; locks D-1..D-N from §14 OQ-A..OQ-L (12 OQs surfaced) per slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 §12 amendment precedent. Impl pickup happens after §12 locks land.

**D-020 closure timing:** drift D-020 closes ✅ at impl-merge of B-086 (the migration in §7 lands the `jd_hash` + `jd_text` columns side-by-side per Q1 LOCKED). Spec body §1.3 + §7 + AC-15 carry the cross-ref.

---

*Spec authored 2026-04-30 at `<this-slice>`. R14 default — net-new feature with data-model surface + new endpoint + new FE component + analytics catalog extension + drift D-020 closure at impl-merge. R15(c) forward-file: B-086 🔴 inserted above B-085 (numerically descending) in BACKLOG.md per highest-numeric-first ordering. R17 watermark verified at slice start: B-085 highest in-use; B-086 free pre-slice; B-087 next-free post-slice.*
