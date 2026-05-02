import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ThumbsResponse } from '@/types'

const submitThumbs = vi.fn<
  [string, { score: -1 | 1 }],
  Promise<ThumbsResponse>
>()

vi.mock('@/services/api', () => ({
  submitThumbs: (...args: unknown[]) =>
    submitThumbs(...(args as Parameters<typeof submitThumbs>)),
}))

import { useThumbs } from '@/hooks/useThumbs'

beforeEach(() => {
  submitThumbs.mockReset()
})

describe('useThumbs', () => {
  it('updates state from server response on success', async () => {
    submitThumbs.mockResolvedValueOnce({
      accepted: true,
      score: 1,
      aggregate_score: 0.5,
      aggregate_count: 2,
    })
    const { result } = renderHook(() => useThumbs('l1'))

    await act(async () => {
      await result.current.submit(1)
    })

    expect(result.current.score).toBe(1)
    expect(result.current.aggregate).toBe(0.5)
    expect(result.current.count).toBe(2)
    expect(result.current.error).toBeNull()
  })

  it('reverts optimistic state on error and surfaces error message', async () => {
    submitThumbs.mockRejectedValueOnce(new Error('network down'))
    const { result } = renderHook(() =>
      useThumbs('l1', { score: -1, aggregate: -1, count: 1 }),
    )

    await act(async () => {
      await result.current.submit(1)
    })

    expect(result.current.score).toBe(-1)
    expect(result.current.aggregate).toBe(-1)
    expect(result.current.count).toBe(1)
    expect(result.current.error).toBe('network down')
  })

  it('toggles isSubmitting during the round-trip', async () => {
    let resolve!: (resp: ThumbsResponse) => void
    submitThumbs.mockImplementationOnce(
      () =>
        new Promise<ThumbsResponse>((r) => {
          resolve = r
        }),
    )
    const { result } = renderHook(() => useThumbs('l1'))

    let submitPromise: Promise<void>
    act(() => {
      submitPromise = result.current.submit(1)
    })
    await waitFor(() => {
      expect(result.current.isSubmitting).toBe(true)
    })
    await act(async () => {
      resolve({
        accepted: true,
        score: 1,
        aggregate_score: 1,
        aggregate_count: 1,
      })
      await submitPromise
    })
    expect(result.current.isSubmitting).toBe(false)
  })
})
