import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Lesson, LessonUpdateResponse, QuizItem } from '@/types'

const adminListLessons = vi.fn()
const adminListQuizItems = vi.fn()
const adminUpdateLesson = vi.fn()
const adminPublishLesson = vi.fn()
const adminArchiveLesson = vi.fn()
const captureMock = vi.fn()

vi.mock('@/services/api', () => ({
  adminListLessons: (...args: unknown[]) => adminListLessons(...args),
  adminListQuizItems: (...args: unknown[]) => adminListQuizItems(...args),
  adminUpdateLesson: (...args: unknown[]) => adminUpdateLesson(...args),
  adminPublishLesson: (...args: unknown[]) => adminPublishLesson(...args),
  adminArchiveLesson: (...args: unknown[]) => adminArchiveLesson(...args),
}))
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => captureMock(...args),
}))

import AdminLessonEditor from '@/pages/admin/AdminLessonEditor'

function lesson(overrides: Partial<Lesson> = {}): Lesson {
  return {
    id: 'lesson-1',
    deck_id: 'deck-1',
    slug: 'introduction',
    title: 'Introduction',
    concept_md: 'a'.repeat(100),
    production_md: 'b'.repeat(100),
    examples_md: 'c'.repeat(100),
    display_order: 0,
    version: 1,
    version_type: 'initial',
    published_at: null,
    generated_by_model: null,
    source_content_id: null,
    quality_score: null,
    created_at: '2026-04-27T00:00:00Z',
    updated_at: '2026-04-27T00:00:00Z',
    archived_at: null,
    ...overrides,
  }
}

