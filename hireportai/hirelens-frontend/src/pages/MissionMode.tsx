/**
 * MissionMode — time-bound study sprint page.
 *
 * Route: /mission
 *
 * States:
 *   loading   — fetching mission data
 *   setup     — no active mission → show MissionSetup form
 *   active    — mission in progress → Countdown + DailyTarget
 *   studying  — user clicked "Study" → FlipCard + QuizPanel review
 *   dayDone   — all daily cards reviewed → celebration + XP
 *   completed — mission finished → final celebration
 *   error     — fetch failed
 *
 * PostHog events:
 *   mission_created, mission_day_completed, mission_completed
 */
import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, AlertCircle, RefreshCw, Trophy } from 'lucide-react'
import clsx from 'clsx'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { FlipCard } from '@/components/study/FlipCard'
import { QuizPanel } from '@/components/study/QuizPanel'
import { MissionSetup } from '@/components/mission/MissionSetup'
import { Countdown } from '@/components/mission/Countdown'
import { DailyTarget } from '@/components/mission/DailyTarget'
import { useMission } from '@/hooks/useMission'
import { useGamification } from '@/context/GamificationContext'
import { capture } from '@/utils/posthog'
import type { FsrsRating, ReviewResponse, MissionDailyCard, MissionCreateRequest } from '@/types'

// ─── Tab types (same as DailyReview) ────────────────────────────────────────

type TabId = 'concept' | 'production' | 'example' | 'quiz'

const TABS: { id: TabId; label: string }[] = [
  { id: 'concept',    label: 'Concept'    },
  { id: 'production', label: 'Production' },
  { id: 'example',    label: 'Example'    },
  { id: 'quiz',       label: 'Quiz'       },
]

// ─── Content helpers ────────────────────────────────────────────────────────

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

// ─── Difficulty styles ──────────────────────────────────────────────────────

const DIFF_STYLE: Record<string, string> = {
  easy:   'bg-accent-primary/10 text-accent-primary   border-accent-primary/20',
  medium: 'bg-orange-500/10     text-orange-400       border-orange-500/20',
  hard:   'bg-red-500/10        text-red-400          border-red-500/20',
}

// ─── Tab body ───────────────────────────────────────────────────────────────

