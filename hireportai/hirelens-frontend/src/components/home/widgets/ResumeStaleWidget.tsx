import { DashboardWidget } from '@/components/home/DashboardWidget'
import { capture } from '@/utils/posthog'
import type { Persona } from '@/context/AuthContext'
import type { HomeStateContext } from '@/types/homeState'

interface ResumeStaleWidgetProps {
  persona: Persona
  context: HomeStateContext
}

function _daysSinceISO(iso: string | null): number | null {
  if (!iso) return null
  const last = new Date(iso)
  const now = new Date()
  const ms = now.getTime() - last.getTime()
  return Math.max(0, Math.round(ms / 86_400_000))
}

export function ResumeStaleWidget({ persona, context }: ResumeStaleWidgetProps) {
  const days = _daysSinceISO(context.last_scan_date)

  return (
    <DashboardWidget
      title="Resume needs a refresh"
      testid="resume-stale"
      persona={persona}
      state="data"
      action={{
        label: 'Run a scan',
        href: '/prep/analyze',
        onClick: () =>
          capture('home_state_widget_clicked', {
            state: 'resume_stale',
            cta: '/prep/analyze',
          }),
      }}
    >
      <div className="flex flex-col gap-1">
        <div className="font-display text-base font-semibold text-text-primary">
          {days !== null
            ? `Last scan was ${days} ${days === 1 ? 'day' : 'days'} ago.`
            : 'Run a scan to track your progress.'}
        </div>
        <div className="text-sm text-text-secondary">
          Re-scan to track gap progress.
        </div>
      </div>
    </DashboardWidget>
  )
}
