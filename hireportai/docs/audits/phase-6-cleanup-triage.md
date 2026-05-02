# Phase 6 cleanup triage — per-item retire/migrate/defer verdicts

**Audit date:** 2026-05-02
**Anchor HEAD:** `c6415a2`
**Mode:** scout (read-only reconnaissance, doc-only output — R14 exception (b))
**Closes:** B-100

## Why this exists

The Phase-6 spec catalog defers cleanup work to "slice 6.15" in 8
distinct specs (`01`, `02`, `03`, `04`, `06`, `07`, `08`, `09`) plus
`audits/phase-6-scout.md` and the `curriculum.md` skill. A spec-author
attempt for slice 6.15 on `c6415a2` STOPPED at Step 1 because the
exhaustive sweep revealed ~20 distinct deferred items across 8 themes
— well over the prompt's >6 stop threshold — and the R16 audit found
live consumers (`Learn.tsx:133` navigates to `/learn/category`,
`gap_mapping_service` serves `/api/v1/onboarding/recommendations`,
~10 services read `card_progress`) that block a single-slice retirement.

This triage produces a per-item verdict so chat-Claude / Dhamo can
decide spec-15 scope. It is purely advisory — it does not commit any
retirement work.

## Sourcing

- `docs/specs/phase-6/{01,02,03,04,06,07,08,09}.md` — every "slice 6.15"
  reference (`rg "6\.15|slice 6\.15"`)
- `docs/audits/phase-6-scout.md` lines 906, 1036, 1095
- `BACKLOG.md` closure trails: B-061 (slice 6.1), B-062 (slice 6.2),
  B-074 (slice 6.6), B-077 (slice 6.7), B-094a (slice 6.13.5a)
- `.agent/skills/curriculum.md` ("slice 6.15 cleanup")
- R16 consumer audit run on disk at HEAD `c6415a2` for: `gap_mapping_service`,
  `card_progress`, `card_feedback`, `/learn/category`, `Navbar`,
  `card_admin_service`, `card_service`, `SkillRadar`, `study_dashboard_*`

## Per-item verdicts

Verdict legend:
- **RETIRE-NOW** — zero live consumers, or trivially re-pointed in same commit
- **RETIRE-WITH-MIGRATION** — live consumers exist; migration steps enumerable
- **DEFER** — blocked by dependency outside Phase 6 scope (named blocker)
- **DONE** — already shipped in another slice; no action needed

### Theme 1 — FE legacy route mounts

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T1.1** `/learn/category/:id` mount + `pages/CategoryDetail.tsx` | `App.tsx:98`; `Learn.tsx:133` navigates here | RETIRE-WITH-MIGRATION | Re-point `Learn.tsx:133` (LearnHabitMode `?category=` consumer) to either `/learn/lesson/:id` OR drop the "browse by category" affordance entirely. Then `git rm pages/CategoryDetail.tsx`. |
| **T1.2** `/learn/card/:id` mount + `pages/CardViewer.tsx` | `App.tsx:99`; `CategoryDetail.tsx:159` navigates here; `useCardViewer.ts` | RETIRE-WITH-MIGRATION | Cascades from T1.1 (only nav source is the page being deleted). `git rm pages/CardViewer.tsx` + `hooks/useCardViewer.ts`. |
| **T1.3** `/study/category/:id` + `/study/card/:id` redirects | `App.tsx:136-137` (pure redirects to T1.1/T1.2 targets) | RETIRE-NOW | Mechanical removal once T1.1/T1.2 retire — redirects to dead routes. |
| **T1.4** `/learn/mission` mount + `MissionMode.tsx` | `App.tsx`; live Mission Mode surface; reads `Card`/`Category` | DEFER | Spec `01` §5.2 states Mission Mode "operates on legacy schema until a Phase-6 follow-up retires it (out of the 18-slice plan)". Spec `09` line 822: "Slice 6.15 — Phase 6 cleanup. Decides whether to retire". Out-of-Phase-6 work. |

