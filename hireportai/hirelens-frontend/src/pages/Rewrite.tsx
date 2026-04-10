import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, PenTool, Download, MessageSquare, Lock, Crown, Zap, FileDown } from 'lucide-react'
import clsx from 'clsx'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { ResumeEditor } from '@/components/rewrite/ResumeEditor'
import { CoverLetterViewer } from '@/components/rewrite/CoverLetterViewer'
import { downloadResumeDocx } from '@/utils/docxExport'
import { useAnalysisContext } from '@/context/AnalysisContext'
import { useRewrite } from '@/hooks/useRewrite'
import { useUsage } from '@/context/UsageContext'

type TabId = 'resume' | 'cover-letter'

/** Shown when the user's plan doesn't include Premium features */
function PremiumGate() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center justify-center py-24 text-center max-w-md mx-auto"
    >
      <div className="w-16 h-16 rounded-2xl bg-accent-secondary/10 border border-accent-secondary/20 flex items-center justify-center mb-6">
        <Lock size={28} className="text-accent-secondary" />
      </div>
      <div className="flex items-center gap-2 mb-3">
        <Crown size={14} className="text-accent-secondary" />
        <span className="text-xs font-semibold uppercase tracking-widest text-accent-secondary">
          Premium Feature
        </span>
      </div>
      <h2 className="font-display text-2xl font-bold text-text-primary mb-3">
        AI Resume Rewriting
      </h2>
      <p className="text-text-secondary text-sm leading-relaxed mb-8">
        AI rewriting and cover letter generation are exclusive to the Premium plan.
        Upgrade to unlock ATS-optimised bullet points, tailored cover letters, and PDF export.
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          to="/pricing"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-accent-secondary text-bg-base text-sm font-semibold hover:bg-accent-secondary/90 transition-all shadow-[0_0_20px_rgba(139,92,246,0.25)]"
        >
          <Crown size={14} />
          Upgrade to Premium
        </Link>
        <Link
          to="/results"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-contrast/[0.04] border border-contrast/[0.08] text-text-secondary text-sm font-medium hover:text-text-primary transition-all"
        >
          View Results
        </Link>
      </div>
      <p className="mt-6 text-xs text-text-muted">
        Demo mode — upgrade instantly on the{' '}
        <Link to="/pricing" className="text-accent-primary hover:underline">
          Pricing page
        </Link>
        .
      </p>
    </motion.div>
  )
}

