import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AuthUser } from '@/context/AuthContext'
import type { LessonWithQuizzes } from '@/types'

// Slice 6.3 spec §10.2 — Lesson page tests.
// Mocks useLesson + AuthContext + UsageContext so the page renders
// past the loading state without hitting the API.

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const recordLessonView = vi.fn().mockResolvedValue(undefined)
vi.mock('@/services/api', async () => {
  const actual =
    await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    recordLessonView: (...args: unknown[]) => recordLessonView(...args),
  }
})

const lessonFixture: LessonWithQuizzes = {
  lesson: {
    id: 'lesson-fixture-attention-mechanism',
    deck_id: 'deck-fixture-transformer-llm-internals',
    slug: 'attention-mechanism',
    title: 'The Attention Mechanism',
    concept_md:
      '## Concept\n\nAttention is how a transformer **routes information**.',
    production_md:
      '## Production\n\n```bash\npip install torch transformers\n```',
    examples_md:
      '## Examples\n\n| Variant | Use |\n|---------|-----|\n| Self | encoder |\n| Cross | translation |\n',
    display_order: 0,
    version: 1,
    version_type: 'initial',
    published_at: '2026-04-27T00:00:00Z',
    generated_by_model: null,
    source_content_id: null,
    quality_score: null,
    created_at: '2026-04-27T00:00:00Z',
    updated_at: '2026-04-27T00:00:00Z',
    archived_at: null,
  },
  quiz_items: [
    {
      id: 'quiz-fixture-attention-1',
      lesson_id: 'lesson-fixture-attention-mechanism',
      question: 'What is a query vector?',
      answer: 'It represents what a token is looking for.',
      question_type: 'free_text',
      distractors: null,
      difficulty: 'easy',
      display_order: 0,
      version: 1,
      superseded_by_id: null,
      retired_at: null,
      generated_by_model: null,
      created_at: '2026-04-27T00:00:00Z',
      updated_at: '2026-04-27T00:00:00Z',
    },
  ],
  deck_id: 'deck-fixture-transformer-llm-internals',
  deck_slug: 'transformer-llm-internals',
  deck_title: 'Transformer LLM Internals',
}

let mockLesson: LessonWithQuizzes | null = lessonFixture
let mockError: 'not_found' | 'network' | null = null
let mockLoading = false

vi.mock('@/hooks/useLesson', () => ({
  useLesson: () => ({
    lesson: mockLesson,
    isLoading: mockLoading,
    error: mockError,
    reload: vi.fn(),
  }),
}))

const userFixture: AuthUser = {
  id: 'u1',
  email: 't@example.com',
  name: 'Tester',
  avatar_url: null,
  role: 'user',
  persona: 'career_climber',
  onboarding_completed: true,
  home_first_visit_seen_at: '2026-04-01T00:00:00Z',
}

vi.mock('@/context/AuthContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/AuthContext')>(
      '@/context/AuthContext',
    )
  return {
    ...actual,
    useAuth: () => ({
      user: userFixture,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      updateUser: vi.fn(),
    }),
  }
})

vi.mock('@/context/UsageContext', async () => {
  const actual =
    await vi.importActual<typeof import('@/context/UsageContext')>(
      '@/context/UsageContext',
    )
  return {
    ...actual,
    useUsage: () => ({
      usage: {
        plan: 'free',
        scansUsed: 0,
        maxScans: 1,
        isAdmin: false,
        rewritesUsed: 0,
        rewritesMax: 0,
        coverLettersUsed: 0,
        coverLettersMax: 0,
        interviewPrepsUsed: 0,
        interviewPrepsRemaining: 3,
        interviewPrepsMax: 3,
      },
      canScan: true,
      canUsePro: false,
      canUsePremium: false,
      refreshUsage: vi.fn(),
      upgradePlan: vi.fn(),
      showUpgradeModal: false,
      setShowUpgradeModal: vi.fn(),
      checkAndPromptUpgrade: () => false,
    }),
  }
})

import Lesson from '@/pages/Lesson'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/learn/lesson/:id" element={<Lesson />} />
        <Route path="/learn" element={<div>Learn Dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  recordLessonView.mockClear()
  mockLesson = lessonFixture
  mockError = null
  mockLoading = false
})

describe('Lesson page — slice 6.3', () => {
  it('renders concept, production, examples sections from Markdown', () => {
    renderAt('/learn/lesson/lesson-fixture-attention-mechanism')
    // Concept section is expanded by default → its body renders.
    expect(
      screen.getByText(/routes information/i, { selector: 'strong' }),
    ).toBeInTheDocument()
    // Section headings render for all four sections (concept / production /
    // examples / quiz).
    expect(screen.getAllByRole('heading', { level: 2 }).length).toBeGreaterThanOrEqual(4)
  })

  it('renders a GFM table from examples_md', () => {
    renderAt('/learn/lesson/lesson-fixture-attention-mechanism')
    const tables = document.querySelectorAll('table')
    expect(tables.length).toBeGreaterThanOrEqual(1)
  })

  it('renders fenced code blocks from production_md', () => {
    renderAt('/learn/lesson/lesson-fixture-attention-mechanism')
    const codeBlocks = document.querySelectorAll('pre')
    expect(codeBlocks.length).toBeGreaterThanOrEqual(1)
  })

  it('renders the not-found state when the hook returns error=not_found', () => {
    mockLesson = null
    mockError = 'not_found'
    renderAt('/learn/lesson/does-not-exist')
    expect(screen.getByText(/lesson not found/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to learn/i })).toBeInTheDocument()
  })

  it('fires lesson_viewed once on successful mount', () => {
    renderAt('/learn/lesson/lesson-fixture-attention-mechanism')
    const calls = capture.mock.calls.filter((c) => c[0] === 'lesson_viewed')
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toMatchObject({
      lesson_id: 'lesson-fixture-attention-mechanism',
      deck_id: 'deck-fixture-transformer-llm-internals',
      deck_slug: 'transformer-llm-internals',
      version: 1,
      persona: 'career_climber',
      plan: 'free',
    })
  })

  // Slice 6.0 AC-11 — recordLessonView fires alongside the existing
  // lesson_viewed PostHog capture on the same useEffect mount (D-10).
  it('calls recordLessonView alongside lesson_viewed PostHog capture', () => {
    renderAt('/learn/lesson/lesson-fixture-attention-mechanism')
    expect(recordLessonView).toHaveBeenCalledTimes(1)
    expect(recordLessonView).toHaveBeenCalledWith(
      'lesson-fixture-attention-mechanism',
      expect.objectContaining({
        deck_id: 'deck-fixture-transformer-llm-internals',
        version: 1,
        session_id: expect.any(String),
      }),
    )
  })
})
