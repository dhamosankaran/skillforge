/**
 * Spec #66 — Live loop-progress strip in AppShell.
 * Render gate, state-machine derivation, click navigation, analytics.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser, Persona } from '@/context/AuthContext'
import type { HomeStateResponse } from '@/types/homeState'
import type { LoopProgressResponse, ScoreHistoryResponse } from '@/types'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const fetchHomeState = vi.fn()
const fetchScoreHistory = vi.fn()
const fetchLoopProgress = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchHomeState: () => fetchHomeState(),
    fetchScoreHistory: (id: string) => fetchScoreHistory(id),
    fetchLoopProgress: (id: string) => fetchLoopProgress(id),
  }
})

let mockUser: AuthUser | null = null
vi.mock('@/context/AuthContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/AuthContext')>(
      '@/context/AuthContext',
    )
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      updateUser: vi.fn(),
    }),
  }
})

import { LoopProgressStrip } from '@/components/layout/LoopProgressStrip'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Tester',
    avatar_url: null,
    role: 'user',
    persona: 'interview_prepper',
    onboarding_completed: true,
    ...overrides,
  }
}

function homeStateFixture(
  overrides: Partial<HomeStateResponse['context']> = {},
): HomeStateResponse {
  return {
    persona: 'interview_prepper',
    states: [],
    context: {
      current_streak: 0,
      last_review_at: null,
      active_mission_id: null,
      mission_target_date: null,
      last_scan_date: null,
      plan: 'free',
      last_activity_at: null,
      next_interview: {
        date: '2026-06-01',
        company: 'Google',
        tracker_id: 't-1',
      },
      ...overrides,
    },
  }
}

function scoreHistoryFixture(
  overall_score = 71,
  rows = 1,
): ScoreHistoryResponse {
  return {
    tracker_application_id: 't-1',
    history: Array.from({ length: rows }).map((_, i) => ({
      id: `s-${i}`,
      scan_id: `scan-${i}`,
      overall_score,
      keyword_match_score: 60,
      skills_coverage_score: 65,
      formatting_compliance_score: 80,
      bullet_strength_score: 70,
      scanned_at: new Date(2026, 3, 1 + i).toISOString(),
    })),
    delta: null,
  }
}

function loopProgressFixture(
  overrides: Partial<LoopProgressResponse> = {},
): LoopProgressResponse {
  return {
    tracker_application_id: 't-1',
    total_gap_cards: 10,
    reviewed_gap_cards: 0,
    percent_reviewed: 0,
    days_since_last_scan: 1,
    ...overrides,
  }
}

function isoDaysFromNow(n: number): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

beforeEach(() => {
  capture.mockReset()
  mockNavigate.mockReset()
  fetchHomeState.mockReset()
  fetchScoreHistory.mockReset()
  fetchLoopProgress.mockReset()
  mockUser = userFixture()
  fetchHomeState.mockResolvedValue(homeStateFixture())
  fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(71, 1))
  fetchLoopProgress.mockResolvedValue(loopProgressFixture())
})

function renderStrip() {
  return render(
    <MemoryRouter initialEntries={['/home']}>
      <LoopProgressStrip />
    </MemoryRouter>,
  )
}

describe('LoopProgressStrip — render gates', () => {
  it('returns null when persona is not interview_prepper', async () => {
    mockUser = userFixture({ persona: 'career_climber' })
    const { container } = renderStrip()
    await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
    expect(
      container.querySelector('[data-testid="loop-progress-strip"]'),
    ).toBeNull()
  })

  it('returns null when next_interview is null', async () => {
    fetchHomeState.mockResolvedValue(homeStateFixture({ next_interview: null }))
    const { container } = renderStrip()
    await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
    expect(
      container.querySelector('[data-testid="loop-progress-strip"]'),
    ).toBeNull()
  })

  it('returns null when persona is null (defensive)', async () => {
    mockUser = userFixture({ persona: null as unknown as Persona })
    const { container } = renderStrip()
    await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
    expect(
      container.querySelector('[data-testid="loop-progress-strip"]'),
    ).toBeNull()
  })

  it('renders for interview_prepper with next_interview', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-progress-strip')).toBeInTheDocument(),
    )
  })
})

describe('LoopProgressStrip — step state derivation', () => {
  it('step 1 = future when no scan history', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(0, 0))
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-1')).toHaveAttribute(
        'data-state',
        'future',
      ),
    )
  })

  it('step 1 = done when score history has at least one row', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(71, 1))
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-1')).toHaveAttribute(
        'data-state',
        'done',
      ),
    )
  })

  it('step 2 = current when scan exists and percent_reviewed < 50', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(71, 1))
    fetchLoopProgress.mockResolvedValue(
      loopProgressFixture({
        total_gap_cards: 10,
        reviewed_gap_cards: 3,
        percent_reviewed: 30,
        days_since_last_scan: 1,
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-2')).toHaveAttribute(
        'data-state',
        'current',
      ),
    )
  })

  it('step 3 = current when step 2 done AND days_since_last_scan ≥ 3', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(71, 1))
    fetchLoopProgress.mockResolvedValue(
      loopProgressFixture({
        total_gap_cards: 10,
        reviewed_gap_cards: 6,
        percent_reviewed: 60,
        days_since_last_scan: 4,
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-3')).toHaveAttribute(
        'data-state',
        'current',
      ),
    )
  })

  it('step 3 = locked when days_since_last_scan < 3', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(71, 1))
    fetchLoopProgress.mockResolvedValue(
      loopProgressFixture({
        total_gap_cards: 10,
        reviewed_gap_cards: 6,
        percent_reviewed: 60,
        days_since_last_scan: 2,
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-3')).toHaveAttribute(
        'data-state',
        'locked',
      ),
    )
  })

  it('step 3 = done per D-1 heuristic (history.length ≥ 2 AND step 2 done)', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(75, 2))
    fetchLoopProgress.mockResolvedValue(
      loopProgressFixture({
        total_gap_cards: 10,
        reviewed_gap_cards: 8,
        percent_reviewed: 80,
        days_since_last_scan: 1,
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-3')).toHaveAttribute(
        'data-state',
        'done',
      ),
    )
  })

  it('step 4 = alert when interview is in the past', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(-2),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-4')).toHaveAttribute(
        'data-state',
        'alert',
      ),
    )
  })

  it('step 4 = current when interview is within 7 days', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(5),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-4')).toHaveAttribute(
        'data-state',
        'current',
      ),
    )
  })
})

describe('LoopProgressStrip — click + analytics', () => {
  it('step 3 click navigates to /prep/tracker rescan deep-link and fires loop_strip_step_clicked', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 'trk-abc',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(71, 1))
    fetchLoopProgress.mockResolvedValue(
      loopProgressFixture({
        total_gap_cards: 10,
        reviewed_gap_cards: 6,
        percent_reviewed: 60,
        days_since_last_scan: 4,
      }),
    )
    renderStrip()
    // Wait for state to settle — initial render shows step 3 'locked' until
    // useScoreHistory + useLoopProgress resolve. State change from locked
    // (<div>) to current (<button>) re-mounts the DOM node, so re-query
    // post-resolution rather than capturing a stale element handle.
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-3')).toHaveAttribute(
        'data-state',
        'current',
      ),
    )

    await userEvent.click(screen.getByTestId('loop-step-3'))

    expect(mockNavigate).toHaveBeenCalledWith(
      '/prep/tracker?focus=trk-abc&action=rescan',
    )
    const clickCall = capture.mock.calls.find(
      (c) => c[0] === 'loop_strip_step_clicked',
    )
    expect(clickCall).toBeDefined()
    expect(clickCall![1]).toMatchObject({ step: 3, plan: 'free' })
  })

  it('fires loop_strip_rendered exactly once on mount with persona + tracker_id', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    renderStrip()
    await waitFor(() => {
      const c = capture.mock.calls.filter((x) => x[0] === 'loop_strip_rendered')
      expect(c).toHaveLength(1)
      expect(c[0][1]).toMatchObject({
        persona: 'interview_prepper',
        tracker_id: 't-1',
      })
    })
  })

  it('does NOT fire loop_frame_rendered (suppressed for surface=appshell per D-4)', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-progress-strip')).toBeInTheDocument(),
    )
    const c = capture.mock.calls.find((x) => x[0] === 'loop_frame_rendered')
    expect(c).toBeUndefined()
  })

  it('D-14: useLoopProgress error keeps step 3 locked', async () => {
    fetchHomeState.mockResolvedValue(
      homeStateFixture({
        next_interview: {
          date: isoDaysFromNow(30),
          company: 'Google',
          tracker_id: 't-1',
        },
      }),
    )
    fetchScoreHistory.mockResolvedValue(scoreHistoryFixture(71, 1))
    fetchLoopProgress.mockRejectedValue(new Error('boom'))
    renderStrip()
    await waitFor(() =>
      expect(screen.getByTestId('loop-step-3')).toHaveAttribute(
        'data-state',
        'locked',
      ),
    )
  })
})
