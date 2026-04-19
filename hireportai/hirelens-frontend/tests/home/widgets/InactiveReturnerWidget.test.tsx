import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { InactiveReturnerWidget } from '@/components/home/widgets/InactiveReturnerWidget'

describe('InactiveReturnerWidget', () => {
  it('renders welcome copy and a CTA to /learn/daily', () => {
    render(
      <MemoryRouter>
        <InactiveReturnerWidget
          persona="career_climber"
          context={{
            current_streak: 0,
            last_review_at: null,
            active_mission_id: null,
            mission_target_date: null,
            last_scan_date: null,
            plan: 'free',
            last_activity_at: null,
          }}
        />
      </MemoryRouter>,
    )
    expect(
      screen.getByText(/welcome back — your next card is ready/i),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /pick up where you left off/i }),
    ).toHaveAttribute('href', '/learn/daily')
  })
})
