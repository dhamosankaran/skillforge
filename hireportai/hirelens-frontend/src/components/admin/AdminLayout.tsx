import { NavLink, Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Layers, BookOpen, BarChart3 } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'

// Phase 6 slice 6.4a — multi-route admin shell. Wrapped externally by
// `<ProtectedRoute><AdminGate>` in App.tsx; this component renders the
// sidebar nav + `<Outlet />` for nested admin pages.
//
// `/admin/audit` is intentionally omitted per spec §12 D-14 — the FE
// consumer was never built (BE endpoint exists but un-consumed).

const NAV_LINKS = [
  { to: '/admin/cards', label: 'Cards', icon: FileText },
  { to: '/admin/decks', label: 'Decks', icon: Layers },
  { to: '/admin/lessons', label: 'Lessons', icon: BookOpen },
  { to: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
] as const

export default function AdminLayout() {
  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-7xl mx-auto px-4 py-10">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <h1 className="font-display text-3xl font-bold text-text-primary">
            Admin <span className="text-accent-primary">Console</span>
          </h1>
          <p className="text-text-secondary text-sm mt-1">
            Curriculum, content, and analytics surface.
          </p>
        </motion.div>

        <div className="flex flex-col md:flex-row gap-6">
          <nav
            aria-label="Admin sections"
            data-testid="admin-sidebar"
            className="md:w-56 shrink-0"
          >
            <ul className="flex flex-row md:flex-col gap-1 p-1 bg-bg-surface/60 border border-contrast/[0.06] rounded-xl overflow-x-auto md:overflow-visible">
              {NAV_LINKS.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    className={({ isActive }) =>
                      `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                        isActive
                          ? 'bg-accent-primary text-bg-base'
                          : 'text-text-secondary hover:text-text-primary hover:bg-contrast/[0.04]'
                      }`
                    }
                  >
                    <Icon size={14} />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <main className="flex-1 min-w-0">
            <Outlet />
          </main>
        </div>
      </div>
    </PageWrapper>
  )
}
