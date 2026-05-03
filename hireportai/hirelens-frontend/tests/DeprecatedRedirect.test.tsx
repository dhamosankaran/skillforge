/**
 * DeprecatedRedirect — mounts a Navigate redirect AND fires
 * `deprecated_route_hit` PostHog event with from_path/to_path (B-008).
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

import { DeprecatedRedirect } from '@/components/DeprecatedRedirect'

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="probe" data-pathname={loc.pathname} />
}

beforeEach(() => {
  capture.mockReset()
})

describe('DeprecatedRedirect', () => {
  it('navigates to the static `to` destination and fires deprecated_route_hit', () => {
    render(
      <MemoryRouter initialEntries={['/old']}>
        <Routes>
          <Route path="/old" element={<DeprecatedRedirect to="/new" />} />
          <Route path="/new" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('probe')).toHaveAttribute('data-pathname', '/new')
    expect(capture).toHaveBeenCalledTimes(1)
    expect(capture).toHaveBeenCalledWith('deprecated_route_hit', {
      from_path: '/old',
      to_path: '/new',
    })
  })

  it('substitutes route params via `build` and reports the resolved to_path', () => {
    render(
      <MemoryRouter initialEntries={['/study/category/abc-123']}>
        <Routes>
          <Route
            path="/study/category/:id"
            element={<DeprecatedRedirect build={(p) => `/learn/category/${p.id}`} />}
          />
          <Route path="/learn/category/:id" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('probe')).toHaveAttribute(
      'data-pathname',
      '/learn/category/abc-123',
    )
    expect(capture).toHaveBeenCalledWith('deprecated_route_hit', {
      from_path: '/study/category/abc-123',
      to_path: '/learn/category/abc-123',
    })
  })

  it('fires the event exactly once even after redirect lands and re-renders', () => {
    const { rerender } = render(
      <MemoryRouter initialEntries={['/old']}>
        <Routes>
          <Route path="/old" element={<DeprecatedRedirect to="/new" />} />
          <Route path="/new" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
    rerender(
      <MemoryRouter initialEntries={['/old']}>
        <Routes>
          <Route path="/old" element={<DeprecatedRedirect to="/new" />} />
          <Route path="/new" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
    // Fresh remount fires once each — first render mount + second render mount.
    // Critical: a single mount must not double-fire (mount-only effect).
    expect(capture.mock.calls.every(([name]) => name === 'deprecated_route_hit')).toBe(true)
  })
})
