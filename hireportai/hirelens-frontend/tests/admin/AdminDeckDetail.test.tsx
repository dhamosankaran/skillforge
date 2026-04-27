import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Deck, Lesson } from '@/types'

const adminListDecks = vi.fn()
const adminListLessons = vi.fn()
const adminUpdateDeck = vi.fn()
const adminArchiveDeck = vi.fn()
const captureMock = vi.fn()

vi.mock('@/services/api', () => ({
  adminListDecks: (...args: unknown[]) => adminListDecks(...args),
  adminListLessons: (...args: unknown[]) => adminListLessons(...args),
  adminUpdateDeck: (...args: unknown[]) => adminUpdateDeck(...args),
  adminArchiveDeck: (...args: unknown[]) => adminArchiveDeck(...args),
  adminCreateLesson: vi.fn(),
}))
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => captureMock(...args),
}))

import AdminDeckDetail from '@/pages/admin/AdminDeckDetail'

function deck(overrides: Partial<Deck> = {}): Deck {
  return {
    id: 'deck-1',
    slug: 'system-design',
    title: 'System Design',
    description: 'desc',
    display_order: 0,
    icon: null,
    persona_visibility: 'both',
    tier: 'premium',
    created_at: '2026-04-27T00:00:00Z',
    updated_at: '2026-04-27T00:00:00Z',
    archived_at: null,
    ...overrides,
  }
}

function lesson(overrides: Partial<Lesson> = {}): Lesson {
  return {
    id: 'lesson-1',
    deck_id: 'deck-1',
    slug: 'introduction',
    title: 'Introduction',
    concept_md: 'concept',
    production_md: 'production',
    examples_md: 'examples',
    display_order: 0,
    version: 1,
    version_type: 'initial',
    published_at: null,
    generated_by_model: null,
    source_content_id: null,
    quality_score: null,
    created_at: '2026-04-27T00:00:00Z',
    updated_at: '2026-04-27T00:00:00Z',
    archived_at: null,
    ...overrides,
  }
}

function renderAt(deckId: string) {
  return render(
    <MemoryRouter initialEntries={[`/admin/decks/${deckId}`]}>
      <Routes>
        <Route path="/admin/decks" element={<div data-testid="page-decks" />} />
        <Route path="/admin/decks/:deckId" element={<AdminDeckDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  adminListDecks.mockReset()
  adminListLessons.mockReset()
  adminUpdateDeck.mockReset()
  adminArchiveDeck.mockReset()
  captureMock.mockReset()
})

describe('AdminDeckDetail (slice 6.4b)', () => {
  it('loads the deck plus its lessons and renders both', async () => {
    adminListDecks.mockResolvedValue([deck()])
    adminListLessons.mockResolvedValue([lesson()])
    renderAt('deck-1')
    await waitFor(() =>
      expect(screen.getByTestId('admin-deck-detail-form')).toBeInTheDocument(),
    )
    expect(screen.getAllByText('System Design').length).toBeGreaterThan(0)
    expect(screen.getByText('Introduction')).toBeInTheDocument()
  })

  it('archive button calls adminArchiveDeck and fires admin_deck_archived', async () => {
    adminListDecks.mockResolvedValue([deck()])
    adminListLessons.mockResolvedValue([])
    adminArchiveDeck.mockResolvedValue(deck({ archived_at: '2026-04-27T00:00:00Z' }))
    renderAt('deck-1')
    const archiveBtn = await screen.findByTestId('admin-deck-detail-archive')
    fireEvent.click(archiveBtn)
    await waitFor(() => expect(adminArchiveDeck).toHaveBeenCalledWith('deck-1'))
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_deck_archived',
        expect.objectContaining({ deck_id: 'deck-1', internal: true }),
      ),
    )
  })

  it('narrowing persona_visibility opens the ConfirmPersonaNarrowingModal', async () => {
    adminListDecks.mockResolvedValue([deck({ persona_visibility: 'both' })])
    adminListLessons.mockResolvedValue([])
    renderAt('deck-1')
    await screen.findByTestId('admin-deck-detail-form')

    fireEvent.change(screen.getByTestId('admin-deck-detail-persona'), {
      target: { value: 'climber' },
    })
    fireEvent.click(screen.getByTestId('admin-deck-detail-save'))

    await waitFor(() =>
      expect(
        screen.getByTestId('confirm-persona-narrow-modal'),
      ).toBeInTheDocument(),
    )
    expect(screen.getByTestId('confirm-persona-narrow-copy')).toHaveTextContent(
      /interview_prepper/,
    )
    // Modal must NOT have fired the PATCH yet — admin still has to confirm.
    expect(adminUpdateDeck).not.toHaveBeenCalled()
  })
})
