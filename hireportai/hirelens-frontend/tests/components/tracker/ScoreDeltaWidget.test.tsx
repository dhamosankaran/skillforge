import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ScoreHistoryResponse } from '@/types'

const fetchScoreHistory = vi.fn()
vi.mock('@/services/api', () => ({
  fetchScoreHistory: (...args: unknown[]) => fetchScoreHistory(...args),
}))

import { ScoreDeltaWidget } from '@/components/tracker/ScoreDeltaWidget'

const TRACKER_ID = 'tracker-uuid-1'

function emptyHistory(): ScoreHistoryResponse {
  return { tracker_application_id: TRACKER_ID, history: [], delta: null }
}

function singleHistory(score = 70): ScoreHistoryResponse {
  return {
    tracker_application_id: TRACKER_ID,
    history: [
      {
        id: 's1',
        scan_id: 'sid-1',
        overall_score: score,
        keyword_match_score: 0.5,
        skills_coverage_score: 0.5,
        formatting_compliance_score: 0.9,
        bullet_strength_score: 0.4,
        scanned_at: '2026-04-20T00:00:00Z',
      },
    ],
    delta: null,
  }
}

function deltaHistory(prev = 60, latest = 80): ScoreHistoryResponse {
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

beforeEach(() => {
  fetchScoreHistory.mockReset()
})

describe('ScoreDeltaWidget — spec #63 §8.1', () => {
  it('empty history renders the re-scan CTA empty state', async () => {
    fetchScoreHistory.mockResolvedValue(emptyHistory())
    render(<ScoreDeltaWidget trackerApplicationId={TRACKER_ID} />)
    await waitFor(() =>
      expect(screen.getByTestId('score-delta-widget-empty')).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/re-scan this application/i),
    ).toBeInTheDocument()
  })

  it('single-row history renders first-scan baseline (no delta)', async () => {
    fetchScoreHistory.mockResolvedValue(singleHistory(72))
    render(<ScoreDeltaWidget trackerApplicationId={TRACKER_ID} />)
    await waitFor(() =>
      expect(
        screen.getByTestId('score-delta-widget-baseline'),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText('72')).toBeInTheDocument()
    expect(screen.getByText(/first scan baseline/i)).toBeInTheDocument()
  })

  it('multi-row history renders the delta envelope with per-axis rows', async () => {
    fetchScoreHistory.mockResolvedValue(deltaHistory(60, 88))
    render(<ScoreDeltaWidget trackerApplicationId={TRACKER_ID} />)
    await waitFor(() =>
      expect(screen.getByTestId('score-delta-widget')).toBeInTheDocument(),
    )
    // Before / after / delta header
    expect(screen.getByText('60')).toBeInTheDocument()
    expect(screen.getByText('88')).toBeInTheDocument()
    expect(screen.getByTestId('score-delta-overall-badge')).toHaveTextContent(
      '+28 points',
    )
    // Per-axis rows
    expect(screen.getByText(/keyword match/i)).toBeInTheDocument()
    expect(screen.getByText(/skills coverage/i)).toBeInTheDocument()
    expect(screen.getByText(/formatting/i)).toBeInTheDocument()
    expect(screen.getByText(/bullets/i)).toBeInTheDocument()
    expect(screen.getByText(/compared over 7 days/i)).toBeInTheDocument()
  })

  it('negative overall delta renders danger tone with no plus sign', async () => {
    fetchScoreHistory.mockResolvedValue(deltaHistory(80, 65))
    render(<ScoreDeltaWidget trackerApplicationId={TRACKER_ID} />)
    await waitFor(() =>
      expect(screen.getByTestId('score-delta-widget')).toBeInTheDocument(),
    )
    const badge = screen.getByTestId('score-delta-overall-badge')
    expect(badge).toHaveTextContent('-15 points')
    expect(badge.className).toMatch(/text-danger/)
  })

  it('error path renders the fallback copy without crashing', async () => {
    fetchScoreHistory.mockRejectedValue(new Error('boom'))
    render(<ScoreDeltaWidget trackerApplicationId={TRACKER_ID} />)
    await waitFor(() =>
      expect(
        screen.getByTestId('score-delta-widget-error'),
      ).toBeInTheDocument(),
    )
  })
})
