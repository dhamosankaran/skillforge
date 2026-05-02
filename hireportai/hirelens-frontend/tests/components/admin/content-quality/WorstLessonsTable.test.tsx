import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { WorstLessonsTable } from '@/components/admin/content-quality/WorstLessonsTable'
import type { LessonQualityRow } from '@/types'

function row(overrides: Partial<LessonQualityRow> = {}): LessonQualityRow {
  return {
    lesson_id: 'l1',
    lesson_slug: 'lesson-1',
    lesson_title: 'Lesson 1',
    deck_id: 'd1',
    deck_slug: 'deck-1',
    review_count_window: 12,
    view_count_window: 30,
    pass_rate: 0.5,
    smoothed_quality_score: 0.55,
    persisted_quality_score: 0.55,
    low_volume: false,
    archived: false,
    published_at: '2026-04-01T00:00:00Z',
    // Slice 6.13.5a additions — default to empty per AC-13 / AC-14.
    critique_scores: null,
    thumbs_aggregate: null,
    thumbs_count: 0,
    ...overrides,
  }
}

describe('WorstLessonsTable', () => {
  it('renders empty state when no lessons', () => {
    render(
      <MemoryRouter>
        <WorstLessonsTable lessons={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('worst-lessons-empty')).toBeInTheDocument()
  })

  it('renders the low-volume tag when row.low_volume=true', () => {
    render(
      <MemoryRouter>
        <WorstLessonsTable
          lessons={[
            row({
              lesson_slug: 'low',
              low_volume: true,
              smoothed_quality_score: null,
            }),
          ]}
        />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('low-volume-low')).toBeInTheDocument()
  })

  it('renders rows in the order received (caller pre-sorts)', () => {
    render(
      <MemoryRouter>
        <WorstLessonsTable
          lessons={[
            row({
              lesson_id: 'first',
              lesson_slug: 'first',
              lesson_title: 'First',
            }),
            row({
              lesson_id: 'second',
              lesson_slug: 'second',
              lesson_title: 'Second',
            }),
          ]}
        />
      </MemoryRouter>,
    )
    const rows = screen.getAllByRole('button')
    expect(rows[0]).toHaveTextContent('First')
    expect(rows[1]).toHaveTextContent('Second')
  })

  // ── Slice 6.13.5a — critique_scores column (AC-13) ──────────────────────

  it('renders the critique_scores column when scores are present', () => {
    render(
      <MemoryRouter>
        <WorstLessonsTable
          lessons={[
            row({
              lesson_slug: 'with-critique',
              critique_scores: {
                accuracy: 0.8,
                clarity: 0.6,
              },
            }),
          ]}
        />
      </MemoryRouter>,
    )
    const cell = screen.getByTestId('critique-scores-with-critique')
    expect(cell).toHaveTextContent('A 0.80')
    expect(cell).toHaveTextContent('C 0.60')
  })

  it('renders an em-dash when critique_scores is null', () => {
    render(
      <MemoryRouter>
        <WorstLessonsTable
          lessons={[
            row({
              lesson_slug: 'cold',
              critique_scores: null,
            }),
          ]}
        />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('critique-scores-cold')).toHaveTextContent('—')
  })
})
