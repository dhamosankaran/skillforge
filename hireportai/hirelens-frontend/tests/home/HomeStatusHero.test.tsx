import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser, Persona } from '@/context/AuthContext'
import type { HomeStateResponse } from '@/types/homeState'
import type { TrackerApplication } from '@/types'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchDailyQueue = vi.fn()
const fetchUserApplications = vi.fn()
const fetchHomeState = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchDailyQueue: () => fetchDailyQueue(),
    fetchUserApplications: () => fetchUserApplications(),
    fetchHomeState: () => fetchHomeState(),
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

import { HomeStatusHero } from '@/components/home/HomeStatusHero'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Dhamo',
    avatar_url: null,
    role: 'user',
    persona: 'interview_prepper',
    onboarding_completed: true,
    home_first_visit_seen_at: '2026-04-01T00:00:00Z',
    ...overrides,
  }
}

function homeStateFixture(
  overrides: Partial<HomeStateResponse['context']> = {},
  states: HomeStateResponse['states'] = [],
): HomeStateResponse {
  return {
    persona: 'interview_prepper',
    states,
    context: {
      current_streak: 0,
      last_review_at: null,
      active_mission_id: null,
      mission_target_date: null,
      last_scan_date: null,
      plan: 'free',
      last_activity_at: null,
      next_interview: null,
      ...overrides,
    },
  }
}

function appFixture(overrides: Partial<TrackerApplication> = {}): TrackerApplication {
  return {
    id: 'a1',
    company: 'Google',
    role: 'SWE',
    date_applied: '2026-04-20',
    ats_score: 71,
    status: 'Applied',
    scan_id: 's1',
    created_at: '2026-04-25T00:00:00Z',
    ...overrides,
  }
}

function isoNDaysFromNow(n: number): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

beforeEach(() => {
  capture.mockReset()
  fetchDailyQueue.mockReset()
  fetchUserApplications.mockReset()
  fetchHomeState.mockReset()
  fetchDailyQueue.mockResolvedValue({ total_due: 0, completed_today: false })
  fetchUserApplications.mockResolvedValue([])
  fetchHomeState.mockResolvedValue(homeStateFixture())
  mockUser = userFixture()
})

