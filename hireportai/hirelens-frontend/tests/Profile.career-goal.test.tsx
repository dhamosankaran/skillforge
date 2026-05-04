/**
 * Spec #67 §8.2 — Profile "Career goal" section.
 * AC-22: persona=CC, no current intent → "Set my goal →" CTA.
 * AC-23: persona=CC, has intent → "Edit" + "Clear" affordances.
 * AC-24: persona=interview_prepper → section does NOT render.
 * AC-25: Clear confirmed → DELETE /career-intent fires; section re-renders empty.
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

let mockUser: AuthUser = {
  id: 'u1',
  email: 't@example.com',
  name: 'Test',
  avatar_url: null,
  role: 'user',
  persona: 'career_climber',
  onboarding_completed: true,
}
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
    updateUser: vi.fn(),
    refreshUser: vi.fn(),
  }),
}))

const getCareerIntent = vi.fn()
const setCareerIntent = vi.fn()
const clearCareerIntent = vi.fn()
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({
      data: { total_reviewed: 0, by_state: {}, total_reps: 0, total_lapses: 0 },
    }),
  },
  createBillingPortalSession: vi.fn(),
  generateExperience: vi.fn(),
  getCareerIntent: (...args: unknown[]) => getCareerIntent(...args),
  setCareerIntent: (...args: unknown[]) => setCareerIntent(...args),
  clearCareerIntent: (...args: unknown[]) => clearCareerIntent(...args),
}))

vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: 'free', scansUsed: 0, maxScans: 3 },
    canScan: true,
    canUsePro: false,
    canUsePremium: false,
    incrementScan: vi.fn(),
    upgradePlan: vi.fn(),
    showUpgradeModal: false,
    setShowUpgradeModal: vi.fn(),
    checkAndPromptUpgrade: vi.fn(),
  }),
}))

vi.mock('@/context/GamificationContext', () => ({
  useGamification: () => ({
    stats: { current_streak: 0, longest_streak: 0, freezes_available: 0, total_xp: 0, badges: [] },
    isLoading: false,
    refresh: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/components/progress/SkillRadar', () => ({ SkillRadar: () => null }))
vi.mock('@/components/progress/ActivityHeatmap', () => ({ ActivityHeatmap: () => null }))
vi.mock('@/components/settings/EmailPreferences', () => ({ EmailPreferences: () => null }))
vi.mock('@/components/settings/ThemePicker', () => ({ ThemePicker: () => null }))
vi.mock('@/components/profile/XPBar', () => ({ XPBar: () => null }))
vi.mock('@/components/layout/PageWrapper', () => ({
  PageWrapper: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

import Profile from '@/pages/Profile'

function renderProfile() {
  return render(
    <MemoryRouter>
      <Profile />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  getCareerIntent.mockReset()
  setCareerIntent.mockReset()
  clearCareerIntent.mockReset()
  navigate.mockReset()
  mockUser = {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
  }
  // Pin system time so quarter dropdown options are deterministic.
  vi.setSystemTime(new Date('2026-05-04T12:00:00Z'))
})

afterEach(() => {
  vi.useRealTimers()
})

describe('Profile — Career-goal section (spec #67 §8.2)', () => {
  it('AC-24: does NOT render for interview_prepper persona', async () => {
    mockUser.persona = 'interview_prepper'
    getCareerIntent.mockResolvedValueOnce(null)
    renderProfile()
    expect(screen.queryByTestId('career-goal-section')).not.toBeInTheDocument()
    expect(getCareerIntent).not.toHaveBeenCalled()
  })

  it('AC-22: renders "Set my goal →" CTA when CC user has no current intent', async () => {
    getCareerIntent.mockResolvedValueOnce(null)
    renderProfile()
    expect(screen.getByTestId('career-goal-section')).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByTestId('career-goal-set')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('career-goal-edit')).not.toBeInTheDocument()
  })

  it('AC-23: renders "Targeting … Edit + Clear" when CC user has current intent', async () => {
    getCareerIntent.mockResolvedValueOnce({
      id: 'intent-1',
      user_id: 'u1',
      target_role: 'staff',
      target_quarter: '2099-Q1',
      created_at: '2026-05-04T00:00:00Z',
      superseded_at: null,
    })
    renderProfile()
    await waitFor(() =>
      expect(screen.getByTestId('career-goal-edit')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('career-goal-clear')).toBeInTheDocument()
    expect(screen.getByTestId('career-goal-section')).toHaveTextContent('Staff Engineer')
    expect(screen.getByTestId('career-goal-section')).toHaveTextContent('2099 Q1')
  })

  it('Edit form saves via setCareerIntent and fires career_intent_updated', async () => {
    const user = userEvent.setup()
    getCareerIntent.mockResolvedValueOnce({
      id: 'intent-1',
      user_id: 'u1',
      target_role: 'staff',
      target_quarter: '2099-Q1',
      created_at: '2026-05-04T00:00:00Z',
      superseded_at: null,
    })
    setCareerIntent.mockResolvedValueOnce({
      id: 'intent-2',
      user_id: 'u1',
      target_role: 'principal',
      target_quarter: '2027-Q2',
      created_at: '2026-05-04T00:00:00Z',
      superseded_at: null,
    })

    renderProfile()
    await waitFor(() =>
      expect(screen.getByTestId('career-goal-edit')).toBeInTheDocument(),
    )
    await user.click(screen.getByTestId('career-goal-edit'))

    await user.selectOptions(screen.getByTestId('career-goal-role-input'), 'principal')
    await user.selectOptions(screen.getByTestId('career-goal-quarter-input'), '2027-Q2')
    await user.click(screen.getByTestId('career-goal-save'))

    await waitFor(() => expect(setCareerIntent).toHaveBeenCalledTimes(1))
    expect(setCareerIntent).toHaveBeenCalledWith(
      { target_role: 'principal', target_quarter: '2027-Q2' },
      'profile_edit',
    )
    expect(capture).toHaveBeenCalledWith('career_intent_updated', {
      target_role: 'principal',
      target_quarter: '2027-Q2',
      source: 'profile_edit',
    })
  })

  it('AC-25: Clear (after window.confirm) calls clearCareerIntent and re-renders empty', async () => {
    const user = userEvent.setup()
    getCareerIntent.mockResolvedValueOnce({
      id: 'intent-1',
      user_id: 'u1',
      target_role: 'staff',
      target_quarter: '2099-Q1',
      created_at: '2026-05-04T00:00:00Z',
      superseded_at: null,
    })
    clearCareerIntent.mockResolvedValueOnce(undefined)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderProfile()
    await waitFor(() =>
      expect(screen.getByTestId('career-goal-clear')).toBeInTheDocument(),
    )
    await user.click(screen.getByTestId('career-goal-clear'))

    await waitFor(() => expect(clearCareerIntent).toHaveBeenCalledTimes(1))
    expect(capture).toHaveBeenCalledWith(
      'career_intent_updated',
      expect.objectContaining({ cleared: true, source: 'profile_edit' }),
    )
    await waitFor(() =>
      expect(screen.getByTestId('career-goal-set')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('career-goal-edit')).not.toBeInTheDocument()

    confirmSpy.mockRestore()
  })
})
