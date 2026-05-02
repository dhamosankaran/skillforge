import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { AdminContentQualityResponse } from '@/types'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchContentQuality = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchAdminContentQuality: (...args: unknown[]) =>
      fetchContentQuality(...args),
  }
})

const mockUser: AuthUser = {
  id: 'admin-1',
  email: 'admin@example.com',
  name: 'Admin',
  avatar_url: null,
  role: 'admin',
  persona: 'interview_prepper',
  onboarding_completed: true,
  interview_target_company: null,
  interview_target_date: null,
  home_first_visit_seen_at: '2026-01-01T00:00:00Z',
}

vi.mock('@/context/AuthContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/AuthContext')>(
      '@/context/AuthContext',
    )
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      updateUser: vi.fn(),
    }),
  }
})

import AdminContentQuality from '@/pages/admin/AdminContentQuality'

function responseFixture(
  overrides: Partial<AdminContentQualityResponse> = {},
): AdminContentQualityResponse {
  return {
    window_days: 30,
    include_archived: false,
    generated_at: '2026-05-01T10:00:00Z',
    is_cold_start: false,
    decks: [
      {
        deck_id: 'd1',
        deck_slug: 'transformers',
        deck_title: 'Transformers',
        tier: 'foundation',
        persona_visibility: 'both',
        archived: false,
        lesson_count: 2,
        review_count_window: 50,
        weighted_pass_rate: 0.7,
        avg_quality_score: 0.65,
      },
    ],
    worst_lessons: [
      {
        lesson_id: 'l1',
        lesson_slug: 'attention',
        lesson_title: 'Attention is all you need',
        deck_id: 'd1',
        deck_slug: 'transformers',
        review_count_window: 12,
        view_count_window: 30,
        pass_rate: 0.4,
        smoothed_quality_score: 0.43,
        persisted_quality_score: 0.43,
        low_volume: false,
        archived: false,
        published_at: '2026-04-01T00:00:00Z',
        critique_scores: null,
        thumbs_aggregate: null,
        thumbs_count: 0,
      },
    ],
    worst_quiz_items: [
      {
        quiz_item_id: 'q1',
        lesson_id: 'l1',
        deck_id: 'd1',
        question_preview: 'What is self-attention?',
        review_count_window: 8,
        pass_rate: 0.25,
        lapse_rate: 0.5,
        low_volume: true,
        retired: false,
        pass_rate_persisted: null,
        thumbs_aggregate: null,
        thumbs_count: 0,
      },
    ],
    writebacks_applied: 1,
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/content-quality']}>
      <Routes>
        <Route
          path="/admin/content-quality"
          element={<AdminContentQuality />}
        />
        <Route path="/admin/decks/:id" element={<div>deck detail</div>} />
        <Route
          path="/admin/lessons/:id"
          element={<div>lesson editor</div>}
        />
        <Route
          path="/admin/lessons/:id/quiz-items"
          element={<div>quiz items page</div>}
        />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  fetchContentQuality.mockReset()
  fetchContentQuality.mockResolvedValue(responseFixture())
})

describe('AdminContentQuality', () => {
  it('renders all three sections from a populated response', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('deck-rollup-table')).toBeInTheDocument()
      expect(screen.getByTestId('worst-lessons-table')).toBeInTheDocument()
      expect(screen.getByTestId('worst-quiz-items-table')).toBeInTheDocument()
    })
    expect(screen.getByText('Transformers')).toBeInTheDocument()
    expect(
      screen.getByText('Attention is all you need'),
    ).toBeInTheDocument()
    expect(screen.getByText('What is self-attention?')).toBeInTheDocument()
  })

  it('shows the cold-start banner when is_cold_start=true', async () => {
    fetchContentQuality.mockResolvedValueOnce(
      responseFixture({
        is_cold_start: true,
        decks: [],
        worst_lessons: [],
        worst_quiz_items: [],
        writebacks_applied: 0,
      }),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('cold-start-banner')).toBeInTheDocument()
    })
  })

  it('refetches when window selector changes', async () => {
    renderPage()
    await waitFor(() =>
      expect(fetchContentQuality).toHaveBeenCalledTimes(1),
    )
    fireEvent.change(screen.getByTestId('window-selector'), {
      target: { value: '60' },
    })
    await waitFor(() =>
      expect(fetchContentQuality).toHaveBeenCalledTimes(2),
    )
    expect(fetchContentQuality).toHaveBeenLastCalledWith({
      window_days: 60,
      include_archived: false,
    })
  })

  it('refetches when archived toggle flips', async () => {
    renderPage()
    await waitFor(() =>
      expect(fetchContentQuality).toHaveBeenCalledTimes(1),
    )
    fireEvent.click(screen.getByTestId('include-archived-toggle'))
    await waitFor(() =>
      expect(fetchContentQuality).toHaveBeenCalledTimes(2),
    )
    expect(fetchContentQuality).toHaveBeenLastCalledWith({
      window_days: 30,
      include_archived: true,
    })
  })

  it('fires admin_content_quality_viewed exactly once per mount', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('deck-rollup-table')).toBeInTheDocument()
    })
    // Trigger a refetch — event must NOT fire again on the same mount.
    fireEvent.change(screen.getByTestId('window-selector'), {
      target: { value: '7' },
    })
    await waitFor(() =>
      expect(fetchContentQuality).toHaveBeenCalledTimes(2),
    )
    const fired = capture.mock.calls.filter(
      (c) => c[0] === 'admin_content_quality_viewed',
    )
    expect(fired).toHaveLength(1)
    expect(fired[0][1]).toMatchObject({
      admin_id: 'admin-1',
      window_days: 30,
      include_archived: false,
      internal: true,
    })
  })

  it('clicking a lesson row navigates to /admin/lessons/:id', async () => {
    renderPage()
    await waitFor(() => screen.getByTestId('worst-lessons-row-attention'))
    fireEvent.click(screen.getByTestId('worst-lessons-row-attention'))
    await waitFor(() =>
      expect(screen.getByText('lesson editor')).toBeInTheDocument(),
    )
  })

  it('clicking a quiz-item row navigates to the quiz-items page', async () => {
    renderPage()
    await waitFor(() => screen.getByTestId('worst-quiz-items-row-q1'))
    fireEvent.click(screen.getByTestId('worst-quiz-items-row-q1'))
    await waitFor(() =>
      expect(screen.getByText('quiz items page')).toBeInTheDocument(),
    )
  })

  it('clicking a deck row navigates to /admin/decks/:id', async () => {
    renderPage()
    await waitFor(() => screen.getByTestId('deck-rollup-row-transformers'))
    fireEvent.click(screen.getByTestId('deck-rollup-row-transformers'))
    await waitFor(() =>
      expect(screen.getByText('deck detail')).toBeInTheDocument(),
    )
  })
})
