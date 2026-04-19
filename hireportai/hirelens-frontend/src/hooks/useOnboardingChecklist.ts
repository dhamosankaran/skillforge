import { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { fetchOnboardingChecklist, type ChecklistResponse } from '@/services/api'

interface UseOnboardingChecklistResult {
  data: ChecklistResponse | null
  isLoading: boolean
  error: Error | null
}

/**
 * Fetches the Interview-Prepper 5-step onboarding checklist.
 *
 * Only fires when `user.persona === 'interview_prepper'`. For every
 * other persona (including `null`) the hook returns `{data: null,
 * isLoading: false}` and never hits the network — mirrors the
 * persona-gate contract on the backend endpoint (403 for non-Prepper).
 */
export function useOnboardingChecklist(): UseOnboardingChecklistResult {
  const { user } = useAuth()
  const [data, setData] = useState<ChecklistResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (user?.persona !== 'interview_prepper') {
      setData(null)
      setIsLoading(false)
      setError(null)
      return
    }

    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchOnboardingChecklist()
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error('checklist fetch failed'))
          setData(null)
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [user?.persona])

  return { data, isLoading, error }
}
