import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { ReactNode } from 'react'
import type { InterviewPrepResponse } from '@/types'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const generateInterviewPrep = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    generateInterviewPrep: (...args: unknown[]) => generateInterviewPrep(...args),
  }
})

let mockPlan: 'free' | 'pro' = 'free'
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: mockPlan, scansUsed: 0, maxScans: mockPlan === 'free' ? 3 : Infinity },
    canScan: true,
    canUsePro: mockPlan === 'pro',
    canUsePremium: mockPlan === 'pro',
    incrementScan: vi.fn(),
    upgradePlan: vi.fn(),
    showUpgradeModal: false,
    setShowUpgradeModal: vi.fn(),
    checkAndPromptUpgrade: vi.fn(),
  }),
  UsageProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

// Stub AnalysisContext to provide resume + JD so the page jumps straight to
// the "ready to generate" state without exercising the manual-input branch.
const RESUME = 'A'.repeat(120)
const JD = 'B'.repeat(120)
vi.mock('@/context/AnalysisContext', () => ({
  useAnalysisContext: () => ({
    state: {
      isLoading: false,
      error: null,
      result: { resume_text: RESUME },
      resumeFile: null,
      jobDescription: JD,
    },
    dispatch: vi.fn(),
  }),
  AnalysisProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import Interview from '@/pages/Interview'

function renderInterview() {
  return render(
    <MemoryRouter initialEntries={['/prep/interview']}>
      <Interview />
    </MemoryRouter>,
  )
}

const SAMPLE_QUESTIONS = [
  { question: 'Tell me about a time you led a team', star_framework: 'Situation: ...' },
]

beforeEach(() => {
  capture.mockReset()
  generateInterviewPrep.mockReset()
  mockPlan = 'free'
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Interview page — cache-aware UI (5.17b)', () => {
  it('renders the cached chip and hides the free-usage chip when response.cached === true', async () => {
    const user = userEvent.setup()
    const generatedAt = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() // 2h ago
    const cachedResponse: InterviewPrepResponse = {
      questions: SAMPLE_QUESTIONS,
      cached: true,
      generated_at: generatedAt,
      model_used: 'gemini-2.5-pro',
    }
    generateInterviewPrep.mockResolvedValueOnce(cachedResponse)

    renderInterview()
    await user.click(screen.getByRole('button', { name: /Generate Interview Questions/i }))

    await waitFor(() => expect(screen.getByTestId('cached-chip')).toBeInTheDocument())
    expect(screen.getByTestId('cached-chip').textContent).toMatch(/Cached/)
    // AC-5a: cache hits never show the "uses 1 of N" chip — would be wrong UX
    // because cache hits don't decrement the free-tier counter.
    expect(screen.queryByTestId('free-usage-chip')).not.toBeInTheDocument()
  })

  it('shows the "uses 1 of monthly free generations" chip on a fresh (cached:false) free-tier generation', async () => {
    const user = userEvent.setup()
    const freshResponse: InterviewPrepResponse = {
      questions: SAMPLE_QUESTIONS,
      cached: false,
      generated_at: new Date().toISOString(),
      model_used: 'gemini-2.5-pro',
    }
    generateInterviewPrep.mockResolvedValueOnce(freshResponse)

    renderInterview()
    await user.click(screen.getByRole('button', { name: /Generate Interview Questions/i }))

    await waitFor(() => expect(screen.getByTestId('free-usage-chip')).toBeInTheDocument())
    expect(screen.queryByTestId('cached-chip')).not.toBeInTheDocument()
  })

  it('passes forceRegenerate:true through the api layer when Regenerate is clicked', async () => {
    const user = userEvent.setup()
    // First call: serves a cached set so the Regenerate button renders.
    generateInterviewPrep.mockResolvedValueOnce({
      questions: SAMPLE_QUESTIONS,
      cached: true,
      generated_at: new Date().toISOString(),
      model_used: 'gemini-2.5-pro',
    } as InterviewPrepResponse)
    // Second call (regenerate): fresh.
    generateInterviewPrep.mockResolvedValueOnce({
      questions: SAMPLE_QUESTIONS,
      cached: false,
      generated_at: new Date().toISOString(),
      model_used: 'gemini-2.5-pro',
    } as InterviewPrepResponse)

    // Free-tier path triggers a confirm() — auto-accept it.
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderInterview()
    await user.click(screen.getByRole('button', { name: /Generate Interview Questions/i }))
    await waitFor(() => expect(screen.getByTestId('cached-chip')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Regenerate Questions/i }))

    await waitFor(() => expect(generateInterviewPrep).toHaveBeenCalledTimes(2))
    // First call: no force_regenerate; second call: forceRegenerate:true.
    expect(generateInterviewPrep.mock.calls[0][2]).toBeUndefined()
    expect(generateInterviewPrep.mock.calls[1][2]).toEqual({ forceRegenerate: true })
    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(capture).toHaveBeenCalledWith(
      'interview_questions_regenerated',
      expect.objectContaining({ from_free_tier: true }),
    )
  })
})
