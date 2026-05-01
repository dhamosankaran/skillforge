import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchScoreHistory = vi.fn()
vi.mock('@/services/api', () => ({
  fetchScoreHistory: (...args: unknown[]) => fetchScoreHistory(...args),
}))

import { useScoreHistory } from '@/hooks/useScoreHistory'

beforeEach(() => {
  fetchScoreHistory.mockReset()
})

describe('useScoreHistory — spec #63 §8.3', () => {
  it('disabled when trackerApplicationId is null', () => {
    const { result } = renderHook(() => useScoreHistory(null))
    expect(fetchScoreHistory).not.toHaveBeenCalled()
    expect(result.current.data).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })

  it('fetches and stores data when trackerApplicationId is provided', async () => {
    const payload = {
      tracker_application_id: 'tx',
      history: [],
      delta: null,
    }
    fetchScoreHistory.mockResolvedValue(payload)
    const { result } = renderHook(() => useScoreHistory('tx'))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(fetchScoreHistory).toHaveBeenCalledWith('tx')
    expect(result.current.data).toEqual(payload)
    expect(result.current.error).toBeNull()
  })

  it('exposes refetch that re-runs the fetch', async () => {
    fetchScoreHistory.mockResolvedValue({
      tracker_application_id: 'tx',
      history: [],
      delta: null,
    })
    const { result } = renderHook(() => useScoreHistory('tx'))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    fetchScoreHistory.mockClear()
    result.current.refetch()
    await waitFor(() =>
      expect(fetchScoreHistory).toHaveBeenCalledWith('tx'),
    )
  })
})
