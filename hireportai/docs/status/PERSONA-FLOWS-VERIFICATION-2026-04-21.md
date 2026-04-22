# Persona Flows Verification — 2026-04-21

> Read-only code audit. Every claim cites a file + line. No fabricated behavior.
> HEAD at audit: `6f6f61f`. Answers three questions from Dhamo's E2E walkthrough.

---

## Q1 — Which LLM tier does Analysis Results use?

**Answer: FAST tier. Default model = `gemini-2.0-flash`.**

### Trace

1. **FE entry**: `hirelens-frontend/src/pages/Analyze.tsx:1-22` (resume + JD form) → calls `useAnalysis` hook → `services/api.ts` POST to backend. Results render at `/prep/results` via `Results.tsx` which reads from `useAnalysisContext`.
2. **BE v1 route**: `hirelens-backend/app/api/v1/routes/analyze.py:1-4` re-exports the legacy router (`from app.api.routes.analyze import router`). So `POST /api/v1/analyze` === `POST /api/analyze`.
3. **Route handler**: `hirelens-backend/app/api/routes/analyze.py:46-47` `analyze_resume(...)`. Non-LLM work (parsing, keywords, scoring, gap detection) runs first via local services (`parser`, `nlp`, `keywords`, `scorer`, `gap_detector`, `bullet_analyzer`, `formatter_check`).
4. **LLM call**: `hirelens-backend/app/api/routes/analyze.py:168-179` calls `generate_job_fit_explanation(...)` inside a `try/except` (LLM path is optional — falls back to a canned string on failure).
5. **Task name**: `hirelens-backend/app/services/gpt_service.py:161` `generate_for_task(task="ats_keyword_extraction", prompt=..., json_mode=True, max_tokens=800, temperature=0.6)`.
6. **Tier classification**: `hirelens-backend/app/core/llm_router.py:23-30` `FAST_TASKS = frozenset([..., "ats_keyword_extraction", ...])`. Not in `REASONING_TASKS` (llm_router.py:32-37).
7. **Model resolution**: `hirelens-backend/app/core/llm_router.py:225-226` — fast tier reads `settings.llm_fast_provider` + `settings.llm_fast_model`. Defaults in `hirelens-backend/app/core/config.py:54` — `llm_fast_model: str = "gemini-2.0-flash"`. The legacy `gemini_model` field (config.py:13) is unused by the router and is documented as a legacy single-model fallback.

### Nuance

- **`gap_mapping`** (`app/services/gap_mapping_service.py` → drives `MissingSkillsPanel` free-tier preview) is also FAST tier (llm_router.py:27).
- The **reasoning tier** (`gemini-2.5-pro` default) is reserved for: `resume_rewrite`, `resume_rewrite_section`, `cover_letter`, `interview_questions` (llm_router.py:32-37).
- So the Results page is Flash-driven end-to-end; Rewrite / Cover Letter / Interview Prep pages kick off reasoning-tier calls. This matches `.agent/skills/llm-strategy.md` intent.

---

## Q2 — Interview-Prepper persona flow (end-to-end as built)

### After PersonaPicker

- **Selection** fires `PATCH /api/v1/users/me/persona` with `{persona: 'interview_prepper', interview_target_date?, interview_target_company?}` (`hirelens-frontend/src/pages/PersonaPicker.tsx:56-66`).
- **First-time routing**: `PersonaPicker.tsx:73-76` — if localStorage `first_action_seen === 'true'` → `/home`; else → `/first-action`.
- **PersonaGate**: `hirelens-frontend/src/components/PersonaGate.tsx:11` passes through if `user.persona !== null`. No persona-specific gating.

### FirstAction CTA (spec #46)

- Logic at `hirelens-frontend/src/pages/FirstAction.tsx:22-45` (`computeCta`):
  - If `interview_target_date` is null/empty → **"Browse interview prep categories"** → `/learn` (line 34-36).
  - If date set + `interview_target_company` set → **"Start your N-day Mission to <company>"** → `/learn/mission` (line 39-44).
  - If date set + no company → **"Start your N-day Mission"** → `/learn/mission`.
- Subtitle: `"You're prepping for an interview. Here's the fastest way to start."` (FirstAction.tsx:112-113).
- Secondary CTA: "Take me to the dashboard instead" → `/home` (FirstAction.tsx:149).

### HomeDashboard widgets (Interview-Prepper mode)

Render tree: `StateAwareWidgets` (always mounted, renders nothing for fresh users — see below) → `InterviewPrepperChecklist` → a 4-widget grid.

**Always on top: `InterviewPrepperChecklist`** — `hirelens-frontend/src/components/home/widgets/InterviewPrepperChecklist.tsx:43-58`. Null if persona ≠ interview_prepper, localStorage-skipped, or checklist complete + 7 days elapsed. Backed by `GET /api/v1/onboarding/checklist` (`useOnboardingChecklist` hook).

**Grid (`HomeDashboard.tsx:28-34`)**, 4 widgets:

