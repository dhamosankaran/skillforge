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

import { TopNav } from '@/components/layout/TopNav'

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

describe('TopNav', () => {
  // B-029: Profile removed from TopNav nav items (now lives in the UserMenu
  // avatar dropdown). MobileNav still keeps Profile as a tab.
  it('renders three tabs for a non-admin user (Home/Learn/Prep)', () => {
    mockUser = userFixture({ role: 'user' })
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TopNav />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('top-nav-home')).toBeInTheDocument()
    expect(screen.getByTestId('top-nav-learn')).toBeInTheDocument()
    expect(screen.getByTestId('top-nav-prep')).toBeInTheDocument()
    expect(screen.queryByTestId('top-nav-profile')).not.toBeInTheDocument()
    expect(screen.queryByTestId('top-nav-admin')).not.toBeInTheDocument()
  })

  it('renders four tabs (including Admin) for an admin user', () => {
    mockUser = userFixture({ role: 'admin' })
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TopNav />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('top-nav-home')).toBeInTheDocument()
    expect(screen.getByTestId('top-nav-learn')).toBeInTheDocument()
    expect(screen.getByTestId('top-nav-prep')).toBeInTheDocument()
    expect(screen.queryByTestId('top-nav-profile')).not.toBeInTheDocument()
    expect(screen.getByTestId('top-nav-admin')).toBeInTheDocument()
  })

  const activeCases: Array<{ path: string; activeTab: string }> = [
    { path: '/home',          activeTab: 'home' },
    { path: '/learn/daily',   activeTab: 'learn' },
    { path: '/prep/rewrite',  activeTab: 'prep' },
    { path: '/admin',         activeTab: 'admin' },
  ]

  it.each(activeCases)('marks the $activeTab tab active at $path', ({ path, activeTab }) => {
    mockUser = userFixture({ role: 'admin' })
    render(
      <MemoryRouter initialEntries={[path]}>
        <TopNav />
      </MemoryRouter>,
    )
    const active = screen.getByTestId(`top-nav-${activeTab}`)
    expect(active).toHaveAttribute('data-active', 'true')
    expect(active.className).toContain('text-accent-primary')

    const others = activeCases.filter((c) => c.activeTab !== activeTab)
    for (const other of others) {
      const el = screen.queryByTestId(`top-nav-${other.activeTab}`)
      if (el) expect(el).toHaveAttribute('data-active', 'false')
    }
  })

  it('treats /home as an exact match (does not activate Home on /home-extra paths)', () => {
    render(
      <MemoryRouter initialEntries={['/learn/daily']}>
        <TopNav />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('top-nav-home')).toHaveAttribute('data-active', 'false')
    expect(screen.getByTestId('top-nav-learn')).toHaveAttribute('data-active', 'true')
  })

  // B-028: UserMenu (avatar + sign-out dropdown) mounts in the TopNav.
  it('mounts the UserMenu avatar trigger alongside the nav tabs', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <TopNav />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('user-menu-trigger')).toBeInTheDocument()
  })
})
