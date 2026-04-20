import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { AnalysisResponse } from '@/types'

vi.mock('@/utils/posthog', () => ({
  capture: vi.fn(),
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

describe('Results page — AC-3 every major section renders info icon', () => {
  it('test_every_major_section_renders_info_icon', () => {
    renderResults()
    // AC-3: nine section headers each have an Info trigger.
    const expectedSections = [
      /info: ats score/i,
      /info: score breakdown/i,
      /info: job fit explanation/i,
      /info: keyword frequency analysis/i,
      /info: skills coverage radar/i,
      /info: bullet point analysis/i,
      /info: missing skills/i,
      /info: ats formatting issues/i,
      /info: improvement suggestions/i,
    ]
    for (const pattern of expectedSections) {
      expect(screen.getByRole('button', { name: pattern })).toBeInTheDocument()
    }
    // Exactly nine — no extras, no regressions.
    const allInfo = screen.getAllByRole('button').filter((b) =>
      /^info: /i.test(b.getAttribute('aria-label') ?? ''),
    )
    expect(allInfo).toHaveLength(9)
  })
})
