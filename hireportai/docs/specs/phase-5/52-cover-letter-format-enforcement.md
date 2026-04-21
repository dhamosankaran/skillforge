# Spec #52 — Cover Letter: Format Enforcement via Structured Output

**Status:** Shipped
**Owner:** Dhamo
**Created:** 2026-04-21
**Phase:** 5
**Closes:** BACKLOG row B-002 (P0, `interview`, source slice P5-S10) — **on implementation ship, not on this spec.**
**Depends on:** Investigation report `docs/audit/2026-04-b002-cover-letter-investigation.md` (2026-04-21; commit `010fe8b`). All §-references to "the investigation" in this spec point there.
**Structural template:** Spec #51 (AI Resume Rewrite: Section Preservation) — same shape (Mode-4 spec, structured-output fix, AC-5 error envelope, `thinking_budget` cap). Transfers and non-transfers from #51 are enumerated in §3 and §11.

---

## 1. Problem Statement

**User-facing symptom.** Users running **Generate Cover Letter** on `/prep/rewrite` (cover-letter tab) receive output with format issues: markdown headers leaking through, body paragraphs merged into a wall of text, or missing blocks (greeting, signoff, signature) entirely. Format compliance is probabilistic because the LLM is asked to obey a 14-step structural prompt but nothing downstream validates compliance.

**Root cause (investigation §4, dominant branch).** `CoverLetterResponse.cover_letter: str` is a single free-form string with **prompt-only** format enforcement — no structured output, no parse-time validation, no structural schema. Any model non-compliance with the prompt's negative instructions ("no markdown headers", "no section labels") propagates straight to the UI. The FE amplifies this by rendering through `ReactMarkdown`, which was wired against an earlier prompt contract that used markdown — prompt ↔ renderer drift. Thinking-budget contention (the B-001 dominant cause) is a **low-probability secondary** here because the 400-word target has ~3× token headroom against `max_tokens=1500`. See investigation §4–5 for the full probability breakdown and the transfer analysis vs B-001.

---

## 2. Scope

**In scope.**
- `POST /api/cover-letter` and `POST /api/v1/cover-letter` (the v1 route is a pure re-export; both URL surfaces hit the same handler — investigation §1).
- `app/services/gpt_service.py::generate_cover_letter` (the live path used by the handler).
- Prompt wording, output-shape contract, and JSON-structured-output strategy for the above.
- `CoverLetterResponse` Pydantic schema in `app/schemas/responses.py`.
- `src/components/rewrite/CoverLetterViewer.tsx` rendering path (ReactMarkdown removal — investigation §4 branch (c) amplifier).
- `src/services/api.ts::generateCoverLetter` signature reconciliation.
- Regression tests for §8.

**Out of scope.**
- `app/services/ai_service.py::generate_cover_letter` — dormant duplicate not imported by any live route. Tracked under S47-defer for Phase-6 cleanup.
- Per-paragraph regen affordance (LD-3). Cover letters are short enough (400 words) that full-letter regen is sufficient for V1; per-paragraph is polish-phase surface area tracked separately if telemetry warrants.
- Auth + rate limit on the cover-letter endpoint — tracked under `BACKLOG.md` E-037 (amended 2026-04-21 to include cover-letter in its scope). This spec does not change the auth posture.
- `downloadCoverLetterDocx` in `utils/docxExport.ts` — consumes the raw full-text string; reconciled to read `full_text` from the new response shape, no logic change (§10 mechanics).
- Tone *behavior* redesign. Tone is user-selectable today (3-button selector in `CoverLetterViewer`); this spec validates it end-to-end (AC-4) but does not add, rename, or reshape tones.

---

## 3. Locked Decisions

> These are inputs to the spec. They are not re-debated in the implementation slice. If Dhamo overrides any of these before the implementation slice starts, the implementation slice amends this spec first.

**LD-1 — Lock the existing 8-block prompt structure as canonical.** The canonical cover-letter shape is: `date, recipient (2 lines: "Hiring Manager" + company name), greeting, body_hook, body_fit, body_close, signoff, signature`. This is the shape the current prompt already describes. The bug is enforcement, not design — do not redesign the format. Codify this shape in the response schema and in the acceptance tests.

