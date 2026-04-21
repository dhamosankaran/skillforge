# B-001 Investigation — AI Resume Rewrite Drops Original Sections

**Date:** 2026-04-21
**Mode:** 1 (read-only audit; no code changes)
**BACKLOG row:** B-001 (P0, `ats-scanner`, source slice P5-S9)
**Author:** Claude Code
**R15:** B-001 is **not closed by this report** — the report is investigation output. The follow-up fix slice will close B-001.

---

## 1. File Inventory

| Concern | File path | Line range | Notes |
|---------|-----------|------------|-------|
| Route decorator (live) | `hirelens-backend/app/api/routes/rewrite.py` | 12–63 | `POST /api/rewrite` — defines `rewrite_resume` handler. Auth: none (route predates Phase-1 auth hardening; no `Depends(get_current_user)` on this legacy surface). |
| Route decorator (v1 re-export) | `hirelens-backend/app/api/v1/routes/rewrite.py` | 1–4 | Pure re-export of the legacy router: `from app.api.routes.rewrite import router`. Both URL surfaces hit the same handler. |
| Live rewrite service | `hirelens-backend/app/services/gpt_service.py` | 88–139 | `generate_resume_rewrite(resume_data, jd_requirements, template_type, major, missing_keywords, missing_skills)` — this is what the live route imports. |
| **Duplicate rewrite service** (dead) | `hirelens-backend/app/services/ai_service.py` | 89–134 | Also defines `generate_resume_rewrite` but with a 2-arg signature (no `template_type`/`major`/`missing_keywords`/`missing_skills`). **Not imported by the route.** Near-identical prompt body. Should be flagged for P6 cleanup or logged as dead-code candidate (see Section 7 follow-ups). |
| LLM router | `hirelens-backend/app/core/llm_router.py` | 32–36, 39–44, 49–93, 177–224 | `resume_rewrite` is in `REASONING_TASKS` frozenset → `_get_tier` returns `"reasoning"` → dispatches to `settings.llm_reasoning_provider` / `settings.llm_reasoning_model`. **Default per `AGENTS.md:160-161`:** `gemini` / `gemini-2.5-pro`. |
| Pydantic response schema | `hirelens-backend/app/schemas/responses.py` | 89–110 | `RewriteResponse { header: RewriteHeader, sections: List[RewriteSection], full_text: str, template_type: str = "general" }`. `RewriteSection` has `{title, content, entries: List[RewriteEntry]}`. |
| Frontend page | `hirelens-frontend/src/pages/Rewrite.tsx` | 68–472 | Orchestrator. Calls `useRewrite().runRewrite(resumeText, jobDescription)`. Renders `<ResumeEditor rewrite={rewriteResult} …/>` + handles PDF/DOCX export locally. |
| Frontend renderer | `hirelens-frontend/src/components/rewrite/ResumeEditor.tsx` | 155–321 | Branches on `isMarkdown = rewrite.sections.length === 0 && rewrite.full_text.length > 0` (line 186). Since BE always ships `sections=[]`, this is **always true** and `MarkdownPreview` renders the markdown directly via `react-markdown`. `ResumePreview` (lines 19–97, structured) is **dead as of current BE contract**. |
| Parser | `hirelens-backend/app/services/parser.py` | 1–198 | `parse_pdf` + `parse_docx` both return `{full_text, sections (dict from detect_sections), bullet_points, contact_info, formatting_hints, source_type}`. **The rewrite route does NOT call the parser** — it receives `resume_text` directly in the request body (`RewriteRequest`), which is the upstream parser output stored in `AnalysisContext` on the FE. |
| Pre-read skill | `.agent/skills/ats-scanner.md` | 23–26, 44–53 | Rewrite is owned by the ATS-scanner flow. Lists `gpt_service.py` **and** `ai_service.py` as rewrite callers — confirms the duplicate isn't an oversight in the skill file. No dedicated `rewrite` skill exists; `ats-scanner.md` is the correct skill for the fix slice. **Skill-inventory gap:** none; `ats-scanner.md` suffices. |

### Control flow (live path)

