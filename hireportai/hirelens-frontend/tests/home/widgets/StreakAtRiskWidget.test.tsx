import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { StreakAtRiskWidget } from '@/components/home/widgets/StreakAtRiskWidget'

describe('StreakAtRiskWidget', () => {
  it('shows streak length and links to /learn/daily', () => {
    render(
      <MemoryRouter>
        <StreakAtRiskWidget
          persona="career_climber"
          context={{
            current_streak: 7,
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
    expect(screen.getByText(/your 7-day streak is at risk/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /review now/i })).toHaveAttribute(
      'href',
      '/learn/daily',
    )
  })
})
