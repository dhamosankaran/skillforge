import { DashboardWidget } from '@/components/home/DashboardWidget'
import type { Persona } from '@/context/AuthContext'

interface TeamComingSoonWidgetProps {
  persona: Persona
}

export function TeamComingSoonWidget({ persona }: TeamComingSoonWidgetProps) {
  return (
    <DashboardWidget
      title="Team Dashboards"
      testid="team-coming-soon"
      persona={persona}
      state="data"
    >
      <div className="text-sm text-text-secondary">
        Team dashboards are coming in a future release. For now, here's your
        personal learning progress.
      </div>
    </DashboardWidget>
  )
}
