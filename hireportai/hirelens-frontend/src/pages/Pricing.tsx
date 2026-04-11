import { useCallback, useEffect, useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import { Check, X, Sparkles, Zap, CheckCircle2 } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { useUsage } from '@/context/UsageContext'
import type { PlanType } from '@/context/UsageContext'
import { usePricing } from '@/hooks/usePricing'
import { capture } from '@/utils/posthog'

// ─── 3D Tilt Card ───
function TiltCard({ children, className = '', intensity = 6 }: { children: React.ReactNode; className?: string; intensity?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const rotateX = useMotionValue(0)
  const rotateY = useMotionValue(0)
  const springX = useSpring(rotateX, { stiffness: 200, damping: 20 })
  const springY = useSpring(rotateY, { stiffness: 200, damping: 20 })

  const handleMouse = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    rotateX.set(y * -intensity)
    rotateY.set(x * intensity)
  }, [rotateX, rotateY, intensity])

  const handleLeave = useCallback(() => {
    rotateX.set(0)
    rotateY.set(0)
  }, [rotateX, rotateY])

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouse}
      onMouseLeave={handleLeave}
      style={{ rotateX: springX, rotateY: springY, transformPerspective: 1000 }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

interface PlanFeature {
  text: string
  included: boolean
}

interface PlanConfig {
  name: string
  planKey: PlanType
  price: number
  period: string
  description: string
  icon: React.ElementType
  features: PlanFeature[]
  cta: string
  popular?: boolean
  accent: string
}

const plans: PlanConfig[] = [
  {
    name: 'Free',
    planKey: 'free',
    price: 0,
    period: '',
    description: 'Try SkillForge with 3 free resume analyses. No card required.',
    icon: Zap,
    accent: 'text-text-secondary',
    cta: 'Start Free',
    features: [
      { text: '3 resume analyses', included: true },
      { text: 'ATS match score', included: true },
      { text: 'Matched & missing keywords', included: true },
      { text: 'Basic dashboard results', included: true },
      { text: 'Unlimited scans', included: false },
      { text: 'Full skill gap analysis', included: false },
      { text: 'AI resume rewriting', included: false },
      { text: 'Cover letter generation', included: false },
      { text: 'Interview prep (Mission mode)', included: false },
      { text: 'Resume PDF export', included: false },
      { text: 'Application tracker', included: false },
    ],
  },
  {
    name: 'Pro',
    planKey: 'pro',
    price: 49,
    period: '/mo',
    description: 'Full platform access — scan, rewrite, prep, and track. Everything you need to land the role.',
    icon: Sparkles,
    accent: 'text-accent-primary',
    cta: 'Upgrade to Pro',
    popular: true,
    features: [
      { text: 'Unlimited ATS scans', included: true },
      { text: 'Full ATS compatibility score', included: true },
      { text: 'Keyword & skill gap analysis', included: true },
      { text: 'AI bullet point suggestions', included: true },
      { text: 'AI resume rewriting (all templates)', included: true },
      { text: 'Auto-tailored resume for each JD', included: true },
      { text: 'Resume PDF & DOCX export', included: true },
      { text: 'AI cover letter generation', included: true },
      { text: 'Interview prep — Mission mode', included: true },
      { text: 'Application tracker (Kanban)', included: true },
      { text: 'Priority processing', included: true },
    ],
  },
]

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
}

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] } },
}

