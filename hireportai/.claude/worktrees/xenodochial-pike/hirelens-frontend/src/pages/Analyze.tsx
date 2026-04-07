import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Cpu, ChevronRight, Shield } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { ResumeDropzone } from '@/components/upload/ResumeDropzone'
import { JDInput } from '@/components/upload/JDInput'
import { GlowButton } from '@/components/ui/GlowButton'
import { useAnalysis } from '@/hooks/useAnalysis'
import { useUsage } from '@/context/UsageContext'

const LOADING_MESSAGES = [
  'Parsing resume structure...',
  'Running NLP pipeline...',
  'Extracting keywords with TF-IDF...',
  'Calculating ATS score...',
  'Detecting skill gaps...',
  'Analyzing bullet points...',
  'Checking formatting compliance...',
  'Generating fit analysis...',
  'Finalizing your report...',
]

function LoadingOverlay() {
  const [msgIdx, setMsgIdx] = useState(0)

  useState(() => {
    const interval = setInterval(() => {
      setMsgIdx((i) => (i + 1) % LOADING_MESSAGES.length)
    }, 1800)
    return () => clearInterval(interval)
  })

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bg-base/95 backdrop-blur-xl"
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 40% 40% at 50% 45%, rgba(0,255,200,0.05) 0%, transparent 70%)' }}
      />
      <div className="relative mb-8">
        <motion.div
          animate={{ boxShadow: ['0 0 30px rgba(0,255,200,0.15)', '0 0 50px rgba(0,255,200,0.25)', '0 0 30px rgba(0,255,200,0.15)'] }}
          transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          className="w-20 h-20 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center"
        >
          <Cpu size={32} className="text-accent-primary" strokeWidth={1.5} />
        </motion.div>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 3, ease: 'linear' }}
          className="absolute inset-[-4px] rounded-2xl border-t border-accent-primary/30"
        />
      </div>

      <h3 className="font-display text-lg font-semibold text-text-primary mb-3">Analyzing Your Resume</h3>
      <AnimatePresence mode="wait">
        <motion.p
          key={msgIdx}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          className="text-[13px] text-text-muted font-mono"
        >
          {LOADING_MESSAGES[msgIdx]}
        </motion.p>
      </AnimatePresence>

      <div className="w-48 h-0.5 bg-bg-elevated rounded-full mt-6 overflow-hidden">
        <motion.div
          className="h-full bg-accent-primary/70 rounded-full"
          initial={{ width: '0%' }}
          animate={{ width: `${((msgIdx + 1) / LOADING_MESSAGES.length) * 100}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </motion.div>
  )
}

export default function Analyze() {
  const { resumeFile, jobDescription, isLoading, setFile, setJobDescription, runAnalysis } = useAnalysis()
  const { usage, canScan } = useUsage()

  const canAnalyze = !!resumeFile && jobDescription.trim().length >= 50

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <AnimatePresence>{isLoading && <LoadingOverlay />}</AnimatePresence>

      <div className="max-w-5xl mx-auto px-5 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="font-display text-3xl sm:text-4xl font-bold mb-3 tracking-tight">
            Resume <span className="text-accent-primary">Analysis</span>
          </h1>
          <p className="text-text-secondary text-sm max-w-md mx-auto leading-relaxed">
            Upload your resume and paste the job description to get your instant ATS score.
          </p>

          {/* Usage indicator for free tier */}
          {usage.plan === 'free' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 mt-4 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-xs text-text-muted"
            >
              <span className="font-mono">{usage.scansUsed}/3</span> free scans used
              {!canScan && (
                <span className="text-warning font-medium ml-1">
                  — Upgrade for more
                </span>
              )}
            </motion.div>
          )}
        </motion.div>

        {/* Upload area */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8"
        >
          <div className="bg-bg-surface/50 border border-white/[0.06] rounded-2xl p-5 min-h-[300px] flex flex-col transition-colors hover:border-white/[0.1]">
            <ResumeDropzone file={resumeFile} onFileChange={setFile} />
          </div>
          <div className="bg-bg-surface/50 border border-white/[0.06] rounded-2xl p-5 min-h-[300px] flex flex-col transition-colors hover:border-white/[0.1]">
            <JDInput value={jobDescription} onChange={setJobDescription} />
          </div>
        </motion.div>

        {/* Analyze button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.16 }}
          className="flex flex-col items-center gap-4"
        >
          <GlowButton
            size="lg"
            className="w-full max-w-sm"
            onClick={runAnalysis}
            disabled={!canAnalyze}
            isLoading={isLoading}
          >
            {isLoading ? 'Analyzing...' : 'Analyze Resume'}
            {!isLoading && <ChevronRight size={14} />}
          </GlowButton>

          {!canAnalyze && !isLoading && (
            <p className="text-[11px] text-text-muted text-center">
              {!resumeFile
                ? 'Upload your resume to continue'
                : 'Add more content to the job description (50+ words)'}
            </p>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex items-center justify-center gap-1.5 mt-8"
        >
          <Shield size={11} className="text-text-muted" />
          <p className="text-[11px] text-text-muted">
            Your resume is processed in memory and never stored.
          </p>
        </motion.div>
      </div>
    </PageWrapper>
  )
}
