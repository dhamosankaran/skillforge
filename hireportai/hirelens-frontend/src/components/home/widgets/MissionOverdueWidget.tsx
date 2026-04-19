import { DashboardWidget } from '@/components/home/DashboardWidget'
import { capture } from '@/utils/posthog'
import type { Persona } from '@/context/AuthContext'
import type { HomeStateContext } from '@/types/homeState'

interface MissionOverdueWidgetProps {
  persona: Persona
  context: HomeStateContext
}

function _daysSince(targetDate: string | null): number | null {
  if (!targetDate) return null
  const target = new Date(targetDate + 'T00:00:00Z')
  const today = new Date()
  today.setUTCHours(0, 0, 0, 0)
  const ms = today.getTime() - target.getTime()
  return Math.max(0, Math.round(ms / 86_400_000))
}

export function MissionOverdueWidget({
  persona,
  context,
}: MissionOverdueWidgetProps) {
  const days = _daysSince(context.mission_target_date)

  return (
    <DashboardWidget
      title="Mission overdue"
      testid="mission-overdue"
      persona={persona}
      state="data"
      action={{
        label: 'Review mission',
        href: '/learn/mission',
        onClick: () =>
          capture('home_state_widget_clicked', {
            state: 'mission_overdue',
            cta: '/learn/mission',
          }),
      }}
    >
      <div className="flex flex-col gap-1">
        <div className="font-display text-base font-semibold text-text-primary">
          {days !== null && days > 0
            ? `Mission overdue by ${days} ${days === 1 ? 'day' : 'days'}.`
            : 'Mission target date has passed.'}
        </div>
        <div className="text-sm text-text-secondary">
          Wrap it up or end the mission to start fresh.
        </div>
      </div>
    </DashboardWidget>
  )
}
