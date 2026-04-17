# SPEC: Custom Domain + SSL + Stripe Go-Live

## Status: Complete — Spec Backfill Pending (P4-S4 retrospective)

## Naming Note
The playbook §3.3 reserves number `25` for this spec, but `25-performance-hardening.md` already occupies that slot. This placeholder uses `25a` to avoid the collision. Rename to `25` during P5-S0b cleanup only if `25-performance-hardening.md` is renumbered too.

## Code / Runbook Pointers
- Ops runbook: `docs/runbooks/custom-domain.md`.
- Stripe go-live runbook: `docs/runbooks/stripe-go-live.md`.
- Backup + DR runbook: `docs/runbooks/backup-restore.md`.
- Completed in slice P4-S4 per SESSION-STATE "Recently Completed".
- Domain: `theskillsforge.dev` (per AGENTS.md + local-setup-guide).

## Problem
*(to be filled in during P4-S4 retrospective / P5 housekeeping)*

## Solution
*(to be filled in — domain DNS setup, Vercel + Railway SSL, Stripe live-keys cutover, CORS origin update)*

## Acceptance Criteria
- `curl https://theskillsforge.dev/health` → 200.
- Stripe live keys verified end-to-end (test purchase refunded).

## Open Audit Items
- P4-S4 shipped without a spec at the time (only runbooks). This placeholder closes the documentation gap.

---
*Placeholder created during P5-S0b on 2026-04-17. Fill in during Phase 5 housekeeping (H.2 Playbook v3 rollup).*
