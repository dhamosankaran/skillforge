import { useCallback, useEffect, useState } from 'react'
import { fetchScoreHistory } from '@/services/api'
import type { ScoreHistoryResponse } from '@/types'

interface UseScoreHistoryResult {
  data: ScoreHistoryResponse | null
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Spec #63 (E-043) §8.3 — fetch the score history for a tracker
 * application. Disabled (no fetch) when ``trackerApplicationId`` is
 * null. Mirrors the bare-`useState`/`useEffect` pattern used by
 * `useHomeState` (this codebase does not run @tanstack/react-query).
 */
export function useScoreHistory(
  trackerApplicationId: string | null | undefined,
): UseScoreHistoryResult {
  const [data, setData] = useState<ScoreHistoryResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<Error | null>(null)

  const load = useCallback(async () => {
    if (!trackerApplicationId) {
      setData(null)
      setIsLoading(false)
      setError(null)
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      const result = await fetchScoreHistory(trackerApplicationId)
      setData(result)
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error('score_history fetch failed'),
      )
      setData(null)
    } finally {
      setIsLoading(false)
    }
  }, [trackerApplicationId])

  useEffect(() => {
    void load()
  }, [load])

  return { data, isLoading, error, refetch: load }
}
