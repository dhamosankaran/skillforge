import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PaywallModal, type PaywallTrigger } from '@/components/PaywallModal'

// ── Mocks ───────────────────────────────────────────────────────────────────

const mockCapture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => mockCapture(...args),
}))

const mockCreateCheckoutSession = vi.fn()
const mockFetchPricing = vi.fn()
const mockDismissPaywall = vi.fn()
vi.mock('@/services/api', () => ({
  createCheckoutSession: (...args: unknown[]) => mockCreateCheckoutSession(...args),
  fetchPricing: (...args: unknown[]) => mockFetchPricing(...args),
  dismissPaywall: (...args: unknown[]) => mockDismissPaywall(...args),
}))

// Stub framer-motion to avoid animation timing issues in tests.
vi.mock('framer-motion', () => ({
  motion: {
    div: ({
      children,
      ...props
    }: React.PropsWithChildren<Record<string, unknown>>) => {
      // Strip motion-specific props so they don't hit the DOM.
      const {
        initial: _i,
        animate: _a,
        exit: _e,
        transition: _t,
        ...rest
      } = props
      return <div {...rest}>{children}</div>
    },
  },
  AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
}))

// ── Helpers ──────────────────────────────────────────────────────────────────

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  trigger: 'scan_limit' as PaywallTrigger,
}

function renderModal(overrides: Partial<typeof defaultProps> = {}) {
  return render(<PaywallModal {...defaultProps} {...overrides} />)
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('PaywallModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCreateCheckoutSession.mockResolvedValue({ url: 'https://checkout.stripe.com/test' })
    mockFetchPricing.mockResolvedValue({
      currency: 'usd',
      price: 49,
      price_display: '$49/mo',
      stripe_price_id: 'price_test',
    })
    mockDismissPaywall.mockResolvedValue({
      logged: true,
      dismissal_id: 'dismissal-1',
      dismissals_in_window: 1,
    })
  })

  it('renders correct headline for each trigger', () => {
    const expected: Record<PaywallTrigger, string> = {
      scan_limit: "You've hit your free scan limit",
      card_limit: 'Unlock the full card library',
      locked_category: 'This category is Pro-only',
      daily_review: 'Daily Review is a Pro feature',
      interview_limit: "You've used your free interview preps",
      skill_gap_study: 'Study skill gaps with flashcards',
      rewrite_limit: 'AI Rewrite is a Pro feature',
      cover_letter_limit: 'Cover letters are a Pro feature',
    }

    for (const [trigger, headline] of Object.entries(expected)) {
      const { unmount } = renderModal({ trigger: trigger as PaywallTrigger })
      expect(screen.getByText(headline)).toBeInTheDocument()
      unmount()
    }
  })

  it('cover_letter_limit renders spec #58 §9 subline copy', () => {
    renderModal({ trigger: 'cover_letter_limit' })
    expect(
      screen.getByText(
        'Upgrade to Pro to generate tailored cover letters, ATS-optimized resume rewrites, and PDF export.',
      ),
    ).toBeInTheDocument()
  })

  it('CTA calls createCheckoutSession', async () => {
    const user = userEvent.setup()

    // Prevent navigation (window.location.href assignment)
    const locationSpy = vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      href: '',
      assign: vi.fn(),
    } as unknown as Location)

    renderModal()

    await user.click(screen.getByRole('button', { name: /upgrade to pro/i }))

    await waitFor(() => {
      expect(mockCreateCheckoutSession).toHaveBeenCalledOnce()
    })

    locationSpy.mockRestore()
  })

  it('shows loading state on click', async () => {
    const user = userEvent.setup()

    // Make checkout hang so we can observe loading state.
    mockCreateCheckoutSession.mockReturnValue(new Promise(() => {}))

    // Prevent navigation
    const locationSpy = vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      href: '',
      assign: vi.fn(),
    } as unknown as Location)

    renderModal()

    await user.click(screen.getByRole('button', { name: /upgrade to pro/i }))

    await waitFor(() => {
      expect(screen.getByText(/starting checkout/i)).toBeInTheDocument()
    })

    locationSpy.mockRestore()
  })

  it('Not now button closes modal', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    renderModal({ onClose })

    await user.click(screen.getByRole('button', { name: /not now/i }))

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledOnce()
    })
  })

  // ─── Spec #42 dismissal wiring ────────────────────────────────────────────

  it('Not now click calls dismissPaywall with the trigger', async () => {
    const user = userEvent.setup()
    renderModal({ trigger: 'daily_review' })

    await user.click(screen.getByRole('button', { name: /not now/i }))

    await waitFor(() => {
      expect(mockDismissPaywall).toHaveBeenCalledWith('daily_review')
    })
  })

  it('Not now click fires paywall_dismissed event with BE window count', async () => {
    const user = userEvent.setup()
    mockDismissPaywall.mockResolvedValueOnce({
      logged: true,
      dismissal_id: 'd-42',
      dismissals_in_window: 2,
    })
    renderModal({ trigger: 'daily_review' })

    await user.click(screen.getByRole('button', { name: /not now/i }))

    await waitFor(() => {
      expect(mockCapture).toHaveBeenCalledWith('paywall_dismissed', {
        trigger: 'daily_review',
        dismissals_in_window: 2,
        action_count_at_dismissal: null,
        will_get_winback: false,
      })
    })
  })

  it('Not now closes modal on dismiss API failure (graceful degradation)', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    mockDismissPaywall.mockRejectedValueOnce(new Error('network down'))

    renderModal({ onClose, trigger: 'daily_review' })

    await user.click(screen.getByRole('button', { name: /not now/i }))

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledOnce()
    })
    expect(errorSpy).toHaveBeenCalled()
    // Event should NOT fire when the API call failed — cleaner analytics.
    const dismissEvent = mockCapture.mock.calls.find(
      (c) => c[0] === 'paywall_dismissed',
    )
    expect(dismissEvent).toBeUndefined()

    errorSpy.mockRestore()
  })

  it('X close button also wires through handleDismiss', async () => {
    const user = userEvent.setup()
    renderModal({ trigger: 'daily_review' })

    await user.click(screen.getByRole('button', { name: /close paywall/i }))

    await waitFor(() => {
      expect(mockDismissPaywall).toHaveBeenCalledWith('daily_review')
    })
  })

  it('fires checkout_started event on CTA click', async () => {
    const user = userEvent.setup()

    // Prevent navigation
    const locationSpy = vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      href: '',
      assign: vi.fn(),
    } as unknown as Location)

    renderModal({ trigger: 'card_limit' })

    await user.click(screen.getByRole('button', { name: /upgrade to pro/i }))

    expect(mockCapture).toHaveBeenCalledWith('checkout_started', {
      trigger: 'card_limit',
      plan: 'pro',
      price: 49,
      currency: 'usd',
    })

    locationSpy.mockRestore()
  })
})
