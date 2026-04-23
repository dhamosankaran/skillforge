import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { useAuth } from '@/context/AuthContext'
import { capture } from '@/utils/posthog'
import { UserMenu } from '@/components/layout/UserMenu'

interface NavItem {
  label: string
  to: string
  prefix: string
  exact?: boolean
  adminOnly?: boolean
}

// Profile deliberately not listed here (B-029). Desktop users reach it via
// the UserMenu avatar dropdown on the right. MobileNav keeps the Profile tab
// because the mobile layout has no UserMenu — it's the only path to
// Sign out on mobile (Profile → Account section).
const NAV_ITEMS: NavItem[] = [
  { label: 'Home',    to: '/home',    prefix: '/home',    exact: true },
  { label: 'Learn',   to: '/learn',   prefix: '/learn' },
  { label: 'Prep',    to: '/prep',    prefix: '/prep' },
  { label: 'Admin',   to: '/admin',   prefix: '/admin', adminOnly: true },
]

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact) return pathname === item.prefix
  return pathname === item.prefix || pathname.startsWith(`${item.prefix}/`)
}

function namespaceFor(prefix: string): string {
  return prefix.replace(/^\//, '')
}

export function TopNav() {
  const location = useLocation()
  const { user } = useAuth()
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === 'admin')

  const onClick = (to: string, prefix: string) => () => {
    capture('nav_clicked', {
      namespace: namespaceFor(prefix),
      from_path: location.pathname,
      to_path: to,
    })
  }

  return (
    <header
      className="sticky top-0 z-40 hidden md:block bg-bg-surface/80 backdrop-blur-xl border-b border-contrast/[0.06]"
      data-testid="top-nav"
    >
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between gap-8">
        <Link
          to="/home"
          className="font-editorial text-[20px] tracking-[0.08em] text-text-primary"
          onClick={onClick('/home', '/home')}
        >
          SKILL<span className="text-accent-primary">FORGE</span>
        </Link>

        <div className="flex items-center gap-6">
          <nav className="flex items-center gap-6" role="navigation" aria-label="Main navigation">
            {items.map((item) => {
              const active = isActive(location.pathname, item)
              return (
                <Link
                  key={item.prefix}
                  to={item.to}
                  onClick={onClick(item.to, item.prefix)}
                  data-testid={`top-nav-${namespaceFor(item.prefix)}`}
                  data-active={active ? 'true' : 'false'}
                  className={clsx(
                    'text-[11px] tracking-[0.18em] uppercase font-medium transition-colors duration-200',
                    active ? 'text-accent-primary' : 'text-text-secondary hover:text-text-primary',
                  )}
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>
          <UserMenu />
        </div>
      </div>
    </header>
  )
}

export default TopNav