export default function Pricing() {
  const { usage, upgradePlan } = useUsage()
  const { pricing } = usePricing()
  const [searchParams, setSearchParams] = useSearchParams()

  // Post-checkout return from Stripe. Backend webhook flips the
  // Subscription row asynchronously — we optimistically flip the local
  // plan and fire `payment_completed` so PostHog sees the conversion.
  // (Server-side webhook also fires the canonical event; the client
  // event is the user-attributed mirror.)
  useEffect(() => {
    const upgradeStatus = searchParams.get('upgrade')
    if (upgradeStatus !== 'success') return

    upgradePlan('pro')
    capture('payment_completed', {
      plan: 'pro',
      price: pricing.price,
      currency: pricing.currency,
      source: 'stripe_checkout_return',
    })
    toast.success('Welcome to Pro! Full library unlocked.', { duration: 5000 })

    // Strip the query params so a refresh doesn't refire the toast.
    const next = new URLSearchParams(searchParams)
    next.delete('upgrade')
    next.delete('session_id')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams, upgradePlan])

  const handleCta = (plan: PlanConfig) => {
    if (plan.planKey === 'free') return
    if (usage.plan === plan.planKey) return
    upgradePlan(plan.planKey)
  }

  return (
    <PageWrapper className="min-h-screen bg-bg-base relative overflow-hidden">
      {/* Aurora background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div
          className="aurora-blob w-[600px] h-[600px] top-[-15%] left-[10%] opacity-[0.08]"
          style={{ background: 'radial-gradient(circle, var(--accent-primary), transparent 65%)' }}
        />
        <div
          className="aurora-blob aurora-blob-2 w-[500px] h-[500px] bottom-[-10%] right-[-5%] opacity-[0.06]"
          style={{ background: 'radial-gradient(circle, var(--accent-secondary), transparent 65%)' }}
        />
        <div className="absolute inset-0 grid-pattern opacity-20" />
      </div>

      <div className="max-w-3xl mx-auto px-5 py-20 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-accent-primary/15 text-accent-primary text-xs font-medium mb-6 glow-hover"
            style={{ background: 'var(--accent-glow)' }}
          >
            <Sparkles size={11} />
            Simple, transparent pricing
          </motion.div>
          <h1 className="font-display text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            Choose your{' '}
            <span className="shimmer-text">plan</span>
          </h1>
          <p className="text-text-secondary text-base max-w-lg mx-auto leading-relaxed">
            Start free with 3 scans. Go Pro for unlimited access to every SkillForge tool.
          </p>
          {/* Current plan indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mt-5 inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-contrast/[0.08] text-text-muted text-xs"
            style={{ background: `rgb(var(--color-contrast) / 0.03)` }}
          >
            Current plan: <span className="font-semibold text-text-primary ml-1 capitalize">{usage.plan}</span>
          </motion.div>
        </motion.div>

        {/* Pricing cards */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 sm:grid-cols-2 gap-5 items-start"
        >
          {plans.map((basePlan) => {
            const plan = basePlan.planKey === 'pro'
              ? { ...basePlan, price: pricing.price, period: '/mo' }
              : basePlan
            const isCurrentPlan = usage.plan === plan.planKey
            const priceSymbol = plan.planKey === 'pro' && pricing.currency === 'inr' ? '\u20b9' : '$'
            return (
              <motion.div key={plan.name} variants={cardVariants}>
                <TiltCard className="h-full" intensity={plan.popular ? 4 : 6}>
                  <div
                    className={clsx(
                      'relative rounded-2xl border transition-all duration-300 h-full overflow-hidden',
                      plan.popular
                        ? 'border-accent-primary/25 sm:-mt-4'
                        : 'border-contrast/[0.06] hover:border-contrast/[0.12]',
                      isCurrentPlan && 'ring-2 ring-accent-primary/30'
                    )}
                    style={{
                      background: plan.popular
                        ? `linear-gradient(135deg, rgb(var(--color-bg-surface) / 0.95), rgb(var(--color-bg-elevated) / 0.9))`
                        : `linear-gradient(135deg, rgb(var(--color-bg-surface) / 0.8), rgb(var(--color-bg-base) / 0.9))`,
                    }}
                  >
                    {/* Gradient top border for popular */}
                    {plan.popular && (
                      <div className="absolute top-0 left-0 right-0 h-px animated-gradient-line" />
                    )}

                    {/* Ambient glow for popular */}
                    {plan.popular && (
                      <div className="absolute inset-0 pointer-events-none"
                        style={{ background: `radial-gradient(ellipse at 50% 0%, var(--accent-glow) 0%, transparent 60%)` }} />
                    )}

                    {/* Popular badge */}
                    {plan.popular && !isCurrentPlan && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                        <div
                          className="relative px-4 py-1 rounded-full text-white text-[11px] font-semibold tracking-wide uppercase overflow-hidden"
                          style={{
                            background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)',
                            boxShadow: '0 4px 16px var(--accent-glow)',
                          }}
                        >
                          <span className="relative z-10">Most Popular</span>
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-contrast/20 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
                        </div>
                      </div>
                    )}

                    {/* Current plan badge */}
                    {isCurrentPlan && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                        <div
                          className="flex items-center gap-1 px-4 py-1 rounded-full text-white text-[11px] font-semibold tracking-wide uppercase"
                          style={{
                            background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)',
                            boxShadow: '0 4px 16px var(--accent-glow)',
                          }}
                        >
                          <CheckCircle2 size={10} />
                          Current Plan
                        </div>
                      </div>
                    )}

                    <div className="p-7 relative">
                      {/* Plan header */}
                      <div className="flex items-center gap-2.5 mb-4">
                        <div className={clsx(
                          'w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-300',
                          plan.popular
                            ? 'bg-accent-primary/10 border border-accent-primary/20'
                            : 'bg-contrast/[0.04] border border-contrast/[0.08]'
                        )}>
                          <plan.icon size={16} className={plan.accent} strokeWidth={1.8} />
                        </div>
                        <span className="font-display font-semibold text-text-primary text-base">
                          {plan.name}
                        </span>
                      </div>

                      {/* Price */}
                      <div className="mb-5">
                        <div className="flex items-baseline gap-1">
                          <span
                            className="font-display text-5xl font-bold tracking-tight"
                            style={plan.popular ? {
                              background: 'linear-gradient(135deg, var(--text-primary) 0%, var(--accent-primary) 150%)',
                              WebkitBackgroundClip: 'text',
                              WebkitTextFillColor: 'transparent',
                            } : {
                              color: 'var(--bg-base)',
                            }}
                          >
                            {priceSymbol}{plan.price}
                          </span>
                          {plan.period && (
                            <span className="text-sm text-text-muted font-medium">{plan.period}</span>
                          )}
                        </div>
                        <p className="text-sm text-text-secondary mt-2 leading-relaxed">
                          {plan.description}
                        </p>
                      </div>

                      {/* CTA */}
                      {plan.planKey === 'free' ? (
                        <Link
                          to="/analyze"
                          className="block w-full text-center py-3 rounded-xl text-sm font-medium transition-all duration-300 bg-contrast/[0.04] border border-contrast/[0.08] text-text-secondary hover:bg-contrast/[0.06] hover:text-text-primary hover:border-contrast/[0.14] glow-hover"
                        >
                          {isCurrentPlan ? 'Currently Active' : plan.cta}
                        </Link>
                      ) : (
                        <button
                          onClick={() => handleCta(plan)}
                          disabled={isCurrentPlan}
                          className="relative block w-full text-center py-3 rounded-xl text-sm font-semibold transition-all duration-300 disabled:opacity-60 disabled:cursor-default overflow-hidden text-white"
                          style={{
                            background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)',
                            boxShadow: '0 4px 20px var(--accent-glow)',
                          }}
                        >
                          <span className="relative z-10">
                            {isCurrentPlan ? 'Currently Active' : plan.cta}
                          </span>
                          {!isCurrentPlan && (
                            <div className="absolute inset-0 -translate-x-full hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-contrast/20 to-transparent" />
                          )}
                        </button>
                      )}

                      {/* Divider */}
                      <div className="my-6">
                        {plan.popular ? (
                          <div className="animated-gradient-line opacity-60" />
                        ) : (
                          <div className="h-px bg-contrast/[0.06]" />
                        )}
                      </div>

                      {/* Features */}
                      <ul className="space-y-3">
                        {plan.features.map((feature, fi) => (
                          <motion.li
                            key={feature.text}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.4 + fi * 0.04, duration: 0.3 }}
                            className="flex items-start gap-2.5"
                          >
                            {feature.included ? (
                              <div className={clsx(
                                'mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center',
                                plan.popular ? 'bg-accent-primary/15' : 'bg-contrast/[0.06]'
                              )}>
                                <Check
                                  size={10}
                                  strokeWidth={3}
                                  className={plan.popular ? 'text-accent-primary' : 'text-text-muted'}
                                />
                              </div>
                            ) : (
                              <div className="mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center bg-contrast/[0.03]">
                                <X size={10} strokeWidth={2} className="text-text-muted/30" />
                              </div>
                            )}
                            <span
                              className={clsx(
                                'text-[13px] leading-snug',
                                feature.included ? 'text-text-secondary' : 'text-text-muted/40'
                              )}
                            >
                              {feature.text}
                            </span>
                          </motion.li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </TiltCard>
              </motion.div>
            )
          })}
        </motion.div>

        {/* Trust / FAQ */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="mt-16 text-center"
        >
          <div className="inline-flex items-center gap-6 flex-wrap justify-center">
            {['No credit card required', 'Cancel anytime', 'Privacy-first'].map((t) => (
              <span key={t} className="flex items-center gap-1.5 text-[12px] text-text-muted">
                <Check size={12} className="text-success/50" strokeWidth={2.5} />
                {t}
              </span>
            ))}
          </div>
          <p className="text-xs text-text-muted/40 mt-4">
            Demo mode — no real payments. Plan saved locally.
          </p>
        </motion.div>
      </div>
    </PageWrapper>
  )
}
