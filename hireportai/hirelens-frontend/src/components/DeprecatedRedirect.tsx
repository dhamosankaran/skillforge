import { useEffect } from 'react'
import { Navigate, useLocation, useParams } from 'react-router-dom'
import { capture } from '@/utils/posthog'

/**
 * Wraps `<Navigate replace />` for the transitional redirect block in
 * `App.tsx`. Fires PostHog `deprecated_route_hit` once on mount with
 * `{from_path, to_path}` so we can measure when the old paths stop
 * receiving hits and drop the redirect block in Phase 6 cleanup.
 *
 * Use `to` for static destinations or `build` for destinations that
 * substitute dynamic route params (React Router does NOT thread
 * params through `<Navigate to="/foo/:id">` — it would redirect to
 * the literal string).
 *
 * Spec: docs/specs/phase-5/12-navigation-restructure.md §Analytics.
 * Catalog: .agent/skills/analytics.md (`deprecated_route_hit`).
 */
export function DeprecatedRedirect(props: {
  to?: string
  build?: (params: Record<string, string>) => string
}) {
  const params = useParams()
  const location = useLocation()
  const resolvedTo = props.build
    ? props.build(params as Record<string, string>)
    : (props.to as string)

  useEffect(() => {
    capture('deprecated_route_hit', {
      from_path: location.pathname,
      to_path: resolvedTo,
    })
    // Mount-only fire; redirect unmounts the component immediately after.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return <Navigate to={resolvedTo} replace />
}
