import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Deck } from '@/types'

const adminListDecks = vi.fn()
const adminCreateDeck = vi.fn()
const captureMock = vi.fn()

vi.mock('@/services/api', () => ({
  adminListDecks: (...args: unknown[]) => adminListDecks(...args),
  adminCreateDeck: (...args: unknown[]) => adminCreateDeck(...args),
  adminUpdateDeck: vi.fn(),
  adminArchiveDeck: vi.fn(),
}))
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => captureMock(...args),
}))

import AdminDecks from '@/pages/admin/AdminDecks'

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

beforeEach(() => {
  adminListDecks.mockReset()
  adminCreateDeck.mockReset()
  captureMock.mockReset()
})

describe('AdminDecks (slice 6.4b)', () => {
  it('renders the deck list with status filter (D-16: active/archived/all)', async () => {
    adminListDecks.mockResolvedValue([deck()])
    render(
      <MemoryRouter>
        <AdminDecks />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByTestId('admin-decks-list')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('admin-decks-filter-active')).toBeInTheDocument()
    expect(screen.getByTestId('admin-decks-filter-archived')).toBeInTheDocument()
    expect(screen.getByTestId('admin-decks-filter-all')).toBeInTheDocument()
    expect(screen.getByText('System Design')).toBeInTheDocument()
    expect(adminListDecks).toHaveBeenCalledWith('active')
  })

  it('switching status refetches with the new filter', async () => {
    adminListDecks.mockResolvedValue([])
    render(
      <MemoryRouter>
        <AdminDecks />
      </MemoryRouter>,
    )
    await waitFor(() => expect(adminListDecks).toHaveBeenCalledWith('active'))
    fireEvent.click(screen.getByTestId('admin-decks-filter-archived'))
    await waitFor(() =>
      expect(adminListDecks).toHaveBeenCalledWith('archived'),
    )
  })

  it('submits create-deck form, fires admin_deck_created event', async () => {
    adminListDecks.mockResolvedValue([])
    adminCreateDeck.mockResolvedValue(deck({ id: 'new-deck', slug: 'new' }))
    render(
      <MemoryRouter>
        <AdminDecks />
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByTestId('admin-decks-toggle-create'))
    fireEvent.change(screen.getByPlaceholderText('system-design-fundamentals'), {
      target: { value: 'new' },
    })
    fireEvent.change(screen.getByLabelText(/Title/i), {
      target: { value: 'New Deck' },
    })
    fireEvent.change(screen.getByLabelText(/Description/i), {
      target: { value: 'desc' },
    })
    fireEvent.click(screen.getByTestId('admin-decks-submit-create'))
    await waitFor(() => expect(adminCreateDeck).toHaveBeenCalledOnce())
    await waitFor(() =>
      expect(captureMock).toHaveBeenCalledWith(
        'admin_deck_created',
        expect.objectContaining({ internal: true, slug: 'new' }),
      ),
    )
  })
})

describe('AdminDecks routing', () => {
  it('deck title links to /admin/decks/:deckId', async () => {
    adminListDecks.mockResolvedValue([deck({ id: 'deck-42' })])
    render(
      <MemoryRouter initialEntries={['/admin/decks']}>
        <Routes>
          <Route path="/admin/decks" element={<AdminDecks />} />
          <Route
            path="/admin/decks/:deckId"
            element={<div data-testid="page-deck-detail" />}
          />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => screen.getByText('System Design'))
    const link = screen.getByRole('link', { name: /System Design/i })
    expect(link).toHaveAttribute('href', '/admin/decks/deck-42')
  })
})
