import { useEffect } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GoogleLogin } from '@react-oauth/google'
import { ArrowLeft, Sparkles } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

/**
 * Dedicated sign-in page.
 *
 * Entry point for guests arriving from the landing page CTAs (see
 * LandingPage.tsx — the "/login" links). Reuses the Google OAuth flow
 * from AuthContext, so sign-in here is identical to the Navbar button.
 *
 * After a successful sign-in, the user is redirected to /analyze.
 * If an already-authenticated user somehow lands here (manual URL,
 * stale tab), they're bounced to /analyze immediately.
 */
export default function LoginPage() {
  const { user, isLoading, signIn } = useAuth()
  const navigate = useNavigate()

  // After the AuthContext finishes its sign-in round-trip (updating the
  // `user` value), push the user into the app.
  useEffect(() => {
    if (user) navigate('/analyze', { replace: true })
  }, [user, navigate])

  // Still hydrating auth state — avoid flashing the sign-in UI.
  if (isLoading) return null

  // Already signed in — send them through immediately.
  if (user) return <Navigate to="/analyze" replace />

  return (
    <div className="min-h-screen bg-bg-base text-text-primary flex items-center justify-center px-5 py-12 relative overflow-hidden">
      {/* Ambient glow to match the rest of the dark theme */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 60% 50% at 50% 35%, rgba(0,255,200,0.06) 0%, transparent 70%)',
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="relative w-full max-w-sm"
      >
        {/* Back to home */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-[11px] tracking-wide uppercase text-text-muted hover:text-text-secondary transition-colors mb-8"
        >
          <ArrowLeft size={12} />
          Back to home
        </Link>

        {/* Card */}
        <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/70 backdrop-blur-xl shadow-[0_20px_60px_rgba(0,0,0,0.5)] p-8">
          {/* Brand */}
          <div className="flex flex-col items-center text-center mb-7">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-[10px] tracking-[0.18em] uppercase font-mono text-accent-primary mb-5">
              <Sparkles size={10} />
              SKILLFORGE
            </div>
            <h1 className="font-display text-2xl font-bold tracking-tight mb-2">
              Sign in to <span className="text-accent-primary">SkillForge</span>
            </h1>
            <p className="text-sm text-text-secondary leading-relaxed max-w-[280px]">
              Scan your resume, find your gaps, and start studying the right
              cards in under a minute.
            </p>
          </div>

          {/* Google sign-in */}
          <div className="flex justify-center mb-5">
            <GoogleLogin
              onSuccess={(cred) => {
                if (cred.credential) {
                  signIn(cred.credential).catch(() => {
                    // Errors are surfaced by the axios interceptor's toast.
                  })
                }
              }}
              onError={() => {
                // No client ID configured → the button renders a disabled
                // state; silence the console noise.
              }}
              theme="filled_black"
              size="large"
              shape="pill"
              text="signin_with"
              logo_alignment="left"
              width="280"
            />
          </div>

          {/* Legal line */}
          <p className="text-[10px] text-text-muted text-center leading-relaxed">
            By continuing, you agree to the Terms of Service and Privacy Policy.
            We never store your resume — scans are processed in memory.
          </p>
        </div>

        {/* Sub-card helper */}
        <p className="text-[11px] text-text-muted text-center mt-5">
          New here? Signing in with Google creates your account automatically.
        </p>
      </motion.div>
    </div>
  )
}
