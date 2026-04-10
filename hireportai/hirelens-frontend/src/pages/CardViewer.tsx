/**
 * CardViewer — single card study page.
 *
 * Route: /study/card/:id
 *
 * Layout:
 *   - Breadcrumb + difficulty badge
 *   - FlipCard (front = question, back = 4 content tabs)
 *   - Back-to-dashboard link
 *
 * Tabs (on back face):
 *   Concept     — full answer text
 *   Production  — production-context lines extracted from answer
 *   Example     — code blocks extracted from answer
 *   Quiz        — interactive self-rating via QuizPanel → POST /study/review
 */
import { useState, useEffect, useMemo, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, AlertCircle, Tag } from 'lucide-react'
import clsx from 'clsx'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { FlipCard } from '@/components/study/FlipCard'
import { QuizPanel } from '@/components/study/QuizPanel'
import { PaywallModal } from '@/components/PaywallModal'
import { useCardViewer } from '@/hooks/useCardViewer'
import { capture } from '@/utils/posthog'
import type { FsrsRating, ReviewResponse } from '@/types'

// ─── Tab types ────────────────────────────────────────────────────────────────

type TabId = 'concept' | 'production' | 'example' | 'quiz'

const TABS: { id: TabId; label: string }[] = [
  { id: 'concept',    label: 'Concept'    },
  { id: 'production', label: 'Production' },
  { id: 'example',    label: 'Example'    },
  { id: 'quiz',       label: 'Quiz'       },
]

// ─── Content derivation helpers ───────────────────────────────────────────────

/** Extract fenced code blocks from markdown text. */
function extractCodeBlocks(text: string): string[] {
  const blocks: string[] = []
  const re = /```[\w]*\n([\s\S]*?)```/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    blocks.push(m[1].trimEnd())
  }
  return blocks
}

/** Extract lines/sentences that suggest production context. */
const PROD_PREFIXES = /^(in production|tip:|note:|warning:|use case:|best practice:|avoid:|prefer:|never:|always:)/i

function extractProductionLines(text: string): string[] {
  // Split by newlines and filter for production-hint lines
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  const hits = lines.filter((l) => PROD_PREFIXES.test(l) || l.startsWith('- '))
  return hits.length >= 2 ? hits : [] // need at least 2 to be meaningful
}

// ─── Difficulty badge ─────────────────────────────────────────────────────────

const DIFF_STYLE: Record<string, string> = {
  easy:   'bg-accent-primary/10   text-accent-primary   border-accent-primary/20',
  medium: 'bg-orange-500/10       text-orange-400       border-orange-500/20',
  hard:   'bg-red-500/10          text-red-400          border-red-500/20',
}

// ─── Tab content renderer ─────────────────────────────────────────────────────

interface TabBodyProps {
  activeTab: TabId
  answer: string
  cardId: string
  question: string
  sessionId: string
  startTimeMs: number
  onRated: (r: FsrsRating, res: ReviewResponse) => void
}

