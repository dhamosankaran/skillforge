# B-002 Cover Letter Format Investigation

> **Mode 1 read-only audit.** No code changes in this slice. Output informs the
> spec-then-impl follow-up that will close B-002.
>
> **Commit at audit time:** `a06f015` (post-B-001 series; post-CODE-REALITY regen).
> **Investigator:** Claude Code, 2026-04-21.

---

## 1. File inventory

| Role | File | Notes |
|------|------|-------|
| Legacy route | `app/api/routes/cover_letter.py` | Single `POST /cover-letter` decorator; auth = **none**; mounted at `/api/*` (main.py:122) |
| v1 route | `app/api/v1/routes/cover_letter.py` | Re-export of the legacy router (`from app.api.routes.cover_letter import router`); mounted at `/api/v1/*` (main.py:131) |
| Request schema | `app/schemas/requests.py:30` (`CoverLetterRequest`) | `{resume_text: str, job_description: str, tone: "professional\|confident\|conversational"}`, tone default `"professional"`, resume/JD `min_length=50` |
| Response schema | `app/schemas/responses.py:113` (`CoverLetterResponse`) | `{cover_letter: str, tone: str}` — single free-form string |
| Service (live) | `app/services/gpt_service.py::generate_cover_letter` (L560-629) | Sync function; prompt + `generate_for_task(task="cover_letter", …)`; fallback template on exception |
| Service (dup) | `app/services/ai_service.py::generate_cover_letter` | Duplicate public API; `[S47-defer]` — route imports `gpt_service`, not `ai_service` |
| LLM router task | `app/core/llm_router.py:35` | `"cover_letter"` ∈ `REASONING_TASKS` → Gemini 2.5 Pro (same tier as B-001's `resume_rewrite`) |
| FE client | `src/services/api.ts:203` (`generateCoverLetter`) | Calls `POST /api/cover-letter` (legacy path, not v1) |
| FE hook | `src/hooks/useRewrite.ts:26` (`runCoverLetter`) | Stateful `coverLetter: CoverLetterResponse \| null`; no error-state wiring beyond try/finally |
| FE component | `src/components/rewrite/CoverLetterViewer.tsx` | Renders `coverLetter.cover_letter` via **ReactMarkdown** (despite prompt forbidding markdown — see §5) |
| FE export | `src/utils/docxExport.ts:235` (`downloadCoverLetterDocx`) | Out of scope — consumes the raw string |
| Skill ownership | `.agent/skills/ats-scanner.md` §LLM Task Mapping | Lists `cover_letter` under the ATS-scanner umbrella; no dedicated cover-letter skill file exists (skill-inventory gap, minor) |

**Auth posture.** Unauthed + no rate limit visible on either mount (same shape as the rewrite endpoints — see BACKLOG E-037 for the parallel cost-exposure concern; a cover-letter analogue should be tracked too, but is out of scope for this investigation).

**Telemetry.** `cover_letter_generated {tone, resume_chars, company_name_present}` fires on success. No failure event. No format-validation event. No structured-output event. Compared to B-001's post-fix contract (`rewrite_succeeded` / `rewrite_failed` with `strategy=chunked\|fallback_full`), there is zero observability on format quality.

---

## 2. Prompt template (verbatim, from `gpt_service.py:574-609`)

```
You are an expert career coach writing a compelling cover letter in traditional business-letter format.

STRICT FORMAT RULES:
- Do NOT use markdown headers (no "##", no "#", no bold section titles).
- Do NOT label sections with words like "Opening", "Why I'm a Fit", "Key Achievement", or "Closing".
- Output plain text with blank lines between blocks.

Exact structure, in this order:

1. Date line: "{today}"
2. Blank line.
3. Recipient block (2 lines):
   Hiring Manager
   {company_name}
4. Blank line.
5. Greeting: "Dear Hiring Manager,"
6. Blank line.
7. Body paragraph 1 — hook: state the role and company by name, express genuine interest, 2–3 sentences.
8. Blank line.
9. Body paragraph 2 — fit: connect 2–3 specific, quantified achievements from the resume to the JD requirements. Incorporate missing keywords naturally.
10. Blank line.
11. Body paragraph 3 — close: reiterate enthusiasm, invite an interview, thank the reader.
12. Blank line.
13. Sign-off line: "Sincerely,"
14. Signature line: "{candidate_name}"

Keep the total length under 400 words. Tone: {tone}.

Candidate resume:
{resume_text}

Job description:
{jd_text}

Missing skills to incorporate if possible:
{missing_keywords}
```

**Router call.** `generate_for_task(task="cover_letter", prompt=prompt, max_tokens=1500, temperature=0.7)`. No `system_prompt`. No `json_mode`. No `thinking_budget` (post-B-001 this kwarg exists but is not used here — defaults to whatever Gemini 2.5 Pro's shared pool allocates).

**Budget vs target.** 400 words ≈ 500-600 tokens. `max_tokens=1500` is ~2.5× the target. Output-side truncation is unlikely in isolation but — per B-001's root cause — Gemini 2.5 Pro's *thinking* pool competes with the *output* pool at the same shared ceiling. For short targets (cover letter) this is less hostile than for 4-page resumes, but the risk vector exists.

**Structure enforcement.** Pure prompt-level. No:
- JSON schema / structured output (cf. B-001 fix)
- Post-generation regex validation
- Retry / repair loop on format drift
- Per-block parsing before return

The prompt is a 14-step format contract; the code trusts the model to obey it and returns whatever string comes back (`cover_letter.strip()`).

---

## 3. Response handling flow

```
Route  (app/api/routes/cover_letter.py:11)
  ├─ Pydantic-validates CoverLetterRequest
  ├─ nlp.extract_job_requirements(job_description)  → {company_name, all_skills, …}
  ├─ gpt_service.generate_cover_letter(resume_data, jd_requirements, tone)
  │    ├─ Build prompt (see §2) with candidate_name, company_name, today, tone, missing_keywords
  │    ├─ generate_for_task(task="cover_letter", max_tokens=1500, temperature=0.7)   — Gemini 2.5 Pro, reasoning tier
  │    ├─ return CoverLetterResponse(cover_letter=raw_string.strip(), tone=tone)
  │    └─ on Exception:  return static fallback template (hard-coded 3-paragraph string)
  ├─ analytics_track("cover_letter_generated", {tone, resume_chars, company_name_present})
  └─ HTTPException 503 (RuntimeError) or 500 (Exception) — note: the service catches Exception internally and
     returns a fallback instead of raising, so the 500 branch only fires if extract_job_requirements or
     model-building raises before the service is called.

Frontend (CoverLetterViewer.tsx)
  ├─ Receives `coverLetter: CoverLetterResponse | null`
  ├─ Renders `coverLetter.cover_letter` via <ReactMarkdown>
  │     — this renders markdown even though the prompt forbids markdown (§5 smell)
  ├─ Export paths (PDF/DOCX/.txt/Copy) also operate on the raw string
  │     — handleDownloadPDF has an `isHeader = trimmed.startsWith('## ')` branch,
  │       which implies the FE was authored against a version of the prompt that
  │       used markdown headers. Design drift not reconciled.
  └─ No UI affordance for format-failure recovery; failed/malformed output just renders awkwardly
```

**Where format can break** — ranked by blast radius:

1. **Model ignores "no markdown" rule** — emits `## Opening`, `**Key Achievement**`, etc. The prompt explicitly warns against this in two places, but LLM compliance with negative instructions is probabilistic. Output gets rendered by ReactMarkdown → visible headers, bold blocks.
2. **Model skips blocks** — omits the Date line, the Recipient block, the signoff, or the signature. No structural validation catches this.
3. **Model merges paragraphs** — emits single `\n` instead of blank line `\n\n` between blocks. ReactMarkdown treats that as a line-break within one paragraph, not a paragraph break → wall-of-text render.
4. **Model adds labels** — "Why I'm a Fit:" at the start of a paragraph despite the prompt forbidding exactly that wording.
5. **Fallback template fires silently** — any LLM exception (rate limit, network, quota) returns the hard-coded fallback template. User sees generic copy instead of an error; no telemetry indicates this happened.

---

## 4. Root cause hypothesis

The symptom per BACKLOG B-002 and playbook P5-S10: *"cover letter generation produces output that doesn't match the expected format (headers wrong, paragraphs malformed, missing greeting/signature blocks)."*

| Branch | Probability | Evidence |
|--------|-------------|----------|
| (a) Prompt doesn't pin format | **Low** | The prompt is *extremely* explicit — a numbered 14-step structure, two negative rules against markdown/labels, word cap, tone slot. If prompt-level enforcement worked reliably for long-form business text, this bug wouldn't exist. |
| (b) Response is free-form text being awkwardly parsed | **HIGH — dominant** | `CoverLetterResponse.cover_letter: str` is a single unvalidated string. No JSON schema. No per-block parsing. No structural validation. No retry on format drift. Any deviation from the 14-step prompt contract propagates straight to the UI. This is the exact class of bug B-001 was (free-form output → empty structured fields); same family, different surface. |
| (c) FE rendering drops/munges structure | **Medium — contributes** | `CoverLetterViewer.tsx` uses `<ReactMarkdown>` to render a response that the prompt explicitly tells the model **not** to emit as markdown. If the model obeys (plain text, blank-line separated), ReactMarkdown handles it as paragraphs — OK. If the model disobeys (markdown headers), ReactMarkdown renders them — produces the "headers wrong" symptom. `handleDownloadPDF` also has a `## ` header detection branch, suggesting the FE was authored against a different prompt contract than the current one. Prompt ↔ FE contract drift. |
| (d) Thinking-budget contention (B-001 analogue) | **Low** | Target length is 400 words (~500-600 tokens) against `max_tokens=1500` — ~3× headroom. Unlike a 4-page resume rewrite, the cover letter has slack. But the *reasoning* tier is shared and bursty, so occasional format-compressing truncation is possible for long-tail JDs. Should not be dismissed; should not be the leading hypothesis. |
| (e) Fallback template firing silently | **Low-to-medium** | If an exception trips the fallback template, the user sees the 3-paragraph static copy — which *is* well-formatted but is wrong-for-the-role. Not "malformed" but "wrong content." Not observable without telemetry. Should be logged as a telemetry gap, not the primary hypothesis. |

**Dominant hypothesis:** (b) with (c) as the amplifier. The response shape is a single free-form string. The prompt is the only mechanism enforcing structure, and LLMs are probabilistically non-compliant with negative instructions at the margin. The FE then renders whatever comes back via a markdown parser that was built against a different prompt contract.

**Secondary:** (c) is a standalone bug worth naming — the FE markdown renderer is mismatched to the prompt's "plain text" instruction. Even if (b) is fully fixed (structured output), the FE will still need to be reconciled to render the new shape without markdown interpretation.

---

## 5. Comparison to B-001 fix pattern

| Axis | B-001 (resume rewrite) | B-002 (cover letter) | Transfer? |
|------|------------------------|----------------------|-----------|
| Root cause family | Output-side thinking-budget contention + free-form response + empty structured fields | Free-form response + no structural validation + prompt ↔ FE contract drift | **Yes, same family** — structured-output fix applies |
| Response shape pre-fix | `RewriteResponse.sections` always empty; everything in `full_text` | `CoverLetterResponse.cover_letter: str` (unstructured) | Both collapse structure into a string |
| Target output size | 2-4 page resume (huge — 4000+ output tokens) | 400-word cover letter (~600 tokens) | **Different** — B-002 has 10× less token pressure |
| Thinking-budget relevance | **Primary** root cause | Possible-but-not-dominant | **Does not transfer** as root cause — but `thinking_budget` cap is cheap insurance |
| Fix shape B-001 used | (i) per-section chunking; (ii) full-document fallback with `thinking_budget=2000`; (iii) structured JSON output; (iv) AC-5 structured 502 error envelope; (v) per-section regen endpoint | (i) **NOT NEEDED** (letter is short enough to generate in one call); (ii) optional `thinking_budget` cap as insurance; (iii) **TRANSFERS** — structured JSON response shape is the core of the fix; (iv) **TRANSFERS** — same 502 envelope pattern; (v) **OPTIONAL** — per-paragraph regen is a polish-phase affordance | Partial — (iii), (iv) transfer; (i), (v) do not; (ii) is cheap-to-add |
| New task name in `REASONING_TASKS` | `resume_rewrite_section` added | **Not needed** — single-call is sufficient | — |
| Test shape | AC-1 through AC-6; 6-section render order; per-section regen; 4-page no-truncation; PDF/DOCX fidelity | Analogous ACs needed: 8-block structural validity; greeting/signoff present; no markdown headers in output; tone reflected in output; fallback-template-fires telemetry | Same shape, different content |

**Net:** B-001's **structured-output fix** is the core transfer. Per-section chunking + fallback-full machinery does **not** transfer (single-call is enough for 400 words). `thinking_budget` cap + AC-5 envelope are cheap insurance and should come along for free.

---

## 6. Slice classification

**Recommendation: Spec-then-impl (per R16).**

Reasoning:
- **Design surface exists.** The canonical cover-letter block structure needs to be locked at the schema level, not just in the prompt. That's a product+engineering call, not a mechanical code change.
- **Response-shape change is breaking.** Going from `{cover_letter: str, tone: str}` to a structured shape is a contract break — FE consumers (CoverLetterViewer, docxExport) need reconciliation. Specs catch this before the impl commit chain starts.
- **FE prompt ↔ renderer drift is its own decision.** Once the response is structured, does ReactMarkdown stay (for future rich-text support) or get replaced with block-by-block render? That decision belongs in the spec, not post-hoc.
- **AC matrix is non-trivial.** At minimum: AC-1 (structural validity — all 8 blocks present), AC-2 (no markdown headers leak through), AC-3 (greeting is exactly "Dear Hiring Manager,"), AC-4 (signoff is exactly "Sincerely,"), AC-5 (fallback-template telemetry fires), AC-6 (tone control reflects in output measurably), AC-7 (AC-5-style 502 envelope on LLM failure). That's 7 ACs with fixture inputs and assertions — spec-shaped work.
- **Precedent.** B-001 went spec-then-impl via spec #51. Same size and class of change; same mode warranted here.

Reject **Direct-fix** — too much design surface for a single slice. Reject **Further investigation needed** — the hypothesis is strong enough to write a spec against (hypothesis confirms with a live repro; no repro is strictly needed to author the spec, because the fix shape is deterministic from the code inspection).

---

## 7. Four open product questions + recommendations

### Q1: What's the canonical cover-letter format?

Define explicitly (header? greeting? N body paragraphs? signature?).

**Recommendation — [PRODUCT CALL]:** Lock the existing prompt's 8-block structure as canonical: `date, recipient_block (2 lines), greeting, body_hook, body_fit, body_close, signoff, signature`. The prompt already describes it; codify it in the response schema and acceptance tests. Three body paragraphs is the right default for a 400-word target — fewer feels thin, more is over budget.
**Rationale:** the current prompt is right; the bug is enforcement, not design. Pick up the design as-is.

### Q2: Should the response shape change from `{cover_letter: string, tone: string}` to a structured shape?

Analogous to B-001's `RewriteResponse.sections` fix.

**Recommendation — [BOTH]:** **Yes.** New shape: `{date: str, recipient: {name: str, company: str}, greeting: str, body_paragraphs: List[str], signoff: str, signature: str, tone: str, full_text: str}`. Keep `full_text` for exporters/copy-to-clipboard (same pattern as `RewriteResponse.full_text`). Use `json_mode=True` on `generate_for_task` + Pydantic validation on parse. This *is* the fix.
**Rationale:** prompt-only enforcement of format is the dominant root cause; schema-level enforcement removes the failure mode.

### Q3: Per-paragraph regen affordance like B-001's per-section regen?

Or full-letter only?

**Recommendation — [PRODUCT CALL]:** **Full-letter only for V1.** A 400-word cover letter is short enough that "dislike this paragraph" is usually "dislike the whole letter's angle" — per-paragraph regen is polish-phase surface area. Ship the structured-response fix first; collect telemetry on regenerate-rate; add per-paragraph if users actually use it. Cf. `rewrite_section` endpoint which exists because resumes are long (5-10 sections, each with real cost to re-render from scratch).
**Rationale:** B-001's per-section UX was justified by 4-page-resume cost; that economics doesn't transfer to a 400-word letter.

### Q4: Tone control — is "tone" parameter currently honored end-to-end? Is it user-selectable in the UI?

**Recommendation — [ENGINEERING CALL]:** Tone *is* end-to-end (request schema validates `^(professional|confident|conversational)$`; prompt inlines `Tone: {tone}`; FE `CoverLetterViewer.tsx` has a 3-button tone selector that re-calls `onGenerate(tone)`). But: **no assertion that the model's output actually reflects the selected tone**. Add an AC that runs the three tones against the same resume+JD and asserts that at least one token-level signal differs (e.g., no-shared-trigram-with-other-tone for the hook paragraph). This is *verification*, not *implementation* — the plumbing is there.
**Rationale:** the bug report is about format, not tone, so tone is an adjacent integrity check. Cheap to add; catches silent drift.

---

## 8. What would change the hypothesis (manual repro)

The dominant hypothesis (b) can be confirmed or falsified by 3 manual reproductions:

1. **Happy path against a representative JD.** Upload a real resume + paste a JD (> 300 words); generate at each of the 3 tones; inspect the raw `cover_letter` string for:
   - Does `## ` or `**` appear anywhere?  → (b) + (c) confirmed
   - Are all 8 blocks present (Date, Recipient, Greeting, Hook, Fit, Close, Signoff, Signature)? → (b) scoping
   - Are paragraphs separated by `\n\n` or `\n`? → (c) scoping
   - Is the response under 400 words? → (d) not firing
2. **Edge: long-tail JD.** Run with a 4000-word JD (copy a startup's full careers-page text). Does the output truncate mid-signoff? → (d) relevant at the long tail
3. **Edge: provoke fallback.** Set `GEMINI_API_KEY=invalid_key` locally, generate once, confirm the static fallback template appears in the UI, and check PostHog for a `cover_letter_generated` event. If the event fires with the fallback text → (e) telemetry gap confirmed (we can't tell real generation from fallback from the event alone).

**If all three reproductions show well-formatted output** — (b) hypothesis weakens; the bug is intermittent or specific to a subset of JDs. Gather a corpus of failing JDs from Dhamo's test history before writing the spec.

**If reproductions are variably formatted** — dominant hypothesis confirmed; spec ships the structured-output fix as described in §6/§7.

**R15 reminder:** This commit does **not** close B-002. The fix slice that follows closes it. BACKLOG B-002 remains `P0 🔴` until a spec lands and is implemented.

---

## 9. Related items surfaced (not in scope)

- **Cover-letter endpoint auth parallel to E-037.** `/api/cover-letter` (and the v1 re-export) is unauthed and calls Pro-tier Gemini — same cost-exposure shape as E-037 (rewrite). Worth a follow-up row after B-002 closes.
- **`ai_service.py` duplicate of `generate_cover_letter`.** `[S47-defer]` still open; the B-002 fix will need to pick one service or the other (recommend: fix in `gpt_service.py`, leave `ai_service.py` alone pending the enterprise-path cleanup decision).
- **Skill-inventory gap.** No dedicated cover-letter skill file. `.agent/skills/ats-scanner.md` lists `cover_letter` under its LLM task table but doesn't own the surface. Not blocking this work; minor doc hygiene.
- **FE prompt ↔ renderer drift.** `CoverLetterViewer` uses `ReactMarkdown` + has a `## ` header detection branch in `handleDownloadPDF`, despite the prompt forbidding markdown. The fix slice should reconcile — either drop ReactMarkdown in favor of block-by-block render or re-allow markdown in the prompt and own it deliberately.

---

*End of investigation.*
