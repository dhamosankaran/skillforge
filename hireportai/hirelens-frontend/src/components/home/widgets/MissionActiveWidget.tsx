import { DashboardWidget } from '@/components/home/DashboardWidget'
import { capture } from '@/utils/posthog'
import type { Persona } from '@/context/AuthContext'
import type { HomeStateContext } from '@/types/homeState'

interface MissionActiveWidgetProps {
  persona: Persona
  context: HomeStateContext
}

function _daysUntil(targetDate: string | null): number | null {
  if (!targetDate) return null
  const target = new Date(targetDate + 'T00:00:00Z')
  const today = new Date()
  today.setUTCHours(0, 0, 0, 0)
  const ms = target.getTime() - today.getTime()
  return Math.max(0, Math.round(ms / 86_400_000))
}

export function MissionActiveWidget({
  persona,
  context,
}: MissionActiveWidgetProps) {
  const days = _daysUntil(context.mission_target_date)

  return (
    <DashboardWidget
      title="Mission in flight"
      testid="mission-active"
      persona={persona}
      state="data"
      action={{
        label: 'Open mission',
        href: '/learn/mission',
        onClick: () =>
          capture('home_state_widget_clicked', {
            state: 'mission_active',
            cta: '/learn/mission',
          }),
      }}
    >
      <div className="flex flex-col gap-1">
        <div className="font-display text-base font-semibold text-text-primary">
          {days !== null
            ? `${days} ${days === 1 ? 'day' : 'days'} left in your mission`
            : 'Mission in flight'}
        </div>
        <div className="text-sm text-text-secondary">
          Today's cards are queued up.
        </div>
      </div>
    </DashboardWidget>
  )
}