```
FE Rewrite.tsx → useRewrite().runRewrite()
  → services/api.ts:generateResumeRewrite({resume_text, job_description, template_type?, major?})
  → BE POST /api/rewrite (or /api/v1/rewrite — re-export)
  → rewrite_resume() in app/api/routes/rewrite.py
     │
     ├─ extract_skills(body.resume_text)         (services/nlp.py)
     ├─ extract_job_requirements(body.job_description)
     ├─ match_keywords(...)                       (services/keywords.py)
     │
     └─ gpt_service.generate_resume_rewrite(resume_data, jd_requirements, template_type, major, missing_keywords, missing_skills)
            │
            ├─ build prompt with resume_text[:40000]
            ├─ generate_for_task(task="resume_rewrite", prompt=..., max_tokens=8000, temperature=0.4)
            │     → llm_router._get_tier("resume_rewrite") = "reasoning"
            │     → _call_gemini(model="gemini-2.5-pro", ..., max_tokens=8000)
            │     → response.text  (free-form markdown string)
            │
            └─ return RewriteResponse(
                  header=RewriteHeader(),        # empty {name:"", contact:""}
                  sections=[],                    # always empty
                  full_text=markdown.strip(),     # entire LLM output as one string
                  template_type=template_type,
              )
  → FE ResumeEditor: isMarkdown=true → <MarkdownPreview content={full_text}/>
```

**Zero parser calls, zero JSON schema enforcement, zero section splitting.**

---

## 2. Prompt Template (Verbatim)

From `app/services/gpt_service.py:104-121` (live path):

```python
prompt = f"""You are an expert resume writer specializing in ATS optimization.
Rewrite the following resume to maximize ATS compatibility for the target role.

Rules:
1. Maintain the EXACT same sections as the original (Summary, Experience, Skills, Education, etc.)
2. Improve bullet points with quantified achievements (numbers, percentages, dollar amounts)
3. Incorporate the missing keywords naturally into relevant sections
4. Use strong action verbs at the start of each bullet
5. Keep the tone professional and confident
6. Output in clean markdown with ## headers for each section, - for bullet points
7. Do NOT add sections that weren't in the original resume
8. Do NOT remove any jobs, education entries, or skills — only improve the language

Missing keywords to incorporate: {missing_kw_str}
Target role: {jd_title}

Original resume:
{resume_text}"""
```

Call site:
```python
markdown = generate_for_task(
    task="resume_rewrite", prompt=prompt, max_tokens=8000, temperature=0.4,
)
```

No `system_prompt` argument, no `json_mode=True`, no structured-output schema. Pure free-form string generation.

### Prompt characteristics

