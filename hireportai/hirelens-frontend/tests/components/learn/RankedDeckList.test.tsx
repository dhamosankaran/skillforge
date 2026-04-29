import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { RankedDeck, RankedDecksResponse } from '@/types'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  )
  return {
    ...actual,
    useNavigate: () => navigate,
  }
})

import { RankedDeckList } from '@/components/learn/RankedDeckList'

function deckFixture(overrides: Partial<RankedDeck['deck']> = {}): RankedDeck {
  return {
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
      ...overrides,
    },
    score: 0.8,
    rank: 1,
    matched_gaps: ['RAG'],
    score_breakdown: {
      gap_match: 0.9,
      fsrs_due: 0.5,
      avg_quality: 0.5,
      display_order_rank: 1,
    },
  }
}

function responseFixture(
  overrides: Partial<RankedDecksResponse> = {},
): RankedDecksResponse {
  return {
    user_id: 'u1',
    persona: 'interview_prepper',
    cold_start: false,
    lookback_days: 30,
    recent_gap_count: 2,
    ranked_at: '2026-04-28T12:00:00Z',
    decks: [deckFixture()],
    lessons: null,
    ...overrides,
  }
}

function renderList(props: {
  data?: RankedDecksResponse | null
  isLoading?: boolean
  error?: Error | null
}) {
  return render(
    <MemoryRouter>
      <RankedDeckList
        data={props.data ?? null}
        isLoading={props.isLoading ?? false}
        error={props.error ?? null}
        persona="interview_prepper"
        plan="free"
      />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  navigate.mockReset()
})

describe('RankedDeckList — render branches', () => {
  it('isLoading renders the skeleton placeholder', () => {
    renderList({ isLoading: true })
    expect(screen.getByTestId('ranked-deck-list-loading')).toBeInTheDocument()
  })

  it('error state renders error block', () => {
    renderList({ error: new Error('boom') })
    expect(screen.getByTestId('ranked-deck-list-error')).toBeInTheDocument()
  })

  it('cold_start=true renders cold-start CTA with verbose copy (D-7)', () => {
    renderList({
      data: responseFixture({ cold_start: true, decks: [], recent_gap_count: 0 }),
    })
    const cta = screen.getByTestId('ranked-deck-list-cold-start')
    expect(cta.textContent).toContain('Take a scan to personalize your learning path.')
    expect(cta.textContent).toContain(
      "We'll rank the lessons that close your skill gaps.",
    )
  })

  it('cold-start CTA button navigates to /prep/analyze', () => {
    renderList({
      data: responseFixture({ cold_start: true, decks: [] }),
    })
    fireEvent.click(screen.getByTestId('ranked-deck-list-cold-start-cta'))
    expect(navigate).toHaveBeenCalledWith('/prep/analyze')
  })

  it('empty list (decks=[], cold_start=false) renders D-2 actionable copy', () => {
    renderList({ data: responseFixture({ decks: [] }) })
    const empty = screen.getByTestId('ranked-deck-list-empty')
    expect(empty.textContent).toContain(
      'No decks match your profile yet — scan your resume to get personalized recommendations.',
    )
  })

  it('renders one card per deck with matched_gap chips', () => {
    renderList({
      data: responseFixture({
        decks: [
          deckFixture({ id: 'd1', slug: 'llm-internals', title: 'LLM Internals' }),
          deckFixture({ id: 'd2', slug: 'react-perf', title: 'React Perf' }),
        ],
      }),
    })
    expect(screen.getByTestId('ranked-deck-card-llm-internals')).toBeInTheDocument()
    expect(screen.getByTestId('ranked-deck-card-react-perf')).toBeInTheDocument()
    expect(
      screen.getByTestId('ranked-deck-card-llm-internals-gaps'),
    ).toBeInTheDocument()
  })
})

describe('RankedDeckList — click telemetry + nav (§9)', () => {
  it('deck-card click fires learn_deck_clicked with rank/persona/plan/score/matched_gap_count', () => {
    renderList({ data: responseFixture() })
    fireEvent.click(screen.getByTestId('ranked-deck-card-llm-internals'))
    const calls = capture.mock.calls.filter((c) => c[0] === 'learn_deck_clicked')
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toMatchObject({
      deck_slug: 'llm-internals',
      deck_position: 1,
      persona: 'interview_prepper',
      plan: 'free',
      score: 0.8,
      matched_gap_count: 1,
      is_cold_start: false,
    })
  })

  it('deck-card click navigates to /learn fallback when no resolveFirstLessonId provided', () => {
    renderList({ data: responseFixture() })
    fireEvent.click(screen.getByTestId('ranked-deck-card-llm-internals'))
    expect(navigate).toHaveBeenCalledWith('/learn')
  })
})
