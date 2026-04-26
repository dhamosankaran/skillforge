import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

// Spec #61 §4 + §8 ACs (AC-4..AC-8, AC-11..AC-12) — StudyGapsPromptWidget
// is the new free-tier scan→study/upgrade surface. Tests cover render
// gates, primary/secondary CTA wiring, telemetry firing, and the
// LastScan suppression precondition (StudyGapsPromptWidget rendering
// implies LastScan is hidden by HomeDashboard — the suppression flag
// is exercised in HomeDashboard.test.tsx).

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchUserApplications = vi.fn()
const fetchActiveMission = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchUserApplications: () => fetchUserApplications(),
    fetchActiveMission: () => fetchActiveMission(),
  }
})

let mockUser: AuthUser | null = null
vi.mock('@/context/AuthContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/AuthContext')>(
      '@/context/AuthContext',
    )
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      updateUser: vi.fn(),
    }),
  }
})

const setShowUpgradeModal = vi.fn()
let mockUsageState = {
  plan: 'free' as 'free' | 'pro' | 'enterprise',
  isAdmin: false,
}
vi.mock('@/context/UsageContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/UsageContext')>(
      '@/context/UsageContext',
    )
  return {
    ...actual,
    useUsage: () => ({
      usage: { plan: mockUsageState.plan, isAdmin: mockUsageState.isAdmin },
      setShowUpgradeModal: (show: boolean) => setShowUpgradeModal(show),
    }),
  }
})

import { StudyGapsPromptWidget } from '@/components/home/widgets/StudyGapsPromptWidget'

function userFixture(): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Dhamo Sankaran',
    avatar_url: null,
    role: 'user',
    persona: 'interview_prepper',
    onboarding_completed: true,
    home_first_visit_seen_at: '2026-04-01T00:00:00Z',
  }
}

function appFixture(overrides = {}) {
  return {
    id: 'a1',
    company: 'JPMorgan Chase & Co.',
    role: 'Software Engineer',
    date_applied: '2026-04-20',
    status: 'Applied' as const,
    ats_score: 71,
    scan_id: 'scan_abc',
    skills_matched: ['react', 'typescript'],
    skills_missing: ['rust', 'kubernetes', 'docker', 'aws', 'terraform'],
    created_at: '2026-04-25T12:00:00Z',
    ...overrides,
  }
}

function renderWidget(props: { suppressed?: boolean } = {}) {
  return render(
    <MemoryRouter>
      <StudyGapsPromptWidget {...props} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  fetchUserApplications.mockReset()
  fetchActiveMission.mockReset()
  setShowUpgradeModal.mockReset()
  mockUser = userFixture()
  mockUsageState = {
    plan: 'free',
    isAdmin: false,
  }
})