**LD-2 — Response shape: structured, populated end-to-end.** The `CoverLetterResponse` Pydantic schema changes from `{cover_letter: str, tone: str}` to:
```
{
  date: str,
  recipient: {name: str, company: str},
  greeting: str,
  body_paragraphs: List[str],   # Field(min_length=3, max_length=3)  — exactly 3
  signoff: str,
  signature: str,
  tone: str,
  full_text: str               # server-side join of the 8 blocks
}
```
`body_paragraphs` is typed with `min_length=3` and `max_length=3` to match the hook / fit / close structure; any other length is a structural error (AC-2). `full_text` is retained for the one-click copy-to-clipboard and DOCX export UX — mirrors spec #51 LD-5 pattern ("both structured fields AND full_text populated, served from the same LLM response"). Use `json_mode=True` on the router call with the Pydantic schema as the response schema.

**LD-3 — Full-letter regen only for V1.** No per-paragraph regen affordance. Over-engineering at 400 words; the full-letter regen button covers the iteration need. If post-ship telemetry shows high regen frequency and user interviews surface "I only wanted to fix the middle paragraph," revisit as a new backlog row.

**LD-4 — Tone parameter validation: two-layer testing.**
  - **AC-4a (mock, runs every CI build):** assert the `tone` request parameter reaches the `generate_for_task` call unmodified. Mock-level test. Fast. Required green on every PR.
  - **AC-4b (integration, gated):** marker `@pytest.mark.integration_llm`. Generates cover letters with all three tones (`professional`, `confident`, `conversational`) against a fixed resume + JD fixture. Asserts token-level differentiation between outputs. "Differentiation" defined precisely as: for each pair of tone outputs, the Jaccard word-overlap on body_paragraphs is **< 0.70** (i.e., at least 30% of unique words differ between any two tones on the same input). CI skips this marker by default (`-m "not integration and not integration_llm"`); run locally pre-merge. Threshold (0.70) is a spec-author proposal; the implementation slice may tune based on empirical measurement and must log the tuned value in the slice's SESSION-STATE entry.

  Both layers required. The marker name `integration_llm` is new (distinct from the existing `integration` marker per CLAUDE.md Rule 13) because it specifically gates live-LLM calls — the implementation slice registers it in `pytest.ini` / `pyproject.toml` markers list and in `.agent/skills/testing.md`.

**LD-5 — `thinking_budget=2000` cap.** Apply the same `thinking_budget` kwarg the B-001 fix introduced to `generate_for_task` (llm_router.py:57, 199, 242). Cheap insurance against Gemini 2.5 Pro's thinking pool occasionally starving the output pool on long JDs, even though token contention is low-probability at 400-word targets. Cost: zero additional code path. Transfer from spec #51.

**LD-6 — AC-5 error envelope transfers from spec #51.** Truncated or malformed LLM response → HTTP 502 with body:
```json
{
  "detail": {
    "error": "cover_letter_truncated" | "cover_letter_parse_error" | "cover_letter_llm_error" | "cover_letter_validation_error",
    "message": "<human-readable explanation>",
    "retry_hint": "retry" | "reduce_input" | "contact_support"
  }
}
```
Same shape as spec #51 AC-5, same status code. Adds one variant — `cover_letter_validation_error` — for the LD-2 Pydantic validation path (body_paragraphs length ≠ 3, missing block, etc.). FE shows a user-visible error toast and does not render a partial-success state. Silent partial success — the current behavior, where the FE renders whatever string comes back — is the worst possible outcome.

**LD-7 — Response-shape migration: hard-cut.** Enumerated consumers of `CoverLetterResponse.cover_letter` (investigation §1 File Inventory):
1. `src/components/rewrite/CoverLetterViewer.tsx:30` (`handleCopy`) → copy `coverLetter.cover_letter` to clipboard
2. `src/components/rewrite/CoverLetterViewer.tsx:37` (`handleDownloadTxt`) → blob from `coverLetter.cover_letter`
3. `src/components/rewrite/CoverLetterViewer.tsx:51` (`handleDownloadPDF`) → parses `coverLetter.cover_letter` lines with a `## ` header-detection branch
4. `src/components/rewrite/CoverLetterViewer.tsx:203` (motion `key`) → uses `coverLetter.cover_letter.slice(0, 20)` as render key
5. `src/components/rewrite/CoverLetterViewer.tsx:249` (ReactMarkdown children) → renders `coverLetter.cover_letter`
6. `src/utils/docxExport.ts:235` (`downloadCoverLetterDocx`) → parses the full-text string

