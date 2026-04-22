import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AxiosError, AxiosHeaders } from 'axios'

// ─── Mocks ────────────────────────────────────────────────────────────────

const toastError = vi.fn()
vi.mock('react-hot-toast', () => {
  const api = {
    error: (...args: unknown[]) => toastError(...args),
    success: vi.fn(),
    dismiss: vi.fn(),
    loading: vi.fn(),
    custom: vi.fn(),
  }
  return {
    default: api,
    toast: api,
    Toaster: () => null,
  }
})

import api from '@/services/api'

// ─── Helpers ──────────────────────────────────────────────────────────────

function makeAxiosError(status: number, data: unknown): AxiosError {
  const err = new AxiosError('Request failed')
  err.response = {
    status,
    data,
    statusText: '',
    headers: {},
    config: { headers: new AxiosHeaders() },
  }
  err.isAxiosError = true
  return err
}

function rejectingAdapter(status: number, data: unknown) {
  return () => Promise.reject(makeAxiosError(status, data))
}

async function fire(status: number, data: unknown) {
  const originalAdapter = api.defaults.adapter
  api.defaults.adapter = rejectingAdapter(status, data)
  try {
    await expect(api.get('/test')).rejects.toBeDefined()
  } finally {
    api.defaults.adapter = originalAdapter
  }
}

beforeEach(() => {
  toastError.mockReset()
})

// ─── Tests — B-015 interceptor wall-awareness ──────────────────────────────

describe('api response interceptor — B-015 wall-aware pass-through', () => {
  it('does NOT toast for 402 with spec #50 daily_review wall payload', async () => {
    await fire(402, {
      detail: {
        error: 'free_tier_limit',
        trigger: 'daily_review',
        cards_consumed: 15,
        cards_limit: 15,
        resets_at: '2026-04-22T00:00:00+00:00',
      },
    })
    expect(toastError).not.toHaveBeenCalled()
  })

  it('does NOT toast for 402 with any string trigger (generic wall contract)', async () => {
    await fire(402, {
      detail: { trigger: 'interview_limit', cards_consumed: 5 },
    })
    expect(toastError).not.toHaveBeenCalled()
  })

  it('DOES toast for 402 whose detail has no trigger (non-wall payment error)', async () => {
    await fire(402, { detail: 'Payment declined' })
    expect(toastError).toHaveBeenCalledWith('Payment declined')
  })
})

describe('api response interceptor — B-015 object-coercion guard', () => {
  it('never toasts "[object Object]" when detail is a non-wall object', async () => {
    await fire(500, { detail: { something: 'bad happened' } })
    expect(toastError).toHaveBeenCalledTimes(1)
    const message = toastError.mock.calls[0][0]
    expect(message).not.toMatch(/\[object Object\]/)
    expect(typeof message).toBe('string')
    expect((message as string).length).toBeGreaterThan(0)
  })

  it('never toasts "[object Object]" when error field is an object', async () => {
    await fire(400, { error: { code: 'X' } })
    expect(toastError).toHaveBeenCalledTimes(1)
    const message = toastError.mock.calls[0][0]
    expect(message).not.toMatch(/\[object Object\]/)
    expect(typeof message).toBe('string')
  })
})

describe('api response interceptor — existing behaviour preserved', () => {
  it('still toasts string `error` on 500', async () => {
    await fire(500, { error: 'Server exploded' })
    expect(toastError).toHaveBeenCalledWith('Server exploded')
  })

  it('still toasts string `detail` on 400', async () => {
    await fire(400, { detail: 'Bad request body' })
    expect(toastError).toHaveBeenCalledWith('Bad request body')
  })

  it('falls back to error.message when response data has no usable fields', async () => {
    await fire(503, {})
    expect(toastError).toHaveBeenCalledTimes(1)
    const message = toastError.mock.calls[0][0]
    expect(typeof message).toBe('string')
    expect((message as string).length).toBeGreaterThan(0)
  })
})
