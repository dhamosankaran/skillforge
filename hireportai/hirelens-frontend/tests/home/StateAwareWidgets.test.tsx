import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach } from 'vitest'
import type { HomeStateResponse } from '@/types/homeState'

// Spec #61 — StateAwareWidgets now receives data/isLoading/error as
// props from HomeDashboard rather than fetching itself, so the hook
// mock is gone. Tests pass the hook-shape state directly.

type HookState = {
  data: HomeStateResponse | null
  isLoading: boolean
  error: Error | null
}

let mockState: HookState = { data: null, isLoading: true, error: null }

import { StateAwareWidgets } from '@/components/home/StateAwareWidgets'

function emptyContext() {
  return {
    current_streak: 0,
    last_review_at: null,
    active_mission_id: null,
    mission_target_date: null,
    last_scan_date: null,
    plan: 'free' as const,
    last_activity_at: null,
  }
}

function renderSlot() {
  return render(
    <MemoryRouter>
      <StateAwareWidgets
        persona="career_climber"
        data={mockState.data}
        isLoading={mockState.isLoading}
        error={mockState.error}
      />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mockState = { data: null, isLoading: true, error: null }
})

describe('StateAwareWidgets', () => {
  it('renders nothing while loading', () => {
    mockState = { data: null, isLoading: true, error: null }
    const { container } = renderSlot()
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing on API error', () => {
    mockState = { data: null, isLoading: false, error: new Error('boom') }
    const { container } = renderSlot()
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when states[] is empty', () => {
    mockState = {
      data: {
        persona: 'career_climber',
        states: [],
        context: emptyContext(),
      },
      isLoading: false,
      error: null,
    }
    const { container } = renderSlot()
    expect(container.firstChild).toBeNull()
  })

  it('renders the widget for the top-priority state only', () => {
    mockState = {
      data: {
        persona: 'career_climber',
        states: ['streak_at_risk', 'resume_stale'],
        context: { ...emptyContext(), current_streak: 5 },
      },
      isLoading: false,
      error: null,
    }
    renderSlot()
    expect(screen.getByTestId('widget-streak-at-risk')).toBeInTheDocument()
    expect(screen.queryByTestId('widget-resume-stale')).toBeNull()
  })

  it('maps mission_overdue to MissionOverdueWidget', () => {
    mockState = {
      data: {
        persona: 'interview_prepper',
        states: ['mission_overdue'],
        context: {
          ...emptyContext(),
          mission_target_date: '2026-04-01',
        },
      },
      isLoading: false,
      error: null,
    }
    renderSlot()
    expect(screen.getByTestId('widget-mission-overdue')).toBeInTheDocument()
  })
})
