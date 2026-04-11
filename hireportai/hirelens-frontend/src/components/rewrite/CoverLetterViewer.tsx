import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Copy, Check, RefreshCw, FileText, Download, FileDown } from 'lucide-react'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import { downloadCoverLetterDocx } from '@/utils/docxExport'
import type { CoverLetterResponse } from '@/types'

const TONES = ['professional', 'confident', 'conversational'] as const

const TONE_DESCRIPTIONS: Record<string, string> = {
  professional: 'Formal & polished',
  confident: 'Bold & assertive',
  conversational: 'Warm & personable',
}

interface CoverLetterViewerProps {
  coverLetter: CoverLetterResponse | null
  isLoading: boolean
  onGenerate: (tone: string) => void
}

export function CoverLetterViewer({ coverLetter, isLoading, onGenerate }: CoverLetterViewerProps) {
  const [selectedTone, setSelectedTone] = useState<string>('professional')
  const [copied, setCopied] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const handleCopy = async () => {
    if (!coverLetter) return
    await navigator.clipboard.writeText(coverLetter.cover_letter)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadTxt = () => {
    if (!coverLetter) return
    const blob = new Blob([coverLetter.cover_letter], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'cover-letter.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadPDF = async () => {
    if (!coverLetter) return
    setIsExporting(true)
    try {
      // Build HTML string for cover letter
      const lines = coverLetter.cover_letter.split('\n').filter(l => l.trim())
      let html = `<div style="font-family: 'Times New Roman', Times, serif; font-size: 11pt; line-height: 1.6; color: #000; width: 100%;">`

      for (const line of lines) {
        const trimmed = line.trim()
        const isGreeting = trimmed.startsWith('Dear ')
        const isSignoff = /^(Sincerely|Best regards|Regards|Warm regards|Respectfully|Respectfully yours),?\s*$/i.test(trimmed)
        const isHeader = trimmed.startsWith('## ')

        if (isHeader) {
          html += `<div style="margin-top: 16px; margin-bottom: 8px; font-weight: bold; font-size: 12pt;">${trimmed.replace(/^##\s*/, '')}</div>`
        } else if (isGreeting) {
          html += `<div style="margin: 16px 0;">${trimmed}</div>`
        } else if (isSignoff) {
          html += `<div style="margin-top: 24px; margin-bottom: 4px;">${trimmed}</div>`
        } else {
          html += `<div style="margin-bottom: 12px;">${trimmed}</div>`
        }
      }
      html += `</div>`

      const html2pdf = (await import('html2pdf.js')).default
      await html2pdf()
        .from(html)
        .set({
          margin: [20, 20, 20, 20],
          filename: `cover-letter-${selectedTone}.pdf`,
          image: { type: 'jpeg', quality: 0.98 },
          html2canvas: { scale: 2, logging: false },
          jsPDF: { unit: 'mm', format: 'letter', orientation: 'portrait' },
        })
        .save()
    } finally {
      setIsExporting(false)
    }
  }

  const handleDownloadDocx = async () => {
    if (!coverLetter) return
    await downloadCoverLetterDocx(coverLetter, selectedTone)
  }

  return (
    <div>
      {/* Tone selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-6">
        <span className="text-sm text-text-secondary font-medium">Tone:</span>
        <div className="flex items-center gap-2">
          {TONES.map((tone) => (
            <button
              key={tone}
              onClick={() => setSelectedTone(tone)}
              className={clsx(
                'px-4 py-2.5 rounded-xl text-sm font-medium capitalize transition-all duration-200',
                selectedTone === tone
                  ? 'bg-accent-secondary/12 text-accent-secondary border border-accent-secondary/25 shadow-glow-violet/30'
                  : 'text-text-secondary hover:text-text-primary hover:bg-contrast/[0.04] border border-transparent'
              )}
              aria-label={`Select ${tone} tone`}
            >
              <span className="block">{tone}</span>
              <span className="block text-[10px] mt-0.5 opacity-60">{TONE_DESCRIPTIONS[tone]}</span>
            </button>
          ))}
        </div>
        <button
          onClick={() => onGenerate(selectedTone)}
          disabled={isLoading}
          className={clsx(
            'sm:ml-auto flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
            'bg-accent-secondary/10 border border-accent-secondary/25 text-accent-secondary',
            'hover:bg-accent-secondary/18 disabled:opacity-50 disabled:cursor-not-allowed'
          )}
          aria-label="Generate cover letter"
        >
          <RefreshCw size={14} className={clsx(isLoading && 'animate-spin')} />
          {coverLetter ? 'Regenerate' : 'Generate'}
        </button>
      </div>

      {/* Cover letter content */}
      {isLoading ? (
        <div className="space-y-4 p-8">
          <div className="h-4 bg-bg-elevated rounded-full w-1/4 animate-pulse" />
          <div className="h-px bg-contrast/[0.04] my-4" />
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-3 mb-6">
              <div className="h-3 bg-bg-elevated rounded-full w-full animate-pulse" />
              <div className="h-3 bg-bg-elevated rounded-full w-11/12 animate-pulse" />
              <div className="h-3 bg-bg-elevated rounded-full w-3/4 animate-pulse" />
            </div>
          ))}
          <div className="h-3 bg-bg-elevated rounded-full w-1/5 animate-pulse mt-6" />
          <div className="h-3 bg-bg-elevated rounded-full w-1/4 animate-pulse" />
        </div>
      ) : coverLetter ? (
        <div className="relative">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-secondary animate-pulse" />
              <span className="text-xs text-text-muted uppercase tracking-wider font-medium">
                {coverLetter.tone} tone
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadPDF}
                disabled={isExporting}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors disabled:opacity-50"
                aria-label="Download as PDF"
              >
                <Download size={12} className={isExporting ? 'animate-bounce' : ''} />
                {isExporting ? 'Exporting...' : 'PDF'}
              </button>
              <button
                onClick={handleDownloadDocx}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors"
                aria-label="Download as DOCX"
              >
                <FileDown size={12} />
                DOCX
              </button>
              <button
                onClick={handleDownloadTxt}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors"
                aria-label="Download as text"
              >
                <Download size={12} />
                .txt
              </button>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-accent-primary hover:bg-accent-primary/5 transition-colors"
                aria-label="Copy cover letter"
              >
                {copied ? (
                  <>
                    <Check size={12} className="text-success" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    Copy
                  </>
                )}
              </button>
            </div>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={coverLetter.cover_letter.slice(0, 20)}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-8 bg-bg-elevated/60 backdrop-blur-sm border border-accent-secondary/10 rounded-2xl shadow-card"
            >
              <div className="cover-letter-content">
                <ReactMarkdown
                  components={{
                    h2: ({ children }) => (
                      <h2 className="text-base font-semibold text-accent-secondary mt-5 mb-3 first:mt-0">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-sm font-semibold text-text-primary mt-4 mb-2">
                        {children}
                      </h3>
                    ),
                    p: ({ children }) => (
                      <p className="text-text-primary/90 text-sm leading-[1.8] mb-4 last:mb-0">
                        {children}
                      </p>
                    ),
                    ul: ({ children }) => (
                      <ul className="space-y-1 mb-4 ml-1">
                        {children}
                      </ul>
                    ),
                    li: ({ children }) => (
                      <li className="flex gap-2 text-sm text-text-primary/85 leading-relaxed">
                        <span className="text-accent-secondary/60 flex-shrink-0 mt-0.5">•</span>
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
                  {coverLetter.cover_letter}
                </ReactMarkdown>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-accent-secondary/8 border border-accent-secondary/15 flex items-center justify-center mb-5">
            <FileText size={28} className="text-accent-secondary/60" />
          </div>
          <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
            No Cover Letter Yet
          </h3>
          <p className="text-sm text-text-secondary max-w-sm leading-relaxed">
            Select a tone and click Generate to create a professionally formatted cover letter tailored to the job.
          </p>
        </div>
      )}
    </div>
  )
}
