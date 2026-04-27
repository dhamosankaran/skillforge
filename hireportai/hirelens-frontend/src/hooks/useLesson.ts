import { useCallback, useEffect, useState } from 'react'
import { AxiosError } from 'axios'
import { fetchLesson } from '@/services/api'
import type { LessonWithQuizzes } from '@/types'

export type LessonError = 'not_found' | 'network' | null

interface UseLessonResult {
  lesson: LessonWithQuizzes | null
  isLoading: boolean
  error: LessonError
  reload: () => void
}

/** Fetch a lesson by id (slice 6.3). 404 → `error: 'not_found'`. */
export function useLesson(lessonId: string | undefined): UseLessonResult {
  const [lesson, setLesson] = useState<LessonWithQuizzes | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<LessonError>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!lessonId) {
      setIsLoading(false)
      setError('not_found')
      setLesson(null)
      return
    }
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchLesson(lessonId)
      .then((data) => {
        if (cancelled) return
        setLesson(data)
        setIsLoading(false)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        if (err instanceof AxiosError && err.response?.status === 404) {
          setError('not_found')
        } else {
          setError('network')
        }
        setLesson(null)
        setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lessonId, reloadKey])

  const reload = useCallback(() => setReloadKey((k) => k + 1), [])
  return { lesson, isLoading, error, reload }
}
