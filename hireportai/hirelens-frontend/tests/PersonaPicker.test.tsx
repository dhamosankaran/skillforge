import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const updatePersona = vi.fn()
vi.mock('@/services/api', () => ({
  updatePersona: (...args: unknown[]) => updatePersona(...args),
}))

const updateUser = vi.fn()
let mockUser: AuthUser | null = null
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

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

import PersonaPicker from '@/pages/PersonaPicker'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: null,
    onboarding_completed: false,
    ...overrides,
  }
}

beforeEach(() => {
  capture.mockReset()
  updatePersona.mockReset()
  updateUser.mockReset()
  navigate.mockReset()
  mockUser = userFixture()
  window.localStorage.clear()
})

function renderPicker() {
  return render(
    <MemoryRouter initialEntries={['/onboarding/persona']}>
      <PersonaPicker />
    </MemoryRouter>,
  )
}

describe('PersonaPicker', () => {
  it('renders one card per PRD persona (three cards)', () => {
    renderPicker()
    expect(screen.getByTestId('persona-card-interview_prepper')).toBeInTheDocument()
    expect(screen.getByTestId('persona-card-career_climber')).toBeInTheDocument()
    expect(screen.getByTestId('persona-card-team_lead')).toBeInTheDocument()
  })

  it('disables Continue on mount', () => {
    renderPicker()
    expect(screen.getByTestId('persona-continue')).toBeDisabled()
  })

  it('enables Continue after selecting a card', async () => {
    const user = userEvent.setup()
    renderPicker()
    await user.click(screen.getByTestId('persona-card-career_climber'))
    expect(screen.getByTestId('persona-continue')).toBeEnabled()
  })

  it('reveals date + company inputs when Interview-Prepper is selected', async () => {
    const user = userEvent.setup()
    renderPicker()
    await user.click(screen.getByTestId('persona-card-interview_prepper'))
    expect(screen.getByTestId('interview-target-date-input')).toBeInTheDocument()
    expect(screen.getByTestId('interview-target-company-input')).toBeInTheDocument()
  })

  it('does not reveal interview inputs for Career-Climber or Team Lead', async () => {
    const user = userEvent.setup()
    renderPicker()
    await user.click(screen.getByTestId('persona-card-career_climber'))
    expect(screen.queryByTestId('interview-target-date-input')).not.toBeInTheDocument()
    expect(screen.queryByTestId('interview-target-company-input')).not.toBeInTheDocument()

    await user.click(screen.getByTestId('persona-card-team_lead'))
    expect(screen.queryByTestId('interview-target-date-input')).not.toBeInTheDocument()
    expect(screen.queryByTestId('interview-target-company-input')).not.toBeInTheDocument()
  })

  it('submits selected persona and navigates to /first-action when the seen flag is absent', async () => {
    const user = userEvent.setup()
    const apiResponse: AuthUser = userFixture({
      persona: 'career_climber',
      onboarding_completed: true,
    })
    updatePersona.mockResolvedValueOnce(apiResponse)

    renderPicker()
    await user.click(screen.getByTestId('persona-card-career_climber'))
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    expect(updatePersona).toHaveBeenCalledWith({ persona: 'career_climber' })
    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith('/first-action', { replace: true }),
    )
    expect(updateUser).toHaveBeenCalledWith(apiResponse)
    expect(capture).toHaveBeenCalledWith('persona_picker_shown', { is_new_user: true })
    expect(capture).toHaveBeenCalledWith('persona_selected', {
      persona: 'career_climber',
      has_target_date: false,
      has_target_company: false,
    })
  })

  it('navigates straight to /home when first_action_seen is already set (persona-switch path)', async () => {
    const user = userEvent.setup()
    const apiResponse: AuthUser = userFixture({
      persona: 'team_lead',
      onboarding_completed: true,
    })
    updatePersona.mockResolvedValueOnce(apiResponse)
    window.localStorage.setItem('first_action_seen', 'true')

    renderPicker()
    await user.click(screen.getByTestId('persona-card-team_lead'))
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith('/home', { replace: true }),
    )
    expect(navigate).not.toHaveBeenCalledWith('/first-action', expect.anything())
  })
})
