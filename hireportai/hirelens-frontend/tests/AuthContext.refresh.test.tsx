/**
 * AuthContext — refreshUser (B-118).
 *
 * Covers scout cluster #6/#8/#17/#18/#20: post-Stripe-redirect cached
 * user staleness. refreshUser() re-fetches /auth/me and updates the
 * context user; concurrent calls dedupe via inflight-promise ref.
 */
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import {
  AuthProvider,
  STORAGE_KEY_ACCESS,
  useAuth,
  type AuthUser,
} from '@/context/AuthContext'

vi.mock('axios')
const mockedGet = axios.get as unknown as ReturnType<typeof vi.fn>

function makeUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: 'career_climber',
    onboarding_completed: true,
    ...overrides,
  }
}

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
)

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem(STORAGE_KEY_ACCESS, 'tok-1')
  mockedGet.mockReset()
})

afterEach(() => {
  localStorage.clear()
})

describe('AuthContext.refreshUser', () => {
  it('re-fetches /auth/me and updates the context user', async () => {
    const initial = makeUser({
      subscription: {
        plan: 'free',
        status: 'active',
        current_period_end: null,
        cancel_at_period_end: false,
      },
    })
    const refreshed = makeUser({
      subscription: {
        plan: 'pro',
        status: 'active',
        current_period_end: '2026-06-03 00:00:00',
        cancel_at_period_end: false,
      },
    })
    mockedGet
      .mockResolvedValueOnce({ data: initial })
      .mockResolvedValueOnce({ data: refreshed })

    const { result } = renderHook(() => useAuth(), { wrapper })
    await waitFor(() => expect(result.current.user?.subscription?.plan).toBe('free'))

    await act(async () => {
      await result.current.refreshUser()
    })

    expect(result.current.user?.subscription?.plan).toBe('pro')
    expect(result.current.user?.subscription?.current_period_end).toBe(
      '2026-06-03 00:00:00',
    )
    // Hydration + one explicit refresh = 2 calls.
    expect(mockedGet).toHaveBeenCalledTimes(2)
  })

  it('dedupes concurrent refreshUser calls (single in-flight /auth/me)', async () => {
    mockedGet.mockResolvedValue({ data: makeUser() })

    const { result } = renderHook(() => useAuth(), { wrapper })
    await waitFor(() => expect(result.current.user).not.toBeNull())
    mockedGet.mockClear()

    // Fire two refresh calls before the first resolves.
    let p1: Promise<void> | undefined
    let p2: Promise<void> | undefined
    await act(async () => {
      p1 = result.current.refreshUser()
      p2 = result.current.refreshUser()
      await Promise.all([p1, p2])
    })

    // Only one network call — second call rode the inflight promise.
    expect(mockedGet).toHaveBeenCalledTimes(1)
  })

  it('is a no-op when no access token is stored', async () => {
    mockedGet.mockResolvedValue({ data: makeUser() })
    localStorage.removeItem(STORAGE_KEY_ACCESS)

    const { result } = renderHook(() => useAuth(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(mockedGet).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.refreshUser()
    })

    expect(mockedGet).not.toHaveBeenCalled()
    expect(result.current.user).toBeNull()
  })

  it('swallows refresh errors so callers can fire-and-forget', async () => {
    mockedGet
      .mockResolvedValueOnce({ data: makeUser() })
      .mockRejectedValueOnce(new Error('network down'))

    const { result } = renderHook(() => useAuth(), { wrapper })
    await waitFor(() => expect(result.current.user).not.toBeNull())

    await expect(
      act(async () => {
        await result.current.refreshUser()
      }),
    ).resolves.not.toThrow()

    // Cached user from hydration is preserved on refresh failure.
    expect(result.current.user?.id).toBe('u1')
  })
})
