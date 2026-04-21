# Spec #51 — AI Resume Rewrite: Section Preservation + Token-Budget Fix

**Status:** Draft — awaiting implementation slice
**Owner:** Dhamo
**Created:** 2026-04-20
**Phase:** 5
**Closes:** BACKLOG row B-001 (P0, `ats-scanner`, source slice P5-S9) — **on implementation ship, not on this spec.**
**Depends on:** Investigation report `docs/audit/2026-04-b001-rewrite-investigation.md` (2026-04-21; commit `92b7bde`). All §-references to "the investigation" in this spec point there.
**Supersedes (partial):** Spec #47 (Resume Rewrite: Content Preservation). Spec #47 closed the v2.1 playbook flag by pinning the P5-S9 input-truncation fix with a prompt-contract regression test, and asserted "the bug does not reproduce on main." B-001 was subsequently re-filed as P0 🔴 after production reports, and the 2026-04-21 investigation identifies a different dominant root cause (output-side token-budget contention under Gemini 2.5 Pro thinking budget), which #47 did not cover. Spec #51 is the live-fix spec; #47's preservation-contract regression test (AC-2) remains valid and is inherited by §8 below.

---

## 1. Problem Statement

**User-facing symptom.** Users running **Rewrite Resume** on `/prep/rewrite` receive an output that reads like a summary, not a full rewritten resume. Original sections (work history, education, certifications, projects) are dropped or collapsed. On a 4-page senior-engineer resume, later sections disappear entirely. Premium users who paid for the AI rewrite are the primary reporters.

**Root cause (from investigation §4, probability ranking).** The dominant cause is **output-side token-budget truncation**: the call passes `max_tokens=8000` to Gemini 2.5 Pro, but Gemini 2.5 Pro's thinking budget consumes tokens from the same pool. Under long resumes or complex rewrites the thinking budget eats 3k–6k tokens, leaving only 2k–5k for output — insufficient for a complete 2-page rewrite and well short for 4-page resumes. The router already carries an explicit `logger.warning` for this failure mode on other reasoning-tier calls (`llm_router.py:81-93`). Input truncation at `[:40000]` characters and the absence of structured output (the `RewriteResponse.sections` field ships empty every time, breaking PDF/DOCX export paths that iterate it) are secondary issues this spec must also resolve. See investigation §4 for the full probability breakdown and §3 for the latent export-path regression.

---

## 2. Scope

**In scope.**
- `POST /api/rewrite` and `POST /api/v1/rewrite` (the v1 route is a pure re-export; both URL surfaces hit the same handler — investigation §1).
- `app/services/gpt_service.py::generate_resume_rewrite` (the live path used by the handler).
- Prompt wording, output-shape contract, and token-budget strategy for the above.
- `src/pages/Rewrite.tsx` + `src/components/rewrite/ResumeEditor.tsx` rendering path (including the currently-dead `ResumePreview` branch and the currently-broken PDF/DOCX export paths that iterate `RewriteResponse.sections`).
- `RewriteResponse` Pydantic schema in `app/schemas/responses.py`.
- Regression tests for §8.

