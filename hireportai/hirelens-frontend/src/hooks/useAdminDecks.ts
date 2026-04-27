import { useCallback, useEffect, useState } from 'react'
import {
  adminArchiveDeck,
  adminCreateDeck,
  adminListDecks,
  adminUpdateDeck,
} from '@/services/api'
import type {
  AdminDeckStatusFilter,
  Deck,
  DeckCreateRequest,
  DeckUpdateRequest,
} from '@/types'

interface UseAdminDecksResult {
  decks: Deck[]
  loading: boolean
  error: string | null
  status: AdminDeckStatusFilter
  setStatus: (next: AdminDeckStatusFilter) => void
  refetch: () => Promise<void>
  createDeck: (payload: DeckCreateRequest) => Promise<Deck>
  updateDeck: (id: string, payload: DeckUpdateRequest) => Promise<Deck>
  archiveDeck: (id: string) => Promise<Deck>
}

export function useAdminDecks(
  initialStatus: AdminDeckStatusFilter = 'active',
): UseAdminDecksResult {
  const [decks, setDecks] = useState<Deck[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<AdminDeckStatusFilter>(initialStatus)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await adminListDecks(status)
      setDecks(list)
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load decks')
    } finally {
      setLoading(false)
    }
  }, [status])

  useEffect(() => {
    void refetch()
  }, [refetch])

  const createDeck = useCallback(
    async (payload: DeckCreateRequest) => {
      const next = await adminCreateDeck(payload)
      await refetch()
      return next
    },
    [refetch],
  )

  const updateDeck = useCallback(
    async (id: string, payload: DeckUpdateRequest) => {
      const next = await adminUpdateDeck(id, payload)
      await refetch()
      return next
    },
    [refetch],
  )

  const archiveDeck = useCallback(
    async (id: string) => {
      const next = await adminArchiveDeck(id)
      await refetch()
      return next
    },
    [refetch],
  )

  return {
    decks,
    loading,
    error,
    status,
    setStatus,
    refetch,
    createDeck,
    updateDeck,
    archiveDeck,
  }
}
