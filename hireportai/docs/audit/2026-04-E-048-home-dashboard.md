# E-048 — HomeDashboard Widget Composition Audit (Mode 1)

**HEAD at audit:** `1fc8cb2`
**Mode:** audit-only. R14 exception (a) regenerated audit artifact. Zero code, zero spec, zero test edits.
**BACKLOG anchor:** E-048 (P1, 🔴, audit-only, from 2026-04-25 chat UX audit).
**Scope:** Audit `HomeDashboard.tsx` widget rendering rules against `{persona × plan × has_mission × has_recent_scan × streak_state}`, focused on the free-user-post-scan case.

## 1. Reported symptom (verbatim from E-048 BACKLOG row + 2026-04-25 audit)

Free-user-post-scan view of `/home` shows:

- **Mission-in-flight + Countdown widgets framing the same mission twice.** `Mission in flight` says "3 days left in your mission" with `Open mission` CTA. `Countdown` says "4 DAYS LEFT, Interview, Day 1 of 4, 0% complete" with `View mission` CTA. Two widgets, two CTAs pointing to the same `/learn/mission`. Redundant + confusing.
- **`Interview Target: No interview company set yet` empty-state alongside an ACTIVE Mission widget.** Persona data appears not to flow into the InterviewTarget widget (audit's framing — actual root cause is the user has `interview_target_company == null` while having `interview_target_date != null`; the widget honestly reports the field state but coexists badly with an active Mission).
- **`Today's Review: 5 cards due` + `Start review`** — fine.
- **`Last Scan: JPMorgan Chase & Co. ATS score: 71%` + `View results`** — fine, but for a free user this should be the strongest next action and is buried below two redundant Mission widgets.
- **For a free user who has burned their scan and has no Pro subscription**, the dashboard should foreground (a) "Study the gaps from your last scan" OR (b) "Upgrade to unlock the study engine" — **neither is present**.

## 2. SOP gates passed at slice start

- SOP-1 ✅ HEAD `1fc8cb2` matched prompt
- SOP-2 ✅ working tree dirt smaller than prompt expected — `UsageContext.tsx` was committed in `63203ef` (P5-S63); known-set is now just `.DS_Store`, `Enhancements.txt`, `wipe_local_user_data.py` + untracked items
- SOP-4 ✅ `.agent/skills/home.md` exists; loaded
- SOP-5 ✅ read specs `34-persona-picker-and-home.md`, `35-home-dashboard-and-widgets.md`, `40-home-dashboard-state-aware.md`, `44-home-widget-empty-states.md`, `46-post-persona-first-action.md`
- SOP-6 / R17 ✅ B-050 highest in-use, B-051 free (not claimed; per LD-7, only file if regressions ≥3 surface — they did not)
- SOP-8 ✅ no concurrent commits
- Persona enum verified against `src/context/AuthContext.tsx:25` — `'interview_prepper' | 'career_climber' | 'team_lead'` (3-value)
- Plan enum verified against `src/context/UsageContext.tsx:7` — `'free' | 'pro' | 'enterprise'` plus orthogonal `isAdmin: boolean`
- HomeStateName enum verified against `src/types/homeState.ts` — 6 values: `mission_overdue | streak_at_risk | mission_active | resume_stale | inactive_returner | first_session_done`

> **Spec #40 status correction (worth flagging):** spec #40 frontmatter on disk says `Status: Done — Backfilled (shipped in commit 55ac7bd)`. So **P5-S18b is NOT 🔴 pending** — it shipped 2026-04-18 and was retroactively spec-closed 2026-04-19. The original prompt's framing assumed spec #40 was pending; on disk it's done. This shifts the LD-6 recommendation away from option (b).

## 3. HomeDashboard render tree (current on-disk)

Per `src/pages/HomeDashboard.tsx` (lines 105-125):

```
HomeDashboard
├── <h1> greeting (B-016/B-027 isFirstVisit fork)
├── <StateAwareWidgets persona={user.persona}>           (line 111 — top slot)
│     └── if data && states.length>0:
│         _renderWidget(states[0], persona, context)
│         ├── 'mission_overdue'      → MissionOverdueWidget
│         ├── 'streak_at_risk'       → StreakAtRiskWidget
│         ├── 'mission_active'       → MissionActiveWidget    ← E-048 anchor
│         ├── 'resume_stale'         → ResumeStaleWidget
│         ├── 'inactive_returner'    → InactiveReturnerWidget
│         └── 'first_session_done'   → FirstSessionDoneWidget
└── persona switch:
    ├── 'interview_prepper' → InterviewPrepperMode
    │     ├── InterviewPrepperChecklist               (above grid; auto-hide ≤14d post-completion)
    │     └── grid: CountdownWidget · InterviewTargetWidget · TodaysReviewWidget · LastScanWidget
    ├── 'career_climber'    → CareerClimberMode
    │     └── grid: StreakWidget · TodaysReviewWidget · WeeklyProgressWidget · LastScanWidget
    └── 'team_lead'         → TeamLeadMode
          └── grid: TodaysReviewWidget · StreakWidget · WeeklyProgressWidget · TeamComingSoonWidget
```

**BE state evaluator priority** (`hirelens-backend/app/services/home_state_service.py:38-46`):
`mission_overdue > streak_at_risk > mission_active > resume_stale > inactive_returner > first_session_done`

Returns ALL active states; FE renders only `states[0]` (top-priority slot).

## 4. Per-widget gate inventory

| Widget | Render-trigger | Gate condition | Reads from | Plan-aware? |
|--------|----------------|---------------|-----------|-------------|
| InterviewPrepperChecklist | `persona === 'interview_prepper'` AND `!skip` AND not auto-hidden | localStorage `SKIP_STORAGE_KEY` + `completedAt` 14-day auto-hide | `useAuth` + `/api/v1/onboarding/checklist` | no |
| CountdownWidget | unconditional in `InterviewPrepperMode` | branches on `!date` (Mode 1: link/modal) vs `date` (Mode 2: countdown + mission CTA via `fetchActiveMission()`) | `user.interview_target_date` (prop) + active mission fetch | no |
| InterviewTargetWidget | unconditional in `InterviewPrepperMode` | `emptyCopy(company, date)` 3-case empty-state (B-017 fix) | `user.interview_target_company` + `user.interview_target_date` (props) | no |
| TodaysReviewWidget | unconditional in IP / CC / TL modes | `completed_today === true` → empty state "Done for today" (B-019); else "N cards due" + `Start review` | `GET /api/v1/study/daily` (`fetchDailyQueue`) | no — but spec #50 wall fires server-side; widget shows `daily_review` paywall if hit |
| LastScanWidget | unconditional in IP / CC modes | `apps.length === 0` → "Run your first scan to see results here." (empty); else latest tracker app | `fetchUserApplications()` | no |
| StreakWidget | unconditional in CC / TL modes | renders `current_streak` from gamification stats | `useGamification` | no |
| WeeklyProgressWidget | unconditional in CC / TL modes | empty heuristic `total_xp === 0 && longest_streak === 0` | `useGamification` | no |
| TeamComingSoonWidget | unconditional in TL mode | static placeholder ("Team dashboards coming") | none | no |
| MissionActiveWidget | state-slot trigger when `mission_active` is `states[0]` | `_daysUntil(mission_target_date)` for copy | `context.mission_target_date` from `/api/v1/home/state` | no — but `context.plan` available, **not consumed** |
| MissionOverdueWidget | state-slot trigger when `mission_overdue` is `states[0]` | overdue mission framing | `context` | no |
| StreakAtRiskWidget | state-slot trigger when `streak_at_risk` is `states[0]` | `current_streak >= 3` AND `last_review_at > 18h ago` (BE) | `context.current_streak` | no |
| ResumeStaleWidget | state-slot trigger when `resume_stale` is `states[0]` | `last_scan_date > 21d ago` AND no other higher-priority state (BE) | `context.last_scan_date` | no — and spec #56 free-tier lifetime scan cap means the `Re-scan` CTA dead-ends for free users (separate gap) |
| InactiveReturnerWidget | state-slot trigger when `inactive_returner` is `states[0]` | 7d ≤ `last_activity_at` ≤ 30d (BE) | `context` | no |
| FirstSessionDoneWidget | state-slot trigger when `first_session_done` is `states[0]` | first-session badge fired AND reps ≤ 3 (BE) | `context` | no |

## 5. Findings — matrix table

Each row = a widget interaction. Classification: ✅ correct / 🟡 contradictory / 🔴 missing / ❓ ambiguous.

| # | Persona | Plan | has_mission | has_recent_scan | streak_state | Widget(s) | Behavior | Classification | Confidence |
|---|---------|------|-------------|-----------------|--------------|-----------|----------|----------------|------------|
| 1 | interview_prepper | free | true (active) | true | any | MissionActiveWidget (top slot) + CountdownWidget Mode 2 (in-grid) | **Both render the same active mission**. MissionActive: "X days left in your mission" → CTA `Open mission` → `/learn/mission`. Countdown Mode 2: countdown progress bar + CTA `View mission` → `/learn/mission`. Same data, same CTA target, two surfaces. Reproduces E-048 symptom #1 verbatim. | **🟡 CONTRADICTORY** | **HIGH** |
| 2 | interview_prepper | any | any | any | any (with `interview_target_date != null` AND `interview_target_company == null`) | InterviewTargetWidget | Renders `'No interview company set yet.'` empty state (B-017 third branch). Coexists with CountdownWidget Mode 2 + MissionActiveWidget which all reference the same date. Reproduces E-048 symptom #2. Widget is "honest" but the InterviewPrepperMode grid forces a 4th widget that has no useful content for this state-shape. | **🟡 CONTRADICTORY** (composition issue, not widget issue) | **HIGH** |
| 3 | interview_prepper | free | any | true | any | LastScanWidget (in-grid, position 4) | Renders correctly with company + score, but lives at DOM position 5 in `InterviewPrepperMode` (after Checklist · Countdown · InterviewTarget · TodaysReview). For free-user-post-scan, this is the highest-signal "next action" and it's buried. Reproduces E-048 symptom #3. | **🟡 CONTRADICTORY** (correct content, wrong priority) | **HIGH** |
| 4 | any | free | any | true | any | (no widget exists) | **No `study_the_gaps` widget on `/home`**. Missing Skills CTA lives only on `/prep/results`; no on-home equivalent. Free user post-scan has no "study these gaps" call-to-action without re-navigating to `/prep/results`. Reproduces E-048 symptom #4. | **🔴 MISSING** | **HIGH** |
| 5 | any | free | any | true | any | (no widget exists) | **No `upgrade_to_study` widget on `/home`**. PaywallModal fires only on locked-feature click (Mission setup, daily-card wall, scan-cap reach). Free user with completed scan has no proactive upgrade CTA on home. Reproduces E-048 symptom #4. | **🔴 MISSING** | **HIGH** |
| 6 | any | any | true | true (>21d ago) | any | MissionActiveWidget OR (would-be) ResumeStaleWidget | BE priority: `mission_active > resume_stale`. User with active mission AND stale resume only sees mission framing — never gets the "your scan is 30 days old" nudge. **NET-NEW FINDING beyond E-048's reported set.** For Pro users with active mission this suppresses a useful prompt; for free users with active mission it's moot (re-scan blocked anyway by spec #56 lifetime cap). | **🟡 CONTRADICTORY (priority order)** | **MEDIUM** (Pro impact only — free is already constrained by spec #56) |
| 7 | any | any (incl. free) | any | any | any | All 6 state-aware widgets | **None of the 6 widgets branches on `context.plan`** even though the API contract surfaces it (spec #40 §5 line 100). So a `plan === 'free'` variant of any state cannot fire from the state-slot today — would need a new state name + new widget, OR plan-branching inside an existing widget. **NET-NEW FINDING beyond E-048's reported set.** This is the structural reason for findings #4 and #5. | **🔴 MISSING (architecturally — no plan-branching surface in state-aware layer)** | **HIGH** |
| 8 | career_climber | any | any | any | any | CareerClimberMode | Grid: StreakWidget · TodaysReview · WeeklyProgress · LastScan. No mission slot at all (career_climber has no `interview_target_date`); state-slot can still fire `mission_active` if user manually started a Mission. No contradiction observed in this composition. | **✅ CORRECT** for the documented persona shape | HIGH |
| 9 | team_lead | any | any | any | any | TeamLeadMode | Grid: TodaysReview · Streak · WeeklyProgress · TeamComingSoon. No scan widget — team_leads have no in-product scan flow exposed; LastScan absent is consistent. **TeamComingSoonWidget has no waitlist signup** (`[S35-flag]` already tracked in SESSION-STATE Deferred Hygiene). Not a regression from this audit; carrying forward existing flag. | ✅ for current scope; existing `[S35-flag]` carries the waitlist ask | HIGH |

### Summary counts

| Classification | Count | Findings |
|---|---|---|
| ✅ correct | 2 | #8, #9 |
| 🟡 contradictory | 4 | #1, #2, #3, #6 |
| 🔴 missing | 3 | #4, #5, #7 |
| ❓ ambiguous | 0 | — |

**Net-new findings beyond E-048's reported symptom: 2** (#6 + #7). Below the PUSHBACK threshold of ≥3. Both fold into the recommended fix-slice scope (no separate BACKLOG row needed).

## 6. Free-user-post-scan dedicated treatment

The audit's primary case. Concrete slice:

| Source | Citation | Observation |
|--------|----------|-------------|
| `HomeDashboard.tsx:111` | `<StateAwareWidgets persona={user.persona} />` | Top slot — for our user, BE returns `states=['mission_active', ...]` (active interview mission); slot renders `MissionActiveWidget`. |
| `HomeDashboard.tsx:113-118` | `<InterviewPrepperMode persona company={user.interview_target_company} date={user.interview_target_date} />` | Grid renders unconditionally below state slot. |
| `CountdownWidget.tsx:90-117` | Mode 2 (date set) | Calls `fetchActiveMission()`, sees `mission.status === 'active'`, sets action to `{ label: 'View mission', href: '/learn/mission' }`. **Same CTA target as MissionActiveWidget.** |
| `InterviewTargetWidget.tsx:30-36` | `emptyCopy()` | `(!company && date)` → `'No interview company set yet.'` Renders this empty state alongside the active Mission for the same date. |
| `LastScanWidget.tsx:17-46` | renders latest tracker app | Position 4/4 in IP grid, position 5 from top including Checklist. |
| **Missing** | (no file) | No widget bridges scan→study handoff on `/home`. No proactive upgrade CTA. |

**Root cause classification:**
- Symptoms #1-#3: composition issue. Both InterviewPrepperMode (P5-S18, spec #35) and StateAwareWidgets (P5-S18b, spec #40) render in parallel without coordination. Spec #40 §7 says "the static S18 persona grid stands alone in those cases" referring to *empty `states[]`* — not the case here. There is no rule for "when state-aware slot renders a state matching a static-grid widget's content, suppress the static widget."
- Symptom #4-#5: missing free-tier widget surface. No widget on `/home` covers the scan→study or scan→upgrade transition. The closest existing surface is `MissingSkillsPanel` on `/prep/results`.

## 7. Recommended next-slice — fix path

### Recommendation: **(c) NEW SPEC**

**Why not (a) amend P5-S18 widget logic only:** the fix needs cross-widget coordination (suppress static when state-slot renders matching content) AND a new free-tier study/upgrade surface. (a) would be a multi-widget edit with no governing spec — violates R14 default for new design surface.

**Why not (b) fold into P5-S18b spec #40:** spec #40 is **already shipped** ("Status: Done — Backfilled in commit 55ac7bd", retroactively closed 2026-04-19). Folding into a closed spec is a spec-amendment slice itself; cleaner to author a follow-on.

**Proposed spec sketch (do NOT write this slice — for next-slice planning only):**

```
spec #61 — HomeDashboard composition rules + free-tier study/upgrade surface

§1 Problem Statement
   - Free-user-post-scan symptom (E-048 anchor)
   - Composition gap: P5-S18 static grid + P5-S18b state slot render in parallel
     without coordination

§2 Goals / Non-Goals
   - Fix duplicate-mission-render (state slot + Countdown Mode 2)
   - Add free-tier scan→study/upgrade CTA on /home
   - Out of scope: TeamComingSoon waitlist (already tracked); resume_stale priority
     vs mission_active (defer, low blast radius)

§3 Suppression Rules (LD-1)
   When state-slot widget X renders for the same data domain as static-grid widget Y,
   suppress Y. Initial rule set:
   - if state-slot = mission_active → suppress CountdownWidget Mode 2 mission CTA
     (keep countdown progress bar; drop the mission-CTA footer)
     OR suppress entire CountdownWidget Mode 2 (keep mission-active in state slot)
   - decision: which to keep — needs Dhamo product call

§4 Free-tier study/upgrade widget (LD-2)
   New state name (e.g., 'scan_complete_study_prompt') OR new static widget conditional
   on (plan === 'free' && has_recent_scan && !has_active_mission).
   Copy: "Study the 5 gaps from your last scan" + CTA → /learn (Pro) or PaywallModal (free).

§5 InterviewTarget empty state coexistence (LD-3)
   When InterviewTarget would render its empty state ('No interview company set yet')
   AND CountdownWidget Mode 2 is rendering, suppress InterviewTarget — countdown alone
   is sufficient signal.

§6 Plan-aware state-slot extension (LD-4)
   Extend home_state_service.py state catalog to support a plan-keyed state.
   Either: add 'free_post_scan' state to STATE_PRIORITY, OR plumb context.plan
   into existing widget render decisions in StateAwareWidgets._renderWidget.

§7 Acceptance Criteria
§8 Tests
§9 Out of Scope
```

### Confidence in recommendation: **HIGH**

Verified against:
- `src/pages/HomeDashboard.tsx` (render tree)
- `src/components/home/StateAwareWidgets.tsx` (state-slot logic)
- `src/components/home/widgets/{Countdown,MissionActive,InterviewTarget,LastScan}Widget.tsx` (gate conditions)
- `src/types/homeState.ts` (state enum)
- `src/context/{Auth,Usage}Context.tsx` (persona + plan enums)
- `hirelens-backend/app/services/home_state_service.py` (BE priority order + plan availability)
- specs #34, #35, #40, #44, #46

Symptoms #1-#3 reproducible by code inspection without running the app. Symptoms #4-#5 reproducible by absence-of-grep (no `study_the_gaps` / `scan_complete_study_prompt` / `upgrade_to_study` widget exists on disk).

## 8. What NOT to do (per LD-7)

- **DO NOT** flip E-048 to ✅ — audit done, fix slice not yet shipped.
- **DO NOT** modify HomeDashboard.tsx, StateAwareWidgets.tsx, or any widget file.
- **DO NOT** modify any spec.
- **DO NOT** write spec #61 in this slice. The §3-§6 sketch above is decision-input for the next slice's spec-author prompt.
- **DO NOT** file a new BACKLOG row for findings #6 or #7. Below the PUSHBACK threshold of 3 net-new; both fold into E-048's fix-slice scope.

## 9. SOP-state recap for the audit row

E-048 Notes column update (per Step 5 of prompt):

> Audit shipped `<this-slice>`. Findings: 4 cells contradictory, 3 missing, 0 ambiguous (2 of which are net-new beyond E-048's reported symptom — both fold into fix-slice scope, no separate BACKLOG row filed). Recommended next-slice: **(c) new spec #61** per audit §7. Spec #40 (P5-S18b) is shipped 🟢 — option (b) fold-into-pending was moot. Status stays 🔴 until fix slice ships.

---

*Audit complete. No code changed. No status flipped. No spec written. Next: chat-Claude to greenlight spec #61 author slice (per audit §7) or pick a different fix path.*