describe('HomeStatusHero', () => {
  describe('Interview-Prepper', () => {
    it('AC-1: renders all three clauses when company + days + due + score all available', async () => {
      mockUser = userFixture({ persona: 'interview_prepper' })
      fetchHomeState.mockResolvedValue(
        homeStateFixture({
          next_interview: {
            date: isoNDaysFromNow(12),
            company: 'Google',
            tracker_id: 't-1',
          },
          plan: 'free',
        }),
      )
      fetchDailyQueue.mockResolvedValue({ total_due: 5, completed_today: false })
      fetchUserApplications.mockResolvedValue([
        appFixture({ ats_score: 71, created_at: '2026-04-25T00:00:00Z' }),
      ])

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(screen.getByTestId('home-status-hero')).toHaveTextContent(
          'Google interview in 12d. 5 cards due today. Last scan was 71%.',
        ),
      )
    })

    it('AC-3: omits interview clause when next_interview is null', async () => {
      mockUser = userFixture({ persona: 'interview_prepper' })
      fetchHomeState.mockResolvedValue(homeStateFixture({ next_interview: null }))
      fetchDailyQueue.mockResolvedValue({ total_due: 5, completed_today: false })
      fetchUserApplications.mockResolvedValue([appFixture({ ats_score: 71 })])

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(screen.getByTestId('home-status-hero')).toHaveTextContent(
          '5 cards due today. Last scan was 71%.',
        ),
      )
      expect(screen.getByTestId('home-status-hero').textContent).not.toMatch(
        /interview in/i,
      )
    })

    it('omits scan clause when no applications exist', async () => {
      mockUser = userFixture({ persona: 'interview_prepper' })
      fetchHomeState.mockResolvedValue(
        homeStateFixture({
          next_interview: {
            date: isoNDaysFromNow(7),
            company: 'Stripe',
            tracker_id: 't-2',
          },
        }),
      )
      fetchDailyQueue.mockResolvedValue({ total_due: 3, completed_today: false })
      fetchUserApplications.mockResolvedValue([])

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(screen.getByTestId('home-status-hero')).toHaveTextContent(
          'Stripe interview in 7d. 3 cards due today.',
        ),
      )
      expect(screen.getByTestId('home-status-hero').textContent).not.toMatch(
        /Last scan/,
      )
    })

    it('AC-2 variant: renders "No cards due today." when total_due is 0', async () => {
      mockUser = userFixture({ persona: 'interview_prepper' })
      fetchHomeState.mockResolvedValue(homeStateFixture({ next_interview: null }))
      fetchDailyQueue.mockResolvedValue({ total_due: 0, completed_today: false })
      fetchUserApplications.mockResolvedValue([])

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(screen.getByTestId('home-status-hero')).toHaveTextContent(
          'No cards due today.',
        ),
      )
    })
  })

  describe('Career-Climber', () => {
    it('AC-4: renders streak + due', async () => {
      mockUser = userFixture({ persona: 'career_climber' })
      fetchHomeState.mockResolvedValue(homeStateFixture({ current_streak: 14 }))
      fetchDailyQueue.mockResolvedValue({ total_due: 5, completed_today: false })

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(screen.getByTestId('home-status-hero')).toHaveTextContent(
          '14-day streak. 5 cards due today.',
        ),
      )
    })

    it('AC-5: renders "Start your streak today." when current_streak is 0', async () => {
      mockUser = userFixture({ persona: 'career_climber' })
      fetchHomeState.mockResolvedValue(homeStateFixture({ current_streak: 0 }))
      fetchDailyQueue.mockResolvedValue({ total_due: 5, completed_today: false })

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(screen.getByTestId('home-status-hero')).toHaveTextContent(
          'Start your streak today. 5 cards due today.',
        ),
      )
    })

    it('AC-6: renders "No cards due today." when total_due is 0', async () => {
      mockUser = userFixture({ persona: 'career_climber' })
      fetchHomeState.mockResolvedValue(homeStateFixture({ current_streak: 7 }))
      fetchDailyQueue.mockResolvedValue({ total_due: 0, completed_today: false })

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(screen.getByTestId('home-status-hero')).toHaveTextContent(
          '7-day streak. No cards due today.',
        ),
      )
    })

    it('does NOT fetch tracker applications for career_climber', async () => {
      mockUser = userFixture({ persona: 'career_climber' })
      fetchHomeState.mockResolvedValue(homeStateFixture({ current_streak: 3 }))
      fetchDailyQueue.mockResolvedValue({ total_due: 2, completed_today: false })

      render(<HomeStatusHero />)

      await waitFor(() => expect(fetchDailyQueue).toHaveBeenCalled())
      expect(fetchUserApplications).not.toHaveBeenCalled()
    })
  })

  describe('Render gate', () => {
    it('AC-7: returns null for team_lead persona', async () => {
      mockUser = userFixture({ persona: 'team_lead' })
      fetchHomeState.mockResolvedValue(homeStateFixture())
      fetchDailyQueue.mockResolvedValue({ total_due: 5, completed_today: false })

      const { container } = render(<HomeStatusHero />)
      await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
      expect(container.querySelector('[data-testid="home-status-hero"]')).toBeNull()
    })

    it('AC-8: returns null when persona is null', async () => {
      mockUser = userFixture({ persona: null as unknown as Persona })
      fetchHomeState.mockResolvedValue(homeStateFixture())

      const { container } = render(<HomeStatusHero />)
      await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())
      expect(container.querySelector('[data-testid="home-status-hero"]')).toBeNull()
    })
  })

  describe('Analytics', () => {
    it('AC-9: fires home_status_hero_rendered exactly once with correct clauses_shown', async () => {
      mockUser = userFixture({ persona: 'interview_prepper' })
      fetchHomeState.mockResolvedValue(
        homeStateFixture({
          next_interview: {
            date: isoNDaysFromNow(12),
            company: 'Google',
            tracker_id: 't-1',
          },
          plan: 'pro',
        }),
      )
      fetchDailyQueue.mockResolvedValue({ total_due: 5, completed_today: false })
      fetchUserApplications.mockResolvedValue([
        appFixture({ ats_score: 71, created_at: '2026-04-25T00:00:00Z' }),
      ])

      render(<HomeStatusHero />)

      await waitFor(() =>
        expect(capture).toHaveBeenCalledWith(
          'home_status_hero_rendered',
          expect.objectContaining({
            persona: 'interview_prepper',
            plan: 'pro',
          }),
        ),
      )

      const heroCalls = capture.mock.calls.filter(
        (c) => c[0] === 'home_status_hero_rendered',
      )
      expect(heroCalls).toHaveLength(1)
      expect(heroCalls[0][1].clauses_shown).toEqual([
        'company',
        'days',
        'due',
        'score',
      ])
    })

    it('does NOT fire when component renders null (team_lead)', async () => {
      mockUser = userFixture({ persona: 'team_lead' })
      fetchHomeState.mockResolvedValue(homeStateFixture())
      fetchDailyQueue.mockResolvedValue({ total_due: 5, completed_today: false })

      render(<HomeStatusHero />)
      await waitFor(() => expect(fetchHomeState).toHaveBeenCalled())

      const heroCalls = capture.mock.calls.filter(
        (c) => c[0] === 'home_status_hero_rendered',
      )
      expect(heroCalls).toHaveLength(0)
    })
  })
})
