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

  // Spec #56's submit-time gate path is preserved as defense-in-depth in
  // `useAnalysis.ts` (cross-tab race per spec #60 LD-7) but is no longer
  // user-reachable from /prep/analyze — spec #60's pre-flight gate hides the
  // Analyze button before the click can happen. The gate behavior is covered
  // by the spec #60 describe block below; the defense-in-depth path is covered
  // by useAnalysis hook tests, not this page-level harness. Test rewritten to
  // assert the new at-cap path (gate visible, no API call) rather than the
  // now-unreachable submit-click.
  it('free user past cap: gate card replaces form + does not call API on page load', () => {
    usageState.scansUsed = 1
    usageState.canScan = false
    renderPage()

    expect(screen.getByTestId('analyze-scan-gate')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^analyze resume$/i })).toBeNull()
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

describe('Analyze page — spec #60 pre-flight gate (B-045)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usageState.plan = 'free'
    usageState.scansUsed = 0
    usageState.maxScans = 1
    usageState.isAdmin = false
    usageState.canScan = true
    usageState.canUsePro = false
  })

  it('AC-1/AC-2 — free user at cap: gate card renders, upload form absent', () => {
    usageState.scansUsed = 1
    usageState.canScan = false
    renderPage()
    expect(screen.getByTestId('analyze-scan-gate')).toBeInTheDocument()
    expect(screen.getByText(/you've used your free ats scan/i)).toBeInTheDocument()
    // Dropzone, JD textarea, Analyze button all absent (form replaced, not disabled).
    expect(screen.queryByRole('button', { name: /^analyze resume$/i })).toBeNull()
    expect(screen.queryByLabelText(/resume file upload/i)).toBeNull()
    expect(screen.queryByLabelText(/job description text/i)).toBeNull()
  })

  it('AC-3 — gate Upgrade CTA opens app-root paywall via setShowUpgradeModal(true)', async () => {
    usageState.scansUsed = 1
    usageState.canScan = false
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByTestId('analyze-scan-gate-cta'))
    expect(setShowUpgradeModal).toHaveBeenCalledWith(true)
  })

  it('AC-4 — Pro user: form renders, no gate card', () => {
    usageState.plan = 'pro'
    usageState.canScan = true
    usageState.canUsePro = true
    usageState.maxScans = -1
    renderPage()
    expect(screen.queryByTestId('analyze-scan-gate')).toBeNull()
    expect(screen.getByRole('button', { name: /analyze resume/i })).toBeInTheDocument()
  })

  it('AC-4 — Enterprise user: form renders, no gate card', () => {
    usageState.plan = 'enterprise'
    usageState.canScan = true
    usageState.canUsePro = true
    usageState.maxScans = -1
    renderPage()
    expect(screen.queryByTestId('analyze-scan-gate')).toBeNull()
    expect(screen.getByRole('button', { name: /analyze resume/i })).toBeInTheDocument()
  })

  it('AC-4 — admin on free plan: form renders, no gate card', () => {
    usageState.plan = 'free'
    usageState.isAdmin = true
    usageState.canScan = true
    usageState.canUsePro = true
    usageState.maxScans = -1
    renderPage()
    expect(screen.queryByTestId('analyze-scan-gate')).toBeNull()
    expect(screen.getByRole('button', { name: /analyze resume/i })).toBeInTheDocument()
  })

  it('AC-5 — free user with quota remaining: form renders, no gate card', () => {
    usageState.scansUsed = 0
    usageState.canScan = true
    renderPage()
    expect(screen.queryByTestId('analyze-scan-gate')).toBeNull()
    expect(screen.getByRole('button', { name: /analyze resume/i })).toBeInTheDocument()
  })

  it('AC-6 — quota chip stays visible above gate at cap; dead "Upgrade for more" span removed', () => {
    usageState.scansUsed = 1
    usageState.canScan = false
    renderPage()
    expect(screen.getByText('1/1')).toBeInTheDocument()
    expect(screen.getByText(/free scans used/i)).toBeInTheDocument()
    // Regression guard: dead span from spec #56 era removed entirely (LD-3).
    expect(screen.queryByText(/upgrade for more/i)).toBeNull()
  })

  it('AC-7 — paywall_hit fires once on gate mount with {trigger, surface, plan}', () => {
    usageState.scansUsed = 1
    usageState.canScan = false
    renderPage()
    const calls = capture.mock.calls.filter((c) => c[0] === 'paywall_hit')
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toEqual({
      trigger: 'scan_limit',
      surface: 'analyze_page_load',
      plan: 'free',
    })
  })

  it('AC-7 negative — paywall_hit does NOT fire when form renders normally', () => {
    usageState.plan = 'pro'
    usageState.canScan = true
    usageState.canUsePro = true
    usageState.maxScans = -1
    renderPage()
    const calls = capture.mock.calls.filter(
      (c) => c[0] === 'paywall_hit' && (c[1] as { surface?: string }).surface === 'analyze_page_load',
    )
    expect(calls).toHaveLength(0)
  })
})
