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

  // ── B-017 empty-state copy: three-case split ──────────────────────────
  // Pre-B-017 the widget emitted one copy string that pointed at a
  // non-existent Countdown company field. Post-B-017 the copy picks the
  // branch that matches the actual gap; the date-missing branch is the
  // only one that points at another widget (Countdown does capture date).

  it('empty: "No interview target set yet." when both company and date are missing', () => {
    renderWidget({ company: null, date: null })
    expect(
      screen.getByText(/^no interview target set yet\.?$/i),
    ).toBeInTheDocument()
    // Regression guard: the old dead copy must not appear anywhere.
    expect(
      screen.queryByText(/set your interview company in the countdown widget/i),
    ).toBeNull()
  })

  it('empty: "No interview company set yet." when company missing but date set', () => {
    renderWidget({ company: null, date: '2026-06-01' })
    expect(
      screen.getByText(/^no interview company set yet\.?$/i),
    ).toBeInTheDocument()
  })

  it('empty: "Set your interview date in the Countdown widget below." when date missing but company set', () => {
    renderWidget({ company: 'Google', date: null })
    expect(
      screen.getByText(/set your interview date in the countdown widget/i),
    ).toBeInTheDocument()
  })
})