export default function Rewrite() {
  const { state } = useAnalysisContext()
  const navigate = useNavigate()
  const { canUsePremium } = useUsage()
  const [activeTab, setActiveTab] = useState<TabId>('resume')
  const [isExportingPDF, setIsExportingPDF] = useState(false)
  const {
    rewriteResult,
    coverLetter,
    isLoadingRewrite,
    isLoadingCoverLetter,
    runRewrite,
    runCoverLetter,
  } = useRewrite()

  const resumeText = state.result?.resume_text || ''
  const jobDescription = state.jobDescription || ''

  const handleDownloadPDF = async () => {
    if (!rewriteResult) return
    setIsExportingPDF(true)
    try {
      const r = rewriteResult
      const { jsPDF } = await import('jspdf')
      const doc = new jsPDF({ unit: 'mm', format: 'letter', orientation: 'portrait' })

      const pageW = doc.internal.pageSize.getWidth()
      const pageH = doc.internal.pageSize.getHeight()
      const marginL = 12.7
      const marginR = 12.7
      const contentW = pageW - marginL - marginR
      const marginTop = 12
      const marginBottom = 8
      const availableH = pageH - marginTop - marginBottom

      // ── Base font sizes (will be scaled to fit) ──
      const BASE = {
        name: 16, contact: 9, sectionTitle: 10.5,
        org: 10, title: 10, detail: 9.5, bullet: 9.5, content: 10,
        headerGap: 1, contactGap: 1.5, afterRule: 3,
        sectionGapBefore: 3, sectionGapAfterTitle: 2, sectionGapAfterRule: 4,
        entryGap: 2.5, bulletGapBefore: 0.5, contentLineGap: 0.5,
        lineHeightFactor: 0.45,
      }

      // ── Helper: measure total height needed at a given scale ──
      const measureHeight = (s: number): number => {
        const sz = (base: number) => base * s
        const lh = (base: number) => sz(base) * BASE.lineHeightFactor
        const gap = (base: number) => base * s

        const countLines = (text: string, fontSize: number, maxW: number): number => {
          doc.setFontSize(fontSize)
          return (doc.splitTextToSize(text, maxW) as string[]).length
        }

        let h = 0
        // Header
        if (r.header?.name) { h += lh(BASE.name) + gap(BASE.headerGap) }
        if (r.header?.contact) { h += lh(BASE.contact) + gap(BASE.contactGap) }
        h += gap(BASE.afterRule) + 0.5 // rule + gap

        for (const section of r.sections) {
          const hasEntries = section.entries?.some(e => e.org || e.title || (e.bullets && e.bullets.length > 0))
          const hasContent = section.content?.trim()
          if (!hasEntries && !hasContent) continue

          h += gap(BASE.sectionGapBefore) + lh(BASE.sectionTitle) + gap(BASE.sectionGapAfterTitle) + 0.3 + gap(BASE.sectionGapAfterRule)

          if (section.entries) {
            for (let ei = 0; ei < section.entries.length; ei++) {
              const entry = section.entries[ei]
              if (!entry.org && !entry.title && (!entry.bullets || entry.bullets.length === 0)) continue
              if (entry.org) h += lh(BASE.org)
              if (entry.title) {
                const n = countLines(entry.title, sz(BASE.title), contentW)
                h += n * lh(BASE.title)
              }
              if (entry.details) {
                for (const d of entry.details) {
                  if (!d.trim()) continue
                  const n = countLines(d, sz(BASE.detail), contentW)
                  h += n * lh(BASE.detail)
                }
              }
              if (entry.bullets && entry.bullets.length > 0) {
                h += gap(BASE.bulletGapBefore)
                for (const b of entry.bullets) {
                  const n = countLines(b, sz(BASE.bullet), contentW - 6)
                  h += n * lh(BASE.bullet)
                }
              }
              if (ei < section.entries.length - 1) h += gap(BASE.entryGap)
            }
          }
          if (hasContent && !hasEntries) {
            for (const line of section.content.split('\n')) {
              if (!line.trim()) continue
              const n = countLines(line.trim(), sz(BASE.content), contentW)
              h += n * lh(BASE.content) + gap(BASE.contentLineGap)
            }
          }
        }
        return h
      }

      // ── Find optimal scale: start at 1.0, shrink until it fits ──
      let scale = 1.0
      const minScale = 0.55 // don't go below ~55% — keeps text readable
      while (measureHeight(scale) > availableH && scale > minScale) {
        scale -= 0.02
      }

      // ── Scaled helpers ──
      const sz = (base: number) => base * scale
      const lh = (base: number) => sz(base) * BASE.lineHeightFactor
      const gap = (base: number) => base * scale
      let y = marginTop

      const wrapText = (text: string, fontSize: number, maxWidth: number): string[] => {
        doc.setFontSize(fontSize)
        return doc.splitTextToSize(text, maxWidth) as string[]
      }

      const drawText = (text: string, x: number, baseFontSize: number, opts?: { bold?: boolean; italic?: boolean; align?: 'center' | 'left' | 'right'; maxWidth?: number }) => {
        const fontSize = sz(baseFontSize)
        const style = opts?.bold && opts?.italic ? 'bolditalic' : opts?.bold ? 'bold' : opts?.italic ? 'italic' : 'normal'
        doc.setFont('times', style)
        doc.setFontSize(fontSize)
        const mw = opts?.maxWidth || contentW
        if (opts?.align === 'center') {
          doc.text(text, pageW / 2, y, { align: 'center' })
          y += lh(baseFontSize)
        } else if (opts?.align === 'right') {
          doc.text(text, pageW - marginR, y, { align: 'right' })
        } else {
          const lines = wrapText(text, fontSize, mw)
          for (const line of lines) {
            doc.text(line, x, y)
            y += lh(baseFontSize)
          }
        }
      }

      const drawLine = (thickness = 0.4) => {
        doc.setLineWidth(thickness)
        doc.line(marginL, y, pageW - marginR, y)
      }

      // ── Header ──
      if (r.header?.name) {
        drawText(r.header.name.toUpperCase(), marginL, BASE.name, { bold: true, align: 'center' })
        y += gap(BASE.headerGap)
      }
      if (r.header?.contact) {
        drawText(r.header.contact, marginL, BASE.contact, { align: 'center' })
        y += gap(BASE.contactGap)
      }
      drawLine(0.5)
      y += gap(BASE.afterRule)

      // ── Sections ──
      for (const section of r.sections) {
        const hasEntries = section.entries && section.entries.length > 0 &&
          section.entries.some(e => e.org || e.title || (e.bullets && e.bullets.length > 0))
        const hasContent = section.content && section.content.trim().length > 0
        if (!hasEntries && !hasContent) continue

        y += gap(BASE.sectionGapBefore)
        drawText(section.title.toUpperCase(), marginL, BASE.sectionTitle, { bold: true })
        y += gap(BASE.sectionGapAfterTitle)
        drawLine(0.3)
        y += gap(BASE.sectionGapAfterRule)

        if (section.entries) {
          for (let ei = 0; ei < section.entries.length; ei++) {
            const entry = section.entries[ei]
            if (!entry.org && !entry.title && (!entry.bullets || entry.bullets.length === 0)) continue

            if (entry.org) {
              doc.setFont('times', 'bold')
              doc.setFontSize(sz(BASE.org))
              doc.text(entry.org, marginL, y)
              if (entry.date) {
                doc.setFont('times', 'normal')
                doc.setFontSize(sz(BASE.org))
                doc.text(entry.date, pageW - marginR, y, { align: 'right' })
              }
              y += lh(BASE.org)
            }

            if (entry.title) {
              drawText(entry.title, marginL, BASE.title, { italic: true })
            }

            if (entry.details) {
              for (const d of entry.details) {
                if (!d.trim()) continue
                drawText(d, marginL, BASE.detail, {})
              }
            }

            if (entry.bullets && entry.bullets.length > 0) {
              y += gap(BASE.bulletGapBefore)
              for (const b of entry.bullets) {
                const bulletFontSize = sz(BASE.bullet)
                doc.setFont('times', 'normal')
                doc.setFontSize(bulletFontSize)
                const bulletLines = wrapText(b, bulletFontSize, contentW - 6)
                for (let li = 0; li < bulletLines.length; li++) {
                  if (li === 0) {
                    doc.text('\u2022', marginL + 1, y)
                    doc.text(bulletLines[li], marginL + 5, y)
                  } else {
                    doc.text(bulletLines[li], marginL + 5, y)
                  }
                  y += lh(BASE.bullet)
                }
              }
            }

            if (ei < section.entries.length - 1) {
              y += gap(BASE.entryGap)
            }
          }
        }

        if (hasContent && (!section.entries || section.entries.length === 0)) {
          const lines = section.content.split('\n')
          for (const line of lines) {
            if (!line.trim()) continue
            drawText(line.trim(), marginL, BASE.content, {})
            y += gap(BASE.contentLineGap)
          }
        }
      }

      doc.save('optimized-resume.pdf')
    } finally {
      setIsExportingPDF(false)
    }
  }

  const handleDownloadDocx = async () => {
    if (!rewriteResult) return
    setIsExportingPDF(true)
    try {
      await downloadResumeDocx(rewriteResult)
    } finally {
      setIsExportingPDF(false)
    }
  }

  // No analysis yet
  if (!state.result) {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-6xl mx-auto px-4 py-24 text-center">
          <PenTool size={48} className="text-text-muted mx-auto mb-4" />
          <h2 className="font-display text-2xl font-bold mb-2 text-text-primary">
            No Analysis Data
          </h2>
          <p className="text-text-secondary mb-8">
            Run an analysis first to generate your optimized resume.
          </p>
          <GlowButton onClick={() => navigate('/analyze')}>
            <Zap size={14} />
            Start Analysis
          </GlowButton>
        </div>
      </PageWrapper>
    )
  }

  const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
    { id: 'resume', label: 'Resume Rewrite', icon: FileText },
    { id: 'cover-letter', label: 'Cover Letter', icon: MessageSquare },
  ]

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-6xl mx-auto px-4 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8"
        >
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="font-display text-3xl font-bold text-text-primary">
                AI <span className="text-accent-primary">Optimization</span>
              </h1>
              {!canUsePremium && (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-secondary/10 border border-accent-secondary/20 text-accent-secondary text-[11px] font-semibold">
                  <Crown size={10} />
                  Premium
                </span>
              )}
            </div>
            <p className="text-text-secondary text-sm">
              Get an ATS-optimized rewrite of your resume and a tailored cover letter.
            </p>
          </div>

          {canUsePremium && (
            <div className="flex items-center gap-3">
              {activeTab === 'resume' && !rewriteResult && (
                <GlowButton
                  size="sm"
                  onClick={() => runRewrite(resumeText, jobDescription)}
                  isLoading={isLoadingRewrite}
                >
                  <PenTool size={13} />
                  Generate AI Rewrite
                </GlowButton>
              )}
              {activeTab === 'resume' && rewriteResult && (
                <>
                  <GlowButton
                    variant="ghost"
                    size="sm"
                    onClick={handleDownloadPDF}
                    isLoading={isExportingPDF}
                  >
                    <Download size={13} />
                    {isExportingPDF ? 'Exporting…' : 'Download PDF'}
                  </GlowButton>
                  <GlowButton
                    variant="ghost"
                    size="sm"
                    onClick={handleDownloadDocx}
                  >
                    <FileDown size={13} />
                    Download DOCX
                  </GlowButton>
                </>
              )}
            </div>
          )}
        </motion.div>

        {/* Premium gate — shown when plan is free or pro */}
        {!canUsePremium ? (
          <PremiumGate />
        ) : (
          <>
            {/* Tabs */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="flex items-center gap-1 mb-8 border-b border-contrast/[0.06]"
            >
              {tabs.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all border-b-2 -mb-px',
                    activeTab === id
                      ? 'text-accent-primary border-accent-primary'
                      : 'text-text-secondary border-transparent hover:text-text-primary hover:border-contrast/10'
                  )}
                  aria-label={label}
                >
                  <Icon size={14} />
                  {label}
                </button>
              ))}
            </motion.div>

            {/* Content */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {activeTab === 'resume' ? (
                <ResumeEditor
                  original={resumeText}
                  rewrite={rewriteResult}
                  isLoading={isLoadingRewrite}
                  onDownloadPDF={handleDownloadPDF}
                  onDownloadDocx={handleDownloadDocx}
                  isExportingPDF={isExportingPDF}
                />
              ) : (
                <CoverLetterViewer
                  coverLetter={coverLetter}
                  isLoading={isLoadingCoverLetter}
                  onGenerate={(tone) => runCoverLetter(resumeText, jobDescription, tone)}
                />
              )}
            </motion.div>
          </>
        )}
      </div>

      {/* PDF is now generated from HTML string — no hidden template needed */}
    </PageWrapper>
  )
}
