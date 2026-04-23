import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

let mockUser: AuthUser | null = null
let mockIsLoading = false
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: mockIsLoading,
    signIn: vi.fn(),
    signOut: vi.fn(),
    updateUser: vi.fn(),
  }),
}))

import { AdminGate } from '@/components/auth/AdminGate'

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

function renderGate() {
  return render(
    <MemoryRouter>
      <AdminGate>
        <div data-testid="admin-children">admin-only content</div>
      </AdminGate>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mockUser = null
  mockIsLoading = false
})

describe('AdminGate (spec #54 / E-040)', () => {
  it('renders children when user.role is admin', () => {
    mockUser = userFixture({ role: 'admin' })
    renderGate()
    expect(screen.getByTestId('admin-children')).toBeInTheDocument()
    expect(screen.queryByTestId('admin-gate-forbidden')).not.toBeInTheDocument()
  })

  it('renders the Forbidden view when user.role is user', () => {
    mockUser = userFixture({ role: 'user' })
    renderGate()
    expect(screen.getByTestId('admin-gate-forbidden')).toBeInTheDocument()
    expect(screen.queryByTestId('admin-children')).not.toBeInTheDocument()
    expect(screen.getByText('Admin access required.')).toBeInTheDocument()
  })

  it('renders the Forbidden view when user is null', () => {
    mockUser = null
    renderGate()
    expect(screen.getByTestId('admin-gate-forbidden')).toBeInTheDocument()
  })

  it('returns null while auth is loading (prevents flicker)', () => {
    mockIsLoading = true
    mockUser = userFixture({ role: 'admin' })
    const { container } = renderGate()
    expect(container.firstChild).toBeNull()
  })

  it('Forbidden view has a back-link to /home', () => {
    mockUser = userFixture({ role: 'user' })
    renderGate()
    const link = screen.getByRole('link', { name: /back to home/i })
    expect(link).toHaveAttribute('href', '/home')
  })
})