| Property | Value | Notes |
|---------|-------|-------|
| Enforces full-document output? | **Yes — strongly** | Rules 1, 7, 8 are explicit. "Maintain the EXACT same sections", "Do NOT add sections", "Do NOT remove any jobs, education entries, or skills". |
| Names every expected section? | **No** | Rule 1 lists examples ("Summary, Experience, Skills, Education, etc.") but does not enumerate the candidate's actual sections. The model has to infer the section list from the raw resume text. |
| Pins a template? | **No** | `template_type` is accepted in the service signature but **never surfaced into the prompt** — `gpt_service.py:88-122` ignores `template_type` / `major` entirely when building the prompt. (The duplicate in `ai_service.py` doesn't accept the argument at all.) |
| Structure enforcement? | **Free-form** | No JSON schema, no XML tags, no section-delimiter contract. Just "output in clean markdown with ## headers." |
| Truncates input? | **Yes** | `resume_text = resume_data.get("full_text", "")[:40000]`. ~8k–10k tokens of input. For a 4-page resume this can silently drop the tail (late experience, education, certifications). |

### Token budget

| Knob | Value | Risk |
|------|-------|------|
| `max_tokens=8000` on the Gemini call | Hard cap on output tokens | **Gemini 2.5 Pro has a thinking budget that consumes from the same pool.** `llm_router.py:81-93` has an explicit `logger.warning` that exists *precisely for this failure mode*: "a finish_reason like MAX_TOKENS (e.g. thinking budget consumed the cap)." If thinking consumes 3k-6k tokens on a complex rewrite, only 2k-5k are left for output — not enough for a full 2-page resume rewrite. |
| `temperature=0.4` | Lower-variance output | Fine; not implicated. |
| Input truncation at 40000 chars | Pre-LLM | Silent. Long resumes (dense 4-page, academic CVs) may arrive at the LLM with the tail missing — the model physically cannot rewrite what it wasn't shown. |
| Truncation / graceful degradation | **None in-prompt** | Prompt never tells the model "if input was truncated, note it." Exception handler in `gpt_service.py:133-139` returns the **original resume text** (not the partial rewrite) as `full_text` on any failure — so "rewrite returned the original text" is a valid failure mode users could hit. |

---

## 3. Response Handling Flow

```
LLM returns:     markdown: str     (may be empty on MAX_TOKENS; may be partial; may lack sections)
                       │
                       ▼
gpt_service.py:127-132:
    RewriteResponse(
        header=RewriteHeader(),        # empty stub — name="", contact=""
        sections=[],                    # always empty list
        full_text=markdown.strip(),
        template_type=template_type,
    )
                       │
                       ▼
FastAPI → JSON over wire
                       │
                       ▼
FE useRewrite hook → rewriteResult: RewriteResponse
                       │
                       ▼
ResumeEditor.tsx:186
    const isMarkdown = rewrite.sections.length === 0 && rewrite.full_text.length > 0
    // sections is ALWAYS [] on the current contract → isMarkdown = full_text is non-empty
                       │
                       ├─ isMarkdown = true  → <MarkdownPreview content={rewrite.full_text}/>
                       │                       (renders via react-markdown; no filtering, no section drop)
                       │
                       └─ isMarkdown = false → <ResumePreview rewrite={...}/>
                                               (structured renderer — DEAD PATH under current BE contract)
```

### Where sections could be dropped between LLM and FE render

Scanning each link in the chain:

| Hop | Drops sections? | Evidence |
|-----|-----------------|----------|
| LLM response → `markdown` string | **Yes — possible (root cause candidate)** | Free-form output; no schema enforcement; Gemini 2.5 Pro thinking budget can truncate or summarize under MAX_TOKENS. |
| `markdown.strip()` → `full_text` | No | `.strip()` only trims leading/trailing whitespace. |
| `sections=[]` on BE | N/A | Sections aren't populated at all — there's nothing to drop because nothing was built. |
| Pydantic serialization | No | Standard JSON encode; no filtering. |
| HTTP → FE | No | No middleware rewrites the body. |
| `ResumeEditor` isMarkdown branch | No | `MarkdownPreview` just hands `full_text` to `react-markdown` as the entire `children` prop. Every H2/bullet the LLM emitted gets rendered. |
| `MarkdownPreview` component overrides | No | `h1`/`h2`/`h3`/`p`/`ul`/`li`/`strong`/`em`/`hr` all render identically to default, just with styling. No content filtering. |

### Export-path regression (separate bug — not B-001's user-visible symptom)

`Rewrite.tsx:86-309` (PDF) and `utils/docxExport.ts` (DOCX, via `downloadResumeDocx`) both iterate `r.sections` (e.g., `Rewrite.tsx:130`, `230`). Since BE always ships `sections=[]`, **these paths produce empty PDFs/DOCX with only a header** (and the header is also empty today — `RewriteHeader()` is a `name=""` stub). This is a second, latent bug: the structured renderer was presumably the original product intent; somewhere in the contract migration BE was simplified to markdown-only but the export paths weren't migrated. Surfacing as a follow-up (E-0xx candidate) — **not B-001's root cause**, but worth logging in the fix slice.

---

## 4. Root Cause Hypothesis

Per prompt B.4: assign each P5-S9 branch a probability.

### (a) Prompt doesn't enforce full-document output — **LOW**

**Evidence against:**
- Rules 1, 7, 8 in the prompt are *unusually* direct: "Maintain the EXACT same sections", "Do NOT add sections that weren't in the original resume", "Do NOT remove any jobs, education entries, or skills — only improve the language."
- Rule 6 pins the output format: "clean markdown with ## headers for each section, - for bullet points."

**Caveats:**
- Prompt doesn't enumerate the candidate's actual section list — the model has to infer it from raw text. For resumes with unusual section names ("Research", "Teaching", "Patents", "Selected Publications"), the model might collapse or re-label them.
- `template_type` is accepted but ignored in prompt construction — if a user picks "academic" or "tech", the prompt is identical. Possible minor factor but doesn't explain "summary instead of full rewrite."
- No explicit "if you must abbreviate, never drop a section header — reply with the header + `[truncated]`" instruction. A well-behaved model would still obey Rule 8; a thinking-budget-pressured model might silently summarize.

**Verdict:** prompt-quality is not the most likely dominant cause. It's already near the ceiling of what prose instructions can enforce.

### (b) Token limit truncating response — **HIGH**

**Evidence for:**
- `max_tokens=8000` is the hard cap on the Gemini call. This is the output-side cap, and under Gemini 2.5 Pro this pool is **shared with the model's thinking tokens**.
- `llm_router.py:81-93` has an **explicit `logger.warning`** for empty-text responses calling out "a finish_reason like MAX_TOKENS (e.g. thinking budget consumed the cap)." The router author has already identified this exact failure mode for other reasoning-tier calls.
- A 2-page resume is ~800-1200 words ~ ~1500-2000 output tokens. A rewrite of comparable length needs ~2000 output tokens. If thinking consumes 3000-6000 tokens, the effective output budget drops to 2000-5000 — right at the edge for 2-page, insufficient for 4-page.
- Input truncation at `[:40000]` characters (~8-10k tokens) is a **secondary channel for section loss**: if a long resume's tail gets chopped before the prompt, the LLM literally cannot rewrite what it wasn't shown. The user sees "my education/awards section is missing" because it never reached the model.
- Fallback path (`except Exception: return RewriteResponse(..., full_text=resume_text, ...)`) returns the **original text**, not a truncated rewrite. So "the rewrite is just a summary" cannot come from this fallback. But a **successful-but-MAX_TOKENS-hit** response comes back as a partial markdown string, which `markdown.strip()` happily wraps and returns.

**Evidence against:**
- Can't 100% distinguish "model summarized on its own" from "model hit MAX_TOKENS and stopped mid-rewrite" without logs. Both produce a shorter-than-expected output.

**Verdict:** strongest candidate by evidence, especially given the router's own documented warning for this failure mode on the same tier. **Likely primary root cause.**

### (c) Frontend display dropping sections — **RULED OUT**

**Evidence:**
- `ResumeEditor.tsx:186` forces the markdown path for every current response (`sections=[]` from BE → `isMarkdown=true`).
- `MarkdownPreview` (lines 100-153) calls `react-markdown` with no filtering, no custom component that drops children — all H1/H2/H3/P/UL/LI map to styled equivalents.
- No conditional rendering on section count, no "if more than N sections, hide the rest" logic.

Export-path sections-drop is a separate latent issue (Section 3 above), not the user-visible bug in B-001.

### (d) Parser dropping sections before rewrite — **LOW**

**Evidence:**
- Parser is not on the rewrite-route critical path. `app/api/routes/rewrite.py:13` receives `body.resume_text` directly as a string. The FE gets this text from `AnalysisContext.state.result?.resume_text` (`Rewrite.tsx:83`), which was populated during the **upstream /analyze call**. So "parser" here means "the parser that ran during the user's last analyze call, some time earlier."
- `parser.py::parse_pdf` and `parse_docx` concatenate all page text into `full_text` via `"\n".join(text_parts)` → `clean_resume_text(full_text)`. No section-level filtering at this stage; every character the extractor got is preserved (subject to text cleaner).
- `text_cleaner.clean_resume_text` normalizes whitespace — not a section-dropper.
- `detect_sections` is a separate dict on the `sections` key (not `full_text`) and isn't piped into the rewrite prompt.

**Caveats:**
- Complex PDF layouts (multi-column, tables with rotated text, image-embedded bullet points) can silently lose content at the `pdfplumber.extract_text()` stage. `formatting_hints` flags `multi_column` / `has_tables` / `has_images` but doesn't alert the rewrite route.
- Resumes with very tight visual layouts can produce interleaved text order from multi-column extraction — the LLM sees a garbled-ordered wall of text, might interpret as "no education section" and drop it from output.

**Verdict:** possible contributing factor for specific resume formats; unlikely to explain the broad user-reported symptom.

### Summary

| Branch | Probability | Primary evidence |
|--------|-------------|------------------|
| (a) Prompt doesn't enforce | **LOW** | Prompt is explicit; rules 1/7/8 are near-ceiling for prose instructions. |
| (b) Token limit truncating | **HIGH** | `max_tokens=8000` on Gemini 2.5 Pro with thinking budget; router has documented warning for this exact mode; input `[:40000]` truncation; fallback returns original (so partial-response is the remaining explanation for "summary-shaped output"). |
| (c) Frontend dropping | **RULED OUT** | `MarkdownPreview` renders `full_text` verbatim; no filter. |
| (d) Parser dropping | **LOW** | Parser off the rewrite critical path; may contribute for multi-column/table PDFs but not the dominant cause. |

### Caveat — needs manual repro to fully confirm

While (b) has the strongest documented mechanism, **"needs manual repro"** for definitive confirmation. The confirming/refuting artifacts are listed in Section 7.

---

## 5. Slice Classification Recommendation

**Recommended: spec-then-impl (per CLAUDE.md R16).**

### Reasoning

Even if (b) token budget is confirmed as the primary cause, the repair space involves real design decisions that need product input:

1. **Output shape:** stay free-form markdown, OR move to structured JSON (per-section keyed output) with a schema enforced by the router's `json_mode=True`. Structured output would fix the export-path regression (Section 3) **and** make section preservation machine-verifiable post-hoc ("did the response contain every section we sent in?") — but it requires a BE contract change and FE renderer changes.
2. **Per-section vs full rewrite:** see Q3 below. Per-section chunking sidesteps the `max_tokens` cliff by bounding each LLM call's output budget, but introduces latency (N sequential calls) and a new UX decision (streaming? progress indicator?).
3. **Token budget strategy:** raise to 16k? Switch to `gemini-2.5-flash-thinking` (cheaper, still reasoning-capable)? Disable thinking entirely? Each has ops cost implications.
4. **Preservation guarantees:** Q1 and Q2 (preserve structure/order vs restructure/optimize) are product calls that shape the prompt + the post-validation logic.

A "direct-fix" (single slice, no spec) would work **only** if the fix is "bump `max_tokens=8000` to `max_tokens=16000`" — a one-line mechanical change. That's unlikely to be sufficient on its own (doesn't fix input truncation, doesn't fix the broken export paths, doesn't address per-section chunking), and even if it turns out to be the minimal viable patch, locking a spec first makes the success criteria explicit (e.g., "3-page CV rewritten with all 8 sections preserved, tested against a fixture set").

