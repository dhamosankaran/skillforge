import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AxiosHeaders } from 'axios'

// Slice 6.0 spec §10.5 — recordLessonView FE helper.

const toastError = vi.fn()
vi.mock('react-hot-toast', () => {
  const fakeToast = {
    error: (...args: unknown[]) => toastError(...args),
    success: vi.fn(),
    dismiss: vi.fn(),
    loading: vi.fn(),
    custom: vi.fn(),
  }
  return { default: fakeToast, toast: fakeToast, Toaster: () => null }
})

import api, { recordLessonView } from '@/services/api'

describe('recordLessonView — slice 6.0 dual-write FE helper', () => {
  const originalAdapter = api.defaults.adapter

  beforeEach(() => {
    toastError.mockReset()
  })

  afterEach(() => {
    api.defaults.adapter = originalAdapter
  })

  it('POSTs to /api/v1/lessons/:id/view-event with the body shape', async () => {
    const adapter = vi.fn().mockResolvedValue({
      status: 204,
      data: '',
      statusText: 'No Content',
      headers: {},
      config: { headers: new AxiosHeaders() },
    })
    api.defaults.adapter = adapter

    await recordLessonView('lesson-abc', {
      deck_id: 'deck-xyz',
      version: 3,
      session_id: 'sess-9',
    })

    expect(adapter).toHaveBeenCalledOnce()
    const config = adapter.mock.calls[0][0]
    expect(config.method).toBe('post')
    expect(config.url).toBe('/api/v1/lessons/lesson-abc/view-event')
    expect(JSON.parse(config.data)).toEqual({
      deck_id: 'deck-xyz',
      version: 3,
      session_id: 'sess-9',
    })
  })

  it('swallows network errors silently (best-effort per spec §6.4 + D-7)', async () => {
    api.defaults.adapter = vi.fn().mockRejectedValue(new Error('network down'))

    await expect(
      recordLessonView('lesson-x', {
        deck_id: 'deck-y',
        version: 1,
        session_id: 'sess-z',
      }),
    ).resolves.toBeUndefined()
  })
})
