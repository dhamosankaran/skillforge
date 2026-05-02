/**
 * ThumbsControl — Phase 6 slice 6.13.5b.
 *
 * Spec: docs/specs/phase-6/12-quality-signals.md §8.1 + §11 AC-15..AC-18.
 *
 * Lesson-level thumbs UI mounted on `pages/Lesson.tsx`. Two icon
 * buttons (👍 / 👎); one is active at a time based on the user's
 * prior submission seeded via `LessonWithQuizzes.viewer_thumbs` (§12
 * D-12). Sticky thumbs v1 (§12 D-11) — clicking the same icon a
 * second time is a no-op (sends UPSERT, server returns same row);
 * clicking the opposite icon flips the vote. R12 — uses design
 * tokens only (no hardcoded hex).
 */
import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { useThumbs } from '@/hooks/useThumbs'
import type { ThumbsResponse } from '@/types'
import { capture } from '@/utils/posthog'

export interface ThumbsControlProps {
  lessonId: string
  initialThumbs?: ThumbsResponse | null
  persona?: string | null
  plan?: string | null
}

export function ThumbsControl({
  lessonId,
  initialThumbs,
  persona,
  plan,
}: ThumbsControlProps) {
  const initialScore = (initialThumbs?.score ?? 0) as -1 | 0 | 1
  const { score, aggregate, count, isSubmitting, error, submit } = useThumbs(
    lessonId,
    {
      score: initialScore,
      aggregate: initialThumbs?.aggregate_score ?? null,
      count: initialThumbs?.aggregate_count ?? 0,
    },
  )

  const handleClick = async (next: -1 | 1) => {
    const previousScore = score
    await submit(next)
    // Fire after the optimistic update so the payload reflects the
    // user's intended direction. If submit() reverts on error the
    // PostHog event has still fired with the user's intent — that's
    // fine for funnel signal.
    capture('lesson_thumbs_submitted', {
      lesson_id: lessonId,
      score: next,
      previous_score: previousScore,
      persona: persona ?? null,
      plan: plan ?? null,
    })
  }

  const upActive = score === 1
  const downActive = score === -1

  return (
    <div
      className="flex items-center gap-3 mt-6 pt-4 border-t border-border-accent/40"
      data-testid="thumbs-control"
      aria-label="Was this lesson helpful?"
    >
      <span className="text-sm text-text-secondary">
        Was this lesson helpful?
      </span>
      <button
        type="button"
        disabled={isSubmitting}
        onClick={() => handleClick(1)}
        aria-pressed={upActive}
        aria-label="Yes, this lesson was helpful"
        data-testid="thumbs-up"
        className={`inline-flex items-center justify-center rounded-md px-2 py-1 transition-colors ${
          upActive
            ? 'text-accent-primary bg-bg-elevated'
            : 'text-text-secondary hover:text-text-primary'
        }`}
      >
        <ThumbsUp size={16} />
      </button>
      <button
        type="button"
        disabled={isSubmitting}
        onClick={() => handleClick(-1)}
        aria-pressed={downActive}
        aria-label="No, this lesson was not helpful"
        data-testid="thumbs-down"
        className={`inline-flex items-center justify-center rounded-md px-2 py-1 transition-colors ${
          downActive
            ? 'text-accent-primary bg-bg-elevated'
            : 'text-text-secondary hover:text-text-primary'
        }`}
      >
        <ThumbsDown size={16} />
      </button>
      {count > 0 && aggregate !== null && (
        <span
          className="text-xs text-text-secondary"
          data-testid="thumbs-aggregate"
        >
          {aggregate >= 0 ? '+' : ''}
          {aggregate.toFixed(2)} · {count} vote{count === 1 ? '' : 's'}
        </span>
      )}
      {error && (
        <span
          role="alert"
          className="text-xs text-accent-danger"
          data-testid="thumbs-error"
        >
          {error}
        </span>
      )}
    </div>
  )
}
