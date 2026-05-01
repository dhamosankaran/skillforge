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
})
