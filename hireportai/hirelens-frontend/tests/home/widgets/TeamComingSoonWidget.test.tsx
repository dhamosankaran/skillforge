import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { TeamComingSoonWidget } from '@/components/home/widgets/TeamComingSoonWidget'

function renderWidget() {
  return render(
    <MemoryRouter>
      <TeamComingSoonWidget persona="team_lead" />
    </MemoryRouter>,
  )
}

describe('TeamComingSoonWidget', () => {
  it('renders the coming-soon copy', () => {
    renderWidget()
    expect(
      screen.getByText(/team dashboards are coming in a future release/i),
    ).toBeInTheDocument()
  })

  it('does not render an action (no waitlist component on disk)', () => {
    renderWidget()
    // Scope: only inside the widget. No link, no button.
    const widget = screen.getByTestId('widget-team-coming-soon')
    expect(widget.querySelector('a')).toBeNull()
    expect(widget.querySelector('button')).toBeNull()
  })
})
