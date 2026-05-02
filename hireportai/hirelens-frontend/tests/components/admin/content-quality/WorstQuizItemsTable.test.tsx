import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { WorstQuizItemsTable } from '@/components/admin/content-quality/WorstQuizItemsTable'
import type { QuizItemQualityRow } from '@/types'

function row(overrides: Partial<QuizItemQualityRow> = {}): QuizItemQualityRow {
  return {
    quiz_item_id: 'q1',
    lesson_id: 'l1',
    deck_id: 'd1',
    question_preview: 'What is X?',
    review_count_window: 10,
    pass_rate: 0.4,
    lapse_rate: 0.3,
    low_volume: false,
    retired: false,
    // Slice 6.13.5a additions — default empty.
    pass_rate_persisted: null,
    thumbs_aggregate: null,
    thumbs_count: 0,
    ...overrides,
  }
}

describe('WorstQuizItemsTable', () => {
  it('renders empty state when no items', () => {
    render(
      <MemoryRouter>
        <WorstQuizItemsTable items={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('worst-quiz-items-empty')).toBeInTheDocument()
  })

  it('formats null pass and lapse rates as em-dash', () => {
    render(
      <MemoryRouter>
        <WorstQuizItemsTable
          items={[row({ pass_rate: null, lapse_rate: null })]}
        />
      </MemoryRouter>,
    )
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })

  it('renders the question preview in the row', () => {
    render(
      <MemoryRouter>
        <WorstQuizItemsTable
          items={[row({ question_preview: 'Custom question text?' })]}
        />
      </MemoryRouter>,
    )
    expect(
      screen.getByText('Custom question text?'),
    ).toBeInTheDocument()
  })

  // ── Slice 6.13.5a — pass_rate_persisted column ──────────────────────────

  it('renders the persisted pass_rate when present', () => {
    render(
      <MemoryRouter>
        <WorstQuizItemsTable
          items={[
            row({ quiz_item_id: 'qi-persisted', pass_rate_persisted: 0.62 }),
          ]}
        />
      </MemoryRouter>,
    )
    expect(
      screen.getByTestId('pass-rate-persisted-qi-persisted'),
    ).toHaveTextContent('0.62')
  })

  it('renders an em-dash when pass_rate_persisted is null', () => {
    render(
      <MemoryRouter>
        <WorstQuizItemsTable items={[row({ quiz_item_id: 'qi-cold' })]} />
      </MemoryRouter>,
    )
    expect(
      screen.getByTestId('pass-rate-persisted-qi-cold'),
    ).toHaveTextContent('—')
  })
})
