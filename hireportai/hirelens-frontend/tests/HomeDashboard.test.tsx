import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser, Persona } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

// Stub widgets so the page test focuses on shell behavior (modes, ordering,
// greeting, analytics). Each stub renders the real widget's root testid.
vi.mock('@/components/home/widgets/TodaysReviewWidget', () => ({
  TodaysReviewWidget: () => <div data-testid="widget-todays-review" />,
}))
vi.mock('@/components/home/widgets/StreakWidget', () => ({
  StreakWidget: () => <div data-testid="widget-streak" />,
}))
vi.mock('@/components/home/widgets/WeeklyProgressWidget', () => ({
  WeeklyProgressWidget: () => <div data-testid="widget-weekly-progress" />,
}))
vi.mock('@/components/home/widgets/LastScanWidget', () => ({
  LastScanWidget: () => <div data-testid="widget-last-scan" />,
}))
vi.mock('@/components/home/widgets/InterviewTargetWidget', () => ({
  InterviewTargetWidget: () => <div data-testid="widget-interview-target" />,
}))
vi.mock('@/components/home/widgets/CountdownWidget', () => ({
  CountdownWidget: () => <div data-testid="widget-countdown" />,
}))
vi.mock('@/components/home/widgets/TeamComingSoonWidget', () => ({
  TeamComingSoonWidget: () => <div data-testid="widget-team-coming-soon" />,
}))
// State-aware slot is exercised by its own test file. Stub it to a no-op
// here so this file's tests stay focused on shell behavior + widget order.
vi.mock('@/components/home/StateAwareWidgets', () => ({
  StateAwareWidgets: () => null,
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

import HomeDashboard from '@/pages/HomeDashboard'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Dhamo Sankaran',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
    ...overrides,
  }
}

function renderHome() {
  return render(
    <MemoryRouter initialEntries={['/home']}>
      <HomeDashboard />
    </MemoryRouter>,
  )
}

function getWidgetTestidsInOrder(container: HTMLElement): string[] {
  const nodes = container.querySelectorAll('[data-testid^="widget-"]')
  return Array.from(nodes).map((n) => n.getAttribute('data-testid') ?? '')
}

beforeEach(() => {
  capture.mockReset()
  mockUser = userFixture()
})

describe('HomeDashboard', () => {
  it('renders home-mode-interview_prepper when persona is interview_prepper', () => {
    mockUser = userFixture({
      persona: 'interview_prepper',
      interview_target_date: '2026-06-01',
      interview_target_company: 'Google',
    })
    renderHome()
    expect(screen.getByTestId('home-mode-interview_prepper')).toBeInTheDocument()
  })

  it('renders home-mode-career_climber when persona is career_climber', () => {
    mockUser = userFixture({ persona: 'career_climber' })
    renderHome()
    expect(screen.getByTestId('home-mode-career_climber')).toBeInTheDocument()
  })

  it('renders home-mode-team_lead when persona is team_lead', () => {
    mockUser = userFixture({ persona: 'team_lead' })
    renderHome()
    expect(screen.getByTestId('home-mode-team_lead')).toBeInTheDocument()
  })

  it('renders greeting with first name', () => {
    mockUser = userFixture({ name: 'Dhamo Sankaran' })
    renderHome()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome back, Dhamo.',
    )
  })

  it('falls back to "Welcome back." when user.name is empty', () => {
    mockUser = userFixture({ name: '' })
    renderHome()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome back.',
    )
  })

  it('fires home_dashboard_viewed exactly once on mount with persona', async () => {
    mockUser = userFixture({ persona: 'career_climber' })
    renderHome()
    await waitFor(() => expect(capture).toHaveBeenCalledTimes(1))
    expect(capture).toHaveBeenCalledWith('home_dashboard_viewed', {
      persona: 'career_climber',
    })
  })

  it('Interview-Prepper renders widgets in order: countdown, interview-target, todays-review, last-scan', () => {
    mockUser = userFixture({
      persona: 'interview_prepper',
      interview_target_date: '2026-06-01',
      interview_target_company: 'Google',
    })
    const { container } = renderHome()
    expect(getWidgetTestidsInOrder(container as HTMLElement)).toEqual([
      'widget-countdown',
      'widget-interview-target',
      'widget-todays-review',
      'widget-last-scan',
    ])
  })

  it('Career-Climber renders widgets in order: streak, todays-review, weekly-progress, last-scan', () => {
    mockUser = userFixture({ persona: 'career_climber' })
    const { container } = renderHome()
    expect(getWidgetTestidsInOrder(container as HTMLElement)).toEqual([
      'widget-streak',
      'widget-todays-review',
      'widget-weekly-progress',
      'widget-last-scan',
    ])
  })

  it('Team Lead renders widgets in order: todays-review, streak, weekly-progress, team-coming-soon', () => {
    mockUser = userFixture({ persona: 'team_lead' })
    const { container } = renderHome()
    expect(getWidgetTestidsInOrder(container as HTMLElement)).toEqual([
      'widget-todays-review',
      'widget-streak',
      'widget-weekly-progress',
      'widget-team-coming-soon',
    ])
  })

  it('returns null when persona is null (defensive — PersonaGate normally redirects)', () => {
    mockUser = userFixture({ persona: null as unknown as Persona })
    const { container } = renderHome()
    expect(container.querySelector('[data-testid^="home-mode-"]')).toBeNull()
  })
})
