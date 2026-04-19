/**
 * InterviewPrepperChecklist tests (Spec #41).
 *
 * Covers AC-1 (renders for Interview-Prepper), AC-2 (progress count),
 * AC-3 (step click → navigate), AC-4 (skip → localStorage hide),
 * AC-5 (celebration within 7d; auto-hide past 7d), AC-6 (never renders
 * for other personas).
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { ChecklistResponse } from '@/services/api'

// ── Mocks ────────────────────────────────────────────────────────────────

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchOnboardingChecklist = vi.fn()
vi.mock('@/services/api', () => ({
  fetchOnboardingChecklist: (...args: unknown[]) => fetchOnboardingChecklist(...args),
}))

let mockUser: AuthUser | null = {
  id: 'u1',
  email: 't@example.com',
  name: 'Test',
  avatar_url: null,
  role: 'user',
  persona: 'interview_prepper',
  onboarding_completed: true,
}
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
    updateUser: vi.fn(),
  }),
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

import { InterviewPrepperChecklist } from '@/components/home/widgets/InterviewPrepperChecklist'

function buildChecklist(overrides: Partial<ChecklistResponse> = {}): ChecklistResponse {
  const base: ChecklistResponse = {
    steps: [
      { id: 'scan_resume', title: 'Scan your resume', description: 'Get ATS score', link_target: '/prep/analyze', complete: false },
      { id: 'review_gaps', title: 'Review your gaps', description: 'See skills', link_target: '/prep/results', complete: false },
      { id: 'pick_category', title: 'Pick a study category', description: 'Focus', link_target: '/learn', complete: false },
      { id: 'set_mission', title: 'Set a mission', description: 'Sprint', link_target: '/learn/mission', complete: false },
      { id: 'first_review', title: 'Do your first daily review', description: 'Habit', link_target: '/learn/daily', complete: false },
    ],
    all_complete: false,
    completed_at: null,
  }
  return { ...base, ...overrides }
}

function renderWidget() {
  return render(
    <MemoryRouter>
      <InterviewPrepperChecklist />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  fetchOnboardingChecklist.mockReset()
  navigate.mockReset()
  localStorage.clear()
  mockUser = {
    id: 'u1',
    email: 't@example.com',
    name: 'Test',
    avatar_url: null,
    role: 'user',
    persona: 'interview_prepper',
    onboarding_completed: true,
  }
})

describe('InterviewPrepperChecklist', () => {
  it('renders for Interview-Prepper with correct progress count (AC-1, AC-2)', async () => {
    fetchOnboardingChecklist.mockResolvedValue(
      buildChecklist({
        steps: [
          { id: 'scan_resume', title: 'Scan your resume', description: '', link_target: '/prep/analyze', complete: true },
          { id: 'review_gaps', title: 'Review your gaps', description: '', link_target: '/prep/results', complete: true },
          { id: 'pick_category', title: 'Pick a study category', description: '', link_target: '/learn', complete: false },
          { id: 'set_mission', title: 'Set a mission', description: '', link_target: '/learn/mission', complete: false },
          { id: 'first_review', title: 'Do your first daily review', description: '', link_target: '/learn/daily', complete: false },
        ],
      }),
    )
    renderWidget()

    await screen.findByTestId('interview-prepper-checklist')
    expect(screen.getByText('Get started')).toBeInTheDocument()
    expect(screen.getByText(/2 of 5 done/)).toBeInTheDocument()
    await waitFor(() =>
      expect(capture).toHaveBeenCalledWith('checklist_shown', {
        complete_count: 2,
        all_complete: false,
      }),
    )
  })

  it('never renders for career_climber users (AC-6)', async () => {
    mockUser = { ...(mockUser as AuthUser), persona: 'career_climber' }
    fetchOnboardingChecklist.mockResolvedValue(buildChecklist())

    renderWidget()

    await new Promise((r) => setTimeout(r, 10))
    expect(screen.queryByTestId('interview-prepper-checklist')).not.toBeInTheDocument()
    expect(fetchOnboardingChecklist).not.toHaveBeenCalled()
  })

  it('navigates on step click (AC-3)', async () => {
    fetchOnboardingChecklist.mockResolvedValue(buildChecklist())
    renderWidget()

    await screen.findByTestId('interview-prepper-checklist')
    await userEvent.click(screen.getByTestId('checklist-step-scan_resume'))

    expect(navigate).toHaveBeenCalledWith('/prep/analyze')
    expect(capture).toHaveBeenCalledWith('checklist_step_clicked', {
      step_id: 'scan_resume',
    })
  })

  it('hides on Skip click and writes localStorage flag (AC-4)', async () => {
    fetchOnboardingChecklist.mockResolvedValue(buildChecklist())
    renderWidget()

    await screen.findByTestId('interview-prepper-checklist')
    await userEvent.click(screen.getByRole('button', { name: /skip checklist/i }))

    expect(localStorage.getItem('interview_prepper_checklist_skipped')).toBe('true')
    expect(capture).toHaveBeenCalledWith('checklist_skipped', { complete_count: 0 })
    expect(screen.queryByTestId('interview-prepper-checklist')).not.toBeInTheDocument()
  })

  it('shows the celebration state when all_complete within 7d (AC-5)', async () => {
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    fetchOnboardingChecklist.mockResolvedValue(
      buildChecklist({
        steps: buildChecklist().steps.map((s) => ({ ...s, complete: true })),
        all_complete: true,
        completed_at: yesterday,
      }),
    )
    renderWidget()

    await screen.findByTestId('interview-prepper-checklist')
    expect(screen.getByText(/you're all set/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument()
    await waitFor(() =>
      expect(capture).toHaveBeenCalledWith('checklist_completed', {
        completed_at: yesterday,
      }),
    )
  })

  it('auto-hides when all_complete > 7d ago (AC-5)', async () => {
    const tenDaysAgo = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString()
    fetchOnboardingChecklist.mockResolvedValue(
      buildChecklist({
        steps: buildChecklist().steps.map((s) => ({ ...s, complete: true })),
        all_complete: true,
        completed_at: tenDaysAgo,
      }),
    )
    renderWidget()

    await new Promise((r) => setTimeout(r, 20))
    expect(screen.queryByTestId('interview-prepper-checklist')).not.toBeInTheDocument()
  })
})
