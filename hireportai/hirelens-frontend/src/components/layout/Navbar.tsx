import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Link, useLocation } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { Sparkles, ChevronDown, CreditCard, Menu, X, User } from 'lucide-react'
import clsx from 'clsx'
import { useUsage } from '@/context/UsageContext'
import { useAuth } from '@/context/AuthContext'
import { StreakBadge } from '@/components/profile/StreakBadge'

const navLinks = [
  { href: '/analyze', label: 'Analyze' },
  { href: '/results', label: 'Results' },
  { href: '/rewrite', label: 'Rewrite' },
  { href: '/interview', label: 'Interview' },
  { href: '/tracker', label: 'Tracker' },
  { href: '/pricing', label: 'Pricing' },
]

const PLAN_CONFIG = {
  free: { label: 'Free', color: 'text-text-muted', border: 'border-contrast/[0.08]', icon: null },
  pro: {
    label: 'Pro',
    color: 'text-accent-primary',
    border: 'border-accent-primary/30',
    icon: Sparkles,
  },
}

export function Navbar() {
  const location = useLocation()
  const { usage } = useUsage()
  const { user, signIn, signOut } = useAuth()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)

  const planKey = usage.plan === 'pro' ? 'pro' : 'free'
  const plan = PLAN_CONFIG[planKey]
  const PlanIcon = plan.icon

  return (
    <>
      <motion.header
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="sticky top-0 z-50 bg-bg-base/70 backdrop-blur-2xl backdrop-saturate-150"
      >
        {/* Animated gradient bottom border */}
        <div className="absolute bottom-0 left-0 right-0 h-px animated-gradient-line opacity-60" />

        <div className="max-w-7xl mx-auto px-6 sm:px-8 h-14 flex items-center justify-between gap-6">
          {/* ── Logo ── */}
          <Link to="/" className="flex-shrink-0 group">
            <span className="font-editorial text-[20px] tracking-[0.08em] text-text-primary group-hover:text-text-primary transition-colors">
              SKILL<span className="text-accent-primary">FORGE</span>
            </span>
          </Link>

          {/* ── Nav Links (desktop) ── */}
          <nav
            className="hidden lg:flex items-center gap-6 flex-1 justify-center"
            role="navigation"
            aria-label="Main navigation"
          >
            {navLinks.map(({ href, label }) => {
              const active = location.pathname === href
              return (
                <Link
                  key={href}
                  to={href}
                  className={clsx(
                    'relative py-1 text-[10px] tracking-[0.18em] uppercase font-medium transition-all duration-200',
                    active ? 'text-text-primary' : 'text-text-muted hover:text-text-secondary'
                  )}
                >
                  {label}
                  {active && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute -bottom-0.5 left-0 right-0 h-px"
                      style={{ background: `linear-gradient(90deg, transparent, var(--accent-primary), transparent)` }}
                      transition={{ type: 'spring', bounce: 0.15, duration: 0.45 }}
                    />
                  )}
                </Link>
              )
            })}
          </nav>

          {/* ── Right: streak + plan + auth + hamburger ── */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Streak badge (signed-in users only; component renders null otherwise) */}
            {user && <span data-tour="streak-badge"><StreakBadge /></span>}

            {/* Plan badge (hidden on mobile) */}
            <Link
              to="/pricing"
              className={clsx(
                'hidden sm:flex items-center gap-1.5 px-2.5 py-1 border rounded-lg text-[10px] tracking-[0.15em] uppercase font-semibold transition-all duration-200 glow-hover',
                plan.border,
                plan.color
              )}
            >
              {PlanIcon && <PlanIcon size={10} strokeWidth={2.2} />}
              {plan.label}
            </Link>

            {/* Auth (desktop) */}
            {user ? (
              <div className="relative hidden sm:block">
                <button
                  onClick={() => setShowUserMenu((v) => !v)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-contrast/[0.03] transition-all"
                >
                  {user.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user.name}
                      className="w-6 h-6 rounded-full border border-contrast/10 ring-2 ring-accent-primary/20"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-accent-primary/20 border border-accent-primary/30 flex items-center justify-center text-accent-primary text-[10px] font-bold">
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <span className="hidden sm:block text-[11px] text-text-secondary font-medium max-w-[90px] truncate tracking-wide">
                    {user.name.split(' ')[0]}
                  </span>
                  <ChevronDown size={11} className="text-text-muted" />
                </button>

                <AnimatePresence>
                  {showUserMenu && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
                      <motion.div
                        initial={{ opacity: 0, y: 6, scale: 0.97 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 4, scale: 0.97 }}
                        transition={{ duration: 0.15 }}
                        className="absolute right-0 top-full mt-2 w-52 rounded-xl border border-contrast/[0.08] bg-bg-surface/95 backdrop-blur-xl shadow-modal z-50 overflow-hidden"
                      >
                        <div className="px-4 py-3 border-b border-contrast/[0.06]">
                          <p className="text-[12px] font-medium text-text-primary truncate">{user.name}</p>
                          <p className="text-[10px] text-text-muted truncate mt-0.5">{user.email}</p>
                        </div>
                        <div className="p-1.5">
                          <Link
                            to="/profile"
                            onClick={() => setShowUserMenu(false)}
                            className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-[11px] tracking-wide uppercase text-text-muted hover:bg-contrast/[0.03] hover:text-text-secondary transition-all"
                          >
                            <User size={12} />
                            Profile
                          </Link>
                          <Link
                            to="/pricing"
                            onClick={() => setShowUserMenu(false)}
                            className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-[11px] tracking-wide uppercase text-text-muted hover:bg-contrast/[0.03] hover:text-text-secondary transition-all"
                          >
                            <CreditCard size={12} />
                            Manage Plan
                          </Link>
                          <button
                            onClick={() => { signOut(); setShowUserMenu(false) }}
                            className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-[11px] tracking-wide uppercase text-text-muted hover:bg-contrast/[0.03] hover:text-text-secondary transition-all"
                          >
                            Sign Out
                          </button>
                        </div>
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <div className="hidden sm:block">
                <GoogleLogin
                  onSuccess={(cred) => {
                    if (cred.credential) signIn(cred.credential).catch(() => {})
                  }}
                  onError={() => {/* silent – no client ID configured */}}
                  theme="filled_black"
                  size="medium"
                  shape="pill"
                  text="signin_with"
                  logo_alignment="left"
                />
              </div>
            )}

            {/* Hamburger (mobile/tablet) */}
            <button
              onClick={() => setShowMobileMenu((v) => !v)}
              className="lg:hidden flex items-center justify-center w-8 h-8 rounded-lg hover:bg-contrast/[0.04] transition-all text-text-muted hover:text-text-primary"
              aria-label="Toggle menu"
            >
              {showMobileMenu ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </motion.header>

      {/* ── Mobile drawer ── */}
      <AnimatePresence>
        {showMobileMenu && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
              onClick={() => setShowMobileMenu(false)}
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 260 }}
              className="fixed top-0 right-0 bottom-0 z-50 w-72 bg-bg-surface/95 backdrop-blur-2xl border-l border-contrast/[0.07] lg:hidden flex flex-col"
            >
              {/* Drawer header */}
              <div className="flex items-center justify-between px-5 h-14 border-b border-contrast/[0.06]">
                <span className="font-editorial text-[18px] tracking-[0.08em] text-text-primary">
                  SKILL<span className="text-accent-primary">FORGE</span>
                </span>
                <button
                  onClick={() => setShowMobileMenu(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-contrast/[0.04] text-text-muted"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Nav links */}
              <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
                {navLinks.map(({ href, label }) => {
                  const active = location.pathname === href
                  return (
                    <Link
                      key={href}
                      to={href}
                      onClick={() => setShowMobileMenu(false)}
                      className={clsx(
                        'flex items-center px-4 py-3 rounded-xl text-[11px] tracking-[0.15em] uppercase font-medium transition-all duration-200',
                        active
                          ? 'bg-accent-primary/10 text-accent-primary border border-accent-primary/20'
                          : 'text-text-muted hover:text-text-secondary hover:bg-contrast/[0.03]'
                      )}
                    >
                      {label}
                    </Link>
                  )
                })}
              </nav>

              {/* Drawer footer: plan + auth */}
              <div className="px-4 py-4 border-t border-contrast/[0.06] space-y-3">
                {/* Plan badge */}
                <Link
                  to="/pricing"
                  onClick={() => setShowMobileMenu(false)}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-2 border rounded-lg text-[10px] tracking-[0.15em] uppercase font-semibold w-full',
                    plan.border,
                    plan.color
                  )}
                >
                  {PlanIcon && <PlanIcon size={10} strokeWidth={2.2} />}
                  {plan.label} Plan
                </Link>

                {/* Auth */}
                {user ? (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5 px-3 py-2">
                      {user.avatar_url ? (
                        <img
                          src={user.avatar_url}
                          alt={user.name}
                          className="w-7 h-7 rounded-full border border-contrast/10"
                          referrerPolicy="no-referrer"
                        />
                      ) : (
                        <div className="w-7 h-7 rounded-full bg-accent-primary/20 border border-accent-primary/30 flex items-center justify-center text-accent-primary text-[11px] font-bold">
                          {user.name.charAt(0).toUpperCase()}
                        </div>
                      )}
                      <div className="min-w-0">
                        <p className="text-[12px] font-medium text-text-primary truncate">{user.name}</p>
                        <p className="text-[10px] text-text-muted truncate">{user.email}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => { signOut(); setShowMobileMenu(false) }}
                      className="w-full text-left px-3 py-2 rounded-lg text-[11px] tracking-wide uppercase text-text-muted hover:bg-contrast/[0.03] hover:text-text-secondary transition-all"
                    >
                      Sign Out
                    </button>
                  </div>
                ) : (
                  <div className="px-1">
                    <GoogleLogin
                      onSuccess={(cred) => {
                        if (cred.credential) signIn(cred.credential).catch(() => {})
                        setShowMobileMenu(false)
                      }}
                      onError={() => {}}
                      theme="filled_black"
                      size="large"
                      shape="pill"
                      text="signin_with"
                      logo_alignment="left"
                      width="240"
                    />
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