| # | Widget | File | Fresh-user default | CTA + destination |
|---|--------|------|--------------------|-------------------|
| 1 | CountdownWidget | `home/widgets/CountdownWidget.tsx:20-124` | **Mode 1 (no date)** → inline `<input type="date">` + Save button (no CTA). **Mode 2 (date set)** → countdown + `"Start a Mission sprint"` if no active mission (line 105) else `"View mission"` (line 104). | `/learn/mission` |
| 2 | InterviewTargetWidget | `home/widgets/InterviewTargetWidget.tsx:20-46` | **empty state** if missing company OR date: `"Set your interview company in the Countdown widget below."` (line 34). **No CTA** — display-only. | — |
| 3 | TodaysReviewWidget | `home/widgets/TodaysReviewWidget.tsx:10-51` | **empty** if `total_due === 0`: `"You're all caught up — no cards due today."` (no CTA in empty state — `action` only set when `state === 'data'`, line 38-41). | `/learn/daily` (only when cards due) |
| 4 | LastScanWidget | `home/widgets/LastScanWidget.tsx:11-76` | **empty** if no applications in tracker: `"Run your first scan to see results here."` (line 55) + CTA `"Scan a resume"` (line 46). | `/prep/analyze` |

### Mission surface

- **NOT auto-created**. `hirelens-backend/app/services/mission_service.py:112` `create_mission(...)` is only reachable via `POST /api/v1/missions/create` (`app/api/v1/routes/mission.py:58-64`), which requires a `MissionCreateRequest`.
- `/learn/mission` renders `MissionMode.tsx`; no active mission → shows `MissionSetup` form (`hirelens-frontend/src/pages/MissionMode.tsx:6-16` "States" doc comment: `setup` state).
- So the "Start a Mission sprint" CTA on CountdownWidget navigates to the setup form, not a running mission. **Dhamo's "No active mission" finding is by design, not a bug** — mission is explicit user action.

### State-aware slot (`StateAwareWidgets`)

- `hirelens-frontend/src/components/home/StateAwareWidgets.tsx:46` — renders nothing on `isLoading`, `error`, or `states[].length === 0`. For a fresh user, backend (`home_state_service.py:STATE_PRIORITY`) returns no active states → slot is blank. Not a bug; spec #40 §7 behavior.

---

## Q3 — Team Lead persona flow (end-to-end as built)

### After PersonaPicker

- Same POST / routing as Interview-Prepper, except **no `interview_target_*` fields are sent** (PersonaPicker.tsx:58-64 conditionally adds them only for `interview_prepper`).
- PersonaGate: identical pass-through.

### FirstAction CTA

- `FirstAction.tsx:30-32`: **"Browse the card library"** → `/learn`.
- Subtitle: `"You're exploring for your team. Here's the fastest way to start."` (FirstAction.tsx:115-116).

### HomeDashboard widgets (Team Lead mode)

Render tree: `StateAwareWidgets` (same null-on-fresh behavior) → a 4-widget grid (no checklist).

**Grid (`HomeDashboard.tsx:49-58`)**, 4 widgets:

| # | Widget | File | Fresh-user default | CTA + destination |
|---|--------|------|--------------------|-------------------|
| 1 | TodaysReviewWidget | `home/widgets/TodaysReviewWidget.tsx` | empty ("You're all caught up…"), no CTA | `/learn/daily` (when cards due) |
| 2 | StreakWidget | `home/widgets/StreakWidget.tsx:9-57` | **empty** if `current_streak === 0` (line 17): `"Start your streak — review a card today."` + **"Start now"** CTA (line 36). | `/learn/daily` |
| 3 | WeeklyProgressWidget | `home/widgets/WeeklyProgressWidget.tsx:16-46` | **empty** if `total_xp === 0 && longest_streak === 0` (line 22): `"Review your first card to see your activity heatmap."` + **"Start reviewing"** CTA (line 39). | `/learn/daily` |
| 4 | TeamComingSoonWidget | `home/widgets/TeamComingSoonWidget.tsx:8-22` | static `state="data"`: `"Team dashboards are coming in a future release. For now, here's your personal learning progress."` **No CTA** (component passes no `action` prop). | — |

### Mission surface

- **Not surfaced** in Team Lead mode — `TeamLeadMode` (HomeDashboard.tsx:49-58) does not render `CountdownWidget` or any mission affordance.
- Route `/learn/mission` is still accessible by direct URL (App.tsx:88 has no persona-gate on the route), but `MissionMode.tsx` will show the setup form for any persona. No persona-specific copy there.

### State-aware slot

- Same as Interview-Prepper — blank for fresh user.

---

## Q4 — Cross-cutting findings

### Persona matrix

