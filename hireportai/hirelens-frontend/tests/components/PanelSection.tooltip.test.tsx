import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { Info } from 'lucide-react'
import { PanelSection } from '@/components/dashboard/PanelSection'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const TOOLTIP = {
  what: 'What this means: JD-to-resume match strength.',
  how: 'How to act: aim for 75+.',
  why: 'Why it matters: filters below a cutoff.',
}

beforeEach(() => {
  capture.mockReset()
})

describe('PanelSection tooltip — AC-3/4/5/6/7', () => {
  it('test_info_icon_absent_when_tooltip_prop_absent', () => {
    render(
      <PanelSection title="X" icon={Info}>
        <div>body</div>
      </PanelSection>,
    )
    expect(screen.queryByRole('button', { name: /info:/i })).toBeNull()
  })

  it('test_info_icon_renders_and_is_focusable_when_tooltip_provided', async () => {
    render(
      <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
        <div>body</div>
      </PanelSection>,
    )
    const trigger = screen.getByRole('button', { name: /info: ats score/i })
    expect(trigger).toBeInTheDocument()
    // Native <button> is tabbable by default; spec requires keyboard-reachable via Tab.
    expect(trigger.tagName).toBe('BUTTON')
    // Should not have tabindex=-1
    expect(trigger.getAttribute('tabindex')).not.toBe('-1')
  })

  it('test_tooltip_opens_on_click_and_shows_copy', async () => {
    const user = userEvent.setup()
    render(
      <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
        <div>body</div>
      </PanelSection>,
    )
    await user.click(screen.getByRole('button', { name: /info: ats score/i }))
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    expect(screen.getByText(/JD-to-resume match strength/i)).toBeInTheDocument()
    expect(screen.getByText(/aim for 75\+/i)).toBeInTheDocument()
    expect(screen.getByText(/filters below a cutoff/i)).toBeInTheDocument()
  })

  it('test_tooltip_opens_on_enter_key', async () => {
    const user = userEvent.setup()
    render(
      <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
        <div>body</div>
      </PanelSection>,
    )
    const trigger = screen.getByRole('button', { name: /info: ats score/i })
    trigger.focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
  })

  it('test_tooltip_closes_on_escape_and_returns_focus_to_trigger', async () => {
    const user = userEvent.setup()
    render(
      <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
        <div>body</div>
      </PanelSection>,
    )
    const trigger = screen.getByRole('button', { name: /info: ats score/i })
    await user.click(trigger)
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('tooltip')).toBeNull()
    expect(document.activeElement).toBe(trigger)
  })

  it('test_tooltip_closes_on_click_outside', async () => {
    const user = userEvent.setup()
    render(
      <div>
        <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
          <div>body</div>
        </PanelSection>
        <button>outside</button>
      </div>,
    )
    await user.click(screen.getByRole('button', { name: /info: ats score/i }))
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'outside' }))
    expect(screen.queryByRole('tooltip')).toBeNull()
  })

  it('test_tooltip_has_correct_aria_attributes', async () => {
    const user = userEvent.setup()
    render(
      <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
        <div>body</div>
      </PanelSection>,
    )
    const trigger = screen.getByRole('button', { name: /info: ats score/i })
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    await user.click(trigger)
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    const tooltip = screen.getByRole('tooltip')
    const tooltipId = tooltip.getAttribute('id')
    expect(tooltipId).toBeTruthy()
    expect(trigger.getAttribute('aria-describedby')).toBe(tooltipId)
  })

  it('test_tooltip_fires_results_tooltip_opened_with_section_id', async () => {
    const user = userEvent.setup()
    render(
      <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
        <div>body</div>
      </PanelSection>,
    )
    await user.click(screen.getByRole('button', { name: /info: ats score/i }))
    expect(capture).toHaveBeenCalledWith('results_tooltip_opened', { section: 'ats_score' })
  })

  it('test_tooltip_does_not_fire_close_event', async () => {
    const user = userEvent.setup()
    render(
      <PanelSection title="ATS Score" icon={Info} tooltip={TOOLTIP} section="ats_score">
        <div>body</div>
      </PanelSection>,
    )
    const trigger = screen.getByRole('button', { name: /info: ats score/i })
    await user.click(trigger)
    await user.keyboard('{Escape}')
    // Exactly one call: the open. No close event.
    expect(capture).toHaveBeenCalledTimes(1)
    expect(capture).not.toHaveBeenCalledWith('results_tooltip_closed', expect.anything())
  })

  it('test_tooltip_does_not_fire_when_reopened_without_section', async () => {
    const user = userEvent.setup()
    render(
      <PanelSection title="Misc" icon={Info} tooltip={TOOLTIP}>
        <div>body</div>
      </PanelSection>,
    )
    await user.click(screen.getByRole('button', { name: /info: misc/i }))
    // section is optional; if absent, no analytics event
    expect(capture).not.toHaveBeenCalled()
  })
})
