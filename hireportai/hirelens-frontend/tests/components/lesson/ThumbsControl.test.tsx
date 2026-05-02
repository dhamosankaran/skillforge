import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ThumbsResponse } from '@/types'

const submitThumbs = vi.fn<
  [string, { score: -1 | 1 }],
  Promise<ThumbsResponse>
>()
const captureMock = vi.fn()

vi.mock('@/services/api', () => ({
  submitThumbs: (...args: unknown[]) =>
    submitThumbs(...(args as Parameters<typeof submitThumbs>)),
}))

vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => captureMock(...args),
}))

import { ThumbsControl } from '@/components/lesson/ThumbsControl'

beforeEach(() => {
  submitThumbs.mockReset()
  captureMock.mockReset()
})

function ok(score: -1 | 1, aggregate: number, count: number): ThumbsResponse {
  return {
    accepted: true,
    score,
    aggregate_score: aggregate,
    aggregate_count: count,
  }
}

describe('ThumbsControl', () => {
  it('renders both buttons unselected when no initial thumbs', () => {
    render(<ThumbsControl lessonId="l1" initialThumbs={null} />)
    expect(screen.getByTestId('thumbs-up')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.getByTestId('thumbs-down')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.queryByTestId('thumbs-aggregate')).not.toBeInTheDocument()
  })

  it('seeds initial state from viewer_thumbs prop', () => {
    render(
      <ThumbsControl
        lessonId="l1"
        initialThumbs={{
          accepted: true,
          score: 1,
          aggregate_score: 0.75,
          aggregate_count: 4,
        }}
      />,
    )
    expect(screen.getByTestId('thumbs-up')).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByTestId('thumbs-down')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.getByTestId('thumbs-aggregate')).toHaveTextContent(
      '+0.75 · 4 votes',
    )
  })

  it('submits thumbs-up and updates aggregate on success (AC-16, AC-18)', async () => {
    submitThumbs.mockResolvedValueOnce(ok(1, 1, 1))
    render(<ThumbsControl lessonId="l1" persona="climber" plan="free" />)

    fireEvent.click(screen.getByTestId('thumbs-up'))

    await waitFor(() => {
      expect(submitThumbs).toHaveBeenCalledWith('l1', { score: 1 })
    })
    await waitFor(() => {
      expect(screen.getByTestId('thumbs-up')).toHaveAttribute(
        'aria-pressed',
        'true',
      )
    })
    expect(screen.getByTestId('thumbs-aggregate')).toHaveTextContent(
      '+1.00 · 1 vote',
    )
    expect(captureMock).toHaveBeenCalledWith(
      'lesson_thumbs_submitted',
      expect.objectContaining({
        lesson_id: 'l1',
        score: 1,
        previous_score: 0,
        persona: 'climber',
        plan: 'free',
      }),
    )
  })

  it('flips from up to down on opposite click and overwrites server-side', async () => {
    submitThumbs.mockResolvedValueOnce(ok(-1, -1, 1))
    render(
      <ThumbsControl
        lessonId="l1"
        initialThumbs={{
          accepted: true,
          score: 1,
          aggregate_score: 1,
          aggregate_count: 1,
        }}
      />,
    )

    fireEvent.click(screen.getByTestId('thumbs-down'))
    await waitFor(() => {
      expect(screen.getByTestId('thumbs-down')).toHaveAttribute(
        'aria-pressed',
        'true',
      )
    })
    expect(screen.getByTestId('thumbs-up')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(submitThumbs).toHaveBeenCalledWith('l1', { score: -1 })
  })

  it('reverts optimistic state on submit error', async () => {
    submitThumbs.mockRejectedValueOnce(new Error('boom'))
    render(<ThumbsControl lessonId="l1" initialThumbs={null} />)

    fireEvent.click(screen.getByTestId('thumbs-up'))

    await waitFor(() => {
      expect(screen.getByTestId('thumbs-error')).toHaveTextContent('boom')
    })
    expect(screen.getByTestId('thumbs-up')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.getByTestId('thumbs-down')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  it('R12 — uses design tokens (no inline hex)', () => {
    const { container } = render(
      <ThumbsControl lessonId="l1" initialThumbs={null} />,
    )
    const html = container.innerHTML
    expect(html).not.toMatch(/#[0-9a-fA-F]{3,6}/)
  })
})
