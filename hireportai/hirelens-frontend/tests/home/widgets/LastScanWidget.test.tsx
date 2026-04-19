import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { TrackerApplication } from '@/types'

const fetchUserApplications = vi.fn()
vi.mock('@/services/api', () => ({
  fetchUserApplications: (...args: unknown[]) => fetchUserApplications(...args),
}))

import { LastScanWidget } from '@/components/home/widgets/LastScanWidget'

function renderWidget() {
  return render(
    <MemoryRouter>
      <LastScanWidget persona="career_climber" />
    </MemoryRouter>,
  )
}

function app(overrides: Partial<TrackerApplication> = {}): TrackerApplication {
  return {
    id: 'a1',
    company: 'Acme',
    role: 'Engineer',
    date_applied: '2026-04-01',
    ats_score: 82,
    status: 'Applied',
    scan_id: 'scan-1',
    skills_matched: null,
    skills_missing: null,
    created_at: '2026-04-01T00:00:00Z',
    ...overrides,
  }
}

beforeEach(() => {
  fetchUserApplications.mockReset()
})

describe('LastScanWidget', () => {
  it('renders a skeleton in the loading state', () => {
    fetchUserApplications.mockReturnValue(new Promise(() => {}))
    const { container } = renderWidget()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders the latest app (by created_at desc) with scan_id in View results link', async () => {
    fetchUserApplications.mockResolvedValueOnce([
      app({ id: 'old', company: 'Old', created_at: '2026-01-01T00:00:00Z' }),
      app({
        id: 'latest',
        company: 'Google',
        role: 'Senior SWE',
        ats_score: 91,
        scan_id: 'scan-latest',
        created_at: '2026-04-15T00:00:00Z',
      }),
    ])
    renderWidget()
    expect(await screen.findByText('Google')).toBeInTheDocument()
    expect(screen.getByText('Senior SWE')).toBeInTheDocument()
    expect(screen.getByText('91%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view results/i })).toHaveAttribute(
      'href',
      '/prep/results?scan_id=scan-latest',
    )
  })

  it('renders the empty state when no applications exist', async () => {
    fetchUserApplications.mockResolvedValueOnce([])
    renderWidget()
    expect(
      await screen.findByText(/run your first scan to see results/i),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /scan a resume/i }),
    ).toHaveAttribute('href', '/prep/analyze')
  })

  it('renders no company/role/ATS score when api returns empty (AC-1, AC-3)', async () => {
    // Regression test for the cross-user data leak that motivated spec #44.
    // When the data source is empty, the widget must not render any text
    // that resembles real user scan data (company name, role, ATS %).
    fetchUserApplications.mockResolvedValueOnce([])
    renderWidget()

    // Wait for the empty-state transition (anchors on the CTA).
    await screen.findByText(/run your first scan to see results/i)
    const widget = screen.getByTestId('widget-last-scan')

    // No "ATS score:" label, no percentage, no "View results" link.
    expect(within(widget).queryByText(/ats score:/i)).not.toBeInTheDocument()
    expect(within(widget).queryByText(/\d+%/)).not.toBeInTheDocument()
    expect(
      within(widget).queryByRole('link', { name: /view results/i }),
    ).not.toBeInTheDocument()
  })

  it('renders the error state + retry re-fetches', async () => {
    fetchUserApplications.mockRejectedValueOnce(new Error('boom'))
    renderWidget()
    expect(
      await screen.findByText(/couldn't load your last scan/i),
    ).toBeInTheDocument()

    fetchUserApplications.mockResolvedValueOnce([app({ company: 'Recovered' })])
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: /try again/i }))
    await waitFor(() =>
      expect(fetchUserApplications).toHaveBeenCalledTimes(2),
    )
    expect(await screen.findByText('Recovered')).toBeInTheDocument()
  })
})