**Decision — hard-cut, not soft-cut.** All six consumers migrate to the new shape in the same impl commit. Rationale:
- Soft-cut (return both old and new fields for one release, deprecate `cover_letter` later) keeps the bug alive in any code path still reading the old field. The bug *is* that field being a single free-form string.
- Only one component (`CoverLetterViewer`) + one utility (`docxExport`) consume the response. Both live in the same codebase and the same PR scope. No external consumer.
- `full_text` in the new shape (LD-2) covers consumers 1, 2, 4, 6 with a trivial rename (`cover_letter` → `full_text`). Consumers 3 and 5 (the parsers) migrate to structured-field reads.
- The PR description must enumerate the six consumers and their migration per CLAUDE.md Rule 16 step-1 audit.

**LD-8 — ReactMarkdown removal from the cover-letter render path.** Investigation §4 branch (c) identifies ReactMarkdown as the propagation vector for any markdown leakage from the LLM. With structured output (LD-2), the FE renders blocks directly — no markdown parsing, no interpretation, no `## ` header detection branch. `CoverLetterViewer` renders `{date}`, `{recipient}`, `{greeting}`, `{body_paragraphs.map(...)}`, `{signoff}`, `{signature}` as explicit JSX blocks with design-token-driven styling. AC-6 asserts ReactMarkdown is removed from this component. If future rich-text support is wanted (bold, italic, links), that's a new spec, and it starts from a known-good structured baseline instead of a string-parsing one.

---

## 4. Acceptance Criteria

> All ACs are test-gated (§8 Test Plan maps each AC to a test). No live-LLM calls in default CI tests — mock `generate_for_task` and assert against the prompt / the mocked response. AC-4b is the sole exception (gated behind `@pytest.mark.integration_llm`).

- **AC-1 — All 8 canonical blocks present, in order.** Given a representative resume + JD fixture, the `CoverLetterResponse` contains non-empty `date`, `recipient.name`, `recipient.company`, `greeting`, exactly 3 `body_paragraphs`, `signoff`, `signature`, `tone`, and `full_text`. The `full_text` serialization (§7) preserves block order: date → recipient → greeting → body[0] → body[1] → body[2] → signoff → signature.

- **AC-2 — body_paragraphs length enforcement.** Pydantic rejects responses with `len(body_paragraphs) != 3` at model-construction time. Service catches the `ValidationError` and raises the AC-5 `cover_letter_validation_error` variant. Test variants: LLM returns 2 paragraphs, 4 paragraphs, 0 paragraphs → all return structured 502.

- **AC-3 — full_text server-side join format.** `full_text` equals:
  ```
  {date}\n\nHiring Manager\n{recipient.company}\n\n{greeting}\n\n{body_paragraphs[0]}\n\n{body_paragraphs[1]}\n\n{body_paragraphs[2]}\n\n{signoff}\n{signature}
  ```
  (Blank lines between blocks; signoff → signature is single-newline per business-letter convention.) `recipient.name` is always the literal string `"Hiring Manager"` in V1 and is not surfaced in `full_text` as a separate line — the `recipient.company` line is what appears. Implementation-slice note: if a future spec makes `recipient.name` dynamic (e.g., "Dear Jane Doe," after LinkedIn scrape), this format string updates.

- **AC-4 — Tone parameter end-to-end.**
  - **AC-4a (mock, CI-green every PR):** `generate_for_task` is called with a prompt string that contains the literal `f"Tone: {tone}"` fragment for the tone passed in the request. Test asserts by substring match on the captured prompt argument.
  - **AC-4b (integration, gated, run locally pre-merge):** `@pytest.mark.integration_llm`. Fixture: one resume + one JD, held constant. Calls `generate_cover_letter` three times with `tone ∈ {"professional", "confident", "conversational"}`. For each of the 3 tone-pair combinations (pro↔conf, pro↔conv, conf↔conv), compute Jaccard word-overlap on the concatenation of `body_paragraphs` and assert < 0.70. CI does not run this marker; it must pass locally before the impl PR merges. Implementation slice logs the three measured Jaccard values in the SESSION-STATE entry.

- **AC-5 — Structured error on truncation / parse / validation failure.** Same shape as spec #51 AC-5, status 502. Variants: `cover_letter_truncated` (finish_reason MAX_TOKENS), `cover_letter_parse_error` (malformed JSON), `cover_letter_validation_error` (Pydantic ValidationError from LD-2 shape), `cover_letter_llm_error` (catch-all upstream exception). FE shows error toast; no partial-success render.

