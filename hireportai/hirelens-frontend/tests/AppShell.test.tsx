import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

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

vi.mock('@/utils/posthog', () => ({
  capture: vi.fn(),
  default: {},
}))

import { AppShell } from '@/components/layout/AppShell'

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
  mockUser = userFixture()
})

function renderAt(pathname: string) {
  return render(
    <MemoryRouter initialEntries={[pathname]}>
      <AppShell>
        <div data-testid="app-content" />
      </AppShell>
    </MemoryRouter>,
  )
}

describe('AppShell chrome hide-list', () => {
  it('hides TopNav and MobileNav on /onboarding/persona', () => {
    renderAt('/onboarding/persona')
    expect(screen.queryByTestId('top-nav')).not.toBeInTheDocument()
    expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
    expect(screen.getByTestId('app-content')).toBeInTheDocument()
  })

  it('renders TopNav and MobileNav on a non-chromeless protected path', () => {
    renderAt('/home')
    expect(screen.getByTestId('top-nav')).toBeInTheDocument()
    expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
  })

  it.each(['/', '/login', '/onboarding/persona', '/first-action'])(
    'stays chromeless on %s regardless of auth state',
    (path) => {
      mockUser = userFixture()
      renderAt(path)
      expect(screen.queryByTestId('top-nav')).not.toBeInTheDocument()
      expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
    },
  )

  it('keeps /pricing chromeless for guests (user === null)', () => {
    mockUser = null
    renderAt('/pricing')
    expect(screen.queryByTestId('top-nav')).not.toBeInTheDocument()
    expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
    expect(screen.getByTestId('app-content')).toBeInTheDocument()
  })

  it('shows TopNav and MobileNav on /pricing for authed users so they can escape paywall flows', () => {
    mockUser = userFixture()
    renderAt('/pricing')
    expect(screen.getByTestId('top-nav')).toBeInTheDocument()
    expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
  })
})
