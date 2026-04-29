import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser, Persona } from '@/context/AuthContext'
import type { Category, RankedDecksResponse } from '@/types'

// Phase 6 slice 6.7 — persona-aware Learn page tests.
// Spec: docs/specs/phase-6/08-persona-learn-page.md §10.1 + §11
// AC-1..AC-15. Per D-5 (locked) the persona modes are inline functions
// inside Learn.tsx, so the §10.2/§10.3 mode-isolation tests roll into
// this file (covering the same behavior via persona switching). The
// surfaced JC #1 explains the test-file-count divergence from spec
// §10's 4-file plan.

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchRankedDecks = vi.fn()
vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>(
    '@/services/api',
  )
  return {
    ...actual,
    fetchRankedDecks: (...args: unknown[]) => fetchRankedDecks(...args),
  }
})

// Stub the categories surface used by HabitMode's "Browse categories" section.
const categoriesFixture: Category[] = [
  {
    id: 'cat-1',
    name: 'JavaScript',
    icon: '🟨',
    color: '#f7df1e',
    display_order: 1,
    source: 'foundation',
    card_count: 10,
    studied_count: 0,
    locked: false,
  },
  {
    id: 'cat-2',
    name: 'React',
    icon: '⚛️',
    color: '#61dafb',
    display_order: 2,
    source: 'foundation',
    card_count: 8,
    studied_count: 0,
    locked: false,
  },
]
vi.mock('@/hooks/useStudyDashboard', () => ({
  useStudyDashboard: () => ({
    categories: categoriesFixture,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

let mockUser: AuthUser | null = null
vi.mock('@/context/AuthContext', async () => {
  const actual = await vi.importActual<typeof import('@/context/AuthContext')>(
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

vi.mock('@/context/UsageContext', async () => {
  const actual = await vi.importActual<typeof import('@/context/UsageContext')>(
    '@/context/UsageContext',
  )
  return {
    ...actual,
    useUsage: () => ({
      usage: { plan: 'free', isAdmin: false },
      setShowUpgradeModal: vi.fn(),
    }),
  }
})

vi.mock('@/context/GamificationContext', async () => {
  const actual = await vi.importActual<
    typeof import('@/context/GamificationContext')
  >('@/context/GamificationContext')
  return {
    ...actual,
    useGamification: () => ({
      stats: { current_streak: 0, longest_streak: 0, total_xp: 0 },
    }),
  }
})

// Stub the home/widgets used by Learn modes — they pull contexts we
// don't want to wire up for these page-level assertions.
vi.mock('@/components/home/widgets/TodaysReviewWidget', () => ({
  TodaysReviewWidget: () => <div data-testid="widget-todays-review" />,
}))
vi.mock('@/components/home/widgets/LastScanWidget', () => ({
  LastScanWidget: () => <div data-testid="widget-last-scan" />,
}))
vi.mock('@/components/home/widgets/StreakWidget', () => ({
  StreakWidget: () => <div data-testid="widget-streak" />,
}))
vi.mock('@/components/home/widgets/WeeklyProgressWidget', () => ({
  WeeklyProgressWidget: () => <div data-testid="widget-weekly-progress" />,
}))
vi.mock('@/components/home/widgets/TeamComingSoonWidget', () => ({
  TeamComingSoonWidget: () => <div data-testid="widget-team-coming-soon" />,
}))

import Learn from '@/pages/Learn'

function userFixture(persona: Persona | null): AuthUser {
  return {
    id: 'u1',
    email: 't@example.com',
    name: 'Dhamo',
    avatar_url: null,
    role: 'user',
    persona,
    onboarding_completed: true,
    home_first_visit_seen_at: '2026-04-01T00:00:00Z',
  }
}

function rankerFixture(
  overrides: Partial<RankedDecksResponse> = {},
): RankedDecksResponse {
  return {
    user_id: 'u1',
    persona: 'interview_prepper',
    cold_start: false,
    lookback_days: 30,
    recent_gap_count: 3,
    ranked_at: '2026-04-28T12:00:00Z',
    decks: [
      {
        deck: {
          id: 'd1',
          slug: 'llm-internals',
          title: 'LLM Internals',
          description: 'Transformers, attention, training.',
          display_order: 1,
          icon: null,
          persona_visibility: 'both',
          tier: 'foundation',
          created_at: '2026-04-01T00:00:00Z',
          updated_at: '2026-04-01T00:00:00Z',
          archived_at: null,
        },
        score: 0.72,
        rank: 1,
        matched_gaps: ['RAG', 'Embeddings'],
        score_breakdown: {
          gap_match: 0.8,
          fsrs_due: 0.5,
          avg_quality: 0.5,
          display_order_rank: 1,
        },
      },
    ],
    lessons: null,
    ...overrides,
  }
}

async function renderAt(initialEntry: string) {
  const result = render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Learn />
    </MemoryRouter>,
  )
  // Let the ranker promise resolve so effects settle.
  await act(async () => {
    await Promise.resolve()
  })
  return result
}

beforeEach(() => {
  capture.mockReset()
  fetchRankedDecks.mockReset()
  fetchRankedDecks.mockResolvedValue(rankerFixture())
  mockUser = null
})

describe('Learn — page mode routing (AC-1..AC-3)', () => {
  it('AC-1: renders LearnInterviewMode for interview_prepper', async () => {
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn')
    expect(screen.getByTestId('learn-mode-interview')).toBeInTheDocument()
    expect(screen.queryByTestId('learn-mode-habit')).toBeNull()
    expect(screen.queryByTestId('learn-mode-team')).toBeNull()
  })

  it('AC-2: renders LearnHabitMode for career_climber', async () => {
    mockUser = userFixture('career_climber')
    await renderAt('/learn')
    expect(screen.getByTestId('learn-mode-habit')).toBeInTheDocument()
    expect(screen.queryByTestId('learn-mode-interview')).toBeNull()
  })

  it('AC-3: renders LearnTeamMode for team_lead', async () => {
    mockUser = userFixture('team_lead')
    await renderAt('/learn')
    expect(screen.getByTestId('learn-mode-team')).toBeInTheDocument()
    expect(screen.queryByTestId('learn-mode-habit')).toBeNull()
  })

  it('AC-4: persona=null → page renders nothing (PersonaGate fires upstream)', async () => {
    mockUser = userFixture(null)
    await renderAt('/learn')
    expect(screen.queryByTestId('page-learn')).toBeNull()
  })
})

describe('Learn — ranker hook gating (AC-5/AC-6)', () => {
  it('AC-5: fetches ranked decks for interview_prepper', async () => {
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn')
    // Both the page-level telemetry call AND the IP-mode call fire —
    // see JC in Learn.tsx about the pragmatic-v1 double-fetch.
    expect(fetchRankedDecks).toHaveBeenCalled()
  })

  it('AC-5b: fetches ranked decks for team_lead (inherits IP behavior)', async () => {
    mockUser = userFixture('team_lead')
    await renderAt('/learn')
    expect(fetchRankedDecks).toHaveBeenCalled()
  })

  it('AC-6: career_climber still fetches the ranker for HabitMode "Curriculum suggestions" (D-4 expanded)', async () => {
    // Per spec §4.2 the page-level (telemetry) call skips for habit;
    // the HabitMode component fetches because §4.1 + D-4 render the
    // section expanded by default.
    mockUser = userFixture('career_climber')
    await renderAt('/learn')
    expect(fetchRankedDecks).toHaveBeenCalled()
  })
})

describe('Learn — cold-start UX (AC-7) + ranker render (AC-8)', () => {
  it('AC-7: cold_start=true renders cold-start CTA card with /prep/analyze target', async () => {
    fetchRankedDecks.mockResolvedValue(
      rankerFixture({ cold_start: true, recent_gap_count: 0, decks: [] }),
    )
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn')
    const cta = await screen.findByTestId('ranked-deck-list-cold-start')
    expect(cta).toBeInTheDocument()
    expect(cta.textContent).toContain('Take a scan to personalize your learning path')
    expect(cta.textContent).toContain(
      "We'll rank the lessons that close your skill gaps",
    )
  })

  it('AC-8: cold_start=false + decks renders one card per deck with matched_gaps chips', async () => {
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn')
    expect(
      await screen.findByTestId('ranked-deck-card-llm-internals'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('ranked-deck-card-llm-internals-gaps'),
    ).toBeInTheDocument()
  })
})

describe('Learn — HabitMode composition (AC-9 + D-4)', () => {
  it('AC-9: TodaysReview spine sits above StreakWidget which sits above the legacy categories grid', async () => {
    mockUser = userFixture('career_climber')
    await renderAt('/learn')
    const review = screen.getByTestId('widget-todays-review')
    const streak = screen.getByTestId('widget-streak')
    const categories = screen.getByTestId('learn-mode-habit-browse-categories')
    // DOM-order: review precedes streak precedes categories.
    expect(
      review.compareDocumentPosition(streak) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      streak.compareDocumentPosition(categories) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('D-4: Curriculum suggestions section renders expanded by default (no toggle)', async () => {
    mockUser = userFixture('career_climber')
    await renderAt('/learn')
    expect(
      screen.getByTestId('learn-mode-habit-curriculum-suggestions'),
    ).toBeInTheDocument()
    // RankedDeckList rendered inside, not collapsed behind a button.
    expect(screen.getByTestId('ranked-deck-list')).toBeInTheDocument()
  })
})

describe('Learn — query params (AC-10/AC-11/AC-12)', () => {
  it('AC-10: ?source=last_scan renders the spec #62 banner', async () => {
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn?source=last_scan')
    expect(
      screen.getByTestId('study-dashboard-source-hint'),
    ).toBeInTheDocument()
  })

  it('AC-10b: dismiss button hides banner', async () => {
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn?source=last_scan')
    fireEvent.click(screen.getByTestId('study-dashboard-source-hint-dismiss'))
    await waitFor(() =>
      expect(screen.queryByTestId('study-dashboard-source-hint')).toBeNull(),
    )
  })

  it('AC-11: ?category=cat-1 filters HabitMode browse grid to that category', async () => {
    mockUser = userFixture('career_climber')
    await renderAt('/learn?category=cat-1')
    // JavaScript visible, React filtered out.
    expect(screen.getByText('JavaScript')).toBeInTheDocument()
    expect(screen.queryByText('React')).toBeNull()
    expect(
      screen.getByTestId('learn-habit-clear-category-filter'),
    ).toBeInTheDocument()
  })

  it('AC-12: ?category=cat-1 silently ignored for interview_prepper (no error, no filter pill)', async () => {
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn?category=cat-1')
    // No filter pill in InterviewMode (HabitMode is the only consumer).
    expect(screen.queryByTestId('learn-habit-clear-category-filter')).toBeNull()
    // IP page renders normally.
    expect(screen.getByTestId('learn-mode-interview')).toBeInTheDocument()
  })
})

describe('Learn — analytics events (D-6 + D-8 + spec §9)', () => {
  it('learn_page_viewed fires once on mount with payload including persona/plan/mode/has_ranked_decks/cold_start', async () => {
    mockUser = userFixture('interview_prepper')
    await renderAt('/learn')
    const calls = capture.mock.calls.filter((c) => c[0] === 'learn_page_viewed')
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toMatchObject({
      persona: 'interview_prepper',
      plan: 'free',
      mode: 'interview',
      has_ranked_decks: true,
      cold_start: false,
    })
  })

  it('learn_mode_rendered fires once on mount via useRef (D-6)', async () => {
    mockUser = userFixture('habit' as Persona)
    mockUser.persona = 'career_climber'
    await renderAt('/learn')
    const calls = capture.mock.calls.filter(
      (c) => c[0] === 'learn_mode_rendered',
    )
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toEqual({ mode: 'habit', persona: 'career_climber' })
  })

  it('D-8: study_dashboard_source_hint_shown preserved verbatim (event name, payload, copy_variant=6A)', async () => {
    mockUser = userFixture('career_climber')
    await renderAt('/learn?source=last_scan')
    const calls = capture.mock.calls.filter(
      (c) => c[0] === 'study_dashboard_source_hint_shown',
    )
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toEqual({
      source: 'last_scan',
      persona: 'career_climber',
      copy_variant: '6A',
    })
  })

  it('study_dashboard_source_hint_shown does NOT re-fire on dismiss', async () => {
    mockUser = userFixture('career_climber')
    await renderAt('/learn?source=last_scan')
    fireEvent.click(screen.getByTestId('study-dashboard-source-hint-dismiss'))
    await waitFor(() =>
      expect(screen.queryByTestId('study-dashboard-source-hint')).toBeNull(),
    )
    const calls = capture.mock.calls.filter(
      (c) => c[0] === 'study_dashboard_source_hint_shown',
    )
    expect(calls).toHaveLength(1)
  })
})
