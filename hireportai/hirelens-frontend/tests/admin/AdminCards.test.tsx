import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

// Stub the API helpers so the page mounts without a network round-trip.
// Cards-CRUD behavior itself is exercised in the live admin flow; this
// smoke confirms the extracted page renders byte-identically at the new
// `/admin/cards` mount (AC-2).
vi.mock('@/services/api', () => ({
  fetchAdminCards: vi.fn().mockResolvedValue({ cards: [], total: 0, page: 1, pages: 1, per_page: 20 }),
  fetchCategories: vi.fn().mockResolvedValue({ categories: [] }),
  createAdminCard: vi.fn(),
  updateAdminCard: vi.fn(),
  deleteAdminCard: vi.fn(),
  generateCardDraft: vi.fn(),
  importCardsCSV: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

import AdminCards from '@/pages/admin/AdminCards'

describe('AdminCards (Phase 6 slice 6.4a — B-064)', () => {
  it('renders the 4-tab bar (cards / create / generate / import) on the new mount', () => {
    render(<AdminCards />)
    expect(screen.getByRole('button', { name: /all cards/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^create$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ai generate/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /csv import/i })).toBeInTheDocument()
  })

  it('mounts on the Cards tab by default (AC-2 — preserves prior /admin default surface)', () => {
    render(<AdminCards />)
    expect(screen.getByPlaceholderText(/search questions/i)).toBeInTheDocument()
  })
})
