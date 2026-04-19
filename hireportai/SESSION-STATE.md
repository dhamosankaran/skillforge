# SESSION STATE — SkillForge

> **Purpose**: This is the live "where we are right now" pointer for Claude Code. Read at the start of every session. Update at the end.
> **Companion to**: AGENTS.md (how project works) + CLAUDE.md (how to behave) + spec file (what to build).
> **Update cadence**: End of every implementation slice. Drift will hurt — keep this current.

---

## Active Phase

**Phase 5: Enhancements + UX Restructure**

Phases 0–4 are complete. Phase 5 absorbs the ad-hoc enhancement work plus the UX restructure (PersonaPicker, /learn and /prep namespaces, persona-aware home dashboard) plus the v2.2 patch additions from the user-flow audit.

---

## Active Prompt Files

- `claude-code-prompts-all-phases-v2.md` (v2.1) — base of Phase 5
- `claude-code-prompts-all-phases-v2.2-patch.md` — additions from flow audit (5 new slices + 1 spec amendment)
- Always read both when planning Phase 5 work.

---

## Last Completed Slice

**P5-S18** — HomeDashboard + widget catalog. Replaced `HomeDashboardPlaceholder` with a real `src/pages/HomeDashboard.tsx` that branches on `user.persona` into three render modes with `data-testid="home-mode-<persona>"` markers. Implemented the `DashboardWidget` primitive (`src/components/home/DashboardWidget.tsx`) with the spec #35 §Solution contract (`loading` → `SkeletonCard`, `data` → children + optional footer action, `empty` → `emptyMessage`, `error` → `errorMessage` + `Try again` retry). Seven widgets under `src/components/home/widgets/`: `TodaysReviewWidget` (fetchDailyQueue → total_due), `StreakWidget` (useGamification → current_streak/longest_streak), `WeeklyProgressWidget` (wraps `ActivityHeatmap`, empty-gate on `total_xp === 0 && longest_streak === 0`), `LastScanWidget` (derives from `getApplications()` desc by created_at), `InterviewTargetWidget` (AuthContext company+date, display-only — no Edit action per Resolved Decision #6), `CountdownWidget` (Mode 1 inline `<input type="date">` → `updatePersona({persona, interview_target_date})`; Mode 2 wraps `mission/Countdown` + active-mission CTA via `fetchActiveMission()` — `"Start a Mission sprint"` or `"View mission"`), `TeamComingSoonWidget` (static copy, action-less — no waitlist component found on disk). Grid `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`. Greeting `Welcome back, <first name>.` with `Welcome back.` fallback on empty name. `home_dashboard_viewed` capture with `useRef` idempotency guard (AC-7), `{persona}` property. `App.tsx` swap: import + route element `HomeDashboardPlaceholder → HomeDashboard`; `tests/App.redirects.test.tsx` updated to stub new path. `HomeDashboardPlaceholder.tsx` deleted. Analytics catalog row added. AGENTS.md `/home` row updated. FE tests **38 → 78** (+40): 6 `DashboardWidget.test.tsx`, 9 `HomeDashboard.test.tsx`, 25 across seven `widgets/*.test.tsx`. AC-9 regression-catch asserted: `CountdownWidget` Mode 1 submit calls `updatePersona` with `{persona: 'interview_prepper', interview_target_date: '...'}`. BE unchanged at **184 unit + 6 integration deselected**. tsc clean, `npm run build` succeeds.

---

## Previously Completed

