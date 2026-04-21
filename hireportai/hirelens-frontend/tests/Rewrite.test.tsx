import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { ReactNode } from 'react'
import type { RewriteResponse, RewriteSection } from '@/types'

// ─── Mocks ──────────────────────────────────────────────────────────────
const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const rewriteResume = vi.fn()
const rewriteSection = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    rewriteResume: (...args: unknown[]) => rewriteResume(...args),
    rewriteSection: (...args: unknown[]) => rewriteSection(...args),
  }
})

vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({
    usage: { plan: 'pro', scansUsed: 0, maxScans: Infinity },
    canScan: true,
    canUsePro: true,
    canUsePremium: true,
    incrementScan: vi.fn(),
    upgradePlan: vi.fn(),
    showUpgradeModal: false,
    setShowUpgradeModal: vi.fn(),
    checkAndPromptUpgrade: vi.fn(),
  }),
  UsageProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

const RESUME = 'Jane Doe\njane@example.com\n\nSummary\nEngineer.\n\nExperience\nACME.\n\nSkills\nPython.'
const JD = 'Senior Python engineer wanted.'.repeat(5)
vi.mock('@/context/AnalysisContext', () => ({
  useAnalysisContext: () => ({
    state: {
      isLoading: false,
      error: null,
      result: { resume_text: RESUME },
      resumeFile: null,
      jobDescription: JD,
    },
    dispatch: vi.fn(),
  }),
  AnalysisProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import Rewrite from '@/pages/Rewrite'

function renderRewrite() {
  return render(
    <MemoryRouter initialEntries={['/prep/rewrite']}>
      <Rewrite />
    </MemoryRouter>,
  )
}

function makeSection(title: string, content: string): RewriteSection {
  return {
    title,
    content,
    entries: [],
  }
}

const FIXTURE_6: RewriteResponse = {
  header: { name: 'Jane Doe', contact: 'jane@example.com | 555-1234' },
  sections: [
    makeSection('Contact', 'Jane Doe\njane@example.com'),
    makeSection('Summary', 'Seasoned engineer.'),
    makeSection('Experience', 'ACME — Senior Engineer.'),
    makeSection('Education', 'State University, BS CS.'),
    makeSection('Skills', 'Python, Go, Rust.'),
    makeSection('Projects', 'Side project: X.'),
  ],
  full_text: '## Contact\n...\n\n## Summary\n...',
  template_type: 'general',
}

beforeEach(() => {
  capture.mockReset()
  rewriteResume.mockReset()
  rewriteSection.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Rewrite page — structured section render (B-001 / spec #51)', () => {
  it('renders all 6 sections from a fixture RewriteResponse in order (AC-1)', async () => {
    const user = userEvent.setup()
    rewriteResume.mockResolvedValueOnce(FIXTURE_6)

    renderRewrite()
    await user.click(screen.getByRole('button', { name: /Generate AI Rewrite/i }))

    // All 6 sections rendered as data-testid nodes.
    await waitFor(() => expect(screen.getByTestId('rewrite-section-0')).toBeInTheDocument())
    for (let i = 0; i < 6; i++) {
      expect(screen.getByTestId(`rewrite-section-${i}`)).toBeInTheDocument()
    }

    // Order preserved: nodes are in the order we specified.
    const nodes = screen.getAllByTestId(/^rewrite-section-/)
    const titles = nodes.map((n) => n.getAttribute('data-section-title'))
    expect(titles).toEqual([
      'Contact',
      'Summary',
      'Experience',
      'Education',
      'Skills',
      'Projects',
    ])
  })

  it('fires rewrite_requested on Generate click', async () => {
    const user = userEvent.setup()
    rewriteResume.mockResolvedValueOnce(FIXTURE_6)

    renderRewrite()
    await user.click(screen.getByRole('button', { name: /Generate AI Rewrite/i }))

    expect(capture).toHaveBeenCalledWith(
      'rewrite_requested',
      expect.objectContaining({
        resume_char_length: RESUME.length,
        jd_char_length: JD.length,
      }),
    )
  })

  it('per-section regenerate replaces only the target section and leaves siblings unchanged (AC-4)', async () => {
    const user = userEvent.setup()
    rewriteResume.mockResolvedValueOnce(FIXTURE_6)

    renderRewrite()
    await user.click(screen.getByRole('button', { name: /Generate AI Rewrite/i }))
    await waitFor(() => expect(screen.getByTestId('rewrite-section-2')).toBeInTheDocument())

    // Before regen: Experience section content matches fixture.
    const experienceNode = screen.getByTestId('rewrite-section-2')
    expect(within(experienceNode).getByText(/ACME — Senior Engineer\./)).toBeInTheDocument()

    // Click Regenerate on Experience (index 2).
    rewriteSection.mockResolvedValueOnce({
      section_id: 'sec-2',
      section: makeSection('Experience', 'ACME — rewritten bullet.'),
    })
    const regenBtn = within(experienceNode).getByRole('button', {
      name: /Regenerate Experience section/i,
    })
    await user.click(regenBtn)

    // After regen: Experience content updated.
    await waitFor(() =>
      expect(within(screen.getByTestId('rewrite-section-2')).getByText(/rewritten bullet/)).toBeInTheDocument(),
    )

    // Sibling sections untouched.
    expect(
      within(screen.getByTestId('rewrite-section-1')).getByText(/Seasoned engineer\./),
    ).toBeInTheDocument()
    expect(
      within(screen.getByTestId('rewrite-section-3')).getByText(/State University/),
    ).toBeInTheDocument()
    expect(
      within(screen.getByTestId('rewrite-section-4')).getByText(/Python, Go, Rust\./),
    ).toBeInTheDocument()

    // API called exactly once with the target section's data.
    expect(rewriteSection).toHaveBeenCalledTimes(1)
    const call = rewriteSection.mock.calls[0]
    expect(call[0]).toBe('sec-2')        // section_id
    expect(call[1]).toBe('Experience')   // section_title
    expect(call[2]).toContain('ACME')    // section_text
    expect(call[3]).toBe(JD)             // jd_text

    // PostHog event fired.
    expect(capture).toHaveBeenCalledWith(
      'rewrite_section_regenerated',
      expect.objectContaining({ section_title: 'Experience' }),
    )
  })

  it('does not render a Regenerate button on the Contact section (contact is not rewritten)', async () => {
    const user = userEvent.setup()
    rewriteResume.mockResolvedValueOnce(FIXTURE_6)

    renderRewrite()
    await user.click(screen.getByRole('button', { name: /Generate AI Rewrite/i }))
    await waitFor(() => expect(screen.getByTestId('rewrite-section-0')).toBeInTheDocument())

    const contactNode = screen.getByTestId('rewrite-section-0')
    expect(contactNode.getAttribute('data-section-title')).toBe('Contact')
    expect(
      within(contactNode).queryByRole('button', { name: /Regenerate/i }),
    ).not.toBeInTheDocument()

    // But Experience (idx 2) does get a button.
    const experienceNode = screen.getByTestId('rewrite-section-2')
    expect(
      within(experienceNode).getByRole('button', { name: /Regenerate Experience section/i }),
    ).toBeInTheDocument()
  })
})
