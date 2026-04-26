import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Spec #61 §6 — plan-aware ResumeStaleWidget. Free users are routed to
// PaywallModal (avoiding spec #56 free-tier scan-cap dead-end); Pro
// users keep the original /prep/analyze navigation.

const setShowUpgradeModal = vi.fn()
let mockUsage = {
  setShowUpgradeModal: (show: boolean) => setShowUpgradeModal(show),
}
vi.mock('@/context/UsageContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/UsageContext')>(
      '@/context/UsageContext',
    )
  return {
    ...actual,
    useUsage: () => mockUsage,
  }
})

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

import { ResumeStaleWidget } from '@/components/home/widgets/ResumeStaleWidget'

beforeEach(() => {
  setShowUpgradeModal.mockReset()
  capture.mockReset()
  mockUsage = {
    setShowUpgradeModal: (show: boolean) => setShowUpgradeModal(show),
  }
})

function renderWidget(plan: 'free' | 'pro' | 'enterprise') {
  const past = new Date()
  past.setUTCDate(past.getUTCDate() - 30)
  return render(
    <MemoryRouter>
      <ResumeStaleWidget
        persona="career_climber"
        context={{
          current_streak: 0,
          last_review_at: null,
          active_mission_id: null,
          mission_target_date: null,
          last_scan_date: past.toISOString(),
          plan,
          last_activity_at: null,
        }}
      />
    </MemoryRouter>,
  )
}

describe('ResumeStaleWidget', () => {
  it('renders days-since copy in body for any plan', () => {
    renderWidget('pro')
    expect(screen.getByText(/last scan was/i)).toBeInTheDocument()
  })

  // Spec #61 §6 — Pro path preserved.
  it('Pro user: CTA navigates to /prep/analyze (existing behavior)', () => {
    renderWidget('pro')
    expect(
      screen.getByRole('link', { name: /run a scan/i }),
    ).toHaveAttribute('href', '/prep/analyze')
  })

  // Spec #61 §6 / AC-10 — free-tier dead-end fix.
  // Pre-spec: free user navigated to /prep/analyze and immediately hit
  // the spec #56 lifetime cap (re-scan blocked) — dead-end UX.
  // Post-spec: free user opens PaywallModal via setShowUpgradeModal(true),
  // surfacing the upgrade path as the natural next step.
  it('AC-10 free user: CTA opens UpgradeModal (no href navigation)', () => {
    renderWidget('free')
    const cta = screen.getByRole('button', { name: /re-scan/i })
    expect(cta).toBeInTheDocument()
    fireEvent.click(cta)
    expect(setShowUpgradeModal).toHaveBeenCalledWith(true)
    expect(capture).toHaveBeenCalledWith(
      'home_state_widget_clicked',
      expect.objectContaining({ state: 'resume_stale', cta: 'paywall' }),
    )
  })
})
