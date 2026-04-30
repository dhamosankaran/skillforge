import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { Countdown } from '@/components/mission/Countdown'
import { type Persona } from '@/context/AuthContext'
import { fetchActiveMission } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { MissionDetailResponse } from '@/types'
import type { NextInterview } from '@/types/homeState'

interface CountdownWidgetProps {
  persona: Persona
  /**
   * Spec #57 — nearest-upcoming interview sourced from
   * `tracker_applications_v2`. Null while loading or when no row matches.
   */
  nextInterview: NextInterview | null
  /**
   * Spec #61 §3.1 — when the state-aware Mission slot renders for the
   * same active mission as this user's interview, the static Countdown is
   * suppressed to avoid the duplicate-render symptom (audit finding #1).
   * HomeDashboard computes this and passes it down. Default false.
   */
  suppressedByMissionState?: boolean
}

function daysUntil(iso: string): number {
  const target = new Date(`${iso}T00:00:00`)
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const diffMs = target.getTime() - now.getTime()
  return Math.max(0, Math.ceil(diffMs / 86_400_000))
}

export function CountdownWidget({
  persona,
  nextInterview,
  suppressedByMissionState = false,
}: CountdownWidgetProps) {
  const renderedRef = useRef(false)

  if (suppressedByMissionState) return null

  const [mission, setMission] = useState<MissionDetailResponse | null>(null)
  const [missionChecked, setMissionChecked] = useState(false)

  const hasDate = nextInterview != null
  const days = hasDate ? daysUntil(nextInterview.date) : null

  useEffect(() => {
    if (!hasDate) {
      setMissionChecked(true)
      return
    }
    fetchActiveMission()
      .then((m) => setMission(m))
      .catch(() => setMission(null))
      .finally(() => setMissionChecked(true))
  }, [hasDate])

  // Spec #57 §7.1 — once-per-mount render telemetry. `days_until` only when
  // a date is present.
  useEffect(() => {
    if (renderedRef.current) return
    renderedRef.current = true
    capture('countdown_widget_rendered', {
      has_date: hasDate,
      ...(hasDate && days != null ? { days_until: days } : {}),
    })
  }, [hasDate, days])

  // Spec #57 AC-5 — third branch: no date AND non-interview-prepper persona
  // → widget does not render at all. HomeDashboard only mounts this widget
  // for interview_prepper, but the branch is defensive against future mounts.
  if (!hasDate && persona !== 'interview_prepper') return null

  // Spec #57 AC-5 — no date AND interview_prepper: "Add your interview date"
  // CTA routing to /prep/tracker?new=1. Date capture lives in the tracker
  // row editor (§6.1); this widget no longer writes user-level fields.
  if (!hasDate) {
    return (
      <DashboardWidget
        title="Countdown"
        testid="countdown"
        persona={persona}
        state="data"
      >
        <div className="flex flex-col gap-3">
          <p className="text-sm text-text-secondary">
            Add your interview date to unlock countdown.
          </p>
          <Link
            to="/prep/tracker?new=1"
            data-testid="countdown-add-date-cta"
            onClick={() =>
              capture('countdown_widget_add_date_cta_clicked', { source: 'home' })
            }
            className="self-start px-4 py-2 rounded-md bg-accent-primary text-white text-sm font-medium hover:bg-accent-primary/90 transition-colors"
          >
            Add your interview date
          </Link>
        </div>
      </DashboardWidget>
    )
  }

  // Date-present branch
  const totalDays = Math.max(days ?? 1, 1)
  const progressPct = totalDays === 0 ? 100 : ((totalDays - (days ?? 0)) / totalDays) * 100

  const state: WidgetState = 'data'
  const action = missionChecked
    ? mission && mission.status === 'active'
      ? { label: 'View mission', href: '/learn/mission' }
      : { label: 'Start a Mission sprint', href: '/learn/mission' }
    : undefined

  const dayLabel = days === 0 ? 'Today' : `${days} days until ${nextInterview.company}`
  const focusHref = `/prep/tracker?focus=${encodeURIComponent(nextInterview.tracker_id)}`

  return (
    <DashboardWidget
      title="Countdown"
      testid="countdown"
      persona={persona}
      state={state}
      action={action}
    >
      <div className="flex flex-col gap-2">
        <Link
          to={focusHref}
          data-testid="countdown-tracker-link"
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          {dayLabel}
        </Link>
        <Countdown
          title="Interview"
          daysRemaining={days ?? 0}
          totalDays={totalDays}
          progressPct={progressPct}
        />
      </div>
    </DashboardWidget>
  )
}
