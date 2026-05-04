import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { TopNav } from './TopNav'
import { MobileNav } from './MobileNav'
import { LoopProgressStrip } from './LoopProgressStrip'

const CHROMELESS_PATHS = new Set(['/', '/login', '/onboarding/persona', '/first-action'])

export function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const { user } = useAuth()
  // /pricing is chromeless for guests (matches Stripe/Linear/Notion) but shows
  // chrome for authed users so they can escape after a mid-flow paywall hit.
  const isGuestPricing = pathname === '/pricing' && user === null
  const showChrome = !CHROMELESS_PATHS.has(pathname) && !isGuestPricing

  return (
    <>
      {showChrome && <TopNav />}
      {/* Spec #66 / D-8 — sibling below TopNav. Internal render gate
          handles persona + next_interview suppression; chromeless paths
          gated here so the strip never mounts when chrome is hidden. */}
      {showChrome && <LoopProgressStrip />}
      <main className={showChrome ? 'pb-20 md:pb-0' : undefined}>{children}</main>
      {showChrome && <MobileNav />}
    </>
  )
}

export default AppShell
