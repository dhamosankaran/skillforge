import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { DeckRollupTable } from '@/components/admin/content-quality/DeckRollupTable'
import type { DeckQualityRow } from '@/types'

function row(overrides: Partial<DeckQualityRow> = {}): DeckQualityRow {
  return {
    deck_id: 'd1',
    deck_slug: 'd1-slug',
    deck_title: 'Deck One',
    tier: 'foundation',
    persona_visibility: 'both',
    archived: false,
    lesson_count: 2,
    review_count_window: 10,
    weighted_pass_rate: 0.5,
    avg_quality_score: 0.6,
    ...overrides,
  }
}

describe('DeckRollupTable', () => {
  it('renders empty state when no decks', () => {
    render(
      <MemoryRouter>
        <DeckRollupTable decks={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('deck-rollup-empty')).toBeInTheDocument()
  })

  it('formats null pass-rate and quality as em-dash', () => {
    render(
      <MemoryRouter>
        <DeckRollupTable
          decks={[
            row({ weighted_pass_rate: null, avg_quality_score: null }),
          ]}
        />
      </MemoryRouter>,
    )
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })

  it('renders archived badge when deck.archived=true', () => {
    render(
      <MemoryRouter>
        <DeckRollupTable decks={[row({ archived: true })]} />
      </MemoryRouter>,
    )
    expect(screen.getByText('(archived)')).toBeInTheDocument()
  })
})
