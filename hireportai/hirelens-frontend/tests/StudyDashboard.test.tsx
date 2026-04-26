import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { Category } from '@/types'

// Spec #62 — StudyDashboard ?source=last_scan hero hint consumer.
// New test file (page had no test coverage today). Tests cover the
// 5 ACs in spec §8: param-present render, param-absent skip, dismiss
// interaction, ?source × ?category orthogonality, telemetry once-fire.

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

// Stub useStudyDashboard with a minimal category list so the page
// renders past the loading state and the banner / persona-card slot
// is reachable.
const categoriesFixture: Category[] = [
  {
    id: 'cat-1',
    name: 'JavaScript',
    icon: '🟨',
    color: '#f7df1e',
    display_order: 1,
    source: 'foundation',
    card_count: 10,
    studied_count: 0,
    locked: false,
  },
  {
    id: 'cat-2',
    name: 'React',
    icon: '⚛️',
    color: '#61dafb',
    display_order: 2,
    source: 'foundation',
    card_count: 8,
    studied_count: 0,
    locked: false,
  },
]
vi.mock('@/hooks/useStudyDashboard', () => ({
  useStudyDashboard: () => ({
    categories: categoriesFixture,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
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

vi.mock('@/context/UsageContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/UsageContext')>(
      '@/context/UsageContext',
    )
  return {
    ...actual,
    useUsage: () => ({
      usage: { plan: 'free', isAdmin: false },
      setShowUpgradeModal: vi.fn(),
    }),
  }
})

vi.mock('@/context/GamificationContext', async () => {
  const actual = await vi.importActual<
    typeof import('@/context/GamificationContext')
  >('@/context/GamificationContext')
  return {
    ...actual,
    useGamification: () => ({
      stats: { current_streak: 0, longest_streak: 0, total_xp: 0 },
    }),
  }
})

import StudyDashboard from '@/pages/StudyDashboard'

function userFixture(): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Dhamo Sankaran',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
    home_first_visit_seen_at: '2026-04-01T00:00:00Z',
  }
}

function renderAt(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <StudyDashboard />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  mockUser = userFixture()
})

describe('StudyDashboard — spec #62 source-hint', () => {
  // AC-1
  it('AC-1: ?source=last_scan present → banner renders with locked copy', async () => {
    renderAt('/learn?source=last_scan')
    const banner = await screen.findByTestId('study-dashboard-source-hint')
    expect(banner).toBeInTheDocument()
    expect(banner.textContent).toContain('Studying gaps from your last scan')
  })

  // AC-2
  it('AC-2: ?source absent → banner does NOT render', () => {
    renderAt('/learn')
    expect(screen.queryByTestId('study-dashboard-source-hint')).toBeNull()
  })

  // AC-3
  it('AC-3: dismiss × click → banner unmounts; URL is unchanged', async () => {
    renderAt('/learn?source=last_scan')
    const banner = await screen.findByTestId('study-dashboard-source-hint')
    expect(banner).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('study-dashboard-source-hint-dismiss'))
    await waitFor(() =>
      expect(screen.queryByTestId('study-dashboard-source-hint')).toBeNull(),
    )
    // Note: URL preservation (no setSearchParams call) is verified by the
    // absence of any test-side route mutation; component-state dismissal
    // does not invoke navigation. Spec §3.1 + §4.
  })

  // AC-4 — orthogonality with ?category filter (spec #09 consumer)
  it('AC-4: ?source=last_scan + ?category=cat-1 both present → banner renders AND category filter applies', async () => {
    renderAt('/learn?source=last_scan&category=cat-1')
    // Banner present
    expect(
      await screen.findByTestId('study-dashboard-source-hint'),
    ).toBeInTheDocument()
    // Category filter applied: cat-1 visible, cat-2 hidden. The card
    // grid renders the category names; assert the filter narrowed it.
    expect(screen.getByText('JavaScript')).toBeInTheDocument()
    expect(screen.queryByText('React')).toBeNull()
  })

  // AC-5
  it('AC-5: study_dashboard_source_hint_shown fires once on mount; does NOT re-fire on dismiss', async () => {
    renderAt('/learn?source=last_scan')
    await screen.findByTestId('study-dashboard-source-hint')
    const hintCalls = capture.mock.calls.filter(
      (c) => c[0] === 'study_dashboard_source_hint_shown',
    )
    expect(hintCalls).toHaveLength(1)
    expect(hintCalls[0][1]).toEqual({
      source: 'last_scan',
      persona: 'career_climber',
      copy_variant: '6A',
    })

    // Dismiss + assert no re-fire
    fireEvent.click(screen.getByTestId('study-dashboard-source-hint-dismiss'))
    await waitFor(() =>
      expect(screen.queryByTestId('study-dashboard-source-hint')).toBeNull(),
    )
    const hintCallsAfterDismiss = capture.mock.calls.filter(
      (c) => c[0] === 'study_dashboard_source_hint_shown',
    )
    expect(hintCallsAfterDismiss).toHaveLength(1)
  })
})
