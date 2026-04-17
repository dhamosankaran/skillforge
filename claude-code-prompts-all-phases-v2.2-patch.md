# SkillForge — Claude Code Prompts (All Phases) — v2.2 PATCH

> **What this is**: A small supplementary patch on top of v2.1, derived from the user-flow diagram audit (new + existing user E2E flows). Adds 5 missing slices and amends 1 spec.
>
> **How to use**: Apply these on top of v2.1. Renumber if needed. Keep v2.1 as the master and treat this as additions.
>
> **Standard prompt header (unchanged)**:
> `Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-N/NN-feature.md.`

---

## Source of these additions

After v2.1 was built, we reviewed two end-to-end user flow diagrams (`new_user_e2e_flow.html` and `existing_user_e2e_flow.html`) and found 5 features promised in the flows that weren't covered in v2.1, plus 1 spec amendment needed to match the flow.

| Patch ID | What | Why it's needed |
|----------|------|-----------------|
| P5-S16-AMEND | Add `interview_target_company` field to User model | New user flow shows Interview-Prepper persona captures "+ company + date", but P5-S16 only added date. |
| P5-S18b | State-aware HomeDashboard logic | Existing user flow says "Smart home dashboard — Persona-aware, **state-aware**". P5-S18 covers persona but not state. |
| P5-S18c | Interview-Prepper guided 5-step checklist | New user flow shows Interview-Prepper Home Dashboard has "Guided 5-step checklist". Not in v2.1. |
| P5-S26b | Paywall dismissal flow + re-engagement | Both flows show paywall has two outcomes (Pay OR "Not now stays free"). Today the paywall just blocks. |
| P5-S26c | Verify Stripe webhook idempotency | Existing user flow has "Idempotent (Phase 4)" annotation, but Phase 4 didn't actually slice this. Needs verification. |

---

## --- INSERT INTO Phase 5D after P5-S16 ---

### P5-S16-AMEND: Spec + Backend Amendment — Add `interview_target_company` 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/34-persona-picker-and-home.md.

The new-user flow promises that Interview-Prepper persona captures BOTH a target date and a target company name (e.g., "Google in 14 days"). The current P5-S16 only added interview_target_date. Amend to add company.

1. Update docs/specs/phase-5/34-persona-picker-and-home.md:
   - In Data Model: add interview_target_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
   - In API Contract: PATCH /api/v1/users/me/persona body now accepts { persona, interview_target_date?, interview_target_company? }
   - In AC: add AC-3b — Interview-Prepper card shows an optional company text input alongside the date picker.

2. Apply the schema change:
   - Add field to User model.
   - Alembic migration: alembic revision --autogenerate -m "add interview_target_company to users"
   - alembic upgrade head
   - Test rollback.

3. Update the PATCH endpoint validator to accept the new field. Reject company strings >100 chars.

4. Tests:
   - test_set_persona_with_company
   - test_company_max_length_enforced
   - test_company_optional_when_persona_is_interview_prepper

