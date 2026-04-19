import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { FirstSessionDoneWidget } from '@/components/home/widgets/FirstSessionDoneWidget'

describe('FirstSessionDoneWidget', () => {
  it('renders first-session copy and a CTA to /learn/daily', () => {
    render(
      <MemoryRouter>
        <FirstSessionDoneWidget
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
    expect(screen.getByText(/great first session/i)).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /keep going/i }),
    ).toHaveAttribute('href', '/learn/daily')
  })
})
