import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { MissionOverdueWidget } from '@/components/home/widgets/MissionOverdueWidget'

describe('MissionOverdueWidget', () => {
  it('renders overdue copy and a CTA to /learn/mission', () => {
    const past = new Date()
    past.setUTCDate(past.getUTCDate() - 3)
    const iso = past.toISOString().slice(0, 10)

    render(
      <MemoryRouter>
        <MissionOverdueWidget
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
    expect(screen.getByText(/mission overdue by/i)).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /review mission/i }),
    ).toHaveAttribute('href', '/learn/mission')
  })
})
