/**
 * Profile — Account section tests (B-028).
 *
 * Covers the "Sign out" affordance added to the Profile page so mobile
 * users (who don't see the desktop-only TopNav UserMenu) can still log
 * out via MobileNav → Profile → Sign out.
 */
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

const signOut = vi.fn()
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
  useAuth: () => ({ user: mockUser, isLoading: false, signIn: vi.fn(), signOut, updateUser: vi.fn(), refreshUser: vi.fn() }),
}))

vi.mock('@/services/api', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: { total_reviewed: 0, by_state: {}, total_reps: 0, total_lapses: 0 } }) },
  createBillingPortalSession: vi.fn(),
  generateExperience: vi.fn(),
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
vi.mock('@/components/profile/CareerGoalSection', () => ({ CareerGoalSection: () => null }))
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
  signOut.mockReset()
  signOut.mockResolvedValue(undefined)
  navigate.mockReset()
})

describe('Profile — Account section (B-028)', () => {
  it('renders the Sign out button inside the Account section', () => {
    renderProfile()
    const section = screen.getByTestId('account-section')
    expect(section).toHaveTextContent('Sign out')
    expect(screen.getByTestId('profile-signout')).toBeInTheDocument()
  })

  it('calls signOut and fires sign_out_clicked analytics on click', async () => {
    renderProfile()
    await userEvent.click(screen.getByTestId('profile-signout'))
    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1))
    expect(capture).toHaveBeenCalledWith('sign_out_clicked', {
      source: 'profile_page',
    })
  })
})
