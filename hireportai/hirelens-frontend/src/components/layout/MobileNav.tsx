import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import {
  Home as HomeOutline,
  BookOpen as BookOpenOutline,
  Briefcase as BriefcaseOutline,
  User as UserOutline,
  Shield as ShieldOutline,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { capture } from '@/utils/posthog'

interface NavItem {
  label: string
  to: string
  prefix: string
  icon: LucideIcon
  exact?: boolean
  adminOnly?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Home',    to: '/home',    prefix: '/home',    icon: HomeOutline,      exact: true },
  { label: 'Learn',   to: '/learn',   prefix: '/learn',   icon: BookOpenOutline },
  { label: 'Prep',    to: '/prep',    prefix: '/prep',    icon: BriefcaseOutline },
  { label: 'Profile', to: '/profile', prefix: '/profile', icon: UserOutline },
  { label: 'Admin',   to: '/admin',   prefix: '/admin',   icon: ShieldOutline, adminOnly: true },
]

const HIDDEN_PATHS = new Set(['/', '/login', '/pricing'])

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact) return pathname === item.prefix
  return pathname === item.prefix || pathname.startsWith(`${item.prefix}/`)
}

function namespaceFor(prefix: string): string {
  return prefix.replace(/^\//, '')
}

export function MobileNav() {
  const location = useLocation()
  const { user } = useAuth()

  if (HIDDEN_PATHS.has(location.pathname)) return null

  const items = NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === 'admin')

  const onClick = (to: string, prefix: string) => () => {
    capture('nav_clicked', {
      namespace: namespaceFor(prefix),
      from_path: location.pathname,
      to_path: to,
    })
  }

  return (
    <nav
      role="navigation"
      aria-label="Main navigation"
      data-testid="mobile-nav"
      className="fixed bottom-0 left-0 right-0 z-40 md:hidden bg-bg-surface/95 backdrop-blur-xl border-t border-contrast/[0.06] pb-[env(safe-area-inset-bottom)] h-16"
    >
      <ul className="flex items-stretch justify-around h-full">
        {items.map((item) => {
          const active = isActive(location.pathname, item)
          const Icon = item.icon
          return (
            <li key={item.prefix} className="flex-1">
              <Link
                to={item.to}
                onClick={onClick(item.to, item.prefix)}
                data-testid={`mobile-nav-${namespaceFor(item.prefix)}`}
                data-active={active ? 'true' : 'false'}
                className={clsx(
                  'flex flex-col items-center justify-center h-full gap-1 text-[10px] tracking-[0.1em] uppercase font-medium transition-colors',
                  active ? 'text-accent-primary' : 'text-text-secondary',
                )}
              >
                <Icon
                  size={20}
                  strokeWidth={active ? 2.4 : 1.8}
                  fill={active ? 'currentColor' : 'none'}
                />
                <span>{item.label}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export default MobileNav
