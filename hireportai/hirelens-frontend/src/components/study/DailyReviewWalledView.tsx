/**
 * Pre-flight upsell rendered in place of the daily-review queue when a
 * free user has consumed today's daily-card budget. Spec #63 / B-059.
 *
 * Mirrors the spec #60 / B-045 (`Analyze.tsx`) gate-card pattern. Copy is
 * locked by spec; styling consumes design tokens only (Rule 12).
 *
 * The page-load `daily_card_wall_hit` analytics fire is owned by the
 * caller (`DailyReview.tsx`) via a `useRef` idempotency guard — keeping
 * the analytics fire in the parent makes the component a pure renderer
 * and easier to test in isolation (props-only, no `useEffect` side
 * effects, no context dependencies).
 */
import { motion } from 'framer-motion'
import { ChevronRight, Lock } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { GlowButton } from '@/components/ui/GlowButton'
import { formatResetsAt } from '@/utils/wallCountdown'

interface DailyReviewWalledViewProps {
  resetsAt: string  // ISO8601 — daily_status.resets_at from GET /api/v1/study/daily
}

export function DailyReviewWalledView({ resetsAt }: DailyReviewWalledViewProps) {
  const navigate = useNavigate()

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        data-testid="daily-review-walled-view"
        className="max-w-md w-full bg-bg-surface/50 border border-contrast/[0.06] rounded-2xl p-8 text-center"
      >
        <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center mx-auto mb-5">
          <Lock size={24} className="text-accent-primary" />
        </div>
        <h2 className="font-display text-xl font-bold text-text-primary mb-2">
          You&apos;ve used today&apos;s free reviews
        </h2>
        <p
          className="text-sm text-text-secondary leading-relaxed mb-6"
          data-testid="daily-review-walled-view-resets-at"
        >
          {formatResetsAt(resetsAt)}
        </p>
        <GlowButton
          size="lg"
          className="w-full mb-3"
          data-testid="daily-review-walled-view-upgrade-cta"
          onClick={() => navigate('/pricing')}
        >
          Upgrade to Pro
          <ChevronRight size={14} />
        </GlowButton>
        <Link
          to="/home"
          data-testid="daily-review-walled-view-home-cta"
          className="block text-sm text-text-muted hover:text-text-secondary transition-colors"
        >
          Back to home
        </Link>
      </motion.div>
    </div>
  )
}
