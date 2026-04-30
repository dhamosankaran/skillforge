import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser, Persona } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const markHomeFirstVisit = vi.fn()
const fetchHomeState = vi.fn()
const fetchUserApplications = vi.fn()
const fetchActiveMission = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    markHomeFirstVisit: () => markHomeFirstVisit(),
    fetchHomeState: () => fetchHomeState(),
    fetchUserApplications: () => fetchUserApplications(),
    fetchActiveMission: () => fetchActiveMission(),
  }
})

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
// Spec #61 — mocks honor suppression props (otherwise the suppression
// composition tests can't observe the early-null return path).
vi.mock('@/components/home/widgets/LastScanWidget', () => ({
  LastScanWidget: ({ suppressed }: { suppressed?: boolean }) =>
    suppressed ? null : <div data-testid="widget-last-scan" />,
}))
vi.mock('@/components/home/widgets/InterviewTargetWidget', () => ({
  InterviewTargetWidget: ({
    suppressedByMissionState,
  }: {
    suppressedByMissionState?: boolean
  }) =>
    suppressedByMissionState ? null : (
      <div data-testid="widget-interview-target" />
    ),
}))
vi.mock('@/components/home/widgets/CountdownWidget', () => ({
  CountdownWidget: ({
    suppressedByMissionState,
  }: {
    suppressedByMissionState?: boolean
  }) =>
    suppressedByMissionState ? null : (
      <div data-testid="widget-countdown" />
    ),
}))
vi.mock('@/components/home/widgets/TeamComingSoonWidget', () => ({
  TeamComingSoonWidget: () => <div data-testid="widget-team-coming-soon" />,
}))
// State-aware slot is exercised by its own test file. Stub it to a no-op
// here so this file's tests stay focused on shell behavior + widget order.
vi.mock('@/components/home/StateAwareWidgets', () => ({
  StateAwareWidgets: () => null,
}))
// Spec #61 §4 — StudyGapsPromptWidget has its own dedicated test file
// (tests/home/widgets/StudyGapsPromptWidget.test.tsx). Stub here so the
// shell test stays focused on persona-mode + widget-order assertions.
vi.mock('@/components/home/widgets/StudyGapsPromptWidget', () => ({
  StudyGapsPromptWidget: () => null,
}))

// Spec #61 — HomeDashboard now calls useUsage() (via useStudyPromptEligibility)
// for the StudyGapsPrompt eligibility / LastScan suppression flag. Mock to a
// free + non-admin default so the existing shell-behavior tests behave as
// they did pre-spec; spec #61 composition tests below override as needed.
let mockUsageState = { plan: 'free' as const, isAdmin: false }
vi.mock('@/context/UsageContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/UsageContext')>(
      '@/context/UsageContext',
    )
  return {
    ...actual,
    useUsage: () => ({
      usage: { plan: mockUsageState.plan, isAdmin: mockUsageState.isAdmin },
      setShowUpgradeModal: vi.fn(),
    }),
  }
})

let mockUser: AuthUser | null = null
const updateUser = vi.fn()
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

