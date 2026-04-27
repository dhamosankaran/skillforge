import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import {
  ConfirmPersonaNarrowingModal,
  computeRemovedPersonas,
} from '@/components/admin/ConfirmPersonaNarrowingModal'

describe('ConfirmPersonaNarrowingModal (D-19 amended de1e9a9)', () => {
  it('renders the locked copy with the persona-array delta', () => {
    render(
      <ConfirmPersonaNarrowingModal
        open
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        removedPersonas={['interview_prepper']}
      />,
    )
    const copy = screen.getByTestId('confirm-persona-narrow-copy')
    expect(copy).toHaveTextContent(
      /Narrowing persona visibility will hide this deck from learners currently in personas interview_prepper\./,
    )
    expect(copy).toHaveTextContent(/FSRS progress on quiz_items in this deck is preserved/)
    // No N-count: copy must reference the array delta, not a learner number.
    expect(copy.textContent).not.toMatch(/\d+ active reviewers/)
  })
})

describe('computeRemovedPersonas (persona-array delta)', () => {
  it('returns the personas removed when narrowing both → climber', () => {
    expect(computeRemovedPersonas('both', 'climber')).toEqual([
      'interview_prepper',
    ])
  })

  it('returns empty array for non-narrowing edits (unchanged or widening)', () => {
    expect(computeRemovedPersonas('both', 'both')).toEqual([])
    expect(computeRemovedPersonas('climber', 'both')).toEqual([])
  })
})
