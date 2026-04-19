import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

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

import FirstAction, { FIRST_ACTION_SEEN_KEY } from '@/pages/FirstAction'

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
  mockUser = null
  window.localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

// Date-math tests need a deterministic "today"; use fake timers locally so
// userEvent's internal setTimeout calls in click-based tests stay on real
// timers and don't hang.
function freezeToday() {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-04-19T12:00:00Z'))
}

describe('FirstAction', () => {
  it('renders date+company CTA for Interview-Prepper with both set', () => {
    freezeToday()
    mockUser = userFixture({
      persona: 'interview_prepper',
      interview_target_date: '2026-05-03', // 14 days after 2026-04-19
      interview_target_company: 'Google',
    })
    renderFirstAction()
    expect(screen.getByTestId('first-action-primary')).toHaveTextContent(
      'Start your 14-day Mission to Google',
    )
  })

  it('renders date-only CTA for Interview-Prepper without company', () => {
    freezeToday()
    mockUser = userFixture({
      persona: 'interview_prepper',
      interview_target_date: '2026-05-03',
      interview_target_company: null,
    })
    renderFirstAction()
    expect(screen.getByTestId('first-action-primary')).toHaveTextContent(
      'Start your 14-day Mission',
    )
    expect(
      screen.getByTestId('first-action-primary').textContent,
    ).not.toContain('to')
  })

  it('renders browse-categories CTA for Interview-Prepper without date', () => {
    mockUser = userFixture({
      persona: 'interview_prepper',
      interview_target_date: null,
      interview_target_company: null,
    })
    renderFirstAction()
    expect(screen.getByTestId('first-action-primary')).toHaveTextContent(
      'Browse interview prep categories',
    )
  })

  it('renders Daily Review CTA for Career-Climber', () => {
    mockUser = userFixture({ persona: 'career_climber' })
    renderFirstAction()
    expect(screen.getByTestId('first-action-primary')).toHaveTextContent(
      'Start your first Daily Review',
    )
  })

  it('renders card-library CTA for Team Lead', () => {
    mockUser = userFixture({ persona: 'team_lead' })
    renderFirstAction()
    expect(screen.getByTestId('first-action-primary')).toHaveTextContent(
      'Browse the card library',
    )
  })

  it('primary CTA sets the seen flag and navigates to the matrix route', async () => {
    const user = userEvent.setup()
    mockUser = userFixture({ persona: 'career_climber' })
    renderFirstAction()
    await user.click(screen.getByTestId('first-action-primary'))
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
    await user.click(screen.getByTestId('first-action-secondary'))
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
    // No CTA rendered when the flag short-circuits the page.
    expect(screen.queryByTestId('first-action-primary')).not.toBeInTheDocument()
    // And no viewed event fires in the bypassed state.
    expect(capture).not.toHaveBeenCalledWith(
      'first_action_viewed',
      expect.anything(),
    )
  })

  it('fires first_action_viewed exactly once per mount', () => {
    mockUser = userFixture({ persona: 'interview_prepper' })
    const { rerender } = renderFirstAction()
    // Rerender in the same mount; the useRef guard should hold.
    rerender(
      <MemoryRouter initialEntries={['/first-action']}>
        <FirstAction />
      </MemoryRouter>,
    )
    const calls = capture.mock.calls.filter(
      ([event]) => event === 'first_action_viewed',
    )
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toEqual({ persona: 'interview_prepper' })
  })
})
