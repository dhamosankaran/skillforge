import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { MissionDetailResponse } from '@/types'

const updatePersona = vi.fn()
const fetchActiveMission = vi.fn()
vi.mock('@/services/api', () => ({
  updatePersona: (...args: unknown[]) => updatePersona(...args),
  fetchActiveMission: (...args: unknown[]) => fetchActiveMission(...args),
}))

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
  updatePersona.mockReset()
  fetchActiveMission.mockReset()
  updateUser.mockReset()
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
  it('Mode 1 (no date) renders the inline date-setter form', () => {
    renderWidget(null)
    expect(screen.getByTestId('countdown-date-input')).toBeInTheDocument()
    expect(screen.getByTestId('countdown-save')).toBeDisabled()
  })

  it('Mode 1 submit calls updatePersona with persona + interview_target_date', async () => {
    updatePersona.mockResolvedValueOnce({ ...mockUser, interview_target_date: '2026-06-01' })
    const user = userEvent.setup()
    renderWidget(null)

    const input = screen.getByTestId('countdown-date-input') as HTMLInputElement
    await user.type(input, '2026-06-01')
    await user.click(screen.getByTestId('countdown-save'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    // AC-9 regression catch: persona MUST be in the PATCH body.
    expect(updatePersona).toHaveBeenCalledWith({
      persona: 'interview_prepper',
      interview_target_date: '2026-06-01',
    })
    expect(updateUser).toHaveBeenCalledTimes(1)
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
