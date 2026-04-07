/**
 * DOCX export utilities for Resume and Cover Letter.
 * Generates editable .docx files using the `docx` library.
 */
import {
  Document,
  Paragraph,
  TextRun,
  AlignmentType,
  BorderStyle,
  TabStopPosition,
  TabStopType,
  Packer,
} from 'docx'
import { saveAs } from 'file-saver'
import type { RewriteResponse, CoverLetterResponse } from '@/types'

/* ────────────────────────────── Resume DOCX ────────────────────────────── */

export async function downloadResumeDocx(rewrite: RewriteResponse): Promise<void> {
  const children: Paragraph[] = []

  // ── Header: Name ──
  if (rewrite.header?.name) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 40 },
        children: [
          new TextRun({
            text: rewrite.header.name.toUpperCase(),
            bold: true,
            size: 32, // 16pt
            font: 'Times New Roman',
          }),
        ],
      })
    )
  }

  // ── Header: Contact ──
  if (rewrite.header?.contact) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 80 },
        border: {
          bottom: { style: BorderStyle.SINGLE, size: 6, color: '000000' },
        },
        children: [
          new TextRun({
            text: rewrite.header.contact,
            size: 19, // 9.5pt
            font: 'Times New Roman',
            color: '333333',
          }),
        ],
      })
    )
  }

  // ── Sections ──
  for (const section of rewrite.sections) {
    const hasEntries =
      section.entries &&
      section.entries.length > 0 &&
      section.entries.some((e) => e.org || e.title || (e.bullets && e.bullets.length > 0))
    const hasContent = section.content && section.content.trim().length > 0
    if (!hasEntries && !hasContent) continue

    // Section heading text
    children.push(
      new Paragraph({
        spacing: { before: 160, after: 0 },
        children: [
          new TextRun({
            text: section.title.toUpperCase(),
            bold: true,
            size: 21,
            font: 'Times New Roman',
          }),
        ],
      })
    )
    // Solid line below heading (separate paragraph with top border)
    children.push(
      new Paragraph({
        spacing: { before: 0, after: 60 },
        border: {
          top: { style: BorderStyle.SINGLE, size: 6, color: '000000', space: 1 },
        },
        children: [],
      })
    )

    // Entries
    if (section.entries) {
      for (const entry of section.entries) {
        if (!entry.org && !entry.title && (!entry.bullets || entry.bullets.length === 0)) continue

        // Org + Date on same line using tab stops
        if (entry.org) {
          children.push(
            new Paragraph({
              spacing: { before: 40, after: 0 },
              tabStops: [
                {
                  type: TabStopType.RIGHT,
                  position: TabStopPosition.MAX,
                },
              ],
              children: [
                new TextRun({
                  text: entry.org,
                  bold: true,
                  size: 21,
                  font: 'Times New Roman',
                }),
                ...(entry.date
                  ? [
                      new TextRun({
                        text: '\t' + entry.date,
                        size: 20,
                        font: 'Times New Roman',
                      }),
                    ]
                  : []),
              ],
            })
          )
        }

        // Title (italic)
        if (entry.title) {
          children.push(
            new Paragraph({
              spacing: { after: 0 },
              children: [
                new TextRun({
                  text: entry.title,
                  italics: true,
                  size: 21,
                  font: 'Times New Roman',
                }),
              ],
            })
          )
        }

        // Details
        if (entry.details) {
          for (const d of entry.details) {
            children.push(
              new Paragraph({
                spacing: { after: 0 },
                children: [
                  new TextRun({
                    text: d,
                    size: 19,
                    font: 'Times New Roman',
                  }),
                ],
              })
            )
          }
        }

        // Bullets
        if (entry.bullets) {
          for (const b of entry.bullets) {
            children.push(
              new Paragraph({
                spacing: { after: 10 },
                indent: { left: 180, hanging: 180 },
                children: [
                  new TextRun({
                    text: '\u2022 ' + b,
                    size: 19,
                    font: 'Times New Roman',
                  }),
                ],
              })
            )
          }
        }
      }
    }

    // Content-only sections (Skills, Honors)
    if (hasContent && (!section.entries || section.entries.length === 0)) {
      const lines = section.content.split('\n')
      for (const line of lines) {
        if (!line.trim()) continue
        children.push(
          new Paragraph({
            spacing: { after: 20 },
            children: [
              new TextRun({
                text: line,
                size: 19,
                font: 'Times New Roman',
              }),
            ],
          })
        )
      }
    }
  }

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 720, // 0.5 inch
              bottom: 720,
              left: 720,
              right: 720,
            },
          },
        },
        children,
      },
    ],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, 'optimized-resume.docx')
}

/* ────────────────────────── Cover Letter DOCX ────────────────────────── */

export async function downloadCoverLetterDocx(
  coverLetter: CoverLetterResponse,
  tone: string
): Promise<void> {
  const lines = coverLetter.cover_letter.split('\n').filter((l) => l.trim())
  const children: Paragraph[] = []

  for (const line of lines) {
    const trimmed = line.trim()

    // Detect greeting
    const isGreeting = trimmed.startsWith('Dear ')
    // Detect sign-off
    const isSignoff = /^(Sincerely|Best regards|Regards|Warm regards|Respectfully|Respectfully yours),?\s*$/i.test(
      trimmed
    )
    // Detect name after sign-off (short line)
    const prevNonEmpty = children.length > 0 ? lines[lines.indexOf(line) - 1]?.trim() || '' : ''
    const isNameLine =
      /^(Sincerely|Best regards|Regards|Warm regards|Respectfully|Respectfully yours),?\s*$/i.test(
        prevNonEmpty
      ) && trimmed.length < 60

    if (isGreeting) {
      children.push(
        new Paragraph({
          spacing: { before: 200, after: 200 },
          children: [
            new TextRun({
              text: trimmed,
              size: 22,
              font: 'Times New Roman',
            }),
          ],
        })
      )
    } else if (isSignoff) {
      children.push(
        new Paragraph({
          spacing: { before: 300, after: 40 },
          children: [
            new TextRun({
              text: trimmed,
              size: 22,
              font: 'Times New Roman',
            }),
          ],
        })
      )
    } else if (isNameLine) {
      children.push(
        new Paragraph({
          spacing: { before: 200, after: 0 },
          children: [
            new TextRun({
              text: trimmed,
              bold: true,
              size: 22,
              font: 'Times New Roman',
            }),
          ],
        })
      )
    } else {
      // Regular paragraph or header info
      children.push(
        new Paragraph({
          spacing: { after: 160 },
          children: [
            new TextRun({
              text: trimmed,
              size: 22,
              font: 'Times New Roman',
            }),
          ],
        })
      )
    }
  }

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 1080, // 0.75 inch
              bottom: 1080,
              left: 1080,
              right: 1080,
            },
          },
        },
        children,
      },
    ],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `cover-letter-${tone}.docx`)
}
