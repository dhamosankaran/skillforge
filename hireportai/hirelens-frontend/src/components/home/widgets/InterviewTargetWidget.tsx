import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import type { Persona } from '@/context/AuthContext'
import type { NextInterview } from '@/types/homeState'

interface InterviewTargetWidgetProps {
  persona: Persona
  /**
   * Spec #57 — nearest-upcoming interview sourced from
   * `tracker_applications_v2`. The widget shows date+company when present
   * and an empty-state message otherwise.
   */
  nextInterview: NextInterview | null
  /**
   * Spec #61 §5 — when the state-aware Mission slot renders
   * (mission_active or mission_overdue), this widget is suppressed
   * entirely; mission framing already covers the date and the
   * company-gap empty state is moot mid-mission (audit finding #2).
   * HomeDashboard computes this and passes it down. Default false.
   */
  suppressedByMissionState?: boolean
}

function formatDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function InterviewTargetWidget({
  persona,
  nextInterview,
  suppressedByMissionState = false,
}: InterviewTargetWidgetProps) {
  if (suppressedByMissionState) return null

  const hasInterview = nextInterview != null
  const state: WidgetState = hasInterview ? 'data' : 'empty'

  return (
    <DashboardWidget
      title="Interview Target"
      testid="interview-target"
      persona={persona}
      state={state}
      emptyMessage="No upcoming interview scheduled. Add a date to a tracker row to see it here."
    >
      {hasInterview && (
        <div className="flex flex-col gap-1">
          <div className="font-display text-base font-semibold text-text-primary">
            {nextInterview.company}
          </div>
          <div className="text-sm text-text-secondary">
            {formatDate(nextInterview.date)}
          </div>
        </div>
      )}
    </DashboardWidget>
  )
}
