# SPEC: IP Registration Blocking — max 2 accounts per IP per 30 days

## Status: Implemented — Spec Backfill Pending (P5-S4)

## Code Pointers
- Logic lives **inline** in `app/api/v1/routes/auth.py` (no dedicated service module; the playbook originally proposed `app/services/registration_guard.py`).
- Constants: `_MAX_REGISTRATIONS_PER_IP = 2`, `_REGISTRATION_WINDOW_DAYS = 30`.
- Storage: DB table `registration_logs` via `app/models/registration_log.py` + migration `f75789e4967f_add_registration_logs_table.py`. **NOT** Redis, despite the playbook's original spec.
- Client IP helper: `_client_ip(request)` — reads `X-Forwarded-For` then falls back to `request.client.host`.
- Tests: `tests/test_registration_limit.py` (green, including "old registrations beyond 30 days don't count").

## Problem
*(to be filled in during P5-S4 backfill)*

## Solution
*(to be filled in during P5-S4 backfill)*

## Acceptance Criteria
*(to be filled in during P5-S4 backfill)*

## Known False-Positive Risk
- Shared-IP environments (corporate NAT, college dorms, cafes) can trip the limit. No bypass procedure exists today. Flag for P5-S4 design.

---
*Placeholder created during P5-S0b on 2026-04-17. Replace with full spec during P5-S4.*
