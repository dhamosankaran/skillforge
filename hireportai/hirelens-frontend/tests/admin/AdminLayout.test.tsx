import { render, screen } from '@testing-library/react'
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

// PageWrapper → minimal passthrough (motion / observers are noisy in jsdom)
vi.mock('@/components/layout/PageWrapper', () => ({
  PageWrapper: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Mutable mock so the AdminGate-wrap test can flip role for one case.
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

import AdminLayout from '@/components/admin/AdminLayout'
import { AdminGate } from '@/components/auth/AdminGate'

function adminUser(): AuthUser {
  return {
    id: 'u1',
    email: 'admin@test',
    name: 'Admin',
    avatar_url: null,
    role: 'admin',
    persona: 'career_climber',
    onboarding_completed: true,
  }
}

function renderAdminTree(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index            element={<Navigate to="/admin/cards" replace />} />
          <Route path="cards"     element={<div data-testid="page-admin-cards" />} />
          <Route path="decks"     element={<div data-testid="page-admin-decks" />} />
          <Route path="lessons"   element={<div data-testid="page-admin-lessons" />} />
          <Route path="analytics" element={<div data-testid="page-admin-analytics" />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mockUser = adminUser()
  mockIsLoading = false
})

describe('AdminLayout (Phase 6 slice 6.4a — B-064)', () => {
  it('renders sidebar with 4 nav links: Cards / Decks / Lessons / Analytics (D-14: no Audit)', () => {
    renderAdminTree('/admin/cards')
    const nav = screen.getByRole('navigation', { name: /admin sections/i })
    const links = nav.querySelectorAll('a')
    expect(links).toHaveLength(4)
    expect(links[0]).toHaveAttribute('href', '/admin/cards')
    expect(links[0]).toHaveTextContent('Cards')
    expect(links[1]).toHaveAttribute('href', '/admin/decks')
    expect(links[1]).toHaveTextContent('Decks')
    expect(links[2]).toHaveAttribute('href', '/admin/lessons')
    expect(links[2]).toHaveTextContent('Lessons')
    expect(links[3]).toHaveAttribute('href', '/admin/analytics')
    expect(links[3]).toHaveTextContent('Analytics')
    expect(nav.querySelector('a[href="/admin/audit"]')).toBeNull()
  })

  it('redirects /admin (index) to /admin/cards', () => {
    renderAdminTree('/admin')
    expect(screen.getByTestId('page-admin-cards')).toBeInTheDocument()
  })

  it('renders the active child route via <Outlet /> (cards / decks / lessons / analytics)', () => {
    renderAdminTree('/admin/decks')
    expect(screen.getByTestId('page-admin-decks')).toBeInTheDocument()
    expect(screen.queryByTestId('page-admin-cards')).not.toBeInTheDocument()
  })

  it('marks the active sidebar link with aria-current="page" (a11y)', () => {
    renderAdminTree('/admin/lessons')
    const nav = screen.getByRole('navigation', { name: /admin sections/i })
    expect(nav.querySelector('a[href="/admin/lessons"]')).toHaveAttribute('aria-current', 'page')
    expect(nav.querySelector('a[href="/admin/cards"]')).not.toHaveAttribute('aria-current', 'page')
  })

  it('keeps `<AdminGate>` as the wrapping auth gate (AC-4 — non-admin sees forbidden view)', () => {
    mockUser = { ...adminUser(), role: 'user' }
    render(
      <MemoryRouter>
        <AdminGate>
          <AdminLayout />
        </AdminGate>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('admin-gate-forbidden')).toBeInTheDocument()
    expect(screen.queryByTestId('admin-sidebar')).not.toBeInTheDocument()
  })
})
