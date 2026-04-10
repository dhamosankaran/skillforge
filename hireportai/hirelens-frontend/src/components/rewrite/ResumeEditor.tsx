import { useState } from 'react'
import { motion } from 'framer-motion'
import { Copy, Check, FileText, Download, FileDown } from 'lucide-react'
import type { RewriteResponse } from '@/types'

interface ResumeEditorProps {
  original: string
  rewrite: RewriteResponse | null
  isLoading: boolean
  onDownloadPDF?: () => void
  onDownloadDocx?: () => void
  isExportingPDF?: boolean
}

/** Full formatted resume preview */
function ResumePreview({ rewrite }: { rewrite: RewriteResponse }) {
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
        <div key={i} style={{ marginTop: i === 0 ? 0 : '14px' }}>
          {/* Section heading */}
          <h2 className="text-[12px] font-bold text-gray-900 tracking-[0.15em] uppercase border-b border-gray-800 pb-1 mb-3">
            {section.title}
          </h2>

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

          {/* Content fallback */}
          {section.content && (!section.entries || section.entries.length === 0) && (
            <p className="text-[10.5px] text-gray-700 leading-relaxed whitespace-pre-wrap">
              {section.content}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

export function ResumeEditor({ original, rewrite, isLoading, onDownloadPDF, onDownloadDocx, isExportingPDF }: ResumeEditorProps) {
  const [copiedFull, setCopiedFull] = useState(false)

  const handleCopyFull = async () => {
    if (!rewrite) return
    await navigator.clipboard.writeText(rewrite.full_text)
    setCopiedFull(true)
    setTimeout(() => setCopiedFull(false), 2000)
  }

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
          Select a template, enter your major, then click &quot;Generate AI Rewrite&quot; to get an ATS-optimized version of your resume.
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
            AI Optimized — {rewrite.template_type === 'data_science' ? 'Data Science' : rewrite.template_type === 'business' ? 'Business' : 'General/STEM'} Template
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopyFull}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors"
          >
            {copiedFull ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            {copiedFull ? 'Copied!' : 'Copy Text'}
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

      {/* Two column: original vs formatted rewrite */}
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

        {/* Formatted rewrite */}
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
            <ResumePreview rewrite={rewrite} />
          </motion.div>
        </div>
      </div>
    </div>
  )
}
