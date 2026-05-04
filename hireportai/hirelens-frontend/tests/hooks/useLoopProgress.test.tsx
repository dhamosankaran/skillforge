import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchLoopProgress = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchLoopProgress: (id: string) => fetchLoopProgress(id),
  }
})

import { useLoopProgress } from '@/hooks/useLoopProgress'

beforeEach(() => {
  fetchLoopProgress.mockReset()
})

describe('useLoopProgress', () => {
  it('returns null + no fetch when trackerId is null', async () => {
    const { result } = renderHook(() => useLoopProgress(null))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toBeNull()
    expect(fetchLoopProgress).not.toHaveBeenCalled()
  })

  it('happy path returns LoopProgressResponse', async () => {
    fetchLoopProgress.mockResolvedValue({
      tracker_application_id: 't-1',
      total_gap_cards: 8,
      reviewed_gap_cards: 4,
      percent_reviewed: 50,
      days_since_last_scan: 2,
    })
    const { result } = renderHook(() => useLoopProgress('t-1'))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data?.percent_reviewed).toBe(50)
    expect(result.current.error).toBeNull()
    expect(fetchLoopProgress).toHaveBeenCalledWith('t-1')
  })

  it('D-14: error sets data null + surfaces error (caller falls back to future)', async () => {
    fetchLoopProgress.mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useLoopProgress('t-1'))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeInstanceOf(Error)
  })
})
