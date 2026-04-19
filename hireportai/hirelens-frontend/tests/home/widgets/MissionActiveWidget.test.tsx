import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { MissionActiveWidget } from '@/components/home/widgets/MissionActiveWidget'

describe('MissionActiveWidget', () => {
  it('renders days-left copy and a CTA to /learn/mission', () => {
    // Use a target date well in the future so days-left is positive.
    const future = new Date()
    future.setUTCDate(future.getUTCDate() + 5)
    const iso = future.toISOString().slice(0, 10)

    render(
      <MemoryRouter>
        <MissionActiveWidget
          persona="interview_prepper"
          context={{
            current_streak: 0,
            last_review_at: null,
            active_mission_id: 'm1',
            mission_target_date: iso,
            last_scan_date: null,
            plan: 'free',
            last_activity_at: null,
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText(/days left in your mission/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open mission/i })).toHaveAttribute(
      'href',
      '/learn/mission',
    )
  })
})