interface TabBodyProps {
  activeTab: TabId
  card: MissionDailyCard
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
            cardId={card.id}
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

// ─── Page states ────────────────────────────────────────────────────────────

type Phase = 'loading' | 'setup' | 'active' | 'studying' | 'dayDone' | 'completed' | 'error'

// ─── Progress bar ───────────────────────────────────────────────────────────

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

// ─── Main page ──────────────────────────────────────────────────────────────

export default function MissionMode() {
  const navigate = useNavigate()
  const { refresh: refreshGamification } = useGamification()
  const {
    mission,
    daily,
    categories,
    isLoading,
    error,
    noMission,
    create,
    completeDay,
    refresh,
    refreshDaily,
  } = useMission()

  const [phase, setPhase]               = useState<Phase>('loading')
  const [cards, setCards]               = useState<MissionDailyCard[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [completedCount, setCompleted]  = useState(0)
  const [isFlipped, setIsFlipped]       = useState(false)
  const [activeTab, setActiveTab]       = useState<TabId>('quiz')
  const [xpAwarded, setXpAwarded]       = useState(0)
  const [, setIsCompleting] = useState(false)
  const startTimeMs                     = useRef(Date.now())
  const sessionId                       = useRef(crypto.randomUUID())

  // ── Derive phase from hook state ──────────────────────────────────────────
  useEffect(() => {
    if (isLoading) {
      setPhase('loading')
      return
    }
    if (error) {
      setPhase('error')
      return
    }
    if (noMission) {
      setPhase('setup')
      return
    }
    if (mission?.status === 'completed') {
      setPhase('completed')
      return
    }
    if (phase !== 'studying' && phase !== 'dayDone') {
      setPhase('active')
    }
  }, [isLoading, error, noMission, mission]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Handle mission creation ───────────────────────────────────────────────
  async function handleCreate(req: MissionCreateRequest) {
    await create(req)
    capture('mission_created', {
      title: req.title,
      target_date: req.target_date,
      categories: req.category_ids.length,
    })
  }

  // ── Start studying ────────────────────────────────────────────────────────
  function handleStudy() {
    if (!daily || daily.cards.length === 0) return
    setCards(daily.cards)
    setCurrentIndex(0)
    setCompleted(0)
    setIsFlipped(false)
    setActiveTab('quiz')
    startTimeMs.current = Date.now()
    sessionId.current = crypto.randomUUID()
    setPhase('studying')
  }

  // ── Card flip ─────────────────────────────────────────────────────────────
  function handleFlip() {
    setIsFlipped((f) => !f)
    if (!isFlipped) setActiveTab('quiz')
  }

  // ── Rating handler ────────────────────────────────────────────────────────
  function handleRated(_rating: FsrsRating, _res: ReviewResponse) {
    void refreshGamification()
    const newCompleted = completedCount + 1
    setCompleted(newCompleted)

    setTimeout(() => {
      if (currentIndex < cards.length - 1) {
        setCurrentIndex((i) => i + 1)
        setIsFlipped(false)
        setActiveTab('quiz')
        startTimeMs.current = Date.now()
      } else {
        // All cards done — complete the day
        handleDayComplete()
      }
    }, 1400)
  }

  // ── Complete day ──────────────────────────────────────────────────────────
  async function handleDayComplete() {
    setIsCompleting(true)
    try {
      const result = await completeDay()
      setXpAwarded(result.xp_awarded)
      void refreshGamification()

      if (result.mission_status === 'completed') {
        capture('mission_completed', {
          mission_id: mission?.id,
          total_days: mission?.days?.length,
        })
        setPhase('completed')
      } else {
        capture('mission_day_completed', {
          mission_id: mission?.id,
          day_number: result.day_number,
          cards_done: result.cards_completed,
        })
        setPhase('dayDone')
      }
    } catch {
      // Fallback to dayDone even if the API call fails
      setPhase('dayDone')
    } finally {
      setIsCompleting(false)
    }
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-10 sm:px-6 space-y-6">
          <div className="h-4 w-48 rounded-full bg-bg-elevated animate-pulse mx-auto" />
          <div className="w-28 h-28 rounded-full bg-bg-elevated animate-pulse mx-auto" />
          <div className="h-24 rounded-2xl bg-bg-elevated animate-pulse" />
        </div>
      </PageWrapper>
    )
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (phase === 'error') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-24 sm:px-6 flex flex-col items-center gap-5 text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <AlertCircle size={24} className="text-red-400" />
          </div>
          <div>
            <p className="text-base font-semibold text-text-primary mb-1">
              Couldn't load your mission
            </p>
            <p className="text-sm text-text-muted">Check your connection and try again.</p>
          </div>
          <GlowButton variant="ghost" size="sm" onClick={refresh}>
            <RefreshCw size={13} />
            Retry
          </GlowButton>
        </div>
      </PageWrapper>
    )
  }

  // ── Setup — no active mission ─────────────────────────────────────────────
  if (phase === 'setup') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-10 sm:px-6">
          <MissionSetup categories={categories} onCreate={handleCreate} />
        </div>
      </PageWrapper>
    )
  }

  // ── Mission completed ─────────────────────────────────────────────────────
  if (phase === 'completed') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-24 sm:px-6 flex flex-col items-center gap-6 text-center">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', bounce: 0.4 }}
            className="w-20 h-20 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center"
          >
            <Trophy size={36} className="text-accent-primary" />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
              Mission Complete!
            </h2>
            <p className="text-sm text-text-secondary max-w-sm mx-auto leading-relaxed">
              You covered {Math.round(mission?.progress_pct ?? 100)}% of your selected categories.
              Great work staying on track!
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <GlowButton onClick={() => { setPhase('setup'); refresh() }} size="sm">
              Start New Mission
            </GlowButton>
            <GlowButton variant="ghost" size="sm" onClick={() => navigate('/study')}>
              Back to Dashboard
            </GlowButton>
          </motion.div>
        </div>
      </PageWrapper>
    )
  }

  // ── Day done — celebration ────────────────────────────────────────────────
  if (phase === 'dayDone') {
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
            🎯
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
              Day Complete!
            </h2>
            <p className="text-sm text-text-secondary max-w-xs mx-auto leading-relaxed">
              You earned {xpAwarded} XP today. Come back tomorrow to keep your mission on track.
            </p>
          </motion.div>

          {mission && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.25 }}
              className="w-full max-w-xs"
            >
              <Countdown
                title={mission.title}
                daysRemaining={mission.days_remaining}
                totalDays={mission.days.length}
                progressPct={mission.progress_pct}
              />
            </motion.div>
          )}

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <GlowButton onClick={() => { setPhase('active'); refresh(); refreshDaily() }} size="sm">
              Back to Mission
            </GlowButton>
            <GlowButton variant="ghost" size="sm" onClick={() => navigate('/study')}>
              Study Dashboard
            </GlowButton>
          </motion.div>
        </div>
      </PageWrapper>
    )
  }

  // ── Studying — card review ────────────────────────────────────────────────
  if (phase === 'studying' && cards.length > 0) {
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

        <div className="flex-1 overflow-hidden" key={currentCard.id}>
          <TabBody
            activeTab={activeTab}
            card={currentCard}
            sessionId={sessionId.current}
            startTimeMs={startTimeMs.current}
            onRated={handleRated}
          />
        </div>
      </div>
    )

    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-8 sm:px-6">

          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between gap-3 mb-4"
          >
            <button
              onClick={() => setPhase('active')}
              className="flex items-center gap-1 text-sm text-text-muted hover:text-text-secondary transition-colors"
            >
              <ChevronLeft size={14} />
              Mission
            </button>

            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">{currentCard.category}</span>
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

          {/* Progress */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.05 }}
            className="mb-6"
          >
            <ProgressBar completed={completedCount} total={cards.length} />
          </motion.div>

          {/* Flip card */}
          <AnimatePresence mode="wait">
            <motion.div
              key={currentCard.id}
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

          {/* Counter */}
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

  // ── Active — mission dashboard ────────────────────────────────────────────
  const dayComplete = daily ? daily.cards_completed >= daily.cards_target : false
  const hasDailyCards = daily && daily.cards.length > 0

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-2xl mx-auto px-4 py-10 sm:px-6">

        {/* Back link */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <button
            onClick={() => navigate('/study')}
            className="flex items-center gap-1 text-sm text-text-muted hover:text-text-secondary transition-colors"
          >
            <ChevronLeft size={14} />
            Dashboard
          </button>
        </motion.div>

        {/* Countdown ring */}
        {mission && (
          <div className="mb-8">
            <Countdown
              title={mission.title}
              daysRemaining={mission.days_remaining}
              totalDays={mission.days.length}
              progressPct={mission.progress_pct}
            />
          </div>
        )}

        {/* Daily target */}
        {daily && (
          <DailyTarget
            cardsTarget={daily.cards_target}
            cardsCompleted={daily.cards_completed}
            onStudy={handleStudy}
            dayComplete={dayComplete && !hasDailyCards}
          />
        )}

        {/* Day progress grid */}
        {mission && mission.days.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="mt-6"
          >
            <p className="text-[11px] uppercase tracking-widest text-text-muted font-semibold mb-3">
              Mission Progress
            </p>
            <div className="flex flex-wrap gap-1.5">
              {mission.days.map((day) => {
                const done = day.cards_completed >= day.cards_target && day.cards_target > 0
                const partial = day.cards_completed > 0 && !done
                const today = day.date === new Date().toISOString().split('T')[0]
                return (
                  <div
                    key={day.day_number}
                    title={`Day ${day.day_number}: ${day.cards_completed}/${day.cards_target}`}
                    className={clsx(
                      'w-6 h-6 rounded-md flex items-center justify-center text-[9px] font-semibold border transition-all',
                      done && 'bg-accent-primary/20 border-accent-primary/30 text-accent-primary',
                      partial && 'bg-orange-500/10 border-orange-500/20 text-orange-400',
                      !done && !partial && today && 'bg-contrast/[0.06] border-accent-primary/40 text-text-secondary',
                      !done && !partial && !today && 'bg-contrast/[0.03] border-contrast/[0.06] text-text-muted'
                    )}
                  >
                    {day.day_number}
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </div>
    </PageWrapper>
  )
}
