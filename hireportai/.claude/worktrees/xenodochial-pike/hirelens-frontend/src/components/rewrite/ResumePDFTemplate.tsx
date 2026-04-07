/**
 * ResumePDFTemplate
 *
 * Hidden, print-ready HTML used as source for html2pdf.js export.
 * Renders structured rewrite data in a clean, professional resume layout
 * that matches the CNS/Business/Data Science template styles.
 */
import { forwardRef } from 'react'
import type { RewriteResponse } from '@/types'

interface ResumePDFTemplateProps {
  rewrite: RewriteResponse
}

export const ResumePDFTemplate = forwardRef<HTMLDivElement, ResumePDFTemplateProps>(
  ({ rewrite }, ref) => {
    return (
      <div
        ref={ref}
        style={{
          position: 'absolute',
          left: '-9999px',
          top: 0,
          width: '190mm',
          fontFamily: "'Times New Roman', Times, Georgia, serif",
          fontSize: '10.5pt',
          lineHeight: '1.3',
          color: '#000000',
          padding: '0',
          backgroundColor: '#ffffff',
        }}
      >
        {/* ── Header ── */}
        {rewrite.header?.name && (
          <div style={{ textAlign: 'center', marginBottom: '6px', paddingBottom: '4px', borderBottom: '1.5px solid #000' }}>
            <h1 style={{
              fontSize: '18pt',
              fontWeight: 'bold',
              letterSpacing: '0.08em',
              margin: '0 0 2px',
              color: '#000',
              textTransform: 'uppercase',
            }}>
              {rewrite.header.name}
            </h1>
            {rewrite.header.contact && (
              <p style={{
                fontSize: '9.5pt',
                color: '#333',
                margin: '0 0 2px',
                letterSpacing: '0.02em',
              }}>
                {rewrite.header.contact}
              </p>
            )}
          </div>
        )}

        {/* ── Sections ── */}
        {rewrite.sections.map((section, idx) => {
          // Skip empty sections
          const hasEntries = section.entries && section.entries.length > 0 &&
            section.entries.some(e => e.org || e.title || (e.bullets && e.bullets.length > 0))
          const hasContent = section.content && section.content.trim().length > 0
          if (!hasEntries && !hasContent) return null

          return (
            <div key={idx} style={{ marginBottom: '7px' }}>
              {/* Section heading */}
              <h2 style={{
                fontSize: '10.5pt',
                fontWeight: 'bold',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                borderBottom: '1px solid #000',
                paddingBottom: '1px',
                marginBottom: '4px',
                marginTop: idx === 0 ? '4px' : '2px',
                color: '#000',
              }}>
                {section.title}
              </h2>

              {/* Structured entries (Experience, Education, Projects, etc.) */}
              {section.entries?.map((entry, j) => {
                if (!entry.org && !entry.title && (!entry.bullets || entry.bullets.length === 0)) return null
                return (
                  <div key={j} style={{ marginBottom: '5px' }}>
                    {/* Row 1: Org + Date */}
                    {entry.org && (
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'baseline',
                        marginBottom: '0',
                      }}>
                        <strong style={{ fontSize: '10.5pt', color: '#000' }}>{entry.org}</strong>
                        {entry.date && (
                          <span style={{
                            fontSize: '10pt',
                            color: '#000',
                            whiteSpace: 'nowrap',
                            flexShrink: 0,
                            marginLeft: '12px',
                          }}>
                            {entry.date}
                          </span>
                        )}
                      </div>
                    )}
                    {/* Row 2: Title/Position */}
                    {entry.title && (
                      <p style={{
                        fontSize: '10.5pt',
                        fontStyle: 'italic',
                        color: '#000',
                        margin: '0 0 1px',
                      }}>
                        {entry.title}
                      </p>
                    )}
                    {/* Details (coursework, minor, etc.) */}
                    {entry.details?.map((d, k) => (
                      <p key={k} style={{
                        fontSize: '10pt',
                        color: '#222',
                        margin: '0 0 1px',
                        paddingLeft: '0',
                      }}>
                        {d}
                      </p>
                    ))}
                    {/* Bullet points */}
                    {entry.bullets && entry.bullets.length > 0 && (
                      <div style={{ marginTop: '1px', paddingLeft: '14px' }}>
                        {entry.bullets.map((b, k) => (
                          <p key={k} style={{
                            fontSize: '10pt',
                            color: '#000',
                            margin: '0 0 1px',
                            textIndent: '-14px',
                            paddingLeft: '0',
                            lineHeight: '1.35',
                          }}>
                            {'\u2022'} {b}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}

              {/* Content-only sections (Skills, Honors, etc.) */}
              {hasContent && (!section.entries || section.entries.length === 0) && (
                <div style={{ fontSize: '10pt', color: '#000', margin: 0 }}>
                  {section.content.split('\n').map((line, k) => (
                    <p key={k} style={{ margin: '0 0 1px', lineHeight: '1.4' }}>
                      {line}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }
)

ResumePDFTemplate.displayName = 'ResumePDFTemplate'
