import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { ResumeStaleWidget } from '@/components/home/widgets/ResumeStaleWidget'

describe('ResumeStaleWidget', () => {
  it('renders days-since copy and a CTA to /prep/analyze', () => {
    const past = new Date()
    past.setUTCDate(past.getUTCDate() - 30)

    render(
      <MemoryRouter>
        <ResumeStaleWidget
          persona="career_climber"
          context={{
            current_streak: 0,
            last_review_at: null,
            active_mission_id: null,
            mission_target_date: null,
            last_scan_date: past.toISOString(),
            plan: 'free',
            last_activity_at: null,
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText(/last scan was/i)).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /run a scan/i }),
    ).toHaveAttribute('href', '/prep/analyze')
  })
})
