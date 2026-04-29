import { useEffect, useState } from 'react'
import { fetchFsrsDashboard, type FetchFsrsDashboardOptions } from '@/services/api'
import type { DashboardResponse } from '@/types'

interface UseFsrsDashboardResult {
  data: DashboardResponse | null
  isLoading: boolean
  error: Error | null
  isColdStart: boolean
}

// Phase 6 slice 6.8 — FE consumer for `GET /api/v1/learn/dashboard`.
// Spec #09 §5.1 + §6 + §12 D-3 (single envelope) / D-7 (default 30d window).
// Mirrors useRankedDecks.ts cancellable-effect pattern.
export function useFsrsDashboard(
  opts: FetchFsrsDashboardOptions = {},
): UseFsrsDashboardResult {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchFsrsDashboard(opts)
      .then((res) => {
        if (cancelled) return
        setData(res)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err : new Error('Failed to load dashboard'))
      })
      .finally(() => {
        if (cancelled) return
        setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.retention_window_days])

  return {
    data,
    isLoading,
    error,
    isColdStart: data?.is_cold_start ?? false,
  }
}
