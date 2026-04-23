import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { AnalysisResponse } from '@/types'

// B-032 — paywall gate on Optimize / AI Rewrite buttons for free users.
// Mirrors Results.reanalyze.test.tsx (B-030) structure exactly.

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchOnboardingRecommendations: vi.fn().mockResolvedValue({ results: [] }),
    createCheckoutSession: vi.fn(),
    dismissPaywall: vi.fn(),
    fetchPricing: vi.fn().mockResolvedValue({
      currency: 'usd',
      price: 49,
      price_display: '$49/mo',
      stripe_price_id: 'price_test',
    }),
  }
})

let mockCanUsePro = false
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: mockCanUsePro ? 'pro' : 'free', scansUsed: 0, maxScans: 3 },
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

const RESULT: AnalysisResponse = {
  scan_id: 'scan-1',
  ats_score: 80,
  grade: 'A',
  score_breakdown: {
    keyword_match: 80,
    skills_coverage: 75,
    formatting_compliance: 90,
    bullet_strength: 70,
  },
  matched_keywords: ['python'],
  missing_keywords: [],
  skill_gaps: [],
  bullet_analysis: [],
  formatting_issues: [],
  job_fit_explanation: 'solid fit',
  top_strengths: [],
  top_gaps: [],
  keyword_chart_data: [],
  skills_overlap_data: [],
}

vi.mock('@/context/AnalysisContext', () => ({
  useAnalysisContext: () => ({
    state: {
      isLoading: false,
      result: RESULT,
      error: null,
      resumeFile: null,
      jobDescription: '',
    },
    dispatch: vi.fn(),
  }),
  AnalysisProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import Results from '@/pages/Results'

function renderResults() {
  return render(
    <MemoryRouter initialEntries={['/prep/results']}>
      <Results />
    </MemoryRouter>,
  )
}

describe('Results page — Optimize paywall gate (B-032)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCanUsePro = false
  })

  it('AC-1: free user click opens PaywallModal with rewrite_limit copy, no navigation', async () => {
    mockCanUsePro = false
    const user = userEvent.setup()
    renderResults()

    await user.click(screen.getByRole('button', { name: /^optimize$/i }))

    expect(screen.getByText('AI Rewrite is a Pro feature')).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('AC-2: pro user click navigates to /prep/rewrite and does not render paywall', async () => {
    mockCanUsePro = true
    const user = userEvent.setup()
    renderResults()

    await user.click(screen.getByRole('button', { name: /^optimize$/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/prep/rewrite')
    expect(
      screen.queryByText('AI Rewrite is a Pro feature'),
    ).not.toBeInTheDocument()
  })

  it('AC-3 (free): optimize_clicked fires with plan=free', async () => {
    mockCanUsePro = false
    const user = userEvent.setup()
    renderResults()

    await user.click(screen.getByRole('button', { name: /^optimize$/i }))

    expect(capture).toHaveBeenCalledWith('optimize_clicked', { plan: 'free' })
  })

  it('AC-3 (pro): optimize_clicked fires with plan=pro', async () => {
    mockCanUsePro = true
    const user = userEvent.setup()
    renderResults()

    await user.click(screen.getByRole('button', { name: /^optimize$/i }))

    expect(capture).toHaveBeenCalledWith('optimize_clicked', { plan: 'pro' })
  })

  it('AC-4: both Optimize (header) and AI Rewrite (sidebar) buttons share the same gate behavior for free users', async () => {
    mockCanUsePro = false
    const user = userEvent.setup()
    renderResults()

    // Header "Optimize" button
    await user.click(screen.getByRole('button', { name: /^optimize$/i }))
    expect(screen.getByText('AI Rewrite is a Pro feature')).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalled()
    expect(capture).toHaveBeenCalledWith('optimize_clicked', { plan: 'free' })

    // Sidebar "AI Rewrite" CTA — same handler, same outcome
    capture.mockClear()
    await user.click(screen.getByRole('button', { name: /^ai rewrite$/i }))
    expect(screen.getByText('AI Rewrite is a Pro feature')).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalled()
    expect(capture).toHaveBeenCalledWith('optimize_clicked', { plan: 'free' })
  })
})
