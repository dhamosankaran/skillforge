import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

import { WallInlineNudge } from '@/components/study/WallInlineNudge'

function renderNudge() {
  return render(
    <MemoryRouter>
      <WallInlineNudge trigger="daily_review" />
    </MemoryRouter>,
  )
}

describe('WallInlineNudge (spec #42 §5.4 / LD-6)', () => {
  beforeEach(() => {
    capture.mockReset()
  })

  it('renders the locked LD-6 copy verbatim', () => {
    renderNudge()
    // LD-6 copy: "This is a Pro feature — upgrade anytime from Profile"
    const nudge = screen.getByTestId('wall-inline-nudge')
    expect(nudge).toHaveTextContent(
      /This is a Pro feature — upgrade anytime from Profile/i,
    )
  })

  it('upgrade link navigates to /pricing', () => {
    renderNudge()
    const link = screen.getByRole('link', { name: /upgrade/i })
    expect(link).toHaveAttribute('href', '/pricing')
  })

  it('fires inline_nudge_shown PostHog event on mount with trigger', () => {
    renderNudge()
    expect(capture).toHaveBeenCalledTimes(1)
    expect(capture).toHaveBeenCalledWith('inline_nudge_shown', {
      trigger: 'daily_review',
    })
  })

  it('does NOT fire paywall_hit on mount (LD-6 — silent denominator guard)', () => {
    renderNudge()
    const paywallHitCall = capture.mock.calls.find(
      (c) => c[0] === 'paywall_hit',
    )
    expect(paywallHitCall).toBeUndefined()
  })
})
