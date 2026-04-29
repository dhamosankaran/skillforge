import { useEffect, useState } from 'react'
import { fetchRankedDecks, type FetchRankedDecksOptions } from '@/services/api'
import type { RankedDecksResponse } from '@/types'

interface UseRankedDecksResult {
  data: RankedDecksResponse | null
  isLoading: boolean
  error: Error | null
  isColdStart: boolean
}

// Phase 6 slice 6.7 — FE consumer for slice 6.6's GET /api/v1/learn/ranked-decks.
// Spec #08 §5.1 + §6 (cold-start branch). Skip the call when `enabled=false`
// (e.g. career_climber persona — see §4.2 cross-cutting rule + §10.3 test #5).
export function useRankedDecks(
  enabled: boolean,
  opts: FetchRankedDecksOptions = {},
): UseRankedDecksResult {
  const [data, setData] = useState<RankedDecksResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(enabled)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!enabled) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchRankedDecks(opts)
      .then((res) => {
        if (cancelled) return
        setData(res)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err : new Error('Failed to load ranked decks'))
      })
      .finally(() => {
        if (cancelled) return
        setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, opts.lookback_days, opts.max_scans])

  return {
    data,
    isLoading,
    error,
    isColdStart: data?.cold_start ?? false,
  }
}