**Spec path:** `docs/specs/phase-5/NN-resume-rewrite-fix.md` covering the four Qs below + minimum acceptance criteria (e.g., "resumes up to X pages preserve all detected sections in output," structured vs markdown contract decision, export-path re-wire).

**Not** "further investigation needed" — the evidence is strong enough to enter design. The manual repro (Section 7) should happen **during** the spec-then-impl slice, not as a separate investigation gate.

---

## 6. Four Open Product Questions + Recommendations

### Q1 — Preserve original section structure, or restructure for ATS optimization?

**Recommendation:** Preserve original section structure (default). Offer an opt-in "ATS-optimize structure" toggle later if data supports it.
**Rationale:** The user-contract word is "rewrite" — users expect a better version of *what they wrote*, not a re-architected document. Restructuring changes the document's identity and can strip candidate-unique sections ("Selected Publications", "Teaching", "Patents") that don't fit a generic ATS template. Restructuring is a separate, larger feature that deserves its own UX.
**Label:** [PRODUCT CALL]

### Q2 — Preserve section ordering, or optimize ordering?

**Recommendation:** Preserve ordering (default). Same reasoning as Q1 — order is part of the candidate's voice. Reorder only as an explicit opt-in.
**Rationale:** The ATS-reorder question (e.g., "Skills before Experience for keyword-dense roles?") has a legitimate answer space, but changing order silently violates user expectation. And silent reordering is indistinguishable from "it dropped my sections" to a user who scans quickly for their education block.
**Label:** [PRODUCT CALL]

