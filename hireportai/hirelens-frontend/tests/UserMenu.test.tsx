import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const signOut = vi.fn()
let mockUser: AuthUser | null = null
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    signIn: vi.fn(),
    signOut,
    updateUser: vi.fn(),
  }),
}))

import { UserMenu } from '@/components/layout/UserMenu'

function userFixture(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 'dhamo@example.com',
    name: 'Dhamo Sankaran',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
    ...overrides,
  }
}

function renderMenu() {
  return render(
    <MemoryRouter>
      <UserMenu />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  signOut.mockReset()
  signOut.mockResolvedValue(undefined)
  mockUser = userFixture()
})

describe('UserMenu', () => {
  it('renders nothing when user is null', () => {
    mockUser = null
    const { container } = renderMenu()
    expect(container.querySelector('[data-testid="user-menu"]')).toBeNull()
  })

  it('renders the avatar trigger with the first initial when avatar_url is empty', () => {
    mockUser = userFixture({ name: 'Dhamo', avatar_url: null })
    renderMenu()
    const trigger = screen.getByTestId('user-menu-trigger')
    expect(trigger).toHaveTextContent('D')
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByTestId('user-menu-dropdown')).not.toBeInTheDocument()
  })

  it('opens the dropdown on trigger click and shows user identity + menu items', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('user-menu-trigger'))
    expect(screen.getByTestId('user-menu-dropdown')).toBeInTheDocument()
    expect(screen.getByTestId('user-menu-profile')).toHaveAttribute('href', '/profile')
    expect(screen.getByTestId('user-menu-signout')).toBeInTheDocument()
    expect(screen.getByText('dhamo@example.com')).toBeInTheDocument()
    expect(screen.getByTestId('user-menu-trigger')).toHaveAttribute('aria-expanded', 'true')
  })

  it('closes the dropdown on Escape', () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('user-menu-trigger'))
    expect(screen.getByTestId('user-menu-dropdown')).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByTestId('user-menu-dropdown')).not.toBeInTheDocument()
  })

  it('closes the dropdown on outside click', () => {
    const { container } = renderMenu()
    fireEvent.click(screen.getByTestId('user-menu-trigger'))
    expect(screen.getByTestId('user-menu-dropdown')).toBeInTheDocument()
    fireEvent.mouseDown(container.ownerDocument.body)
    expect(screen.queryByTestId('user-menu-dropdown')).not.toBeInTheDocument()
  })

  it('fires signOut and sign_out_clicked analytics on Sign out click', async () => {
    renderMenu()
    fireEvent.click(screen.getByTestId('user-menu-trigger'))
    fireEvent.click(screen.getByTestId('user-menu-signout'))
    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1))
    expect(capture).toHaveBeenCalledWith('sign_out_clicked', {
      source: 'topnav_avatar',
    })
  })
})