- **AC-6 — FE renderer consumes structured fields; ReactMarkdown removed from cover-letter path.** `CoverLetterViewer.tsx` imports no `ReactMarkdown` symbol and has no `<ReactMarkdown>` JSX in the cover-letter render subtree. Structured fields are rendered as explicit JSX blocks (LD-8). `full_text` is available for copy-to-clipboard and DOCX export (LD-7) but is not used as a render source. Implementation slice verifies by grep: `grep -n 'ReactMarkdown' src/components/rewrite/CoverLetterViewer.tsx` returns zero matches.

- **AC-7 — `thinking_budget=2000` cap applied.** The `generate_for_task` call in `generate_cover_letter` passes `thinking_budget=2000` as a kwarg. Mock-level test asserts by inspecting the call-args of the mocked router.

---

## 5. Response-Shape Decision (LD-2 + LD-7 rationale in full)

Current `CoverLetterResponse` schema (`app/schemas/responses.py:113-117`):

```python
class CoverLetterResponse(BaseModel):
    """Generated cover letter response."""
    cover_letter: str
    tone: str
```

**Investigation finding (§4).** BE populates `cover_letter = raw_llm_string.strip()` and `tone = tone` — a single unvalidated string. No per-block parsing. No structural schema. No retry on format drift. The prompt is the *only* mechanism enforcing the 14-step structure, and LLM negative-instruction compliance is probabilistic.

**Options considered.**
1. **Structured fields + `full_text` (LD-2).** Chosen. Powers schema-level enforcement, unblocks the bug fix, keeps copy/DOCX export working via `full_text`, aligns with spec #51 LD-5.
2. **Keep single string, add post-generation regex validation.** Rejected. Regex over LLM output is brittle (Unicode quote variants, signoff alternatives, tone-driven greeting drift). Fighting the string representation; not fixing it.
3. **Structured fields only, no `full_text`.** Rejected. Would require deleting copy-to-clipboard and DOCX export OR having the FE re-join server-side-structured fields, which duplicates logic and drifts. `full_text` is cheap to derive once server-side per AC-3.

**Migration: hard-cut (LD-7).** Six consumers enumerated in LD-7; all migrate in one impl commit. The alternative (soft-cut, ship both `cover_letter` and the new fields) keeps the bug alive. The investigation's file-inventory scope is small enough to justify the hard-cut.

**Author recommendation (still subject to Dhamo review):** LD-2 + LD-7 as stated. If Dhamo overrides before implementation, the implementation slice amends this spec first.

---

## 6. API Contract (Draft — implementation slice finalizes)

### 6.1 Generate cover letter (unchanged endpoint; breaking response-shape change per LD-7)

```
POST /api/v1/cover-letter
Content-Type: application/json

Request (CoverLetterRequest — unchanged):
  {
    "resume_text": "<string>",         // min_length=50
    "job_description": "<string>",     // min_length=50
    "tone": "professional" | "confident" | "conversational"   // default "professional"
  }

Response (CoverLetterResponse — NEW shape per LD-2):
  {
    "date": "<string, e.g. 'April 21, 2026'>",
    "recipient": {
      "name": "Hiring Manager",
      "company": "<string>"
    },
    "greeting": "<string, e.g. 'Dear Hiring Manager,'>",
    "body_paragraphs": [
      "<string — hook>",
      "<string — fit>",
      "<string — close>"
    ],
    "signoff": "<string, e.g. 'Sincerely,'>",
    "signature": "<string, candidate name extracted from resume>",
    "tone": "<string — echoed from request>",
    "full_text": "<string — server-side join per AC-3>"
  }
```

Router task name: `cover_letter` (reasoning tier; unchanged — already in `REASONING_TASKS` frozenset in `llm_router.py`).

**No new endpoints per LD-3.** Auth posture unchanged per §2 out-of-scope (E-037 owns that fix).

**Prompt strategy.** The existing 14-step prompt (investigation §2) is retained and adapted for structured output:
- Remove the "Do NOT use markdown headers" and "Do NOT label sections" negative rules — they become moot under JSON-structured output, since the model emits fields, not free-form text.
- Add an explicit `response_mime_type="application/json"` + `response_schema=CoverLetterResponse` to the router call.
- Keep the block-by-block description as guidance for the model on what to put in each field (e.g., "body_paragraphs[0] is the hook — state the role and company by name, express genuine interest, 2–3 sentences").
- Keep the 400-word total cap in the prompt; add `max_output_tokens=2500` on the router call to accommodate JSON overhead (§7).

