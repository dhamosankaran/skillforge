import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquare, ChevronDown, ChevronUp, Zap,
  BookOpen, Brain, Target, RefreshCw, User, Briefcase, Database
} from 'lucide-react'
import clsx from 'clsx'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { AnimatedCard, containerVariants } from '@/components/ui/AnimatedCard'
import { PaywallModal } from '@/components/PaywallModal'
import { useAnalysisContext } from '@/context/AnalysisContext'
import { useUsage } from '@/context/UsageContext'
import { useInterview } from '@/hooks/useInterview'
import { capture } from '@/utils/posthog'
import { jdHashPrefix } from '@/utils/jdHash'

type CategoryFilter = 'all' | 'behavioral' | 'technical' | 'role-specific'

const CATEGORY_ICONS: Record<CategoryFilter, React.ElementType> = {
  all: MessageSquare,
  behavioral: User,
  technical: Brain,
  'role-specific': Briefcase,
}

const CATEGORY_COLORS: Record<CategoryFilter, string> = {
  all: 'text-text-secondary',
  behavioral: 'text-accent-primary',
  technical: 'text-accent-secondary',
  'role-specific': 'text-warning',
}

function detectCategory(question: string): CategoryFilter {
  const q = question.toLowerCase()
  if (q.includes('tell me about') || q.includes('describe a time') || q.includes('how do you handle') || q.includes('give an example')) return 'behavioral'
  if (q.includes('implement') || q.includes('algorithm') || q.includes('data structure') || q.includes('complexity') || q.includes('design') || q.includes('code') || q.includes('technical') || q.includes('difference between') || q.includes('explain how') || q.includes('what is')) return 'technical'
  return 'role-specific'
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const diffMs = Date.now() - then
  const diffMin = Math.max(0, Math.round(diffMs / 60000))
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr} hour${diffHr === 1 ? '' : 's'} ago`
  const diffDay = Math.round(diffHr / 24)
  return `${diffDay} day${diffDay === 1 ? '' : 's'} ago`
}

interface QuestionCardProps {
  question: string
  starFramework: string
  index: number
}

function QuestionCard({ question, starFramework, index }: QuestionCardProps) {
  const [expanded, setExpanded] = useState(false)
  const category = detectCategory(question)
  const CategoryIcon = CATEGORY_ICONS[category]

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.4 }}
      className="rounded-xl border border-contrast/[0.06] bg-bg-surface/50 hover:border-contrast/[0.1] transition-colors"
    >
      <button
        className="w-full text-left p-5 flex items-start gap-4"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        {/* Number badge */}
        <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-contrast/[0.04] border border-contrast/[0.08] flex items-center justify-center text-xs font-mono text-text-muted font-semibold">
          {index + 1}
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary leading-relaxed">{question}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className={clsx('flex items-center gap-1 text-[11px] font-medium capitalize', CATEGORY_COLORS[category])}>
              <CategoryIcon size={10} />
              {category}
            </span>
            <span className="text-[11px] text-text-muted">· STAR framework answer inside</span>
          </div>
        </div>

        <span className="flex-shrink-0 text-text-muted mt-0.5">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-contrast/[0.04] pt-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-5 h-5 rounded bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
                  <BookOpen size={10} className="text-accent-primary" />
                </div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-accent-primary">
                  STAR Framework Answer Guide
                </span>
              </div>
              <div className="pl-1 space-y-2">
                {starFramework.split('\n').filter(Boolean).map((line, i) => {
                  const isLabel = /^(Situation|Task|Action|Result):/i.test(line.trim())
                  return (
                    <p
                      key={i}
                      className={clsx(
                        'text-sm leading-relaxed',
                        isLabel ? 'font-semibold text-text-primary mt-3 first:mt-0' : 'text-text-secondary'
                      )}
                    >
                      {line}
                    </p>
                  )
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function Interview() {
  const { state } = useAnalysisContext()
  const { usage } = useUsage()
  const { interviewResult, isLoading, limitInfo, runInterviewPrep, reset } = useInterview()
  const [showPaywall, setShowPaywall] = useState(false)

  // Form state for manual entry (when no analysis context)
  const [manualResume, setManualResume] = useState('')
  const [manualJD, setManualJD] = useState('')
  const [activeFilter, setActiveFilter] = useState<CategoryFilter>('all')

  const hasContext = !!(state.result?.resume_text && state.jobDescription)
  const resumeText: string = hasContext ? (state.result!.resume_text ?? '') : manualResume
  const jobDescription: string = hasContext ? (state.jobDescription ?? '') : manualJD

  const canGenerate = resumeText.trim().length > 50 && jobDescription.trim().length > 50
  const isFreeTier = usage.plan === 'free'
  // Pre-flight free-tier gate (spec #49 §3.4). `interviewPrepsMax === -1` is
  // the unlimited sentinel for Pro / Enterprise / admin. The post-hoc 403
  // path via `limitInfo` is kept as defense-in-depth for users whose snapshot
  // hasn't hydrated yet.
  const interviewLimitReached =
    isFreeTier &&
    usage.interviewPrepsMax > 0 &&
    usage.interviewPrepsUsed >= usage.interviewPrepsMax
  const limitReached = interviewLimitReached || limitInfo?.limitReached === true

  const handleGenerate = () => {
    runInterviewPrep(resumeText, jobDescription)
  }

  const handleRegenerate = () => {
    capture('interview_questions_regenerated', {
      from_free_tier: isFreeTier,
      remaining_free_quota: isFreeTier ? usage.interviewPrepsRemaining : undefined,
    })
    runInterviewPrep(resumeText, jobDescription, { forceRegenerate: true })
  }

  // Fire one analytics event per cached-served result. Dedupe by generated_at
  // so re-renders during the same response don't spam PostHog.
  const lastCachedAtRef = useRef<string | null>(null)
  useEffect(() => {
    if (!interviewResult?.cached || !interviewResult.generated_at) return
    if (lastCachedAtRef.current === interviewResult.generated_at) return
    lastCachedAtRef.current = interviewResult.generated_at
    const ageMs = Math.max(0, Date.now() - new Date(interviewResult.generated_at).getTime())
    const ageHours = Math.round((ageMs / 36e5) * 10) / 10
    jdHashPrefix(jobDescription).then((prefix) => {
      capture('interview_questions_cached_served', {
        jd_hash_prefix: prefix,
        generated_at_age_hours: ageHours,
      })
    })
  }, [interviewResult, jobDescription])

  const allQuestions = interviewResult?.questions ?? []
  const filteredQuestions = activeFilter === 'all'
    ? allQuestions
    : allQuestions.filter(q => detectCategory(q.question) === activeFilter)

  const filters: CategoryFilter[] = ['all', 'behavioral', 'technical', 'role-specific']

  const showCachedChip = interviewResult?.cached === true && !!interviewResult.generated_at
  const showFreshFreeUsageChip =
    interviewResult !== null &&
    interviewResult.cached === false &&
    isFreeTier

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div data-testid="page-interview" className="max-w-4xl mx-auto px-4 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-8 h-8 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
                  <MessageSquare size={16} className="text-accent-primary" />
                </div>
                <h1 className="font-display text-3xl font-bold text-text-primary">
                  Interview <span className="text-accent-primary">Prep</span>
                </h1>
              </div>
              <p className="text-text-secondary text-sm">
                AI-generated interview questions with STAR framework answer guides, tailored to your resume and the job.
              </p>
            </div>
            {interviewResult && (
              <GlowButton variant="ghost" size="sm" onClick={reset}>
                <RefreshCw size={13} />
                New Session
              </GlowButton>
            )}
          </div>
        </motion.div>

        {/* Context banner if analysis data is available */}
        {hasContext && !interviewResult && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-6 p-4 rounded-xl bg-accent-primary/[0.06] border border-accent-primary/15 flex items-center gap-3"
          >
            <Target size={16} className="text-accent-primary flex-shrink-0" />
            <p className="text-sm text-text-secondary">
              Using your latest resume and job role + skills from your last analysis.{' '}
              <span className="text-accent-primary font-medium">Ready to generate questions.</span>
            </p>
          </motion.div>
        )}

        {/* Manual input if no analysis context */}
        {!hasContext && !interviewResult && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-6 space-y-4"
          >
            <AnimatedCard className="p-5">
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Your Resume Text
              </label>
              <textarea
                value={manualResume}
                onChange={(e) => setManualResume(e.target.value)}
                placeholder="Paste your resume text here..."
                rows={6}
                className="w-full bg-bg-elevated/60 border border-contrast/[0.08] rounded-xl px-4 py-3 text-sm text-text-primary placeholder:text-text-muted resize-none focus:outline-none focus:border-accent-primary/30 transition-colors"
              />
            </AnimatedCard>
            <AnimatedCard className="p-5">
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Job Description
              </label>
              <textarea
                value={manualJD}
                onChange={(e) => setManualJD(e.target.value)}
                placeholder="Paste the job description here..."
                rows={5}
                className="w-full bg-bg-elevated/60 border border-contrast/[0.08] rounded-xl px-4 py-3 text-sm text-text-primary placeholder:text-text-muted resize-none focus:outline-none focus:border-accent-primary/30 transition-colors"
              />
            </AnimatedCard>
          </motion.div>
        )}

        {/* Limit reached banner */}
        {limitReached && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-xl bg-warning/[0.08] border border-warning/20 text-center"
          >
            <p className="text-sm text-text-primary font-medium mb-1">
              Free limit reached ({limitInfo?.limit ?? usage.interviewPrepsMax} per month)
            </p>
            <p className="text-xs text-text-secondary mb-3">
              Upgrade to Pro for unlimited interview prep generations.
            </p>
            <button
              onClick={() => setShowPaywall(true)}
              className="text-xs font-semibold text-accent-primary hover:text-accent-primary/80 transition-colors"
            >
              Upgrade to Pro →
            </button>
          </motion.div>
        )}

        {/* Generate button (pre-result state) */}
        {!interviewResult && !limitReached && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex flex-col items-center gap-2 mb-8"
          >
            <GlowButton
              onClick={handleGenerate}
              isLoading={isLoading}
              disabled={!canGenerate}
              size="sm"
            >
              <Zap size={14} />
              {isLoading ? 'Generating questions…' : 'Generate Interview Questions'}
            </GlowButton>
          </motion.div>
        )}

        {/* Loading skeleton */}
        {isLoading && (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="rounded-xl border border-contrast/[0.04] bg-bg-surface/40 p-5">
                <div className="flex gap-4">
                  <div className="w-7 h-7 rounded-lg bg-bg-elevated animate-pulse" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3.5 bg-bg-elevated rounded-full w-3/4 animate-pulse" />
                    <div className="h-3 bg-bg-elevated rounded-full w-1/2 animate-pulse" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Results */}
        {interviewResult && !isLoading && (
          <motion.div variants={containerVariants} initial="hidden" animate="show">
            {/* Cache + plan-aware status row */}
            {(showCachedChip || showFreshFreeUsageChip) && (
              <div className="flex flex-wrap items-center gap-2 mb-3">
                {showCachedChip && (
                  <span
                    data-testid="cached-chip"
                    className="inline-flex items-center gap-1.5 rounded-full border border-accent-primary/20 bg-accent-primary/[0.08] px-2.5 py-1 text-[11px] font-medium text-accent-primary"
                  >
                    <Database size={10} />
                    Cached — generated {formatRelativeTime(interviewResult!.generated_at!)}
                  </span>
                )}
                {showFreshFreeUsageChip && (
                  <span
                    data-testid="free-usage-chip"
                    className="inline-flex items-center gap-1.5 rounded-full border border-warning/20 bg-warning/[0.08] px-2.5 py-1 text-[11px] font-medium text-warning"
                  >
                    Used 1 of your monthly free generations
                  </span>
                )}
              </div>
            )}

            {/* Stats bar */}
            <div className="flex items-center justify-between mb-5">
              <p className="text-sm text-text-secondary">
                <span className="text-text-primary font-semibold">{allQuestions.length}</span> questions generated
              </p>

              {/* Category filter tabs */}
              <div className="flex items-center gap-1">
                {filters.map((f) => {
                  const Icon = CATEGORY_ICONS[f]
                  return (
                    <button
                      key={f}
                      onClick={() => setActiveFilter(f)}
                      className={clsx(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all',
                        activeFilter === f
                          ? 'bg-contrast/[0.07] text-text-primary border border-contrast/[0.1]'
                          : 'text-text-muted hover:text-text-secondary'
                      )}
                    >
                      <Icon size={11} />
                      {f === 'all' ? `All (${allQuestions.length})` : f}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Question cards */}
            <div className="space-y-3">
              {filteredQuestions.length > 0 ? (
                filteredQuestions.map((q, i) => (
                  <QuestionCard
                    key={i}
                    question={q.question}
                    starFramework={q.star_framework}
                    index={i}
                  />
                ))
              ) : (
                <div className="flex flex-col items-center gap-4 py-16 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
                    <MessageSquare size={24} className="text-accent-primary" />
                  </div>
                  <div>
                    <p className="text-base font-semibold text-text-primary mb-1">No {activeFilter} questions</p>
                    <p className="text-sm text-text-muted max-w-xs mx-auto">
                      Try selecting a different category filter to see more questions.
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveFilter('all')}
                    className="text-sm text-accent-primary hover:text-accent-primary/80 font-medium transition-colors"
                  >
                    Show all questions
                  </button>
                </div>
              )}
            </div>

            {/* Re-generate CTA */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-8 text-center"
            >
              <GlowButton variant="ghost" size="sm" onClick={handleRegenerate} isLoading={isLoading}>
                <RefreshCw size={13} />
                Regenerate Questions
              </GlowButton>
            </motion.div>
          </motion.div>
        )}
      </div>

      <PaywallModal
        open={showPaywall}
        onClose={() => setShowPaywall(false)}
        trigger="interview_limit"
      />
    </PageWrapper>
  )
}
