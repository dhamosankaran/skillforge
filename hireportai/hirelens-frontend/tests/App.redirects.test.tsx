import { render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'

// ── Page component mocks ────────────────────────────────────────────────────
// Stubs let us assert routing independent of page internals (API calls,
// contexts, heavy markup). Each stub renders the same data-testid that the
// real page component exposes.

vi.mock('@/pages/Analyze',                  () => ({ default: () => <div data-testid="page-analyze" /> }))
vi.mock('@/pages/Results',                  () => ({ default: () => <div data-testid="page-results" /> }))
vi.mock('@/pages/Rewrite',                  () => ({ default: () => <div data-testid="page-rewrite" /> }))
vi.mock('@/pages/Interview',                () => ({ default: () => <div data-testid="page-interview" /> }))
vi.mock('@/pages/Tracker',                  () => ({ default: () => <div data-testid="page-tracker" /> }))
vi.mock('@/pages/StudyDashboard',           () => ({ default: () => <div data-testid="page-study-dashboard" /> }))
vi.mock('@/pages/DailyReview',              () => ({ default: () => <div data-testid="page-daily-review" /> }))
vi.mock('@/pages/CategoryDetail',           () => ({ default: () => <div data-testid="page-category-detail" /> }))
vi.mock('@/pages/CardViewer',               () => ({ default: () => <div data-testid="page-card-viewer" /> }))
vi.mock('@/pages/MissionMode',              () => ({ default: () => <div data-testid="page-mission-mode" /> }))
vi.mock('@/pages/HomeDashboard',            () => ({ default: () => <div data-testid="page-home-dashboard" /> }))
vi.mock('@/pages/LandingPage',              () => ({ default: () => <div data-testid="page-landing" /> }))
vi.mock('@/pages/LoginPage',                () => ({ default: () => <div data-testid="page-login" /> }))
vi.mock('@/pages/Pricing',                  () => ({ default: () => <div data-testid="page-pricing" /> }))
vi.mock('@/pages/Onboarding',               () => ({ default: () => <div data-testid="page-onboarding" /> }))
vi.mock('@/pages/Profile',                  () => ({ default: () => <div data-testid="page-profile" /> }))
vi.mock('@/pages/AdminPanel',               () => ({ default: () => <div data-testid="page-admin" /> }))

// Navbar is presentational; skip it so we don't need UsageContext / auth UI.
vi.mock('@/components/layout/Navbar', () => ({ Navbar: () => null }))

// PersonaPicker page — stubbed so ProtectedRoute redirects don't need its internals.
vi.mock('@/pages/PersonaPicker', () => ({
  default: () => <div data-testid="persona-picker" />,
}))

// Authenticated user with a persona set — PersonaGate lets the target page render.
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'u1',
      email: 't@example.com',
      name: 'Test',
      avatar_url: null,
      role: 'user',
      persona: 'career_climber',
      onboarding_completed: true,
    },
    isLoading: false,
    signIn: vi.fn(),
    signOut: vi.fn(),
    updateUser: vi.fn(),
  }),
}))

// Stub framer-motion's AnimatePresence so Suspense / async-lazy don't trip.
vi.mock('framer-motion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('framer-motion')>()
  return { ...actual, AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</> }
})

import App from '@/App'

// Exposes the router's current pathname as a data attribute so dynamic-redirect tests can
// assert the resolved URL (not just the component). Must live inside the MemoryRouter.
function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="location-probe" data-pathname={loc.pathname} />
}

interface RedirectCase {
  oldPath: string
  expectedTestId: string
}

// Static renamespaced routes. Dynamic routes (/study/category/:id, /study/card/:id) are
// covered separately below because they require asserting the resolved URL.
const cases: RedirectCase[] = [
  { oldPath: '/analyze',              expectedTestId: 'page-analyze' },
  { oldPath: '/results',              expectedTestId: 'page-results' },
  { oldPath: '/rewrite',              expectedTestId: 'page-rewrite' },
  { oldPath: '/interview',            expectedTestId: 'page-interview' },
  { oldPath: '/tracker',              expectedTestId: 'page-tracker' },
  { oldPath: '/study',                expectedTestId: 'page-study-dashboard' },
  { oldPath: '/study/daily',          expectedTestId: 'page-daily-review' },
  { oldPath: '/mission',              expectedTestId: 'page-mission-mode' },
]

describe('App transitional redirects', () => {
  it.each(cases)('redirects $oldPath to the new namespaced component', async ({ oldPath, expectedTestId }) => {
    render(
      <MemoryRouter initialEntries={[oldPath]}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByTestId(expectedTestId)).toBeInTheDocument()
  })

  it('redirects /study/category/:id to /learn/category/:id with the id substituted', async () => {
    render(
      <MemoryRouter initialEntries={['/study/category/abc-123']}>
        <App />
        <LocationProbe />
      </MemoryRouter>,
    )
    expect(await screen.findByTestId('page-category-detail')).toBeInTheDocument()
    expect(screen.getByTestId('location-probe')).toHaveAttribute('data-pathname', '/learn/category/abc-123')
  })

  it('redirects /study/card/:id to /learn/card/:id with the id substituted', async () => {
    render(
      <MemoryRouter initialEntries={['/study/card/xyz-789']}>
        <App />
        <LocationProbe />
      </MemoryRouter>,
    )
    expect(await screen.findByTestId('page-card-viewer')).toBeInTheDocument()
    expect(screen.getByTestId('location-probe')).toHaveAttribute('data-pathname', '/learn/card/xyz-789')
  })

  it('redirects bare /prep to /prep/analyze (B-034)', async () => {
    render(
      <MemoryRouter initialEntries={['/prep']}>
        <App />
        <LocationProbe />
      </MemoryRouter>,
    )
    expect(await screen.findByTestId('page-analyze')).toBeInTheDocument()
    expect(screen.getByTestId('location-probe')).toHaveAttribute('data-pathname', '/prep/analyze')
  })

  it('renders the HomeDashboard at /home', async () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByTestId('page-home-dashboard')).toBeInTheDocument()
  })
})
