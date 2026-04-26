import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// Spec #63 / B-059 — pre-flight daily-review wall gate on /learn/daily.

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const mockFetchDailyQueue = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchDailyQueue: (...args: unknown[]) => mockFetchDailyQueue(...args),
  }
})

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

// Configurable UsageContext — drives the 3-clause gate (plan + isAdmin).
const usageState = {
  plan: 'free' as 'free' | 'pro' | 'enterprise',
  isAdmin: false,
}
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: {
      plan: usageState.plan,
      scansUsed: 0,
      maxScans: 1,
      isAdmin: usageState.isAdmin,
    },
    canScan: true,
    canUsePro: usageState.plan !== 'free',
    canUsePremium: usageState.plan !== 'free',
    refreshUsage: vi.fn(),
    upgradePlan: vi.fn(),
    showUpgradeModal: false,
    setShowUpgradeModal: vi.fn(),
    checkAndPromptUpgrade: vi.fn(),
  }),
  UsageProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('@/context/GamificationContext', () => ({
  useGamification: () => ({
    stats: null,
    refresh: vi.fn(),
  }),
  GamificationProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import DailyReview from '@/pages/DailyReview'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/learn/daily']}>
      <DailyReview />
    </MemoryRouter>,
  )
}

function walledQueuePayload(resetsAt: string) {
  return {
    cards: [],
    total_due: 0,
    session_id: 's1',
    completed_today: false,
    daily_status: {
      cards_consumed: 10,
      cards_limit: 10,
      can_review: false,
      resets_at: resetsAt,
    },
  }
}

function freshQueuePayload() {
  return {
    cards: [
      {
        card_id: 'c1',
        question: 'Q?',
        answer: 'A.',
        difficulty: 'easy' as const,
        tags: [],
        category_id: 'cat1',
        category_name: 'Cat',
        fsrs_state: 'new' as const,
        due_date: null,
        reps: 0,
        lapses: 0,
      },
    ],
    total_due: 1,
    session_id: 's1',
    completed_today: false,
    daily_status: {
      cards_consumed: 0,
      cards_limit: 10,
      can_review: true,
      resets_at: new Date(Date.now() + 6 * 3600_000).toISOString(),
    },
  }
}

function unlimitedQueuePayload() {
  return {
    cards: [
      {
        card_id: 'c1',
        question: 'Q?',
        answer: 'A.',
        difficulty: 'easy' as const,
        tags: [],
        category_id: 'cat1',
        category_name: 'Cat',
        fsrs_state: 'new' as const,
        due_date: null,
        reps: 0,
        lapses: 0,
      },
    ],
    total_due: 1,
    session_id: 's1',
    completed_today: false,
    daily_status: {
      cards_consumed: 0,
      cards_limit: -1,
      can_review: true,
      resets_at: new Date(Date.now() + 6 * 3600_000).toISOString(),
    },
  }
}

describe('DailyReview pre-flight gate (spec #63 / B-059)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usageState.plan = 'free'
    usageState.isAdmin = false
  })

  // AC-1
  it('walled free user sees the upsell view and no card UI', async () => {
    const resets = new Date(Date.now() + 6 * 3600_000).toISOString()
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(resets))

    renderPage()

    expect(
      await screen.findByTestId('daily-review-walled-view'),
    ).toBeInTheDocument()
    expect(screen.getByText("You've used today's free reviews")).toBeInTheDocument()
    // No card UI
    expect(screen.queryByText(/All caught up/i)).not.toBeInTheDocument()
    // Single fetch — no retry loop
    expect(mockFetchDailyQueue).toHaveBeenCalledTimes(1)
  })

  // AC-2
  it('free user under cap sees normal review UI (regression)', async () => {
    mockFetchDailyQueue.mockResolvedValue(freshQueuePayload())
    renderPage()

    // Walled view does NOT render and the queue progresses out of the
    // loading skeleton phase. The progress chip "1 of 1" is the cheapest
    // observable that proves the reviewing phase rendered.
    await waitFor(() => {
      expect(screen.getByText(/1 of 1/i)).toBeInTheDocument()
    })
    expect(screen.queryByTestId('daily-review-walled-view')).not.toBeInTheDocument()
  })

  // AC-3
  it('Pro user always sees normal review UI', async () => {
    usageState.plan = 'pro'
    // Even if BE somehow returned can_review=false (clock skew, plan-transition race),
    // the FE 3-clause gate plan-checks first.
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(new Date().toISOString()))
    renderPage()

    await waitFor(() => {
      expect(mockFetchDailyQueue).toHaveBeenCalled()
    })
    expect(screen.queryByTestId('daily-review-walled-view')).not.toBeInTheDocument()
  })

  // AC-4
  it('admin user always sees normal review UI', async () => {
    usageState.plan = 'free'
    usageState.isAdmin = true
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(new Date().toISOString()))
    renderPage()

    await waitFor(() => {
      expect(mockFetchDailyQueue).toHaveBeenCalled()
    })
    expect(screen.queryByTestId('daily-review-walled-view')).not.toBeInTheDocument()
  })

  // AC-5
  it('fires daily_card_wall_hit exactly once on walled mount with surface=daily_review_page_load', async () => {
    const resets = new Date(Date.now() + 6 * 3600_000).toISOString()
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(resets))

    renderPage()
    await screen.findByTestId('daily-review-walled-view')

    const wallHits = capture.mock.calls.filter(
      (c) => c[0] === 'daily_card_wall_hit',
    )
    expect(wallHits).toHaveLength(1)
    const [, props] = wallHits[0]
    expect(props.surface).toBe('daily_review_page_load')
    expect(typeof props.resets_at_hours_from_now).toBe('number')
  })

  // AC-7
  it('Upgrade-to-Pro CTA navigates to /pricing', async () => {
    const resets = new Date(Date.now() + 6 * 3600_000).toISOString()
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(resets))
    renderPage()

    const upgrade = await screen.findByTestId('daily-review-walled-view-upgrade-cta')
    await userEvent.click(upgrade)
    expect(mockNavigate).toHaveBeenCalledWith('/pricing')
  })

  // AC-8
  it('Back-to-home CTA links to /home', async () => {
    const resets = new Date(Date.now() + 6 * 3600_000).toISOString()
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(resets))
    renderPage()

    const home = await screen.findByTestId('daily-review-walled-view-home-cta')
    expect(home).toHaveAttribute('href', '/home')
  })

  // AC-9a
  it('formatResetsAt renders relative format for ≤12h remaining', async () => {
    const resets = new Date(Date.now() + 4 * 3600_000 + 17 * 60_000).toISOString()
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(resets))
    renderPage()

    const subhead = await screen.findByTestId('daily-review-walled-view-resets-at')
    expect(subhead.textContent || '').toMatch(/^Resets in \d+h \d+m$/)
  })

  // AC-9b
  it('formatResetsAt renders absolute format for >12h remaining', async () => {
    const resets = new Date(Date.now() + 18 * 3600_000).toISOString()
    mockFetchDailyQueue.mockResolvedValue(walledQueuePayload(resets))
    renderPage()

    const subhead = await screen.findByTestId('daily-review-walled-view-resets-at')
    expect(subhead.textContent || '').toMatch(/^Resets at /)
  })

  // Defense-in-depth — Pro response with cards_limit=-1 also renders normally.
  it('Pro response (unlimited sentinel) renders normal review UI', async () => {
    usageState.plan = 'pro'
    mockFetchDailyQueue.mockResolvedValue(unlimitedQueuePayload())
    renderPage()
    await waitFor(() => {
      expect(screen.queryByTestId('daily-review-walled-view')).not.toBeInTheDocument()
    })
  })
})
