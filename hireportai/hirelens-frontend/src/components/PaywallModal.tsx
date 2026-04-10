/**
 * PaywallModal — shown when a free user hits Pro-gated content.
 *
 * Spec #11. Replaces the ad-hoc upgrade modals that lived inline in
 * StudyDashboard and CardViewer. Fires `paywall_hit` on open and
 * `checkout_started` on CTA click; `payment_completed` fires on the
 * Pricing page when the user returns from Stripe.
 *
 * The CTA calls POST /api/v1/payments/checkout and redirects the
 * browser to the Stripe-hosted Checkout URL. Errors are surfaced via
 * toast — we never leave the user stranded with a dead button.
 */
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Sparkles, ArrowRight, Check, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { createCheckoutSession } from '@/services/api'
import { capture } from '@/utils/posthog'

export type PaywallTrigger =
  | 'scan_limit'
  | 'card_limit'
  | 'locked_category'
  | 'daily_review'

interface PaywallModalProps {
  open: boolean
  onClose: () => void
  trigger: PaywallTrigger
  context?: { categoryName?: string; cardsViewed?: number }
}

const HEADLINES: Record<PaywallTrigger, string> = {
  scan_limit: "You've hit your free scan limit",
  card_limit: 'Unlock the full card library',
  locked_category: 'This category is Pro-only',
  daily_review: 'Daily Review is a Pro feature',
}

const SUBLINES: Record<PaywallTrigger, string> = {
  scan_limit:
    "You've used all your free ATS scans. Upgrade to Pro for unlimited scans and the full study library.",
  card_limit:
    "You've reached the end of the free tier. Pro unlocks every card, every category, and daily spaced-repetition review.",
  locked_category:
    'Pro unlocks every category in the study library — foundation, advanced, and role-specific decks.',
  daily_review:
    'Daily Review uses FSRS to schedule the exact cards you need to revisit. Pro unlocks the full queue.',
}

const VALUE_PROPS = [
  'Unlimited ATS scans + rewrites',
  'Full card library (all categories)',
  'Daily FSRS spaced-repetition review',
]

export function PaywallModal({
  open,
  onClose,
  trigger,
  context,
}: PaywallModalProps) {
  const [isLoading, setIsLoading] = useState(false)

  // Fire paywall_hit once whenever the modal opens. Re-fires if the same
  // modal instance is re-opened, which is the right semantic — each open
  // is a distinct conversion opportunity.
  useEffect(() => {
    if (!open) return
    capture('paywall_hit', {
      trigger,
      category_name: context?.categoryName,
      cards_viewed: context?.cardsViewed,
    })
  }, [open, trigger, context?.categoryName, context?.cardsViewed])

  async function handleUpgrade() {
    if (isLoading) return
    setIsLoading(true)
    capture('checkout_started', {
      trigger,
      plan: 'pro',
      price_usd: 49,
    })
    try {
      const { url } = await createCheckoutSession()
      window.location.href = url
    } catch (err) {
      setIsLoading(false)
      toast.error('Could not start checkout. Please try again.')
      // Swallow — toast is the user-facing signal; details in devtools.
      console.error('createCheckoutSession failed', err)
    }
  }

  const headline =
    trigger === 'locked_category' && context?.categoryName
      ? `Unlock ${context.categoryName}`
      : HEADLINES[trigger]

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={isLoading ? undefined : onClose}
            className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
            className="fixed inset-0 z-[101] flex items-center justify-center p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="paywall-title"
          >
            <div className="relative w-full max-w-md bg-bg-surface border border-white/[0.08] rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.5)] overflow-hidden">
              {/* Top glow accent */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-px bg-gradient-to-r from-transparent via-accent-primary/50 to-transparent" />

              {/* Close */}
              <button
                onClick={onClose}
                disabled={isLoading}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-text-muted hover:text-text-secondary hover:bg-white/[0.04] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="Close paywall"
              >
                <X size={16} />
              </button>

              <div className="p-8 text-center">
                {/* Icon */}
                <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center mx-auto mb-5">
                  <Sparkles size={24} className="text-accent-primary" />
                </div>

                {/* Title */}
                <h2
                  id="paywall-title"
                  className="font-display text-xl font-bold text-text-primary mb-2"
                >
                  {headline}
                </h2>
                <p className="text-sm text-text-secondary leading-relaxed mb-6 max-w-sm mx-auto">
                  {SUBLINES[trigger]}
                </p>

                {/* Value props */}
                <ul className="text-left space-y-2.5 mb-6 max-w-xs mx-auto">
                  {VALUE_PROPS.map((prop) => (
                    <li
                      key={prop}
                      className="flex items-start gap-2.5 text-sm text-text-secondary"
                    >
                      <Check
                        size={16}
                        className="shrink-0 mt-0.5 text-accent-primary"
                      />
                      <span>{prop}</span>
                    </li>
                  ))}
                </ul>

                {/* Price */}
                <div className="mb-5">
                  <span className="font-display text-3xl font-bold text-text-primary">
                    $49
                  </span>
                  <span className="text-sm text-text-muted">/month</span>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-3">
                  <button
                    onClick={handleUpgrade}
                    disabled={isLoading}
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-accent-primary text-bg-base text-sm font-semibold hover:bg-accent-primary/90 transition-colors shadow-[0_0_20px_rgba(0,255,200,0.15)] disabled:opacity-70 disabled:cursor-wait"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Starting checkout…
                      </>
                    ) : (
                      <>
                        Upgrade to Pro — $49/mo
                        <ArrowRight size={14} />
                      </>
                    )}
                  </button>
                  <button
                    onClick={onClose}
                    disabled={isLoading}
                    className="w-full py-2 text-sm text-text-muted hover:text-text-secondary transition-colors disabled:opacity-40"
                  >
                    Not now
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
