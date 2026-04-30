import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

import { MissionDateGate } from '@/components/mission/MissionDateGate'

function renderGate() {
  return render(
    <MemoryRouter>
      <MissionDateGate />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  navigate.mockReset()
})

describe('MissionDateGate (spec #57 AC-6 — CTA target amended)', () => {
  it('renders the LD-3 copy and both CTAs (AC-4)', () => {
    renderGate()
    expect(screen.getByTestId('mission-date-gate')).toBeInTheDocument()
    expect(
      screen.getByText(/set a date to start a sprint/i),
    ).toBeInTheDocument()
    expect(screen.getByTestId('mission-date-gate-add-date')).toBeInTheDocument()
    expect(screen.getByTestId('mission-date-gate-browse')).toBeInTheDocument()
  })

  it('fires countdown_unlock_cta_shown once on mount (mission_mode surface, preserved per spec #57 §7.3)', async () => {
    renderGate()
    await waitFor(() =>
      expect(capture).toHaveBeenCalledWith('countdown_unlock_cta_shown', {
        surface: 'mission_mode',
      }),
    )
    const shownCalls = capture.mock.calls.filter(
      (c) => c[0] === 'countdown_unlock_cta_shown',
    )
    expect(shownCalls).toHaveLength(1)
  })

  it('Add-date click fires preserved + new events and navigates to /prep/tracker?new=1', async () => {
    const user = userEvent.setup()
    renderGate()
    await user.click(screen.getByTestId('mission-date-gate-add-date'))
    expect(capture).toHaveBeenCalledWith('countdown_unlock_cta_clicked', {
      surface: 'mission_mode',
    })
    expect(capture).toHaveBeenCalledWith(
      'countdown_widget_add_date_cta_clicked',
      { source: 'mission_gate' },
    )
    expect(navigate).toHaveBeenCalledWith('/prep/tracker?new=1')
    // Regression guard: must NOT route through PersonaPicker.
    expect(navigate).not.toHaveBeenCalledWith(
      expect.stringContaining('/onboarding/persona'),
    )
  })

  it('Browse-categories click navigates to /learn (no analytics event)', async () => {
    const user = userEvent.setup()
    renderGate()
    await user.click(screen.getByTestId('mission-date-gate-browse'))
    expect(navigate).toHaveBeenCalledWith('/learn')
    const clickedCalls = capture.mock.calls.filter(
      (c) => c[0] === 'countdown_unlock_cta_clicked',
    )
    expect(clickedCalls).toHaveLength(0)
  })
})