Exact wording is implementation-slice detail; the spec locks the *shape* of the prompt (structured output, block-level guidance) not the prose.

---

## 7. LLM Call Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Task name | `cover_letter` | Unchanged; already in `REASONING_TASKS` frozenset (Gemini 2.5 Pro) |
| Model | Gemini 2.5 Pro | Unchanged — reasoning tier per existing router config |
| `response_mime_type` | `application/json` | json_mode — enables schema enforcement |
| `response_schema` | Pydantic `CoverLetterResponse` (LD-2 shape) | Schema-level block enforcement is the fix |
| `max_output_tokens` | 2500 | 400-word target + JSON key overhead (~100 tokens) + safety margin. Spec-author proposal; impl may tune based on empirical measurements. |
| `thinking_budget` | 2000 | LD-5 — cheap insurance against thinking-pool contention |
| `temperature` | 0.7 | Unchanged from current (`gpt_service.py:612`) |

**Router kwarg plumbing.** `thinking_budget` is already plumbed through `generate_for_task` (llm_router.py:57, 199, 242) from the B-001 fix. `response_mime_type` + `response_schema` must be added if not already — the impl slice audits the router surface and amends if needed (same pattern as the B-001 `thinking_budget` addition).

---

## 8. Regression Test Plan

### 8.1 Backend

Create `tests/test_cover_letter.py` (new file):

| Test | AC | Notes |
|---|---|---|
| `test_all_8_blocks_present_in_order` (**new**) | AC-1 | Fixture: resume + JD; mock `generate_for_task` to return a structured response with all blocks populated. Assert `response.date`, `response.recipient.name`, `response.recipient.company`, `response.greeting`, `len(response.body_paragraphs) == 3`, `response.signoff`, `response.signature`, `response.tone`, `response.full_text` all present + non-empty. Assert `full_text` preserves block order per AC-3. |
| `test_body_paragraphs_length_validation` (**new**) | AC-2 | Three variants: mock returns 2, 4, 0 paragraphs. Assert all three return HTTP 502 with `detail.error == "cover_letter_validation_error"` per AC-5. |
| `test_full_text_server_side_join_format` (**new**) | AC-3 | Mock returns known structured fields; assert `response.full_text` exactly equals the AC-3 format string (blank lines between blocks; signoff → signature single-newline). |
| `test_tone_parameter_reaches_llm_prompt` (**new**) | AC-4a | Parametrized over the 3 tones. Mock `generate_for_task`; assert the captured prompt argument contains the substring `f"Tone: {tone}"`. Mock-level; runs every CI build. |
| `test_tone_outputs_differentiate` (**new**, `@pytest.mark.integration_llm`) | AC-4b | CI-deselected. Real LLM calls for all 3 tones against a fixed fixture. Assert Jaccard word-overlap on body_paragraphs < 0.70 for each of the 3 tone-pair combinations. Log the measured values. |
| `test_cover_letter_truncated_returns_502_structured_error` (**new**) | AC-5 | Mock router to return a response flagged as truncated (finish_reason=MAX_TOKENS). Assert HTTP 502, `detail.error == "cover_letter_truncated"`, envelope matches AC-5 shape. |
| `test_cover_letter_parse_error_returns_502` (**new**) | AC-5 | Mock router to return malformed JSON. Assert `detail.error == "cover_letter_parse_error"`. |
| `test_cover_letter_llm_error_returns_502` (**new**) | AC-5 | Mock router to raise a generic exception. Assert `detail.error == "cover_letter_llm_error"`. (Note: current fallback-template behavior is removed by this fix — silent fallback is replaced with explicit error per investigation §4 branch (e).) |
| `test_thinking_budget_2000_applied` (**new**) | AC-7 | Mock `generate_for_task`; assert it's called with `thinking_budget=2000`. |

**Marker registration.** `@pytest.mark.integration_llm` must be registered in `pytest.ini` / `pyproject.toml` in the impl slice, alongside the existing `integration` marker. CI config (`.github/workflows/ci.yml`) updates its pytest invocation to `-m "not integration and not integration_llm"` so the new marker is deselected by default. `.agent/skills/testing.md` documents the marker and when to run it.

### 8.2 Frontend

