import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchHomeState } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { HomeStateResponse } from '@/types/homeState'

interface UseHomeStateResult {
  data: HomeStateResponse | null
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Fetches the state-aware home dashboard payload from
 * `GET /api/v1/home/state`. Fires `home_state_evaluated` analytics
 * exactly once per resolved fetch (deduped via ref so React Strict
 * Mode's double-invoked effect doesn't double-fire).
 *
 * On API error, returns `data: null` and surfaces the error — the
 * caller (StateAwareWidgets) renders nothing in that case so the
 * static persona grid remains the home page.
 */
export function useHomeState(): UseHomeStateResult {
  const [data, setData] = useState<HomeStateResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<Error | null>(null)
  const capturedRef = useRef<string | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await fetchHomeState()
      setData(result)
      const fingerprint = `${result.persona ?? ''}|${result.states.join(',')}`
      if (capturedRef.current !== fingerprint) {
        capturedRef.current = fingerprint
        capture('home_state_evaluated', {
          persona: result.persona,
          states: result.states,
          state_count: result.states.length,
          cache_hit: false,
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('home_state fetch failed'))
      setData(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return { data, isLoading, error, refetch: load }
}
