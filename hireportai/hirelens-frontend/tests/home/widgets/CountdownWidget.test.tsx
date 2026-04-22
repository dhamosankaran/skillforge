import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { MissionDetailResponse } from '@/types'

const fetchActiveMission = vi.fn()
vi.mock('@/services/api', () => ({
  fetchActiveMission: (...args: unknown[]) => fetchActiveMission(...args),
}))

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

const updateUser = vi.fn()
let mockUser: AuthUser = {
  id: 'u1',
  email: 't@example.com',
  name: 'Test',
  avatar_url: null,
  role: 'user',
  persona: 'interview_prepper',
  onboarding_completed: true,
}

vi.mock('@/context/AuthContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/AuthContext')>('@/context/AuthContext')
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      updateUser,
    }),
  }
})

// Countdown component is visual — stub so we can assert Mode 2 renders it.
vi.mock('@/components/mission/Countdown', () => ({
  Countdown: ({ daysRemaining }: { daysRemaining: number }) => (
    <div data-testid="countdown-view">{daysRemaining} days</div>
  ),
}))

import { CountdownWidget } from '@/components/home/widgets/CountdownWidget'

function renderWidget(date: string | null | undefined) {
  return render(
    <MemoryRouter>
      <CountdownWidget persona="interview_prepper" date={date} />
    </MemoryRouter>,
  )
}

function mission(
  overrides: Partial<MissionDetailResponse> = {},
): MissionDetailResponse {
  return {
    id: 'm1',
    title: 'Google',
    target_date: '2026-06-01',
    category_ids: [],
    daily_target: 5,
    total_cards: 50,
    days_remaining: 10,
    status: 'active',
    progress_pct: 20,
    created_at: '2026-04-01T00:00:00Z',
    days: [],
    ...overrides,
  }
}

beforeEach(() => {
  fetchActiveMission.mockReset()
  updateUser.mockReset()
  capture.mockReset()
  navigate.mockReset()
  mockUser = {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: 'interview_prepper',
    onboarding_completed: true,
  }
})

describe('CountdownWidget', () => {
  // ── Spec #53 / B-018 Mode 1 reframe: link-only unlock affordance ────────

  it('Mode 1 (no date) renders the LD-3 unlock copy and CTA button (AC-3)', () => {
    renderWidget(null)
    expect(
      screen.getByText(/add an interview date to unlock countdown/i),
    ).toBeInTheDocument()
    expect(screen.getByTestId('countdown-unlock-cta')).toBeInTheDocument()
    // Regression guard: no inline date-setter (OD-2 — dropped).
    expect(screen.queryByTestId('countdown-date-input')).toBeNull()
    expect(screen.queryByTestId('countdown-save')).toBeNull()
  })

  it('Mode 1 fires countdown_unlock_cta_shown once on mount (home_countdown surface)', async () => {
    renderWidget(null)
    await waitFor(() =>
      expect(capture).toHaveBeenCalledWith('countdown_unlock_cta_shown', {
        surface: 'home_countdown',
      }),
    )
    // Idempotent via ref — single fire only, even with Strict-Mode-like
    // re-invocation on the same mount.
    const shownCalls = capture.mock.calls.filter(
      (c) => c[0] === 'countdown_unlock_cta_shown',
    )
    expect(shownCalls).toHaveLength(1)
  })

  it('Mode 1 CTA click fires clicked event + navigates to PersonaPicker with return_to=/home', async () => {
    const user = userEvent.setup()
    renderWidget(null)
    await user.click(screen.getByTestId('countdown-unlock-cta'))
    expect(capture).toHaveBeenCalledWith('countdown_unlock_cta_clicked', {
      surface: 'home_countdown',
    })
    expect(navigate).toHaveBeenCalledWith('/onboarding/persona?return_to=%2Fhome')
  })

  it('Mode 2 (date set) renders the Countdown component', async () => {
    fetchActiveMission.mockResolvedValueOnce(mission())
    // Pick a date in the future relative to test execution.
    const future = new Date()
    future.setDate(future.getDate() + 14)
    const iso = future.toISOString().slice(0, 10)
    renderWidget(iso)
    expect(await screen.findByTestId('countdown-view')).toBeInTheDocument()
  })

  it('Mode 2 with no active mission shows "Start a Mission sprint" CTA', async () => {
    fetchActiveMission.mockRejectedValueOnce(new Error('no mission'))
    const future = new Date()
    future.setDate(future.getDate() + 14)
    const iso = future.toISOString().slice(0, 10)
    renderWidget(iso)
    expect(
      await screen.findByRole('link', { name: /start a mission sprint/i }),
    ).toHaveAttribute('href', '/learn/mission')
  })

  it('Mode 2 with active mission shows "View mission" CTA', async () => {
    fetchActiveMission.mockResolvedValueOnce(mission({ status: 'active' }))
    const future = new Date()
    future.setDate(future.getDate() + 14)
    const iso = future.toISOString().slice(0, 10)
    renderWidget(iso)
    expect(
      await screen.findByRole('link', { name: /view mission/i }),
    ).toHaveAttribute('href', '/learn/mission')
  })
})
