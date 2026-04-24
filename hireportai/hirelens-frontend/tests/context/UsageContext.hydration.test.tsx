import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { UsageProvider, useUsage } from '@/context/UsageContext'

// ─── Mocks ────────────────────────────────────────────────────────────────

const mockFetchUsage = vi.fn()
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>()
  return {
    ...actual,
    fetchUsage: (...args: unknown[]) => mockFetchUsage(...args),
  }
})

// ─── Harness ──────────────────────────────────────────────────────────────

function Probe() {
  const { usage, canScan, canUsePro } = useUsage()
  return (
    <>
      <span data-testid="plan">{usage.plan}</span>
      <span data-testid="scans-used">{usage.scansUsed}</span>
      <span data-testid="max-scans">{usage.maxScans}</span>
      <span data-testid="is-admin">{String(usage.isAdmin)}</span>
      <span data-testid="can-scan">{String(canScan)}</span>
      <span data-testid="can-use-pro">{String(canUsePro)}</span>
    </>
  )
}

function renderProvider() {
  return render(
    <UsageProvider>
      <Probe />
    </UsageProvider>,
  )
}

describe('UsageContext — BE hydration (spec #56 LD-2)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('hydrates plan + counts from /payments/usage on mount', async () => {
    mockFetchUsage.mockResolvedValueOnce({
      plan: 'free',
      scans_used: 0,
      scans_remaining: 1,
      max_scans: 1,
      is_admin: false,
    })
    renderProvider()

    await waitFor(() => {
      expect(mockFetchUsage).toHaveBeenCalledTimes(1)
    })
    await waitFor(() => {
      expect(screen.getByTestId('max-scans').textContent).toBe('1')
    })
    expect(screen.getByTestId('plan').textContent).toBe('free')
    expect(screen.getByTestId('scans-used').textContent).toBe('0')
    expect(screen.getByTestId('is-admin').textContent).toBe('false')
    expect(screen.getByTestId('can-scan').textContent).toBe('true')
  })

  it('free user with 1 prior scan has canScan=false — AC-7 localStorage is non-authoritative', async () => {
    // Seed localStorage with a "0 scans used" shape that would grant a scan
    // under the old localStorage-authoritative regime. BE response must win.
    localStorage.setItem(
      'skillforge_usage',
      JSON.stringify({ plan: 'free', scansUsed: 0, maxScans: 1, isAdmin: false }),
    )
    mockFetchUsage.mockResolvedValueOnce({
      plan: 'free',
      scans_used: 1,
      scans_remaining: 0,
      max_scans: 1,
      is_admin: false,
    })
    renderProvider()

    await waitFor(() => {
      expect(screen.getByTestId('scans-used').textContent).toBe('1')
    })
    expect(screen.getByTestId('can-scan').textContent).toBe('false')
  })

  it('pro user is unlimited via -1 sentinel', async () => {
    mockFetchUsage.mockResolvedValueOnce({
      plan: 'pro',
      scans_used: 42,
      scans_remaining: -1,
      max_scans: -1,
      is_admin: false,
    })
    renderProvider()

    await waitFor(() => {
      expect(screen.getByTestId('plan').textContent).toBe('pro')
    })
    expect(screen.getByTestId('can-scan').textContent).toBe('true')
    expect(screen.getByTestId('can-use-pro').textContent).toBe('true')
  })

  it('admin on free plan reads unlimited via is_admin bypass', async () => {
    mockFetchUsage.mockResolvedValueOnce({
      plan: 'free',
      scans_used: 17,
      scans_remaining: -1,
      max_scans: -1,
      is_admin: true,
    })
    renderProvider()

    await waitFor(() => {
      expect(screen.getByTestId('is-admin').textContent).toBe('true')
    })
    expect(screen.getByTestId('plan').textContent).toBe('free')
    expect(screen.getByTestId('can-scan').textContent).toBe('true')
    expect(screen.getByTestId('can-use-pro').textContent).toBe('true')
  })

  it('network failure falls back to cached display state (not authoritative)', async () => {
    localStorage.setItem(
      'skillforge_usage',
      JSON.stringify({ plan: 'pro', scansUsed: 5, maxScans: -1, isAdmin: false }),
    )
    mockFetchUsage.mockRejectedValueOnce(new Error('network down'))
    renderProvider()

    // Cache survives; mount stays usable.
    await waitFor(() => {
      expect(mockFetchUsage).toHaveBeenCalledTimes(1)
    })
    expect(screen.getByTestId('plan').textContent).toBe('pro')
    expect(screen.getByTestId('can-scan').textContent).toBe('true')
  })
})