### Theme 2 — FE legacy components & types

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T2.1** `components/layout/Navbar.tsx` | `LandingPage.tsx`, `LoginPage.tsx` (LIVE imports) | DEFER + flag | B-010 row in BACKLOG.md says "Dead code. Delete after confirming zero imports." — but disk shows 2 live importers. **B-010 is stale**; Navbar is not orphan. Triage flags this as a separate finding (file follow-up to revisit B-010). Out of slice-15 scope. |
| **T2.2** `components/study/QuizPanel.tsx` | `pages/DailyReview.tsx` daily-card flow → `POST /api/v1/study/review` | RETIRE-WITH-MIGRATION | Cascades T3.3 + T5.1. Once `/api/v1/study/...` retires, QuizPanel + DailyReview legacy path go too. Slice 6.5 already shipped `QuizItemPanel.tsx` as the Phase-6 replacement. |
| **T2.3** `components/progress/SkillRadar.tsx` | `pages/Profile.tsx` (LIVE consumer in user-facing page) | DEFER | Spec `09` G-7 says radar/heatmap go dark in 6.15 — but the SkillRadar widget is mounted on the Profile page, not the dashboard. Removing requires Profile-page redesign or a stub replacement. Defer to Phase 6.16 (FSRS retention dashboard) re-platform per spec `01` §5.2. |
| **T2.4** `types/index.ts:148-158` `Card` interface | `useCardViewer.ts:3` (sole direct consumer per spec `01` §5.2) | RETIRE-WITH-MIGRATION | Cascades T1.2 (CardViewer page deletion). Single-line type removal. |
| **T2.5** `hooks/useCardViewer.ts` | Imported by `pages/CardViewer.tsx` only | RETIRE-WITH-MIGRATION | Cascade T1.2. `git rm`. |

### Theme 3 — BE legacy services

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T3.1** `services/gap_mapping_service.py` | `app/api/routes/onboarding.py` (LIVE route `/api/v1/onboarding/recommendations`); 2 test files | RETIRE-WITH-MIGRATION | Two viable paths: (a) re-point onboarding.py to call `deck_ranker_service.rank_decks_for_user` and translate output to the existing recommendations contract; OR (b) delete the recommendations endpoint entirely if FE no longer consumes (audit FE onboarding pages first). Spec `07` §3 explicitly defers the retire-or-rewrite decision to slice 6.15. |
| **T3.2** `services/card_admin_service.py` | `app/api/v1/routes/admin.py` (LIVE admin CRUD route) | RETIRE-WITH-MIGRATION | Slice 6.4 already shipped Phase-6 admin authoring on `lessons` / `quiz_items`. Cleanup = remove legacy admin endpoints from `admin.py` + delete `card_admin_service.py`. Verify admin UI page no longer mounts the legacy CRUD before delete. |
| **T3.3** `services/study_service.py` legacy FSRS path | `app/api/v1/routes/study.py`; gap_mapping_service; tests | RETIRE-WITH-MIGRATION | Cascades T5.1 (the route mount) + T2.2 (the FE submitter). Service retirement = `git rm` + delete tests once route + FE detached. |
| **T3.4** `services/experience_service.py` (CardProgress narrative source) | Reads `card_progress` for "experience narrative" generation; consumed by experience routes | DEFER | Spec `01` §5.2: "Slice 6.15 cleanup OR a future slice migrates the narrative source". No Phase-6-schema narrative target exists yet (`quiz_item_progress` is FSRS state only, no narrative concept). Migrating means designing a new narrative source — out of cleanup scope. |
| **T3.5** `services/mission_service.py` | Reads `Card`; consumed by Mission Mode routes + FE | DEFER | Mission Mode retirement is "out of the 18-slice plan" per spec `01` §5.2. Cannot remove without removing Mission Mode itself. |
| **T3.6** `services/onboarding_checklist_service.py` | Reads `Card` for "studied N cards" telemetry checklist | DEFER | Spec `01` §5.2: "Audit later — check if checklist needs to count quiz_item reviews instead". Re-pointing the count source requires deciding what counts as "studied" in Phase-6 schema. Decision-needed; not pure cleanup. |
| **T3.7** `services/progress_service.py` (radar/heatmap) | Consumes `card_progress`; serves `/api/v1/progress/radar` + `/api/v1/progress/heatmap` | DEFER | Spec `01` §5.2: "Slice 6.16 (FSRS retention dashboard) re-platforms this". Phase-6 owns the re-platform; cleanup follows. |

