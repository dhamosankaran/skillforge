/**
 * Pricing — cancel-pending Pro tile + Reactivate path (B-117).
 *
 * Covers scout findings #14 (Pro tile shows "Cancels [date]" when
 * cancel_at_period_end=true) and #15 (handleCta opens billing portal
 * instead of attempting checkout, sidestepping B-113 AlreadyProError).
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const createCheckoutSession = vi.fn()
const createBillingPortalSession = vi.fn()
vi.mock('@/services/api', () => ({
  default: { get: vi.fn() },
  createCheckoutSession: (...args: unknown[]) => createCheckoutSession(...args),
  createBillingPortalSession: (...args: unknown[]) => createBillingPortalSession(...args),
}))

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

let mockUser: AuthUser = makeUser()
const refreshUser = vi.fn()
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: mockUser, isLoading: false, signIn: vi.fn(), signOut: vi.fn(), updateUser: vi.fn(), refreshUser }),
}))

let mockPlan: 'pro' | 'free' = 'pro'
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: mockPlan },
    upgradePlan: vi.fn(),
  }),
}))

vi.mock('@/hooks/usePricing', () => ({
  usePricing: () => ({
    pricing: { currency: 'usd', price: 19, price_display: '$19', stripe_price_id: 'price_test' },
    isLoading: false,
  }),
}))

vi.mock('@/components/layout/PageWrapper', () => ({
  PageWrapper: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import Pricing from '@/pages/Pricing'

function renderPricing() {
  return render(
    <MemoryRouter>
      <Pricing />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  createCheckoutSession.mockReset()
  createBillingPortalSession.mockReset()
  refreshUser.mockReset()
  mockUser = makeUser()
  mockPlan = 'pro'
})

describe('Pricing — cancel-pending Pro tile (B-117 #14)', () => {
  it('shows "Cancels <date>" badge on the Pro tile when cancel_at_period_end is true', () => {
    mockUser = makeUser({
      subscription: {
        plan: 'pro',
        status: 'active',
        current_period_end: '2026-04-22 00:00:00',
        cancel_at_period_end: true,
      },
    })

    renderPricing()

    // The badge sits on the Pro card (not on the page-header text).
    expect(screen.getByText(/cancels/i)).toBeInTheDocument()
    expect(screen.getByText(/2026/)).toBeInTheDocument()
    // CTA flips to "Reactivate" rather than the disabled "Currently Active".
    expect(screen.getByRole('button', { name: /reactivate/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /currently active/i })).not.toBeInTheDocument()
  })

  it('shows "Currently Active" on the Pro tile when not cancel-pending', () => {
    mockUser = makeUser({
      subscription: {
        plan: 'pro',
        status: 'active',
        current_period_end: null,
        cancel_at_period_end: false,
      },
    })

    renderPricing()

    expect(screen.getByRole('button', { name: /currently active/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reactivate/i })).not.toBeInTheDocument()
  })
})

describe('Pricing — post-checkout return refreshes user (B-118)', () => {
  it('fires refreshUser when ?upgrade=success lands from Stripe', async () => {
    mockPlan = 'free'
    mockUser = makeUser()
    render(
      <MemoryRouter initialEntries={['/pricing?upgrade=success&session_id=cs_test']}>
        <Pricing />
      </MemoryRouter>,
    )
    await waitFor(() => expect(refreshUser).toHaveBeenCalledTimes(1))
  })

  it('does NOT fire refreshUser on a plain /pricing visit', async () => {
    renderPricing()
    // Allow the post-mount effect a tick to run.
    await waitFor(() => {
      expect(refreshUser).not.toHaveBeenCalled()
    })
  })
})

describe('Pricing — handleCta cancel-pending → portal redirect (B-117 #15)', () => {
  it('opens the billing portal instead of checkout when cancel_at_period_end is true', async () => {
    mockUser = makeUser({
      subscription: {
        plan: 'pro',
        status: 'active',
        current_period_end: '2026-04-22 00:00:00',
        cancel_at_period_end: true,
      },
    })
    createBillingPortalSession.mockResolvedValue({
      url: 'https://billing.stripe.com/p/session/bps_reactivate_from_pricing',
    })

    const originalLocation = window.location
    // @ts-expect-error — deleting for test override
    delete window.location
    // @ts-expect-error — plain replacement
    window.location = { href: '' } as Location

    try {
      renderPricing()
      const reactivateBtn = screen.getByRole('button', { name: /reactivate/i })
      await userEvent.click(reactivateBtn)

      await waitFor(() => {
        expect(createBillingPortalSession).toHaveBeenCalledTimes(1)
      })
      // Critical: checkout NOT called — that would hit B-113 AlreadyProError.
      expect(createCheckoutSession).not.toHaveBeenCalled()
      expect(window.location.href).toBe(
        'https://billing.stripe.com/p/session/bps_reactivate_from_pricing',
      )
      expect(capture).toHaveBeenCalledWith('subscription_portal_opened', {
        source: 'pricing_reactivate',
      })
    } finally {
      // @ts-expect-error — restoring
      window.location = originalLocation
    }
  })
})
