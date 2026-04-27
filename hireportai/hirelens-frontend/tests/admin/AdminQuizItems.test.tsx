import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { QuizItem } from '@/types'

const adminListQuizItems = vi.fn()
const adminCreateQuizItem = vi.fn()
const adminRetireQuizItem = vi.fn()
const captureMock = vi.fn()

vi.mock('@/services/api', () => ({
  adminListQuizItems: (...args: unknown[]) => adminListQuizItems(...args),
  adminCreateQuizItem: (...args: unknown[]) => adminCreateQuizItem(...args),
  adminUpdateQuizItem: vi.fn(),
  adminRetireQuizItem: (...args: unknown[]) => adminRetireQuizItem(...args),
}))
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => captureMock(...args),
}))

import AdminQuizItems from '@/pages/admin/AdminQuizItems'

function quizItem(overrides: Partial<QuizItem> = {}): QuizItem {
  return {
    id: 'qi-1',
    lesson_id: 'lesson-1',
    question: 'What is REST?',
    answer: 'Representational State Transfer',
    question_type: 'free_text',
    distractors: null,
    difficulty: 'medium',
    display_order: 0,
    version: 1,
    superseded_by_id: null,
    retired_at: null,
    generated_by_model: null,
    created_at: '2026-04-27T00:00:00Z',
    updated_at: '2026-04-27T00:00:00Z',
    ...overrides,
  }
}

function renderAt(lessonId: string) {
  return render(
    <MemoryRouter
      initialEntries={[
        {
          pathname: `/admin/lessons/${lessonId}/quiz-items`,
          state: { deckId: 'deck-1' },
        },
      ]}
    >
      <Routes>
        <Route
          path="/admin/lessons/:lessonId/quiz-items"
          element={<AdminQuizItems />}
        />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  adminListQuizItems.mockReset()
  adminCreateQuizItem.mockReset()
  adminRetireQuizItem.mockReset()
  captureMock.mockReset()
})

describe('AdminQuizItems (slice 6.4b)', () => {
  it('renders the lesson-scoped quiz_item list with D-16 status filter (active/retired/all)', async () => {
    adminListQuizItems.mockResolvedValue([quizItem()])
    renderAt('lesson-1')
    await waitFor(() =>
      expect(screen.getByTestId('admin-quiz-items-list')).toBeInTheDocument(),
    )
    expect(
      screen.getByTestId('admin-quiz-items-filter-active'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('admin-quiz-items-filter-retired'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('admin-quiz-items-filter-all'),
    ).toBeInTheDocument()
    expect(adminListQuizItems).toHaveBeenCalledWith('lesson-1', 'active')
  })

  it('create form submits and emits admin_quiz_item_created', async () => {
    adminListQuizItems.mockResolvedValue([])
    adminCreateQuizItem.mockResolvedValue(
      quizItem({ id: 'qi-new', question: 'New?', answer: 'Yes' }),
    )
    renderAt('lesson-1')
    fireEvent.click(screen.getByTestId('admin-quiz-items-toggle-create'))
    fireEvent.change(screen.getByLabelText(/^Question/i), {
      target: { value: 'New?' },
    })
    fireEvent.change(screen.getByLabelText(/^Answer/i), {
      target: { value: 'Yes' },
    })
    fireEvent.click(screen.getByTestId('admin-quiz-items-submit-create'))
    await waitFor(() =>
      expect(adminCreateQuizItem).toHaveBeenCalledWith(
        'lesson-1',
        expect.objectContaining({ question: 'New?', answer: 'Yes' }),
      ),
    )
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_quiz_item_created',
        expect.objectContaining({
          lesson_id: 'lesson-1',
          internal: true,
        }),
      ),
    )
  })

  it('retire button calls adminRetireQuizItem with retire_reason="direct"', async () => {
    adminListQuizItems.mockResolvedValue([quizItem()])
    adminRetireQuizItem.mockResolvedValue(
      quizItem({ retired_at: '2026-04-27T00:00:00Z' }),
    )
    renderAt('lesson-1')
    const retireBtn = await screen.findByTestId('admin-quiz-items-retire-qi-1')
    fireEvent.click(retireBtn)
    await waitFor(() =>
      expect(adminRetireQuizItem).toHaveBeenCalledWith('qi-1'),
    )
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_quiz_item_retired',
        expect.objectContaining({
          quiz_item_id: 'qi-1',
          retire_reason: 'direct',
          internal: true,
        }),
      ),
    )
  })

  it('switching status filter refetches with new value', async () => {
    adminListQuizItems.mockResolvedValue([])
    renderAt('lesson-1')
    await waitFor(() =>
      expect(adminListQuizItems).toHaveBeenCalledWith('lesson-1', 'active'),
    )
    fireEvent.click(screen.getByTestId('admin-quiz-items-filter-retired'))
    await waitFor(() =>
      expect(adminListQuizItems).toHaveBeenCalledWith('lesson-1', 'retired'),
    )
  })
})
