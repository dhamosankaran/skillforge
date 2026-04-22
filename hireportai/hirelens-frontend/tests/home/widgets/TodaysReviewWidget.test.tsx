import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchDailyQueue = vi.fn()
vi.mock('@/services/api', () => ({
  fetchDailyQueue: (...args: unknown[]) => fetchDailyQueue(...args),
}))

import { TodaysReviewWidget } from '@/components/home/widgets/TodaysReviewWidget'

function renderWidget() {
  return render(
    <MemoryRouter>
      <TodaysReviewWidget persona="career_climber" />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  fetchDailyQueue.mockReset()
})

describe('TodaysReviewWidget', () => {
  it('renders a skeleton in the loading state', () => {
    fetchDailyQueue.mockReturnValue(new Promise(() => {}))
    const { container } = renderWidget()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders cards-due + Start review when total_due > 0', async () => {
    fetchDailyQueue.mockResolvedValueOnce({
      total_due: 5,
      cards: [],
      session_id: 's1',
    })
    renderWidget()
    expect(await screen.findByText('5')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /start review/i })).toHaveAttribute(
      'href',
      '/learn/daily',
    )
  })

  it('renders the empty state when total_due === 0', async () => {
    fetchDailyQueue.mockResolvedValueOnce({
      total_due: 0,
      cards: [],
      session_id: 's1',
    })
    renderWidget()
    expect(
      await screen.findByText(/all caught up/i),
    ).toBeInTheDocument()
  })

  it('renders the error state + retry triggers another fetch', async () => {
    fetchDailyQueue.mockRejectedValueOnce(new Error('boom'))
    renderWidget()
    expect(
      await screen.findByText(/couldn't load today's review/i),
    ).toBeInTheDocument()

    fetchDailyQueue.mockResolvedValueOnce({
      total_due: 2,
      cards: [],
      session_id: 's1',
    })
    await userEvent.setup().click(screen.getByRole('button', { name: /try again/i }))
    await waitFor(() => expect(fetchDailyQueue).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('2')).toBeInTheDocument()
  })

  // ── B-019 — completed_today flips empty-state copy + kills Start CTA ──

  it('flips to "Done for today" empty state when completed_today=true, even if total_due > 0', async () => {
    fetchDailyQueue.mockResolvedValueOnce({
      total_due: 5, // fresh-fill refilled the queue; widget must not trust this
      cards: [],
      session_id: 's1',
      completed_today: true,
    })
    renderWidget()
    expect(
      await screen.findByText(/done for today — great work/i),
    ).toBeInTheDocument()
    // No Start-review CTA — only the pre-completion data-state renders it.
    expect(screen.queryByRole('link', { name: /start review/i })).toBeNull()
    // Pre-B-019 copy must not leak through.
    expect(screen.queryByText(/all caught up/i)).toBeNull()
  })

  it('shows "all caught up" copy when completed_today=false AND total_due=0 (fresh user day-1 edge)', async () => {
    fetchDailyQueue.mockResolvedValueOnce({
      total_due: 0,
      cards: [],
      session_id: 's1',
      completed_today: false,
    })
    renderWidget()
    expect(await screen.findByText(/all caught up/i)).toBeInTheDocument()
    expect(screen.queryByText(/done for today/i)).toBeNull()
  })

  it('absent completed_today (legacy BE response) falls back to pre-B-019 behaviour', async () => {
    // Shape-stability guard: if the BE deploy trails the FE, the widget must
    // NOT treat undefined as true. Pre-B-019 behaviour (data when >0, empty
    // when 0, with the old copy) is the safe default.
    fetchDailyQueue.mockResolvedValueOnce({
      total_due: 3,
      cards: [],
      session_id: 's1',
    })
    renderWidget()
    expect(await screen.findByText('3')).toBeInTheDocument()
    expect(screen.queryByText(/done for today/i)).toBeNull()
  })
})
