import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { TopNav } from './TopNav'
import { MobileNav } from './MobileNav'

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
      <main className={showChrome ? 'pb-20 md:pb-0' : undefined}>{children}</main>
      {showChrome && <MobileNav />}
    </>
  )
}

export default AppShell