### Q3 — Per-section rewrite, full rewrite, or both?

**Recommendation:** Full rewrite by default, with per-section regeneration as a post-rewrite affordance (click a section → "regenerate this section only"). This also cleanly solves the token-budget problem: per-section calls cap each response at a knowable size.
**Rationale:** Full rewrite matches the current UX and user expectation (one click, complete output). Per-section is a *power-user* iteration mode after the initial pass — not a replacement. Implementing both satisfies the "full rewrite" default and gives an escape hatch for long resumes (fall back to per-section when input exceeds a length threshold).
**Label:** [BOTH] — UX decision (product) + implementation routing (engineering).

### Q4 — Token budget: does the current prompt account for resume length (2-page vs 4-page)?

**Recommendation:** **No, it does not** — and that needs to change. Recommend either (a) dynamic `max_tokens` sizing based on input length (heuristic: `max(8000, 2 × input_tokens)`), (b) per-section calls with a per-section cap, or (c) model switch to a reasoning model without thinking-budget contention (e.g., `gemini-2.5-flash-thinking` with `thinkingBudget=0`, or OpenAI `gpt-4o` via the router).
**Rationale:** Fixed 8k cap is brittle across the range of resumes users upload, and Gemini 2.5 Pro's thinking pool consuming from the same budget compounds the risk. Per-section chunking is the most resilient fix but has latency cost. Input truncation at 40k chars also needs re-examination — either raise the cap or reject overlong uploads with a clear error rather than silently dropping the tail.
**Label:** [ENGINEERING CALL]

