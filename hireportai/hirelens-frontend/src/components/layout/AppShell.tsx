import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { TopNav } from './TopNav'
import { MobileNav } from './MobileNav'

const CHROMELESS_PATHS = new Set(['/', '/login', '/pricing', '/onboarding/persona'])

export function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const showChrome = !CHROMELESS_PATHS.has(pathname)

  return (
    <>
      {showChrome && <TopNav />}
      <main className={showChrome ? 'pb-20 md:pb-0' : undefined}>{children}</main>
      {showChrome && <MobileNav />}
    </>
  )
}

export default AppShell