**Out of scope.**
- `app/services/ai_service.py::generate_resume_rewrite` — dormant duplicate not imported by any live route (investigation §1 "File Inventory"). Tracked under S47-defer (spec #47 §7 "Out of Scope") for Phase-6 cleanup.
- `POST /api/v1/resume/{id}/optimize` (`app/api/v1/routes/resume.py:66`) — dormant enterprise-only endpoint, no frontend caller.
- Authenticating `/api/rewrite` — called out as out-of-scope in spec #09 §Out of Scope and spec #47 §7; still tracked.
- Restructuring resumes for ATS (§3 LD-1), reordering sections (§3 LD-2), `template_type` / `major` prompt influence (the service accepts these args but ignores them — see investigation §2; addressing is out of scope for this slice).

---

## 3. Locked Decisions

> These are inputs to the spec. They are not re-debated in the implementation slice. If Dhamo overrides any of these before the implementation slice starts, the implementation slice amends this spec first.

**LD-1 — Preserve section structure.** Rewrite **MUST** preserve the original section structure. No silent restructuring for ATS optimization. A candidate's unique sections ("Selected Publications", "Patents", "Teaching") are preserved even if a generic ATS template would omit them. Restructuring is a separate, opt-in feature tracked as a future backlog item, not this slice.

**LD-2 — Preserve section ordering.** Rewrite **MUST** preserve the original section ordering. No silent reordering ("Skills before Experience" etc.). Silent reordering is indistinguishable to a skim-reading user from "my section was dropped" — same support cost, same trust hit.

**LD-3 — Full rewrite is the default; per-section regen is a post-result affordance.** The **"Rewrite Resume"** button on `/prep/rewrite` performs a full rewrite. On the results view, each rendered section carries a **"↻ Regenerate this section"** control that requests a rewrite of that one section only. Both modes share the same underlying prompt strategy (same preservation rules, same temperature, same router task name family — §6 specifies the exact task-name split). Per-section regen is a power-user iteration mode layered on top of the default full-rewrite UX; it is not a fallback or replacement.

**LD-4 — Token-budget fix strategy: OPEN; implementation slice picks.** The three candidate paths are laid out in §7 with trade-offs. The implementation slice picks the winner based on empirical measurements (prompt A/B against a fixture set of 1-page, 2-page, and 4-page resumes). The spec does not pick; attempting to pick without measurement risks locking in the wrong answer.

**LD-5 — Response shape: populate `sections` AND keep `full_text`. (New in this spec.)** `RewriteResponse.sections` moves from "always empty list" to "populated array of `RewriteSection`." `full_text` is retained for the one-click copy-to-clipboard UX. Both are served from the same LLM response: the LLM is asked for structured JSON (section-keyed), the service joins the sections into `full_text` server-side. Rationale:
  1. **Unblocks export paths.** `Rewrite.tsx` PDF export (lines 86–309) and `utils/docxExport.ts` DOCX export both iterate `r.sections` and currently produce empty documents (investigation §3 "Export-path regression"). Populating `sections` fixes them with zero FE code change to those export functions.
  2. **Unblocks per-section regen (LD-3).** Per-section regen needs addressable sections; `full_text` as a single markdown blob is not addressable without re-parsing.
  3. **Machine-verifiable preservation contract.** With structured output we can post-validate "every section we sent in is a section we got out" (regression-check-in-code), a stronger guarantee than prose-rule adherence.
  4. **`full_text` retained for copy-paste.** Users who want to paste into a different editor still want one blob. Cheap to provide: `"\n\n".join(section.to_markdown() for section in sections).strip()` on the service side.

  If Dhamo overrides LD-5 (e.g., "drop `sections`, keep only `full_text`"), the implementation slice must also delete the PDF/DOCX export paths or gate them off — per AC-6 no path may be left iterating a field that BE ships empty.

---

## 4. Acceptance Criteria

> All ACs are test-gated (§8 Test Plan maps each AC to a test). No live-LLM calls in CI tests — mock `generate_for_task` and assert against the prompt / the mocked response.

- **AC-1 — 3-page resume, 6 sections, order preserved.** Given a 3-page resume fixture with sections `[contact, summary, experience, education, skills, projects]`, the rewrite output contains all 6 sections in exactly that order. No extra sections, no dropped sections, no reordering.

- **AC-2 — 2-page resume, 4 sections, exact set preserved.** Given a 2-page resume fixture with `[contact, summary, experience, skills]` (no education, no projects), the rewrite output contains exactly those 4 sections in that order. The LLM **MUST NOT** add an "Education" section or any other section the original lacked.

- **AC-3 — 4-page resume, no truncation.** Given a 4-page senior-engineer fixture (`resume_text` length ≥ 10,000 chars, ≥ 8 sections including late-position sections like Certifications and Awards), the rewrite output is not truncated mid-section, and every original section appears in the output. **This is the token-budget regression AC.** The implementation slice's chosen token strategy (§7 / LD-4) is judged against this AC.

- **AC-4 — Per-section regen targets one section only.** Invoking "↻ Regenerate this section" on section N returns a rewritten version of section N. In the rendered UI state after regen, sections `[0 .. N-1]` and `[N+1 .. end]` are byte-for-byte unchanged from pre-regen. No other section's text is mutated.

- **AC-5 — Structured error on truncation / parse failure.** If the LLM response is detected as truncated (finish_reason indicates MAX_TOKENS, or structured-output JSON is malformed / incomplete), the API returns HTTP 502 with body:
  ```json
  {
    "detail": {
      "error": "rewrite_truncated" | "rewrite_parse_error" | "rewrite_llm_error",
      "message": "<human-readable explanation>",
      "retry_hint": "retry" | "reduce_input" | "contact_support"
    }
  }
  ```
  The frontend shows a user-visible error toast and does not render a partial-success state. Silent partial success is the worst possible outcome — users can't tell a half-rewrite from a whole one, so they ship the half.

- **AC-6 — Latent-broken-sweep resolution (cite investigation §7).** By the end of the implementation slice, every FE path that iterates `RewriteResponse.sections` either (a) works correctly because `sections` is populated per LD-5, or (b) is deleted / gated off. Specifically:
  - `ResumePreview` (`ResumeEditor.tsx:19-97`) — **EITHER** rendered via the populated `sections` AND made the default renderer when `sections.length > 0` **OR** deleted entirely.
  - PDF export (`Rewrite.tsx:86-309`) — **EITHER** produces a non-empty PDF over the populated sections **OR** the export button is removed.
  - DOCX export (`utils/docxExport.ts`) — same alternatives.

  No path may be left iterating `sections` while BE ships empty. The implementation slice audits these three paths (call graph: "who reads `.sections`?") and closes each one explicitly; the slice's PR description must enumerate the closure choice per path.

---

## 5. Response-Shape Decision (LD-5 rationale in full)

Current `RewriteResponse` schema (`app/schemas/responses.py:89-110`):

```python
class RewriteResponse(BaseModel):
    header: RewriteHeader
    sections: List[RewriteSection]
    full_text: str
    template_type: str = "general"
```

**Investigation finding (§3).** BE currently populates `header = RewriteHeader(name="", contact="")` (empty stub), `sections = []` (always), `full_text = markdown.strip()` (the entire LLM output as one string). FE's `ResumeEditor.tsx:186` therefore always enters the markdown branch, and PDF/DOCX export paths (which iterate `sections`) silently produce empty documents.

**Options considered.**
1. **Populate `sections` + keep `full_text`.** Chosen (LD-5). Powers structured rendering, exports, and per-section regen; keeps copy-to-clipboard working.
2. **Keep only `full_text`, remove `sections` from the type.** Rejected: requires deleting PDF/DOCX exports AND `ResumePreview`, AND loses per-section regen addressability. A contract regression dressed up as simplification.
3. **Populate `sections`, deprecate `full_text`.** Rejected: breaks the "copy my whole resume" UX without corresponding user gain. `full_text` is cheap to derive server-side.

**Author recommendation (still subject to Dhamo review):** LD-5 as stated — populate `sections`, keep `full_text`. Both served from one LLM call via structured-output (`json_mode=True` on the router with a schema). If Dhamo overrides before implementation, the implementation slice amends this spec first.

---

## 6. API Contract (Draft — implementation slice finalizes)

### 6.1 Full rewrite (unchanged endpoint)

```
POST /api/v1/rewrite
Content-Type: application/json

Request (RewriteRequest — unchanged):
  {
    "resume_text": "<string>",
    "job_description": "<string>",
    "template_type"?: "<string>",
    "major"?: "<string>"
  }

Response (RewriteResponse — sections now populated per LD-5):
  {
    "header": { "name": "<string>", "contact": "<string>" },
    "sections": [
      { "title": "<string>", "content": "<string>", "entries": [ /* RewriteEntry[] */ ] },
      ...
    ],
    "full_text": "<string — sections joined>",
    "template_type": "<string>"
  }
```

Router task name: `resume_rewrite` (reasoning tier; unchanged — in `REASONING_TASKS` frozenset in `llm_router.py`).

### 6.2 Per-section regenerate (NEW per LD-3)

```
POST /api/v1/rewrite/section
Content-Type: application/json

Request:
  {
    "section_id": "<string — index or stable id>",
    "section_title": "<string — e.g. 'Experience'>",
    "section_text": "<string — the original section text the user wants rewritten>",
    "jd_text": "<string — the job description for targeting>",
    "context"?: {
      "missing_keywords"?: ["<string>", ...],
      "target_role"?: "<string>"
    }
  }

Response:
  {
    "section": { "title": "<string>", "content": "<string>", "entries": [ ... ] }
  }

Errors: same error envelope as AC-5.
```

Router task name candidate: `resume_rewrite_section` (fast or reasoning tier — implementation slice decides; fast tier is a good default because the input is bounded to one section, which also cheaply sidesteps the LD-4 token-budget problem for this path). The implementation slice must add the task name to the appropriate `*_TASKS` frozenset in `llm_router.py` before first use.

**Prompt strategy.** Both endpoints share the preservation-rule spine: "preserve the section structure of what's given, improve bullets and language, do not fabricate." The full-rewrite prompt additionally carries "do not add sections not in the original" and "do not drop sections from the original." The section-regen prompt carries "output exactly one section matching the input section's title and semantic content." Exact wording is implementation-slice detail, but both must pass spec #47's AC-2 preservation-contract regression test (inherited here as a baseline — see §8).

---

## 7. Token-Budget Strategy Options (LD-4 — do not pick in this spec)

Per investigation §6 Q4: fixed `max_tokens=8000` on Gemini 2.5 Pro is brittle across the range of resumes users upload. The three candidate paths:

| Option | Description | Latency | Cost | Quality | Complexity |
|---|---|---|---|---|---|
| **A** | Dynamic `max_tokens` sized from input length (e.g. `max(8000, 2 × input_tokens)`), with an explicit `thinkingBudget` cap on the Gemini call to stop the thinking pool from starving the output pool. | **Low** (single call, same shape) | **Low** (one generation) | **Medium** (still one-shot; if model decides to summarize we lose the same way) | **Low** (router change + one call-site change) |
| **B** | Per-section chunking: split resume into detected sections, call the LLM once per section with a bounded per-call `max_tokens`, stitch back server-side. | **Medium** (parallelizable via `asyncio.gather`; wall-clock close to A but more API calls) | **Medium** (N calls instead of 1; token overhead for per-call system prompt) | **High** (each call has ample budget; preservation-by-construction because we stitch exactly the sections we sent in) | **Medium** (section splitter, stitcher, error handling if one section fails) |
| **C** | Model swap to a reasoning model without thinking-budget contention — e.g. Gemini 2.5 Flash with `thinkingBudget=0`, or OpenAI `gpt-4o` routed via the existing multi-provider router. | **Variable** (depends on model) | **Variable** (Flash cheaper, gpt-4o roughly comparable) | **Unknown** (Flash is less capable than 2.5 Pro for long-form; gpt-4o is comparable to 2.5 Pro and has a larger practical output pool) | **Medium** (env-var flip per-tier exists today; the hard part is validating output quality against the current Gemini 2.5 Pro baseline) |

**Author's lean (not binding on the implementation slice).** B as primary, A as safety net. Rationale: B's per-section bounded budget is preservation-by-construction — we literally can't drop a section because the stitcher fails loudly if any section call fails, and each call has enough tokens for one section. A is a useful fallback for cases where splitting isn't worth it (very short resumes) and as a cheaper path under load. C is the escape hatch if A+B both underperform on quality.

**Implementation slice MUST:**
1. Run empirical measurements against a fixture set of 1-page / 2-page / 4-page resumes with each option.
2. Pick the winner and document the choice in the slice's CHANGELOG / SESSION-STATE entry with the measurement numbers.
3. Update `BACKLOG.md` B-001's Notes column with the chosen option before closing.
4. **Not** pick based on intuition alone — this is a user-facing quality surface, the cost of picking wrong is another production B-001.

---

## 8. Regression Test Plan

### 8.1 Backend

Extend `tests/services/test_resume_rewrite.py` (the existing file created in P5-S9 / spec #47):

| Test | AC | Notes |
|---|---|---|
| `test_full_resume_reaches_llm_prompt` (existing, P5-S9) | AC-1 input-side | Already green. Keep. |
| `test_prompt_includes_preservation_rules` (existing, spec #47) | AC-2 prompt-contract | Already green. Keep. |
| `test_3_page_resume_preserves_6_sections_in_order` (**new**) | AC-1 | Fixture: 3-page resume with `[contact, summary, experience, education, skills, projects]`. Mock `generate_for_task` to return a structured response including all 6 sections in order. Assert `response.sections` length == 6, titles in order, each section non-empty. |
| `test_2_page_resume_preserves_exact_section_set` (**new**) | AC-2 | Fixture: 2-page resume with `[contact, summary, experience, skills]`. Mock returns structured response with exactly those 4. Assert no "Education" / "Projects" was injected. A variant of this test uses a mock that *tries* to add an "Education" section, asserting the service surfaces this as an AC-5 validation error (post-validation catches hallucinated sections) — implementation-slice decision on whether to enforce strictly or log-and-pass. |
| `test_4_page_resume_no_truncation` (**new**) | AC-3 | Fixture: senior-engineer resume ≥ 10,000 chars with ≥ 8 sections. The test is chosen per the LD-4 winning strategy: for Option B, assert N section calls happen and the stitch returns all N sections; for Option A, assert `max_tokens` parameter to the router is ≥ the heuristic result for the fixture size; for Option C, assert the router dispatches to the chosen provider/model. In all three cases assert `response.sections` covers every fixture section. |
| `test_per_section_regenerate_returns_one_section` (**new**) | AC-4 backend side | POST `/api/v1/rewrite/section` with a single section's text; assert response contains exactly one section with matching title. |
| `test_rewrite_truncated_returns_502_structured_error` (**new**) | AC-5 | Mock the router to return a response flagged as truncated; assert response is 502 with the AC-5 error envelope. Variants for `rewrite_parse_error` and `rewrite_llm_error`. |

### 8.2 Frontend

Extend `tests/pages/Rewrite.test.tsx` (or create if absent):

| Test | AC | Notes |
|---|---|---|
| `renders_all_sections_from_fixture_response` (**new**) | AC-1, AC-6 | Mock the API to return a 6-section `RewriteResponse`; assert 6 `<section>` markers are rendered in order. |
| `per_section_regenerate_mutates_only_target_section` (**new**) | AC-4 frontend side | Render a 4-section result, click "↻ Regenerate" on section 2, mock the API to return a new section 2; assert sections 0/1/3 are byte-for-byte unchanged, section 2 text is the new text. |
| `pdf_export_iterates_populated_sections` (**new**, AC-6) | AC-6 | Mock `generatePdf` / the export helper; assert it's invoked with a non-empty sections array. If the implementation slice instead **deletes** PDF export per AC-6(b), this test is replaced with `pdf_export_button_not_rendered`. |
| `docx_export_iterates_populated_sections` (**new**, AC-6) | AC-6 | Parallel to PDF. |
| `structured_error_shown_on_truncation` (**new**) | AC-5 FE side | Mock API to return 502 AC-5 error; assert the error toast / banner is rendered, the results view is not. |

**No live LLM calls in any test.** All router calls are mocked. Integration tests (if any) must be gated behind `@pytest.mark.integration` per CLAUDE.md Rule 13 and run locally pre-merge.

---

## 9. Telemetry

**New PostHog events (add to `.agent/skills/analytics.md` during the implementation slice).**

| Event | Surface | Properties | When |
|---|---|---|---|
| `rewrite_requested` | FE | `{resume_char_length, jd_char_length, template_type?}` | User clicks "Rewrite Resume" |
| `rewrite_succeeded` | BE | `{resume_char_length, sections_count, output_char_length, strategy}` where `strategy ∈ {full, per_section_stitched, model_swap}` per LD-4 | Response returns 200 |
| `rewrite_failed` | BE | `{reason, resume_char_length}` where `reason ∈ {truncated, parse_error, llm_error}` matching AC-5 | Response returns 502 |
| `rewrite_section_regenerated` | FE | `{section_title, section_char_length_before, section_char_length_after}` | User clicks "↻ Regenerate this section" and the response returns 200 |

**Operational logging (first week post-ship).** Log `resume_text` length and rewrite output length on every successful call for the first 7 days. Review the histogram to validate the LD-4 strategy choice empirically and catch any ceiling regressions (e.g., "strategy A is still truncating at the 90th percentile"). Remove the verbose logging once the distribution is understood.

---

## 10. Migration / Rollout Notes

- **No DB migration needed.** All changes are in the request/response layer and the LLM service path.
- **`RewriteResponse.sections` contract change** is non-breaking for the FE: existing code that ignored `sections` keeps working; export paths that iterated it come back to life. The implementation slice should still verify no other `sections` consumer exists via a code-reality audit before ship (CLAUDE.md Rule 16 step-1 audit).
- **New endpoint `POST /api/v1/rewrite/section`** (LD-3) — document in the implementation slice's CODE-REALITY regeneration; add to AGENTS.md Routes Table.
- **Router task name addition** — if the implementation slice chooses to register `resume_rewrite_section` as a new task, it must be added to the appropriate `*_TASKS` frozenset in `llm_router.py` in the same commit.
- **No feature flag.** This is a bug fix to a broken live feature, not a new experimental feature. Deploy directly to main per CLAUDE.md Rule 9.
- **B-001 closure** happens on implementation-slice merge, not on spec merge. The implementation slice must include the `closed by <sha> on <YYYY-MM-DD>` line in `BACKLOG.md` per CLAUDE.md Rule 15.

---

## 11. Out-of-Spec Follow-Ups (tracked, not blocking)

- **`app/services/ai_service.py::generate_resume_rewrite`** — dead duplicate of `gpt_service.py::generate_resume_rewrite`. Remains tracked under S47-defer (spec #47 §7 "Out of Scope"), unchanged by this slice.
- **`template_type` and `major` prompt integration.** Both args are accepted by `generate_resume_rewrite` but never surfaced into the prompt (investigation §2 "Pins a template? No"). Fixing is out of scope here — the primary user complaint is content loss, not templating; templating is a separate UX slice.
- **`/api/rewrite` (unauth) → `/api/v1/rewrite` migration.** Flat legacy `/api/*` routes are tracked as Phase-6 cleanup per the `[5.17-follow] flat /api/* legacy-route cleanup` item in SESSION-STATE.
- **Investigation §7 "what would change the hypothesis."** Items 1–6 (log-grep, instrumented logger, manual repros with long/short/multi-column fixtures, section-dict comparison) are diagnostic aids the implementation slice **should** run during its empirical-measurement step (LD-4 §7) but are not acceptance criteria.
- **Spec #47 drift flag (surfaced to Dhamo in pre-flight of this slice):** Spec #47 (2026-04-19) asserted B-001's underlying bug no longer reproduces on `main` after P5-S9. B-001 was subsequently re-opened P0 🔴 and the 2026-04-21 investigation confirms the bug still manifests via a different dominant root cause (output-side thinking-budget contention, export-path regression, empty `sections`). Spec #47's AC-2 preservation-contract regression test remains valid and is inherited here; the "v2.1 flag closed" claim in #47 §8 is stale relative to the live user-reported symptom. Not blocking this spec; flag for SESSION-STATE drift ledger.

---

## 12. R15

**B-001 is NOT closed by this spec slice.** This spec is the design contract; the follow-on implementation slice closes B-001 when it ships the fix and the AC-1…AC-6 tests are green on CI. On implementation-slice merge, `BACKLOG.md` B-001 status flips 🔴 → ✅ with the standard `closed by <commit-sha> on <YYYY-MM-DD>` annotation.
