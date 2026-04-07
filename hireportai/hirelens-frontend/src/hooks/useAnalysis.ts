import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeResume } from '@/services/api'
import { useAnalysisContext } from '@/context/AnalysisContext'
import { useUsage } from '@/context/UsageContext'

export function useAnalysis() {
  const { state, dispatch } = useAnalysisContext()
  const { checkAndPromptUpgrade, incrementScan } = useUsage()
  const navigate = useNavigate()

  const runAnalysis = useCallback(async () => {
    const { resumeFile, jobDescription } = state
    if (!resumeFile || !jobDescription.trim()) return

    // Check usage limits before running
    if (!checkAndPromptUpgrade()) return

    dispatch({ type: 'SET_LOADING', payload: true })
    try {
      const result = await analyzeResume(resumeFile, jobDescription)
      dispatch({ type: 'SET_RESULT', payload: result })
      incrementScan()
      navigate('/results')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed'
      dispatch({ type: 'SET_ERROR', payload: message })
    }
  }, [state, dispatch, navigate, checkAndPromptUpgrade, incrementScan])

  const setFile = useCallback(
    (file: File | null) => dispatch({ type: 'SET_RESUME_FILE', payload: file }),
    [dispatch]
  )

  const setJobDescription = useCallback(
    (jd: string) => dispatch({ type: 'SET_JD', payload: jd }),
    [dispatch]
  )

  const reset = useCallback(() => dispatch({ type: 'RESET' }), [dispatch])

  return {
    ...state,
    runAnalysis,
    setFile,
    setJobDescription,
    reset,
  }
}
