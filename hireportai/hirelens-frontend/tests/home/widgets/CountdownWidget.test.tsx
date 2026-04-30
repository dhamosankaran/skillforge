import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { MissionDetailResponse } from '@/types'
import type { NextInterview } from '@/types/homeState'

const fetchActiveMission = vi.fn()
vi.mock('@/services/api', () => ({
  fetchActiveMission: (...args: unknown[]) => fetchActiveMission(...args),
}))

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

// Countdown component is visual — stub so we can assert Mode 2 renders it.
vi.mock('@/components/mission/Countdown', () => ({
  Countdown: ({ daysRemaining }: { daysRemaining: number }) => (
    <div data-testid="countdown-view">{daysRemaining} days</div>
  ),
}))

import { CountdownWidget } from '@/components/home/widgets/CountdownWidget'

function renderWidget(
  nextInterview: NextInterview | null,
  persona: 'interview_prepper' | 'career_climber' | 'team_lead' = 'interview_prepper',
) {
  return render(
    <MemoryRouter>
      <CountdownWidget persona={persona} nextInterview={nextInterview} />
    </MemoryRouter>,
  )
}

function mission(
  overrides: Partial<MissionDetailResponse> = {},
): MissionDetailResponse {
  return {
    id: 'm1',
    title: 'Google',
    target_date: '2026-06-01',
    category_ids: [],
    daily_target: 5,
    total_cards: 50,
    days_remaining: 10,
    status: 'active',
    progress_pct: 20,
    created_at: '2026-04-01T00:00:00Z',
    days: [],
    ...overrides,
  }
}

function isoNDaysAhead(n: number): string {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

beforeEach(() => {
  fetchActiveMission.mockReset()
  capture.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('CountdownWidget — spec #57', () => {
  // ── No-date branch ───────────────────────────────────────────────────────

  it('AC-5 no-date interview_prepper renders the Add-date CTA pointing to /prep/tracker?new=1', () => {
    renderWidget(null)
    expect(
      screen.getByText(/add your interview date to unlock countdown/i),
    ).toBeInTheDocument()
    const cta = screen.getByTestId('countdown-add-date-cta')
    expect(cta).toHaveAttribute('href', '/prep/tracker?new=1')
    // Regression guard: no inline date editor / modal
    expect(screen.queryByTestId('interview-date-modal')).toBeNull()
  })

  it('AC-5 no-date non-interview-prepper persona — widget does not render', () => {
    const { container } = renderWidget(null, 'career_climber')
    expect(container.firstChild).toBeNull()
  })

  it('CTA click fires countdown_widget_add_date_cta_clicked with source=home', async () => {
    const user = userEvent.setup()
    renderWidget(null)
    await user.click(screen.getByTestId('countdown-add-date-cta'))
    expect(capture).toHaveBeenCalledWith(
      'countdown_widget_add_date_cta_clicked',
      { source: 'home' },
    )
  })

  it('renders fires countdown_widget_rendered once with has_date=false', async () => {
    renderWidget(null)
    await waitFor(() =>
      expect(capture).toHaveBeenCalledWith('countdown_widget_rendered', {
        has_date: false,
      }),
    )
    const calls = capture.mock.calls.filter(
      (c) => c[0] === 'countdown_widget_rendered',
    )
    expect(calls).toHaveLength(1)
  })

  // ── Date-present branch ──────────────────────────────────────────────────

  it('AC-5 date-present renders Countdown component + days-until copy with company', async () => {
    fetchActiveMission.mockRejectedValueOnce(new Error('no mission'))
    const ni: NextInterview = {
      date: isoNDaysAhead(14),
      company: 'Google',
      tracker_id: 't-1',
    }
    renderWidget(ni)
    expect(await screen.findByTestId('countdown-view')).toBeInTheDocument()
    expect(screen.getByTestId('countdown-tracker-link')).toHaveAttribute(
      'href',
      '/prep/tracker?focus=t-1',
    )
    expect(screen.getByText(/14 days until Google/i)).toBeInTheDocument()
  })

  it('AC-5 today copy when interview_date === today', () => {
    fetchActiveMission.mockRejectedValueOnce(new Error('no mission'))
    const ni: NextInterview = {
      date: isoNDaysAhead(0),
      company: 'JPMorgan',
      tracker_id: 't-2',
    }
    renderWidget(ni)
    expect(screen.getByText('Today')).toBeInTheDocument()
  })

  it('Mode 2 with no active mission shows "Start a Mission sprint" CTA', async () => {
    fetchActiveMission.mockRejectedValueOnce(new Error('no mission'))
    const ni: NextInterview = {
      date: isoNDaysAhead(14),
      company: 'Google',
      tracker_id: 't-3',
    }
    renderWidget(ni)
    expect(
      await screen.findByRole('link', { name: /start a mission sprint/i }),
    ).toHaveAttribute('href', '/learn/mission')
  })

  it('Mode 2 with active mission shows "View mission" CTA', async () => {
    fetchActiveMission.mockResolvedValueOnce(mission({ status: 'active' }))
    const ni: NextInterview = {
      date: isoNDaysAhead(14),
      company: 'Google',
      tracker_id: 't-4',
    }
    renderWidget(ni)
    expect(
      await screen.findByRole('link', { name: /view mission/i }),
    ).toHaveAttribute('href', '/learn/mission')
  })

  it('renders fires countdown_widget_rendered with has_date=true and days_until', async () => {
    fetchActiveMission.mockRejectedValueOnce(new Error('no mission'))
    const ni: NextInterview = {
      date: isoNDaysAhead(7),
      company: 'Google',
      tracker_id: 't-5',
    }
    renderWidget(ni)
    await waitFor(() => {
      const call = capture.mock.calls.find(
        (c) => c[0] === 'countdown_widget_rendered',
      )
      expect(call).toBeDefined()
      expect(call?.[1]).toMatchObject({ has_date: true, days_until: 7 })
    })
  })
})
