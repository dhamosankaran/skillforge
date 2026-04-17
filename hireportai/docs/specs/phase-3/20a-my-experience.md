# SPEC: "My Experience" AI Generation

## Status: Implemented — Spec Backfill Pending (P5-S11)

## Code Pointers
- Service: `app/services/experience_service.py`.
- Pre-existing full spec at `docs/specs/phase-3/22-my-experience.md` — this placeholder exists only to close the `20a` slot the playbook references. During P5-S11 backfill, consolidate the two into one spec and delete the duplicate.
- Known-broken: the Profile-page "Generate My Experience" button is a silent-failure bug per SESSION-STATE. Fix slice: P5-S11.
- Profile page: `src/pages/Profile.tsx`.

## Problem
Duplicate placeholder for numbering alignment only.

## Solution
Fold into the existing `22-my-experience.md` during P5-S11. Either:
- Renumber `22-my-experience.md` → `20a-my-experience.md` and delete this file, OR
- Delete this placeholder and update the playbook to reference `22-my-experience.md`.

---
*Placeholder created during P5-S0b on 2026-04-17. Resolve duplication during P5-S11.*
