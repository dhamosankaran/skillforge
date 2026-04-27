/**
 * QuizItemPanel — quiz-submit panel for a single quiz_item (slice 6.3).
 *
 * State machine: idle → revealed → submitting → done.
 * Submits to POST /api/v1/quiz-items/review (slice 6.2 endpoint, D-5).
 *
 * NOT a rename of components/study/QuizPanel.tsx — both coexist until
 * slice 6.15 retires the legacy card flow (D-7).
 */
import { useMemo, useState } from 'react'
import { AxiosError } from 'axios'
import { Eye } from 'lucide-react'
import { submitQuizReview } from '@/services/api'
import type { QuizItem, QuizReviewResponse } from '@/types'

type Rating = 1 | 2 | 3 | 4
type Phase = 'idle' | 'revealed' | 'submitting' | 'done' | 'error'

interface QuizItemPanelProps {
  quizItem: QuizItem
  sessionId: string
}

const RATING_LABEL: Record<Rating, { label: string; sublabel: string }> = {
  1: { label: 'Again', sublabel: "Didn't recall" },
  2: { label: 'Hard', sublabel: 'With effort' },
  3: { label: 'Good', sublabel: 'Recalled well' },
  4: { label: 'Easy', sublabel: 'Instant recall' },
}

function formatScheduled(days: number, dueDateIso: string): string {
  if (Number.isFinite(days) && days >= 1) {
    const rounded = Math.round(days)
    return `Next review in ${rounded} day${rounded === 1 ? '' : 's'}`
  }
  const due = new Date(dueDateIso).getTime()
  const now = Date.now()
  const diffMin = Math.round(Math.max(0, (due - now) / 60_000))
  if (diffMin < 60) return `Next review in ${diffMin} min`
  const diffHr = Math.round(diffMin / 60)
  return `Next review in ${diffHr} hour${diffHr === 1 ? '' : 's'}`
}

export function QuizItemPanel({ quizItem, sessionId }: QuizItemPanelProps) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [selectedMcq, setSelectedMcq] = useState<string | null>(null)
  const [result, setResult] = useState<QuizReviewResponse | null>(null)
  const [errorCopy, setErrorCopy] = useState<string | null>(null)
  const [startTimeMs] = useState(() => Date.now())

  const mcqOptions = useMemo(() => {
    if (quizItem.question_type !== 'mcq') return null
    const distractors = quizItem.distractors ?? []
    return [quizItem.answer, ...distractors]
  }, [quizItem.answer, quizItem.distractors, quizItem.question_type])

  async function handleRate(rating: Rating) {
    setPhase('submitting')
    setErrorCopy(null)
    try {
      const response = await submitQuizReview({
        quiz_item_id: quizItem.id,
        rating,
        session_id: sessionId,
        time_spent_ms: Math.min(300_000, Math.max(0, Date.now() - startTimeMs)),
      })
      setResult(response)
      setPhase('done')
    } catch (err: unknown) {
      if (err instanceof AxiosError && err.response?.status === 409) {
        setErrorCopy(
          'This quiz item has been retired. Try another lesson or refresh.',
        )
      } else if (err instanceof AxiosError && err.response?.status === 403) {
        setErrorCopy('This quiz item is no longer available.')
      } else {
        setErrorCopy("We couldn't save your review. Please try again.")
      }
      setPhase('error')
    }
  }

  return (
    <div
      className="border border-border-default rounded-lg p-4 bg-bg-surface"
      data-testid={`quiz-item-${quizItem.id}`}
    >
      <p className="text-text-primary font-medium mb-3">{quizItem.question}</p>

      {phase === 'idle' && mcqOptions && (
        <fieldset className="space-y-2 mb-3">
          <legend className="sr-only">Answer choices</legend>
          {mcqOptions.map((option) => (
            <label
              key={option}
              className="flex items-start gap-2 text-text-secondary cursor-pointer"
            >
              <input
                type="radio"
                name={`quiz-${quizItem.id}`}
                value={option}
                checked={selectedMcq === option}
                onChange={() => setSelectedMcq(option)}
                className="mt-1"
              />
              <span>{option}</span>
            </label>
          ))}
        </fieldset>
      )}

      {phase === 'idle' && (
        <button
          type="button"
          onClick={() => setPhase('revealed')}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded border border-border-accent text-text-primary hover:bg-bg-elevated"
        >
          <Eye size={16} /> Reveal Answer
        </button>
      )}

      {(phase === 'revealed' ||
        phase === 'submitting' ||
        phase === 'error') && (
        <div className="space-y-3">
          <div className="rounded bg-bg-elevated p-3 border border-border-default">
            <p className="text-xs uppercase tracking-wide text-text-muted mb-1">
              Answer
            </p>
            <p className="text-text-primary whitespace-pre-wrap">
              {quizItem.answer}
            </p>
          </div>
          {phase === 'error' && errorCopy && (
            <p role="alert" className="text-sm text-danger">
              {errorCopy}
            </p>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {([1, 2, 3, 4] as Rating[]).map((r) => (
              <button
                key={r}
                type="button"
                disabled={phase === 'submitting'}
                onClick={() => handleRate(r)}
                className="px-3 py-2 rounded border border-border-default text-text-primary hover:border-border-accent disabled:opacity-50"
              >
                <span className="block font-semibold">
                  {RATING_LABEL[r].label}
                </span>
                <span className="block text-xs text-text-muted">
                  {RATING_LABEL[r].sublabel}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {phase === 'done' && result && (
        <div className="rounded bg-bg-elevated p-3 border border-border-default">
          <p className="text-sm text-text-primary">
            {formatScheduled(result.scheduled_days, result.due_date)}
          </p>
          <p className="text-xs text-text-muted mt-1">
            FSRS state: {result.fsrs_state} · reps {result.reps} · lapses{' '}
            {result.lapses}
          </p>
        </div>
      )}
    </div>
  )
}