Extend or create `tests/components/CoverLetterViewer.test.tsx`:

| Test | AC | Notes |
|---|---|---|
| `renders_structured_fields_as_explicit_blocks` (**new**) | AC-6 | Mock a `CoverLetterResponse` with known values; render `CoverLetterViewer`; assert date, recipient.company, greeting, each body paragraph, signoff, signature appear as distinct DOM elements (match by `data-testid` or text content). |
| `react_markdown_absent_from_render_path` (**new**) | AC-6 / LD-8 | Grep-style test: `expect(container.querySelector('[data-markdown-root]')).toBeNull()` — or equivalent assertion that no markdown-rendered artifacts are present. Paired with a static-analysis check in the impl slice's pre-commit hook / a lint rule (nice-to-have; not required for the impl slice to ship). |
| `copy_to_clipboard_uses_full_text` (**new**) | LD-7 | Click the Copy button; assert `navigator.clipboard.writeText` was called with `response.full_text` (not `response.cover_letter`, which no longer exists). |
| `docx_export_receives_full_text` (**new**) | LD-7 | Click the DOCX button; assert the export helper is invoked with `coverLetter.full_text`. |
| `no_headers_rendered_when_llm_emits_only_structured_fields` (**new**) | AC-6 | Mock response with body_paragraphs containing plain prose (no `##` or `**`); assert rendered DOM contains no `<h1>/<h2>/<h3>` within the cover-letter card. |
| `error_toast_shown_on_502` (**new**) | AC-5 FE side | Mock API to return 502 with the AC-5 envelope; assert an error toast/banner is rendered; assert no cover-letter-body elements are rendered. |

**No live LLM calls in any FE test.** Vitest mocks the `generateCoverLetter` API client.

---

## 9. Telemetry

**New PostHog events (add to `.agent/skills/analytics.md` during the implementation slice).**

| Event | Surface | Properties | When |
|---|---|---|---|
| `cover_letter_requested` | FE | `{resume_char_length, jd_char_length, tone}` | User clicks "Generate" or "Regenerate" on `CoverLetterViewer` |
| `cover_letter_succeeded` | BE | `{resume_char_length, output_char_length, tone, company_name_present}` | Response returns 200 with validated shape |
| `cover_letter_failed` | BE | `{reason, resume_char_length, tone}` where `reason ∈ {truncated, parse_error, validation_error, llm_error}` matching AC-5 | Response returns 502 |

**Deprecation.** The existing `cover_letter_generated` event (currently `{tone, resume_chars, company_name_present}` — see `app/api/routes/cover_letter.py:22-27`) is replaced by `cover_letter_succeeded` on the success path. Move the old event to the "Deprecated Frontend Events" (or "Deprecated Backend Events", new subsection) table in `.agent/skills/analytics.md` with a commit-SHA marker, following the P5-S17 precedent.

