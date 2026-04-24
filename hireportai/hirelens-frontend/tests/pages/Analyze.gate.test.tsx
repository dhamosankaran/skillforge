import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// Spec #56 — Analyze page free-tier cap gate. The modal UI is owned by
// the app-root `UpgradeModal` (wired to `useUsage().showUpgradeModal`);
// here we just assert the context setter fires.

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const mockAnalyzeResume = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    analyzeResume: (...args: unknown[]) => mockAnalyzeResume(...args),
    fetchUsage: vi.fn().mockResolvedValue({
      plan: 'free',
      scans_used: 1,
      scans_remaining: 0,
      max_scans: 1,
      is_admin: false,
    }),
  }
})

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

// Configurable UsageContext — avoids wiring the real BE fetch in unit tests.
const usageState = {
  plan: 'free' as 'free' | 'pro' | 'enterprise',
  scansUsed: 0,
  maxScans: 1,
  isAdmin: false,
  canScan: true,
  canUsePro: false,
}
const setShowUpgradeModal = vi.fn()
const refreshUsage = vi.fn().mockResolvedValue(undefined)

vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: {
      plan: usageState.plan,
      scansUsed: usageState.scansUsed,
      maxScans: usageState.maxScans,
      isAdmin: usageState.isAdmin,
    },
    canScan: usageState.canScan,
    canUsePro: usageState.canUsePro,
    canUsePremium: usageState.canUsePro,
    refreshUsage,
    upgradePlan: vi.fn(),
    showUpgradeModal: false,
    setShowUpgradeModal,
    checkAndPromptUpgrade: vi.fn(),
  }),
  UsageProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('@/context/AnalysisContext', () => {
  const dispatch = vi.fn()
  return {
    useAnalysisContext: () => ({
      state: {
        isLoading: false,
        result: null,
        error: null,
        resumeFile: new File([new Uint8Array(300)], 'r.pdf', { type: 'application/pdf' }),
        jobDescription:
          'We are hiring a senior engineer with 5+ years experience in Python, FastAPI, and distributed systems. Must ship to production.',
      },
      dispatch,
    }),
    AnalysisProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  }
})

import Analyze from '@/pages/Analyze'

function renderPage() {
  return render(
    <MemoryRouter>
      <Analyze />
    </MemoryRouter>,
  )
}

describe('Analyze page — spec #56 free-tier gate', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usageState.plan = 'free'
    usageState.scansUsed = 0
    usageState.maxScans = 1
    usageState.isAdmin = false
    usageState.canScan = true
    usageState.canUsePro = false
  })

  it('renders dynamic free-scan counter from context (no hardcoded /3)', () => {
    usageState.scansUsed = 0
    usageState.maxScans = 1
    renderPage()
    expect(screen.getByText('0/1')).toBeInTheDocument()
    expect(screen.queryByText('0/3')).not.toBeInTheDocument()
  })

  it('free user past cap: submit opens upgrade modal + fires free_scan_cap_hit + does not call API', async () => {
    usageState.scansUsed = 1
    usageState.canScan = false
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /analyze resume/i }))

    expect(setShowUpgradeModal).toHaveBeenCalledWith(true)
    expect(capture).toHaveBeenCalledWith('free_scan_cap_hit', {
      attempted_action: 'initial',
      scans_used_at_hit: 1,
    })
    expect(mockAnalyzeResume).not.toHaveBeenCalled()
  })

  it('free user under cap: submit calls analyze API and does not open paywall', async () => {
    usageState.scansUsed = 0
    usageState.canScan = true
    mockAnalyzeResume.mockResolvedValueOnce({
      scan_id: 's1',
      ats_score: 80,
      grade: 'A',
      score_breakdown: {
        keyword_match: 80, skills_coverage: 70, formatting_compliance: 90, bullet_strength: 60,
      },
      matched_keywords: [], missing_keywords: [], skill_gaps: [],
      bullet_analysis: [], formatting_issues: [],
      job_fit_explanation: '', top_strengths: [], top_gaps: [],
      keyword_chart_data: [], skills_overlap_data: [],
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /analyze resume/i }))

    expect(mockAnalyzeResume).toHaveBeenCalledTimes(1)
    expect(setShowUpgradeModal).not.toHaveBeenCalled()
  })

  it('pro user: counter block is hidden; submit is not gated client-side', async () => {
    usageState.plan = 'pro'
    usageState.canScan = true
    usageState.canUsePro = true
    usageState.maxScans = -1
    mockAnalyzeResume.mockResolvedValueOnce({
      scan_id: 's2', ats_score: 90, grade: 'A',
      score_breakdown: { keyword_match: 90, skills_coverage: 90, formatting_compliance: 90, bullet_strength: 90 },
      matched_keywords: [], missing_keywords: [], skill_gaps: [],
      bullet_analysis: [], formatting_issues: [],
      job_fit_explanation: '', top_strengths: [], top_gaps: [],
      keyword_chart_data: [], skills_overlap_data: [],
    })
    const user = userEvent.setup()
    renderPage()

    // No free-scan indicator for pro.
    expect(screen.queryByText(/free scans used/i)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /analyze resume/i }))
    expect(setShowUpgradeModal).not.toHaveBeenCalled()
  })

  it('admin on free plan: counter hidden (is_admin bypass)', () => {
    usageState.plan = 'free'
    usageState.isAdmin = true
    usageState.maxScans = -1
    usageState.canUsePro = true
    renderPage()
    expect(screen.queryByText(/free scans used/i)).not.toBeInTheDocument()
  })
})