**P5-S17** — Frontend PersonaPicker page + PersonaGate + AppShell hide-list + legacy cleanup. New full-page picker at `/onboarding/persona` (`src/pages/PersonaPicker.tsx`) renders 3 cards using PRD §1.3 copy (Interview-Prepper, Career-Climber, Team Lead); Interview-Prepper card expands with optional `<input type="date">` and a `maxLength={100}` company input (live counter). Continue calls `updatePersona()` → `PATCH /api/v1/users/me/persona`, merges the response into AuthContext via `updateUser`, then `navigate('/home', { replace: true })`. Inline error on API failure, selection preserved. Fires `persona_picker_shown` on mount and `persona_selected` after 2xx (both new, added to `.agent/skills/analytics.md`). New `src/components/PersonaGate.tsx` wraps the protected subtree inside `ProtectedRoute` — redirects `user.persona === null` to `/onboarding/persona` on every protected path except `/`, `/login`, `/onboarding/persona`. `AppShell.CHROMELESS_PATHS` now includes `/onboarding/persona` so TopNav/MobileNav hide there. `AuthUser.persona` narrowed to `Persona = 'interview_prepper' | 'career_climber' | 'team_lead'`; legacy `target_company?`/`target_date?` fields dropped. `services/api.ts` `completeOnboarding` + legacy `updatePersona` (+ their request types) deleted; new `updatePersona(body): Promise<AuthUser>` targets the new endpoint. `StudyDashboard` `PERSONA_CONFIG` rekeyed to snake_case, literal comparisons updated (`'interview_prepper' | 'career_climber' | 'team_lead'`), field reads renamed to `user.interview_target_*`; settings-modal launchers ("Change goal" button + "Set your goal →" button) + `showPersonaPicker` state + legacy import all removed. `LoginPage` doc comment refreshed. Legacy `src/components/onboarding/PersonaPicker.tsx` deleted; `components/onboarding/` kept (holds `GuidedTour.tsx`). Existing test fixtures (`TopNav.test.tsx`, `MobileNav.test.tsx`, `App.redirects.test.tsx`) updated — dropped legacy fields, `'climber' → 'career_climber'`, and `App.redirects.test.tsx` now stubs `@/pages/PersonaPicker` instead of the deleted path. Analytics catalog: `persona_picker_shown` + `persona_selected` added to the active table; the two legacy events (`persona_changed`, `onboarding_persona_selected`) preserved in a new `#### Deprecated Frontend Events` subsection with commit-b5f42c2 markers so historical PostHog data + the Phase-4 dashboards spec stay cross-referenced (post-amend). AGENTS.md Frontend Routes table gained a `/onboarding/persona` row and the nav-chrome-hides sentence now lists the new path. Test counts: FE **38/38** (27 → 38: +6 PersonaPicker, +3 PersonaGate, +2 AppShell); BE unchanged at **184 unit + 6 integration deselected**. TypeScript clean, `npm run build` succeeds.

**Shipped:** pending — commit pending user push. (Previous slice P5-S17: commit `2c01cc7` (amend of `b5f42c2`) pushed to `origin/main` at 2026-04-18 19:49 UTC.) Auto-deploys to Vercel (frontend) + Railway (backend — no-op this slice) per CLAUDE.md §Rule 9. Resolves the known S16-leftover runtime breakage on `/learn` (`PERSONA_CONFIG[user.persona]` returning `undefined` for snake_case persona values).

---

## Next Slice

**P5-S18b** — State-aware dashboard variants (new user / returning user / streak-at-risk / interview-imminent). Layers state detection on top of the static P5-S18 layout. S18 shipped the widget grid + primitive; S18b adds persona-state branching inside widgets so content adapts to "new user no activity" vs. "returning user 7-day streak" vs. "interview in 5 days." See v2.2 patch file for the spec stub.

After P5-S9, continue in this order:
1. P5B (S10–S11) — cover letter, Generate My Experience
2. P5C (S12–S14) — route restructure
3. P5D (S15–S18, **S16-AMEND**, **S18b**, **S18c**) — PersonaPicker + HomeDashboard + state-aware + checklist. *(S19 obsoleted — see "Obsolete Slices".)*
4. P5E (S20–S22) — Analysis Results improvements
5. P5F (S23–S26, **S26b**, **S26c**) — Interview storage + cancel sub + paywall dismissal + webhook idempotency
6. P5G (S27–S30) — Settings + chat AI + interview date
7. P5H (S31–S34) — Admin insights + content feed
8. P5-FINAL (S35) — verify + housekeeping

**Bold = added in v2.2 patch.**

---

## Known-Broken Features (DO NOT modify unless fixing)

These are user-visible bugs. Don't refactor around them — they have dedicated fix slices.

