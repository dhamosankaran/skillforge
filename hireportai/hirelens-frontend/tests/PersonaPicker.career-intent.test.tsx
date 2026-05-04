/**
 * Spec #67 §8.1 — PersonaPicker CC career-intent capture extension.
 * AC-19: filled → updatePersona + setCareerIntent + career_intent_captured.
 * AC-20: blank  → updatePersona only.
 * AC-21: setCareerIntent failure → persona stays committed, navigation proceeds.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const updatePersona = vi.fn()
const setCareerIntent = vi.fn()
vi.mock('@/services/api', () => ({
  updatePersona: (...args: unknown[]) => updatePersona(...args),
  setCareerIntent: (...args: unknown[]) => setCareerIntent(...args),
}))

const toastError = vi.fn()
vi.mock('react-hot-toast', () => ({
  default: { error: (...args: unknown[]) => toastError(...args) },
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
      refreshUser: vi.fn(),
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
  setCareerIntent.mockReset()
  toastError.mockReset()
  updateUser.mockReset()
  navigate.mockReset()
  mockUser = userFixture()
  window.localStorage.clear()
  // Pin system time so quarter options are deterministic.
  // 2026-05-04 → current quarter = 2026-Q2; future options include 2027-Q1.
  vi.setSystemTime(new Date('2026-05-04T12:00:00Z'))
})

afterEach(() => {
  vi.useRealTimers()
})

function renderPicker() {
  return render(
    <MemoryRouter initialEntries={['/onboarding/persona']}>
      <PersonaPicker />
    </MemoryRouter>,
  )
}

describe('PersonaPicker — CC career-intent (spec #67 §8.1)', () => {
  it('auto-expands the CC card with target_role + target_quarter selects on select (D-1)', async () => {
    const user = userEvent.setup()
    renderPicker()
    expect(screen.queryByTestId('cc-target-role-input')).not.toBeInTheDocument()
    expect(screen.queryByTestId('cc-target-quarter-input')).not.toBeInTheDocument()

    await user.click(screen.getByTestId('persona-card-career_climber'))

    expect(screen.getByTestId('cc-target-role-input')).toBeInTheDocument()
    expect(screen.getByTestId('cc-target-quarter-input')).toBeInTheDocument()
  })

  it('AC-20: blank CC fields → updatePersona only, no setCareerIntent', async () => {
    const user = userEvent.setup()
    updatePersona.mockResolvedValueOnce(
      userFixture({ persona: 'career_climber', onboarding_completed: true }),
    )

    renderPicker()
    await user.click(screen.getByTestId('persona-card-career_climber'))
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    expect(setCareerIntent).not.toHaveBeenCalled()
    expect(capture).not.toHaveBeenCalledWith(
      'career_intent_captured',
      expect.anything(),
    )
  })

  it('AC-19: both CC fields filled → updatePersona then setCareerIntent + career_intent_captured', async () => {
    const user = userEvent.setup()
    updatePersona.mockResolvedValueOnce(
      userFixture({ persona: 'career_climber', onboarding_completed: true }),
    )
    setCareerIntent.mockResolvedValueOnce({
      id: 'intent-1',
      user_id: 'u1',
      target_role: 'staff',
      target_quarter: '2027-Q1',
      created_at: '2026-05-04T00:00:00Z',
      superseded_at: null,
    })

    renderPicker()
    await user.click(screen.getByTestId('persona-card-career_climber'))
    await user.selectOptions(screen.getByTestId('cc-target-role-input'), 'staff')
    await user.selectOptions(screen.getByTestId('cc-target-quarter-input'), '2027-Q1')
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(setCareerIntent).toHaveBeenCalledTimes(1))
    expect(setCareerIntent).toHaveBeenCalledWith(
      { target_role: 'staff', target_quarter: '2027-Q1' },
      'persona_picker',
    )
    expect(capture).toHaveBeenCalledWith('career_intent_captured', {
      target_role: 'staff',
      target_quarter: '2027-Q1',
      source: 'persona_picker',
    })
    // Navigation still proceeds.
    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith('/first-action', { replace: true }),
    )
  })

  it('partial fill (role only) → no setCareerIntent (BE requires both)', async () => {
    const user = userEvent.setup()
    updatePersona.mockResolvedValueOnce(
      userFixture({ persona: 'career_climber', onboarding_completed: true }),
    )

    renderPicker()
    await user.click(screen.getByTestId('persona-card-career_climber'))
    await user.selectOptions(screen.getByTestId('cc-target-role-input'), 'principal')
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(updatePersona).toHaveBeenCalledTimes(1))
    expect(setCareerIntent).not.toHaveBeenCalled()
  })

  it('AC-21: setCareerIntent failure → persona stays committed, toast fires, navigation proceeds', async () => {
    const user = userEvent.setup()
    updatePersona.mockResolvedValueOnce(
      userFixture({ persona: 'career_climber', onboarding_completed: true }),
    )
    setCareerIntent.mockRejectedValueOnce(new Error('500'))

    renderPicker()
    await user.click(screen.getByTestId('persona-card-career_climber'))
    await user.selectOptions(screen.getByTestId('cc-target-role-input'), 'em')
    await user.selectOptions(screen.getByTestId('cc-target-quarter-input'), '2027-Q1')
    await user.click(screen.getByTestId('persona-continue'))

    await waitFor(() => expect(setCareerIntent).toHaveBeenCalledTimes(1))
    await waitFor(() =>
      expect(toastError).toHaveBeenCalledWith('Goal not saved — set it from Profile.'),
    )
    expect(updateUser).toHaveBeenCalled()
    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith('/first-action', { replace: true }),
    )
    // career_intent_captured did NOT fire.
    expect(capture).not.toHaveBeenCalledWith(
      'career_intent_captured',
      expect.anything(),
    )
  })
})
