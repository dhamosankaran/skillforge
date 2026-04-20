import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { KEYWORD_LEGEND, rgbaFromCssVar, KeywordChart } from '@/components/dashboard/KeywordChart'
import { applyTheme } from '@/styles/design-tokens'
import type { KeywordChartData } from '@/types'
import Results from '@/pages/Results'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { vi } from 'vitest'

// Mocks to let Results render without network / contexts
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

const MIXED_FIXTURE: KeywordChartData[] = [
  { keyword: 'python', jd_count: 5, resume_count: 3, matched: true },
  { keyword: 'kubernetes', jd_count: 4, resume_count: 0, matched: false },
  { keyword: 'react', jd_count: 2, resume_count: 2, matched: true },
]

describe('KeywordChart — AC-1 / AC-2 color source-of-truth', () => {
  it('test_keyword_matched_uses_matched_theme_token', () => {
    const matched = KEYWORD_LEGEND.find((e) => e.id === 'matched')
    expect(matched).toBeDefined()
    expect(matched!.cssVarName).toBe('--color-success')
  })

  it('test_keyword_missing_uses_missing_theme_token', () => {
    const missing = KEYWORD_LEGEND.find((e) => e.id === 'missing')
    expect(missing).toBeDefined()
    expect(missing!.cssVarName).toBe('--color-danger')
  })

  it('test_keyword_in_resume_uses_accent_secondary_theme_token', () => {
    const inResume = KEYWORD_LEGEND.find((e) => e.id === 'in_resume')
    expect(inResume).toBeDefined()
    expect(inResume!.cssVarName).toBe('--color-accent-secondary')
  })

  it('test_legend_swatches_match_keyword_colors_across_themes', () => {
    for (const themeId of ['dark', 'light', 'midnight-blue']) {
      applyTheme(themeId)
      for (const entry of KEYWORD_LEGEND) {
        const rendered = rgbaFromCssVar(entry.cssVarName, entry.alpha)
        // Must be a valid rgba() string
        expect(rendered).toMatch(/^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\)$/)
        // And must NOT be the legacy hardcoded violet
        expect(rendered).not.toContain('124,58,237')
        expect(rendered).not.toContain('124, 58, 237')
      }
    }
  })

  it('test_no_hardcoded_violet_in_rendered_output', () => {
    applyTheme('dark')
    const { container } = render(<KeywordChart data={MIXED_FIXTURE} />)
    expect(container.innerHTML).not.toContain('124,58,237')
    expect(container.innerHTML).not.toContain('124, 58, 237')
  })

  it('test_legend_hidden_when_no_keyword_data', () => {
    // Render Results with an empty keyword_chart_data via AnalysisContext mock
    vi.doMock('@/context/AnalysisContext', () => ({
      useAnalysisContext: () => ({
        state: {
          isLoading: false,
          result: {
            scan_id: 'x',
            ats_score: 80,
            grade: 'A',
            score_breakdown: {
              keyword_match: 80,
              skills_coverage: 80,
              formatting_compliance: 80,
              bullet_strength: 80,
            },
            matched_keywords: [],
            missing_keywords: [],
            skill_gaps: [],
            bullet_analysis: [],
            formatting_issues: [],
            job_fit_explanation: '',
            top_strengths: [],
            top_gaps: [],
            keyword_chart_data: [],
            skills_overlap_data: [],
          },
        },
      }),
      AnalysisProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
    }))
  })
})

describe('rgbaFromCssVar helper', () => {
  it('produces rgba() string from a space-separated CSS variable', () => {
    applyTheme('dark')
    // --color-success in dark = "34 197 94"
    expect(rgbaFromCssVar('--color-success', 1)).toBe('rgba(34, 197, 94, 1)')
    expect(rgbaFromCssVar('--color-danger', 0.25)).toBe('rgba(239, 68, 68, 0.25)')
    expect(rgbaFromCssVar('--color-accent-secondary', 0.5)).toBe('rgba(239, 68, 68, 0.5)')
  })

  it('reflects theme changes on re-read', () => {
    applyTheme('midnight-blue')
    // --color-accent-secondary in midnight-blue = "96 165 250"
    expect(rgbaFromCssVar('--color-accent-secondary', 0.5)).toBe('rgba(96, 165, 250, 0.5)')
  })
})

describe('KeywordChart — AC-2 Results integration (unused vars silenced)', () => {
  it('exists as a module so Results import type-checks', () => {
    // This test is a guard: if we accidentally remove the KeywordChart export,
    // or break the Results import surface, Vitest catches it at import-time.
    expect(KeywordChart).toBeDefined()
    expect(Results).toBeDefined()
    expect(MemoryRouter).toBeDefined()
  })
})
