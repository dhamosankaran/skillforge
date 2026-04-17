/**
 * DailyReview — FSRS Daily 5 queue.
 *
 * Route: /learn/daily
 *
 * Flow:
 *   1. Fetch GET /api/v1/study/daily → up to 5 due cards + session_id
 *   2. Show cards one at a time (FlipCard + QuizPanel, Quiz tab by default)
 *   3. After each rating, wait 1.4 s then advance to the next card
 *   4. When the queue empties → "All caught up! 🎉" state
 *   5. Same "All caught up!" when the queue is already empty on load
 *
 * PostHog:
 *   daily_review_started  — on first card render
 *   daily_review_completed — when last card is rated
 */
import { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, AlertCircle, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { FlipCard } from '@/components/study/FlipCard'
import { QuizPanel } from '@/components/study/QuizPanel'
import { fetchDailyQueue } from '@/services/api'
import { useGamification } from '@/context/GamificationContext'
import { capture } from '@/utils/posthog'
import type { DailyCard, FsrsRating, ReviewResponse } from '@/types'

// ─── Tab types (mirrors CardViewer) ──────────────────────────────────────────

type TabId = 'concept' | 'production' | 'example' | 'quiz'

const TABS: { id: TabId; label: string }[] = [
  { id: 'concept',    label: 'Concept'    },
  { id: 'production', label: 'Production' },
  { id: 'example',    label: 'Example'    },
  { id: 'quiz',       label: 'Quiz'       },
]

// ─── Content helpers ──────────────────────────────────────────────────────────

function extractCodeBlocks(text: string): string[] {
  const blocks: string[] = []
  const re = /```[\w]*\n([\s\S]*?)```/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) blocks.push(m[1].trimEnd())
  return blocks
}

const PROD_RE = /^(in production|tip:|note:|warning:|use case:|best practice:|avoid:|prefer:|never:|always:)/i

function extractProductionLines(text: string): string[] {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  const hits = lines.filter((l) => PROD_RE.test(l) || l.startsWith('- '))
  return hits.length >= 2 ? hits : []
}

// ─── Difficulty badge colours ─────────────────────────────────────────────────

const DIFF_STYLE: Record<string, string> = {
  easy:   'bg-accent-primary/10 text-accent-primary   border-accent-primary/20',
  medium: 'bg-orange-500/10     text-orange-400       border-orange-500/20',
  hard:   'bg-red-500/10        text-red-400          border-red-500/20',
}

// ─── Tab body ─────────────────────────────────────────────────────────────────

interface TabBodyProps {
  activeTab: TabId
  card: DailyCard
  sessionId: string
  startTimeMs: number
  onRated: (rating: FsrsRating, res: ReviewResponse) => void
}

