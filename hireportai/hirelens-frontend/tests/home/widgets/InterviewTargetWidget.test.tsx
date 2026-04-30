import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { InterviewTargetWidget } from '@/components/home/widgets/InterviewTargetWidget'
import type { NextInterview } from '@/types/homeState'

function renderWidget(nextInterview: NextInterview | null) {
  return render(
    <MemoryRouter>
      <InterviewTargetWidget
        persona="interview_prepper"
        nextInterview={nextInterview}
      />
    </MemoryRouter>,
  )
}

describe('InterviewTargetWidget — spec #57', () => {
  it('shows company + formatted date when nextInterview is set', () => {
    renderWidget({ date: '2026-06-01', company: 'Google', tracker_id: 't-1' })
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText(/2026/)).toBeInTheDocument()
    // Display-only — no link or button action.
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('empty: shows generic empty-state message when nextInterview is null', () => {
    renderWidget(null)
    expect(
      screen.getByText(/no upcoming interview scheduled/i),
    ).toBeInTheDocument()
    // Regression guard: pre-spec-57 partial-set strings no longer apply.
    expect(
      screen.queryByText(/set your interview date in the countdown widget/i),
    ).toBeNull()
    expect(
      screen.queryByText(/no interview company set yet/i),
    ).toBeNull()
  })
})
