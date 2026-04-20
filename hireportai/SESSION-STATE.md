# SESSION STATE — SkillForge

> **Purpose**: This is the live "where we are right now" pointer for Claude Code. Read at the start of every session. Update at the end.
> **Companion to**: AGENTS.md (how project works) + CLAUDE.md (how to behave) + BACKLOG.md (what's queued) + CODE-REALITY.md (what code looks like right now) + spec file (what to build).
> **Update cadence**: End of every implementation slice. Drift will hurt — keep this current.

---

## Session Header

| Field | Value |
|-------|-------|
| **HEAD commit** | `fd4ca3d` (P5-S22b plan-aware Missing Skills CTA; prev `0a161d1` CODE-REALITY regen) |
| **Branch** | `main` |
| **CODE-REALITY.md sha (repo)** | `0a161d1` (regenerated 2026-04-20) — **STALE** (`MissingSkillsPanel.tsx` prop contract changed: `isPro` → `plan` three-state + `scanId`; `Results.tsx` gained `useAuth` + `useSearchParams`. Regenerate before next plan-level prompt.) |
| **CODE-REALITY.md in chat Project** | Stale ❌ — re-upload after next regen |
| **CODE-REALITY stale (either copy)?** | Yes — regenerate before next plan-level prompt |
| **Last hand-edit** | 2026-04-20 — P5-S22b shipped; Missing Skills CTA now plan-aware |

> **Stale-marking rule**: Mark CODE-REALITY stale at the end of any slice that touched routes, models, top-level types, `App.tsx`, or layout components. Regenerate the repo copy AND re-upload to the chat Project before the next plan-level prompt.

---

## Drift flags

> Append-only. When code, specs, docs, and chat-knowledge disagree, log it here. Don't silently reconcile. Resolve in a follow-up commit and close the flag with a one-liner.

| # | Date | Source A | Source B | What disagrees | Resolution / status |
|---|------|----------|----------|----------------|---------------------|
| D-001 | 2026-04-19 | SESSION-STATE.md (stale) | AGENTS.md routes table + git log | AGENTS.md said PersonaPicker shipped in P5-S17; stale SESSION-STATE treated it as upcoming. | ✅ RESOLVED 2026-04-19 — AGENTS.md was authoritative; PersonaPicker shipped in P5-S17 (commit 2c01cc7). SESSION-STATE restored from HEAD (3ad9c90) and forward-patched. |
| D-003 | 2026-04-19 | Chat-Claude prompt | Claude Code pre-flight | Prompt assumed last-good SESSION-STATE was at commit effc980 based on its commit subject. Reality: bad version was uncommitted; HEAD itself was last-good. Following the prompt would have regressed ~10 slices. | ✅ RESOLVED 2026-04-19 — restored from HEAD instead. Lesson: when a working-tree change is uncommitted, "last good" is HEAD, not a prior commit. Future drift-resolution prompts should diff working tree vs HEAD before reaching for git log. |
| D-004 | 2026-04-19 | Session prompts + AGENTS.md (implicit) | Actual git repo layout | Prompts and docs treat `hireportai/` as repo root, but the git repo root is the parent directory. Git-path commands (`git show HEAD:X`) resolve against true root, not CWD. | 🟡 PARTIAL — this instance resolved by using `HEAD:hireportai/SESSION-STATE.md`. Root cause (docs imply repo-root = `hireportai/`) still present. Follow-up tracked as B-013. |
| D-005 | 2026-04-19 | SESSION-STATE.md Locked Decision "Daily review budget + free-tier scope" §1A (locked 2026-04-18) | LD-001 (locked 2026-04-19) | Decision 1A §1A assumed no per-day review counter at all — "Daily Review for free users is unlimited within Foundation. The paywall trigger is non-Foundation category access, not review consumption." Superseded by LD-001 (α): free-tier 15-card budget is consumed by daily review. §1A needs amendment in a future slice (the category-gate half of §1A is still correct and the cap rule §1B is independent). | 🟡 PENDING — §1A marked superseded by this commit's new LD-001 entry; full in-place amendment to §1A deferred to a follow-up doc slice (autonomous SESSION-STATE edits beyond append scoped narrowly per Update Protocol). No code impact — code is silent on α/β. |
| D-006 | 2026-04-19 | BACKLOG.md "Open decisions awaiting Dhamo" row — "Daily review consumes 15-card free budget, or browse-only?" (default: Browse-only) | LD-001 (locked 2026-04-19) | Open-decision row listed (β) browse-only as default. Superseded by LD-001 (α): daily review consumes the 15-card budget. The row needs removal and E-011's Notes need the new spec path. | 🟡 PARTIAL — E-011 Notes column updated in this slice to reference spec #22 and LD-001. Row removal from the "Open decisions awaiting Dhamo" table needs Dhamo (non-status field; outside autonomous edit scope per BACKLOG Rules). |
| D-007 | 2026-04-19 | `../claude-code-prompts-all-phases-v2.2-patch.md` line 282 (planning-era patch doc; frozen per Locked Decision "Phase-5 status is authoritative on disk") | LD-001 (locked 2026-04-19) | Patch doc listed the α vs β question as an open decision. Superseded by LD-001 (α). Doc is frozen chat-Project artifact and is not edited in-repo. | ✅ RESOLVED — supersession recorded on-disk via LD-001 + this flag per Locked Decision "Phase-5 status is authoritative on disk." No follow-up required; frozen-doc drift is expected and bounded. |
| D-008 | 2026-04-20 | Spec `docs/specs/phase-5/50-free-tier-daily-card-wall.md` §Timezone Handling ("or `timezone IS NULL` → default to UTC") | `app/models/email_preference.py:25-27` | `EmailPreference.timezone` is `Mapped[str]` with `nullable=False, default="UTC"`. The "timezone IS NULL" fallback described in the spec is unreachable today; only the "no `EmailPreference` row" branch matters. | ✅ RESOLVED 2026-04-20 — P5-S22-WALL-b impl handles the no-row branch defensively. Minor spec wording discrepancy; leaving spec text as-is (it documents intent accurately; the column constraint is the tighter guarantee). No follow-up. |
| D-009 | 2026-04-20 | Spec `docs/specs/phase-5/50-free-tier-daily-card-wall.md` §UI/UX ("Uses existing date-fns helpers (the codebase already has `date-fns` per `package.json`)") | `hirelens-frontend/package.json` | `date-fns` is **not** in `package.json` (zero imports across `src/`). | ✅ RESOLVED 2026-04-20 — P5-S22-WALL-b impl used native `Intl.DateTimeFormat` + JS math for the `resets_at` formatter instead of adding a new dependency. Spec claim was a planning-era error; no follow-up needed. |
| D-010 | 2026-04-20 | Spec `docs/specs/phase-5/22-plan-aware-missing-skills-cta.md` §Plan Detection (`user.subscription?.plan === "pro"`) | `src/context/AuthContext.tsx` | `AuthUser` has no `subscription` field — plan state lives in `UsageContext` (`{plan: 'free'\|'pro'}`, localStorage-backed), not on `user`. Spec §69 explicitly delegates the exact helper choice to the impl audit, so not a hard conflict. | ✅ RESOLVED 2026-04-20 — P5-S22b derived the three-state plan from the live hooks: `user === null` (from `useAuth`) → `'anonymous'`, `canUsePro === true` (from `useUsage`) → `'pro'`, else `'free'`. `enterprise` is treated as `'pro'` (same "unwalled" semantic); `UsageContext.PlanType` does not model enterprise today. Worth aligning later: when the frontend gains a real `user.subscription` field (e.g., from the auth payload), collapse the two sources into a single helper. Not blocking. |

---

## Active Phase

**Phase 5: Enhancements + UX Restructure**

Phases 0–4 are complete. Phase 5 absorbs the ad-hoc enhancement work plus the UX restructure (PersonaPicker, /learn and /prep namespaces, persona-aware home dashboard) plus the v2.2 patch additions from the user-flow audit.

---

## Active Prompt Files

- `claude-code-prompts-all-phases-v2.md` (v2.1) — base of Phase 5
- `claude-code-prompts-all-phases-v2.2-patch.md` — additions from flow audit (5 new slices + 1 spec amendment)
- Always read both when planning Phase 5 work.
- **On-disk status doc (`docs/PHASE-5-STATUS.md`) is authoritative** when it disagrees with either prompt file — see Locked Decisions.

---

## Last Completed Slice

**P5-S22b — Plan-aware Missing Skills CTA (closes spec #22 / E-011).** Three-state CTA on `/prep/results` Missing Skills section per spec §Copy — anonymous / free / pro. `src/components/dashboard/MissingSkillsPanel.tsx` rewritten: dropped `isPro?: boolean` + `onUpgradeClick?: () => void` prop contract in favor of `plan: 'anonymous' | 'free' | 'pro'` + `scanId?: string | null`; exported `MissingSkillsPlan` type for the Results consumer. CTA copy locked to exact strings (spec §Copy — matchers assert verbatim): anonymous `"Sign in to study"` + `LogIn` icon → `/login?return_to=<URL-encoded>`; free `"Study these cards — free preview"` + `BookOpen` icon → `/learn?category=<id>`; pro `"Study these cards"` + `BookOpen` icon → same URL. Aria-labels differ per plan per spec. Disabled state (spec §Edge Cases) for skills with no matching category: renders a disabled button with `title="No matching study content yet"` tooltip via the native HTML attribute (lightweight; `PanelSection` tooltip primitive was considered but was overkill for a single string). AC-4 category-resolution reuses the existing `gapCategoryMap` Map-build pattern (lowercase-keyed lookup filtering `match_type !== 'none'`). AC-8 `return_to` built by URL-encoding `/prep/results?scan_id=<id>` (or `/prep/results` when scan_id absent) — scan_id read from **URL** via `useSearchParams`, not from `result.scan_id`, per spec §AC-8. `Results.tsx` consumer gained `useAuth()` + `useSearchParams()` imports; three-state plan derived inline as `user === null ? 'anonymous' : canUsePro ? 'pro' : 'free'` and passed as `plan` prop. `onUpgradeClick` for other Results paywall surfaces is **untouched** (spec §32 "Upgrade-modal firing from other Results surfaces is untouched"); `showPaywall` / `setShowPaywall` / `<PaywallModal>` at line 431 stays. The `onUpgradeClick` prop is retained on `MissingSkillsPanel` for back-compat (voided via `void _onUpgradeClick`) but no longer invoked. **Analytics:** new `missing_skills_cta_clicked` (`{plan, skill, category_id}`) fires on click; disabled buttons don't fire (native HTML). Legacy `gap_study_clicked` deprecated per P5-S17 precedent — moved to `.agent/skills/analytics.md` "Deprecated Frontend Events" subsection with a commit-SHA marker. **Tests FE 147 → 161 (+14):** all 14 spec §Test Plan rows covered in `tests/components/MissingSkillsPanel.cta.test.tsx`. Two pre-existing Results-page test files (`Results.ordering.test.tsx`, `Results.tooltips.test.tsx`) gained a `vi.mock('@/context/AuthContext', ...)` stub because Results.tsx now calls `useAuth()`; the mocks mirror the `vi.mock('@/context/UsageContext', ...)` shape already present in those files. `tsc --noEmit` clean. BE **265 unchanged**. **Drift flag D-010 logged:** spec §Plan Detection assumed `user.subscription?.plan` but `AuthUser` has no `subscription` field — plan lives in `UsageContext`; composed live hooks as above (spec §69 explicitly delegated the exact helper choice). **BACKLOG:** E-011 🔴 → ✅. **PHASE-5-STATUS:** new P5-S22b row ✅ SHIPPED. **Unblocks P5-S26b:** the full anonymous→free→wall→paywall routing chain is now end-to-end testable — paywall dismissal can be specced against a real flow.

**P5-S22-WALL-b — Free-tier daily-card review wall (closes spec #50 / E-030; enforces LD-001 in code).** Delivered the implementation contract for LD-001 (α). New backend helper `app/utils/timezone.py::get_user_timezone(user_id, db) -> ZoneInfo` resolves IANA tz from `EmailPreference.timezone`; falls back to UTC on no-row or `ZoneInfoNotFoundError` with a warning log. New `study_service.DailyReviewLimitError(payload)` exception carries the AC-2 402 JSON body on `.payload`. New private `study_service._check_daily_wall(user, db)`: early-exits on `user.role == "admin"` (AC-9) and on non-free plans (§Counter Scope Option 2; no Redis IO for Pros/Enterprise); otherwise computes user-local date via `get_user_timezone`, `INCR`s `daily_cards:{user_id}:{YYYY-MM-DD}`, sets a 48h TTL on first write, raises `DailyReviewLimitError` when post-INCR > 15, else emits `daily_card_submit` with `count_after`. Fail-open on Redis outage: warning log + `daily_card_submit` with `counter_unavailable=true`, review proceeds. Wired into `review_card` **after** the existing `CardForbiddenError` plan-gate and **before** any FSRS / `card_progress` mutation, matching spec §Solution exactly. `review_card` signature gains optional `user: User | None = None` — backward-compat for the 10 direct callers in `test_study_service.py` that pass positional/keyword args without a User (wall silently skipped when `user is None`); the route always forwards `user`. Route `app/api/v1/routes/study.py::submit_review` adds a 402 branch after the existing 403 branch (order of 404→403→402 preserved). **Module-level `_utcnow()` seam** added for time-mocking in tests (no `freezegun` dep). **Module-level `_get_redis()`** copies the `home_state_service` / `geo_pricing_service` pattern byte-for-byte (no new pattern). **Frontend:** `QuizPanel.tsx` (single submit chokepoint used by DailyReview, CardViewer, MissionMode) catches AxiosError 402 with `detail.trigger === 'daily_review'`, sets `wall` state, re-opens `PaywallModal` with `trigger="daily_review"` (existing scaffold; zero modal-component changes). A local `formatResetsAt(iso)` helper renders relative ("Resets in 4h 17m") for ≤12h, absolute ("Resets at 12:00 AM") otherwise; **no `date-fns` dep was added** (spec claimed it was in `package.json` — it is not; used native `Intl.DateTimeFormat` + JS math). `daily_card_wall_hit` fires once on modal open via `useEffect` idempotency (matches the existing `paywall_hit` open-re-fire semantic in `PaywallModal.tsx:78`); props `{resets_at_hours_from_now}` rounded toward zero via `Math.trunc`. Walled submit leaves FSRS state client-side untouched (mirrors backend). **Tests:** BE 254 → 265 (+11, all 11 from spec §Test Plan in `tests/test_wall.py`); FE 142 → 147 (+5, in `tests/components/QuizPanel.wall.test.tsx`). BE-8 concurrency test exercises `_check_daily_wall` directly (AsyncSession can't be shared across `asyncio.gather`'d coroutines — `InterfaceError: cannot use Connection.transaction()` — so we isolate the Redis-atomicity invariant the spec actually names). Full BE suite green; `tsc --noEmit` clean. **Docs:** `.agent/skills/analytics.md` catalog gained `daily_card_submit` (backend) and `daily_card_wall_hit` (frontend) per the P5-S21b convention. `.agent/skills/payments.md:78` was **already** amended in `d235a50` — no edit in this commit (Step 5.1 was a no-op after audit). `.agent/skills/gamification.md:14` (streak vs wall midnight mismatch) untouched — out of scope per spec. `.agent/skills/study-engine.md:32` (`LIMIT 5`) untouched — no orthogonal-file edits bundled. **BACKLOG:** E-030 🔴 → ✅. **PHASE-5-STATUS:** new P5-S22-WALL row ✅ SHIPPED. **Unblocks:** P5-S22b (Missing Skills CTA "free preview" semantics now have a real wall) and P5-S26b (paywall dismissal now has a real paywall to dismiss). **Drift flags discovered during audit:** (i) spec §Timezone Handling says "`timezone IS NULL` → default to UTC" — column is actually `NOT NULL` with `default="UTC"`, only the "no row" branch is reachable; (ii) spec claimed `date-fns` is a dep — it isn't. Both minor; implementation handles them.

**P5-S20 — Move Job Fit Explanation above the fold on `/prep/results` (closes E-009).** Flattened the 3-panel grid in `src/pages/Results.tsx` to 11 direct grid children so DOM order IS the mobile + tab order (was: left-sidebar panel → main panel → right panel, which pushed Job Fit to DOM position 5 on mobile behind ATS + Score Breakdown + Nav + 3 CTA buttons). New DOM order matches spec target: ATS Score → Job Fit (HERO) → Missing Skills → Keywords → Score Breakdown → Skills Radar → Bullets → Formatting → Improvements → Nav → CTAs. Desktop layout preserved via explicit `lg:col-start-* lg:row-start-*` + `xl:col-start-* xl:col-span-*` + `lg:col-span-2` (LG-breakpoint fallback so right-panel items span both cols when the 3-col grid collapses to 2). All 9 section IDs (`ats-score`, `score-breakdown`, `job-fit`, `keywords`, `skills`, `bullets`, `missing-skills`, `formatting`, `improvements`) preserved — `results_tooltip_opened` 9-value enum stable. All 9 PanelSection tooltips (spec #21 copy) preserved verbatim. `lg:sticky lg:top-20` now attaches to the ATS-score grid item (was the left-sidebar wrapper); `xl:sticky xl:top-20` now attaches to the Missing-Skills grid item (was the right-panel wrapper). **New analytics event:** `job_fit_explanation_viewed` fires once per mount (useRef idempotency guard matching `home_dashboard_viewed` / `first_action_viewed` convention) with `{view_position: 'above_fold'}` — `view_position` fixed at "above_fold" after this slice, leaves headroom for scroll-triggered or below-fold variants without a new event name. Catalogued in `.agent/skills/analytics.md`. **Tests (134 → 142, +8):** `tests/pages/Results.ordering.test.tsx` asserts DOM order via `compareDocumentPosition` for ATS<JobFit<MissingSkills<Keywords<ScoreBreakdown, section-id stability, mount-fire of `job_fit_explanation_viewed`, and idempotency across mount→unmount→mount. tsc clean. BE untouched. **BACKLOG:** E-009 🔴 → ✅. R15 observed. No CODE-REALITY regen script exists on disk; CODE-REALITY still stale at sha `f09be80` — log hygiene unchanged by this slice, regenerate before next plan-level prompt.

---

## Previously Completed

**P5-S21b — Analysis Results: keyword color fix + education tooltips (closes B-004 and E-010 info-icon half).** Implemented spec #21 (`fe4a333`). **KeywordChart:** introduced `KEYWORD_LEGEND` constant (3 entries with `{id, label, cssVarName, alpha}`) and `rgbaFromCssVar(varName, alpha)` helper — both exported — as the single source of truth for chart Cell fills AND legend swatches. Replaced hardcoded violet `rgba(124,58,237,0.5)` with `rgbaFromCssVar('--color-accent-secondary', 0.5)`; now theme-correct across Dark / Light / Midnight Blue. Spec Option A applied (legend adopts chart opacities): matched α=1.0, missing α=0.25, in-resume α=0.5. **PanelSection:** extracted from inline `Results.tsx:37-66` to `src/components/dashboard/PanelSection.tsx`. Prop signature changed: `tooltip?: string` → `tooltip?: {what: string; how: string; why: string}` + new `section?: ResultsSectionId` for analytics. Hardened with: Escape-dismiss (focus returns to trigger), click-outside via new `useClickOutside` hook (`src/hooks/useClickOutside.ts` — `mousedown` + `touchstart`), `role="tooltip"`, `aria-describedby`, `aria-expanded`, stable `useId()` tooltip id. **Results.tsx:** Score Breakdown refactored from raw `AnimatedCard` to `PanelSection`. Tooltips added on the 5 previously-uncovered sections (score_breakdown, skills_radar, bullets, formatting, improvements) with drafted what/how/why copy verbatim from spec §Education Layer Design. Section-id anchors added: `ats-score`, `score-breakdown`, `missing-skills`, `formatting`, `improvements` (join existing `job-fit`, `keywords`, `skills`, `bullets`). Legend now driven from `KEYWORD_LEGEND.map()` with `data-testid="legend-swatch-<id>"` markers; hidden when `keyword_chart_data` is empty. **Analytics:** new event `results_tooltip_opened` (`{section: 9-value enum}`) catalogued in `.agent/skills/analytics.md`; fires on open only, guarded on `section` prop being set (non-Results callers of `PanelSection` don't emit). **Tests (114 → 134, +20):** `tests/components/KeywordChart.colors.test.tsx` (9 tests — AC-1/AC-2: legend entries map to expected CSS vars, `rgbaFromCssVar` produces correct rgba in all 3 themes, rendered DOM contains no `124,58,237` substring, empty-data guard), `tests/components/PanelSection.tooltip.test.tsx` (10 tests — AC-3/4/5/7: icon renders, Enter/Space/click open, Escape closes + focus returns, click-outside closes, `role="tooltip"` + `aria-describedby` + `aria-expanded` linkage, analytics fires on open with section id, does not fire on close, does not fire without section prop), `tests/pages/Results.tooltips.test.tsx` (1 test — AC-3: all 9 section headers render exactly one `Info` trigger each). `tsc --noEmit` clean. BE untouched (248 unit + 6 integration). Test-setup side-effect: added ResizeObserver shim in `src/test/setup.ts` for Recharts `ResponsiveContainer` (JSDOM lacks it). **BACKLOG:** B-004 🔴 → ✅, E-010 🔴 → ✅ (info-icon layer; guided-tour half deferred per spec §Out of Scope, added to Deferred Hygiene Items). Spec #21 status Draft → Done. CODE-REALITY.md marked stale (sha `f09be80`, HEAD moved — regen before next plan-level prompt).

**5.17b — Interview Question Storage frontend wiring (closes spec #49 end-to-end).** Wired the cache-aware backend from `a2a79d5` into the Interview Prep page. `services/api.ts::generateInterviewPrep(resume, jd, options?)` now accepts an optional `{forceRegenerate}` and only sends `force_regenerate: true` when set (omits the field on the no-cache path so the BE default holds). `InterviewPrepResponse` gained optional `cached`/`generated_at`/`model_used` fields (additive, structural typing on the existing surface kept unchanged). `useInterview.runInterviewPrep(resume, jd, options?)` passes the flag through. `pages/Interview.tsx`: header CTA stays "Generate Interview Questions" on the cold path; once a result is in state, the bottom CTA reads "Regenerate Questions" and routes through `handleRegenerate` which (a) for free tier shows a `window.confirm("This will use 1 of <N> free generations. Continue?")` (uses `limitInfo.remaining` when populated by a prior 403, else generic copy — no extra `/api/v1/usage` round-trip per Rule 2) and (b) calls `runInterviewPrep(..., {forceRegenerate: true})`. Status row above the question list shows a `data-testid="cached-chip"` "Cached — generated <relative>" pill when `cached === true`, and a `data-testid="free-usage-chip"` "Used 1 of your monthly free generations" pill when `cached === false && plan === 'free'` (AC-5a: chips are mutually exclusive, free-usage chip is hidden on cache hits because cache hits don't decrement the counter). Two new PostHog events: `interview_questions_cached_served` (`{jd_hash_prefix, generated_at_age_hours}` — `jd_hash_prefix` derived client-side via `crypto.subtle.digest` SHA-256 over the same normalize-whitespace+casefold the backend uses, first 8 hex chars only so the JD itself never leaves the user's browser; deduped by `generated_at` via `useRef`) and `interview_questions_regenerated` (`{from_free_tier, remaining_free_quota?}`). New helper `src/utils/jdHash.ts` ships the browser-side `normalizeJd` + `jdHashPrefix` mirror of `app/utils/text_hash.py`. Tests in `tests/Interview.test.tsx` (3 new): cached chip renders + free-usage chip suppressed on `cached:true`; free-usage chip renders on `cached:false` free-tier; Regenerate confirm() → `forceRegenerate:true` reaches the api-layer call (call[0] no options, call[1] `{forceRegenerate:true}`) + `interview_questions_regenerated` fires with `from_free_tier:true`. FE **111 → 114** (+3). BE unchanged at **248 unit + 6 integration deselected** (no backend touched). `tsc --noEmit` clean. Bundled audit findings: **DEFER-A (tracker `jd_hash` dedupe) classified ASPIRATIONAL** — `tracker_service_v2.py` has zero hash logic and `tracker_applications_v2` has no `jd_hash` column; the analyze route uses `find_by_scan_id` for idempotency on `scan_id`, not JD content. Locked Decision "Auto-save scan to tracker" updated to flag dedupe as not-yet-implemented; new follow item `[5.17-follow] tracker jd_hash dedupe` added. **DEFER-B (`/api/interview-prep` /v1 prefix) classified LARGER-CLEANUP** — there are 4 flat legacy `/api/*` routes in `app/main.py:120-123` (`analyze`, `rewrite`, `cover_letter`, `interview`), not a single outlier. S45-pattern cleanup territory; new follow item `[5.17-follow] flat /api/* legacy-route cleanup` added; no route changes in this slice. PHASE-5-STATUS row 5.17 flipped 🟡 PARTIAL → ✅ SHIPPED.

**P5-S18** — HomeDashboard + widget catalog. Replaced `HomeDashboardPlaceholder` with a real `src/pages/HomeDashboard.tsx` that branches on `user.persona` into three render modes with `data-testid="home-mode-<persona>"` markers. Implemented the `DashboardWidget` primitive (`src/components/home/DashboardWidget.tsx`) with the spec #35 §Solution contract (`loading` → `SkeletonCard`, `data` → children + optional footer action, `empty` → `emptyMessage`, `error` → `errorMessage` + `Try again` retry). Seven widgets under `src/components/home/widgets/`: `TodaysReviewWidget` (fetchDailyQueue → total_due), `StreakWidget` (useGamification → current_streak/longest_streak), `WeeklyProgressWidget` (wraps `ActivityHeatmap`, empty-gate on `total_xp === 0 && longest_streak === 0`), `LastScanWidget` (derives from `getApplications()` desc by created_at), `InterviewTargetWidget` (AuthContext company+date, display-only — no Edit action per Resolved Decision #6), `CountdownWidget` (Mode 1 inline `<input type="date">` → `updatePersona({persona, interview_target_date})`; Mode 2 wraps `mission/Countdown` + active-mission CTA via `fetchActiveMission()` — `"Start a Mission sprint"` or `"View mission"`), `TeamComingSoonWidget` (static copy, action-less — no waitlist component found on disk). Grid `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`. Greeting `Welcome back, <first name>.` with `Welcome back.` fallback on empty name. `home_dashboard_viewed` capture with `useRef` idempotency guard (AC-7), `{persona}` property. `App.tsx` swap: import + route element `HomeDashboardPlaceholder → HomeDashboard`; `tests/App.redirects.test.tsx` updated to stub new path. `HomeDashboardPlaceholder.tsx` deleted. Analytics catalog row added. AGENTS.md `/home` row updated. FE tests **38 → 78** (+40): 6 `DashboardWidget.test.tsx`, 9 `HomeDashboard.test.tsx`, 25 across seven `widgets/*.test.tsx`. AC-9 regression-catch asserted: `CountdownWidget` Mode 1 submit calls `updatePersona` with `{persona: 'interview_prepper', interview_target_date: '...'}`. BE unchanged at **184 unit + 6 integration deselected**. tsc clean, `npm run build` succeeds.

**P5-S17** — Frontend PersonaPicker page + PersonaGate + AppShell hide-list + legacy cleanup. New full-page picker at `/onboarding/persona` (`src/pages/PersonaPicker.tsx`) renders 3 cards using PRD §1.3 copy (Interview-Prepper, Career-Climber, Team Lead); Interview-Prepper card expands with optional `<input type="date">` and a `maxLength={100}` company input (live counter). Continue calls `updatePersona()` → `PATCH /api/v1/users/me/persona`, merges the response into AuthContext via `updateUser`, then `navigate('/home', { replace: true })`. Inline error on API failure, selection preserved. Fires `persona_picker_shown` on mount and `persona_selected` after 2xx (both new, added to `.agent/skills/analytics.md`). New `src/components/PersonaGate.tsx` wraps the protected subtree inside `ProtectedRoute` — redirects `user.persona === null` to `/onboarding/persona` on every protected path except `/`, `/login`, `/onboarding/persona`. `AppShell.CHROMELESS_PATHS` now includes `/onboarding/persona` so TopNav/MobileNav hide there. `AuthUser.persona` narrowed to `Persona = 'interview_prepper' | 'career_climber' | 'team_lead'`; legacy `target_company?`/`target_date?` fields dropped. `services/api.ts` `completeOnboarding` + legacy `updatePersona` (+ their request types) deleted; new `updatePersona(body): Promise<AuthUser>` targets the new endpoint. `StudyDashboard` `PERSONA_CONFIG` rekeyed to snake_case, literal comparisons updated (`'interview_prepper' | 'career_climber' | 'team_lead'`), field reads renamed to `user.interview_target_*`; settings-modal launchers ("Change goal" button + "Set your goal →" button) + `showPersonaPicker` state + legacy import all removed. `LoginPage` doc comment refreshed. Legacy `src/components/onboarding/PersonaPicker.tsx` deleted; `components/onboarding/` kept (holds `GuidedTour.tsx`). Existing test fixtures (`TopNav.test.tsx`, `MobileNav.test.tsx`, `App.redirects.test.tsx`) updated — dropped legacy fields, `'climber' → 'career_climber'`, and `App.redirects.test.tsx` now stubs `@/pages/PersonaPicker` instead of the deleted path. Analytics catalog: `persona_picker_shown` + `persona_selected` added to the active table; the two legacy events (`persona_changed`, `onboarding_persona_selected`) preserved in a new `#### Deprecated Frontend Events` subsection with commit-b5f42c2 markers so historical PostHog data + the Phase-4 dashboards spec stay cross-referenced (post-amend). AGENTS.md Frontend Routes table gained a `/onboarding/persona` row and the nav-chrome-hides sentence now lists the new path. Test counts: FE **38/38** (27 → 38: +6 PersonaPicker, +3 PersonaGate, +2 AppShell); BE unchanged at **184 unit + 6 integration deselected**. TypeScript clean, `npm run build` succeeds.

**Shipped:** P5-S17 committed as `2c01cc7` (amend of `b5f42c2`) pushed to `origin/main` at 2026-04-18 19:49 UTC. Auto-deploys to Vercel (frontend) + Railway (backend — no-op this slice) per CLAUDE.md §Rule 9. Resolves the known S16-leftover runtime breakage on `/learn` (`PERSONA_CONFIG[user.persona]` returning `undefined` for snake_case persona values).

---

## Next Slice

**P5-S26b** — Paywall dismissal + win-back (BACKLOG E-014, spec `docs/specs/phase-5/42-paywall-dismissal.md`). Now fully unblocked: the anonymous→free→wall→paywall chain is end-to-end routable after P5-S22-WALL-b (wall shipped `d155dcb`) + P5-S22b (free-preview CTA shipped this slice). Dismissal analytics can be specced against a real user flow — re-prompt cadence, 3rd-dismissal win-back email hook.

After P5-S26b, continue per `docs/PHASE-5-STATUS.md` genuinely-pending list (5.24 chat-with-AI, 5.25 admin insights, 5.26 admin content-feed) — the v2.1 P5E/P5F work is done. Also: **CODE-REALITY.md stale** (last regen at `0a161d1`, HEAD now past it) — regenerate before the next plan-level prompt.

P5E chunk: P5-S22 is the last remaining item (P5-S20/S21 closed; B-004 + E-010 info-icon half closed in P5-S21b).

After P5E, continue per execution order in `claude-code-prompts-all-phases-v2.md` reconciled against `docs/PHASE-5-STATUS.md`:

1. P5E — P5-S22 only (P5-S20, P5-S21 closed)
2. P5F (S23–S26, **S26b**, **S26c**) — Interview storage polish + cancel sub + paywall dismissal + webhook idempotency
3. P5G (S27–S30) — Settings + chat AI + interview date
4. P5H (S31–S34) — Admin insights + content feed
5. P5-FINAL (S35) — verify + housekeeping

**Bold = added in v2.2 patch.** P5-S9/S10/S11/S12/S13/S14/S16/S17/S18/S18b/S18c/S20/S21 all shipped.

---

## Known-Broken Features (DO NOT modify unless fixing)

User-visible bugs with dedicated fix slices. Cross-reference: BACKLOG.md.

| Feature | Symptom | Fix slice | Backlog ID |
|---------|---------|-----------|------------|
| Geo-Pricing Visibility | Audit complete (P5-S8): A+C fixed. Remaining deferred gaps — B: no price on LoginPage; D: ip-api.com rate-limit fallback mis-prices Indian users under load; E: Free-plan shows `$0` even for INR users. | Deferred (post-P5B) | E-020 |

---

## Active Refactor Zones (avoid drive-by changes)

- (P5-S13 landed): `src/App.tsx` carries the nine `/learn/*` + `/prep/*` namespaced routes and a ten-entry transitional redirect block. The redirect block is P5-S13's domain — do not edit it as part of unrelated work.
- (P5-S14 landed): `src/components/layout/TopNav.tsx`, `MobileNav.tsx`, `AppShell.tsx` are the nav source of truth. The legacy `src/components/layout/Navbar.tsx` is no longer imported by `App.tsx` but still sits on disk — delete it when we're sure no other callers exist (Phase 6 cleanup candidate; tracked as B-010).
- (P5-S17 landed): `src/pages/PersonaPicker.tsx` and `src/components/PersonaGate.tsx` are the persona onboarding surface. The picker ships without a "change persona" affordance by design (spec #34 Out of Scope) — do not add one here; the switch UX is a post-spec follow-up (see Deferred Hygiene Items).

---

## Recently Completed (last 5)

1. 2026-04-20 — P5-S22b shipped. Plan-aware Missing Skills CTA on `/prep/results` (spec #22, closes E-011). `MissingSkillsPanel.tsx` prop `isPro` → `plan: 'anonymous'|'free'|'pro'`; new `scanId` prop for anonymous `return_to` building. Copy + aria + icon per plan; disabled state for unmatched skills. `Results.tsx` derives plan via `useAuth + useUsage` and reads `scan_id` from `useSearchParams`. New `missing_skills_cta_clicked` event; `gap_study_clicked` deprecated. FE 147 → 161 (+14). BE unchanged. Commit `fd4ca3d`.
2. 2026-04-20 — CODE-REALITY.md regenerated to match HEAD `2312cc9` (targeted updates to Section 1 metadata, Section 3 /admin/ping + study/review 402 annotation, Section 4 DailyReviewLimitError, Section 6 wall-aware QuizPanel note, Section 7 Results.tsx events). Superseded by the next regen — P5-S22b touched MissingSkillsPanel.tsx prop contract + Results.tsx hooks.
3. P5-S22-WALL-b — Free-tier daily-card review wall (spec #50, closes E-030). `_check_daily_wall` in `study_service.py` + `app/utils/timezone.py::get_user_timezone`; 402 branch on `POST /api/v1/study/review`; `QuizPanel.tsx` wires the modal. Tests BE 254 → 265, FE 142 → 147. Commit `d155dcb`.
4. P5-S20 — Moved Job Fit Explanation above the fold on `/prep/results`. Flattened the 3-panel grid to 11 direct grid children so DOM order = mobile order = tab order. New order: ATS → Job Fit → Missing Skills → Keywords → Score Breakdown → Skills Radar → Bullets → Formatting → Improvements → Nav → CTAs. New PostHog event `job_fit_explanation_viewed`. Tests 134 → 142 (+8). BACKLOG E-009 ✅.
5. P5-S21b — Keyword color fix + education tooltips. `KEYWORD_LEGEND` + `rgbaFromCssVar` helper replace hardcoded violet with theme-aware rgba across 3 themes. `PanelSection` primitive extracted; hardened with Escape-dismiss + click-outside + `role="tooltip"` + `aria-describedby` + `aria-expanded`. Tooltips on 5 previously-uncovered sections + Score Breakdown refactor. New `results_tooltip_opened` event (9-value section enum). Tests 114 → 134 (+20). BACKLOG B-004 + E-010 info-icon half closed.

---

## Open Decisions Awaiting Dhamo

Canonical list lives in **`BACKLOG.md` → "Open decisions awaiting Dhamo"**. Items below are session-scoped; anything blocking a Phase 5 slice should also exist in BACKLOG.md.

| Decision | Context | Blocking? | Decide by |
|----------|---------|-----------|-----------|
| Free-tier interview question limit value | Implemented but value not validated against business model. P5-S6 will flag the current value for confirmation. | No | End of Phase 5 |
| Cancellation win-back flow (50% off 3 months) | Mentioned in P5-S26 spec as optional. | No | Before P5-S26 |
| **Strategic path to $100M ARR**: B2B pivot, adjacent expansion, or geo-volume play? | See `STRATEGIC-OPTIONS.md`. Affects every Phase 6+ decision. | Not yet | Before Phase 6 planning |

---

## Locked Decisions

### LD-001 — Free-tier daily-review budget: CONSUMES (α)
**Locked:** 2026-04-19
**Affected slices:** P5-S22 (this spec — plan-aware Missing Skills CTA), any future paywall trigger around daily review, free-tier budget counter's event hooks, future amendment to Decision 1A below.

**Rule.** Free users get **15 card reviews per day**. The budget is consumed by the daily review flow, not browse-only. Counter resets at the user's local midnight (timezone from existing `EmailPreference.timezone`; defaults to UTC if unset). Three days of active daily use at 5 reviews/day is a *typical* entry path to the paywall, not the definition of the budget. The budget is per-day, not lifetime.

**Rationale.**
(a) Daily review is the core retention mechanic; giving it away free forever inverts value capture.
(b) Senior-engineer target demographic is high-intent; a 3-day free window is enough to validate.
(c) Keeps gating coherent with Mission Mode being Pro-only.

**Rejected alternative (β):** browse-only budget, daily review unlimited free — too generous, conversion-hostile.

**Supersedes.** Any planning-era doc that assumed (β), including:
- `../claude-code-prompts-all-phases-v2.2-patch.md` line 282 (planning-era open decision).
- BACKLOG.md "Open decisions awaiting Dhamo" row whose default answer was "Browse-only (more generous)."
- The §1A half of the 2026-04-18 Locked Decision "Daily review budget + free-tier scope" below, whose "no per-day review counter" rule contradicts α. (§1B's hard 20-card/day cap is independent and still stands; §1A's Foundation-category gating is also still correct. Only the "no counter / review consumption never triggers a paywall" part is superseded.)

Drift flags D-005, D-006, D-007 log the supersessions.

**Cross-check (audit 2026-04-19, in this slice's Step 2):** code is SILENT on α vs β — neither is implemented. `app/services/usage_service.py` has no `card_view` / `daily_review` entry in `PLAN_LIMITS`; `app/services/study_service.py::get_daily_review` gates free users on `Category.source == "foundation"` only and increments no card counter on review submit; `hirelens-frontend/src/components/PaywallModal.tsx` defines a `daily_review` trigger in its union type but nothing in `src/` passes `trigger="daily_review"` — dead dispatch. Frontend `MissingSkillsPanel.tsx` currently branches Pro-vs-free as (navigate) vs (onUpgradeClick) with no routing for free users. LD-001 is a docs-level decision in this slice; the code-level counter (and any paywall re-wiring) is a future implementation slice.

**Amended 2026-04-19 (P5-S22-WALL-a-FOLLOWUP, 8de4ee5):** Clarified the lifetime/daily ambiguity surfaced by P5-S22-WALL-a's audit (the original "5 cards/day × 3 = 15" parenthetical read as a lifetime total). Budget is per-day with user-local-midnight reset. Also confirmed: wall response code is HTTP 402 (not 403 per existing interview-prep pattern — 403→402 migration of that path is out of scope; tracked as future hygiene).

---

### Decision: Daily review budget + free-tier scope
**Locked:** 2026-04-18
**Affected slices:** P5-S22 (FSRS Pro-gating), Phase 1 paywall logic (retroactive doc)

**Amendment note (2026-04-19, LD-001):** §1A's "no per-day review counter… paywall trigger is non-Foundation category access, not review consumption" is **superseded by LD-001 (α)**. §1B (hard 20-card/day cap) and §1A's Foundation-category scoping rule are unaffected. See Drift flag D-005.

**1A — Free tier scope: CATEGORY-GATED (status quo).**
Free users are scoped to the Foundation category. No per-day review counter. No per-session counter. Daily Review for free users is unlimited within Foundation. The paywall trigger is non-Foundation category access, not review consumption.

Rationale: Career-Climber's conversion lever is breadth (full library access), not friction on the daily habit. Adding a per-day review counter would punish the most retentive persona and undermine the retention engine the product is built around. Category-based gating is already in the codebase (verified Step 2) and is the right default.

Implication for P5-S26b (paywall dismissal): the dismissal flow applies to category-access paywalls, not review-consumption paywalls (which don't exist).

**1B — FSRS daily-cap: HARD CAP at 20 cards/day, all plans.**
The Daily Review query (`get_daily_review`) returns at most 20 cards/day, all plans, free or Pro. Applies to:
- Daily Review queue (`/learn/daily`)
- Auto-injection of new cards (state=new)

Ordering inside the cap: due-review cards (state=review/learning/relearning) placed first, ordered by due_date ASC. New cards (state=new) fill remaining slots up to 20.

Mission Mode is exempt: the mission's daily_target wins inside `/learn/mission`. Mission cards are scoped to the mission's selected categories and don't double-count against the Daily Review cap on the same day.

Rationale: 20 cards × ~45 sec ≈ 15-min session = sweet spot for daily habit formation. Above this, FSRS death spiral risk (user opens app, sees 47 due, closes app, breaks streak). 20 is conservative headroom above the "Daily 5" brand framing.

Catch-up mode (offer to review backlog beyond 20) is deferred to a Phase 6 slice once we have data on overflow frequency.

**Implementation note for P5-S22:**
- Update `get_daily_review(user_id)` to apply `LIMIT 20` after ordering.
- Add unit test `test_daily_review_caps_at_20_when_overdue` (seed 30 due cards, assert response length == 20, assert oldest due_date returned first).
- Add unit test `test_daily_review_prefers_due_over_new` (seed 15 due + 10 new, assert response is 15 due + 5 new in that order).
- Update `study-engine.md` skill: change "Daily 5 = ... LIMIT 5" line to reflect 20-cap.

---

### Decision: Phase-5 status is authoritative on disk
**Locked:** 2026-04-19
**Affected slices:** every future slice that ships, closes, or obsoletes a v2.1 or v2.2-patch item

**Rule:** `docs/PHASE-5-STATUS.md` is the on-disk source of truth for v2.1 / v2.2-patch / post-playbook Phase-5 status. Chat-side artifacts (`claude-code-prompts-all-phases-v2.md`, `claude-code-prompts-all-phases-v2.2-patch.md`, `skillforge_playbook_v2.md` status table) are frozen snapshots — when they disagree with the status doc, trust the status doc.

Update protocol: at the end of any slice that ships, closes, or obsoletes a listed item, update the corresponding row in `docs/PHASE-5-STATUS.md` (status marker + evidence + commit SHA) in the same commit as the code change. Do not let status and code diverge across commits.

Rationale: chat-Claude's project knowledge drifts; the v2.1 table had at least eight items marked 🔴 PENDING that were already shipped on disk. The 2026-04-19 reconciliation (this decision) produced the status doc and closed v2.1 item 5.9 (doc audit + sync). Pattern documented in `docs/specs/phase-5/48-doc-audit-pattern.md` — run again every 5–10 slices or when chat-Claude's priority calls feel wrong.

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

**Status (audited 2026-04-19, slice 5.17b):** the dedupe half of this decision is **NOT YET IMPLEMENTED**. The shared util `app/utils/text_hash.py::hash_jd` now exists (created by spec #49 / `a2a79d5`), but `tracker_service_v2.py` does not call it; `tracker_applications_v2` has no `jd_hash` column; the analyze auto-create path (`app/api/routes/analyze.py:206-220`) uses `find_by_scan_id` for `scan_id`-based idempotency only. The "auto-save when JD provided" half also needs verification — no `tracker_autosaved` event exists yet. Migrating tracker to consume `hash_jd` + adding the unique constraint is tracked as `[5.17-follow] tracker jd_hash dedupe` in Deferred Hygiene Items and needs its own spec before implementation per Rule 14.

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

**Affected slices:** P5-S15 (spec describes full-page UX), P5-S17 (PersonaGate implemented as redirect, not overlay), P5-S19 (existing-user banner sits at top of page — later obsoleted).

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

- **2026-04-19 — LD-001 amendment + payments.md fix (follow-up to 8de4ee5).** Resolved the lifetime-vs-daily ambiguity surfaced by P5-S22-WALL-a's audit. LD-001 now locks per-day budget with user-local-midnight reset. `.agent/skills/payments.md` "15 lifetime" → "15 per day with reset" per spec #50. Wall response code confirmed as 402; 403→402 migration of interview-prep path tracked as future hygiene (not in scope for P5-S22-WALL-b). No code changes. Unblocks P5-S22-WALL-b implementation slice.
- **2026-04-19 — P5-S22-WALL-a spec authored (spec #50, BACKLOG E-030).** Addresses the disk gap surfaced by P5-S22a's drift audit (D-005 / D-006 / D-007): LD-001 locked "daily review consumes the 15-card/day budget" but no code enforces it — `usage_service.PLAN_LIMITS` has no `daily_review` feature, `study_service.review_card` increments no counter, `PaywallModal.tsx`'s `daily_review` trigger is a live union-type value with no consumer. Drafted `docs/specs/phase-5/50-free-tier-daily-card-wall.md` at base 72dfab4: per-user counter via Redis `INCR` keyed `daily_cards:<user_id>:<YYYY-MM-DD-user-local>` with 48h TTL; 402 response with `{error, trigger, cards_consumed, cards_limit, resets_at}` payload; reuses existing `PaywallModal` `daily_review` trigger scaffold; reuses `EmailPreference.timezone` (UTC fallback — no new timezone field). AC-1..AC-10 defined; fail-open on Redis outage; admin bypass via `User.role`; Pro/Enterprise skip the Redis call entirely (Option 2 scope); new `daily_card_submit` (BE) + `daily_card_wall_hit` (FE) events to land in `.agent/skills/analytics.md` at impl. Convention-note: uses **402** where existing free-tier caps use **403** — semantically correct (HTTP 402 = "payment would resolve this response") but establishes a new precedent; 403→402 migration for other `check_and_increment` callsites is explicitly out of scope. Interpretation-note in spec: LD-001 text is ambiguous between "15/day with reset" and "15 lifetime"; this spec follows the authoring prompt's explicit per-day-with-reset reading; `.agent/skills/payments.md:78` "Foundation cards: 15 **lifetime**" amendment flagged as impl-slice cleanup. Streak-vs-wall midnight inconsistency flagged (streak=UTC per `gamification.md:14`, wall=user-local) — needs a future Locked Decision, not blocking. BACKLOG E-030 added (P1, 🔴) pointing at spec #50; blocks E-011 (spec #22, P5-S22b) and E-014 (spec #42, P5-S26b). LD-001 unchanged — this spec enforces it, doesn't amend it. No code changes in this slice; implementation follows in P5-S22-WALL-b. Awaiting CODEX review per Rule 11.
- **2026-04-19 — P5-S22a spec authored (closes LD-001 landing).** Authored `docs/specs/phase-5/22-plan-aware-missing-skills-cta.md` at base 6e126b3 + landed Locked Decision LD-001 ("free-tier daily-review budget: CONSUMES (α)") + added drift flags D-005/D-006/D-007 superseding SESSION-STATE §1A, BACKLOG.md:98 open-decision default, and `../claude-code-prompts-all-phases-v2.2-patch.md:282`. Code-level cross-check: silent (neither α nor β implemented in `usage_service.PLAN_LIMITS`, `study_service.get_daily_review`/`review_card`, or `PaywallModal.tsx`'s unused `daily_review` trigger) — no R3 stop. Spec defines AC-1..AC-9 for plan-aware CTAs (anonymous/free/pro) on Missing Skills; new `missing_skills_cta_clicked` event deprecates `gap_study_clicked` at P5-S22b cutover; 15-card-wall dependency flagged for P5-S22b's Step 1 audit. BACKLOG E-011 Notes updated; status untouched (flips at P5-S22b ship per R15). Commit `72dfab4`. Awaiting CODEX review per Rule 11.
- **2026-04-19 — P5-S20 shipped (closes E-009).** Moved Job Fit Explanation above the fold on `/prep/results`. Flattened the `grid grid-cols-1 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_280px]` structure from 3 panel wrappers (left sidebar / main / right panel) to 11 direct grid children, each carrying explicit `lg:col-start-*` + `lg:row-start-*` (+ `lg:col-span-2` for right-panel items at LG breakpoint) + `xl:col-start-*` + `xl:col-span-*` + `xl:row-start-*` classes. Rationale: the previous structure pushed Job Fit to DOM position 5+ on mobile because the left sidebar's 4 items (ATS Score, Score Breakdown, Quick Nav, 3 CTA buttons) rendered before the main panel. Target order (ATS Score → Job Fit → Missing Skills → Keywords → Score Breakdown → Skills Radar → Bullets → Formatting → Improvements → Nav → CTAs) required Missing Skills (formerly right-panel 1st) to be 3rd on mobile — un-achievable with CSS `order-*` alone because the slice prompt mandated "preserve keyboard tab order — Job Fit reachable earlier" (tab order follows DOM, not CSS order). Solution: change JSX DOM order; use Tailwind grid placement to reconstruct desktop layout. `lg:sticky lg:top-20` migrates from the left-sidebar wrapper to the ATS-score grid item directly; `xl:sticky xl:top-20` migrates from the right-panel wrapper to the Missing-Skills grid item. All 9 section IDs (`ats-score`, `score-breakdown`, `job-fit`, `keywords`, `skills`, `bullets`, `missing-skills`, `formatting`, `improvements`) preserved — `results_tooltip_opened` 9-value `section` enum stable. All 9 `PanelSection` tooltip copies (spec #21 §Education Layer Design) preserved verbatim. **New PostHog event:** `job_fit_explanation_viewed` fires once per mount via `useRef` idempotency guard (matches `home_dashboard_viewed` / `first_action_viewed` convention) with `{view_position: 'above_fold'}` — the `view_position` property is fixed at "above_fold" after this slice and leaves headroom for a scroll-triggered or below-fold variant without needing a new event name. Catalogued in `.agent/skills/analytics.md`. **Tests (134 → 142, +8):** `tests/pages/Results.ordering.test.tsx` asserts DOM order via `compareDocumentPosition` across 5 ordering invariants (ATS<JobFit, JobFit<MissingSkills, JobFit<Keywords, MissingSkills<Keywords, Keywords<ScoreBreakdown), section-ID stability (9 ids), mount-fire of `job_fit_explanation_viewed` with correct payload, and idempotency across remount. tsc clean. BE unchanged. R15 observed: BACKLOG E-009 🔴 → ✅ in the same commit with close-line. No CODE-REALITY regen script exists on disk (scripts/ only contains `dev-*.sh` and `start/stop.sh` — flagged 2026-04-19 P5-S21b as stale at sha `f09be80`, still stale after this slice — regenerate before the next plan-level prompt). Awaiting CODEX review per Rule 11.
- **2026-04-19 — P5-S21b shipped (closes B-004 + E-010 info-icon half).** Keyword color mismatch fix + education-layer tooltips per spec #21 (authored in `fe4a333`). KeywordChart: introduced `KEYWORD_LEGEND` + `rgbaFromCssVar` helper (both exported) as single source of truth for chart cells AND legend swatches in `Results.tsx`; replaced the hardcoded violet `rgba(124,58,237,0.5)` at the old line 83 with a theme-aware `rgbaFromCssVar('--color-accent-secondary', 0.5)` call — now correct across Dark/Light/Midnight themes (R12 compliance). Legend adopts chart's opacities per spec Option A (matched α=1.0, missing α=0.25, in-resume α=0.5). PanelSection primitive extracted to `src/components/dashboard/PanelSection.tsx`, hardened with Escape-dismiss + `useClickOutside` (new hook at `src/hooks/useClickOutside.ts`) + `role="tooltip"` + `aria-describedby` + `aria-expanded`; focus returns to trigger on Escape; tooltip copy shape changed from `string` to `{what, how, why}`. Results: Score Breakdown refactored through PanelSection; tooltips added on all 5 previously-uncovered sections (score_breakdown, skills_radar, bullets, formatting, improvements) with drafted copy verbatim from spec §Education Layer Design; section-id anchors added (`ats-score`, `score-breakdown`, `missing-skills`, `formatting`, `improvements`). New PostHog event `results_tooltip_opened` with 9-value `section` enum catalogued in `.agent/skills/analytics.md`; fires on open only (no close event, no hover event). Test setup gained a ResizeObserver shim (Recharts dependency). FE tests **114 → 134 (+20)**: `tests/components/KeywordChart.colors.test.tsx` (9 tests) + `tests/components/PanelSection.tooltip.test.tsx` (10 tests) + `tests/pages/Results.tooltips.test.tsx` (1 test). tsc clean. BE unchanged (no backend touched). R15 discipline: BACKLOG B-004 and E-010 flipped 🔴 → ✅ in the same commit as the code change, with `Closed by <sha>` close-lines; guided-tour half of E-010 deferred per spec §Out of Scope — added to Deferred Hygiene Items. Spec #21 status flipped Draft → Done. CODE-REALITY.md stale (sha `f09be80`, HEAD moved) — regenerate before the next plan-level prompt.
- **2026-04-19 — P5-S18b retrofit (docs reconciliation only).** Feature shipped in commit 55ac7bd on an earlier date but BACKLOG E-006 was 🔴 and spec #40 status was Draft. This slice: flipped E-006 🔴 → ✅ with close-line referencing 55ac7bd; updated spec #40 status to "Done — Backfilled"; added §12 "Known Label Drift" to spec #40 documenting that 17 in-code sites label state-aware work as "P5-S18c" (authoritative ID is P5-S18b per BACKLOG + PHASE-5-STATUS). In-code labels left unchanged — cosmetic, no runtime impact. Process note: commit 55ac7bd should have closed E-006 at commit time per R15; capturing this as a process miss for future reference.
- **2026-04-19 — P5-S18c retrofit (docs reconciliation only).** Feature shipped in commit f075a64 on an earlier date but BACKLOG E-007 was still 🔴. Same R15 miss pattern as E-006 (closed in 623c5a0 earlier today). This slice: flipped E-007 🔴 → ✅ with close-line referencing f075a64; updated spec #41 status to "Done — Backfilled". No runtime change, no in-code label drift to reconcile. Process note: two consecutive R15 misses (55ac7bd and f075a64) suggest BACKLOG-close is being skipped at commit time; worth a process-side check before the next feature slice.
- **2026-04-19 — Generated CODE-REALITY.md at commit `f09be80` on 2026-04-19.** Read-only audit snapshot landed at repo root (`CODE-REALITY.md`, 701 lines). 12 sections: repo metadata, backend models/routes/services/alembic, frontend routes/pages/types, known-dead code, skills inventory, drift flags, open questions. Produced as a map for off-disk advisors (chat-Claude) to draft accurate prompts without needing to re-explore the tree each session. No product code touched. Commit pairs CODE-REALITY.md + SESSION-STATE.md only — dirty parent-repo deletions (`../archive/*`) and in-repo scratch (`Enhancements.txt`, `.dev-pids`, `BACKLOG.md`) intentionally left untouched. Ten drift flags surfaced — most are already tracked in Deferred Hygiene / Tech Debt; net-new flags are (a) legacy `/api/cover_letter` vs real `/api/cover-letter` and `/api/interview` vs `/api/interview-prep` mismatch in AGENTS.md routers table, (b) `onboarding.py` + `payments.py` live in legacy `app/api/routes/` folder despite being v1-mounted, (c) `Category.tags` JSONB column absent from AGENTS.md Models table, (d) `UsageLimit` referenced in AGENTS.md Models table but no model file exists, (e) `study-engine.md` skill file missing `description:` frontmatter. Awaiting CODEX review per Rule 11.
- **2026-04-19 — Local dev-DB user-data wipe.** Ran `scripts/wipe_local_user_data.py` against `localhost:5432/hireport`. Deleted 77 rows across 16 user-gen tables (users=3, subscriptions=3, card_progress=26, missions=1, mission_days=22, mission_categories=7, user_badges=6, gamification_stats=3, email_preferences=3, usage_logs=1, tracker_applications_v2=2, plus 5 empty tables). Preserved 38 content rows (cards=15, categories=14, badges=9) and `alembic_version` (1). Transaction-wrapped, committed cleanly. Railway and all remote DBs untouched. Stripe test-mode customer orphans accepted — no API cleanup. Motivation: unblock obsoleting P5-S19 existing-user migration; also clears stale dev state ahead of P5-S18b.
- **2026-04-19 — Slice 5.17b (closes v2.1 item 5.17 end-to-end + bundled audits).** Wired `services/api.ts::generateInterviewPrep(_, _, {forceRegenerate})` + `useInterview` pass-through + `pages/Interview.tsx` cached chip / fresh free-usage chip / window.confirm() on free-tier regenerate against the `a2a79d5` cache backend. New `src/utils/jdHash.ts` mirrors `app/utils/text_hash.py` for analytics-prefix correlation only (no JD content sent — first 8 hex chars only). New events `interview_questions_cached_served` + `interview_questions_regenerated` in `.agent/skills/analytics.md`. Tests `tests/Interview.test.tsx` (3 new). FE 111 → 114, BE 248/248 unchanged (no backend touched), tsc clean. **Bundled audits:** DEFER-A classified ASPIRATIONAL — tracker has zero `jd_hash` logic; Locked Decision "Auto-save scan to tracker" updated with not-yet-implemented status; `[5.17-follow] tracker jd_hash dedupe` opened. DEFER-B classified LARGER-CLEANUP — 4 flat `/api/*` routes, not 1; `[5.17-follow] flat /api/* legacy-route cleanup` opened. PHASE-5-STATUS row 5.17 flipped 🟡 PARTIAL → ✅ SHIPPED; deferred item 5.17b closed. Awaiting CODEX review per Rule 11.
- **2026-04-19 — Spec #49 (closes v2.1 item 5.17 backend, opens 5.17b).** Built the interview-question cache per spec #49. New files: `app/utils/text_hash.py` (`hash_jd` — whitespace-collapse + casefold + SHA256 hex), `app/models/interview_question_set.py` (PG table, unique index on `(user_id, jd_hash)`), migration `f3350dcba3a5`, `app/services/interview_storage_service.py::generate_or_get_interview_set`. Reworked `app/api/routes/interview.py` so authenticated callers hit the cache before the free-tier gate (AC-5). Additive response fields: `cached`, `generated_at`, `model_used`. Anonymous-caller path preserved unchanged. Schema updates: `InterviewPrepRequest.force_regenerate` (optional, default False); `InterviewPrepResponse` gains three optional fields — frontend keeps parsing unmodified. Tests: `tests/services/test_interview_storage.py` (6 new) pin AC-1..AC-5b. BE tests 242 → 248 (+6, non-integration), 6 integration deselected unchanged. FE 111/111 unchanged; tsc clean. Migration up/down/up verified. **Audit surprise:** `hash_jd` did not exist on disk despite prior playbook references — the tracker Locked Decision authorized creating `app/utils/text_hash.py`, which this slice does; tracker auto-populate can adopt it later. Frontend wiring (force_regenerate + cached indicator) deferred as 5.17b.
- **2026-04-19 — Phase-5 status reconciliation (spec #48, closes v2.1 item 5.9).** Audited all 26 v2.1 Phase-5 items + 5 v2.2-patch items + 4 post-playbook slices (S44–S47) against `main` (post-`f1bcf94`). Produced `docs/PHASE-5-STATUS.md` as the authoritative on-disk status doc (Decision "Phase-5 status is authoritative on disk" in Locked Decisions). Totals: 22 ✅ SHIPPED, 3 🟡 PARTIAL (5.3, 5.13, 5.19 + S26b), 4 🔴 PENDING (5.17, 5.24, 5.25, 5.26), 3 ❓ AMBIGUOUS (5.19, 5.20, 5.23). Surfaced surprises: (a) interview-question storage (5.17) has no spec **and** no code — further behind than playbook implied; (b) spec #36 frontmatter / v2.1 item 5.22 numbering drift (P5-S26a vs P5-S26b) — SHIPPED either way. Pattern captured as spec #48. No product code touched; tests unchanged.
- **2026-04-19 — Spec #47 backfill (resume rewrite content preservation — v2.1 flag closure).** Audited the v2.1 🟡 PARTIAL "missing original content" flag against `main` (`fc933d1`). Bug does not reproduce: P5-S9 (spec #09) already raised the input cap to 40k chars and `max_tokens` to 8k, and the prompt carries explicit preservation rules (rules 1/7/8). Drafted `docs/specs/phase-5/47-resume-rewrite-content-preservation.md` retroactively documenting why the bug no longer reproduces, and added AC-2 regression test `test_prompt_includes_preservation_rules` in `tests/services/test_resume_rewrite.py` pinning the three preservation clauses verbatim. Complements the existing P5-S9 input-truncation test (AC-1). No production code changed. BE tests 241 → 242 (non-integration, +1). FE unchanged at 111. v2.1 resume-rewrite flag closed.
- **2026-04-19 — Spec #43 backfill (Stripe webhook idempotency).** Step-2 audit of P5-S26c found idempotency was already shipped (SELECT-first pattern + `stripe_events` table + one existing test). No code change needed. Drafted `docs/specs/phase-5/43-stripe-webhook-idempotency.md` documenting the existing implementation, added AC-4 test `test_handler_exception_rolls_back_stripe_event_row` (uses SAVEPOINT to mirror production rollback), fixed stale "Spec #22" citation in `payments.md` → Spec #43, dropped the stale Known-Broken row. Rule-14 doc-sync debt closed for webhook idempotency. Concurrent-delivery INSERT-first refactor deferred — see `[S26c-defer]` in Deferred Hygiene Items.

---

## Hard Constraints (current sprint)

These rules apply across Phase 5. Add or remove as the sprint changes.

- **Routes**: All new routes go under `/learn/*` or `/prep/*`. **No new flat routes.** (Reaffirmed at P5-S14 — `TopNav` / `MobileNav` only surface `/home`, `/learn`, `/prep`, `/profile`, `/admin`; any new flat path would have no nav home.)
- **Env vars**: Any new env var requires `.env.example` update in the same commit.
- **LLM calls**: All LLM calls go through the router — `generate_for_task()` in `app/core/llm_router.py`. Do not import a provider SDK (Gemini / Anthropic / OpenAI) directly from service code, and do not call `get_llm_provider()` from the legacy `app/services/llm/factory.py`. Pro/reasoning tier for rewrite, cover letter, gap analysis, chat-with-AI, admin insights. Flash/fast tier for extraction, classification, simple Q&A.
- **Design tokens**: Every color / spacing / shadow in frontend code must come from design tokens (`src/styles/design-tokens.ts`) via Tailwind utilities (`bg-bg-surface`, `text-text-primary`, `border-border-accent`). No hardcoded hex values. (CLAUDE.md R12.)
- **PostHog events**: Every new user-facing feature fires at least one event. snake_case naming. Add the event to `.agent/skills/analytics.md` so the catalog stays current.
- **Backward compatibility**: Phase 5 cannot break existing user data. Migrations need defaults that backfill existing rows.
- **Persona gating**: PersonaPicker shipped in P5-S17 — all `/learn/*`, `/prep/*`, and `/home` routes require `user.persona` to be set. Exception: `/profile`.
- **Stripe**: All webhook handlers must be idempotent (see spec #43). No new webhook events without idempotency check.
- **Frontend test coverage**: Every new page added in Phase 5 must ship with at least one Vitest test. Current frontend count: **142/142** (last run: P5-S20). Grow with every UI slice.
- **Backlog discipline**: Every implementation prompt must reference the BACKLOG ID(s) it closes (CLAUDE.md R15). Status flips to ✅ + `closed by <commit-sha> on <date>` + move to Closed table.
- **Audit-scoped step 1**: Every implementation prompt's first step is an audit calibrated to blast radius (CLAUDE.md R16). Frontend type changes MUST surface the live component graph from CODE-REALITY.md. If CODE-REALITY is stale (sha ≠ HEAD or chat Project copy not synced), regenerate + re-upload before drafting the audit.

---

## Deferred Hygiene Items

- `deprecated_route_hit` PostHog event not wired in the 10 `<Navigate>` redirect nodes in `src/App.tsx`. Defined in spec #12 §Analytics but deferred from P5-S13. Blocks Phase 6 redirect-block cleanup (no signal to confirm when old paths stop receiving hits). Tracked as B-008.
- **AGENTS.md Models table User row (S16 retrofit)** — line 243 still lists legacy `target_company`, `target_date` column names. These were renamed by the P5-S16 migration (`02bf7265b387`) to `interview_target_company` (String(100)) and `interview_target_date` (Date). Update when the Models table is next edited. Surfaced during P5-S17 amend; out of scope for S17 itself.
- **Persona-switch UX from `/profile`** — post-P5-S17 follow-up (spec #34 Out of Scope). P5-S17 removed the legacy in-place "Change goal" modal from StudyDashboard (plus the "Set your goal →" CTA from the `user.persona === null` empty state on `/learn`). No replacement shipped; the persona-switch UX will reuse `/onboarding/persona` (likely `?mode=switch`) when the flow is specced. Until then, users cannot change persona post-pick.
- **StudyDashboard empty-state CTA gap** — the `user.persona === null` branch on `/learn` had its "Set your goal →" CTA button removed in P5-S17 (it launched the deleted settings-modal PersonaPicker). The surrounding "Your Goal / Tell us what you're working towards" card still renders but is now action-less. `PersonaGate` makes this branch effectively unreachable, so the visual gap is theoretical — but revisit with the next `/learn` empty-state redesign.
- **`docs/specs/phase-4/24-posthog-dashboards.md` event #13** — `onboarding_persona_selected` is referenced by name in the Phase-4 dashboards spec. The analytics catalog now carries a deprecation marker pointing to this spec; update the spec (or remove the dashboard entry) when the Phase-4 PostHog dashboard is decommissioned.
- **[S35-flag] `border-contrast` Tailwind class undocumented** — in use across widgets (AnimatedCard, SkeletonCard, DashboardWidget) but not listed in `.agent/skills/design-system.md` token inventory. Backfill the skill file during the next design-system touch.
- **[S35-flag] AGENTS.md Frontend Routes mission path drift** — AGENTS.md Frontend Routes table references `/api/v1/mission` (singular); `services/api.ts` and spec #35 use `/api/v1/missions/active` (plural). Align AGENTS.md to the code's canonical path.
- **[S35-flag, conditional — CONFIRMED P5-S18]** Team-features waitlist signup — no existing waitlist/email-capture/notify-me component was found during P5-S18 (`grep -rn "waitlist\|Waitlist\|WaitList\|NotifyMe\|NotificationSignup" src/` returned zero). `TeamComingSoonWidget` ships action-less; add a Team-features waitlist signup in a follow-up slice. Doubles as a PRD §1.5 Team-dashboards demand signal.
- **[S18-flag]** WeeklyProgress empty-state heuristic: currently uses `stats.total_xp === 0 && longest_streak === 0` as a proxy for "no review history" to avoid duplicating `ActivityHeatmap`'s fetch (`/api/v1/progress/heatmap?days=90`). Edge-case false negatives possible for users with XP from non-review sources or stale streak + empty current window. Fix: expose review-count from `ActivityHeatmap` via a render prop or callback, subscribe from widget.
- **[S18-flag]** `DashboardWidget` contract: `action` prop is hidden when `state === 'error'` (only "Try again" renders). This is sensible UX but not documented in spec #35 §Solution. Document when the primitive's contract is next touched, either in the spec or in a new design-system skill entry.
- **[S26c-defer]** Concurrent-delivery INSERT-first refactor for Stripe webhook. Current SELECT-first pattern can produce a transient 500 on rare concurrent duplicate deliveries hitting separate DB connections — Stripe's retry self-heals. Revisit only if production logs show this occurring with non-trivial frequency; tiny blast radius today. See spec #43 §Out of Scope for the INSERT-first-catch-IntegrityError alternative.
- **[S47-defer]** Confirm `app/services/ai_service.py` is dead code and delete it. It duplicates `app/services/gpt_service.py::generate_resume_rewrite`/`generate_cover_letter`/`generate_interview_questions`/`rewrite_bullets_gpt` and is only imported by `app/api/v1/routes/resume.py::optimize_resume` (enterprise-only path with no frontend caller). Pair the deletion with verifying `/api/v1/resume/{id}/optimize` has no live traffic; if we keep the enterprise path, refactor it to call `gpt_service` instead of duplicating. Surfaced during the spec #47 audit.
- ~~**5.17b — Interview-question storage frontend wiring**~~ **(CLOSED 2026-04-19, slice 5.17b)**. `services/api.ts::generateInterviewPrep` now forwards `{forceRegenerate}` → `force_regenerate` body field, `useInterview.runInterviewPrep(_, _, options?)` passes it through, `Interview.tsx` ships a `data-testid="cached-chip"` "Cached — generated <relative>" pill on `cached:true`, a `data-testid="free-usage-chip"` "Used 1 of your monthly free generations" pill on `cached:false && plan==='free'`, and a `window.confirm()` on free-tier Regenerate. Vitest coverage in `tests/Interview.test.tsx` (3 tests). New events `interview_questions_cached_served` + `interview_questions_regenerated` in `.agent/skills/analytics.md`.
- **[5.17-follow] tracker `jd_hash` dedupe** (opened 2026-04-19 by 5.17b audit). The "Auto-save scan to tracker" Locked Decision specified `(user_id, jd_hash)` dedupe but only the auto-create-on-scan side appears implemented (verify via `tracker_auto_created_from_scan` event); the dedupe-via-`hash_jd` side is not. `app/utils/text_hash.py::hash_jd` now exists (spec #49), but `tracker_service_v2.py` doesn't call it and `tracker_applications_v2` has no `jd_hash` column. Definition of done: add `jd_hash` column + unique index to `tracker_applications_v2`, route the analyze auto-create path through `hash_jd` for upsert, add a consistency test asserting tracker and interview storage produce identical `hash_jd` for the same JD. Needs its own spec per Rule 14.
- **[5.17-follow] flat `/api/*` legacy-route cleanup** (opened 2026-04-19 by 5.17b DEFER-B audit). 4 flat legacy routes still mounted in `app/main.py:120-123` (`analyze`, `rewrite`, `cover_letter`, `interview`) alongside their `/api/v1/*` counterparts. S45 already removed legacy `/api/tracker`; same pattern (deprecation log → FE migration → drop legacy mount after 30 days of zero traffic) applies to these 4. The `/api/interview-prep` → `/api/v1/interview-prep` migration was bundled into 5.17b's scope but classified LARGER-CLEANUP because the same fix needs to land for analyze/rewrite/cover_letter together to avoid four micro-migrations. Needs its own slice + spec.
- **[P5-S21b-follow] Analysis Results first-visit guided tour** (opened 2026-04-19 by P5-S21b). E-010 originally covered two education-layer surfaces: (1) info-icon tooltips on every section, (2) first-visit sequential guided walkthrough. P5-S21b shipped (1) and deferred (2) per spec #21 §Out of Scope. Next steps when picked up: pick a walkthrough primitive (existing `GuidedTour.tsx` in `components/onboarding/` may be reusable; investigate first), scope the copy (likely same 9-section corpus from spec #21), decide the trigger (first visit to `/prep/results` per-user via localStorage flag, mirroring `first_action_seen`). Needs its own spec per Rule 14 before implementation.
- **[local-setup-guide] ruff not installed in backend venv by default setup.** `python -m ruff check` fails with `No module named ruff` in the backend venv; repo has no alternative linter wired in the standard gate path either. Either add `ruff` to `requirements-dev.txt` and document `python -m ruff check app/` in the Makefile / local-setup-guide, or remove ruff from quality-gate expectations in future slice prompts. Surfaced during the spec #47 slice.

---

## Tech Debt (living log — tackle during P6 cleanup unless it escalates)

| Item | Detail |
|---|---|
| Legacy LLM provider factory | `app/services/llm/factory.py` + `claude_provider.py` + `gemini_provider.py` run parallel to the real router at `app/core/llm_router.py`. Not currently breaking. Do not extend the legacy factory — route all new LLM calls through `generate_for_task()`. Consolidate in Phase 6 cleanup. Surfaced by the 2026-04-17 audit. |
| Registration IP-blocking is DB-based, not Redis | `app/api/v1/routes/auth.py` inlines the limit check against the `registration_logs` table (30-day window query). The original playbook skill described a Redis counter. Both approaches work. Kept for P5-S4 backfill; no behavioural change planned. |
| Email-preferences API path mismatch | Frontend `hirelens-frontend/src/services/api.ts:314,321` calls `/api/v1/email-preferences`, but the backend router is mounted at `/api/v1/email-prefs` (`app/main.py`, confirmed in `AGENTS.md:187`). The endpoints currently 404 in production. Surfaced by the 2026-04-17 P5-S11 trace. Fix in a future slice — pick one canonical path (recommend the longer `/email-preferences` to match the spec at `docs/specs/phase-2/16-email-preferences.md`) and update both ends together. |

---

## Test Suite Status

- **Backend (CI subset, `-m "not integration"`)**: 248 passed (last run: slice 5.17b — no backend touched)
- **Backend (integration, `-m integration`)**: 6 deselected in CI; requires live LLM keys — run locally before LLM/extraction/embedding changes
- **Frontend (Vitest)**: 142/142 passing (last run: P5-S20 — 134 → 142 with `tests/pages/Results.ordering.test.tsx`)
- **Coverage tooling**: `pytest-cov` is intentionally NOT installed (CLAUDE.md R13). Do not add `--cov` flags without updating `requirements-dev.txt` and getting sign-off.

---

## Project File Inventory (canonical references)

### In repo (Claude Code reads these)

| File | Purpose | Owner |
|------|---------|-------|
| `AGENTS.md` | How this project works (stack, conventions, source-of-truth hierarchy) | Dhamo (hand-edit) |
| `CLAUDE.md` | How Claude Code should behave (16 rules, 3-strike, test gates) | Dhamo (hand-edit) |
| `BACKLOG.md` | Bugs + enhancements + open decisions; immutable IDs | Dhamo authors; Claude Code flips status only |
| `SESSION-STATE.md` | THIS FILE — live session pointer + drift log | Claude Code updates every slice |
| `CODE-REALITY.md` | Generated snapshot of live codebase (routes, models, component graph, dead code) | Claude Code regenerates on demand |
| `WORKFLOW-MODES.md` | Decision tree for which Claude Code workflow mode to use per slice type | Dhamo (hand-edit) |
| `STRATEGIC-OPTIONS.md` | $100M ARR strategic options analysis. Read before Phase 6 planning. | Dhamo |
| `docs/prd.md` | Product requirements | Dhamo |
| `docs/PHASE-5-STATUS.md` | On-disk authoritative status for all Phase-5 items | Claude Code per Locked Decision |
| `docs/specs/phase-N/NN-feature.md` | Per-feature specs (authored before code per CLAUDE.md R14) | Authored per slice |
| `.agent/skills/*.md` | Subsystem-level domain knowledge | Slow-changing reference |

### In Claude chat Project knowledge (Claude in chat reads these)

| File | Purpose | Sync state |
|------|---------|------------|
| `skillforge_playbook_v2.md` | Master phased plan (v3 due after P5-S35) | Static |
| `claude-code-prompts-all-phases-v2.md` | v2.1 — slice-by-slice prompts (active) | Static |
| `claude-code-prompts-all-phases-v2.2-patch.md` | v2.2 patch — flow-audit additions | Static |
| `prd.md` | Mirror of `docs/prd.md` | Re-upload on PRD changes |
| `CODE-REALITY.md` | Mirror of repo CODE-REALITY.md | Re-upload when repo copy regenerates (see Session Header sync field) |

Removed from chat Project (previously listed): `claude-code-prompts-all-phases.md` (v1 — superseded by v2.1); `local-setup-guide.md` (setup is Claude Code's concern, not chat-Claude's); `ClaudeSkillsforge_sessiontext.docx` (chat transcript — not an agent artifact).

---

## Update Protocol

At the end of every slice:
1. Update **Session Header**: HEAD commit sha, mark CODE-REALITY stale if routes/models/types/App.tsx/layouts changed, flag chat Project copy for re-upload if repo copy regenerated.
2. Move the just-completed slice into "Recently Completed" (top of list, drop oldest).
3. Update "Last Completed Slice" and "Next Slice". Reference the BACKLOG ID(s) closed.
4. If a feature was fixed: remove from "Known-Broken Features" and confirm BACKLOG status flipped to ✅.
5. If a refactor zone is now stable: remove from "Active Refactor Zones".
6. If you noticed any drift between sources: append a row to **Drift flags**.
7. If a new constraint or decision emerged: add to the right section.
8. Commit SESSION-STATE.md alongside the slice's other files.

If you ever feel SESSION-STATE.md is out of sync with reality, run the contingency prompt:
> *"Read SESSION-STATE.md. Run `git log --oneline -20` and read the last 5 commit messages and any `docs/specs/phase-5/` files added recently. Read CODE-REALITY.md and check whether its commit sha matches HEAD. Compare all of the above to SESSION-STATE.md. Report drift and propose updates. Do NOT modify the file until I approve."*

---

*Last hand-edit: 2026-04-19 — D-001/D-003/D-004 resolution; added Drift flags discipline; Session Header now tracks CODE-REALITY sync state for both repo and chat Project copies; Hard Constraints aligned with CLAUDE.md R12/R13/R15/R16; Project File Inventory expanded to include BACKLOG, CODE-REALITY, WORKFLOW-MODES, PHASE-5-STATUS and the chat Project mirror/sync state.*