| Surface | interview_prepper | career_climber | team_lead |
|---------|-------------------|----------------|-----------|
| PersonaPicker extra fields | date + company inputs (PersonaPicker.tsx:60-64) | none | none |
| FirstAction CTA label | "Start your N-day Mission [to <company>]" / "Browse interview prep categories" | "Start your first Daily Review" | "Browse the card library" |
| FirstAction CTA route | `/learn/mission` or `/learn` | `/learn/daily` | `/learn` |
| FirstAction subtitle | "You're prepping for an interview…" | "You're leveling up…" | "You're exploring for your team…" |
| Home checklist | ✅ `InterviewPrepperChecklist` | ❌ | ❌ |
| Home widget 1 | CountdownWidget | StreakWidget | TodaysReviewWidget |
| Home widget 2 | InterviewTargetWidget | TodaysReviewWidget | StreakWidget |
| Home widget 3 | TodaysReviewWidget | WeeklyProgressWidget | WeeklyProgressWidget |
| Home widget 4 | LastScanWidget | LastScanWidget | **TeamComingSoonWidget** |
| Mission affordance on /home | ✅ via Countdown Mode 2 CTA | ❌ not surfaced | ❌ not surfaced |

### What differs
- **Only Interview-Prepper has**: company + date capture, Countdown + InterviewTarget widgets, onboarding checklist, mission CTA on /home.
- **Only Team Lead has**: the static `TeamComingSoonWidget` placeholder.
- **Only Career-Climber has**: the Streak+TodaysReview+WeeklyProgress stack (FirstAction points at `/learn/daily` — daily habit is the conversion lever for this persona).

### What's identical
- Greeting on `/home` (HomeDashboard.tsx:73-74) — `"Welcome back, <first name>."` — not persona-aware.
- `LastScanWidget` — included for Interview-Prepper + Career-Climber, but NOT Team Lead.
- Widget titles (`Today's Review`, `Streak`, `Weekly Progress`) — shared chrome, not persona-aware.
- `StateAwareWidgets` behavior — blank for fresh user, same across personas; widget content is state-named (e.g. `mission_active`, `streak_at_risk`) not persona-named.

### Incomplete / flagged flow gaps

1. **Team Lead `/home` has zero persona-relevant next-step.** `TeamComingSoonWidget` has no CTA. Other three widgets (TodaysReview / Streak / WeeklyProgress) all route to `/learn/daily`, which is the Career-Climber conversion surface. A Team Lead landing on their own dashboard finds no "team" action — arguably graceful (honest about what's unbuilt), but the dashboard feels anemic. **Not a bug**; product call. No BACKLOG row today; candidate for a new row like "Team Lead /home has no persona-relevant CTA."

2. **Career-Climber has no mission affordance on /home.** FirstAction points them at `/learn/daily`; subsequent `/home` visits don't surface Mission or Countdown. If a Career-Climber later wants a time-bounded sprint, they'd need to self-navigate to `/learn/mission` — no discovery path on /home. **Not a bug**; intentional per spec #35 widget catalog.

3. **Mission is never auto-created for any persona.** The Interview-Prepper "Start a Mission sprint" CTA on CountdownWidget (when date is set + no active mission) takes the user to `/learn/mission` → `MissionSetup` form. The user must pick categories + daily target manually. **This is Dhamo's "No active mission" finding** — it's by design. If a smoother "confirm + auto-create" UX is wanted, that's a new spec.

4. **`InterviewTargetWidget` empty-state copy refers to another widget.** `"Set your interview company in the Countdown widget below."` (InterviewTargetWidget.tsx:34) — but `CountdownWidget` only captures **date**, not company (CountdownWidget.tsx:70-85 has a `<input type="date">` only, no company field). The only place company gets captured is the PersonaPicker (PersonaPicker.tsx:62-64). So the empty-state copy is **misleading**: a user who skipped the company field in PersonaPicker has no in-Home path to add it. Candidate BACKLOG row: "InterviewTarget empty-state copy references non-existent Countdown company field."

5. **FirstAction is localStorage-gated, not server-gated.** The `first_action_seen` flag (FirstAction.tsx:7, PersonaPicker.tsx:73-76) is per-browser, not per-user. A user who signs in on a new browser will see FirstAction again even if they've already onboarded. Minor; likely intentional for simplicity.

---

## Meta

| Field | Value |
|-------|-------|
| HEAD at audit | `6f6f61f` |
| Files read | `App.tsx`, `PersonaGate.tsx`, `PersonaPicker.tsx`, `FirstAction.tsx`, `HomeDashboard.tsx`, `StateAwareWidgets.tsx`, 8 widget files, `MissionMode.tsx`, `analyze.py` (BE routes + service), `gpt_service.py`, `llm_router.py`, `config.py`, `home_state_service.py`, `mission_service.py` |
| Cross-referenced specs | #34 (PersonaPicker), #35 (home widgets), #40 (state-aware), #41 (checklist), #46 (FirstAction) |
| Skills checked | `study-engine.md`, `mission-mode.md`, `home.md`, `llm-strategy.md` (referenced but not deep-read — none contradicted the code) |
| Fabrication check | ✅ Every claim has a file:line citation. Where behavior was inferred (e.g. "fresh user default"), the inference is stated as such. |