### Theme 4 — BE dual-read collapses

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T4.1** `services/home_state_service.py` dual-read collapse | Currently reads BOTH `card_progress` + `quiz_item_progress` for `last_review_at` per spec `01` §5.2 | RETIRE-WITH-MIGRATION | Drop the `card_progress` query side; keep `quiz_item_progress` only. Single-file edit, ~5-10 lines, plus test fixture updates. Gated on T6.3 sequencing (collapse before drop or simultaneous). |
| **T4.2** `services/admin_analytics_service.py` UNION collapse | UNION reads `card_progress` ∪ `quiz_item_progress` for admin metrics | RETIRE-WITH-MIGRATION | Drop the `card_progress` UNION leg. Same shape as T4.1. |
| **T4.3** `services/reminder_service.py` UNION collapse | Daily reminder query joins `EmailPreference` × UNION(card_progress, quiz_item_progress) | RETIRE-WITH-MIGRATION | Drop the `card_progress` leg. Same shape. |

### Theme 5 — BE legacy routes

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T5.1** `/api/v1/study/...` mount | `routes/study.py`; FE `QuizPanel.tsx` + `DailyReview.tsx` + tests | RETIRE-WITH-MIGRATION | Cascade T3.3 + T2.2. Unmount router from `app/main.py`; `git rm routes/study.py`. Verify slice 6.2's `/api/v1/quiz-items/...` covers all FE flows first. |
| **T5.2** `/api/v1/cards/...` mount + `services/card_service.py` | `routes/cards.py`; `card_service.py`; consumed by FE `CardViewer.tsx`, `DailyReview.tsx`, `MissionMode.tsx` | RETIRE-WITH-MIGRATION | Cascade T1.2 + T2.2 + T3.5. Delete after FE replacements ship. Mission-mode dependency means full retirement waits on T3.5/T1.4 (DEFERRED) — partial retirement (delete only the unused endpoints) feasible if scoped carefully. |
| **T5.3** `/api/v1/progress/radar` + `/api/v1/progress/heatmap` | `routes/progress.py` reading `card_progress` | DEFER | Spec `09` G-7 says these go dark in 6.15. Spec `01` §5.2 says slice 6.16 re-platforms. Phase-6 cleanup follows the re-platform; not a 6.15 item. |
| **T5.4** `routes/feedback.py` `card_feedback` writes | Live route writing to `card_feedback` table | RETIRE-WITH-MIGRATION (gated on B-094b) | Slice 6.13.5b (B-094b 🔴 forward-filed) ships the user-thumbs route on `card_quality_signals`. Once B-094b ships, feedback.py's `card_feedback` writes can be replaced with `card_quality_signals` writes (or the route can be deleted if FE moves to slice 6.13.5b's new endpoint). Cannot retire before B-094b. |

### Theme 6 — DB table drops

Each is a `DROP TABLE` in the same Alembic migration; they are 4 SQL
operations, gated on every consumer above being migrated.

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T6.1** drop `cards` | `card_service`, `card_admin_service`, `gap_mapping_service`, `mission_service`, `study_service`, `onboarding_checklist_service`, `routes/cards.py`, `routes/study.py`, `routes/admin.py`, `models/card.py` | RETIRE-WITH-MIGRATION | Gated on T3.1 + T3.2 + T3.3 + T3.5 + T3.6 + T5.1 + T5.2 retirements. Drop is one Alembic line; the prerequisites are the migration. |
| **T6.2** drop `categories` | `card_service`, `gap_mapping_service`, `study_service`, `mission_service`, `routes/cards.py`, `routes/study.py`, `models/category.py` | RETIRE-WITH-MIGRATION | Same gating as T6.1 (subset of consumers). |
| **T6.3** drop `card_progress` | 11 services + routes (study, progress, admin_analytics, home_state, reminder, experience, pro_digest, mission, onboarding_checklist, card_admin, paywall_service) + tests + models | RETIRE-WITH-MIGRATION | Gated on T3.3 + T3.4 + T3.5 + T3.6 + T3.7 + T4.1 + T4.2 + T4.3 + T5.1 + T5.3. Many DEFERRED dependencies — drop pushes well past slice 6.15. |
| **T6.4** drop `card_feedback` | `routes/feedback.py`, `models/card_feedback.py` | RETIRE-WITH-MIGRATION | Gated on T5.4 (B-094b shipping). |

