import { useState, useCallback } from 'react'
import { generateInterviewPrep } from '@/services/api'
import type { InterviewPrepResponse } from '@/types'

export function useInterview() {
  const [interviewResult, setInterviewResult] = useState<InterviewPrepResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runInterviewPrep = useCallback(async (resumeText: string, jobDescription: string) => {
    if (!resumeText.trim() || !jobDescription.trim()) return
    setIsLoading(true)
    setError(null)
    try {
      const result = await generateInterviewPrep(resumeText, jobDescription)
      setInterviewResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate interview prep')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setInterviewResult(null)
    setError(null)
  }, [])

  return { interviewResult, isLoading, error, runInterviewPrep, reset }
}
