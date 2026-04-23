import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchMetrics = vi.fn()
const fetchPerf = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchAdminAnalyticsMetrics: (...args: unknown[]) => fetchMetrics(...args),
    fetchAdminAnalyticsPerformance: (...args: unknown[]) => fetchPerf(...args),
  }
})

let mockUser: AuthUser | null = null
vi.mock('@/context/AuthContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/AuthContext')>('@/context/AuthContext')
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      updateUser: vi.fn(),
    }),
  }
})

import AdminAnalytics, { computeFromDate } from '@/pages/AdminAnalytics'

function adminFixture(): AuthUser {
  return {
    id: 'a1',
    email: 'admin@example.com',
    name: 'Admin',
    avatar_url: null,
    role: 'admin',
    persona: 'career_climber',
    onboarding_completed: true,
    interview_target_company: null,
    interview_target_date: null,
    home_first_visit_seen_at: '2026-01-01T00:00:00Z',
  }
}

function userFixture(): AuthUser {
  return { ...adminFixture(), id: 'u1', role: 'user' }
}

function metricsFixture() {
  const tile = {
    current: 100,
    d7_ago: 90,
    d30_ago: 80,
    delta_7d_pct: 11.1,
    delta_30d_pct: 25.0,
  }
  return {
    registered_users: tile,
    paying_pro_users: tile,
    dau_mau_ratio: { ...tile, current: 0.42, d7_ago: 0.4, d30_ago: 0.35 },
    avg_streak_length: tile,
    ats_to_pro_conversion: { ...tile, current: 0.1, d7_ago: 0.08, d30_ago: 0.05 },
    monthly_churn: { ...tile, current: 0.03, d7_ago: 0.04, d30_ago: 0.05 },
    generated_at: '2026-04-23T10:00:00Z',
    from_cache: false,
  }
}

function perfFixture(overrides: Record<string, unknown> = {}) {
  return {
    llm_spend_estimate_usd: 12.34,
    llm_spend_breakdown: { resume_optimize: 12.34 },
    api_latency: [],
    api_latency_available: false,
    error_rate_24h_pct: null,
    error_rate_available: false,
    stripe_webhook_success_24h_pct: null,
    stripe_webhook_available: false,
    generated_at: '2026-04-23T10:00:00Z',
    from_cache: false,
    ...overrides,
  }
}

beforeEach(() => {
  capture.mockReset()
  fetchMetrics.mockReset()
  fetchPerf.mockReset()
  mockUser = adminFixture()
})

describe('AdminAnalytics access gate', () => {
  it('non-admin is redirected to /prep/analyze', async () => {
    mockUser = userFixture()
    fetchMetrics.mockResolvedValue(metricsFixture())
    fetchPerf.mockResolvedValue(perfFixture())
    render(
      <MemoryRouter initialEntries={['/admin/analytics']}>
        <Routes>
          <Route path="/admin/analytics" element={<AdminAnalytics />} />
          <Route path="/prep/analyze" element={<div>analyze page</div>} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('analyze page')).toBeInTheDocument())
    expect(fetchMetrics).not.toHaveBeenCalled()
  })

  it('unauthenticated user is redirected away', async () => {
    mockUser = null
    render(
      <MemoryRouter initialEntries={['/admin/analytics']}>
        <Routes>
          <Route path="/admin/analytics" element={<AdminAnalytics />} />
          <Route path="/prep/analyze" element={<div>analyze page</div>} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('analyze page')).toBeInTheDocument())
  })
})

describe('AdminAnalytics tile rendering', () => {
  it('renders all six OKR tiles + performance tiles including Coming Soon placeholders', async () => {
    fetchMetrics.mockResolvedValue(metricsFixture())
    fetchPerf.mockResolvedValue(perfFixture())
    render(
      <MemoryRouter>
        <AdminAnalytics />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByTestId('metric-tile-Registered users')).toBeInTheDocument()
    })
    for (const label of [
      'Registered users',
      'Paying Pro users',
      'DAU / MAU',
      'Avg streak (days)',
      'ATS → Pro',
      'Monthly churn',
    ]) {
      expect(screen.getByTestId(`metric-tile-${label}`)).toBeInTheDocument()
    }
    // Performance tiles
    expect(screen.getByTestId('perf-tile-llm_spend')).toHaveTextContent('$12.34')
    expect(screen.getByTestId('perf-tile-stripe_webhook')).toHaveTextContent('—')
    // Coming Soon placeholders for deferred fields
    expect(screen.getByTestId('coming-soon-API latency (top 10)')).toBeInTheDocument()
    expect(screen.getByTestId('coming-soon-5xx error rate (24h)')).toBeInTheDocument()
  })

  it('renders stripe webhook percentage when available', async () => {
    fetchMetrics.mockResolvedValue(metricsFixture())
    fetchPerf.mockResolvedValue(
      perfFixture({ stripe_webhook_available: true, stripe_webhook_success_24h_pct: 100 }),
    )
    render(
      <MemoryRouter>
        <AdminAnalytics />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByTestId('perf-tile-stripe_webhook')).toHaveTextContent('100.0%')
    })
  })
})

describe('AdminAnalytics segmented control', () => {
  it('defaults to 30d and re-fetches when segment changes', async () => {
    fetchMetrics.mockResolvedValue(metricsFixture())
    fetchPerf.mockResolvedValue(perfFixture())
    render(
      <MemoryRouter>
        <AdminAnalytics />
      </MemoryRouter>,
    )
    await waitFor(() => expect(fetchMetrics).toHaveBeenCalledTimes(1))
    const thirtyTab = screen.getByTestId('segment-30d')
    expect(thirtyTab).toHaveAttribute('aria-selected', 'true')

    fireEvent.click(screen.getByTestId('segment-7d'))
    await waitFor(() => expect(fetchMetrics).toHaveBeenCalledTimes(2))
    expect(screen.getByTestId('segment-7d')).toHaveAttribute('aria-selected', 'true')
  })
})

describe('computeFromDate', () => {
  const now = new Date('2026-04-23T00:00:00Z')

  it('computes 7d from now', () => {
    expect(computeFromDate('7d', now)).toBe('2026-04-16')
  })
  it('computes 30d from now', () => {
    expect(computeFromDate('30d', now)).toBe('2026-03-24')
  })
  it('computes 90d from now', () => {
    expect(computeFromDate('90d', now)).toBe('2026-01-23')
  })
  it('computes YTD as January 1 of the current year', () => {
    expect(computeFromDate('YTD', now)).toBe('2026-01-01')
  })
})
