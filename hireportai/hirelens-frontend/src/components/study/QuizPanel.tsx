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
import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, CheckCircle, AlertCircle, ThumbsUp, ThumbsDown } from 'lucide-react'
import { AxiosError } from 'axios'
import clsx from 'clsx'
import { shouldShowPaywall, submitReview, submitCardFeedback } from '@/services/api'
import { capture } from '@/utils/posthog'
import { PaywallModal } from '@/components/PaywallModal'
import { WallInlineNudge } from '@/components/study/WallInlineNudge'
import { useUsage } from '@/context/UsageContext'
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

// ─── Daily-card wall (spec #50) ──────────────────────────────────────────────

/** Backend payload attached to the 402 `detail` when the daily-card wall trips. */
interface DailyWallPayload {
  error: 'free_tier_limit'
  trigger: 'daily_review'
  cards_consumed: number
  cards_limit: number
  resets_at: string
}

/** Extract the AC-2 wall payload from a 402 error, else null. */
function extractWallPayload(err: unknown): DailyWallPayload | null {
  if (!(err instanceof AxiosError) || err.response?.status !== 402) return null
  const detail = (err.response.data as { detail?: unknown } | undefined)?.detail
  if (
    typeof detail === 'object' &&
    detail !== null &&
    (detail as DailyWallPayload).trigger === 'daily_review'
  ) {
    return detail as DailyWallPayload
  }
  return null
}

/** Hours from now until `resetsAtIso`, rounded toward zero per spec §Analytics. */
function hoursUntil(resetsAtIso: string): number {
  const diffMs = new Date(resetsAtIso).getTime() - Date.now()
  return Math.trunc(diffMs / 3_600_000)
}

/** Relative for ≤12h remaining; absolute "Resets at H:MM AM/PM" otherwise. */
function formatResetsAt(resetsAtIso: string): string {
  const diffMs = new Date(resetsAtIso).getTime() - Date.now()
  const totalMin = Math.max(0, Math.round(diffMs / 60_000))
  if (totalMin <= 12 * 60) {
    const h = Math.floor(totalMin / 60)
    const m = totalMin % 60
    return `Resets in ${h}h ${m}m`
  }
  const localTime = new Date(resetsAtIso).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
  return `Resets at ${localTime}`
}

// Paywall-dismissal orchestration state (spec #42 §5.4). After a 402,
// QuizPanel asks the backend whether to render the full modal or the
// silent inline nudge. Grace counter lives in React state (Strategy A
// per spec §5.3): each walled retry after a dismissal increments a
// local counter that gets echoed back to the BE on the next
// should-show-paywall call.
type WallUi = 'modal' | 'nudge'

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
  const [wall, setWall] = useState<DailyWallPayload | null>(null)
  const [wallUi, setWallUi] = useState<WallUi | null>(null)
  // LD-3 grace counter — walled retries since last dismissal. Resets to 0
  // on dismissal (PaywallModal onClose → QuizPanel resets wall state).
  const attemptsSinceDismissRef = useRef<number>(0)
  const { canUsePro } = useUsage()

  // Fire `daily_card_wall_hit` on 402 (spec #50 AC-10 frontend side).
  // Matches the existing `paywall_hit` open-semantic in PaywallModal.tsx:78.
  useEffect(() => {
    if (wall === null) return
    capture('daily_card_wall_hit', {
      resets_at_hours_from_now: hoursUntil(wall.resets_at),
    })
  }, [wall])

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
    } catch (err) {
      const payload = extractWallPayload(err)
      if (payload !== null) {
        // Free-tier daily-card wall (spec #50). The backend did not mutate
        // card_progress or FSRS state — we mirror that and route the user
        // into either the full modal or the silent inline nudge based on
        // spec #42's dismissal grace window.
        setWall(payload)
        setState('revealed')

        // Pro/Enterprise defense-in-depth: if the BE ever 402s a Pro user
        // (plan-transition race, clock skew), silently drop — do not
        // render modal or nudge. Spec §5.4 + LD-7.
        if (canUsePro) {
          setWallUi(null)
          return
        }

        try {
          const decision = await shouldShowPaywall(
            'daily_review',
            attemptsSinceDismissRef.current,
          )
          setWallUi(decision.show ? 'modal' : 'nudge')
        } catch (shouldErr) {
          // Fail-safe to the existing modal behavior so free users never
          // get silently softened past the 402. Matches spec §5.3 fail-
          // safe note.
          console.error('shouldShowPaywall failed', shouldErr)
          setWallUi('modal')
        }
        return
      }
      setSubmitError('Failed to save rating. Please try again.')
      setState('revealed') // let user retry
    }
  }

  // PaywallModal onClose and inline-nudge lifecycle both clear the wall
  // state. The grace counter increments so the next walled retry reports
  // a higher `attempts_since_dismiss` to the BE.
  function handleWallClose() {
    attemptsSinceDismissRef.current += 1
    setWall(null)
    setWallUi(null)
  }

  return (
    <div className="h-full flex flex-col gap-5 py-4 px-1">

      {/* ── Question recap ────────────────────────────────────────── */}
      <div className="rounded-xl bg-contrast/[0.03] border border-contrast/[0.05] p-4">
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

            {/* ── Card feedback ── */}
            <CardFeedbackRow cardId={cardId} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Daily-card wall UI (spec #50 modal, spec #42 orchestration) ── */}
      {wall !== null && (
        <>
          <p
            data-testid="wall-resets-label"
            className="sr-only"
            aria-live="polite"
          >
            {formatResetsAt(wall.resets_at)}
          </p>
          {wallUi === 'modal' && (
            <PaywallModal
              open
              onClose={handleWallClose}
              trigger="daily_review"
            />
          )}
          {wallUi === 'nudge' && <WallInlineNudge trigger="daily_review" />}
        </>
      )}
    </div>
  )
}


