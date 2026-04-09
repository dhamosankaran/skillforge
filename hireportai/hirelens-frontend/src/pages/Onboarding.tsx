import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  FileText,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { useAnalysisContext } from '@/context/AnalysisContext'
import { fetchOnboardingRecommendations } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { GapMapping } from '@/types'

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; mappings: GapMapping[] }
  | { status: 'error'; message: string }

export default function Onboarding() {
  const { state } = useAnalysisContext()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [load, setLoad] = useState<LoadState>({ status: 'idle' })

  // Track whether the user engaged with any gap card before leaving.
  const cardsClickedRef = useRef(0)
  const completedFiredRef = useRef(false)

  const result = state.result
  const scanId = searchParams.get('scan_id') ?? undefined
  const gaps = result?.top_gaps ?? []

  // ── Fire onboarding_started once, on first ready mount ────────────────────
  const startedFiredRef = useRef(false)
  useEffect(() => {
    if (startedFiredRef.current || !result) return
    startedFiredRef.current = true
    capture('onboarding_started', {
      scan_id: scanId ?? null,
      gap_count: gaps.length,
      source: 'ats_scan',
    })
  }, [result, scanId, gaps.length])

  // ── Fetch recommendations on mount ────────────────────────────────────────
  useEffect(() => {
    if (!result) return
    if (gaps.length === 0) {
      setLoad({ status: 'ready', mappings: [] })
      return
    }

    let cancelled = false
    setLoad({ status: 'loading' })
    fetchOnboardingRecommendations(gaps, scanId)
      .then((resp) => {
        if (cancelled) return
        setLoad({ status: 'ready', mappings: resp.results })
      })
      .catch((err) => {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Failed to load recommendations'
        setLoad({ status: 'error', message })
      })

    return () => {
      cancelled = true
    }
    // `gaps` is derived from `result`; re-running only on `result` change is
    // intentional so tab-switching doesn't retrigger the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result])

  // ── No scan in context → send user back to /analyze ──────────────────────
  if (!result) {
    return <Navigate to="/analyze" replace />
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function fireCompleted(skipped: boolean) {
    if (completedFiredRef.current) return
    completedFiredRef.current = true
    capture('onboarding_completed', {
      gaps_shown: gaps.length,
      cards_clicked: cardsClickedRef.current,
      skipped,
    })
  }

  function handleStartStudying(mapping: GapMapping) {
    const cat = mapping.matching_categories[0]
    if (!cat) return
    cardsClickedRef.current += 1
    capture('gap_card_clicked', {
      gap: mapping.gap,
      category_id: cat.category_id,
      category_name: cat.name,
    })
    fireCompleted(false)
    navigate(`/study?category=${encodeURIComponent(cat.category_id)}`)
  }

  function handleSkip() {
    fireCompleted(true)
    navigate('/study')
  }

  function handleRetry() {
    // Re-run the fetch effect by toggling load back to idle, then relying
    // on the effect's dependency. Simpler: directly invoke the fetch.
    setLoad({ status: 'loading' })
    fetchOnboardingRecommendations(gaps, scanId)
      .then((resp) => setLoad({ status: 'ready', mappings: resp.results }))
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load recommendations'
        setLoad({ status: 'error', message })
      })
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-3xl mx-auto px-4 py-12 sm:px-6">
        {/* ── Hero: score + grade ─────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-[11px] font-mono text-accent-primary mb-5">
            <Sparkles size={11} />
            SCAN COMPLETE
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight mb-3">
            Your ATS score:{' '}
            <span className="text-accent-primary">{result.ats_score}</span>
            <span className="text-text-muted text-2xl ml-2">({result.grade})</span>
          </h1>
          <p className="text-text-secondary text-sm max-w-md mx-auto leading-relaxed">
            We found gaps in your profile. Here are the study categories that
            will close them fastest.
          </p>
        </motion.div>

        {/* ── Gaps section ────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <h2 className="font-display text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <BookOpen size={14} className="text-accent-primary" />
            We found gaps in:
          </h2>

          {/* Empty: no gaps at all */}
          {gaps.length === 0 && (
            <div className="rounded-xl border border-white/[0.06] bg-bg-surface/50 p-6 text-center">
              <p className="text-sm text-text-secondary mb-4">
                Your resume already covers all the skills we scanned for — nice work.
              </p>
              <GlowButton size="sm" onClick={handleSkip}>
                Go to Study Dashboard
                <ArrowRight size={13} />
              </GlowButton>
            </div>
          )}

          {/* Loading skeleton */}
          {gaps.length > 0 && load.status === 'loading' && (
            <div className="space-y-3">
              {gaps.slice(0, Math.min(5, gaps.length)).map((_, i) => (
                <div
                  key={i}
                  className="h-20 rounded-xl border border-white/[0.06] bg-bg-surface/50 animate-pulse"
                />
              ))}
            </div>
          )}

          {/* Error */}
          {load.status === 'error' && (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 text-center">
              <div className="w-10 h-10 mx-auto mb-3 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <AlertCircle size={18} className="text-red-400" />
              </div>
              <p className="text-sm font-medium text-text-primary mb-1">
                Couldn't load recommendations
              </p>
              <p className="text-xs text-text-muted mb-4">{load.message}</p>
              <div className="flex items-center justify-center gap-2">
                <GlowButton size="sm" variant="ghost" onClick={handleRetry}>
                  <RefreshCw size={13} />
                  Retry
                </GlowButton>
                <button
                  onClick={handleSkip}
                  className="px-3 py-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
                >
                  Skip for now
                </button>
              </div>
            </div>
          )}

          {/* Ready: gap rows */}
          {load.status === 'ready' && load.mappings.length > 0 && (
            <div className="space-y-3">
              {load.mappings.map((m, i) => (
                <GapRow
                  key={`${m.gap}-${i}`}
                  mapping={m}
                  index={i}
                  onStartStudying={() => handleStartStudying(m)}
                />
              ))}
            </div>
          )}
        </motion.div>

        {/* ── Secondary actions ────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4 border-t border-white/[0.05]"
        >
          <button
            onClick={handleSkip}
            className="text-sm text-text-muted hover:text-text-secondary transition-colors"
          >
            Skip for now →
          </button>
          <span className="hidden sm:inline text-text-muted/40">•</span>
          <button
            onClick={() => {
              fireCompleted(false)
              navigate('/results')
            }}
            className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-secondary transition-colors"
          >
            <FileText size={13} />
            See full analysis
          </button>
        </motion.div>
      </div>
    </PageWrapper>
  )
}

// ─── Gap row ──────────────────────────────────────────────────────────────────

interface GapRowProps {
  mapping: GapMapping
  index: number
  onStartStudying: () => void
}

function GapRow({ mapping, index, onStartStudying }: GapRowProps) {
  const cat = mapping.matching_categories[0]
  const hasMatch = !!cat

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * index }}
      className="flex items-center gap-4 rounded-xl border border-white/[0.06] bg-bg-surface/50 p-4 sm:p-5 hover:border-white/[0.12] transition-colors"
    >
      {/* Gap label */}
      <div className="flex-1 min-w-0">
        <p className="text-[11px] uppercase tracking-wider text-text-muted font-mono mb-1">
          Gap
        </p>
        <p className="text-sm font-semibold text-text-primary truncate">
          {mapping.gap}
        </p>
      </div>

      {/* Category pill */}
      <div className="flex-1 min-w-0 hidden sm:block">
        <p className="text-[11px] uppercase tracking-wider text-text-muted font-mono mb-1">
          Recommended
        </p>
        {hasMatch ? (
          <div className="flex items-center gap-2 text-sm text-text-primary truncate">
            <span className="text-lg" aria-hidden="true">{cat.icon}</span>
            <span className="truncate">{cat.name}</span>
            <span className="text-[11px] text-text-muted font-mono shrink-0">
              {cat.matched_card_count} cards
            </span>
          </div>
        ) : (
          <p className="text-sm text-text-muted italic">No study cards yet</p>
        )}
      </div>

      {/* CTA */}
      <div className="shrink-0">
        {hasMatch ? (
          <GlowButton size="sm" onClick={onStartStudying}>
            Start studying
            <ArrowRight size={13} />
          </GlowButton>
        ) : (
          <span className="text-[11px] text-text-muted font-mono">—</span>
        )}
      </div>
    </motion.div>
  )
}
