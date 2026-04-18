import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import type { GamificationStats } from '@/types'

type GamState = {
  stats: GamificationStats | null
  isLoading: boolean
  error: string | null
}

let mockState: GamState = { stats: null, isLoading: true, error: null }

vi.mock('@/context/GamificationContext', () => ({
  useGamification: () => ({
    stats: mockState.stats,
    isLoading: mockState.isLoading,
    error: mockState.error,
    refresh: vi.fn(),
  }),
}))

// ActivityHeatmap self-fetches; stub it so the widget test isn't entangled.
vi.mock('@/components/progress/ActivityHeatmap', () => ({
  ActivityHeatmap: () => <div data-testid="activity-heatmap" />,
}))

import { WeeklyProgressWidget } from '@/components/home/widgets/WeeklyProgressWidget'

function renderWidget() {
  return render(
    <MemoryRouter>
      <WeeklyProgressWidget persona="career_climber" />
    </MemoryRouter>,
  )
}

function stats(overrides: Partial<GamificationStats> = {}): GamificationStats {
  return {
    user_id: 'u1',
    current_streak: 0,
    longest_streak: 0,
    total_xp: 0,
    last_active_date: null,
    freezes_available: 0,
    badges: [],
    ...overrides,
  }
}

describe('WeeklyProgressWidget', () => {
  it('shows skeleton while loading with no stats', () => {
    mockState = { stats: null, isLoading: true, error: null }
    const { container } = renderWidget()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders the heatmap when there is review history', () => {
    mockState = {
      stats: stats({ total_xp: 50, longest_streak: 2 }),
      isLoading: false,
      error: null,
    }
    renderWidget()
    expect(screen.getByTestId('activity-heatmap')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /view profile/i }),
    ).toBeInTheDocument()
  })

  it('shows empty-state CTA when the user has no review history', () => {
    mockState = {
      stats: stats({ total_xp: 0, longest_streak: 0 }),
      isLoading: false,
      error: null,
    }
    renderWidget()
    expect(
      screen.getByText(/review your first card to see your activity heatmap/i),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /start reviewing/i }),
    ).toHaveAttribute('href', '/learn/daily')
  })
})
