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

import { StreakWidget } from '@/components/home/widgets/StreakWidget'

function renderWidget() {
  return render(
    <MemoryRouter>
      <StreakWidget persona="career_climber" />
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

describe('StreakWidget', () => {
  it('shows skeleton while loading with no stats', () => {
    mockState = { stats: null, isLoading: true, error: null }
    const { container } = renderWidget()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('shows current + longest streak when current_streak > 0', () => {
    mockState = {
      stats: stats({ current_streak: 7, longest_streak: 12 }),
      isLoading: false,
      error: null,
    }
    renderWidget()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText(/best: 12 days/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view profile/i })).toHaveAttribute(
      'href',
      '/profile',
    )
  })

  it('shows empty-state CTA when current_streak === 0', () => {
    mockState = {
      stats: stats({ current_streak: 0 }),
      isLoading: false,
      error: null,
    }
    renderWidget()
    expect(
      screen.getByText(/start your streak — review a card today/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /start now/i })).toHaveAttribute(
      'href',
      '/learn/daily',
    )
  })

  it('shows error state when stats fails to load', () => {
    mockState = { stats: null, isLoading: false, error: 'nope' }
    renderWidget()
    expect(screen.getByText(/couldn't load your streak/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /try again/i }),
    ).toBeInTheDocument()
  })
})
