/**
 * MissionMode page-level tests — spec #53 §7.3 branching.
 *
 * Scoped to the `phase === 'setup'` fork:
 *   - interview_prepper with no date  → MissionDateGate
 *   - interview_prepper with a date   → MissionSetup (AC-6)
 *   - non-interview_prepper personas  → MissionSetup regardless of date (AC-6)
 *
 * useMission + useGamification are stubbed so `phase` lands on `setup`
 * immediately without touching the real hook machinery. Child components
 * (MissionSetup, MissionDateGate, Countdown, etc.) are left real — we
 * query by testid to distinguish.
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser, Persona } from '@/context/AuthContext'

vi.mock('@/utils/posthog', () => ({
  capture: vi.fn(),
  default: {},
}))

// Stub useMission to land in the `setup` branch (noMission=true,
// !isLoading, no error, no mission).
const mockUseMission = vi.fn()
vi.mock('@/hooks/useMission', () => ({
  useMission: () => mockUseMission(),
}))

// Spec #57 AC-6 — MissionMode now reads next_interview from useHomeState
// to decide between MissionDateGate vs MissionSetup.
const mockUseHomeState = vi.fn()
vi.mock('@/hooks/useHomeState', () => ({
  useHomeState: () => mockUseHomeState(),
}))

vi.mock('@/context/GamificationContext', () => ({
  useGamification: () => ({ refresh: vi.fn() }),
}))

// MissionSetup mounts an API-fetching hook internally; stub to a simple
// testid marker so we can distinguish it from MissionDateGate.
vi.mock('@/components/mission/MissionSetup', () => ({
  MissionSetup: () => <div data-testid="mission-setup-stub" />,
}))

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
      updateUser: vi.fn(),
    }),
  }
})

import MissionMode from '@/pages/MissionMode'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: 'interview_prepper' as Persona,
    onboarding_completed: true,
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/learn/mission']}>
      <MissionMode />
    </MemoryRouter>,
  )
}

function homeStateFixture(nextInterview: {
  date: string
  company: string
  tracker_id: string
} | null) {
  return {
    data: {
      persona: null,
      states: [],
      context: {
        current_streak: 0,
        last_review_at: null,
        active_mission_id: null,
        mission_target_date: null,
        last_scan_date: null,
        plan: 'free' as const,
        last_activity_at: null,
        next_interview: nextInterview,
      },
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }
}

beforeEach(() => {
  mockUseMission.mockReset()
  mockUseHomeState.mockReset()
  // Default: setup branch (no active mission, not loading, no error).
  mockUseMission.mockReturnValue({
    mission: null,
    daily: null,
    categories: [],
    isLoading: false,
    error: null,
    noMission: true,
    create: vi.fn(),
    completeDay: vi.fn(),
    refresh: vi.fn(),
    refreshDaily: vi.fn(),
  })
  // Default: no next_interview (gate fires for interview_prepper).
  mockUseHomeState.mockReturnValue(homeStateFixture(null))
})

describe('MissionMode setup-phase branching (spec #53 §7.3 + spec #57 AC-6)', () => {
  it('interview_prepper + no next_interview → MissionDateGate, not MissionSetup (AC-4)', () => {
    mockUser = userFixture({ persona: 'interview_prepper' })
    mockUseHomeState.mockReturnValue(homeStateFixture(null))
    renderPage()
    expect(screen.getByTestId('mission-date-gate')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-setup-stub')).toBeNull()
  })

  it('interview_prepper with a next_interview → MissionSetup, not MissionDateGate (AC-6)', () => {
    mockUser = userFixture({ persona: 'interview_prepper' })
    mockUseHomeState.mockReturnValue(
      homeStateFixture({
        date: '2026-06-01',
        company: 'Google',
        tracker_id: 't-1',
      }),
    )
    renderPage()
    expect(screen.getByTestId('mission-setup-stub')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-date-gate')).toBeNull()
  })

  it('career_climber → MissionSetup regardless of next_interview (AC-6 carve-out)', () => {
    mockUser = userFixture({ persona: 'career_climber' as Persona })
    renderPage()
    expect(screen.getByTestId('mission-setup-stub')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-date-gate')).toBeNull()
  })

  it('team_lead → MissionSetup regardless of next_interview (AC-6 carve-out)', () => {
    mockUser = userFixture({ persona: 'team_lead' as Persona })
    renderPage()
    expect(screen.getByTestId('mission-setup-stub')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-date-gate')).toBeNull()
  })
})
