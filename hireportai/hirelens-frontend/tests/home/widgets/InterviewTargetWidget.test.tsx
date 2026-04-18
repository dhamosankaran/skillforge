import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { InterviewTargetWidget } from '@/components/home/widgets/InterviewTargetWidget'

function renderWidget(props: {
  company: string | null
  date: string | null
}) {
  return render(
    <MemoryRouter>
      <InterviewTargetWidget
        persona="interview_prepper"
        company={props.company}
        date={props.date}
      />
    </MemoryRouter>,
  )
}

describe('InterviewTargetWidget', () => {
  it('shows company + formatted date when both fields are present (no action)', () => {
    renderWidget({ company: 'Google', date: '2026-06-01' })
    expect(screen.getByText('Google')).toBeInTheDocument()
    // formatDate uses locale formatting — month name should be present.
    expect(screen.getByText(/2026/)).toBeInTheDocument()
    // Display-only — no link or button action.
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('renders the empty state when either field is missing', () => {
    renderWidget({ company: null, date: '2026-06-01' })
    expect(
      screen.getByText(/set your interview company in the countdown widget/i),
    ).toBeInTheDocument()
  })
})
