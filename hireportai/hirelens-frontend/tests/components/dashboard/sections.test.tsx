import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import type {
  CardsDueSection,
  DeckMasterySection,
  RetentionSection,
  ReviewHistorySection,
  StreakSection,
} from '@/types'
import { DueToday } from '@/components/dashboard/DueToday'
import { Streak } from '@/components/dashboard/Streak'
import { RetentionCurve } from '@/components/dashboard/RetentionCurve'
import { DeckMastery } from '@/components/dashboard/DeckMastery'
import { ReviewHistory } from '@/components/dashboard/ReviewHistory'

// Spec: docs/specs/phase-6/09-fsrs-dashboard.md §10.4 — section component
// coverage. Per spec §10 the 5 section components share a single test file
// (one or two tests each); the §10.4 table makes the per-section assertions
// explicit but doesn't mandate 5 separate files.

function withRouter(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>)
}

const cardsDue: CardsDueSection = {
  due_today: 3,
  due_next_7_days: 7,
  due_breakdown_by_state: { new: 2, learning: 1, review: 5, relearning: 0 },
  total_quiz_items_in_progress: 8,
}

const streak: StreakSection = {
  current_streak: 5,
  longest_streak: 10,
  last_active_date: '2026-04-29',
  freezes_available: 1,
  total_xp: 250,
}

const retention: RetentionSection = {
  sample_size: 3,
  overall_recall_rate: 0.667,
  overall_lapse_rate: 0.333,
  daily_retention: [
    { date: '2026-04-27', sample_size: 1, recall_rate: 1.0 },
    { date: '2026-04-28', sample_size: 0, recall_rate: null },
    { date: '2026-04-29', sample_size: 2, recall_rate: 0.5 },
  ],
}

const deckMastery: DeckMasterySection = {
  decks: [
    {
      deck_id: 'd1',
      deck_slug: 'llm-internals',
      deck_title: 'LLM Internals',
      total_quiz_items_visible: 4,
      quiz_items_with_progress: 4,
      quiz_items_mastered: 3,
      mastery_pct: 0.75,
    },
  ],
}

const reviewHistory: ReviewHistorySection = {
  window_days: 30,
  total_in_window: 1,
  recent_reviews: [
    {
      quiz_item_id: 'qi1',
      lesson_id: 'le1',
      lesson_title: 'Tokenization basics',
      deck_slug: 'llm-internals',
      rating: 3,
      fsrs_state_after: 'review',
      reviewed_at: '2026-04-29T12:00:00Z',
    },
  ],
}

describe('DueToday section', () => {
  it('renders due_today + breakdown when populated', () => {
    withRouter(<DueToday data={cardsDue} coldStart={false} />)
    expect(screen.getByTestId('dashboard-cards-due-today')).toHaveTextContent('3')
    expect(screen.getByTestId('dashboard-cards-due-7d')).toHaveTextContent('7')
  })

  it('renders cold-start copy when coldStart=true (D-13)', () => {
    withRouter(<DueToday data={undefined} coldStart={true} />)
    expect(screen.getByTestId('dashboard-cards-due-empty')).toBeInTheDocument()
  })
})

describe('Streak section', () => {
  it('renders streak stats when populated', () => {
    withRouter(<Streak data={streak} coldStart={false} />)
    expect(screen.getByTestId('dashboard-streak-current')).toHaveTextContent('5')
    expect(screen.getByTestId('dashboard-streak-xp')).toHaveTextContent('250')
  })

  it('renders cold-start copy when streak + xp both zero AND coldStart (D-13)', () => {
    const empty: StreakSection = {
      current_streak: 0,
      longest_streak: 0,
      last_active_date: null,
      freezes_available: 0,
      total_xp: 0,
    }
    withRouter(<Streak data={empty} coldStart={true} />)
    expect(screen.getByTestId('dashboard-streak-empty')).toBeInTheDocument()
  })
})

describe('RetentionCurve section', () => {
  it('renders summary + chart when sample_size > 0 (D-4 hand-rolled SVG)', () => {
    withRouter(<RetentionCurve data={retention} coldStart={false} />)
    expect(screen.getByTestId('dashboard-retention-summary')).toHaveTextContent(
      /67% recall/,
    )
    expect(screen.getByTestId('dashboard-retention-chart')).toBeInTheDocument()
  })

  it('renders cold-start copy when sample_size === 0', () => {
    const empty: RetentionSection = {
      sample_size: 0,
      overall_recall_rate: 0,
      overall_lapse_rate: 0,
      daily_retention: [],
    }
    withRouter(<RetentionCurve data={empty} coldStart={true} />)
    expect(screen.getByTestId('dashboard-retention-empty')).toBeInTheDocument()
  })
})

describe('DeckMastery section', () => {
  it('renders one row per deck (sorted upstream by mastery DESC)', () => {
    withRouter(<DeckMastery data={deckMastery} coldStart={false} />)
    expect(
      screen.getByTestId('dashboard-deck-row-llm-internals'),
    ).toBeInTheDocument()
  })

  it('renders cold-start copy when decks list is empty', () => {
    withRouter(<DeckMastery data={{ decks: [] }} coldStart={true} />)
    expect(screen.getByTestId('dashboard-deck-mastery-empty')).toBeInTheDocument()
  })
})

describe('ReviewHistory section', () => {
  it('row navigates to /learn/lesson/<lesson_id> per D-9', () => {
    withRouter(<ReviewHistory data={reviewHistory} coldStart={false} />)
    const row = screen.getByTestId('dashboard-review-row-qi1')
    const link = row.querySelector('a')
    expect(link?.getAttribute('href')).toBe('/learn/lesson/le1')
  })

  it('renders cold-start copy when recent_reviews is empty', () => {
    withRouter(
      <ReviewHistory
        data={{ window_days: 30, total_in_window: 0, recent_reviews: [] }}
        coldStart={true}
      />,
    )
    expect(screen.getByTestId('dashboard-review-history-empty')).toBeInTheDocument()
  })
})
