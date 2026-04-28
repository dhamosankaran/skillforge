---
slug: parsing-failure-modes
title: ATS Parsing Failure Modes
display_order: 0
quiz_items:
  - question: 'Name three resume formatting choices that cause ATS parsers to silently mis-extract fields.'
    answer: 'Multi-column layouts (columns get linearized in the wrong order), text in headers/footers (often dropped entirely), and graphical elements like icon fonts or text-as-images (extracted as garbage or skipped). Tables for the experience section also commonly mis-attribute companies and titles when the parser falls back to rectangle-based extraction.'
    question_type: free_text
    difficulty: easy
    display_order: 0
  - question: 'Which file format is the safest default for an ATS submission in 2026?'
    answer: 'PDF generated from a text-based source (e.g. exported from a word processor with selectable text layers)'
    question_type: mcq
    distractors:
      - 'A scanned image-based PDF'
      - 'A .docx file with embedded SmartArt graphics'
      - 'An HTML page sent as an attachment'
    difficulty: medium
    display_order: 1
---
## Concept

An ATS does two passes on every resume: parse (extract fields and
freeform text) then rank (score against the requisition keywords).
Mis-parsing torpedoes both — a name extracted into the "skills" field
won't surface in a search; a job title parsed as the company name will
read as a missing year of experience.

The senior move is to write for the parser, not against it. Boring
single-column layouts with standard section headings parse cleanly
across the dozen ATS engines a candidate is likely to encounter
(Greenhouse, Lever, Workday, iCIMS, SuccessFactors, Taleo).

## Production

The safe-format checklist:

1. Single-column layout. No columns, no sidebars.
2. Section headings the parser recognizes: Experience, Education,
   Skills, Projects. Avoid creative headings ("My Journey", "What I
   Bring") — parsers don't pattern-match them.
3. Standard fonts. Times, Arial, Helvetica, Calibri. No icon fonts.
4. Dates as `MMM YYYY` ("Mar 2024") or `MM/YYYY` ("03/2024"). Avoid
   "present" alone in the end-date column for older roles.
5. PDF exported from a word processor, not a scan. Test by selecting
   text in the PDF — if it doesn't highlight, the ATS can't read it.
6. No headers or footers for content the recruiter must see; many
   parsers drop them.

```bash
# A two-second sanity check before submitting.
pdftotext my_resume.pdf - | less
```

If the output looks correct in plain text, the ATS will most likely
parse it correctly too.

## Examples

| Bad signal                  | What the ATS sees                           |
|-----------------------------|---------------------------------------------|
| Two-column layout           | Sentences interleaved across columns        |
| Skills as icon-font glyphs  | Empty skills section                        |
| Email in PDF header         | "No email on file"                          |
| Dates as `Q1 2024`          | Tenure not detected; experience years = 0   |
| Job title above company     | Company name = "Senior Software Engineer"   |

When in doubt, optimize for boring. Recruiters know what a clean
resume looks like; they associate the visual minimalism with seniority.
