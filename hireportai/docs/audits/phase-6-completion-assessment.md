# Phase 6 completion assessment

**Audit date:** 2026-05-02
**Anchor HEAD:** `2f82c27`
**Mode:** scout (Mode 3, read-only — R14 exception (b))
**Closes:** B-111

## Why this exists

Triage `phase-6-cleanup-triage.md` (B-100, `5291d9e`) tripped the >15
stop threshold for slice 6.15 by enumerating 18 RETIRE-WITH-MIGRATION
items deferred to "spec 16." Slice 6.15 (B-102, `e36902c`) shipped
the 4 RETIRE-NOW easy-wins. The remaining items now sit either in a
yet-unauthored slice 6.16 spec or in DEFER buckets blocked by
out-of-Phase-6 work (Mission Mode retirement, Profile-page redesign,
slice 6.16 FSRS retention dashboard re-platform).

The question for this scout: can Phase 6 be declared ✅ complete at
HEAD `2f82c27`, freeing chat-Claude to redirect to the Stripe
launch-readiness cluster (E-033 / E-035 / E-036 / E-039)?

## Phase 6 scorecard

All 16 spec files under `docs/specs/phase-6/` map to ✅ shipped
slices.

| Slice | Spec file | BACKLOG ID(s) | Closure SHA | Date |
|-------|-----------|---------------|-------------|------|
| 6.0 | 00-analytics-tables.md | B-069 | `e7a0044` | 2026-04-26 |
| 6.1 | 01-foundation-schema.md | B-061 | `a989539` / `f621248` | 2026-04-26 |
| 6.2 | 02-fsrs-quiz-item-binding.md | B-062 | `7b654fb` / `a02639c` | 2026-04-26 |
| 6.3 | 03-lesson-ux.md | B-063 | `ba00331` | 2026-04-26 |
| 6.4 | 04-admin-authoring.md | B-064 + B-065 + B-067 + B-068 | `b0806d0` / `d6bda3b` / `634f633` / `78abe56` | 2026-04-27 |
| 6.4.5 | 05-seed-lessons.md | B-071 | `ac5b905` | 2026-04-27 |
| 6.5 | 06-read-time-invariants.md | B-072 | (impl per RC) | 2026-04-28 |
| 6.6 | 07-deck-lesson-ranker.md | B-074 | (impl per RC) | 2026-04-28 |
| 6.7 | 08-persona-learn-page.md | B-077 | (impl per RC) | 2026-04-28 |
| 6.8 | 09-fsrs-dashboard.md | B-080 | (impl per RC) | 2026-04-29 |
| 6.10 | 10-ai-ingestion-pipeline.md | B-083 | (impl per RC) | 2026-04-30 |
| 6.11 | 11-content-quality-retention.md | B-084 | `95104d2` | 2026-05-01 |
| 6.13 | 13-pro-digest-opt-out.md | B-087 | `d020f4d` | 2026-05-01 |
| 6.13.5 | 12-quality-signals.md | B-094a + B-094b | `91be54f` / `85860d5` | 2026-05-02 |
| 6.14 | 14-daily-digest-cron.md | B-098 | `bcd89ce` | 2026-05-02 |
| 6.15 | 15-legacy-retirement-easy-wins.md | B-101 + B-102 + B-103 | `b50a592` / `174e479` / `e36902c` | 2026-05-02 |

User-facing surface count: 16/16 specs shipped. Zero ✅-marked
specs roll back to 🔴 on disk re-check.

## Remaining items (slice 6.16 scope)

Per triage `phase-6-cleanup-triage.md`, slice 6.16 would cover the
18 RETIRE-WITH-MIGRATION items + the 9 DEFER items. None of these
ship a new user feature — every one is legacy-schema retirement or
dual-read collapse.

### RETIRE-WITH-MIGRATION (18 items, deferred to slice 6.16+)

Cards-schema retirement umbrella: T1.1, T1.2, T1.3, T2.2, T2.4, T2.5,
T3.1, T3.2, T3.3, T4.1, T4.2, T4.3, T5.1, T5.2, T5.4, T6.1, T6.2,
T6.3, T6.4.

Per-item launch-block analysis:

| Bucket | Items | User-visible? | Blocks Stripe launch? | Disposition |
|--------|-------|---------------|------------------------|-------------|
| FE legacy routes (`/learn/category`, `/learn/card`) | T1.1 + T1.2 + T1.3 | Yes (live nav targets) but Phase-6 namespaced replacements ship via lessons | No | Slice 6.16 — post-launch cleanup |
| BE legacy services (gap_mapping, card_admin, study) | T3.1 + T3.2 + T3.3 | No (admin-only / cascade-replaced) | No | Slice 6.16 — post-launch cleanup |
| Dual-read collapses (home_state, admin_analytics, reminder) | T4.1 + T4.2 + T4.3 | No | No | Slice 6.16 — post-launch cleanup |
| BE legacy routes (`/api/v1/study`, `/api/v1/cards`, `/api/v1/feedback`) | T5.1 + T5.2 + T5.4 | No (FE migrates to quiz_items + lessons) | No | Slice 6.16 — post-launch cleanup |
| DB table drops (cards, categories, card_progress, card_feedback) | T6.1 + T6.2 + T6.3 + T6.4 | No (legacy tables, dual-write paths exist) | No | Slice 6.16d — gated on every consumer above + on slice 6.16 (FSRS retention dashboard) re-platform |
| FE legacy components/types (QuizPanel, Card type, useCardViewer) | T2.2 + T2.4 + T2.5 | No (replaced by QuizItemPanel + LessonRenderer) | No | Slice 6.16 — post-launch cleanup |

