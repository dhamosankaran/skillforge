import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

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

import { PersonaGate } from '@/components/PersonaGate'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: null,
    onboarding_completed: false,
    ...overrides,
  }
}

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="probe" data-pathname={loc.pathname} />
}

function mount(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/onboarding/persona"
          element={
            <PersonaGate>
              <div data-testid="child-onboarding" />
            </PersonaGate>
          }
        />
        <Route
          path="*"
          element={
            <PersonaGate>
              <div data-testid="child" />
            </PersonaGate>
          }
        />
      </Routes>
      <LocationProbe />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mockUser = null
})

describe('PersonaGate', () => {
  it('redirects null-persona user to /onboarding/persona from /home', () => {
    mockUser = userFixture({ persona: null })
    mount('/home')
    expect(screen.getByTestId('probe')).toHaveAttribute('data-pathname', '/onboarding/persona')
    expect(screen.getByTestId('child-onboarding')).toBeInTheDocument()
    expect(screen.queryByTestId('child')).not.toBeInTheDocument()
  })

  it('renders the route without redirect when persona is set', () => {
    mockUser = userFixture({ persona: 'career_climber' })
    mount('/home')
    expect(screen.getByTestId('probe')).toHaveAttribute('data-pathname', '/home')
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('does not redirect on exempt paths even when persona is null', () => {
    mockUser = userFixture({ persona: null })
    for (const path of ['/', '/login', '/onboarding/persona']) {
      const { unmount } = mount(path)
      expect(screen.getByTestId('probe')).toHaveAttribute('data-pathname', path)
      unmount()
    }
  })
})
