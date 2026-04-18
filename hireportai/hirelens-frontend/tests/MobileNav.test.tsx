import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

let mockUser: AuthUser | null = null
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
    updateUser: vi.fn(),
  }),
}))

import { MobileNav } from '@/components/layout/MobileNav'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
    ...overrides,
  }
}

beforeEach(() => {
  capture.mockReset()
  mockUser = userFixture()
})

describe('MobileNav', () => {
  it('renders four tabs with safe-area padding class', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <MobileNav />
      </MemoryRouter>,
    )
    const nav = screen.getByTestId('mobile-nav')
    expect(nav).toBeInTheDocument()
    expect(nav.className).toContain('pb-[env(safe-area-inset-bottom)]')
    expect(nav.className).toContain('fixed')
    expect(nav.className).toContain('bottom-0')

    expect(screen.getByTestId('mobile-nav-home')).toBeInTheDocument()
    expect(screen.getByTestId('mobile-nav-learn')).toBeInTheDocument()
    expect(screen.getByTestId('mobile-nav-prep')).toBeInTheDocument()
    expect(screen.getByTestId('mobile-nav-profile')).toBeInTheDocument()
    expect(screen.queryByTestId('mobile-nav-admin')).not.toBeInTheDocument()
  })

  it('marks the Learn tab active at /learn/daily', () => {
    render(
      <MemoryRouter initialEntries={['/learn/daily']}>
        <MobileNav />
      </MemoryRouter>,
    )
    const learn = screen.getByTestId('mobile-nav-learn')
    expect(learn).toHaveAttribute('data-active', 'true')
    expect(learn.className).toContain('text-accent-primary')
    expect(screen.getByTestId('mobile-nav-home')).toHaveAttribute('data-active', 'false')
  })

  it('returns null on public paths (/, /login, /pricing)', () => {
    for (const path of ['/', '/login', '/pricing']) {
      const { unmount } = render(
        <MemoryRouter initialEntries={[path]}>
          <MobileNav />
        </MemoryRouter>,
      )
      expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
      unmount()
    }
  })
})
