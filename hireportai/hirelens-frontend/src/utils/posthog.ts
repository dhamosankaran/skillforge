/**
 * PostHog analytics wrapper.
 *
 * Initialised once on first import. If VITE_POSTHOG_KEY is not set
 * (e.g. local dev without a key), all capture calls are silently dropped
 * so no console errors appear.
 */
import posthog from 'posthog-js'

const key = import.meta.env.VITE_POSTHOG_KEY as string | undefined
const host = (import.meta.env.VITE_POSTHOG_HOST as string | undefined) || 'https://app.posthog.com'

if (key) {
  posthog.init(key, {
    api_host: host,
    capture_pageview: false, // we fire events manually per route
    persistence: 'localStorage',
    autocapture: false,
  })
}

/** Fire a PostHog event. No-op if PostHog is not initialised. */
export function capture(event: string, properties?: Record<string, unknown>): void {
  if (!key) return
  posthog.capture(event, properties)
}

export default posthog
