/**
 * Spec #67 §8.6 — services/api.ts career-intent helpers.
 * setCareerIntent (POST 201) / getCareerIntent (404 → null) / clearCareerIntent (204).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AxiosHeaders } from 'axios'

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

import api, {
  clearCareerIntent,
  getCareerIntent,
  setCareerIntent,
} from '@/services/api'

describe('career-intent api helpers (spec #67 §8.6)', () => {
  const originalAdapter = api.defaults.adapter

  beforeEach(() => {
    toastError.mockReset()
  })

  afterEach(() => {
    api.defaults.adapter = originalAdapter
  })

  it('setCareerIntent POSTs body to /api/v1/users/me/career-intent and forwards X-Capture-Source', async () => {
    const intent = {
      id: 'intent-1',
      user_id: 'u1',
      target_role: 'staff',
      target_quarter: '2027-Q1',
      created_at: '2026-05-04T00:00:00Z',
      superseded_at: null,
    }
    const adapter = vi.fn().mockResolvedValue({
      status: 201,
      data: intent,
      statusText: 'Created',
      headers: {},
      config: { headers: new AxiosHeaders() },
    })
    api.defaults.adapter = adapter

    const result = await setCareerIntent(
      { target_role: 'staff', target_quarter: '2027-Q1' },
      'persona_picker',
    )

    expect(adapter).toHaveBeenCalledOnce()
    const config = adapter.mock.calls[0][0]
    expect(config.method).toBe('post')
    expect(config.url).toBe('/api/v1/users/me/career-intent')
    expect(JSON.parse(config.data)).toEqual({
      target_role: 'staff',
      target_quarter: '2027-Q1',
    })
    expect(config.headers['X-Capture-Source']).toBe('persona_picker')
    expect(result).toEqual(intent)
  })

  it('getCareerIntent returns null on 404 without toasting (expected no-intent path)', async () => {
    api.defaults.adapter = vi.fn().mockResolvedValue({
      status: 404,
      data: { detail: 'No current career intent' },
      statusText: 'Not Found',
      headers: {},
      config: { headers: new AxiosHeaders() },
    })

    const result = await getCareerIntent()

    expect(result).toBeNull()
    expect(toastError).not.toHaveBeenCalled()
  })

  it('clearCareerIntent DELETEs /api/v1/users/me/career-intent and resolves on 204', async () => {
    const adapter = vi.fn().mockResolvedValue({
      status: 204,
      data: '',
      statusText: 'No Content',
      headers: {},
      config: { headers: new AxiosHeaders() },
    })
    api.defaults.adapter = adapter

    await expect(clearCareerIntent()).resolves.toBeUndefined()
    const config = adapter.mock.calls[0][0]
    expect(config.method).toBe('delete')
    expect(config.url).toBe('/api/v1/users/me/career-intent')
  })
})
