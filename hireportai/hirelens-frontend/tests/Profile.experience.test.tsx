/**
 * Profile — "Generate My Experience" section tests (B-003 regression guard).
 *
 * P5-S11 fixed the backend side of B-003 (token starvation + empty-response
 * guard). This file locks the FE button wiring so the three observable
 * states the user actually sees — empty history, generation error, and
 * happy-path narrative — stay regression-tested after P5-S11's manual
 * smoke verification.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

// ── Mocks ────────────────────────────────────────────────────────────────

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const apiGet = vi.fn()
const generateExperience = vi.fn()
const createBillingPortalSession = vi.fn()
vi.mock('@/services/api', () => ({
  default: { get: (...args: unknown[]) => apiGet(...args) },
  createBillingPortalSession: (...args: unknown[]) => createBillingPortalSession(...args),
  generateExperience: (...args: unknown[]) => generateExperience(...args),
}))

const mockUser: AuthUser = {
  id: 'u1',
  email: 't@example.com',
  name: 'Test',
  avatar_url: null,
  role: 'user',
  persona: 'career_climber',
  onboarding_completed: true,
}
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: mockUser, isLoading: false, signIn: vi.fn(), signOut: vi.fn(), updateUser: vi.fn(), refreshUser: vi.fn() }),
}))

vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: 'pro' as const, scansUsed: 0, maxScans: 3 },
    canScan: true,
    canUsePro: true,
    canUsePremium: true,
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

// Stub heavy children orthogonal to this section.
vi.mock('@/components/progress/SkillRadar', () => ({ SkillRadar: () => null }))
vi.mock('@/components/progress/ActivityHeatmap', () => ({ ActivityHeatmap: () => null }))
vi.mock('@/components/settings/EmailPreferences', () => ({ EmailPreferences: () => null }))
vi.mock('@/components/settings/ThemePicker', () => ({ ThemePicker: () => null }))
vi.mock('@/components/profile/XPBar', () => ({ XPBar: () => null }))
vi.mock('@/components/layout/PageWrapper', () => ({
  PageWrapper: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => vi.fn() }
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
  apiGet.mockReset()
  generateExperience.mockReset()
})

describe('Profile — Generate My Experience (B-003)', () => {
  it('hides the button and shows the empty-state copy when the user has no study history', async () => {
    apiGet.mockResolvedValue({
      data: { total_reviewed: 0, by_state: {}, total_reps: 0, total_lapses: 0 },
    })

    renderProfile()

    // Wait for the study-progress effect to resolve before asserting.
    await waitFor(() => {
      expect(screen.getByText(/study some cards first/i)).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /generate my experience/i })).not.toBeInTheDocument()
  })

  it('clicks the button → calls generateExperience → renders the narrative + Copy + Regenerate', async () => {
    apiGet.mockResolvedValue({
      data: {
        total_reviewed: 5,
        by_state: { review: 5 },
        total_reps: 12,
        total_lapses: 1,
      },
    })
    generateExperience.mockResolvedValue({
      experience_text: 'Demonstrated strong proficiency in system design through 5 assessments.',
      summary: 'Strong in system design.',
      cards_studied: 5,
    })

    renderProfile()

    const button = await screen.findByRole('button', { name: /generate my experience/i })
    await userEvent.click(button)

    await waitFor(() => {
      expect(generateExperience).toHaveBeenCalledWith({})
    })
    expect(
      await screen.findByText(/demonstrated strong proficiency in system design/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /copy to clipboard/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /regenerate/i })).toBeInTheDocument()
    expect(capture).toHaveBeenCalledWith(
      'experience_generated',
      expect.objectContaining({ cards_studied_count: 5 }),
    )
  })

  it('shows the inline error message when the backend fails (503)', async () => {
    apiGet.mockResolvedValue({
      data: {
        total_reviewed: 5,
        by_state: { review: 5 },
        total_reps: 12,
        total_lapses: 1,
      },
    })
    generateExperience.mockRejectedValue(new Error('Service unavailable'))

    renderProfile()

    const button = await screen.findByRole('button', { name: /generate my experience/i })
    await userEvent.click(button)

    expect(
      await screen.findByText(/failed to generate experience/i),
    ).toBeInTheDocument()
    // Button stays visible so the user can retry without a page reload.
    expect(screen.getByRole('button', { name: /generate my experience/i })).toBeInTheDocument()
    expect(capture).not.toHaveBeenCalledWith('experience_generated', expect.anything())
  })
})
