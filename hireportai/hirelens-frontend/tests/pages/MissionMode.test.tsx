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

beforeEach(() => {
  mockUseMission.mockReset()
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
})

describe('MissionMode setup-phase branching (spec #53 §7.3)', () => {
  it('interview_prepper + null date → MissionDateGate, not MissionSetup (AC-4)', () => {
    mockUser = userFixture({
      persona: 'interview_prepper',
      interview_target_date: null,
    })
    renderPage()
    expect(screen.getByTestId('mission-date-gate')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-setup-stub')).toBeNull()
  })

  it('interview_prepper with a date → MissionSetup, not MissionDateGate (AC-6)', () => {
    mockUser = userFixture({
      persona: 'interview_prepper',
      interview_target_date: '2026-06-01',
    })
    renderPage()
    expect(screen.getByTestId('mission-setup-stub')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-date-gate')).toBeNull()
  })

  it('career_climber → MissionSetup regardless of date field (AC-6)', () => {
    mockUser = userFixture({
      persona: 'career_climber',
      interview_target_date: null,
    })
    renderPage()
    expect(screen.getByTestId('mission-setup-stub')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-date-gate')).toBeNull()
  })

  it('team_lead → MissionSetup regardless of date field (AC-6)', () => {
    mockUser = userFixture({
      persona: 'team_lead',
      interview_target_date: null,
    })
    renderPage()
    expect(screen.getByTestId('mission-setup-stub')).toBeInTheDocument()
    expect(screen.queryByTestId('mission-date-gate')).toBeNull()
  })
})
