import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AxiosError, AxiosHeaders } from 'axios'

// ─── Mocks ────────────────────────────────────────────────────────────────

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const submitReview = vi.fn()
const createCheckoutSession = vi.fn()
const fetchPricing = vi.fn()
const submitCardFeedback = vi.fn()

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    submitReview: (...args: unknown[]) => submitReview(...args),
    createCheckoutSession: (...args: unknown[]) => createCheckoutSession(...args),
    fetchPricing: (...args: unknown[]) => fetchPricing(...args),
    submitCardFeedback: (...args: unknown[]) => submitCardFeedback(...args),
  }
})

import { QuizPanel } from '@/components/study/QuizPanel'

// ─── Helpers ──────────────────────────────────────────────────────────────

function makeAxios402(resetsAt: string): AxiosError {
  const err = new AxiosError('Payment required')
  err.response = {
    status: 402,
    data: {
      detail: {
        error: 'free_tier_limit',
        trigger: 'daily_review',
        cards_consumed: 15,
        cards_limit: 15,
        resets_at: resetsAt,
      },
    },
    statusText: 'Payment Required',
    headers: {},
    config: { headers: new AxiosHeaders() },
  }
  err.isAxiosError = true
  return err
}

function renderQuiz() {
  return render(
    <QuizPanel
      cardId="card-1"
      question="Q?"
      answer="A."
      sessionId="sess-1"
      startTimeMs={Date.now()}
      onRated={vi.fn()}
    />,
  )
}

async function triggerWalledSubmit(resetsAt: string) {
  const user = userEvent.setup()
  submitReview.mockRejectedValueOnce(makeAxios402(resetsAt))
  await user.click(screen.getByRole('button', { name: /Reveal Answer/i }))
  await user.click(screen.getByRole('button', { name: /Good/i }))
}

beforeEach(() => {
  capture.mockReset()
  submitReview.mockReset()
  createCheckoutSession.mockReset()
  fetchPricing.mockReset()
  submitCardFeedback.mockReset()
  fetchPricing.mockResolvedValue({
    currency: 'usd',
    price: 49,
    price_display: '$49/mo',
    stripe_price_id: 'price_123',
  })
})

afterEach(() => {
  vi.useRealTimers()
})

// ─── Tests ────────────────────────────────────────────────────────────────

describe('Daily-card review wall — frontend (spec #50)', () => {
  // FE-1 — AC-7
  it('test_paywall_modal_renders_on_402_with_daily_review_trigger', async () => {
    renderQuiz()
    const resetsAt = new Date(Date.now() + 3 * 3600 * 1000).toISOString()
    await triggerWalledSubmit(resetsAt)

    // Modal opens with daily_review copy
    await waitFor(() =>
      expect(screen.getByText(/Daily Review is a Pro feature/i)).toBeInTheDocument(),
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    // Upgrade CTA from existing modal
    expect(
      screen.getByRole('button', { name: /Upgrade to Pro/i }),
    ).toBeInTheDocument()
  })

  // FE-2 — §UI/UX relative format
  // No fake timers: userEvent and vi.useFakeTimers don't mix without
  // `advanceTimers`, so we pin the target relative to Date.now() instead.
  it('test_modal_shows_resets_at_time_in_relative_format', async () => {
    renderQuiz()
    // ~4h 17m from now — safely inside the "≤12h → relative" window
    const resetsAt = new Date(
      Date.now() + 4 * 3600_000 + 17 * 60_000,
    ).toISOString()
    await triggerWalledSubmit(resetsAt)

    await waitFor(() =>
      expect(screen.getByTestId('wall-resets-label').textContent).toMatch(
        /^Resets in \d+h \d+m$/,
      ),
    )
  })

  // FE-3 — §UI/UX absolute format (>12h)
  it('test_modal_shows_resets_at_time_in_absolute_format_for_long_waits', async () => {
    renderQuiz()
    // 20h from now → above 12h threshold → absolute format
    const resetsAt = new Date(Date.now() + 20 * 3600_000).toISOString()
    await triggerWalledSubmit(resetsAt)

    await waitFor(() => {
      const label = screen.getByTestId('wall-resets-label').textContent ?? ''
      expect(label).toMatch(/^Resets at /i)
      expect(label).not.toMatch(/Resets in/i)
    })
  })

  // FE-4 — CTA smoke (existing Stripe flow)
  it('test_upgrade_cta_routes_to_existing_stripe_flow', async () => {
    const user = userEvent.setup()
    createCheckoutSession.mockResolvedValue({ url: 'https://checkout.stripe.com/x' })
    // Stub window.location so the redirect assignment doesn't throw in JSDOM
    const originalLocation = window.location
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...originalLocation, href: '' },
    })

    renderQuiz()
    await triggerWalledSubmit(new Date(Date.now() + 3600_000).toISOString())

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Upgrade to Pro/i })).toBeInTheDocument(),
    )
    await user.click(screen.getByRole('button', { name: /Upgrade to Pro/i }))
    expect(createCheckoutSession).toHaveBeenCalledWith('usd')

    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    })
  })

  // FE-5 — AC-10 (FE)
  it('test_daily_card_wall_hit_fires_on_modal_open', async () => {
    renderQuiz()
    // 5h 30m from now; hours rounded-toward-zero = 5
    const resetsAt = new Date(Date.now() + 5 * 3600_000 + 30 * 60_000).toISOString()
    await triggerWalledSubmit(resetsAt)

    await waitFor(() => {
      const wallHitCall = capture.mock.calls.find(
        (c) => c[0] === 'daily_card_wall_hit',
      )
      expect(wallHitCall).toBeTruthy()
      expect(wallHitCall![1]).toEqual({ resets_at_hours_from_now: 5 })
    })
  })
})
