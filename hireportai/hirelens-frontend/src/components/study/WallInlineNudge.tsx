/**
 * WallInlineNudge — silent in-flow Pro nudge shown after a paywall dismissal
 * while the LD-3 3-attempt grace window is still active.
 *
 * Spec #42 §5.4 / LD-6. Renders above the rating-button grid in
 * `QuizPanel` when `GET /payments/should-show-paywall` returned
 * `{show: false}`. Does NOT fire `paywall_hit` — counting silent nudges
 * would inflate the paywall-shown denominator and break the conversion-
 * rate funnel. Fires `inline_nudge_shown` once on mount (spec §6 — listed
 * as "optional, impl-slice call"; this slice opts in for grace-period
 * engagement telemetry, which feeds the LD-3 threshold retune plan in
 * §11).
 */
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

import type { PaywallTrigger } from '@/components/PaywallModal'
import { capture } from '@/utils/posthog'

interface WallInlineNudgeProps {
  trigger: PaywallTrigger
}

export function WallInlineNudge({ trigger }: WallInlineNudgeProps) {
  useEffect(() => {
    capture('inline_nudge_shown', { trigger })
  }, [trigger])

  return (
    <div
      role="status"
      data-testid="wall-inline-nudge"
      className="flex items-center gap-2 rounded-xl border border-border-accent/30 bg-contrast/[0.03] px-3 py-2 text-xs text-text-muted"
    >
      <Sparkles size={14} className="shrink-0 text-accent-primary" />
      <span>
        This is a Pro feature —{' '}
        <Link
          to="/pricing"
          className="font-medium text-accent-primary underline-offset-2 hover:underline"
        >
          upgrade
        </Link>{' '}
        anytime from Profile
      </span>
    </div>
  )
}