5. Run: python -m pytest tests/test_users.py -v

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(persona): add interview_target_company field — closes spec #34 (amendment)"
```

---

## --- INSERT INTO Phase 5D after P5-S18 ---

### P5-S18b: State-Aware HomeDashboard Logic 🔴 PENDING 🆕

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/34-persona-picker-and-home.md.

P5-S18 made the HomeDashboard persona-aware. Now make it state-aware: the widgets shown depend on the user's recent activity, not just their persona.

Create docs/specs/phase-5/40-home-dashboard-state-aware.md:

Problem: A persona-aware dashboard is a good start but doesn't change as the user uses the product. An Interview-Prepper who already started a mission shouldn't see "Start your first mission" — they should see "12 days left, today's cards: 8". A Career-Climber whose streak is at risk should see "Streak at risk — review 1 card to keep your 14-day streak alive."

Solution: A state evaluator that runs on each /home load and emits a prioritized list of "states" the user is in. Widgets render based on those states.

State catalog (add more as needed):
- streak_at_risk: last_review > 18 hours ago AND current_streak >= 3
- mission_active: user has an in-flight Mission Mode (return countdown + today's cards)
- mission_overdue: mission day cards uncompleted past target date
- resume_stale: last ATS scan > 30 days ago
- new_pro_member: upgraded < 7 days ago (show "explore Pro features" tour)
- inactive_returner: last activity 7-30 days ago (show "welcome back, here's what's new")
- first_session_done: just finished first daily review (celebrate, set next-step CTA)
- needs_persona_refresh: persona unchanged for 90+ days AND product use changed (low-pri suggestion to revisit persona)

Implementation:
1. Backend: app/services/home_state_service.py with get_user_states(user_id) → list[str] of active states.
2. Backend: GET /api/v1/home/state returns { persona, states: [...], context: { streak, last_scan_date, active_mission_id, ... } }.
3. Frontend: HomeDashboard calls /api/v1/home/state, maps states → widget components, prioritizes them.
4. Each state has a defined widget. Multiple states can render simultaneously, prioritized by urgency.

Acceptance Criteria:
- AC-1: A user with no recent activity sees the "fresh persona" widget set (same as P5-S18).
- AC-2: A user mid-mission sees the mission widget at top of /home regardless of persona.
- AC-3: A streak-at-risk user sees the streak widget at top with a "review 1 card to save your streak" CTA.
- AC-4: A returning user (gap 7-30 days) sees a welcome-back widget.
- AC-5: State evaluation runs in <100ms (use Redis cache for components like last_review_at).
- AC-6: PostHog: home_state_evaluated (with all active states), home_state_widget_clicked (with state name).

Tests:
- test_streak_at_risk_state_for_dormant_user
- test_mission_active_state_overrides_default
- test_multiple_states_returned_in_priority_order
- test_state_endpoint_responds_under_100ms

Implement after spec is reviewed.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(home): state-aware dashboard logic — closes spec #40"
```

---

## --- INSERT INTO Phase 5D after P5-S18b ---

### P5-S18c: Interview-Prepper Guided 5-Step Checklist 🔴 PENDING 🆕

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The new-user flow shows Interview-Prepper persona's HomeDashboard contains a "Guided 5-step checklist" to land them in their first daily review fast. Build it.

Create docs/specs/phase-5/41-interview-prepper-checklist.md:

Problem: A new Interview-Prepper user lands on /home with persona widgets but no clear sequence. They need a step-by-step path: scan resume → see gaps → pick study category → set mission → first daily review. Without it they bounce.

Solution: A persistent 5-step checklist widget on /home (only for Interview-Prepper persona, only until completed). Each step links to the right screen, marks complete on action, and shows progress (e.g., "2 of 5 done").

Steps:
1. **Scan your resume** — link to /prep/analyze. Marks complete when user uploads + scans.
2. **Review your gaps** — link to /prep/results. Marks complete on visit.
3. **Pick a category to study** — link to /learn/categories filtered by gaps. Marks complete when user views category cards.
4. **Set your Mission** — link to /learn/mission. Marks complete when mission is created.
5. **Do your first daily review** — link to /learn/daily. Marks complete after first review submitted.

Data model:
- onboarding_checklist_progress on User (JSON column or separate table): { resume_scanned: bool, gaps_reviewed: bool, category_picked: bool, mission_set: bool, first_review_done: bool, started_at, completed_at }
- Or compute from existing telemetry — simpler. Use existing PostHog events + DB queries to derive each flag. Recommend computing.

API:
- GET /api/v1/onboarding/checklist → returns the 5 steps with completion state for current user.

