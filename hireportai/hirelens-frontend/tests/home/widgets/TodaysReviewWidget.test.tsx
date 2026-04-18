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
})
