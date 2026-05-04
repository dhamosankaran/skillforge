import { useCallback, useEffect, useState } from 'react'
import { fetchLoopProgress } from '@/services/api'
import type { LoopProgressResponse } from '@/types'

interface UseLoopProgressResult {
  data: LoopProgressResponse | null
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Spec #66 §6.1 — fetch the AppShell loop-progress envelope for a
 * tracker. Disabled (no fetch) when ``trackerApplicationId`` is null.
 *
 * D-14 LOCKED — on error, `data` stays null and the strip's step-2
 * derivation falls back to `'future'`. This intentionally prevents
 * step-3 unlock on transient BE failure (documented limitation; user
 * can refresh to retry).
 *
 * Mirrors the bare-`useState`/`useEffect` pattern used by
 * `useScoreHistory` + `useHomeState` (this codebase does not run
 * @tanstack/react-query).
 */
export function useLoopProgress(
  trackerApplicationId: string | null | undefined,
): UseLoopProgressResult {
  const [data, setData] = useState<LoopProgressResponse | null>(null)
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
      const result = await fetchLoopProgress(trackerApplicationId)
      setData(result)
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error('loop_progress fetch failed'),
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
