import { useState, useCallback } from 'react'
import { rewriteResume, generateCoverLetter } from '@/services/api'
import type { RewriteResponse, CoverLetterResponse } from '@/types'

export function useRewrite() {
  const [rewriteResult, setRewriteResult] = useState<RewriteResponse | null>(null)
  const [coverLetter, setCoverLetter] = useState<CoverLetterResponse | null>(null)
  const [isLoadingRewrite, setIsLoadingRewrite] = useState(false)
  const [isLoadingCoverLetter, setIsLoadingCoverLetter] = useState(false)

  const runRewrite = useCallback(
    async (resumeText: string, jdText: string, templateType?: string, major?: string) => {
      setIsLoadingRewrite(true)
      try {
        const result = await rewriteResume(resumeText, jdText, templateType, major)
        setRewriteResult(result)
      } finally {
        setIsLoadingRewrite(false)
      }
    },
    []
  )

  const runCoverLetter = useCallback(
    async (resumeText: string, jdText: string, tone: string) => {
      setIsLoadingCoverLetter(true)
      try {
        const result = await generateCoverLetter(resumeText, jdText, tone)
        setCoverLetter(result)
      } finally {
        setIsLoadingCoverLetter(false)
      }
    },
    []
  )

  return {
    rewriteResult,
    coverLetter,
    isLoadingRewrite,
    isLoadingCoverLetter,
    runRewrite,
    runCoverLetter,
  }
}
