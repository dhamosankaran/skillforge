import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Link, useLocation } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { Sparkles, Crown, ChevronDown, CreditCard } from 'lucide-react'
import clsx from 'clsx'
import { useUsage } from '@/context/UsageContext'
import { useAuth } from '@/context/AuthContext'

const navLinks = [
  { href: '/analyze', label: 'Analyze' },
  { href: '/results', label: 'Results' },
  { href: '/rewrite', label: 'Rewrite' },
  { href: '/interview', label: 'Interview' },
  { href: '/tracker', label: 'Tracker' },
  { href: '/pricing', label: 'Pricing' },
]

const PLAN_CONFIG = {
  free: { label: 'Free', color: 'text-text-muted', border: 'border-white/[0.08]', icon: null },
  pro: {
    label: 'Pro',
    color: 'text-accent-primary',
    border: 'border-accent-primary/30',
    icon: Sparkles,
  },
  premium: {
    label: 'Premium',
    color: 'text-accent-primary',
    border: 'border-accent-primary/40',
    icon: Crown,
  },
}

export function Navbar() {
  const location = useLocation()
  const { usage } = useUsage()
  const { user, signIn, signOut } = useAuth()
  const [showUserMenu, setShowUserMenu] = useState(false)

  const plan = PLAN_CONFIG[usage.plan]
  const PlanIcon = plan.icon

  return (
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
        <Link
          to="/"
          className="flex-shrink-0 group"
        >
          <span className="font-editorial text-[20px] tracking-[0.08em] text-text-primary group-hover:text-text-primary transition-colors">
            HIREPORT<span className="text-accent-primary">AI</span>
          </span>
        </Link>

        {/* ── Nav Links ── */}
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
                    style={{ background: 'linear-gradient(90deg, transparent, #DC2626, transparent)' }}
                    transition={{ type: 'spring', bounce: 0.15, duration: 0.45 }}
                  />
                )}
              </Link>
            )
          })}
        </nav>

        {/* ── Right: plan + auth ── */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Plan badge */}
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

          {/* Auth */}
          {user ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu((v) => !v)}
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/[0.03] transition-all"
              >
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.name}
                    className="w-6 h-6 rounded-full border border-white/10 ring-2 ring-accent-primary/20"
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
                      className="absolute right-0 top-full mt-2 w-52 rounded-xl border border-white/[0.08] bg-bg-surface/95 backdrop-blur-xl shadow-modal z-50 overflow-hidden"
                    >
                      <div className="px-4 py-3 border-b border-white/[0.06]">
                        <p className="text-[12px] font-medium text-text-primary truncate">{user.name}</p>
                        <p className="text-[10px] text-text-muted truncate mt-0.5">{user.email}</p>
                      </div>
                      <div className="p-1.5">
                        <Link
                          to="/pricing"
                          onClick={() => setShowUserMenu(false)}
                          className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-[11px] tracking-wide uppercase text-text-muted hover:bg-white/[0.03] hover:text-text-secondary transition-all"
                        >
                          <CreditCard size={12} />
                          Manage Plan
                        </Link>
                        <button
                          onClick={() => { signOut(); setShowUserMenu(false) }}
                          className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-[11px] tracking-wide uppercase text-text-muted hover:bg-white/[0.03] hover:text-text-secondary transition-all"
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
        </div>
      </div>
    </motion.header>
  )
}