T5.4 unblocked at HEAD `2f82c27` because B-094b (`85860d5`) shipped
the user-thumbs route on `card_quality_signals`. Cleanup work still
needs spec authoring + impl slice.

### DEFER (9 items, blocked outside Phase 6)

| Item | Blocker | User-visible impact |
|------|---------|---------------------|
| T1.4 Mission Mode | Out-of-18-slice-plan retirement | Live feature; works as-is |
| T2.1 Navbar.tsx | B-104 (🟦 PARKED — premise correction needed) | Live in LandingPage + LoginPage; works as-is |
| T2.3 SkillRadar | Profile-page redesign | Live in Profile; works as-is |
| T3.4 experience_service | Narrative source design | Used in admin/experience routes; works as-is |
| T3.5 mission_service | Mission Mode retirement timing | Mission Mode live |
| T3.6 onboarding_checklist_service | "studied N cards" semantics in Phase-6 | Onboarding checklist live |
| T3.7 progress_service (radar/heatmap) | Slice 6.16 FSRS retention dashboard re-platform | `/api/v1/progress/*` routes live |
| T5.3 `/api/v1/progress/*` routes | Same as T3.7 | Live |
| T8.2 `study_dashboard_source_hint_shown` | Decision-needed (rename / retire / keep) | Telemetry name; non-functional |

None of the DEFER items block a user-visible feature; all are
post-launch hygiene.

## Stripe launch-readiness cluster status

| BACKLOG | Status | Phase 6 dependency? |
|---------|--------|----------------------|
| E-033 — Manage Subscription billing portal failure (P1 launch blocker) | 🟦 (test-mode resolved; live-mode Dashboard save + E-039 round-trip pending) | None — Stripe config + upgrade-flow run |
| E-035 — Stripe integration audit (P2) | 🟦 | None |
| E-036 — Stripe E2E test suite (P1) | 🟦 | Depends on E-033 fix; independent of Phase 6 |
| E-039 — Test paid flow E2E (P2) | 🟦 | Depends on E-033; independent of Phase 6 |

The Stripe cluster has zero dependency on Phase 6 cleanup work. E-033
needs ops actions (Stripe Dashboard config save in live mode) plus a
single end-to-end upgrade-flow run; E-035 is a Mode 1 read-only audit;
E-036 is a marker-gated test-suite slice; E-039 is the manual smoke
to close E-033.

## Verdict

**YES-WITH-CAVEATS — Phase 6 can be declared ✅ complete at HEAD
`2f82c27`.**

Caveats:

1. Slice 6.16 (cards-schema retirement umbrella) remains unauthored.
   Per triage Option C, this is intentional — single slice 6.15 cannot
   land 18 migration items. Slice 6.16 would forward-file 4 cascading
   impl slices (16a/b/c/d) with 16d gated on FSRS retention dashboard
   re-platform. **None of this is launch-blocking.**

2. B-104 (Navbar.tsx orphan-status correction) sits at 🟦 PARKED.
   chat-Claude triages activation. **Not launch-blocking.**

3. Process health-check at `2f82c27` reports 4 warns + 1 fail
   (process-tax 53% — sample-window artifact per B-108/B-109 JCs, not
   a regression). **Not launch-blocking.**

4. The original "18 slice" Phase-6 count (lock-list line) numerically
   diverges from the 16 shipped spec files — 6.9 was never authored
   (likely subsumed) and 6.12 was merged into 6.7 per audit slice-by-
   slice review. The 16-spec catalog represents the actual locked
   Phase-6 envelope.

The Phase-6 user-facing surface — admin authoring, persona Learn
page, FSRS dashboard, deck/lesson ranker, AI ingestion pipeline,
content-quality retention dashboard, quality signals, Pro digest
opt-out, daily digest cron — all live at HEAD `2f82c27`.

## Recommended next work

The first Stripe cluster prompt to draft is **E-033 closure**:

1. **Ops action (Dhamo, not CC):** save default Stripe Customer
   Portal config at `dashboard.stripe.com/settings/billing/portal`
   in live mode. Mirrors the test-mode save Dhamo already completed
   on 2026-04-21 per E-033 row.

2. **CC slice — E-033 + E-039 closure (Mode 2 impl + verification):**
   - Step 0: confirm live-mode Dashboard save by Dhamo (manual)
   - Step 1: run upgrade flow locally → populate `stripe_customer_id`
     on a real subscription row
   - Step 2: re-run `scripts/smoke_billing_portal.py --customer
     cus_xxx` → assert Check 2 PASS
   - Step 3: close E-033 + E-039 in same commit; file BACKLOG
     close-line referencing the smoke-script SHA + transcript
   - Expected test-count delta: 0 (manual smoke validation, no new
     test surface). R14 exception (b) — verification, no design.

After E-033/E-039 ship, sequence E-035 (Mode 1 audit, half-day) before
E-036 (impl Mode 2). E-035 surfaces silent-drift risks the audit can
catch before E-036 commits to a test-suite scaffolding.

Slice 6.16 (cards-schema retirement spec authoring + 4 impl slices)
remains a post-launch backlog item. Recommend chat-Claude/Dhamo defer
its authoring until after Stripe launch unblocks production users.

## Closure

- Closes **B-111** (single-slice scout, doc-only).
- No code touched. No tests run (R14 exception (b) — pure scout).
- BE 824 / FE 466 carry-forward unchanged.