### Theme 7 — Helper / type consolidation

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T7.1** Lift `DailyStatus` from `schemas/study.py` to shared module | Currently re-imported by `schemas/quiz_item.py` per spec `02` §6.2 ("weak coupling — slice 6.15 cleanup target") | RETIRE-NOW | Single import-redirect: create new `schemas/daily_status.py` (or move to `schemas/__init__.py`), update both importers. ~3-line change. |
| **T7.2** `_next_local_midnight` dedupe | Duplicated in `study_service.py` AND `quiz_item_study_service.py` per B-062 closure ("duplicated locally per OQ-3 — slice 6.15 git rm cleanliness") | RETIRE-NOW | Move helper to a shared util, delete the duplicate. ~1-line removal once shared. |
| **T7.3** `_resolve_plan` extraction to `curriculum_visibility.py` | Already extracted in slice 6.6 (B-074, D-6) per spec `07` §3 line 168-172 | DONE | No action needed in slice 6.15. Spec `02` line 402/476 reference is now resolved on disk. |
| **T7.4** FSRS helper consolidation across legacy + Phase-6 paths | Specs `02` D-1 + `04` line 289 — "no shared FSRS-helper module" pending | RETIRE-WITH-MIGRATION (subsumed by T3.3) | Folds into T3.3 — once `study_service.py` retires, the legacy FSRS path is gone and there is no consolidation surface left. Not a separate slice item. |

### Theme 8 — Telemetry / event deprecation

| Item | Live consumers | Verdict | Rationale |
|------|---------------|---------|-----------|
| **T8.1** `study_dashboard_viewed` final-disposition tag | Zero emitters on disk (grep confirms) | RETIRE-NOW | Remove the catalog row in `.agent/skills/analytics.md`. No code change needed. |
| **T8.2** `study_dashboard_source_hint_shown` retire-or-keep | Live emitter at `Learn.tsx:302` (slice 6.7 preserved per spec `08` §9 + B-077 D-8 lock) | DEFER | Spec `08` §9.2 explicitly preserved through 6.7. Decision pending — needs Dhamo input (rename to `learn_source_hint_shown`? retire entirely? leave as-is for cross-page identity tracking?). Not a mechanical cleanup. |
| **T8.3** Telemetry-confirmation gate before BE-route drops | Audit `phase-6-scout.md` R-8: "Slice 6.15 (cleanup) should run LAST and consume telemetry" | PROCESS | Not a deletion item — a Step 0 instruction for the impl slice that does T5.1/T5.2 retirements. Convention, not artifact. |

## Summary

### Bucket counts

- **RETIRE-NOW (4):** T1.3, T7.1, T7.2, T8.1
- **RETIRE-WITH-MIGRATION (18):** T1.1, T1.2, T2.2, T2.4, T2.5, T3.1, T3.2, T3.3, T4.1, T4.2, T4.3, T5.1, T5.2, T5.4, T6.1, T6.2, T6.3, T6.4
  - (T7.4 is listed as a separate item in §Theme 7 but is operationally *subsumed* by T3.3 — folded into the count above as 0 incremental work. The 18 total reflects distinct artifact-level deletions.)
- **DEFER (9):** T1.4, T2.1, T2.3, T3.4, T3.5, T3.6, T3.7, T5.3, T8.2
- **DONE (1):** T7.3
- **PROCESS (1):** T8.3

### Stop-condition trigger

The triage produces **18 RETIRE-WITH-MIGRATION items**, exceeding the
prompt's >15 stop threshold. Per the prompt's stop language, this
"suggests Phase 6 cleanup is actually Phase 7 scope."

The on-disk reality reinforces the count: T6.1 (drop `cards`) gates
on 7 service retirements; T6.3 (drop `card_progress`) gates on 10
service retirements (5 of which are DEFERRED to outside Phase 6).
A single "slice 6.15" cannot land all of this without redefining
slice scope.

### Recommended spec scope

