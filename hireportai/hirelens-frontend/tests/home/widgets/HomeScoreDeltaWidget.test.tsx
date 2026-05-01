import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ScoreHistoryResponse } from '@/types'

const fetchScoreHistory = vi.fn()
vi.mock('@/services/api', () => ({
  fetchScoreHistory: (...args: unknown[]) => fetchScoreHistory(...args),
}))

import { HomeScoreDeltaWidget } from '@/components/home/widgets/HomeScoreDeltaWidget'

const TRACKER_ID = 'tracker-uuid-1'

function deltaHistory(prev = 60, latest = 84): ScoreHistoryResponse {
  return {
    tracker_application_id: TRACKER_ID,
    history: [
      {
        id: 's1',
        scan_id: 'sid-1',
        overall_score: prev,
        keyword_match_score: 0.4,
        skills_coverage_score: 0.5,
        formatting_compliance_score: 0.8,
        bullet_strength_score: 0.3,
        scanned_at: '2026-04-15T00:00:00Z',
      },
      {
        id: 's2',
        scan_id: 'sid-2',
        overall_score: latest,
        keyword_match_score: 0.7,
        skills_coverage_score: 0.6,
        formatting_compliance_score: 0.9,
        bullet_strength_score: 0.55,
        scanned_at: '2026-04-22T00:00:00Z',
      },
    ],
    delta: {
      overall_delta: latest - prev,
      keyword_match_delta: 0.3,
      skills_coverage_delta: 0.1,
      formatting_compliance_delta: 0.1,
      bullet_strength_delta: 0.25,
      days_between: 7,
    },
  }
}

function singleHistory(): ScoreHistoryResponse {
  return {
    tracker_application_id: TRACKER_ID,
    history: [
      {
        id: 's1',
        scan_id: 'sid-1',
        overall_score: 60,
        keyword_match_score: 0.4,
        skills_coverage_score: 0.5,
        formatting_compliance_score: 0.8,
        bullet_strength_score: 0.3,
        scanned_at: '2026-04-15T00:00:00Z',
      },
    ],
    delta: null,
  }
}

beforeEach(() => {
  fetchScoreHistory.mockReset()
})

function renderWidget(props: {
  trackerId: string | null
  company?: string | null
}) {
  return render(
    <MemoryRouter>
      <HomeScoreDeltaWidget
        persona="interview_prepper"
        trackerId={props.trackerId}
        company={props.company ?? 'Stripe'}
      />
    </MemoryRouter>,
  )
}

describe('HomeScoreDeltaWidget — spec #63 §8.2', () => {
  it('null trackerId renders nothing (no fetch)', () => {
    const { container } = renderWidget({ trackerId: null })
    expect(container.firstChild).toBeNull()
    expect(fetchScoreHistory).not.toHaveBeenCalled()
  })

  it('cold-start (single-row history) hides the widget entirely', async () => {
    fetchScoreHistory.mockResolvedValue(singleHistory())
    const { container } = renderWidget({ trackerId: TRACKER_ID })
    await waitFor(() => expect(fetchScoreHistory).toHaveBeenCalled())
    expect(container.firstChild).toBeNull()
  })

  it('renders the delta envelope when history.length >= 2', async () => {
    fetchScoreHistory.mockResolvedValue(deltaHistory(60, 84))
    renderWidget({ trackerId: TRACKER_ID, company: 'Stripe' })
    await waitFor(() =>
      expect(screen.getByTestId('widget-home-score-delta')).toBeInTheDocument(),
    )
    expect(screen.getByText('60')).toBeInTheDocument()
    expect(screen.getByText('84')).toBeInTheDocument()
    expect(screen.getByText(/\+24 pts/)).toBeInTheDocument()
    expect(screen.getByText(/Stripe/)).toBeInTheDocument()
  })
})