Frontend:
- New widget src/components/home/widgets/InterviewPrepperChecklist.tsx
- Renders ONLY when persona === interview_prepper AND not all 5 done.
- Auto-hides 7 days after completion (so it doesn't linger).
- Progress bar + "Skip checklist" link (record skip in PostHog, hide widget).

Acceptance Criteria:
- AC-1: New Interview-Prepper sees 5/5 incomplete checklist on first /home visit.
- AC-2: Completing each step marks it done without page reload (poll on focus, or invalidate query on relevant mutation).
- AC-3: Once all 5 done, widget shows celebration state for 1 visit, then hides.
- AC-4: User can dismiss the checklist via "skip" — recorded but not destructive.
- AC-5: Other personas never see this widget.

PostHog: checklist_shown, checklist_step_completed (with step name), checklist_completed, checklist_skipped.

Tests + manual verification.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(home): Interview-Prepper guided checklist — closes spec #41"
```

---

## --- INSERT INTO Phase 5F after P5-S26 ---

### P5-S26b: Paywall Dismissal Flow + Re-Engagement 🔴 PENDING 🆕

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The user flows show the paywall modal has TWO outcomes: pay OR "Not now (stays free)". Today the paywall likely just blocks the action with no clean dismissal path. Fix.

Create docs/specs/phase-5/42-paywall-dismissal.md:

Problem: When a free user hits a paywall (15-card wall, 3rd interview generation, etc.) and chooses NOT to pay, the current behavior either traps them or reloads the same paywall on next attempt. We need: graceful dismissal, log the intent signal, and intelligent re-prompting.

Solution:
1. Paywall modal always has TWO clear actions: "Upgrade to Pro" (primary) and "Not now" (secondary text link).
2. "Not now" closes the modal and returns the user to where they were, but with the gated feature still locked.
3. Each dismissal is logged with: user_id, paywall_trigger (which limit was hit), timestamp.
4. Re-engagement strategy:
   - Don't show the same paywall again on the next 3 actions of the same type (avoid hostile UX).
   - DO show it on the 4th attempt (the recurring intent is the strongest buy signal we have).
   - After 3 dismissals total in 30 days, drop a "We noticed you've hit Pro features 3 times — here's 30% off your first month" win-back email (re-uses Phase 2 Resend infra).

Data model:
- paywall_dismissals table: id, user_id, trigger (e.g., "card_wall_15", "interview_gen_3", "missing_skills_link"), dismissed_at, action_count_at_dismissal.

Backend:
- POST /api/v1/billing/paywall-dismiss — body: { trigger }. Logs the dismissal.
- GET /api/v1/billing/should-show-paywall?trigger=X — returns { show: bool, attempts_until_next: int, win_back_offered: bool }.
- Service to schedule the win-back email at the 3rd dismissal threshold.

Frontend:
- Update Paywall component to call should-show-paywall before rendering. If false, allow the action.
- "Not now" button calls paywall-dismiss and closes.
- After paywall-dismiss, the gated action is still blocked, but the user gets a gentle inline message ("This is a Pro feature — upgrade anytime from your Profile") instead of another modal.

Acceptance Criteria:
- AC-1: Free user hits 15-card wall → paywall → dismisses → can browse another 3 cards before the wall reappears.
- AC-2: 3rd dismissal in 30 days triggers win-back email (verify in Resend logs).
- AC-3: Pro user never sees the paywall regardless of trigger.
- AC-4: Dismissal counts reset when user upgrades (avoid showing win-back to a Pro user).

PostHog: paywall_shown (existing), paywall_dismissed (with trigger), winback_email_sent, winback_email_clicked, winback_converted.

Tests + manual verification.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(billing): paywall dismissal + win-back — closes spec #42"
```

---

## --- INSERT INTO Phase 5F after P5-S26b ---

### P5-S26c: Verify Stripe Webhook Idempotency 🔴 PENDING 🆕

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The existing-user flow has "Idempotent (Phase 4)" annotated next to Stripe checkout, but Phase 4 didn't explicitly slice webhook idempotency. Without it, a duplicate webhook delivery could double-grant Pro, double-charge a refund, or corrupt the subscription state. This is a real production risk that's silent until it bites.

PASS 1 — AUDIT (no code changes):
1. Read app/api/routes/stripe_webhook.py (or wherever the webhook handler lives).
2. Identify whether each event type checks for prior processing:
   - Does the handler look up event.id against a processed_events table (or Redis set) before acting?
   - If not, the handler is non-idempotent and a duplicate webhook will cause data corruption.
3. Read the Stripe documentation for webhook delivery guarantees: Stripe retries failed webhooks for up to 3 days, sometimes delivers the same event twice on retries.
4. Report findings: which event types are safe, which are vulnerable, severity assessment.

PASS 2 — FIX (after my approval):
5. Create stripe_processed_events table: event_id (PK, varchar), event_type, processed_at.
6. In the webhook handler, before processing each event:
   - Check if event.id exists in stripe_processed_events.
   - If yes: return 200 OK immediately (Stripe stops retrying), log "duplicate webhook ignored".
   - If no: process the event, then INSERT into stripe_processed_events in the same transaction as the side effect (atomic).
7. Use SQL UNIQUE constraint on event_id so concurrent duplicate processing fails safely.
8. Tests:
   - test_first_delivery_processes_event
   - test_duplicate_delivery_ignored
   - test_concurrent_duplicates_handled (race condition test using asyncio.gather)
   - test_atomic_failure_no_partial_processing

9. Manual test in Stripe test mode: trigger a test event, then re-deliver it from the Stripe dashboard, verify only one Pro grant.

10. Backfill: query the last 30 days of webhook events from Stripe API, pre-populate stripe_processed_events so we don't re-process anything historical.

Update SESSION-STATE.md (note: Phase 4 retroactive hardening done).
Commit: git add -A && git commit -m "fix(billing): make Stripe webhook handler idempotent — closes spec retroactively"
```

---

# ═══════════════════════════════════════════
# AMENDMENTS TO v2.1 STATUS TABLE
# ═══════════════════════════════════════════

When applying this patch, update the Phase 5 Status table in v2.1 to add:

| # | Feature | Status |
|---|---------|--------|
| 5.27 | Interview-Prepper company field on persona | 🔴 PENDING (P5-S16-AMEND) |
| 5.28 | State-aware HomeDashboard logic | 🔴 PENDING (P5-S18b) |
| 5.29 | Interview-Prepper guided 5-step checklist | 🔴 PENDING (P5-S18c) |
| 5.30 | Paywall dismissal + win-back | 🔴 PENDING (P5-S26b) |
| 5.31 | Stripe webhook idempotency | 🔴 PENDING (P5-S26c) |

---

# ═══════════════════════════════════════════
# OPEN DECISIONS RAISED BY THE FLOW AUDIT
# ═══════════════════════════════════════════

These are NOT slices — they're decisions you (Dhamo) need to make before the relevant slices run. Add them to SESSION-STATE.md "Open Decisions Awaiting Dhamo".

| Decision | Context | Affected slice |
|----------|---------|----------------|
| Persona switch UX: full-page reroute or modal? | Existing-user flow shows it as a modal. P5-S17 currently says reroute to /persona. Modal is lighter; reroute is consistent. | P5-S17 |
| Does daily review consume the free 15-card budget, or is the budget browse-only? | If consumed, Career-Climber free users hit the wall in 3 days. If browse-only, daily review is unlimited for free users. | Affects P5-S22 (Pro-gating) and the Phase 1 paywall logic |
| Auto-save scan to tracker — fully automatic or "Save?" prompt? | P5-S5 spec backfill needs this clarified. Existing-user flow implies automatic. | P5-S5 |
| Email deep links from old Phase 2 emails — do redirects in P5-S13 cover them? | Old emails point at /study/daily etc. Need 301s. | P5-S13 |

---

*v2.2 patch — generated 2026-04-17 from new_user_e2e_flow.html and existing_user_e2e_flow.html audit.*