**Operational logging (first week post-ship).** Log `resume_text` length, JD length, `output_char_length`, and `tone` on every successful call for the first 7 days. Review the histogram to catch any quality drift across tones and validate the 2500-token cap. Remove the verbose logging once the distribution is understood (same pattern as spec #51 §9).

---

## 10. Migration / Rollout Notes

- **DB:** no migration.
- **BE:** `CoverLetterResponse` schema change in `app/schemas/responses.py` is a breaking shape change. The service (`gpt_service.py::generate_cover_letter`) changes in the same commit. The route (`app/api/routes/cover_letter.py`) is re-exported by v1 — no route-layer change needed for v1; the route's `response_model` type handles the new shape automatically.
- **FE hard-cut per LD-7:** six consumers migrate in the same commit as the BE change. The impl slice's step-1 audit (CLAUDE.md Rule 16) greps for `cover_letter` field reads and enumerates the migration per consumer. Expected consumer set is the six listed in LD-7; any additional consumer found during audit flags as drift and halts the slice for Dhamo review.
- **No feature flag.** This is a bug fix to a broken live feature. Deploy to main per CLAUDE.md Rule 9.
- **Silent fallback removed.** The current fallback-template code path in `gpt_service.py:614-629` is deleted — silent fallback on exception yields a well-formatted-but-wrong-content letter (investigation §4 branch (e)), which is observationally indistinguishable from a broken generation. Replaced with the AC-5 error envelope. If Dhamo wants a fallback kept for resilience, that's a design decision to surface before the impl slice starts — but "fail visibly" is the default this spec takes.
- **CODE-REALITY regen:** Section 4 (gpt_service public surface), Section 8 (FE shared types — `CoverLetterResponse` shape), Section 7 (Rewrite.tsx / CoverLetterViewer PostHog events) all change. Impl slice regenerates before SESSION-STATE close, per the standard post-slice hygiene.
- **Testing marker:** `@pytest.mark.integration_llm` is new. CI config update (`-m "not integration and not integration_llm"`), marker registration (`pyproject.toml` / `pytest.ini`), and `.agent/skills/testing.md` doc update all land in the impl slice.
- **B-002 closure** happens on impl-slice merge, not on spec merge (§12 R15).

---

## 11. Transfers and Non-Transfers from Spec #51

| From spec #51 | Transfers? | Where it lands here |
|---|---|---|
| LD-5 (structured output + `full_text`) | **Yes** | LD-2 — same pattern adapted for cover letter block shape |
| LD-3 (per-section regen endpoint) | **No** | LD-3 (inverse) — full-letter regen only. 400-word output doesn't justify per-paragraph regen surface. |
| Per-section chunking (Option B winner) | **No** | Out of scope. Single LLM call is sufficient; no analog to resume's 2-4 page output span. |
| Full-document fallback (Option A safety net) | **No** | Out of scope. Same reason as above. |
| `thinking_budget` cap | **Yes** | LD-5 — `thinking_budget=2000`, cheap insurance |
| AC-5 error envelope (structured 502) | **Yes** | LD-6 — same shape, same status, adds `cover_letter_validation_error` variant |
| AC-6 export-path audit | **Partial** | LD-7 enumerates the six consumers; the audit shape transfers, the specific export code does not (DOCX helper operates on `full_text` in both the old and new shape). |
| Telemetry trio (`*_requested` / `*_succeeded` / `*_failed`) | **Yes** | §9 — same shape with cover-letter-specific property sets |
| AC-3-style load-specific ACs (4-page no-truncation) | **No** | Not relevant — cover letter is fixed-length (400 words). |
| Empirical LD-4 measurement gate | **No** | Not relevant — single fixed LLM call, no option selection. |
| Two-layer test (mock + integration marker) | **Adapted** | LD-4 / AC-4 — new marker `integration_llm` specifically for live-LLM tone differentiation. Spec #51 used existing `integration` marker; this spec adds a new one for finer-grained gating (live-LLM vs live-external-service). |

---

## 12. R15

**B-002 is NOT closed by this spec slice.** This spec is the design contract; the follow-on implementation slice closes B-002 when it ships the fix and the AC-1…AC-7 tests are green on CI (plus AC-4b green locally pre-merge). On implementation-slice merge, `BACKLOG.md` B-002 status flips 🔴 → ✅ with the standard `closed by <commit-sha> on <YYYY-MM-DD>` annotation.

---

## 13. Out-of-Spec Follow-Ups (tracked, not blocking)

- **`app/services/ai_service.py::generate_cover_letter`** — duplicate of `gpt_service.py::generate_cover_letter`. Remains tracked under S47-defer for Phase-6 cleanup, unchanged by this slice.
- **Cover-letter endpoint auth + rate limit** — `/api/cover-letter` and `/api/v1/cover-letter` are unauthed and call Pro-tier Gemini. Tracked under `BACKLOG.md` E-037 (amended 2026-04-21 to include cover-letter in its scope). Not fixed here.
- **Legacy `/api/*` cover-letter mount removal** — same class as the rewrite flat-route cleanup tracked under `[5.17-follow] flat /api/* legacy-route cleanup`. Not fixed here.
- **Dynamic recipient name** — V1 uses literal `"Hiring Manager"`. Future work could scrape LinkedIn / enrich with a hiring-manager lookup service and flow a real name through `recipient.name`. Out of scope.
- **Per-paragraph regen** — deferred per LD-3. Revisit if post-ship telemetry shows high `cover_letter_requested` regen frequency and user interviews confirm the iteration pattern.
- **Tone threshold tuning** — AC-4b uses 0.70 Jaccard as the differentiation threshold. The impl slice logs empirical values and tunes if warranted; any tuning updates this spec or a follow-up.
- **Investigation §8 manual repros** — the three manual reproductions described in the investigation (happy path × 3 tones; 4000-word JD long-tail; provoke-fallback with invalid API key) are diagnostic aids the impl slice **should** run as pre-fix verification but are not acceptance criteria.
