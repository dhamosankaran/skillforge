# SPEC: Free-Tier Limits — 15 Foundation Cards + 3 Interview Qs/month

## Status: Implemented — Spec Backfill Pending (P5-S6)

## Code Pointers
- Interview-question monthly gate: `app/services/usage_service.py` (DB-backed via `usage_logs`; monthly window — NOT Redis-backed as the playbook originally described).
- Foundation-card gate: currently category-level via `Category.source == "foundation"` filter — see `app/services/card_service.py` and `app/services/study_service.py`. Per-user card-count cap (15) is **not yet layered on top** per SESSION-STATE Phase-1 decision log (launch sized for 15 cards total).
- Tests: `tests/test_usage_limits.py` (4 tests, all green).

## Problem
*(to be filled in during P5-S6 backfill)*

## Solution
*(to be filled in during P5-S6 backfill)*

## Acceptance Criteria
*(to be filled in during P5-S6 backfill)*

## Open Questions Flagged by Audit
- Confirm the 3/month value is correct for the business model (SESSION-STATE "Open Decisions").
- Confirm where the 15-Foundation-card wall lives (category filter today; per-user cap TBD).

---
*Placeholder created during P5-S0b on 2026-04-17. Replace with full spec during P5-S6.*
