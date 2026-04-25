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
let mockInterviewPrepsUsed = 0
let mockInterviewPrepsMax = 3
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: {
      plan: mockPlan,
      scansUsed: 0,
      maxScans: mockPlan === 'free' ? 3 : Infinity,
      interviewPrepsUsed: mockInterviewPrepsUsed,
      interviewPrepsRemaining:
        mockInterviewPrepsMax === -1
          ? -1
          : Math.max(0, mockInterviewPrepsMax - mockInterviewPrepsUsed),
      interviewPrepsMax: mockInterviewPrepsMax,
    },
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
  mockInterviewPrepsUsed = 0
  mockInterviewPrepsMax = 3
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

    // window.confirm was dropped — pre-flight gate makes it redundant.
    // If it ever resurfaces, this spy's call count will catch it.
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderInterview()
    await user.click(screen.getByRole('button', { name: /Generate Interview Questions/i }))
    await waitFor(() => expect(screen.getByTestId('cached-chip')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Regenerate Questions/i }))

    await waitFor(() => expect(generateInterviewPrep).toHaveBeenCalledTimes(2))
    // First call: no force_regenerate; second call: forceRegenerate:true.
    expect(generateInterviewPrep.mock.calls[0][2]).toBeUndefined()
    expect(generateInterviewPrep.mock.calls[1][2]).toEqual({ forceRegenerate: true })
    expect(confirmSpy).not.toHaveBeenCalled()
    expect(capture).toHaveBeenCalledWith(
      'interview_questions_regenerated',
      expect.objectContaining({ from_free_tier: true }),
    )
  })
})

describe('Interview page — pre-flight free-tier gate', () => {
  it('hides Generate and renders the limit-reached banner + upgrade CTA when free user is at cap', () => {
    mockPlan = 'free'
    mockInterviewPrepsUsed = 3
    mockInterviewPrepsMax = 3

    renderInterview()

    // Pre-flight: Generate button is not mounted; banner + Upgrade CTA are.
    expect(
      screen.queryByRole('button', { name: /Generate Interview Questions/i }),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/Free limit reached/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Upgrade to Pro/i })).toBeInTheDocument()
    expect(generateInterviewPrep).not.toHaveBeenCalled()
  })

  it('keeps Generate enabled for free user with quota remaining (no banner pre-click)', () => {
    mockPlan = 'free'
    mockInterviewPrepsUsed = 1
    mockInterviewPrepsMax = 3

    renderInterview()

    const btn = screen.getByRole('button', { name: /Generate Interview Questions/i })
    expect(btn).not.toBeDisabled()
    expect(screen.queryByText(/Free limit reached/i)).not.toBeInTheDocument()
  })

  it('keeps Generate enabled for Pro regardless of interviewPrepsUsed (-1 sentinel)', () => {
    mockPlan = 'pro'
    mockInterviewPrepsUsed = 99
    mockInterviewPrepsMax = -1

    renderInterview()

    const btn = screen.getByRole('button', { name: /Generate Interview Questions/i })
    expect(btn).not.toBeDisabled()
    expect(screen.queryByText(/Free limit reached/i)).not.toBeInTheDocument()
  })

  it('renders the softened "Using your latest resume…" copy when context is present', () => {
    mockPlan = 'pro'
    mockInterviewPrepsUsed = 0
    mockInterviewPrepsMax = -1

    renderInterview()

    expect(
      screen.getByText(/Using your latest resume and job role \+ skills from your last analysis\./i),
    ).toBeInTheDocument()
  })
})
