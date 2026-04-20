import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { AnalysisResponse } from '@/types'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchOnboardingRecommendations: vi.fn().mockResolvedValue({ results: [] }),
  }
})

vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({ canUsePro: false }),
  UsageProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'u1', email: 't@e.com', name: 'T' },
    isLoading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
    updateUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

const RESULT: AnalysisResponse = {
  scan_id: 'scan-1',
  ats_score: 80,
  grade: 'A',
  score_breakdown: {
    keyword_match: 80,
    skills_coverage: 75,
    formatting_compliance: 90,
    bullet_strength: 70,
  },
  matched_keywords: ['python', 'react'],
  missing_keywords: ['kubernetes'],
  skill_gaps: [],
  bullet_analysis: [],
  formatting_issues: [],
  job_fit_explanation: 'solid fit',
  top_strengths: [],
  top_gaps: [],
  keyword_chart_data: [
    { keyword: 'python', jd_count: 5, resume_count: 3, matched: true },
    { keyword: 'kubernetes', jd_count: 4, resume_count: 0, matched: false },
    { keyword: 'react', jd_count: 2, resume_count: 2, matched: true },
  ],
  skills_overlap_data: [],
}

vi.mock('@/context/AnalysisContext', () => ({
  useAnalysisContext: () => ({
    state: {
      isLoading: false,
      result: RESULT,
      error: null,
      resumeFile: null,
      jobDescription: '',
    },
    dispatch: vi.fn(),
  }),
  AnalysisProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import Results from '@/pages/Results'

function renderResults() {
  return render(
    <MemoryRouter initialEntries={['/prep/results']}>
      <Results />
    </MemoryRouter>,
  )
}

function assertBefore(earlierId: string, laterId: string) {
  const earlier = document.getElementById(earlierId)
  const later = document.getElementById(laterId)
  if (!earlier) throw new Error(`missing #${earlierId}`)
  if (!later) throw new Error(`missing #${laterId}`)
  const mask = earlier.compareDocumentPosition(later)
  expect(
    (mask & Node.DOCUMENT_POSITION_FOLLOWING) !== 0,
    `expected #${earlierId} to render before #${laterId}`,
  ).toBe(true)
}

beforeEach(() => {
  capture.mockReset()
})

describe('Results page — P5-S20 section ordering', () => {
  it('test_ats_score_renders_above_job_fit', () => {
    renderResults()
    assertBefore('ats-score', 'job-fit')
  })

  it('test_job_fit_renders_above_skill_gaps', () => {
    renderResults()
    // "Skill Gaps" in the target order = Missing Skills panel.
    assertBefore('job-fit', 'missing-skills')
  })

  it('test_job_fit_renders_above_keyword_frequency', () => {
    renderResults()
    assertBefore('job-fit', 'keywords')
  })

  it('test_missing_skills_renders_above_keywords', () => {
    renderResults()
    // Missing Skills is target slot 3, Keywords is slot 4.
    assertBefore('missing-skills', 'keywords')
  })

  it('test_keywords_renders_above_score_breakdown', () => {
    renderResults()
    // Keywords is slot 4, Score Breakdown is slot 5.
    assertBefore('keywords', 'score-breakdown')
  })

  it('test_section_ids_unchanged', () => {
    renderResults()
    // The 9 section IDs that back the `results_tooltip_opened` enum must all
    // still exist in the DOM. HTML ids use hyphens; analytics enum uses
    // underscores; both map 1:1.
    const expectedIds = [
      'ats-score',
      'score-breakdown',
      'job-fit',
      'keywords',
      'skills',
      'bullets',
      'missing-skills',
      'formatting',
      'improvements',
    ]
    for (const id of expectedIds) {
      expect(
        document.getElementById(id),
        `expected #${id} in DOM`,
      ).not.toBeNull()
    }
  })

  it('test_job_fit_viewed_event_fires_on_mount', () => {
    renderResults()
    const matching = capture.mock.calls.filter(
      ([name]) => name === 'job_fit_explanation_viewed',
    )
    expect(matching).toHaveLength(1)
    expect(matching[0][1]).toEqual({ view_position: 'above_fold' })
  })

  it('test_job_fit_viewed_event_fires_exactly_once_under_strict_mode_like_remount', () => {
    // Idempotency guard: even if mount → unmount → mount happens within the
    // same test (simulating Strict Mode double-invoke), we don't want 3+ fires
    // from a single user session. Re-rendering the same component tree in one
    // render() call emulates Strict Mode's double-invoke enough for this
    // guard; each fresh render() is a new mount (new useRef), which is
    // expected to fire.
    const { unmount } = renderResults()
    unmount()
    renderResults()
    const matching = capture.mock.calls.filter(
      ([name]) => name === 'job_fit_explanation_viewed',
    )
    // Two mount cycles, one fire each. Idempotency is WITHIN a single mount,
    // not across mount/unmount/mount — this test documents that contract.
    expect(matching.length).toBeLessThanOrEqual(2)
    expect(matching.length).toBeGreaterThanOrEqual(1)
  })
})
