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

function renderPicker(initialPath = '/onboarding/persona') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
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

  // ── Spec #53 / B-018 — optional fields + return_to + telemetry ──────────

  it('saves interview_prepper with neither date nor company (AC-1)', async () => {
    const user = userEvent.setup()
    const apiResponse: AuthUser = userFixture({
      persona: 'interview_prepper',
      onboarding_completed: true,
    })
    updatePersona.mockResolvedValueOnce(apiResponse)

    renderPicker()
    await user.click(screen.getByTestId('persona-card-interview_prepper'))
    // Both expansion inputs are untouched — still empty.
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    // Body MUST NOT contain interview_target_date / interview_target_company
    // keys when they were left blank (PersonaPicker strips them at submit).
    expect(updatePersona).toHaveBeenCalledWith({ persona: 'interview_prepper' })
    // Skip signal fires; add signal does not.
    expect(capture).toHaveBeenCalledWith('interview_target_date_skipped', {
      source: 'onboarding',
    })
    expect(capture).not.toHaveBeenCalledWith(
      'interview_target_date_added',
      expect.anything(),
    )
  })

  it('date input type is "date" (AC-2 non-regression guard)', async () => {
    const user = userEvent.setup()
    renderPicker()
    await user.click(screen.getByTestId('persona-card-interview_prepper'))
    const dateInput = screen.getByTestId('interview-target-date-input')
    expect(dateInput.getAttribute('type')).toBe('date')
  })

  it('fires interview_target_date_added(source=onboarding) when a date is saved at onboarding', async () => {
    const user = userEvent.setup()
    const apiResponse: AuthUser = userFixture({
      persona: 'interview_prepper',
      onboarding_completed: true,
    })
    updatePersona.mockResolvedValueOnce(apiResponse)

    renderPicker()
    await user.click(screen.getByTestId('persona-card-interview_prepper'))
    await user.type(screen.getByTestId('interview-target-date-input'), '2026-06-01')
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    expect(capture).toHaveBeenCalledWith('interview_target_date_added', {
      source: 'onboarding',
    })
    expect(capture).not.toHaveBeenCalledWith(
      'interview_target_date_skipped',
      expect.anything(),
    )
  })

  it('return_to on whitelist: navigates to origin and fires date_added(source=persona_edit)', async () => {
    const user = userEvent.setup()
    // Pre-existing interview_prepper returning via the unlock CTA.
    mockUser = userFixture({ persona: 'interview_prepper' })
    const apiResponse: AuthUser = userFixture({
      persona: 'interview_prepper',
      onboarding_completed: true,
    })
    updatePersona.mockResolvedValueOnce(apiResponse)

    renderPicker('/onboarding/persona?return_to=/learn/mission')
    // Expansion block should be open automatically (selected pre-filled).
    await user.type(screen.getByTestId('interview-target-date-input'), '2026-06-01')
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith('/learn/mission', { replace: true }),
    )
    expect(navigate).not.toHaveBeenCalledWith('/home', expect.anything())
    expect(navigate).not.toHaveBeenCalledWith('/first-action', expect.anything())
    expect(capture).toHaveBeenCalledWith('interview_target_date_added', {
      source: 'persona_edit',
    })
  })

  it('return_to NOT on whitelist: falls back to default routing (open-redirect guard)', async () => {
    const user = userEvent.setup()
    const apiResponse: AuthUser = userFixture({
      persona: 'career_climber',
      onboarding_completed: true,
    })
    updatePersona.mockResolvedValueOnce(apiResponse)
    window.localStorage.setItem('first_action_seen', 'true')

    renderPicker('/onboarding/persona?return_to=https://evil.example.com')
    await user.click(screen.getByTestId('persona-card-career_climber'))
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    // Falls back to /home (since first_action_seen is set). Never to the
    // untrusted return_to value.
    expect(navigate).toHaveBeenCalledWith('/home', { replace: true })
    expect(navigate).not.toHaveBeenCalledWith(
      'https://evil.example.com',
      expect.anything(),
    )
  })
})
