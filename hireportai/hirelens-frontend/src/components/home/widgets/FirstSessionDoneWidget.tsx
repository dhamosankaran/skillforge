import { DashboardWidget } from '@/components/home/DashboardWidget'
import { capture } from '@/utils/posthog'
import type { Persona } from '@/context/AuthContext'
import type { HomeStateContext } from '@/types/homeState'

interface FirstSessionDoneWidgetProps {
  persona: Persona
  context: HomeStateContext
}

export function FirstSessionDoneWidget({
  persona,
  context: _context,
}: FirstSessionDoneWidgetProps) {
  return (
    <DashboardWidget
      title="Nice start"
      testid="first-session-done"
      persona={persona}
      state="data"
      action={{
        label: 'Keep going',
        href: '/learn/daily',
        onClick: () =>
          capture('home_state_widget_clicked', {
            state: 'first_session_done',
            cta: '/learn/daily',
          }),
      }}
    >
      <div className="flex flex-col gap-1">
        <div className="font-display text-base font-semibold text-text-primary">
          Great first session — keep the momentum.
        </div>
        <div className="text-sm text-text-secondary">
          A few more reviews lock the habit in.
        </div>
      </div>
    </DashboardWidget>
  )
}
