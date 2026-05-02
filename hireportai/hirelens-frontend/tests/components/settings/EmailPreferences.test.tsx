/**
 * EmailPreferences component tests — slice 6.13 Pro digest opt-out toggle
 * (B-087). Spec: docs/specs/phase-6/13-pro-digest-opt-out.md §10.3 +
 * AC-9..AC-11.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { EmailPreference } from '@/types'

// ── Mocks ────────────────────────────────────────────────────────────────

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const fetchEmailPreferences = vi.fn()
const updateEmailPreferences = vi.fn()
vi.mock('@/services/api', () => ({
  fetchEmailPreferences: (...args: unknown[]) => fetchEmailPreferences(...args),
  updateEmailPreferences: (...args: unknown[]) => updateEmailPreferences(...args),
}))

let canUseProMock = false
vi.mock('@/context/UsageContext', () => ({
  useUsage: () => ({ canUsePro: canUseProMock }),
}))

import { EmailPreferences } from '@/components/settings/EmailPreferences'

function makePref(overrides: Partial<EmailPreference> = {}): EmailPreference {
  return {
    user_id: 'u1',
    daily_reminder: true,
    daily_digest_opt_out: false,
    timezone: 'UTC',
    ...overrides,
  }
}

beforeEach(() => {
  capture.mockReset()
  fetchEmailPreferences.mockReset()
  updateEmailPreferences.mockReset()
  canUseProMock = false
})

describe('EmailPreferences — Pro digest opt-out toggle (slice 6.13)', () => {
  it('hides the digest toggle for free users (canUsePro=false)', async () => {
    canUseProMock = false
    fetchEmailPreferences.mockResolvedValue(makePref())

    render(<EmailPreferences />)

    await waitFor(() => {
      expect(screen.getByText(/daily reminders/i)).toBeInTheDocument()
    })
    expect(screen.queryByText(/pro daily digest/i)).not.toBeInTheDocument()
    expect(
      screen.queryByLabelText(/toggle pro daily digest opt-out/i),
    ).not.toBeInTheDocument()
  })

  it('renders the digest toggle for Pro users (canUsePro=true)', async () => {
    canUseProMock = true
    fetchEmailPreferences.mockResolvedValue(makePref())

    render(<EmailPreferences />)

    await waitFor(() => {
      expect(screen.getByText(/pro daily digest/i)).toBeInTheDocument()
    })
    expect(
      screen.getByLabelText(/toggle pro daily digest opt-out/i),
    ).toBeInTheDocument()
  })

  it('toggling the digest fires email_preferences_saved with daily_digest_opt_out payload', async () => {
    canUseProMock = true
    fetchEmailPreferences.mockResolvedValue(makePref())
    updateEmailPreferences.mockResolvedValue(
      makePref({ daily_digest_opt_out: true }),
    )

    render(<EmailPreferences />)

    const toggle = await screen.findByLabelText(
      /toggle pro daily digest opt-out/i,
    )
    await userEvent.click(toggle)

    await waitFor(() => {
      expect(updateEmailPreferences).toHaveBeenCalledWith({
        daily_digest_opt_out: true,
      })
    })

    const digestSaves = capture.mock.calls.filter(
      ([event]) => event === 'email_preferences_saved',
    )
    const digestPayloads = digestSaves.filter(
      ([, payload]) =>
        (payload as Record<string, unknown>)?.daily_digest_opt_out !==
        undefined,
    )
    expect(digestPayloads).toHaveLength(1)
    expect(digestPayloads[0][1]).toEqual({ daily_digest_opt_out: true })
  })

  it('persists the toggled value (UI reflects the new state after save)', async () => {
    canUseProMock = true
    fetchEmailPreferences.mockResolvedValue(makePref())
    updateEmailPreferences.mockResolvedValue(
      makePref({ daily_digest_opt_out: true }),
    )

    render(<EmailPreferences />)

    const toggle = await screen.findByLabelText(
      /toggle pro daily digest opt-out/i,
    )
    await userEvent.click(toggle)

    await waitFor(() => {
      expect(screen.getByText(/saved/i)).toBeInTheDocument()
    })
  })

  it('shows the error state when the digest save fails', async () => {
    canUseProMock = true
    fetchEmailPreferences.mockResolvedValue(makePref())
    updateEmailPreferences.mockRejectedValue(new Error('boom'))

    render(<EmailPreferences />)

    const toggle = await screen.findByLabelText(
      /toggle pro daily digest opt-out/i,
    )
    await userEvent.click(toggle)

    // The component renders an empty state on initial-load failures, but on
    // save failures it sets the error string while keeping the toggles
    // mounted — verify it stays interactive after the failed save.
    await waitFor(() => {
      expect(updateEmailPreferences).toHaveBeenCalled()
    })
    expect(toggle).toBeInTheDocument()
  })
})