describe('StudyGapsPromptWidget', () => {
  // AC-4: renders for plan=free + !isAdmin + recent scan + no active mission
  it('AC-4 renders with primary + secondary CTAs when all 4 predicates pass', async () => {
    fetchUserApplications.mockResolvedValueOnce([appFixture()])
    fetchActiveMission.mockResolvedValueOnce(null)
    renderWidget()

    await waitFor(() =>
      expect(screen.getByTestId('study-gaps-prompt')).toBeInTheDocument(),
    )
    const primary = screen.getByTestId('study-gaps-prompt-primary')
    expect(primary).toHaveTextContent('Study the gaps from your last scan')
    expect(primary.getAttribute('href')).toBe('/learn?source=last_scan')

    const secondary = screen.getByTestId('study-gaps-prompt-secondary')
    expect(secondary.getAttribute('data-emphasis')).toBe('secondary')
    expect(secondary.textContent?.toLowerCase()).toContain('upgrade')
    // Secondary is an <a> link, not a primary <button>
    expect(secondary.tagName).toBe('A')
  })

  // AC-5: hidden when active mission
  it('AC-5 does NOT render when an active mission exists', async () => {
    fetchUserApplications.mockResolvedValueOnce([appFixture()])
    fetchActiveMission.mockResolvedValueOnce({ id: 'm1', status: 'active' })
    const { container } = renderWidget()
    await waitFor(() => expect(fetchActiveMission).toHaveBeenCalled())
    expect(screen.queryByTestId('study-gaps-prompt')).toBeNull()
    expect(container.querySelector('[data-testid="study-gaps-prompt"]')).toBeNull()
  })

  // AC-6: hidden for Pro / Enterprise / admin
  it('AC-6 does NOT render for plan=pro', async () => {
    mockUsageState = { ...mockUsageState, plan: 'pro' }
    fetchUserApplications.mockResolvedValueOnce([appFixture()])
    fetchActiveMission.mockResolvedValueOnce(null)
    renderWidget()
    // Predicates short-circuit; no fetch should happen.
    await new Promise((r) => setTimeout(r, 0))
    expect(screen.queryByTestId('study-gaps-prompt')).toBeNull()
    expect(fetchUserApplications).not.toHaveBeenCalled()
  })

  it('AC-6 does NOT render when isAdmin=true', async () => {
    mockUsageState = { ...mockUsageState, isAdmin: true }
    renderWidget()
    await new Promise((r) => setTimeout(r, 0))
    expect(screen.queryByTestId('study-gaps-prompt')).toBeNull()
    expect(fetchUserApplications).not.toHaveBeenCalled()
  })

  // AC-7: hidden when no recent scan
  it('AC-7 does NOT render when there are no scans', async () => {
    fetchUserApplications.mockResolvedValueOnce([])
    fetchActiveMission.mockResolvedValueOnce(null)
    renderWidget()
    await waitFor(() => expect(fetchUserApplications).toHaveBeenCalled())
    expect(screen.queryByTestId('study-gaps-prompt')).toBeNull()
  })

  // AC-11: home_study_gaps_prompt_shown fires once on mount when eligible
  it('AC-11 fires home_study_gaps_prompt_shown once on mount', async () => {
    fetchUserApplications.mockResolvedValueOnce([appFixture()])
    fetchActiveMission.mockResolvedValueOnce(null)
    renderWidget()
    await waitFor(() => expect(screen.getByTestId('study-gaps-prompt')))
    expect(capture).toHaveBeenCalledWith('home_study_gaps_prompt_shown', {
      plan: 'free',
      persona: 'interview_prepper',
    })
  })

  // AC-12: home_study_gaps_clicked fires with cta enum on each CTA click
  it('AC-12 fires home_study_gaps_clicked {cta: primary} on primary click', async () => {
    fetchUserApplications.mockResolvedValueOnce([appFixture()])
    fetchActiveMission.mockResolvedValueOnce(null)
    renderWidget()
    await waitFor(() => expect(screen.getByTestId('study-gaps-prompt-primary')))
    fireEvent.click(screen.getByTestId('study-gaps-prompt-primary'))
    expect(capture).toHaveBeenCalledWith('home_study_gaps_clicked', {
      plan: 'free',
      persona: 'interview_prepper',
      cta: 'primary',
    })
  })

  it('AC-12 fires home_study_gaps_clicked {cta: secondary_upgrade} + opens UpgradeModal on secondary click', async () => {
    fetchUserApplications.mockResolvedValueOnce([appFixture()])
    fetchActiveMission.mockResolvedValueOnce(null)
    renderWidget()
    await waitFor(() => expect(screen.getByTestId('study-gaps-prompt-secondary')))
    fireEvent.click(screen.getByTestId('study-gaps-prompt-secondary'))
    expect(capture).toHaveBeenCalledWith('home_study_gaps_clicked', {
      plan: 'free',
      persona: 'interview_prepper',
      cta: 'secondary_upgrade',
    })
    expect(setShowUpgradeModal).toHaveBeenCalledWith(true)
  })

  // suppressed prop short-circuits any fetch + render
  it('suppressed=true → renders nothing AND skips both fetches', async () => {
    renderWidget({ suppressed: true })
    await new Promise((r) => setTimeout(r, 0))
    expect(screen.queryByTestId('study-gaps-prompt')).toBeNull()
    expect(fetchUserApplications).not.toHaveBeenCalled()
    expect(fetchActiveMission).not.toHaveBeenCalled()
  })

  // Body copy includes scan company name + gap count when available
  it('body copy includes the company name and gap count from the latest scan', async () => {
    fetchUserApplications.mockResolvedValueOnce([appFixture()])
    fetchActiveMission.mockResolvedValueOnce(null)
    renderWidget()
    await waitFor(() => expect(screen.getByTestId('study-gaps-prompt')))
    expect(screen.getByText(/JPMorgan Chase/)).toBeInTheDocument()
    expect(screen.getByText(/5 skill gaps/)).toBeInTheDocument()
  })
})