function quizItem(overrides: Partial<QuizItem> = {}): QuizItem {
  return {
    id: 'qi-1',
    lesson_id: 'lesson-1',
    question: 'Q1',
    answer: 'A1',
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

function renderAt(lessonId: string, deckId = 'deck-1') {
  return render(
    <MemoryRouter
      initialEntries={[
        { pathname: `/admin/lessons/${lessonId}`, state: { deckId } },
      ]}
    >
      <Routes>
        <Route
          path="/admin/lessons/:lessonId"
          element={<AdminLessonEditor />}
        />
        <Route
          path="/admin/decks/:deckId"
          element={<div data-testid="page-deck-detail" />}
        />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  adminListLessons.mockReset()
  adminListQuizItems.mockReset()
  adminUpdateLesson.mockReset()
  adminPublishLesson.mockReset()
  adminArchiveLesson.mockReset()
  captureMock.mockReset()
})

describe('AdminLessonEditor (slice 6.4b)', () => {
  it('loads the lesson + active quiz items and renders the form', async () => {
    adminListLessons.mockResolvedValue([lesson()])
    adminListQuizItems.mockResolvedValue([quizItem()])
    renderAt('lesson-1')
    await waitFor(() =>
      expect(
        screen.getByTestId('admin-lesson-editor-form'),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByTestId('admin-lesson-editor-quiz-items-link'),
    ).toHaveTextContent('Quiz items (1)')
  })

  it('minor edit submits PATCH without firing the cascade modal', async () => {
    adminListLessons.mockResolvedValue([lesson()])
    adminListQuizItems.mockResolvedValue([])
    const response: LessonUpdateResponse = {
      lesson: lesson({ version: 1, version_type: 'minor_edit' }),
      version_type_applied: 'minor',
      quiz_items_retired_count: 0,
      quiz_items_retired_ids: [],
    }
    adminUpdateLesson.mockResolvedValue(response)
    renderAt('lesson-1')
    await screen.findByTestId('admin-lesson-editor-form')

    // Tiny title change — concept/production/examples bodies unchanged →
    // classifyLessonEdit returns 'minor', PATCH fires immediately.
    fireEvent.change(screen.getByLabelText(/^Title$/i), {
      target: { value: 'Introduction (revised)' },
    })
    fireEvent.click(screen.getByTestId('admin-lesson-editor-save'))

    await waitFor(() => expect(adminUpdateLesson).toHaveBeenCalledOnce())
    expect(adminUpdateLesson.mock.calls[0][1]).toMatchObject({
      edit_classification: 'minor',
    })
    expect(screen.queryByTestId('confirm-cascade-modal')).not.toBeInTheDocument()
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_lesson_updated_minor',
        expect.objectContaining({ internal: true }),
      ),
    )
  })

  it('substantive edit fires ConfirmCascadeModal before PATCH; confirm runs PATCH and shows results', async () => {
    adminListLessons.mockResolvedValue([lesson()])
    adminListQuizItems.mockResolvedValue([quizItem(), quizItem({ id: 'qi-2' })])
    adminUpdateLesson.mockResolvedValue({
      lesson: lesson({ version: 2, version_type: 'substantive_edit' }),
      version_type_applied: 'substantive',
      quiz_items_retired_count: 2,
      quiz_items_retired_ids: ['qi-1', 'qi-2'],
    })
    renderAt('lesson-1')
    await screen.findByTestId('admin-lesson-editor-form')

    // Replace the entire concept_md → ratio = 1.0 → substantive.
    const conceptTextarea = screen.getByTestId(
      'admin-lesson-editor-concept-textarea',
    )
    fireEvent.change(conceptTextarea, {
      target: { value: 'z'.repeat(200) },
    })
    fireEvent.click(screen.getByTestId('admin-lesson-editor-save'))

    // Pre-PATCH cascade-warning modal must show.
    const cascadeModal = await screen.findByTestId('confirm-cascade-modal')
    expect(cascadeModal).toHaveTextContent(/All 2 active quiz_items/i)
    // PATCH must NOT have fired yet.
    expect(adminUpdateLesson).not.toHaveBeenCalled()

    fireEvent.click(screen.getByTestId('confirm-cascade-confirm'))
    await waitFor(() => expect(adminUpdateLesson).toHaveBeenCalledOnce())
    expect(adminUpdateLesson.mock.calls[0][1]).toMatchObject({
      edit_classification: 'substantive',
    })
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_lesson_substantively_edited',
        expect.objectContaining({
          quiz_items_retired_count: 2,
          internal: true,
        }),
      ),
    )
  })

  it('publish click calls adminPublishLesson and emits admin_lesson_published', async () => {
    adminListLessons.mockResolvedValue([lesson()])
    adminListQuizItems.mockResolvedValue([])
    adminPublishLesson.mockResolvedValue(
      lesson({ published_at: '2026-04-27T00:00:00Z' }),
    )
    renderAt('lesson-1')
    fireEvent.click(await screen.findByTestId('admin-lesson-editor-publish'))
    await waitFor(() =>
      expect(adminPublishLesson).toHaveBeenCalledWith('lesson-1'),
    )
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_lesson_published',
        expect.objectContaining({ internal: true }),
      ),
    )
  })

  it('archive click calls adminArchiveLesson and emits admin_lesson_archived with was_published', async () => {
    adminListLessons.mockResolvedValue([
      lesson({ published_at: '2026-04-27T00:00:00Z' }),
    ])
    adminListQuizItems.mockResolvedValue([])
    adminArchiveLesson.mockResolvedValue(
      lesson({
        published_at: '2026-04-27T00:00:00Z',
        archived_at: '2026-04-27T00:00:00Z',
      }),
    )
    renderAt('lesson-1')
    fireEvent.click(await screen.findByTestId('admin-lesson-editor-archive'))
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_lesson_archived',
        expect.objectContaining({ was_published: true, internal: true }),
      ),
    )
  })

  it('renders MarkdownEditor with edit/preview tabs for each Markdown field', async () => {
    adminListLessons.mockResolvedValue([lesson()])
    adminListQuizItems.mockResolvedValue([])
    renderAt('lesson-1')
    await screen.findByTestId('admin-lesson-editor-form')
    // Three editors → 6 tab buttons (3 × Edit, 3 × Preview).
    const editTabs = screen.getAllByRole('tab', { name: /^Edit$/ })
    const previewTabs = screen.getAllByRole('tab', { name: /^Preview$/ })
    expect(editTabs.length).toBe(3)
    expect(previewTabs.length).toBe(3)
  })
})
