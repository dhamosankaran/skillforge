import { render } from '@testing-library/react'
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

// B-055 worst-case fixture: critical missing skills + missing keywords so
// ImprovementSuggestions renders all 5 cards (the static 3 + 2 dynamic).
// That's the configuration that produced the visible ~800px void on real
// scans before the fix.
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
  missing_keywords: ['kubernetes', 'terraform', 'aws', 'docker'],
  skill_gaps: [
    { skill: 'Kubernetes', category: 'Technical', importance: 'critical' },
    { skill: 'Terraform', category: 'Tool', importance: 'critical' },
  ],
  bullet_analysis: [],
  formatting_issues: [],
  job_fit_explanation: 'solid fit',
  top_strengths: [],
  top_gaps: [],
  keyword_chart_data: [
    { keyword: 'python', jd_count: 5, resume_count: 3, matched: true },
    { keyword: 'kubernetes', jd_count: 4, resume_count: 0, matched: false },
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

describe('Results page — B-055 layout: xl row-coupling void', () => {
  it('test_improvements_spans_two_rows_at_xl_to_decouple_row3_height', () => {
    // The 9 PanelSection cells share a single CSS Grid at xl
    // (`xl:grid-cols-[240px_1fr_280px]`). Row-3 holds [Jump-nav |
    // Skills Radar | Improvements]. Improvements is taller than the
    // chart, so a single-row placement made row-3's auto height equal
    // Improvements' height — leaving a ~800px void below Skills Radar
    // and Jump-nav before row-4 began. Spanning rows 3-4 in col-3
    // distributes Improvements' height across two row tracks so cols
    // 1+2 row heights track only their own cells.
    renderResults()
    const improvements = document.getElementById('improvements')
    expect(improvements, 'expected #improvements in DOM').not.toBeNull()
    const className = improvements!.className
    expect(className).toContain('xl:col-start-3')
    expect(className).toContain('xl:row-start-3')
    expect(className).toMatch(/xl:row-end-5|xl:row-span-2/)
  })

  it('test_skills_radar_uses_default_single_row_span', () => {
    // Skills Radar lives at row-3 col-2 (lg classes apply at xl too via
    // Tailwind cascade — no explicit xl override). It must keep the
    // default span-1; if a future change adds row-span / row-end to it,
    // the void can re-emerge through a different shape (row-4 cells
    // forced to align below an extended Skills Radar). Pin the contract.
    renderResults()
    const skills = document.getElementById('skills')
    expect(skills, 'expected #skills in DOM').not.toBeNull()
    const className = skills!.className
    expect(className).toContain('lg:row-start-3')
    expect(className).not.toMatch(/(?:lg|xl):row-(?:end|span)-/)
  })

  it('test_no_sticky_classes_on_results_grid_children', () => {
    // The B-055 prompt hypothesis was that an `xl:sticky xl:top-20` on
    // Missing Skills was holding the right column open. Audit found no
    // sticky placements anywhere in Results.tsx or its direct children;
    // the bug was CSS Grid row coupling. Lock that finding so a future
    // sticky reintroduction is forced to revisit this regression.
    renderResults()
    const grid = document.querySelector('[data-testid="page-results"]')
    expect(grid, 'expected page-results wrapper').not.toBeNull()
    const stickyEls = grid!.querySelectorAll('[class*="sticky"]')
    expect(stickyEls.length).toBe(0)
  })
})
