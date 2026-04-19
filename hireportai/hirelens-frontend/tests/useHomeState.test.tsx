import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchHomeState = vi.fn()
vi.mock('@/services/api', () => ({
  fetchHomeState: (...args: unknown[]) => fetchHomeState(...args),
}))

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

import { useHomeState } from '@/hooks/useHomeState'

beforeEach(() => {
  fetchHomeState.mockReset()
  capture.mockReset()
})

describe('useHomeState', () => {
  it('returns data on happy-path fetch and fires home_state_evaluated', async () => {
    fetchHomeState.mockResolvedValueOnce({
      persona: 'career_climber',
      states: ['streak_at_risk'],
      context: {
        current_streak: 5,
        last_review_at: null,
        active_mission_id: null,
        mission_target_date: null,
        last_scan_date: null,
        plan: 'free',
        last_activity_at: null,
      },
    })

    const { result } = renderHook(() => useHomeState())
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data?.states).toEqual(['streak_at_risk'])
    expect(result.current.error).toBeNull()
    expect(capture).toHaveBeenCalledWith(
      'home_state_evaluated',
      expect.objectContaining({
        persona: 'career_climber',
        states: ['streak_at_risk'],
        state_count: 1,
      }),
    )
  })

  it('returns null data + error on API failure (no throw)', async () => {
    fetchHomeState.mockRejectedValueOnce(new Error('500'))

    const { result } = renderHook(() => useHomeState())
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toBeNull()
    expect(result.current.error).not.toBeNull()
    expect(capture).not.toHaveBeenCalled()
  })
})
