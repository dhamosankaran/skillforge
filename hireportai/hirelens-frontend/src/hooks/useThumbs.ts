/**
 * useThumbs — Phase 6 slice 6.13.5b.
 *
 * Spec: docs/specs/phase-6/12-quality-signals.md §8.3 + §11 AC-15..AC-18.
 *
 * Mirrors the existing custom-hook idiom in `useLesson.ts` (no
 * react-query in this codebase). Wraps `submitThumbs(...)` with
 * optimistic state + revert-on-error so `<ThumbsControl />` can
 * pre-flip the active icon before the network round-trip resolves.
 */
import { useCallback, useState } from 'react'
import { submitThumbs } from '@/services/api'
import type { ThumbsResponse } from '@/types'

export type ThumbsScore = -1 | 0 | 1

export interface UseThumbsState {
  score: ThumbsScore
  aggregate: number | null
  count: number
  isSubmitting: boolean
  error: string | null
}

export interface UseThumbsResult extends UseThumbsState {
  submit: (next: -1 | 1) => Promise<void>
}

export function useThumbs(
  lessonId: string,
  initial: { score?: ThumbsScore; aggregate?: number | null; count?: number } = {},
): UseThumbsResult {
  const [score, setScore] = useState<ThumbsScore>(initial.score ?? 0)
  const [aggregate, setAggregate] = useState<number | null>(
    initial.aggregate ?? null,
  )
  const [count, setCount] = useState<number>(initial.count ?? 0)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const submit = useCallback(
    async (next: -1 | 1) => {
      const previousScore = score
      const previousAggregate = aggregate
      const previousCount = count

      // Optimistic update — pre-flip so the icon responds immediately.
      setScore(next)
      setIsSubmitting(true)
      setError(null)
      try {
        const response: ThumbsResponse = await submitThumbs(lessonId, {
          score: next,
        })
        setScore(response.score)
        setAggregate(response.aggregate_score)
        setCount(response.aggregate_count)
      } catch (err) {
        // Revert optimistic state on failure.
        setScore(previousScore)
        setAggregate(previousAggregate)
        setCount(previousCount)
        const message =
          err instanceof Error ? err.message : 'Could not save your vote'
        setError(message)
      } finally {
        setIsSubmitting(false)
      }
    },
    [lessonId, score, aggregate, count],
  )

  return { score, aggregate, count, isSubmitting, error, submit }
}
