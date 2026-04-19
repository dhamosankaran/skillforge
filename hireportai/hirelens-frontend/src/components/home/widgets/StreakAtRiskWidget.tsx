import { DashboardWidget } from '@/components/home/DashboardWidget'
import { capture } from '@/utils/posthog'
import type { Persona } from '@/context/AuthContext'
import type { HomeStateContext } from '@/types/homeState'

interface StreakAtRiskWidgetProps {
  persona: Persona
  context: HomeStateContext
}

export function StreakAtRiskWidget({
  persona,
  context,
}: StreakAtRiskWidgetProps) {
  const streak = context.current_streak

  return (
    <DashboardWidget
      title="Streak at risk"
      testid="streak-at-risk"
      persona={persona}
      state="data"
      action={{
        label: 'Review now',
        href: '/learn/daily',
        onClick: () =>
          capture('home_state_widget_clicked', {
            state: 'streak_at_risk',
            cta: '/learn/daily',
          }),
      }}
    >
      <div className="flex flex-col gap-1">
        <div className="font-display text-base font-semibold text-text-primary">
          Your {streak}-day streak is at risk.
        </div>
        <div className="text-sm text-text-secondary">
          Review 1 card today to keep it alive.
        </div>
      </div>
    </DashboardWidget>
  )
}