| Feature | Symptom | Fix slice |
|---------|---------|-----------|
| Geo-Pricing Visibility | Audit complete (P5-S8): A+C fixed. Remaining deferred gaps — B: no price on LoginPage; D: ip-api.com rate-limit fallback mis-prices Indian users under load; E: Free-plan shows `$0` even for INR users. | Deferred (post-P5B) |
| Stripe Webhook Idempotency | Possible — duplicate webhook delivery could double-grant Pro. Audit pending. | P5-S26c |

---

## Active Refactor Zones (avoid drive-by changes)

- (P5-S13 landed): `src/App.tsx` carries the nine `/learn/*` + `/prep/*` namespaced routes and a ten-entry transitional redirect block. The redirect block is P5-S13's domain — do not edit it as part of unrelated work.
- (P5-S14 landed): `src/components/layout/TopNav.tsx`, `MobileNav.tsx`, `AppShell.tsx` are the nav source of truth. The legacy `src/components/layout/Navbar.tsx` is no longer imported by `App.tsx` but still sits on disk — delete it when we're sure no other callers exist (Phase 6 cleanup candidate).
- (P5-S17 landed): `src/pages/PersonaPicker.tsx` and `src/components/PersonaGate.tsx` are the persona onboarding surface. The picker ships without a "change persona" affordance by design (spec #34 Out of Scope) — do not add one here; the switch UX is a post-spec follow-up (see Deferred Hygiene Items).

---

## Recently Completed (last 5)

1. P5-S18 — HomeDashboard + widget catalog. `DashboardWidget` primitive (`loading/data/empty/error` states). Seven widgets under `src/components/home/widgets/`: TodaysReview, Streak, WeeklyProgress, LastScan, InterviewTarget (display-only), Countdown (Mode 1 inline date-setter → `updatePersona({persona, interview_target_date})`; Mode 2 wraps `mission/Countdown` + active-mission CTA), TeamComingSoon (action-less — no waitlist component on disk). Persona-keyed render modes (`home-mode-<persona>`), 1/2/3 responsive grid, greeting with first-name fallback, `home_dashboard_viewed` with useRef guard. `App.tsx` swapped `HomeDashboardPlaceholder` → `HomeDashboard`; placeholder deleted; `tests/App.redirects.test.tsx` updated. FE tests 38 → 78 (+40). BE 184/184 unchanged. AC-9 persona-in-PATCH-body regression assertion in `CountdownWidget.test.tsx`.
2. P5-S17 — Frontend PersonaPicker page + PersonaGate + AppShell hide-list + legacy cleanup. New `/onboarding/persona` route renders three persona cards (PRD §1.3 copy); Interview-Prepper expands with optional `interview_target_date` + `interview_target_company` (maxLength 100 + live counter); Continue → `PATCH /api/v1/users/me/persona` → merge into AuthContext → `navigate('/home', { replace: true })`. `PersonaGate` redirects null-persona users from all protected paths except `/`, `/login`, `/onboarding/persona`. `AppShell` hides chrome on `/onboarding/persona`. `AuthUser.persona` narrowed to `Persona` union; legacy `target_*` fields + legacy onboarding component (`src/components/onboarding/PersonaPicker.tsx`) + legacy `completeOnboarding`/`updatePersona` api helpers deleted. `StudyDashboard` PERSONA_CONFIG + persona comparisons rekeyed to snake_case; settings-modal launchers removed (no replacement — persona-switch UX is post-spec). Analytics: `persona_picker_shown` + `persona_selected` added; two legacy events removed (source file deleted). FE tests 27 → 38 (+6 PersonaPicker, +3 PersonaGate, +2 AppShell hide-list). Backend unchanged at 184+6.
2. P5-S16 — Persona backend foundations: Alembic migration `02bf7265b387` renames `target_*` → `interview_target_*` + retypes (DateTime→Date, String(255)→String(100)) + migrates legacy persona values (`team` → `team_lead`) + widens persona to String(30); new `PATCH /api/v1/users/me/persona` endpoint (JWT, 10/min) with `PersonaEnum` validation and conditional `onboarding_completed` flip; `/auth/onboarding` + `/auth/persona` deleted; `_user_dict` now returns `interview_target_*` instead of legacy keys. Frontend additively gains optional `interview_target_*` fields on `AuthUser` — persona literal union and legacy target_* kept to preserve StudyDashboard / legacy PersonaPicker typecheck until P5-S17. Backend tests +10 → 184/184 (6 integration deselected). Frontend 27/27 unchanged. S16-AMEND folded in.
3. P5-S14 — `TopNav` / `MobileNav` / `AppShell` shipped and wired into `src/App.tsx` (replacing `Navbar`). Four tabs (Home/Learn/Prep/Profile) + Admin for admins. `nav_clicked` event (`{namespace, from_path, to_path}`) fires on every tap. MobileNav is a fixed bottom bar with safe-area padding. All colors via design tokens — no hex literals. Tests: `TopNav.test.tsx` + `MobileNav.test.tsx`; frontend count 16 → 27. Flagged: transitional `deprecated_route_hit` event from the nav spec is not wired in the redirect block (P5-S13 gap, backfill out of scope).
4. P5-S13 — Route restructure + internal-reference sweep: `/learn/*` and `/prep/*` namespaces live in `src/App.tsx`, 10-entry `<Navigate replace>` redirect block covers the old flat paths, post-login target now `/home`, `HomeDashboardPlaceholder` added, daily-reminder email deep-link → `/learn/daily`. Sweep proof at `docs/audit/2026-04-p5-s13-sweep-proof.txt`. Frontend tests 5 → 16 (new `App.redirects.test.tsx`); backend 174/174.

---

## Open Decisions Awaiting Dhamo

| Decision | Context | Blocking? | Decide by |
|----------|---------|-----------|-----------|
| Free-tier interview question limit value | Implemented but value not validated against business model. P5-S6 will flag the current value for confirmation. | No | End of Phase 5 |
| Cancellation win-back flow (50% off 3 months) | Mentioned in P5-S26 spec as optional. | No | Before P5-S26 |
| **Strategic path to $100M ARR**: B2B pivot, adjacent expansion, or geo-volume play? | See `STRATEGIC-OPTIONS.md`. Affects every Phase 6+ decision. | Not yet | Before Phase 6 planning |

---

## Locked Decisions

### Decision: Daily review budget + free-tier scope
**Locked:** 2026-04-18
**Affected slices:** P5-S22 (FSRS Pro-gating), Phase 1 paywall logic (retroactive doc)

**1A — Free tier scope: CATEGORY-GATED (status quo).**
Free users are scoped to the Foundation category. No per-day review counter. No per-session counter. Daily Review for free users is unlimited within Foundation. The paywall trigger is non-Foundation category access, not review consumption.

Rationale: Career-Climber's conversion lever is breadth (full library access), not friction on the daily habit. Adding a per-day review counter would punish the most retentive persona and undermine the retention engine the product is built around. Category-based gating is already in the codebase (verified Step 2) and is the right default.

Implication for P5-S26b (paywall dismissal): the dismissal flow applies to category-access paywalls, not review-consumption paywalls (which don't exist).

**1B — FSRS daily-cap: HARD CAP at 20 cards/day, all plans.**
The Daily Review query (`get_daily_review`) returns at most 20 cards/day, all plans, free or Pro. Applies to:
- Daily Review queue (`/learn/daily`)
- Auto-injection of new cards (state=new)

Ordering inside the cap: due-review cards (state=review/learning/relearning) placed first, ordered by due_date ASC. New cards (state=new) fill remaining slots up to 20.

Mission Mode is exempt: the mission's daily_target wins inside `/learn/mission`. Mission cards are scoped to the mission's selected categories and don't double-count against the Daily Review cap on the same day. (Decision: Mission and Daily Review are separate queues. If user does Mission Mode that day, Daily Review still shows up to 20 of whatever's due outside the mission.)

Rationale: 20 cards × ~45 sec ≈ 15-min session = sweet spot for daily habit formation. Above this, FSRS death spiral risk (user opens app, sees 47 due, closes app, breaks streak). 20 is conservative headroom above the "Daily 5" brand framing.

Catch-up mode (offer to review backlog beyond 20) is deferred to a Phase 6 slice once we have data on overflow frequency.

**Implementation note for P5-S22:**
- Update `get_daily_review(user_id)` to apply `LIMIT 20` after ordering.
- Add unit test `test_daily_review_caps_at_20_when_overdue` (seed 30 due cards, assert response length == 20, assert oldest due_date returned first).
- Add unit test `test_daily_review_prefers_due_over_new` (seed 15 due + 10 new, assert response is 15 due + 5 new in that order).
- Update `study-engine.md` skill: change "Daily 5 = ... LIMIT 5" line to reflect 20-cap.

---

### Decision: Auto-save scan to tracker
**Locked:** 2026-04-18
**Affected slices:** P5-S5 spec amendment (tracker auto-populate), any future scan flow work

**Rule:** Auto-save when JD is provided, dedupe on `(user_id, jd_hash)`.

Behavior:
- Scan with JD pasted/uploaded → on scan-complete, upsert a tracker entry. Hash the normalized JD (whitespace-normalized, casefold, then SHA256) as `jd_hash`. If a tracker entry with `(user_id, jd_hash)` already exists, UPDATE it (`last_scan_id`, `current_ats_score`, `current_gaps`, `last_scanned_at`); do not create a duplicate.
- Scan without JD (resume-only / exploratory) → no tracker entry created. No prompt. User can scan again with a JD if they want it tracked.
- Inline confirmation toast on results page when auto-save fires: `"Saved to your tracker → [View]"`. Non-blocking, dismissible, ~4s auto-hide.

Rationale: A scan with a JD is, by definition, an application or close to one — high-value path, no friction. Resume-only scans are exploratory; auto-saving them pollutes the tracker and trains users to ignore it. Dedupe prevents the "scanned the same JD 4 times while iterating my resume" pollution. JD-hashing reuses the pattern already specified in spec #35 (interview question storage), so it's a familiar primitive.

**Implementation note for P5-S5 spec amendment:**
- Reuse the `hash_jd(text)` helper pattern from spec #35 (or extract to a shared util `app/utils/text_hash.py` if it doesn't already exist).
- On the tracker model, add unique constraint on `(user_id, jd_hash)` if not already present.
- Add toast component to scan results page; reuse existing toast primitive if available.
- PostHog: `tracker_autosaved` (with `is_update: bool`), `tracker_autosave_skipped_no_jd`.

**Deferred (S5-flag):** if PostHog later shows resume-only scans are a meaningful chunk of free-tier behavior, add a "Tracking an application? Add the JD" inline nudge on the results page. Not blocking.

---

## Resolved Decisions

### Decision 1 — Persona switch UX (resolved 2026-04-17)

**Resolution:** Full-page reroute to `/onboarding/persona`, not modal.

**Rationale:**
- New-user flow lands fresh; no page behind a modal worth seeing.
- Existing-user migration UX (P5-S19) fits better as a page with banner than as a modal with banner-header.
- PersonaGate becomes a clean `<Navigate to="/onboarding/persona" replace />` redirect — route-based gating is simpler to test than render-based overlay.
- Three fields on the surface (persona + `interview_target_date` + `interview_target_company` per v2.2 S16-AMEND) argue for page not modal.
- Mobile: full-screen modal ≈ full page, so the pattern matters on desktop where page wins.

**Affected slices:** P5-S15 (spec describes full-page UX), P5-S17 (PersonaGate implemented as redirect, not overlay), P5-S19 (existing-user banner sits at top of page).

### Decision 2 — Persona count (resolved 2026-04-17)

**Resolution:** Stay at 3 personas: Interview-Prepper, Career-Climber, Team Lead. No "New User" persona.

**Rationale:**
- PRD §1.3 lists 3. Playbook v2 lines 36-40, 207, 1231 consistent. v2.2 patch consistent.
- v2.1 P5-S15 prompt's "4 personas including New User" was a documentation bug — conflated the no-persona state with a persona value.
- "New User" is a state (no activity yet), not a durable intent. Handled by P5-S18b state-aware dashboard logic, not by a persona enum value.

**Affected slices:** P5-S15 spec (amended), P5-S16 (PersonaEnum has 3 values), P5-S17 (picker has 3 cards), P5-S18 (widget catalog has 3 modes).

### Decision 3 — Resolved 2026-04-17
Email deep-link coverage: App is pre-production, no legacy user traffic exists.
AC-5 reframed as internal-reference sweep (email templates, PostHog config,
hardcoded links) rather than external-facing 301 redirects. P5-S13 owns
executing the sweep.

### Decision 4 — Legacy `target_*` column overlap (resolved 2026-04-17)

**Resolution:** Rename in the P5-S16 migration. `target_company → interview_target_company` (String(255) → String(100)); `target_date → interview_target_date` (DateTime → Date). Via `op.alter_column`.

**Rationale:**
- Pre-production; row-data risk ≈ zero. `alter_column` preserves data regardless.
- Duplicate schema is tech debt "Phase 6 cleanup" will never actually reach.
- Small surface: model, migration, `/auth/me` serialiser. No legacy frontend UX reads the columns.

**Affected slices:** P5-S15 spec (amended — rename rather than keep-separate), P5-S16 (migration does rename + retype, with a pre-flight row-count diagnostic).

---

## Obsolete Slices

Slices that were in the backlog but are no longer needed. Do **not** ship them.

- **P5-S19 — Existing-user persona migration.** Obsoleted 2026-04-19 by local dev-DB wipe (77 user-gen rows removed; see Ops Log). No pre-S17 users exist in any environment: local is freshly wiped and production has never been opened to real traffic (Railway DB never accumulated users per prior decisions). The "auto-default vs force-pick" open decision is moot — `PersonaGate` (shipped in P5-S17) already redirects every `user.persona === null` session to `/onboarding/persona`, so all future users pick a persona at first login. Re-evaluate only if/when production users accumulate **before** a future persona-schema change requires backfill.

---

## Ops Log

Infra / data events outside the slice flow. Keep concise.

- **2026-04-19 — Local dev-DB user-data wipe.** Ran `scripts/wipe_local_user_data.py` against `localhost:5432/hireport`. Deleted 77 rows across 16 user-gen tables (users=3, subscriptions=3, card_progress=26, missions=1, mission_days=22, mission_categories=7, user_badges=6, gamification_stats=3, email_preferences=3, usage_logs=1, tracker_applications_v2=2, plus 5 empty tables). Preserved 38 content rows (cards=15, categories=14, badges=9) and `alembic_version` (1). Transaction-wrapped, committed cleanly. Railway and all remote DBs untouched. Stripe test-mode customer orphans accepted — no API cleanup. Motivation: unblock obsoleting P5-S19 existing-user migration; also clears stale dev state ahead of P5-S18b.

---

## Hard Constraints (current sprint)

These rules apply across Phase 5. Add or remove as the sprint changes.

- **Routes**: All new routes go under `/learn/*` or `/prep/*`. **No new flat routes.** (Reaffirmed at P5-S14 — `TopNav` / `MobileNav` only surface `/home`, `/learn`, `/prep`, `/profile`, `/admin`; any new flat path would have no nav home.)
- **Env vars**: Any new env var requires `.env.example` update in the same commit.
- **LLM calls**: All LLM calls go through the LLM router (`app/core/llm_router.py`, entry point `generate_for_task(task=..., ...)`). Don't bypass it. Pro for reasoning (rewrite, cover letter, gap analysis, chat-with-AI, admin insights). Flash for fast tasks (extraction, classification, simple Q&A).
- **PostHog events**: Every new user-facing feature fires at least one event. snake_case naming.
- **Backward compatibility**: Phase 5 cannot break existing user data. Migrations need defaults that backfill existing rows.
- **Persona gating**: Once PersonaPicker is shipped (P5-S17), all `/learn/*` and `/prep/*` and `/home` routes require `user.persona` to be set. Exception: `/profile`.
- **Stripe**: All webhook handlers must be idempotent (P5-S26c). No new webhook events without idempotency check.
- **Frontend test coverage**: Every new page added in Phase 5 (`HomeDashboard`, `PersonaPicker` page, `CardChatPanel`, `AdminInsights`, etc.) must ship with at least one Vitest test. Current frontend test count is **5** (only `PaywallModal`) — this number must grow with every Phase 5 UI slice.

---

## Deferred Hygiene Items

- `deprecated_route_hit` PostHog event not wired in the 10 `<Navigate>` redirect nodes in `src/App.tsx`. Defined in spec #12 §Analytics but deferred from P5-S13. Blocks Phase 6 redirect-block cleanup (no signal to confirm when old paths stop receiving hits).
- **AGENTS.md Models table User row (S16 retrofit)** — line 243 still lists legacy `target_company`, `target_date` column names. These were renamed by the P5-S16 migration (`02bf7265b387`) to `interview_target_company` (String(100)) and `interview_target_date` (Date). Update when the Models table is next edited. Surfaced during P5-S17 amend; out of scope for S17 itself.
- **Persona-switch UX from `/profile`** — post-P5-S17 follow-up (spec #34 Out of Scope). P5-S17 removed the legacy in-place "Change goal" modal from StudyDashboard (plus the "Set your goal →" CTA from the `user.persona === null` empty state on `/learn`). No replacement shipped; the persona-switch UX will reuse `/onboarding/persona` (likely `?mode=switch`) when the flow is specced. Until then, users cannot change persona post-pick.
- **StudyDashboard empty-state CTA gap** — the `user.persona === null` branch on `/learn` had its "Set your goal →" CTA button removed in P5-S17 (it launched the deleted settings-modal PersonaPicker). The surrounding "Your Goal / Tell us what you're working towards" card still renders but is now action-less. `PersonaGate` makes this branch effectively unreachable, so the visual gap is theoretical — but revisit with the next `/learn` empty-state redesign.
- **`docs/specs/phase-4/24-posthog-dashboards.md` event #13** — `onboarding_persona_selected` is referenced by name in the Phase-4 dashboards spec. The analytics catalog now carries a deprecation marker pointing to this spec; update the spec (or remove the dashboard entry) when the Phase-4 PostHog dashboard is decommissioned.
- **[S35-flag] `border-contrast` Tailwind class undocumented** — in use across widgets (AnimatedCard, SkeletonCard, DashboardWidget) but not listed in `.agent/skills/design-system.md` token inventory. Backfill the skill file during the next design-system touch.
- **[S35-flag] AGENTS.md Frontend Routes mission path drift** — AGENTS.md Frontend Routes table references `/api/v1/mission` (singular); `services/api.ts` and spec #35 use `/api/v1/missions/active` (plural). Align AGENTS.md to the code's canonical path.
- **[S35-flag, conditional — CONFIRMED P5-S18]** Team-features waitlist signup — no existing waitlist/email-capture/notify-me component was found during P5-S18 (`grep -rn "waitlist\|Waitlist\|WaitList\|NotifyMe\|NotificationSignup" src/` returned zero). `TeamComingSoonWidget` ships action-less; add a Team-features waitlist signup in a follow-up slice. Doubles as a PRD §1.5 Team-dashboards demand signal.
- **[S35-flag, P5-S18]** Spec #35 §API Contract lists Last Scan as `/api/v1/tracker`, but the existing `getApplications()` helper hits the legacy `/api/tracker`. P5-S18 reused the existing helper unchanged — migrating the helper to `/api/v1/tracker` is an orthogonal slice that affects every `Tracker.tsx` consumer. Align when the tracker migration is scheduled.
- **[S18-flag]** WeeklyProgress empty-state heuristic: currently uses `stats.total_xp === 0 && longest_streak === 0` as a proxy for "no review history" to avoid duplicating `ActivityHeatmap`'s fetch (`/api/v1/progress/heatmap?days=90`). Edge-case false negatives possible for users with XP from non-review sources or stale streak + empty current window. Fix: expose review-count from `ActivityHeatmap` via a render prop or callback, subscribe from widget.
- **[S18-flag]** `DashboardWidget` contract: `action` prop is hidden when `state === 'error'` (only "Try again" renders). This is sensible UX but not documented in spec #35 §Solution. Document when the primitive's contract is next touched, either in the spec or in a new design-system skill entry.

---

## Tech Debt (living log — tackle during P6 cleanup unless it escalates)

| Item | Detail |
|---|---|
| Legacy LLM provider factory | `app/services/llm/factory.py` + `claude_provider.py` + `gemini_provider.py` run parallel to the real router at `app/core/llm_router.py`. Not currently breaking. Do not extend the legacy factory — route all new LLM calls through `generate_for_task()`. Consolidate in Phase 6 cleanup. Surfaced by the 2026-04-17 audit. |
| Registration IP-blocking is DB-based, not Redis | `app/api/v1/routes/auth.py` inlines the limit check against the `registration_logs` table (30-day window query). The original playbook skill described a Redis counter. Both approaches work. Kept for P5-S4 backfill; no behavioural change planned. |
| Email-preferences API path mismatch | Frontend `hirelens-frontend/src/services/api.ts:314,321` calls `/api/v1/email-preferences`, but the backend router is mounted at `/api/v1/email-prefs` (`app/main.py`, confirmed in `AGENTS.md:187`). The endpoints currently 404 in production. Surfaced by the 2026-04-17 P5-S11 trace. Fix in a future slice — pick one canonical path (recommend the longer `/email-preferences` to match the spec at `docs/specs/phase-2/16-email-preferences.md`) and update both ends together. |

---

## Test Suite Status

- **Backend**: 184 unit passed, 6 integration deselected (last run: P5-S18)
- **Frontend**: 78/78 passing (last run: P5-S18)
- **Note**: Run full suites at the start of P5-S0 to establish a baseline before Phase 5 changes begin.

---

## Project File Inventory (canonical references)

### In repo (Claude Code reads these)

| File | Purpose |
|------|---------|
| `AGENTS.md` | How this project works (stack, conventions, deploy) |
| `CLAUDE.md` | How Claude Code should behave (rules, 3-strike, test gates) |
| `SESSION-STATE.md` | THIS FILE — live state pointer |
| `STRATEGIC-OPTIONS.md` | $100M ARR strategic options analysis. Read before Phase 6 planning. |
| `docs/prd.md` | Product requirements |
| `docs/specs/phase-N/NN-feature.md` | Per-feature specs |

### In Claude Project knowledge (Claude in chat reads these)

| File | Purpose |
|------|---------|
| `skillforge_playbook_v2.md` | Master phased plan (v3 due after P5-S35) |
| `claude-code-prompts-all-phases-v2.md` | v2.1 — slice-by-slice prompts (active) |
| `claude-code-prompts-all-phases-v2.2-patch.md` | v2.2 patch — flow-audit additions |
| `local-setup-guide.md` | Local dev setup (refresh due at P5-S35) |
| `ClaudeSkillsforge_sessiontext.docx` | Conversation transcript — **archive after Phase 5** per H.1 |

---

## Update Protocol

At the end of every slice:
1. Move the just-completed slice into "Recently Completed" (top of list, drop oldest).
2. Update "Last Completed Slice" and "Next Slice".
3. If a feature was fixed: remove from "Known-Broken Features".
4. If a refactor zone is now stable: remove from "Active Refactor Zones".
5. If a new constraint or decision emerged: add to the right section.
6. Commit SESSION-STATE.md alongside the slice's other files.

If you ever feel SESSION-STATE.md is out of sync with reality, run the contingency prompt:
> *"Read SESSION-STATE.md. Run git log --oneline -20 and read the last 5 commit messages and any docs/specs/phase-5/ files added recently. Compare to SESSION-STATE.md. Report drift and propose updates. Do NOT modify the file until I approve."*

---

*Last hand-edit: 2026-04-17 by Dhamo (added v2.2 patch references + flow audit decisions + STRATEGIC-OPTIONS.md reference)*
