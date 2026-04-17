# SESSION-STATE.md
## Current Status
Last updated: 2026-04-16
Phase: 1
Current session: P1-S1a
Last completed slice: P0-S7 — CI/CD Pipeline (Phase 0 complete)
Next slice to run: P1-S1a — Schema closeout + soft-delete filter test

### Pending slices
- **P1-S1a** — Schema closeout + soft-delete filter test (~25–30 min)
  - Add `Category.tags` JSON column + Alembic migration
  - Patch `extract_cards.py` to seed `tags=[]`
  - Add partial index migration on `cards (category_id) WHERE deleted_at IS NULL`
  - Add soft-delete filter integration test
- **P1-S1b** — ANN index + extraction unit tests (~25–30 min)
  - HNSW migration on `cards.embedding` (IVFFlat fallback if pgvector < 0.5.0)
  - UUID5 determinism unit test
  - `_synthetic_embedding` unit test
  - EXPLAIN-plan integration test verifying the ANN index is used
- **P1-S2** — (existing) Embeddings generation hardening / cards API polish

## Phase Completion Tracker
- Phase 0: ✅ Complete (S1–S8)
- Phase 1: 🔄 In Progress (S1 spec rewritten 2026-04-16; split into S1a/S1b; implementation pending)
- Phase 2–4: ⬜ Not started

## Decisions Made
| Decision | Rationale | Date |
|----------|-----------|------|
| Free tier limit reduced from 15 to 5 Foundation cards | Original 15 was sized for a 177-card library; with 15 total cards in launch deck, 15-card free tier = no paywall. 5 keeps a meaningful free-vs-Pro distinction. Will revisit when library grows past 50 cards. | 2026-04-16 |
| Option A on content scaling — accept 15-card reality, defer bulk authoring | Content creation throughput (5–12 hours admin review for 150 cards) made Option B a multi-week side quest; Option C (defer paywall) loses Phase 1 revenue signal; Option A keeps Phase 1 on-plan with an honest pricing story (feature-driven Pro + growing library). | 2026-04-16 |
| P1-S1 split into P1-S1a + P1-S1b | Original scope (3 migrations + 3 tests + extract_cards patch) estimated 55–70 min — exceeds the 30-min slice budget. Split along theme: S1a = schema + soft-delete; S1b = ANN index + extraction tests. | 2026-04-16 |

## Enhancement Status
- ENH-1 LLM router: ⬜ (build in P1-S4)
- ENH-2 Geo pricing: ⬜ (build in P1-S22)
- ENH-3 IP blocking: ⬜ (build in P1-S19)
- ENH-4 Card soft-delete: 🔄 (Card.deleted_at column exists; filter test + partial index pending in P1-S1a)
- ENH-5 Design system: ⬜ (build in P3-S3)
- ENH-6 Free tier interview limits: ⬜ (build in P1-S19)
- ENH-7 Tracker auto-populate: ⬜ (build in P1-S20)
- ENH-8 Resume/cover letter fix: ⬜ (build in P3-S7)

## Future Considerations

### Content scaling timeline
- Launch: 15 cards (current state from cards.js)
- Pre-launch additions: user has a separate content plan to add more cards before paid launch
- Phase 3: admin panel + AI card generation enables ongoing content scaling
- Phase 1 paywall sized for current library (5 free / 15 total); revisit limits when library > 50

### Free tier gating code surface area (for Task 1.12)
The "5 Foundation cards" cap does not yet exist in code. Today's gate is category-level only:
- `app/services/card_service.py` — 6 call sites filtering on `Category.source == "foundation"`
- `app/services/study_service.py` — 4 call sites with the same filter
- `app/api/v1/routes/study.py:66` — docstring reference
- `.agent/skills/testing.md:10` — `client_free_tier` fixture

Task 1.12 will need to layer a per-user card-count cap on top of these filters.

## What Was Built Last Session
- Phase 0 closed (S7 CI/CD green; S8 partial items rolled into Phase 1)
- Card-extraction integration tests marker-gated (`-m "not integration"` in CI)
- Latest commit: `50f06f5 chore: close out P0-S2 — Phase 0 complete, advance SESSION-STATE to P1-S1`

## Known Issues
- `docs/specs/phase-1/03-card-extraction.md` was stale (said 177 cards, Done status). Rewritten 2026-04-16 to reflect reality (15 cards / 14 categories), marked partially-done, split work into S1a/S1b.
- Card-extraction skill file (`.agent/skills/card-extraction.md`) still says "177 study cards" — update when the deck is authored post-P1 UX.

## Start-of-Next-Session Prompt
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Continue with P1-S1a per `docs/specs/phase-1/03-card-extraction.md` "Work Remaining — P1-S1a" checklist.
