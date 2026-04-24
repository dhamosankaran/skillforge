/** Spec #59 — Results.tsx hydration from URL scan_id (AC-6).
 *
 * Covers the five branches of the hydration effect:
 *   1. result === null + URL scan_id + 200 → dispatch(SET_RESULT) + full dashboard
 *   2. result === null + URL scan_id + 410 → legacy empty-state copy (Clock icon,
 *      "re-scan to view")
 *   3. result === null + URL scan_id + 404 → generic empty-state ("No Analysis Yet")
 *   4. result === null + URL scan_id + network error → retryable error empty-state
 *   5. result === null + NO URL scan_id → idle empty-state (no fetch attempted)
 *
 * Also asserts:
 *   - result !== null on mount → no fetch fires (short-circuit)
 *   - scan_rehydrated / scan_rehydrate_failed PostHog events fire per branch
 *   - retry CTA on the error state re-triggers the hydration effect
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { AnalysisResponse } from '@/types'

// ─── Mocks ────────────────────────────────────────────────────────────────

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchScanById = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchScanById: (...args: unknown[]) => fetchScanById(...args),
    fetchOnboardingRecommendations: vi.fn().mockResolvedValue({ results: [] }),
  }
})

let mockCanUsePro = false
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: 'free', scansUsed: 0, maxScans: 3 },
    canScan: true,
    canUsePro: mockCanUsePro,
    canUsePremium: mockCanUsePro,
    incrementScan: vi.fn(),
    upgradePlan: vi.fn(),
    showUpgradeModal: false,
    setShowUpgradeModal: vi.fn(),
    checkAndPromptUpgrade: vi.fn(),
  }),
  UsageProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'u1', email: 't@e.com', name: 'T' },
    isLoading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
    updateUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// AnalysisContext mock — swap `contextResult` per-test to simulate
// "fresh session empty context" vs "populated context" branches.
let contextResult: AnalysisResponse | null = null
const contextDispatch = vi.fn()
vi.mock('@/context/AnalysisContext', () => ({
  useAnalysisContext: () => ({
    state: {
      isLoading: false,
      result: contextResult,
      error: null,
      resumeFile: null,
      jobDescription: '',
    },
    dispatch: contextDispatch,
  }),
  AnalysisProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

const FULL_RESULT: AnalysisResponse = {
  scan_id: 'scan-xyz',
  ats_score: 88,
  grade: 'A',
  score_breakdown: {
    keyword_match: 85,
    skills_coverage: 90,
    formatting_compliance: 92,
    bullet_strength: 80,
  },
  matched_keywords: ['python', 'fastapi'],
  missing_keywords: [],
  skill_gaps: [],
  bullet_analysis: [],
  formatting_issues: [],
  job_fit_explanation: 'Strong backend match.',
  top_strengths: ['python'],
  top_gaps: [],
  keyword_chart_data: [],
  skills_overlap_data: [],
}

import Results from '@/pages/Results'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Results />
    </MemoryRouter>,
  )
}

function axios404() {
  return Object.assign(new Error('Not Found'), {
    isAxiosError: true,
    response: { status: 404, data: {} },
  })
}

function axios410() {
  return Object.assign(new Error('Gone'), {
    isAxiosError: true,
    response: { status: 410, data: {} },
  })
}

function networkError() {
  return Object.assign(new Error('Network Error'), {
    isAxiosError: true,
    response: undefined,
  })
}

describe('Results hydration from URL scan_id (spec #59, AC-6)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    contextResult = null
    mockCanUsePro = false
  })

  it('200 path: hydrates context, renders full dashboard, fires scan_rehydrated', async () => {
    fetchScanById.mockResolvedValueOnce(FULL_RESULT)
    renderAt('/prep/results?scan_id=scan-xyz')

    await waitFor(() => {
      expect(contextDispatch).toHaveBeenCalledWith({
        type: 'SET_RESULT',
        payload: FULL_RESULT,
      })
    })
    expect(fetchScanById).toHaveBeenCalledWith('scan-xyz')
    expect(capture).toHaveBeenCalledWith('scan_rehydrated', {
      scan_id: 'scan-xyz',
    })
  })

  it('410 legacy: renders legacy empty-state copy + fires scan_rehydrate_failed', async () => {
    fetchScanById.mockRejectedValueOnce(axios410())
    renderAt('/prep/results?scan_id=legacy-scan')

    await waitFor(() => {
      expect(
        screen.getByTestId('results-empty-legacy'),
      ).toBeInTheDocument()
    })
    expect(
      screen.getByText(
        'This scan is from before we stored full results — re-scan to view.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('Results Not Available')).toBeInTheDocument()
    expect(contextDispatch).not.toHaveBeenCalled()
    expect(capture).toHaveBeenCalledWith('scan_rehydrate_failed', {
      scan_id: 'legacy-scan',
      reason: 'legacy',
      http_status: 410,
    })
  })

  it('404 not-found: renders generic empty-state copy', async () => {
    fetchScanById.mockRejectedValueOnce(axios404())
    renderAt('/prep/results?scan_id=missing-scan')

    await waitFor(() => {
      expect(
        screen.getByTestId('results-empty-not_found'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('No Analysis Yet')).toBeInTheDocument()
    expect(
      screen.getByText('Upload your resume to see your results.'),
    ).toBeInTheDocument()
    expect(capture).toHaveBeenCalledWith('scan_rehydrate_failed', {
      scan_id: 'missing-scan',
      reason: 'not_found',
      http_status: 404,
    })
  })

  it('network error: renders retryable error empty-state', async () => {
    fetchScanById.mockRejectedValueOnce(networkError())
    renderAt('/prep/results?scan_id=net-fail')

    await waitFor(() => {
      expect(
        screen.getByTestId('results-empty-error'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText("Couldn't Load Results")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    expect(capture).toHaveBeenCalledWith('scan_rehydrate_failed', {
      scan_id: 'net-fail',
      reason: 'error',
      http_status: 0,
    })
  })

  it('no URL scan_id: shows idle empty-state, no fetch attempted', async () => {
    renderAt('/prep/results')

    // Idle branch uses the 'not_found' copy (LD-4 spec §10 — idle and
    // not_found collapse to the same "Start Analysis" CTA).
    expect(screen.getByText('No Analysis Yet')).toBeInTheDocument()
    expect(fetchScanById).not.toHaveBeenCalled()
    expect(contextDispatch).not.toHaveBeenCalled()
  })

  it('context already populated: no fetch fires even with URL scan_id', async () => {
    contextResult = FULL_RESULT
    renderAt('/prep/results?scan_id=scan-xyz')

    // Effect short-circuits on result !== null.
    expect(fetchScanById).not.toHaveBeenCalled()
  })

  it('retry from error state re-triggers the fetch', async () => {
    fetchScanById
      .mockRejectedValueOnce(networkError())
      .mockResolvedValueOnce(FULL_RESULT)

    const user = userEvent.setup()
    renderAt('/prep/results?scan_id=scan-xyz')

    await waitFor(() => {
      expect(screen.getByTestId('results-empty-error')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /retry/i }))

    await waitFor(() => {
      expect(contextDispatch).toHaveBeenCalledWith({
        type: 'SET_RESULT',
        payload: FULL_RESULT,
      })
    })
    expect(fetchScanById).toHaveBeenCalledTimes(2)
  })
})