Three viable shapes; recommendation is **Option C** (split):

**Option A — Single umbrella spec.** Author one `15-legacy-retirement.md`
covering all 18 RETIRE-WITH-MIGRATION items + 4 RETIRE-NOW items.
Spec body would be ~2500-3000 lines; impl would forward-file ~5-7
sub-slices (`6.15a`-`6.15g`). Risk: spec authorship cost is high
(several days), and the umbrella may bottleneck on locked decisions
that only become clear after the first sub-slice ships.

**Option B — Tight cleanup spec for the easy wins.** Author
`15-legacy-retirement.md` covering ONLY the 4 RETIRE-NOW items + the
2 cleanest RETIRE-WITH-MIGRATION clusters (T7.4 helper-fold + T1.3
redirect-removal). Forward-file separate B-### rows at 🟦 (parked)
for the other 16 migration items, each scoped against its concrete
prerequisite (e.g. "B-### gap_mapping retirement: gated on onboarding
recommendations decision"). Risk: under-promises; chat-Claude has to
re-evaluate the parked rows individually anyway.

**Option C — Split into two independent specs (RECOMMENDED).**

1. **`15-legacy-retirement-easy-wins.md`** (1 impl slice, ~150-300 lines):
   T1.3 + T7.1 + T7.2 + T8.1 + T7.4 (cascade-deletion of `study_service`
   helpers if T3.3 is co-shipped) — 4-5 items, all mechanical, no
   migration design surface.

2. **`16-legacy-cards-schema-retirement.md`** (3-4 impl slices,
   ~1500-2000 lines spec, cascading scope):
   - Slice 16a: FE-side cleanup (T1.1 + T1.2 + T2.2 + T2.4 + T2.5)
   - Slice 16b: BE service migrations (T3.1 + T3.2 + T3.3 + T5.1 + T5.2)
   - Slice 16c: dual-read collapses (T4.1 + T4.2 + T4.3 + T5.4 once B-094b)
   - Slice 16d: table drops (T6.1 + T6.2 + T6.3 + T6.4) — gated on all
     prior + DEFERRED items (T3.7 / T5.3 / T6.3 specifically wait on
     slice 6.16 FSRS retention dashboard re-platform)

The "16" numbering is illustrative — exact slot per phase-6 catalog.

### Estimated impl slice count for Option C

- Easy-wins spec: **1 slice** (~+0..+5 BE tests, ~+0..+3 FE tests)
- Cards-schema retirement spec: **4 slices** (16a/b/c/d), with 16d
  gated on slice 6.16 (FSRS retention re-platform) shipping first
  before T6.3 can land

### BACKLOG row recommendations

Items to file as 🟦 PARKED rows (chat-Claude triages activation per
cohort discipline):

- **B-### "Phase 6 — DEFERRED legacy items audit"** — umbrella row
  pointing at the 10 DEFER items, with each linked to its blocker
  (Mission Mode retirement / experience narrative source / slice 6.16
  re-platform / B-094b)
- **B-### "Phase 6 — Mission Mode retirement scope"** — wraps T1.4 +
  T3.5; out-of-18-slice-plan; needs separate scoping
- **B-### "Phase 6 — Profile page SkillRadar disposition"** — wraps
  T2.3; needs Profile-page redesign decision
- **B-### "Phase 6 — `study_dashboard_source_hint_shown` rename or
  retire"** — wraps T8.2; decision-needed
- **B-010 review** — Navbar.tsx is NOT orphan on disk (live in
  LandingPage + LoginPage); B-010 row is stale and should be either
  closed (no action) or rewritten to track a real cleanup target

## Out of scope (deliberately)

- Authoring the spec(s) themselves — this triage is the input, not
  the spec.
- Estimating test deltas at slice granularity — done at spec-author
  time, not triage time.
- Deciding the Mission Mode retirement timing — out of Phase 6
  scope per spec `01` §5.2.
- Re-evaluating B-010's Navbar claim — flagged here, but B-010 row
  edit is its own slice.

## Closure

- Closes **B-100** (single-slice scout, doc-only).
- No code touched. No tests run (R14 exception (b) — pure audit).
- BE 842 / FE 456 carry-forward unchanged.
