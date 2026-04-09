import { useState, useEffect } from 'react'
import { fetchCard } from '@/services/api'
import type { Card } from '@/types'

interface UseCardViewerResult {
  card: Card | null
  isLoading: boolean
  error: Error | null
}

export function useCardViewer(cardId: string): UseCardViewerResult {
  const [card, setCard] = useState<Card | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!cardId) return
    setIsLoading(true)
    setError(null)
    fetchCard(cardId)
      .then(setCard)
      .catch((err) => {
        const status = err?.response?.status
        setError(new Error(status === 404 ? 'Card not found' : 'Failed to load card'))
      })
      .finally(() => setIsLoading(false))
  }, [cardId])

  return { card, isLoading, error }
}
