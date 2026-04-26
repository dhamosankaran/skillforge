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

function _daysSinceISO(iso: string | null): number | null {
  if (!iso) return null
  const last = new Date(iso)
  const now = new Date()
  const ms = now.getTime() - last.getTime()
  return Math.max(0, Math.round(ms / 86_400_000))
}

const RESUME_STALE_DAYS = 21

export function MissionActiveWidget({
  persona,
  context,
}: MissionActiveWidgetProps) {
  const days = _daysUntil(context.mission_target_date)

  // Spec #61 §6 — Pro × mission_active footer affordance: surface
  // resume_stale as a within-mount secondary signal for Pro/Enterprise
  // users with a 21+d-old scan. Free users don't get this affordance
  // (re-scan blocked by spec #56 lifetime cap; would dead-end).
  const isPaid = context.plan === 'pro' || context.plan === 'enterprise'
  const scanAgeDays = _daysSinceISO(context.last_scan_date)
  const showStaleScanFooter =
    isPaid && scanAgeDays !== null && scanAgeDays >= RESUME_STALE_DAYS

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
        {showStaleScanFooter && (
          <div
            data-testid="mission-active-stale-scan-footer"
            className="mt-2 text-xs text-text-muted"
          >
            Your scan is {scanAgeDays} days old — re-scan after this mission.
          </div>
        )}
      </div>
    </DashboardWidget>
  )
}
