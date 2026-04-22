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

describe('MissionDateGate (spec #53 §7.3)', () => {
  it('renders the LD-3 copy and both CTAs (AC-4)', () => {
    renderGate()
    expect(screen.getByTestId('mission-date-gate')).toBeInTheDocument()
    expect(
      screen.getByText(/set a date to start a sprint/i),
    ).toBeInTheDocument()
    expect(screen.getByTestId('mission-date-gate-add-date')).toBeInTheDocument()
    expect(screen.getByTestId('mission-date-gate-browse')).toBeInTheDocument()
  })

  it('fires countdown_unlock_cta_shown once on mount (mission_mode surface)', async () => {
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

  it('Add-date click fires clicked event + navigates to PersonaPicker with return_to=/learn/mission', async () => {
    const user = userEvent.setup()
    renderGate()
    await user.click(screen.getByTestId('mission-date-gate-add-date'))
    expect(capture).toHaveBeenCalledWith('countdown_unlock_cta_clicked', {
      surface: 'mission_mode',
    })
    expect(navigate).toHaveBeenCalledWith(
      '/onboarding/persona?return_to=%2Flearn%2Fmission',
    )
  })

  it('Browse-categories click navigates to /learn (no analytics event)', async () => {
    const user = userEvent.setup()
    renderGate()
    await user.click(screen.getByTestId('mission-date-gate-browse'))
    expect(navigate).toHaveBeenCalledWith('/learn')
    // No unlock_cta_clicked fire on the secondary path.
    const clickedCalls = capture.mock.calls.filter(
      (c) => c[0] === 'countdown_unlock_cta_clicked',
    )
    expect(clickedCalls).toHaveLength(0)
  })
})
