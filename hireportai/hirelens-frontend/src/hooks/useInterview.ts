import { useState, useCallback } from 'react'
import { generateInterviewPrep } from '@/services/api'
import type { InterviewPrepResponse } from '@/types'
import { AxiosError } from 'axios'

interface LimitInfo {
  limitReached: boolean
  limit: number
  remaining: number
}

export function useInterview() {
  const [interviewResult, setInterviewResult] = useState<InterviewPrepResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [limitInfo, setLimitInfo] = useState<LimitInfo | null>(null)

  const runInterviewPrep = useCallback(
    async (
      resumeText: string,
      jobDescription: string,
      options?: { forceRegenerate?: boolean },
    ) => {
      if (!resumeText.trim() || !jobDescription.trim()) return
      setIsLoading(true)
      setError(null)
      setLimitInfo(null)
      try {
        const result = await generateInterviewPrep(resumeText, jobDescription, options)
        setInterviewResult(result)
      } catch (err) {
        if (err instanceof AxiosError && err.response?.status === 403) {
          const detail = err.response.data?.detail
          if (detail?.code === 'LIMIT_REACHED') {
            setLimitInfo({
              limitReached: true,
              limit: detail.limit ?? 3,
              remaining: detail.remaining ?? 0,
            })
            return
          }
        }
        setError(err instanceof Error ? err.message : 'Failed to generate interview prep')
      } finally {
        setIsLoading(false)
      }
    },
    [],
  )

  const reset = useCallback(() => {
    setInterviewResult(null)
    setError(null)
    setLimitInfo(null)
  }, [])

  return { interviewResult, isLoading, error, limitInfo, runInterviewPrep, reset }
}