function TabBody({ activeTab, answer, cardId, question, sessionId, startTimeMs, onRated }: TabBodyProps) {
  const codeBlocks = useMemo(() => extractCodeBlocks(answer), [answer])
  const prodLines  = useMemo(() => extractProductionLines(answer), [answer])
  // Strip code blocks for prose-only display
  const prose = useMemo(() => answer.replace(/```[\w]*\n[\s\S]*?```/g, '').trim(), [answer])

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.18 }}
        className="h-full overflow-y-auto px-5 py-4"
      >
        {/* CONCEPT -------------------------------------------------------- */}
        {activeTab === 'concept' && (
          <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
            {prose || answer}
          </p>
        )}

        {/* PRODUCTION ------------------------------------------------------ */}
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
            <div className="flex flex-col items-center justify-center h-32 gap-2 text-center">
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {prose || answer}
              </p>
              <p className="text-[11px] text-text-muted mt-3">
                No dedicated production notes — full answer shown.
              </p>
            </div>
          )
        )}

        {/* EXAMPLE -------------------------------------------------------- */}
        {activeTab === 'example' && (
          codeBlocks.length > 0 ? (
            <div className="space-y-3">
              {codeBlocks.map((block, i) => (
                <pre
                  key={i}
                  className="text-[12px] font-mono bg-bg-base/60 border border-white/[0.06] rounded-xl p-4 overflow-x-auto text-text-secondary leading-relaxed"
                >
                  {block}
                </pre>
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {prose || answer}
              </p>
              <p className="text-[11px] text-text-muted">
                No code examples in this card.
              </p>
            </div>
          )
        )}

        {/* QUIZ ----------------------------------------------------------- */}
        {activeTab === 'quiz' && (
          <QuizPanel
            cardId={cardId}
            question={question}
            answer={answer}
            sessionId={sessionId}
            startTimeMs={startTimeMs}
            onRated={onRated}
          />
        )}
      </motion.div>
    </AnimatePresence>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CardViewer() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { card, isLoading, error, forbidden } = useCardViewer(id)

  const [isFlipped, setIsFlipped]   = useState(false)
  const [activeTab, setActiveTab]   = useState<TabId>('concept')
  const startTimeMs                 = useRef(Date.now())

  // Generate a stable session ID for this viewer instance
  const sessionId = useRef(crypto.randomUUID())

  // Fire card_viewed once card loads
  useEffect(() => {
    if (!card) return
    startTimeMs.current = Date.now()
    capture('card_viewed', {
      card_id: card.id,
      category_id: card.category_id,
      difficulty: card.difficulty,
    })
  }, [card?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleFlip() {
    setIsFlipped((f) => !f)
    if (!isFlipped) setActiveTab('concept') // reset to concept on flip-open
  }

  function handleRated(rating: FsrsRating, res: ReviewResponse) {
    // After a successful rating, wait 1.2s then navigate back to dashboard
    setTimeout(() => navigate('/study'), 1200)
    void rating; void res // used by QuizPanel, acknowledged here
  }

  // ── Loading skeleton ───────────────────────────────────────────────────
  if (isLoading) {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-10 sm:px-6">
          <div className="h-4 w-40 rounded-full bg-bg-elevated animate-pulse mb-8" />
          <div className="rounded-2xl border border-white/[0.06] bg-bg-surface/50 animate-pulse" style={{ minHeight: 420 }} />
        </div>
      </PageWrapper>
    )
  }

  // ── Pro-gated card (free user hit a non-foundation card) ─────────────
  if (forbidden) {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-20 sm:px-6 flex flex-col items-center gap-5 text-center">
          <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
            <AlertCircle size={24} className="text-accent-primary" />
          </div>
          <div>
            <p className="text-base font-semibold text-text-primary mb-1">
              This card is Pro-only
            </p>
            <p className="text-sm text-text-muted">
              Upgrade to unlock the full library.
            </p>
          </div>
          <Link
            to="/study"
            className="flex items-center gap-1.5 text-sm text-accent-primary hover:text-accent-primary/80 transition-colors"
          >
            <ChevronLeft size={14} />
            Back to Dashboard
          </Link>
        </div>
        <PaywallModal
          open
          onClose={() => navigate('/study')}
          trigger="card_limit"
        />
      </PageWrapper>
    )
  }

  // ── Error / 404 state ─────────────────────────────────────────────────
  if (error) {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-2xl mx-auto px-4 py-20 sm:px-6 flex flex-col items-center gap-5 text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <AlertCircle size={24} className="text-red-400" />
          </div>
          <div>
            <p className="text-base font-semibold text-text-primary mb-1">{error.message}</p>
            <p className="text-sm text-text-muted">The card may have been removed or you may not have access.</p>
          </div>
          <Link
            to="/study"
            className="flex items-center gap-1.5 text-sm text-accent-primary hover:text-accent-primary/80 transition-colors"
          >
            <ChevronLeft size={14} />
            Back to Dashboard
          </Link>
        </div>
      </PageWrapper>
    )
  }

  if (!card) return null

  // ── Back-face content (tabs + body) ───────────────────────────────────
  const backContent = (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div className="flex shrink-0 border-b border-white/[0.06] px-4 pt-3 gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors',
              activeTab === tab.id
                ? 'text-text-primary bg-white/[0.05] border-b-2 border-accent-primary'
                : 'text-text-muted hover:text-text-secondary'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab body */}
      <div className="flex-1 overflow-hidden">
        <TabBody
          activeTab={activeTab}
          answer={card.answer}
          cardId={card.id}
          question={card.question}
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

        {/* ── Breadcrumb + meta ─────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-center justify-between gap-3 mb-6"
        >
          {/* Back link */}
          <button
            onClick={() => navigate('/study')}
            className="flex items-center gap-1 text-sm text-text-muted hover:text-text-secondary transition-colors"
          >
            <ChevronLeft size={14} />
            Study Dashboard
          </button>

          {/* Category + difficulty */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">{card.category_name}</span>
            <span
              className={clsx(
                'text-[11px] font-medium px-2 py-0.5 rounded-full border capitalize',
                DIFF_STYLE[card.difficulty] ?? DIFF_STYLE.medium
              )}
            >
              {card.difficulty}
            </span>
          </div>
        </motion.div>

        {/* ── Flip card ────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.4 }}
        >
          <FlipCard
            question={card.question}
            isFlipped={isFlipped}
            onFlip={handleFlip}
            backContent={backContent}
          />
        </motion.div>

        {/* ── Tags ─────────────────────────────────────────────────────── */}
        {card.tags.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex flex-wrap items-center gap-1.5 mt-5"
          >
            <Tag size={11} className="text-text-muted shrink-0" />
            {card.tags.map((tag) => (
              <span
                key={tag}
                className="text-[11px] px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-text-muted"
              >
                {tag}
              </span>
            ))}
          </motion.div>
        )}
      </div>
    </PageWrapper>
  )
}
