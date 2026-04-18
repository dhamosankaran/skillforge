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

describe('AppShell chrome hide-list', () => {
  it('hides TopNav and MobileNav on /onboarding/persona', () => {
    render(
      <MemoryRouter initialEntries={['/onboarding/persona']}>
        <AppShell>
          <div data-testid="app-content" />
        </AppShell>
      </MemoryRouter>,
    )
    expect(screen.queryByTestId('top-nav')).not.toBeInTheDocument()
    expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
    expect(screen.getByTestId('app-content')).toBeInTheDocument()
  })

  it('renders TopNav and MobileNav on a non-chromeless protected path', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <AppShell>
          <div data-testid="app-content" />
        </AppShell>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('top-nav')).toBeInTheDocument()
    expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
  })
})