function TabBody({ activeTab, card, sessionId, startTimeMs, onRated }: TabBodyProps) {
  const codeBlocks = useMemo(() => extractCodeBlocks(card.answer), [card.answer])
  const prodLines  = useMemo(() => extractProductionLines(card.answer), [card.answer])
  const prose      = useMemo(
    () => card.answer.replace(/```[\w]*\n[\s\S]*?```/g, '').trim(),
    [card.answer]
  )

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.15 }}
        className="h-full overflow-y-auto px-5 py-4"
      >
        {activeTab === 'concept' && (
          <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
            {prose || card.answer}
          </p>
        )}

        {activeTab === 'production' && (
          prodLines.length > 0 ? (
            <ul className="space-y-2.5">
              {prodLines.map((line, i) => (
                <li key={i} className="flex gap-2.5 text-sm text-text-secondary leading-relaxed">
                  <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-accent-primary/60" />
                  <span>{line.replace(/^[-•]\s*/, '')}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div>
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {prose || card.answer}
              </p>
              <p className="text-[11px] text-text-muted mt-3">
                No dedicated production notes — full answer shown.
              </p>
            </div>
          )
        )}

        {activeTab === 'example' && (
          codeBlocks.length > 0 ? (
            <div className="space-y-3">
              {codeBlocks.map((block, i) => (
                <pre
                  key={i}
                  className="text-[12px] font-mono bg-bg-base/60 border border-contrast/[0.06] rounded-xl p-4 overflow-x-auto text-text-secondary leading-relaxed"
                >
                  {block}
                </pre>
              ))}
            </div>
          ) : (
            <div>
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {prose || card.answer}
              </p>
              <p className="text-[11px] text-text-muted mt-3">
                No code examples in this card.
              </p>
            </div>
          )
        )}

        {activeTab === 'quiz' && (
          <QuizPanel
            cardId={card.card_id}
            question={card.question}
            answer={card.answer}
            sessionId={sessionId}
            startTimeMs={startTimeMs}
            onRated={onRated}
          />
        )}
      </motion.div>
    </AnimatePresence>
  )
}

// ─── Phase types ──────────────────────────────────────────────────────────────

type Phase = 'loading' | 'error' | 'empty' | 'reviewing' | 'done'

// ─── Progress bar ─────────────────────────────────────────────────────────────

function ProgressBar({ completed, total }: { completed: number; total: number }) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 rounded-full bg-contrast/[0.06] overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-accent-primary to-accent-secondary"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs text-text-muted tabular-nums shrink-0">
        {completed}/{total}
      </span>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DailyReview() {
  const navigate = useNavigate()
  const { refresh: refreshGamification } = useGamification()

  const [phase, setPhase]               = useState<Phase>('loading')
  const [cards, setCards]               = useState<DailyCard[]>([])
  const [sessionId, setSessionId]       = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)
  const [completedCount, setCompleted]  = useState(0)
  const [isFlipped, setIsFlipped]       = useState(false)
  const [activeTab, setActiveTab]       = useState<TabId>('quiz')
  const startTimeMs                     = useRef(Date.now())
  const startedFired                    = useRef(false)

  // ── Fetch queue on mount ─────────────────────────────────────────────────
  useEffect(() => {
    fetchDailyQueue()
      .then((data) => {
        if (data.cards.length === 0) {
          setPhase('empty')
        } else {
          setCards(data.cards)
          setSessionId(data.session_id)
          setPhase('reviewing')
          startTimeMs.current = Date.now()
        }
      })
      .catch(() => setPhase('error'))
  }, [])

  // ── Fire daily_review_started once queue is loaded ───────────────────────
  useEffect(() => {
    if (phase === 'reviewing' && !startedFired.current && cards.length > 0) {
      startedFired.current = true
      capture('daily_review_started', {
        total_due: cards.length,
        session_id: sessionId,
      })
    }
  }, [phase, cards.length, sessionId])

  // ── Card flip handler ────────────────────────────────────────────────────
  function handleFlip() {
    setIsFlipped((f) => !f)
    if (!isFlipped) setActiveTab('quiz') // default to quiz when opening back
  }

  // ── Rating handler: advance or complete ─────────────────────────────────
  function handleRated(rating: FsrsRating, _res: ReviewResponse) {
    void rating
    // Refresh gamification stats so navbar StreakBadge / Profile reflect the
    // new XP and streak immediately.
    void refreshGamification()
    const newCompleted = completedCount + 1
    setCompleted(newCompleted)

    setTimeout(() => {
      if (currentIndex < cards.length - 1) {
        // Advance to next card
        setCurrentIndex((i) => i + 1)
        setIsFlipped(false)
        setActiveTab('quiz')
        startTimeMs.current = Date.now()
      } else {
        // All done
        capture('daily_review_completed', {
          cards_reviewed: newCompleted,
          session_id: sessionId,
        })
        setPhase('done')
      }
    }, 1400) // let QuizPanel's "Saved!" state show briefly
  }

  // ── Loading skeleton ─────────────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-10 sm:px-6 space-y-6">
          <div className="h-4 w-48 rounded-full bg-bg-elevated animate-pulse" />
          <div className="h-1.5 rounded-full bg-bg-elevated animate-pulse" />
          <div
            className="rounded-2xl border border-contrast/[0.06] bg-bg-surface/50 animate-pulse"
            style={{ minHeight: 420 }}
          />
        </div>
      </PageWrapper>
    )
  }

  // ── Error state ──────────────────────────────────────────────────────────
  if (phase === 'error') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-24 sm:px-6 flex flex-col items-center gap-5 text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <AlertCircle size={24} className="text-red-400" />
          </div>
          <div>
            <p className="text-base font-semibold text-text-primary mb-1">
              Couldn't load your daily queue
            </p>
            <p className="text-sm text-text-muted">Check your connection and try again.</p>
          </div>
          <GlowButton
            variant="ghost"
            size="sm"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={13} />
            Retry
          </GlowButton>
        </div>
      </PageWrapper>
    )
  }

  // ── Empty / done state ───────────────────────────────────────────────────
  if (phase === 'empty' || phase === 'done') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-24 sm:px-6 flex flex-col items-center gap-6 text-center">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', bounce: 0.4 }}
            className="text-6xl"
            aria-hidden="true"
          >
            🎉
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
              All caught up!
            </h2>
            <p className="text-sm text-text-secondary max-w-xs mx-auto leading-relaxed">
              {phase === 'done'
                ? `You reviewed ${completedCount} card${completedCount !== 1 ? 's' : ''} today. Come back tomorrow for your next session.`
                : 'No cards due right now. Great work keeping up — come back later today or tomorrow.'}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <GlowButton onClick={() => navigate('/learn')} size="sm">
              Back to Dashboard
            </GlowButton>
            <GlowButton
              variant="ghost"
              size="sm"
              onClick={() => navigate('/learn')}
            >
              Browse all categories
            </GlowButton>
          </motion.div>
        </div>
      </PageWrapper>
    )
  }

  // ── Reviewing state ──────────────────────────────────────────────────────
  const currentCard = cards[currentIndex]

  const backContent = (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div className="flex shrink-0 border-b border-contrast/[0.06] px-4 pt-3 gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors',
              activeTab === tab.id
                ? 'text-text-primary bg-contrast/[0.05] border-b-2 border-accent-primary'
                : 'text-text-muted hover:text-text-secondary'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab body — key on card_id so QuizPanel fully remounts on advance */}
      <div className="flex-1 overflow-hidden" key={currentCard.card_id}>
        <TabBody
          activeTab={activeTab}
          card={currentCard}
          sessionId={sessionId}
          startTimeMs={startTimeMs.current}
          onRated={handleRated}
        />
      </div>
    </div>
  )

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div data-testid="page-daily-review" className="max-w-2xl mx-auto px-4 py-8 sm:px-6">

        {/* ── Header ────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between gap-3 mb-4"
        >
          <button
            onClick={() => navigate('/learn')}
            className="flex items-center gap-1 text-sm text-text-muted hover:text-text-secondary transition-colors"
          >
            <ChevronLeft size={14} />
            Dashboard
          </button>

          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">{currentCard.category_name}</span>
            <span
              className={clsx(
                'text-[11px] font-medium px-2 py-0.5 rounded-full border capitalize',
                DIFF_STYLE[currentCard.difficulty] ?? DIFF_STYLE.medium
              )}
            >
              {currentCard.difficulty}
            </span>
          </div>
        </motion.div>

        {/* ── Progress bar ──────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.05 }}
          className="mb-6"
        >
          <ProgressBar completed={completedCount} total={cards.length} />
        </motion.div>

        {/* ── Flip card — key forces remount on card advance ─────────────── */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentCard.card_id}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.28, ease: 'easeInOut' }}
          >
            <FlipCard
              question={currentCard.question}
              isFlipped={isFlipped}
              onFlip={handleFlip}
              backContent={backContent}
            />
          </motion.div>
        </AnimatePresence>

        {/* ── Card counter ──────────────────────────────────────────────── */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-center text-xs text-text-muted mt-4"
        >
          Card {currentIndex + 1} of {cards.length}
        </motion.p>
      </div>
    </PageWrapper>
  )
}
