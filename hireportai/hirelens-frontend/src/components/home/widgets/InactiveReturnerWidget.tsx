import { DashboardWidget } from '@/components/home/DashboardWidget'
import { capture } from '@/utils/posthog'
import type { Persona } from '@/context/AuthContext'
import type { HomeStateContext } from '@/types/homeState'

interface InactiveReturnerWidgetProps {
  persona: Persona
  context: HomeStateContext
}

export function InactiveReturnerWidget({
  persona,
  context: _context,
}: InactiveReturnerWidgetProps) {
  return (
    <DashboardWidget
      title="Welcome back"
      testid="inactive-returner"
      persona={persona}
      state="data"
      action={{
        label: 'Pick up where you left off',
        href: '/learn/daily',
        onClick: () =>
          capture('home_state_widget_clicked', {
            state: 'inactive_returner',
            cta: '/learn/daily',
          }),
      }}
    >
      <div className="flex flex-col gap-1">
        <div className="font-display text-base font-semibold text-text-primary">
          Welcome back — your next card is ready.
        </div>
        <div className="text-sm text-text-secondary">
          One review is enough to start a new streak.
        </div>
      </div>
    </DashboardWidget>
  )
}
