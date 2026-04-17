# SPEC: Job Tracker Auto-Populate from ATS Scan

## Status: Implemented — Spec Backfill Pending (P5-S5)

## Code Pointers
- Service: `app/services/tracker_service_v2.py` (note the `_v2` suffix — not `tracker_service.py` as the playbook prompt names it).
- Model: `app/models/tracker.py` (`TrackerApplicationModel`, table `tracker_applications_v2`).
- Migration: `alembic/versions/e4eab11b8e33_add_scan_id_skills_matched_skills_.py` (adds `scan_id`, `skills_matched`, `skills_missing` columns).
- Scan-triggered creation path: v1 `/api/v1/analyze` handler — see `app/api/v1/routes/analyze.py`.
- Tests: `tests/test_tracker_orm.py`, `tests/test_tracker_scan.py`.

## Problem
*(to be filled in during P5-S5 backfill)*

## Solution
*(to be filled in during P5-S5 backfill)*

## Acceptance Criteria
*(to be filled in during P5-S5 backfill)*

## Open Questions Flagged by Audit
- Auto-create vs "Save?" prompt (SESSION-STATE "Open Decisions") — existing-user flow currently auto-creates.

---
*Placeholder created during P5-S0b on 2026-04-17. Replace with full spec during P5-S5.*
