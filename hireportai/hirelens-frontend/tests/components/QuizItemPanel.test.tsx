import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AxiosError, AxiosHeaders } from 'axios'
import type { QuizItem, QuizReviewResponse } from '@/types'

const submitQuizReview = vi.fn<
  [Parameters<typeof import('@/services/api').submitQuizReview>[0]],
  Promise<QuizReviewResponse>
>()

vi.mock('@/services/api', () => ({
  submitQuizReview: (...args: unknown[]) =>
    submitQuizReview(...(args as Parameters<typeof submitQuizReview>)),
}))

import { QuizItemPanel } from '@/components/lesson/QuizItemPanel'

const freeTextItem: QuizItem = {
  id: 'qi-free-text',
  lesson_id: 'l1',
  question: 'What is a query vector?',
  answer: 'It represents what a token is looking for.',
  question_type: 'free_text',
  distractors: null,
  difficulty: 'easy',
  display_order: 0,
  version: 1,
  superseded_by_id: null,
  retired_at: null,
  generated_by_model: null,
  created_at: '2026-04-27T00:00:00Z',
  updated_at: '2026-04-27T00:00:00Z',
}

const mcqItem: QuizItem = {
  ...freeTextItem,
  id: 'qi-mcq',
  question_type: 'mcq',
  distractors: ['Wrong A', 'Wrong B', 'Wrong C'],
}

function makeReviewResponse(
  partial: Partial<QuizReviewResponse> = {},
): QuizReviewResponse {
  return {
    quiz_item_id: 'qi-free-text',
    fsrs_state: 'review',
    stability: 1.5,
    difficulty: 6.0,
    due_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
    reps: 1,
    lapses: 0,
    scheduled_days: 2,
    ...partial,
  }
}

beforeEach(() => {
  submitQuizReview.mockReset()
})

describe('QuizItemPanel — slice 6.3', () => {
  it('flips from idle (Reveal Answer button) to revealed (answer shown)', () => {
    render(<QuizItemPanel quizItem={freeTextItem} sessionId="s1" />)
    expect(
      screen.queryByText(/it represents what a token is looking for/i),
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /reveal answer/i }))
    expect(
      screen.getByText(/it represents what a token is looking for/i),
    ).toBeInTheDocument()
    // Four FSRS rating buttons render.
    expect(screen.getByRole('button', { name: /again/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /good/i })).toBeInTheDocument()
  })

  it('submits to /quiz-items/review with the rating + session id', async () => {
    submitQuizReview.mockResolvedValueOnce(makeReviewResponse({ scheduled_days: 3 }))
    render(<QuizItemPanel quizItem={freeTextItem} sessionId="s-abc" />)
    fireEvent.click(screen.getByRole('button', { name: /reveal answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /good/i }))
    await waitFor(() => expect(submitQuizReview).toHaveBeenCalledTimes(1))
    expect(submitQuizReview.mock.calls[0][0]).toMatchObject({
      quiz_item_id: 'qi-free-text',
      rating: 3,
      session_id: 's-abc',
    })
  })

  it('renders post-review FSRS state in the done step', async () => {
    submitQuizReview.mockResolvedValueOnce(makeReviewResponse({ scheduled_days: 3 }))
    render(<QuizItemPanel quizItem={freeTextItem} sessionId="s1" />)
    fireEvent.click(screen.getByRole('button', { name: /reveal answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /good/i }))
    await waitFor(() =>
      expect(screen.getByText(/next review in 3 day/i)).toBeInTheDocument(),
    )
    expect(screen.getByText(/fsrs state: review/i)).toBeInTheDocument()
  })

  it('mcq question renders one radio per option (answer + distractors)', () => {
    render(<QuizItemPanel quizItem={mcqItem} sessionId="s1" />)
    const radios = screen.getAllByRole('radio')
    expect(radios).toHaveLength(4)
  })

  it('shows an inline error when the BE returns 409 retired', async () => {
    const headers = new AxiosHeaders()
    const err = new AxiosError(
      'retired',
      '409',
      { headers, url: '/api/v1/quiz-items/review' } as never,
      null,
      {
        status: 409,
        statusText: 'Conflict',
        data: { detail: 'retired' },
        headers,
        config: { headers } as never,
      },
    )
    submitQuizReview.mockRejectedValueOnce(err)
    render(<QuizItemPanel quizItem={freeTextItem} sessionId="s1" />)
    fireEvent.click(screen.getByRole('button', { name: /reveal answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /good/i }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/retired/i),
    )
  })
})
