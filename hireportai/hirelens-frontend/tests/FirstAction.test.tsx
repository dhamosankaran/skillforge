import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { NextInterview } from '@/types/homeState'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

let mockNextInterview: NextInterview | null = null
const fetchHomeState = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
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

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

import FirstAction, { FIRST_ACTION_SEEN_KEY, computeCta } from '@/pages/FirstAction'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 'test@example.com',
    name: 'Ada Lovelace',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
    ...overrides,
  }
}

function renderFirstAction() {
  return render(
    <MemoryRouter initialEntries={['/first-action']}>
      <FirstAction />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  navigate.mockReset()
  fetchHomeState.mockReset()
  mockUser = null
  mockNextInterview = null
  fetchHomeState.mockImplementation(() =>
    Promise.resolve({
      persona: null,
      states: [],
      context: { next_interview: mockNextInterview },
    }),
  )
  window.localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

function freezeToday() {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-04-19T12:00:00Z'))
}

describe('FirstAction — spec #57 AC-7 re-source from next_interview', () => {
  it('computeCta — interview_prepper with next_interview present uses date+company', () => {
    freezeToday()
    const cta = computeCta('interview_prepper', {
      date: '2026-05-03',
      company: 'Google',
      tracker_id: 't-1',
    })
    expect(cta).toEqual({
      label: 'Start your 14-day Mission to Google',
      route: '/learn/mission',
    })
  })

  it('computeCta — interview_prepper with null next_interview falls back to browse-categories', () => {
    const cta = computeCta('interview_prepper', null)
    expect(cta).toEqual({
      label: 'Browse interview prep categories',
      route: '/learn',
    })
  })

  it('computeCta — career_climber and team_lead branches preserved verbatim', () => {
    expect(computeCta('career_climber', null)).toEqual({
      label: 'Start your first Daily Review',
      route: '/learn/daily',
    })
    expect(computeCta('team_lead', null)).toEqual({
      label: 'Browse the card library',
      route: '/learn',
    })
  })
})

describe('FirstAction', () => {
  it('renders Daily Review CTA for Career-Climber', async () => {
    mockUser = userFixture({ persona: 'career_climber' })
    renderFirstAction()
    expect(
      await screen.findByTestId('first-action-primary'),
    ).toHaveTextContent('Start your first Daily Review')
  })

  it('renders card-library CTA for Team Lead', async () => {
    mockUser = userFixture({ persona: 'team_lead' })
    renderFirstAction()
    expect(
      await screen.findByTestId('first-action-primary'),
    ).toHaveTextContent('Browse the card library')
  })

  it('renders browse-categories CTA for Interview-Prepper without next_interview', async () => {
    mockUser = userFixture({ persona: 'interview_prepper' })
    mockNextInterview = null
    renderFirstAction()
    expect(
      await screen.findByTestId('first-action-primary'),
    ).toHaveTextContent('Browse interview prep categories')
  })

  it('primary CTA sets the seen flag and navigates to the matrix route', async () => {
    const user = userEvent.setup()
    mockUser = userFixture({ persona: 'career_climber' })
    renderFirstAction()
    await user.click(await screen.findByTestId('first-action-primary'))
    expect(window.localStorage.getItem(FIRST_ACTION_SEEN_KEY)).toBe('true')
    expect(navigate).toHaveBeenCalledWith('/learn/daily', { replace: true })
    expect(capture).toHaveBeenCalledWith('first_action_primary_clicked', {
      persona: 'career_climber',
      cta_route: '/learn/daily',
    })
  })

  it('secondary link sets the seen flag and navigates to /home', async () => {
    const user = userEvent.setup()
    mockUser = userFixture({ persona: 'team_lead' })
    renderFirstAction()
    await user.click(await screen.findByTestId('first-action-secondary'))
    expect(window.localStorage.getItem(FIRST_ACTION_SEEN_KEY)).toBe('true')
    expect(navigate).toHaveBeenCalledWith('/home', { replace: true })
    expect(capture).toHaveBeenCalledWith('first_action_secondary_clicked', {
      persona: 'team_lead',
    })
  })

  it('redirects to /home on mount when the seen flag is already set', () => {
    mockUser = userFixture({ persona: 'career_climber' })
    window.localStorage.setItem(FIRST_ACTION_SEEN_KEY, 'true')
    renderFirstAction()
    expect(navigate).toHaveBeenCalledWith('/home', { replace: true })
    expect(screen.queryByTestId('first-action-primary')).not.toBeInTheDocument()
    expect(capture).not.toHaveBeenCalledWith(
      'first_action_viewed',
      expect.anything(),
    )
  })

  it('fires first_action_viewed exactly once per mount', async () => {
    mockUser = userFixture({ persona: 'interview_prepper' })
    const { rerender } = renderFirstAction()
    rerender(
      <MemoryRouter initialEntries={['/first-action']}>
        <FirstAction />
      </MemoryRouter>,
    )
    // Allow the home-state fetch to settle so the CTA renders.
    await screen.findByTestId('first-action-primary')
    const calls = capture.mock.calls.filter(
      ([event]) => event === 'first_action_viewed',
    )
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toEqual({ persona: 'interview_prepper' })
  })
})
