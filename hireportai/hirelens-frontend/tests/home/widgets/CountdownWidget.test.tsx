import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { MissionDetailResponse } from '@/types'

const fetchActiveMission = vi.fn()
const updatePersona = vi.fn()
vi.mock('@/services/api', () => ({
  fetchActiveMission: (...args: unknown[]) => fetchActiveMission(...args),
  updatePersona: (...args: unknown[]) => updatePersona(...args),
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
  updatePersona.mockReset()
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

  // ── B-037: Mode 1 CTA opens an inline date modal instead of navigating ─
  // away to the new-user onboarding page. Spec #53 §Supersession.

  it('Mode 1 CTA click fires clicked event + opens the inline date modal (B-037)', async () => {
    const user = userEvent.setup()
    renderWidget(null)
    expect(screen.queryByTestId('interview-date-modal')).toBeNull()
    await user.click(screen.getByTestId('countdown-unlock-cta'))
    expect(capture).toHaveBeenCalledWith('countdown_unlock_cta_clicked', {
      surface: 'home_countdown',
    })
    expect(await screen.findByTestId('interview-date-modal')).toBeInTheDocument()
    // Regression guard: must NOT route through the onboarding PersonaPicker.
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringContaining('/onboarding/persona'),
    )
  })

  it('Mode 1 modal Save calls PATCH with persona + date + preserves existing company (B-037 / B-038 read-and-preserve)', async () => {
    mockUser = {
      ...mockUser,
      interview_target_company: 'JPMorgan',
      interview_target_date: null,
    }
    updatePersona.mockResolvedValueOnce({
      ...mockUser,
      interview_target_date: '2026-06-01',
    })
    const user = userEvent.setup()
    renderWidget(null)
    await user.click(screen.getByTestId('countdown-unlock-cta'))
    const input = await screen.findByTestId('interview-date-input')
    await user.type(input, '2026-06-01')
    await user.click(screen.getByTestId('interview-date-save'))
    await waitFor(() => {
      expect(updatePersona).toHaveBeenCalledWith({
        persona: 'interview_prepper',
        interview_target_date: '2026-06-01',
        interview_target_company: 'JPMorgan',
      })
    })
    expect(updateUser).toHaveBeenCalledWith(
      expect.objectContaining({ interview_target_date: '2026-06-01' }),
    )
    expect(capture).toHaveBeenCalledWith('interview_target_date_added', {
      source: 'persona_edit',
      surface: 'home_countdown',
    })
  })

  it('Mode 1 modal Save sends interview_target_company=null when user has none', async () => {
    mockUser = {
      ...mockUser,
      interview_target_company: null,
      interview_target_date: null,
    }
    updatePersona.mockResolvedValueOnce({
      ...mockUser,
      interview_target_date: '2026-06-01',
    })
    const user = userEvent.setup()
    renderWidget(null)
    await user.click(screen.getByTestId('countdown-unlock-cta'))
    await user.type(screen.getByTestId('interview-date-input'), '2026-06-01')
    await user.click(screen.getByTestId('interview-date-save'))
    await waitFor(() => {
      expect(updatePersona).toHaveBeenCalledWith({
        persona: 'interview_prepper',
        interview_target_date: '2026-06-01',
        interview_target_company: null,
      })
    })
  })

  it('Mode 1 modal Cancel closes without calling PATCH', async () => {
    const user = userEvent.setup()
    renderWidget(null)
    await user.click(screen.getByTestId('countdown-unlock-cta'))
    expect(await screen.findByTestId('interview-date-modal')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    await waitFor(() =>
      expect(screen.queryByTestId('interview-date-modal')).toBeNull(),
    )
    expect(updatePersona).not.toHaveBeenCalled()
    expect(updateUser).not.toHaveBeenCalled()
  })

  it('Mode 1 modal Save is disabled until a date is entered', async () => {
    const user = userEvent.setup()
    renderWidget(null)
    await user.click(screen.getByTestId('countdown-unlock-cta'))
    expect(await screen.findByTestId('interview-date-save')).toBeDisabled()
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
