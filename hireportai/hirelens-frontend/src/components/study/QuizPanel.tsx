/**
 * QuizPanel — self-rated recall quiz for a single card.
 *
 * States: idle → revealed → submitting → done
 *
 * Idle:      Shows question + "Reveal Answer" button.
 * Revealed:  Shows question + full answer + four FSRS rating buttons.
 * Submitting: Buttons disabled while POST /study/review is in-flight.
 * Done:       Shows next-review result; parent is notified via onRated.
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, CheckCircle, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { submitReview } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { FsrsRating, ReviewResponse } from '@/types'

interface RatingOption {
  rating: FsrsRating
  label: string
  sublabel: string
  colorClass: string
  bgClass: string
}

const RATING_OPTIONS: RatingOption[] = [
  {
    rating: 1,
    label: 'Again',
    sublabel: "Didn't recall",
    colorClass: 'text-red-400',
    bgClass: 'border-red-500/20 hover:border-red-500/40 hover:bg-red-500/[0.06]',
  },
  {
    rating: 2,
    label: 'Hard',
    sublabel: 'With effort',
    colorClass: 'text-orange-400',
    bgClass: 'border-orange-500/20 hover:border-orange-500/40 hover:bg-orange-500/[0.06]',
  },
  {
    rating: 3,
    label: 'Good',
    sublabel: 'Recalled well',
    colorClass: 'text-accent-primary',
    bgClass: 'border-accent-primary/20 hover:border-accent-primary/40 hover:bg-accent-primary/[0.06]',
  },
  {
    rating: 4,
    label: 'Easy',
    sublabel: 'Instant recall',
    colorClass: 'text-accent-secondary',
    bgClass: 'border-accent-secondary/20 hover:border-accent-secondary/40 hover:bg-accent-secondary/[0.06]',
  },
]

type QuizState = 'idle' | 'revealed' | 'submitting' | 'done'

interface QuizPanelProps {
  cardId: string
  question: string
  answer: string
  sessionId: string
  startTimeMs: number
  onRated: (rating: FsrsRating, result: ReviewResponse) => void
}

function formatNextReview(dueDateIso: string): string {
  const now = Date.now()
  const due = new Date(dueDateIso).getTime()
  const diffMs = due - now
  const diffMin = Math.round(diffMs / 60_000)
  if (diffMin < 60) return `${diffMin} min`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr} hour${diffHr !== 1 ? 's' : ''}`
  const diffDays = Math.round(diffHr / 24)
  return `${diffDays} day${diffDays !== 1 ? 's' : ''}`
}

export function QuizPanel({
  cardId,
  question,
  answer,
  sessionId,
  startTimeMs,
  onRated,
}: QuizPanelProps) {
  const [state, setState] = useState<QuizState>('idle')
  const [result, setResult] = useState<ReviewResponse | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  function handleReveal() {
    capture('quiz_submitted', {
      card_id: cardId,
      time_to_reveal_ms: Date.now() - startTimeMs,
    })
    setState('revealed')
  }

  async function handleRate(rating: FsrsRating) {
    setState('submitting')
    setSubmitError(null)
    try {
      const res = await submitReview({
        card_id: cardId,
        rating,
        session_id: sessionId,
        time_spent_ms: Date.now() - startTimeMs,
      })
      // `card_reviewed` is fired server-side from study_service.review_card
      // — see Spec #10. The backend is the single source of truth so the
      // event can't be blocked by adblock and rating/state come straight
      // from the FSRS scheduler.
      setResult(res)
      setState('done')
      onRated(rating, res)
    } catch {
      setSubmitError('Failed to save rating. Please try again.')
      setState('revealed') // let user retry
    }
  }

  return (
    <div className="h-full flex flex-col gap-5 py-4 px-1">

      {/* ── Question recap ────────────────────────────────────────── */}
      <div className="rounded-xl bg-white/[0.03] border border-white/[0.05] p-4">
        <p className="text-[10px] uppercase tracking-widest text-text-muted font-semibold mb-2">
          Question
        </p>
        <p className="text-sm text-text-secondary leading-relaxed">{question}</p>
      </div>

      {/* ── Idle: reveal button ───────────────────────────────────── */}
      {state === 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center gap-3 py-4"
        >
          <p className="text-xs text-text-muted text-center max-w-xs">
            Think about your answer, then reveal to check.
          </p>
          <button
            onClick={handleReveal}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-sm font-semibold hover:bg-accent-primary/18 transition-colors"
          >
            <Eye size={14} />
            Reveal Answer
          </button>
        </motion.div>
      )}

      {/* ── Revealed / submitting: answer + ratings ───────────────── */}
      <AnimatePresence>
        {(state === 'revealed' || state === 'submitting') && (
          <motion.div
            key="revealed"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col gap-4"
          >
            {/* Answer */}
            <div className="rounded-xl bg-accent-primary/[0.04] border border-accent-primary/10 p-4">
              <p className="text-[10px] uppercase tracking-widest text-accent-primary font-semibold mb-2">
                Answer
              </p>
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {answer}
              </p>
            </div>

            {/* Error */}
            {submitError && (
              <div className="flex items-center gap-2 text-xs text-red-400">
                <AlertCircle size={12} />
                {submitError}
              </div>
            )}

            {/* Rating prompt */}
            <p className="text-xs text-text-muted text-center">How well did you recall this?</p>

            {/* Rating buttons */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {RATING_OPTIONS.map((opt) => (
                <button
                  key={opt.rating}
                  onClick={() => handleRate(opt.rating)}
                  disabled={state === 'submitting'}
                  className={clsx(
                    'flex flex-col items-center gap-0.5 py-3 px-2 rounded-xl border transition-all duration-150',
                    'disabled:opacity-40 disabled:cursor-not-allowed',
                    opt.bgClass
                  )}
                >
                  <span className={clsx('text-sm font-bold font-display', opt.colorClass)}>
                    {opt.label}
                  </span>
                  <span className="text-[10px] text-text-muted">{opt.sublabel}</span>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Done ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {state === 'done' && result && (
          <motion.div
            key="done"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center gap-3 py-4 text-center"
          >
            <div className="w-10 h-10 rounded-full bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
              <CheckCircle size={18} className="text-accent-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text-primary">Saved!</p>
              <p className="text-xs text-text-muted mt-0.5">
                Next review in{' '}
                <span className="text-accent-primary font-medium">
                  {formatNextReview(result.due_date)}
                </span>
                {result.scheduled_days >= 1 && (
                  <> &nbsp;·&nbsp; {Math.round(result.scheduled_days)} day interval</>
                )}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
