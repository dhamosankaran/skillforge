import { useCallback, useEffect, useState } from 'react'
import {
  adminCreateQuizItem,
  adminListQuizItems,
  adminRetireQuizItem,
  adminUpdateQuizItem,
} from '@/services/api'
import type {
  AdminQuizItemStatusFilter,
  QuizItem,
  QuizItemCreateRequest,
  QuizItemUpdateRequest,
} from '@/types'

interface UseAdminQuizItemsResult {
  items: QuizItem[]
  loading: boolean
  error: string | null
  status: AdminQuizItemStatusFilter
  setStatus: (next: AdminQuizItemStatusFilter) => void
  refetch: () => Promise<void>
  createQuizItem: (payload: QuizItemCreateRequest) => Promise<QuizItem>
  updateQuizItem: (
    quizItemId: string,
    payload: QuizItemUpdateRequest,
  ) => Promise<QuizItem>
  retireQuizItem: (quizItemId: string) => Promise<QuizItem>
}

export function useAdminQuizItems(
  lessonId: string | undefined,
  initialStatus: AdminQuizItemStatusFilter = 'active',
): UseAdminQuizItemsResult {
  const [items, setItems] = useState<QuizItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<AdminQuizItemStatusFilter>(initialStatus)

  const refetch = useCallback(async () => {
    if (!lessonId) {
      setItems([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const list = await adminListQuizItems(lessonId, status)
      setItems(list)
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load quiz items')
    } finally {
      setLoading(false)
    }
  }, [lessonId, status])

  useEffect(() => {
    void refetch()
  }, [refetch])

  const createQuizItem = useCallback(
    async (payload: QuizItemCreateRequest) => {
      if (!lessonId) throw new Error('No lesson selected')
      const next = await adminCreateQuizItem(lessonId, payload)
      await refetch()
      return next
    },
    [lessonId, refetch],
  )

  const updateQuizItem = useCallback(
    async (quizItemId: string, payload: QuizItemUpdateRequest) => {
      const next = await adminUpdateQuizItem(quizItemId, payload)
      await refetch()
      return next
    },
    [refetch],
  )

  const retireQuizItem = useCallback(
    async (quizItemId: string) => {
      const next = await adminRetireQuizItem(quizItemId)
      await refetch()
      return next
    },
    [refetch],
  )

  return {
    items,
    loading,
    error,
    status,
    setStatus,
    refetch,
    createQuizItem,
    updateQuizItem,
    retireQuizItem,
  }
}
