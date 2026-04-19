/**
 * Profile — Subscription section tests (Spec #36).
 *
 * Covers AC-1 (Pro sees Manage button), AC-3 (Free sees Upgrade button),
 * and AC-2 (Manage click creates portal session and redirects).
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

// ── Mocks ────────────────────────────────────────────────────────────────

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const createBillingPortalSession = vi.fn()
vi.mock('@/services/api', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: { total_reviewed: 0, by_state: {}, total_reps: 0, total_lapses: 0 } }) },
  createBillingPortalSession: (...args: unknown[]) => createBillingPortalSession(...args),
  generateExperience: vi.fn(),
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
  useAuth: () => ({ user: mockUser, isLoading: false, signIn: vi.fn(), signOut: vi.fn(), updateUser: vi.fn() }),
}))

let mockPlan: 'pro' | 'free' = 'free'
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: mockPlan, scansUsed: 0, maxScans: 3 },
    canScan: true,
    canUsePro: mockPlan === 'pro',
    canUsePremium: mockPlan === 'pro',
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

// Stub out heavy child components that are orthogonal to this section.
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
  createBillingPortalSession.mockReset()
  navigate.mockReset()
})

describe('Profile — Subscription section', () => {
  it('shows the Manage subscription button for Pro users (AC-1)', () => {
    mockPlan = 'pro'
    renderProfile()

    const section = screen.getByTestId('subscription-section')
    expect(section).toHaveTextContent('Pro plan')
    expect(section).toHaveTextContent('Active')
    expect(screen.getByRole('button', { name: /manage subscription/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /upgrade to pro/i })).not.toBeInTheDocument()
  })

  it('shows the Upgrade to Pro button for free users (AC-3)', async () => {
    mockPlan = 'free'
    renderProfile()

    const section = screen.getByTestId('subscription-section')
    expect(section).toHaveTextContent('Free plan')
    expect(screen.queryByRole('button', { name: /manage subscription/i })).not.toBeInTheDocument()

    const upgradeBtn = screen.getByRole('button', { name: /upgrade to pro/i })
    await userEvent.click(upgradeBtn)
    expect(navigate).toHaveBeenCalledWith('/pricing')
  })

  it('creates a portal session and redirects on Manage click (AC-2)', async () => {
    mockPlan = 'pro'
    createBillingPortalSession.mockResolvedValue({
      url: 'https://billing.stripe.com/p/session/bps_test',
    })

    // Stub window.location.href assignment — jsdom throws on navigation, and
    // some jsdom builds make `location` non-writable. Replace it with a
    // plain object for the duration of this test.
    const originalLocation = window.location
    // @ts-expect-error — deleting for test override
    delete window.location
    // @ts-expect-error — assigning a plain object replacement
    window.location = { href: '' } as Location

    try {
      renderProfile()
      await userEvent.click(screen.getByRole('button', { name: /manage subscription/i }))

      await waitFor(() => {
        expect(createBillingPortalSession).toHaveBeenCalledTimes(1)
      })
      expect(capture).toHaveBeenCalledWith('subscription_portal_opened')
      expect(window.location.href).toBe('https://billing.stripe.com/p/session/bps_test')
    } finally {
      // @ts-expect-error — restoring original
      window.location = originalLocation
    }
  })
})
