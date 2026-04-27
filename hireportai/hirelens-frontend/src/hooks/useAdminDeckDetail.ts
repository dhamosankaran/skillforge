import { useCallback, useEffect, useState } from 'react'
import {
  adminArchiveDeck,
  adminListDecks,
  adminListLessons,
  adminUpdateDeck,
} from '@/services/api'
import type {
  AdminLessonStatusFilter,
  Deck,
  DeckUpdateRequest,
  Lesson,
} from '@/types'

interface UseAdminDeckDetailResult {
  deck: Deck | null
  lessons: Lesson[]
  loading: boolean
  error: string | null
  lessonStatus: AdminLessonStatusFilter
  setLessonStatus: (next: AdminLessonStatusFilter) => void
  refetch: () => Promise<void>
  updateDeck: (payload: DeckUpdateRequest) => Promise<Deck>
  archiveDeck: () => Promise<Deck>
}

export function useAdminDeckDetail(
  deckId: string | undefined,
  initialLessonStatus: AdminLessonStatusFilter = 'active',
): UseAdminDeckDetailResult {
  const [deck, setDeck] = useState<Deck | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lessonStatus, setLessonStatus] = useState<AdminLessonStatusFilter>(
    initialLessonStatus,
  )

  const refetch = useCallback(async () => {
    if (!deckId) {
      setDeck(null)
      setLessons([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      // Admin-LIST decks endpoint returns the full table; pick the matching
      // deck. (Slice 6.4 spec does not ship a single-deck admin GET; this
      // matches §5.4 + the Lens-ranked admin-LIST contract.)
      const [allDecks, lessonList] = await Promise.all([
        adminListDecks('all'),
        adminListLessons(deckId, lessonStatus),
      ])
      const match = allDecks.find((d) => d.id === deckId) ?? null
      setDeck(match)
      setLessons(lessonList)
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load deck')
    } finally {
      setLoading(false)
    }
  }, [deckId, lessonStatus])

  useEffect(() => {
    void refetch()
  }, [refetch])

  const updateDeck = useCallback(
    async (payload: DeckUpdateRequest) => {
      if (!deckId) throw new Error('No deck selected')
      const next = await adminUpdateDeck(deckId, payload)
      setDeck(next)
      return next
    },
    [deckId],
  )

  const archiveDeck = useCallback(async () => {
    if (!deckId) throw new Error('No deck selected')
    const next = await adminArchiveDeck(deckId)
    setDeck(next)
    return next
  }, [deckId])

  return {
    deck,
    lessons,
    loading,
    error,
    lessonStatus,
    setLessonStatus,
    refetch,
    updateDeck,
    archiveDeck,
  }
}
