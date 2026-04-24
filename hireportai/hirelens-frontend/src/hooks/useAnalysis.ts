import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { analyzeResume } from '@/services/api'
import { useAnalysisContext } from '@/context/AnalysisContext'
import { useUsage } from '@/context/UsageContext'
import { capture } from '@/utils/posthog'

/** Shape of the 402 detail body produced by analyze when the free-tier
 *  1-lifetime cap is hit (spec #56, mirrors spec #50's DailyReviewLimitError
 *  envelope). */
export interface ScanLimitDetail {
  error: 'free_tier_limit'
  trigger: 'scan_limit'
  scans_used: number
  scans_limit: number
  plan: string
}

function extractScanLimitDetail(err: unknown): ScanLimitDetail | null {
  if (!axios.isAxiosError(err)) return null
  if (err.response?.status !== 402) return null
  const detail = err.response.data?.detail
  if (!detail || typeof detail !== 'object') return null
  if (detail.trigger !== 'scan_limit') return null
  return detail as ScanLimitDetail
}

export function useAnalysis() {
  const { state, dispatch } = useAnalysisContext()
  const { usage, canScan, refreshUsage, setShowUpgradeModal } = useUsage()
  const navigate = useNavigate()

  const runAnalysis = useCallback(async () => {
    const { resumeFile, jobDescription } = state
    if (!resumeFile || !jobDescription.trim()) return

    // Client-side pre-gate — cheap bounce before hitting the network.
    // BE is still authoritative via the 402 handler below (spec #56 LD-2).
    if (!canScan) {
      capture('free_scan_cap_hit', {
        attempted_action: 'initial',
        scans_used_at_hit: usage.scansUsed,
      })
      setShowUpgradeModal(true)
      return
    }

    dispatch({ type: 'SET_LOADING', payload: true })
    try {
      const result = await analyzeResume(resumeFile, jobDescription)
      dispatch({ type: 'SET_RESULT', payload: result })
      // Re-hydrate usage from BE so scans_used reflects the committed row.
      await refreshUsage()
      // Post-scan lands on the onboarding bridge (spec #09). A client-side
      // scan_id is used purely for PostHog correlation — the backend doesn't
      // persist scans yet.
      const scanId =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`
      navigate(`/onboarding?scan_id=${encodeURIComponent(scanId)}`)
    } catch (err) {
      const capDetail = extractScanLimitDetail(err)
      if (capDetail) {
        // BE-authoritative cap hit — refresh usage so the UI reflects the
        // server count, fire the event, and surface the paywall.
        capture('free_scan_cap_hit', {
          attempted_action: 'initial',
          scans_used_at_hit: capDetail.scans_used,
        })
        await refreshUsage()
        dispatch({ type: 'SET_LOADING', payload: false })
        setShowUpgradeModal(true)
        return
      }
      const message = err instanceof Error ? err.message : 'Analysis failed'
      dispatch({ type: 'SET_ERROR', payload: message })
    }
  }, [state, dispatch, navigate, canScan, refreshUsage, setShowUpgradeModal, usage.scansUsed])

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
