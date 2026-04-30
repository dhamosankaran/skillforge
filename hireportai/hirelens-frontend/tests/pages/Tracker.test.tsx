/**
 * Tracker page-level tests — spec #57 §6.1 / §6.3.
 *
 * Coverage:
 *   - new interview_date field on the create form (validation + payload)
 *   - `?new=1` query-param opens the create form on mount
 *   - `?focus={tracker_id}` query-param opens the per-row date editor
 *   - tracker_interview_date_set / _cleared telemetry events
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { TrackerApplication } from '@/types'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const mockUseTracker = vi.fn()
vi.mock('@/hooks/useTracker', () => ({
  useTracker: () => mockUseTracker(),
}))

import Tracker from '@/pages/Tracker'

function app(
  overrides: Partial<TrackerApplication> = {},
): TrackerApplication {
  return {
    id: 'a1',
    company: 'Google',
    role: 'SWE',
    date_applied: '2026-04-20',
    ats_score: 72,
    status: 'Applied',
    created_at: '2026-04-20T00:00:00Z',
    ...overrides,
  }
}

function renderTracker(initialPath = '/prep/tracker') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Tracker />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  mockUseTracker.mockReset()
  mockUseTracker.mockReturnValue({
    applications: [],
    isLoading: false,
    add: vi.fn().mockResolvedValue(app()),
    update: vi.fn().mockResolvedValue(app()),
    remove: vi.fn(),
    moveStatus: vi.fn(),
  })
})

describe('Tracker — spec #57', () => {
  it('?new=1 opens the create form on mount', async () => {
    renderTracker('/prep/tracker?new=1')
    await waitFor(() => {
      expect(screen.getByTestId('tracker-form-interview-date')).toBeInTheDocument()
    })
  })

  it('create form includes the interview_date field with min=today validator', async () => {
    const user = userEvent.setup()
    renderTracker()
    await user.click(screen.getByRole('button', { name: /add application/i }))
    const dateInput = await screen.findByTestId('tracker-form-interview-date')
    const today = new Date().toISOString().slice(0, 10)
    expect(dateInput).toHaveAttribute('min', today)
    expect(dateInput).toHaveAttribute('type', 'date')
  })

  it('submitting create form with interview_date passes it through and fires set event', async () => {
    const created = app({ id: 'a-new' })
    const addMock = vi.fn().mockResolvedValue(created)
    mockUseTracker.mockReturnValue({
      applications: [],
      isLoading: false,
      add: addMock,
      update: vi.fn(),
      remove: vi.fn(),
      moveStatus: vi.fn(),
    })
    const user = userEvent.setup()
    renderTracker()
    await user.click(screen.getByRole('button', { name: /add application/i }))
    await user.type(
      screen.getAllByPlaceholderText(/e.g. Google/i)[0],
      'JPMorgan',
    )
    await user.type(screen.getByPlaceholderText(/e.g. Senior SWE/i), 'SWE')
    const future = new Date()
    future.setDate(future.getDate() + 30)
    const futureIso = future.toISOString().slice(0, 10)
    await user.type(screen.getByTestId('tracker-form-interview-date'), futureIso)
    await user.click(screen.getByRole('button', { name: /save application/i }))

    await waitFor(() => {
      expect(addMock).toHaveBeenCalledWith(
        expect.objectContaining({ interview_date: futureIso }),
      )
    })
    expect(capture).toHaveBeenCalledWith(
      'tracker_interview_date_set',
      expect.objectContaining({ tracker_id: 'a-new', source: 'create' }),
    )
  })

  it('?focus={id} opens the focused row editor when the row exists', async () => {
    mockUseTracker.mockReturnValue({
      applications: [app({ id: 'fooid', interview_date: '2026-06-01' })],
      isLoading: false,
      add: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      moveStatus: vi.fn(),
    })
    renderTracker('/prep/tracker?focus=fooid')
    expect(
      await screen.findByTestId('tracker-focused-editor'),
    ).toBeInTheDocument()
    expect(screen.getByTestId('tracker-focused-date-input')).toHaveValue(
      '2026-06-01',
    )
  })

  it('?focus={id} on a missing row drops focus state silently', async () => {
    mockUseTracker.mockReturnValue({
      applications: [app({ id: 'other-id' })],
      isLoading: false,
      add: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      moveStatus: vi.fn(),
    })
    renderTracker('/prep/tracker?focus=missing-id')
    await waitFor(() => {
      expect(screen.queryByTestId('tracker-focused-editor')).toBeNull()
    })
  })
})