/* ── Card Feedback Row ───────────────────────────────────────────────────── */

type FeedbackState = 'idle' | 'comment' | 'submitting' | 'sent'

function CardFeedbackRow({ cardId }: { cardId: string }) {
  const [fbState, setFbState] = useState<FeedbackState>('idle')
  const [vote, setVote] = useState<'up' | 'down' | null>(null)
  const [comment, setComment] = useState('')

  async function handleVote(v: 'up' | 'down') {
    setVote(v)
    if (v === 'up') {
      // Submit immediately for upvotes
      setFbState('submitting')
      try {
        await submitCardFeedback(cardId, { vote: v })
        capture('card_feedback_submitted', { card_id: cardId, vote: v, has_comment: false })
        setFbState('sent')
      } catch {
        setFbState('idle')
      }
    } else {
      // Show comment input for downvotes
      setFbState('comment')
    }
  }

  async function handleSubmitComment() {
    if (!vote) return
    setFbState('submitting')
    try {
      const trimmed = comment.trim() || undefined
      await submitCardFeedback(cardId, { vote, comment: trimmed })
      capture('card_feedback_submitted', {
        card_id: cardId,
        vote,
        has_comment: !!trimmed,
      })
      setFbState('sent')
    } catch {
      setFbState('comment')
    }
  }

  if (fbState === 'sent') {
    return (
      <p className="text-[11px] text-text-muted mt-2">Thanks for your feedback!</p>
    )
  }

  return (
    <div className="mt-3 w-full max-w-xs">
      {fbState === 'idle' && (
        <div className="flex items-center justify-center gap-3">
          <span className="text-[11px] text-text-muted">Rate this card:</span>
          <button
            onClick={() => handleVote('up')}
            className="p-1.5 rounded-lg border border-contrast/[0.08] hover:border-accent-primary/30 hover:bg-accent-primary/[0.06] transition-all text-text-muted hover:text-accent-primary"
            aria-label="Thumbs up"
          >
            <ThumbsUp size={14} />
          </button>
          <button
            onClick={() => handleVote('down')}
            className="p-1.5 rounded-lg border border-contrast/[0.08] hover:border-red-500/30 hover:bg-red-500/[0.06] transition-all text-text-muted hover:text-red-400"
            aria-label="Thumbs down"
          >
            <ThumbsDown size={14} />
          </button>
        </div>
      )}

      {(fbState === 'comment' || fbState === 'submitting') && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="flex flex-col gap-2"
        >
          <textarea
            placeholder="What's wrong with this card? (optional)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 rounded-lg border border-contrast/[0.08] bg-contrast/[0.03] text-xs text-text-secondary placeholder:text-text-muted resize-none focus:outline-none focus:border-accent-primary/30"
          />
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => { setVote(null); setFbState('idle'); setComment('') }}
              disabled={fbState === 'submitting'}
              className="px-3 py-1 text-[11px] text-text-muted hover:text-text-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitComment}
              disabled={fbState === 'submitting'}
              className="px-3 py-1 rounded-lg bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-[11px] font-medium hover:bg-accent-primary/18 transition-colors disabled:opacity-40"
            >
              {fbState === 'submitting' ? 'Sending...' : 'Send feedback'}
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
