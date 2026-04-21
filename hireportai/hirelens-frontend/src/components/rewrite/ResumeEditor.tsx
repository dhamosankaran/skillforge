import { useState } from 'react'
import { motion } from 'framer-motion'
import { Copy, Check, FileText, Download, FileDown, RefreshCw } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { RewriteResponse, RewriteSection } from '@/types'

interface ResumeEditorProps {
  original: string
  rewrite: RewriteResponse | null
  isLoading: boolean
  onRegenerate?: () => void
  onRegenerateSection?: (idx: number, section: RewriteSection) => void
  regeneratingIdx?: number | null
  onDownloadPDF?: () => void
  onDownloadDocx?: () => void
  isExportingPDF?: boolean
  isRegenerating?: boolean
}

/** Full formatted resume preview — structured sections */
function ResumePreview({
  rewrite,
  onRegenerateSection,
  regeneratingIdx,
}: {
  rewrite: RewriteResponse
  onRegenerateSection?: (idx: number, section: RewriteSection) => void
  regeneratingIdx?: number | null
}) {
  return (
    <div className="p-8 bg-white rounded-2xl shadow-card min-h-[400px]" style={{ fontFamily: 'Times New Roman, serif' }}>
      {/* Header */}
      {rewrite.header?.name && (
        <div className="text-center mb-5 pb-3 border-b-2 border-gray-800">
          <h1 className="text-[20px] font-bold text-gray-900 tracking-wide uppercase">
            {rewrite.header.name}
          </h1>
          {rewrite.header.contact && (
            <p className="text-[11px] text-gray-600 mt-1.5 tracking-wide">{rewrite.header.contact}</p>
          )}
        </div>
      )}

      {/* Sections */}
      {rewrite.sections.map((section, i) => (
        <div
          key={i}
          data-testid={`rewrite-section-${i}`}
          data-section-title={section.title}
          style={{ marginTop: i === 0 ? 0 : '14px' }}
        >
          {/* Section heading + per-section regenerate */}
          <div className="flex items-center justify-between border-b border-gray-800 pb-1 mb-3">
            <h2 className="text-[12px] font-bold text-gray-900 tracking-[0.15em] uppercase">
              {section.title}
            </h2>
            {onRegenerateSection && section.title.toLowerCase() !== 'contact' && (
              <button
                type="button"
                onClick={() => onRegenerateSection(i, section)}
                disabled={regeneratingIdx === i}
                aria-label={`Regenerate ${section.title} section`}
                title="Regenerate this section"
                className="text-[10px] text-gray-500 hover:text-gray-900 flex items-center gap-1 disabled:opacity-50 transition-colors"
              >
                <RefreshCw
                  size={10}
                  className={regeneratingIdx === i ? 'animate-spin' : ''}
                />
                {regeneratingIdx === i ? 'Regenerating…' : 'Regenerate'}
              </button>
            )}
          </div>

          {/* Entries */}
          {section.entries?.length > 0 &&
            section.entries.map((entry, j) => (
              <div key={j} className="mb-4">
                {entry.org && (
                  <div className="flex justify-between items-baseline gap-4">
                    <span className="font-bold text-gray-900 text-[11px]">{entry.org}</span>
                    {entry.date && (
                      <span className="text-gray-600 text-[10.5px] whitespace-nowrap">{entry.date}</span>
                    )}
                  </div>
                )}
                {entry.title && (
                  <p className="text-gray-700 text-[11px] italic mt-0.5">{entry.title}</p>
                )}
                {entry.details?.map((d, k) => (
                  <p key={k} className="text-gray-600 text-[10.5px] mt-0.5">{d}</p>
                ))}
                {entry.bullets?.length > 0 && (
                  <ul className="mt-1.5 space-y-1">
                    {entry.bullets.map((b, k) => (
                      <li key={k} className="flex gap-2 text-[10.5px] text-gray-700 leading-relaxed">
                        <span className="flex-shrink-0 mt-0.5">•</span>
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}

          {/* Content fallback (Skills, Honors, etc.) */}
          {section.content && (!section.entries || section.entries.length === 0) && (
            <div className="text-[10.5px] text-gray-700 leading-relaxed">
              {section.content.split('\n').map((line, k) => {
                const trimmed = line.trim()
                if (!trimmed) return null
                // Render "Category: items" lines with bold category label
                const colonIdx = trimmed.indexOf(':')
                if (colonIdx > 0 && colonIdx < 40) {
                  return (
                    <p key={k} className="mb-0.5">
                      <span className="font-bold text-gray-900">{trimmed.slice(0, colonIdx + 1)}</span>
                      {trimmed.slice(colonIdx + 1)}
                    </p>
                  )
                }
                return <p key={k} className="mb-0.5">{trimmed}</p>
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// The old "empty-sections → render full_text as markdown" branch is kept as a
// defensive fallback only; post spec #51 the backend always populates
// `sections`, so this renderer shouldn't fire in practice.
/** Markdown-rendered resume preview */
function MarkdownPreview({ content }: { content: string }) {
  return (
    <div className="p-8 bg-bg-elevated/60 backdrop-blur-sm border border-accent-primary/10 rounded-2xl shadow-card min-h-[400px]">
      <div className="prose-resume">
        <ReactMarkdown
          components={{
            h1: ({ children }) => (
              <h1 className="text-xl font-bold text-text-primary mb-4 pb-2 border-b border-contrast/10">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-lg font-semibold text-accent-primary mt-6 mb-3 pb-1 border-b border-contrast/[0.06] uppercase tracking-wide text-sm">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-sm font-semibold text-text-primary mt-4 mb-2">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="text-sm text-text-primary/90 leading-relaxed mb-3">
                {children}
              </p>
            ),
            ul: ({ children }) => (
              <ul className="space-y-1.5 mb-4 ml-1">
                {children}
              </ul>
            ),
            li: ({ children }) => (
              <li className="flex gap-2 text-sm text-text-primary/85 leading-relaxed">
                <span className="text-accent-primary/60 flex-shrink-0 mt-0.5">•</span>
                <span>{children}</span>
              </li>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-text-primary">{children}</strong>
            ),
            em: ({ children }) => (
              <em className="italic text-text-secondary">{children}</em>
            ),
            hr: () => (
              <hr className="border-contrast/[0.06] my-4" />
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

export function ResumeEditor({
  original,
  rewrite,
  isLoading,
  onRegenerate,
  onRegenerateSection,
  regeneratingIdx,
  onDownloadPDF,
  onDownloadDocx,
  isExportingPDF,
  isRegenerating,
}: ResumeEditorProps) {
  const [copiedFull, setCopiedFull] = useState(false)

  const handleCopyFull = async () => {
    if (!rewrite) return
    await navigator.clipboard.writeText(rewrite.full_text)
    setCopiedFull(true)
    setTimeout(() => setCopiedFull(false), 2000)
  }

  const handleDownloadTxt = () => {
    if (!rewrite) return
    const blob = new Blob([rewrite.full_text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'resume-rewrite.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  // Whether this rewrite uses markdown (full_text only, no structured sections)
  const isMarkdown = rewrite && rewrite.sections.length === 0 && rewrite.full_text.length > 0

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="space-y-3 p-6 bg-bg-surface/50 rounded-2xl border border-contrast/[0.06]">
              <div className="h-5 w-32 bg-bg-elevated rounded-full animate-pulse" />
              <div className="h-px bg-bg-elevated" />
              {[...Array(10)].map((_, j) => (
                <div
                  key={j}
                  className={`h-3 bg-bg-elevated rounded-full animate-pulse ${j % 3 === 2 ? 'w-3/4' : 'w-full'}`}
                  style={{ animationDelay: `${j * 100}ms` }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!rewrite) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-2xl bg-accent-primary/8 border border-accent-primary/15 flex items-center justify-center mb-5">
          <FileText size={28} className="text-accent-primary/60" />
        </div>
        <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
          No Rewrite Yet
        </h3>
        <p className="text-sm text-text-secondary max-w-sm leading-relaxed">
          Click &quot;Generate AI Rewrite&quot; to get an ATS-optimized version of your resume.
        </p>
      </div>
    )
  }

  return (
    <div>
      {/* Action bar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
          <span className="text-xs font-medium text-accent-primary uppercase tracking-wider">
            AI Optimized
          </span>
        </div>
        <div className="flex items-center gap-1">
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              disabled={isRegenerating}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={12} className={isRegenerating ? 'animate-spin' : ''} />
              Regenerate
            </button>
          )}
          <button
            onClick={handleCopyFull}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors"
          >
            {copiedFull ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            {copiedFull ? 'Copied!' : 'Copy'}
          </button>
          <button
            onClick={handleDownloadTxt}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors"
          >
            <Download size={12} />
            .txt
          </button>
          {onDownloadPDF && (
            <button
              onClick={onDownloadPDF}
              disabled={isExportingPDF}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 transition-colors disabled:opacity-50"
            >
              <Download size={12} />
              {isExportingPDF ? 'Exporting...' : 'PDF'}
            </button>
          )}
          {onDownloadDocx && (
            <button
              onClick={onDownloadDocx}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 transition-colors"
            >
              <FileDown size={12} />
              DOCX
            </button>
          )}
        </div>
      </div>

      {/* Two column: original vs rewrite */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Original */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-text-muted" />
            <h3 className="text-xs font-medium text-text-muted uppercase tracking-wider">Original</h3>
          </div>
          <div className="p-5 bg-bg-surface/50 border border-contrast/[0.06] rounded-2xl shadow-card min-h-[400px]">
            <pre className="font-mono text-[11px] text-text-secondary whitespace-pre-wrap leading-relaxed">
              {original.slice(0, 3000) || 'Original resume text not available.'}
            </pre>
          </div>
        </div>

        {/* Rewrite */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
            <h3 className="text-xs font-medium text-accent-primary uppercase tracking-wider">
              ATS-Optimized Resume
            </h3>
          </div>
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {isMarkdown ? (
              <MarkdownPreview content={rewrite.full_text} />
            ) : (
              <ResumePreview
                rewrite={rewrite}
                onRegenerateSection={onRegenerateSection}
                regeneratingIdx={regeneratingIdx}
              />
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
