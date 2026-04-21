import { useState, useCallback } from 'react'
import { rewriteResume, rewriteSection, generateCoverLetter } from '@/services/api'
import type { RewriteResponse, RewriteSection, CoverLetterResponse } from '@/types'
import { capture } from '@/utils/posthog'

export function useRewrite() {
  const [rewriteResult, setRewriteResult] = useState<RewriteResponse | null>(null)
  const [coverLetter, setCoverLetter] = useState<CoverLetterResponse | null>(null)
  const [isLoadingRewrite, setIsLoadingRewrite] = useState(false)
  const [isLoadingCoverLetter, setIsLoadingCoverLetter] = useState(false)
  const [regeneratingIdx, setRegeneratingIdx] = useState<number | null>(null)

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

  const regenerateSection = useCallback(
    async (idx: number, section: RewriteSection, jdText: string) => {
      setRegeneratingIdx(idx)
      const beforeLen = section.content?.length ?? 0
      try {
        const { section: rewritten } = await rewriteSection(
          `sec-${idx}`,
          section.title,
          section.content || '',
          jdText,
        )
        setRewriteResult((prev) => {
          if (!prev) return prev
          const nextSections = prev.sections.map((s, i) => (i === idx ? rewritten : s))
          return { ...prev, sections: nextSections }
        })
        capture('rewrite_section_regenerated', {
          section_title: section.title,
          section_char_length_before: beforeLen,
          section_char_length_after: rewritten.content?.length ?? 0,
        })
      } finally {
        setRegeneratingIdx(null)
      }
    },
    []
  )

  return {
    rewriteResult,
    coverLetter,
    isLoadingRewrite,
    isLoadingCoverLetter,
    regeneratingIdx,
    runRewrite,
    runCoverLetter,
    regenerateSection,
  }
}
