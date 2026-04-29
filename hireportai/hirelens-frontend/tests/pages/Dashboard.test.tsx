import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { DashboardResponse } from '@/types'

// Phase 6 slice 6.8 — User-self FSRS dashboard tests.
// Spec: docs/specs/phase-6/09-fsrs-dashboard.md §10.3 + §11
// AC-1..AC-13 + §12 D-1..D-14.

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchFsrsDashboard = vi.fn()
vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>(
    '@/services/api',
  )
  return {
    ...actual,
    fetchFsrsDashboard: (...args: unknown[]) => fetchFsrsDashboard(...args),
  }
})

let mockUser: AuthUser | null = null
vi.mock('@/context/AuthContext', async () => {
  const actual = await vi.importActual<typeof import('@/context/AuthContext')>(
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

import Dashboard from '@/pages/Dashboard'

function userFixture(): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Dhamo',
    avatar_url: null,
    role: 'user',
    persona: 'interview_prepper',
    onboarding_completed: true,
    home_first_visit_seen_at: '2026-04-01T00:00:00Z',
  }
}

function dashboardFixture(
  overrides: Partial<DashboardResponse> = {},
): DashboardResponse {
  return {
    user_id: 'u1',
    persona: 'interview_prepper',
    plan: 'free',
    is_cold_start: false,
    retention_window_days: 30,
    generated_at: '2026-04-29T12:00:00Z',
    cards_due: {
      due_today: 5,
      due_next_7_days: 12,
      due_breakdown_by_state: {
        new: 4,
        learning: 2,
        review: 8,
        relearning: 1,
      },
      total_quiz_items_in_progress: 15,
    },
    retention: {
      sample_size: 4,
      overall_recall_rate: 0.75,
      overall_lapse_rate: 0.25,
      daily_retention: [
        { date: '2026-04-27', sample_size: 2, recall_rate: 1.0 },
        { date: '2026-04-28', sample_size: 0, recall_rate: null },
        { date: '2026-04-29', sample_size: 2, recall_rate: 0.5 },
      ],
    },
    deck_mastery: {
      decks: [
        {
          deck_id: 'd1',
          deck_slug: 'llm-internals',
          deck_title: 'LLM Internals',
          total_quiz_items_visible: 4,
          quiz_items_with_progress: 4,
          quiz_items_mastered: 3,
          mastery_pct: 0.75,
        },
      ],
    },
    streak: {
      current_streak: 7,
      longest_streak: 12,
      last_active_date: '2026-04-29',
      freezes_available: 2,
      total_xp: 450,
    },
    review_history: {
      window_days: 30,
      total_in_window: 4,
      recent_reviews: [
        {
          quiz_item_id: 'qi1',
          lesson_id: 'le1',
          lesson_title: 'Tokenization basics',
          deck_slug: 'llm-internals',
          rating: 3,
          fsrs_state_after: 'review',
          reviewed_at: '2026-04-29T12:00:00Z',
        },
      ],
    },
    ...overrides,
  }
}

function coldStartFixture(): DashboardResponse {
  return dashboardFixture({
    is_cold_start: true,
    cards_due: {
      due_today: 0,
      due_next_7_days: 0,
      due_breakdown_by_state: { new: 0, learning: 0, review: 0, relearning: 0 },
      total_quiz_items_in_progress: 0,
    },
    retention: {
      sample_size: 0,
      overall_recall_rate: 0,
      overall_lapse_rate: 0,
      daily_retention: Array.from({ length: 30 }, (_, i) => ({
        date: `2026-04-${String(i + 1).padStart(2, '0')}`,
        sample_size: 0,
        recall_rate: null,
      })),
    },
    deck_mastery: { decks: [] },
    streak: {
      current_streak: 0,
      longest_streak: 0,
      last_active_date: null,
      freezes_available: 0,
      total_xp: 0,
    },
    review_history: { window_days: 30, total_in_window: 0, recent_reviews: [] },
  })
}

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/learn/dashboard']}>
      <Dashboard />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  fetchFsrsDashboard.mockReset()
  mockUser = userFixture()
})

describe('Dashboard page (slice 6.8 / spec #09)', () => {
  it('renders all five section components when data resolves', async () => {
    fetchFsrsDashboard.mockResolvedValueOnce(dashboardFixture())

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-cards-due')).toBeInTheDocument()
    })
    expect(screen.getByTestId('dashboard-streak')).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-retention')).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-deck-mastery')).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-review-history')).toBeInTheDocument()
  })

  it('mounts cold-start variants when is_cold_start === true (D-13)', async () => {
    fetchFsrsDashboard.mockResolvedValueOnce(coldStartFixture())

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-cards-due-empty')).toBeInTheDocument()
    })
    expect(screen.getByTestId('dashboard-streak-empty')).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-retention-empty')).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-deck-mastery-empty')).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-review-history-empty')).toBeInTheDocument()
  })

  it('shows skeleton state during fetch', () => {
    fetchFsrsDashboard.mockReturnValueOnce(new Promise(() => {})) // never resolves

    renderDashboard()

    expect(screen.getByTestId('dashboard-loading')).toBeInTheDocument()
  })

  it('surfaces fetch error inline (no toast — read surface)', async () => {
    fetchFsrsDashboard.mockRejectedValueOnce(new Error('boom'))

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-error')).toBeInTheDocument()
    })
  })

  it('dashboard_viewed fires once via useRef even on Strict-Mode double-render (D-11)', async () => {
    fetchFsrsDashboard.mockResolvedValue(dashboardFixture())

    const { rerender } = renderDashboard()
    rerender(
      <MemoryRouter initialEntries={['/learn/dashboard']}>
        <Dashboard />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(capture).toHaveBeenCalledWith(
        'dashboard_viewed',
        expect.any(Object),
      )
    })
    const calls = capture.mock.calls.filter((c) => c[0] === 'dashboard_viewed')
    expect(calls.length).toBe(1)
  })

  it('dashboard_viewed payload includes persona + plan + is_cold_start + retention_window_days (D-11)', async () => {
    fetchFsrsDashboard.mockResolvedValueOnce(dashboardFixture())

    renderDashboard()

    await waitFor(() => {
      expect(capture).toHaveBeenCalledWith('dashboard_viewed', {
        persona: 'interview_prepper',
        plan: 'free',
        is_cold_start: false,
        retention_window_days: 30,
      })
    })
  })

  it('renders sections in DOM order locked at §12 D-2 (cards-due → streak → retention → deck-mastery → review-history)', async () => {
    fetchFsrsDashboard.mockResolvedValueOnce(dashboardFixture())

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-cards-due')).toBeInTheDocument()
    })
    const order = [
      'dashboard-cards-due',
      'dashboard-streak',
      'dashboard-retention',
      'dashboard-deck-mastery',
      'dashboard-review-history',
    ]
    const positions = order.map((id) =>
      screen.getByTestId(id).getBoundingClientRect
        ? document.querySelector(`[data-testid="${id}"]`)
        : null,
    )
    // Compare DOM order via compareDocumentPosition
    for (let i = 0; i < positions.length - 1; i++) {
      const cmp = positions[i]!.compareDocumentPosition(positions[i + 1]!)
      // Bit 4 set = following node
      expect(cmp & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    }
  })
})