---

## 7. What Would Change the Hypothesis

The following manual repros and log queries would promote (b) from "HIGH" to "confirmed" — or demote it if (a) or (d) turn out to dominate:

1. **Grep production logs for the router's own warning:** `"Gemini returned empty text"` in the backend log stream over the last 30 days. If this fires frequently on `task=resume_rewrite` calls, (b) is confirmed. Absence doesn't rule out (b) — partial responses don't trigger the warning (it's guarded on `if not text`).
2. **Instrument a one-shot logger** in `gpt_service.py:124-126`: log `len(markdown)`, `markdown[:200]`, `markdown[-200:]` to inspect the tail. If the response ends mid-sentence / mid-bullet, (b) is confirmed. If the response ends cleanly with a summary paragraph, (a) is more likely.
3. **Repro with a known-long resume** (4-page CV, ~3000 words). If the output is truncated ~60-70% through the expected length, that's MAX_TOKENS behavior. If the output is a concise 2-page summary of a 4-page input, that's (a) — the model is electing to summarize.
4. **Repro with a 1-page resume** (~300 words). If the 1-page output is *also* missing sections, (b) is less likely (token budget is ample for 1-page) and (a) / (d) rise in relative probability.
5. **Repro with a multi-column PDF** (e.g., a European CV template). If section loss tracks to `formatting_hints.multi_column=true` specifically, (d) parser-side is contributing.
6. **Compare `resume_data["sections"]` dict** (detected section names) against the rendered markdown's `## ` headings. If the LLM output systematically drops the 4th+ section regardless of length, that's a section-ordering effect — not purely token-budget.

### Dead-code / hygiene follow-ups surfaced during the audit (not B-001 scope, logging for P6 cleanup):

- `app/services/ai_service.py::generate_resume_rewrite` is an unused duplicate of `gpt_service.py::generate_resume_rewrite`. Route imports from `gpt_service`; `ai_service` variant is uncalled. Flag for deletion in P6 cleanup or log as a new BACKLOG row if we prefer explicit tracking.
- `ResumePreview` component (`ResumeEditor.tsx:19-97`) is dead under the current BE contract (`sections` is always `[]`). Either re-populate `sections` on BE (structured output) or delete `ResumePreview`.
- PDF export (`Rewrite.tsx:86-309`) and DOCX export (`utils/docxExport.ts`) both iterate `r.sections` which is always `[]` → they produce empty documents. Latent bug; not B-001 scope but should be logged as its own row if not already present.

---

## R15 Confirmation

This report is **investigation output**, not a fix. **B-001 is not closed by this report.** The fix slice that follows (spec-then-impl per §5) will close B-001 when the fix is shipped and verified.
