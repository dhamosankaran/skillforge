import { useCallback, useEffect, useState } from 'react'
import {
  adminArchiveLesson,
  adminListLessons,
  adminListQuizItems,
  adminPublishLesson,
  adminUpdateLesson,
} from '@/services/api'
import type {
  Lesson,
  LessonUpdateRequest,
  LessonUpdateResponse,
  QuizItem,
} from '@/types'

interface UseAdminLessonEditorResult {
  lesson: Lesson | null
  activeQuizItems: QuizItem[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  updateLesson: (payload: LessonUpdateRequest) => Promise<LessonUpdateResponse>
  publishLesson: () => Promise<Lesson>
  archiveLesson: () => Promise<Lesson>
}

// Admin lesson editor hook. The slice does not ship a single-lesson admin
// GET endpoint (spec §5 covers POST/PATCH/publish/archive/list); we resolve
// `lessonId` by paging the deck's admin-LIST and matching by id. The deck id
// is required upfront so the list scopes correctly.
export function useAdminLessonEditor(
  deckId: string | undefined,
  lessonId: string | undefined,
): UseAdminLessonEditorResult {
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [activeQuizItems, setActiveQuizItems] = useState<QuizItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    if (!lessonId) {
      setLesson(null)
      setActiveQuizItems([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const [items] = await Promise.all([
        adminListQuizItems(lessonId, 'active'),
      ])
      setActiveQuizItems(items)

      if (deckId) {
        const lessons = await adminListLessons(deckId, 'all')
        const match = lessons.find((l) => l.id === lessonId) ?? null
        setLesson(match)
      }
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load lesson')
    } finally {
      setLoading(false)
    }
  }, [deckId, lessonId])

  useEffect(() => {
    void refetch()
  }, [refetch])

  const updateLesson = useCallback(
    async (payload: LessonUpdateRequest) => {
      if (!lessonId) throw new Error('No lesson selected')
      const response = await adminUpdateLesson(lessonId, payload)
      setLesson(response.lesson)
      // After a substantive edit the cascade retires every active quiz_item.
      // Mirror that locally so the page reflects the new state without a
      // network round-trip.
      if (response.version_type_applied === 'substantive') {
        setActiveQuizItems([])
      }
      return response
    },
    [lessonId],
  )

  const publishLesson = useCallback(async () => {
    if (!lessonId) throw new Error('No lesson selected')
    const next = await adminPublishLesson(lessonId)
    setLesson(next)
    return next
  }, [lessonId])

  const archiveLesson = useCallback(async () => {
    if (!lessonId) throw new Error('No lesson selected')
    const next = await adminArchiveLesson(lessonId)
    setLesson(next)
    return next
  }, [lessonId])

  return {
    lesson,
    activeQuizItems,
    loading,
    error,
    refetch,
    updateLesson,
    publishLesson,
    archiveLesson,
  }
}