import HomeDashboard from '@/pages/HomeDashboard'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  // Default to a return visitor so the bulk of shell-behavior tests read
  // the stable "Welcome back" copy. First-visit tests pass
  // `home_first_visit_seen_at: null` to flip the branch.
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Dhamo Sankaran',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
    home_first_visit_seen_at: '2026-04-01T00:00:00Z',
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
  updateUser.mockReset()
  markHomeFirstVisit.mockReset()
  markHomeFirstVisit.mockResolvedValue(userFixture())
  fetchHomeState.mockReset()
  fetchHomeState.mockResolvedValue({
    persona: null,
    states: [],
    context: { next_interview: null },
  })
  fetchUserApplications.mockReset()
  fetchUserApplications.mockResolvedValue([])
  fetchActiveMission.mockReset()
  fetchActiveMission.mockResolvedValue(null)
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

  it('renders return-visit greeting with first name when home_first_visit_seen_at is set', () => {
    mockUser = userFixture({ name: 'Dhamo Sankaran' })
    renderHome()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome back, Dhamo.',
    )
  })

  it('return-visit: falls back to "Welcome back." when user.name is empty', () => {
    mockUser = userFixture({ name: '' })
    renderHome()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome back.',
    )
  })

  // ── B-016 first-visit greeting ──────────────────────────────────────────
  it('first-visit: renders "Welcome, <first name>." when home_first_visit_seen_at is null', () => {
    mockUser = userFixture({
      name: 'Dhamo Sankaran',
      home_first_visit_seen_at: null,
    })
    renderHome()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome, Dhamo.',
    )
  })

  it('first-visit: falls back to "Welcome to SkillForge." when user.name is empty', () => {
    mockUser = userFixture({ name: '', home_first_visit_seen_at: null })
    renderHome()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome to SkillForge.',
    )
  })

  it('first-visit: POSTs the stamp endpoint once and applies the returned user', async () => {
    const stamped = userFixture({
      name: 'Dhamo Sankaran',
      home_first_visit_seen_at: '2026-04-22T10:00:00Z',
    })
    markHomeFirstVisit.mockResolvedValueOnce(stamped)
    mockUser = userFixture({
      name: 'Dhamo Sankaran',
      home_first_visit_seen_at: null,
    })
    renderHome()
    await waitFor(() => expect(markHomeFirstVisit).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(updateUser).toHaveBeenCalledWith(stamped))
  })

  it('return-visit: does NOT POST the stamp endpoint', async () => {
    mockUser = userFixture({ home_first_visit_seen_at: '2026-04-01T00:00:00Z' })
    renderHome()
    // Give the effect a tick; then assert no call.
    await waitFor(() => expect(capture).toHaveBeenCalled())
    expect(markHomeFirstVisit).not.toHaveBeenCalled()
  })

  // B-027: greeting must not flip from "Welcome" → "Welcome back" inside a
  // single mount once the post-stamp updateUser applies the stamped user.
  it('first-visit: greeting stays "Welcome, <name>." after the stamp flips server-side (no mid-session flash)', async () => {
    const stamped = userFixture({
      name: 'Dhamo Sankaran',
      home_first_visit_seen_at: '2026-04-23T10:00:00Z',
    })
    markHomeFirstVisit.mockResolvedValueOnce(stamped)
    mockUser = userFixture({
      name: 'Dhamo Sankaran',
      home_first_visit_seen_at: null,
    })
    const { rerender } = renderHome()

    await waitFor(() => expect(markHomeFirstVisit).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(updateUser).toHaveBeenCalledWith(stamped))

    // Simulate the updateUser effect in AuthContext by swapping mockUser to
    // the stamped value and re-rendering the same tree. isFirstVisit was
    // snapshotted on mount, so the greeting must stay as-is.
    mockUser = stamped
    rerender(
      <MemoryRouter initialEntries={['/home']}>
        <HomeDashboard />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome, Dhamo.',
    )
  })

  it('first-visit stamp failure is silent (no toast, no crash)', async () => {
    markHomeFirstVisit.mockRejectedValueOnce(new Error('network'))
    mockUser = userFixture({
      name: 'Dhamo Sankaran',
      home_first_visit_seen_at: null,
    })
    renderHome()
    await waitFor(() => expect(markHomeFirstVisit).toHaveBeenCalledTimes(1))
    // Greeting still renders and updateUser never fires on rejection.
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome, Dhamo.',
    )
    expect(updateUser).not.toHaveBeenCalled()
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

  // ── Spec #61 §3 composition suppression — AC-1, AC-2, AC-3, AC-8 ─────────
  describe('Spec #61 — composition suppression', () => {
    it('AC-1 + AC-2: when state slot fires mission_active for the user mission, Countdown AND InterviewTarget are suppressed', async () => {
      mockUser = userFixture({
        persona: 'interview_prepper',
        interview_target_date: '2026-06-01',
        interview_target_company: 'Google',
      })
      fetchHomeState.mockResolvedValueOnce({
        persona: 'interview_prepper',
        states: ['mission_active'],
        context: {
          current_streak: 0,
          last_review_at: null,
          active_mission_id: 'm1',
          mission_target_date: '2026-06-01',
          last_scan_date: null,
          plan: 'free',
          last_activity_at: null,
          next_interview: {
            date: '2026-06-01',
            company: 'Google',
            tracker_id: 't-1',
          },
        },
      })
      const { container } = renderHome()
      // Wait for useHomeState to resolve and trigger re-render with topState set
      await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
      await waitFor(() => {
        expect(container.querySelector('[data-testid="widget-countdown"]')).toBeNull()
        expect(
          container.querySelector('[data-testid="widget-interview-target"]'),
        ).toBeNull()
      })
    })

    it('AC-3: when no Mission state in slot, both Countdown and InterviewTarget render', async () => {
      mockUser = userFixture({
        persona: 'interview_prepper',
        interview_target_date: '2026-06-01',
        interview_target_company: 'Google',
      })
      fetchHomeState.mockResolvedValueOnce({
        persona: 'interview_prepper',
        states: [],
        context: {
          current_streak: 0,
          last_review_at: null,
          active_mission_id: null,
          mission_target_date: null,
          last_scan_date: null,
          plan: 'free',
          last_activity_at: null,
          next_interview: {
            date: '2026-06-01',
            company: 'Google',
            tracker_id: 't-1',
          },
        },
      })
      renderHome()
      await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
      // Both widgets present after the hook resolves
      await waitFor(() => {
        expect(screen.getByTestId('widget-countdown')).toBeInTheDocument()
        expect(screen.getByTestId('widget-interview-target')).toBeInTheDocument()
      })
    })

    it('AC-1 carve-out: Countdown is NOT suppressed when active mission target_date differs from user.interview_target_date', async () => {
      mockUser = userFixture({
        persona: 'interview_prepper',
        interview_target_date: '2026-06-01',
        interview_target_company: 'Google',
      })
      fetchHomeState.mockResolvedValueOnce({
        persona: 'interview_prepper',
        states: ['mission_active'],
        context: {
          current_streak: 0,
          last_review_at: null,
          active_mission_id: 'm1',
          mission_target_date: '2026-08-15', // ≠ user's next_interview date
          last_scan_date: null,
          plan: 'free',
          last_activity_at: null,
          next_interview: {
            date: '2026-06-01',
            company: 'Google',
            tracker_id: 't-1',
          },
        },
      })
      renderHome()
      await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
      // Countdown NOT suppressed (different mission); InterviewTarget IS
      // suppressed (broader rule per §5).
      await waitFor(() => {
        expect(screen.getByTestId('widget-countdown')).toBeInTheDocument()
        expect(
          screen.queryByTestId('widget-interview-target'),
        ).toBeNull()
      })
    })

    it('AC-8: when StudyGapsPromptWidget eligibility is true, LastScan is suppressed from the static grid', async () => {
      mockUser = userFixture({
        persona: 'interview_prepper',
        interview_target_date: '2026-06-01',
        interview_target_company: 'Google',
      })
      // Eligibility predicates true: free user, has scan, no mission.
      fetchUserApplications.mockResolvedValue([
        {
          id: 'a1',
          company: 'JPMorgan',
          role: 'SWE',
          date_applied: '2026-04-20',
          status: 'Applied',
          ats_score: 71,
          scan_id: 's1',
          created_at: '2026-04-25',
        },
      ])
      fetchActiveMission.mockResolvedValue(null)
      const { container } = renderHome()
      await waitFor(() => expect(fetchUserApplications).toHaveBeenCalled())
      await waitFor(() =>
        expect(container.querySelector('[data-testid="widget-last-scan"]')).toBeNull(),
      )
    })
  })
})
