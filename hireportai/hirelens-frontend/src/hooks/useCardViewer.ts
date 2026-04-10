import { useState, useEffect } from 'react'
import { fetchCard } from '@/services/api'
import type { Card } from '@/types'

interface UseCardViewerResult {
  card: Card | null
  isLoading: boolean
  error: Error | null
  /** True when the backend returned 403 — card exists but free user
   *  cannot access it. Drives PaywallModal in the viewer. */
  forbidden: boolean
}

export function useCardViewer(cardId: string): UseCardViewerResult {
  const [card, setCard] = useState<Card | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    if (!cardId) return
    setIsLoading(true)
    setError(null)
    setForbidden(false)
    fetchCard(cardId)
      .then(setCard)
      .catch((err) => {
        const status = err?.response?.status
        if (status === 403) {
          setForbidden(true)
          return
        }
        setError(new Error(status === 404 ? 'Card not found' : 'Failed to load card'))
      })
      .finally(() => setIsLoading(false))
  }, [cardId])

  return { card, isLoading, error, forbidden }
}
