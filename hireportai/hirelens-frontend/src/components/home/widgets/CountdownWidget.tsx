import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { Countdown } from '@/components/mission/Countdown'
import { type Persona } from '@/context/AuthContext'
import { fetchActiveMission } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { MissionDetailResponse } from '@/types'

interface CountdownWidgetProps {
  persona: Persona
  date: string | null | undefined
}

function daysUntil(iso: string): number {
  const target = new Date(iso)
  const now = new Date()
  const diffMs = target.getTime() - now.getTime()
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)))
}

export function CountdownWidget({ persona, date }: CountdownWidgetProps) {
  const navigate = useNavigate()
  const shownRef = useRef(false)

  const [mission, setMission] = useState<MissionDetailResponse | null>(null)
  const [missionChecked, setMissionChecked] = useState(false)

  useEffect(() => {
    if (!date) {
      setMissionChecked(true)
      return
    }
    fetchActiveMission()
      .then((m) => setMission(m))
      .catch(() => setMission(null))
      .finally(() => setMissionChecked(true))
  }, [date])

  // Spec #53 §7.2 / §9: fire countdown_unlock_cta_shown once on mount of the
  // no-date unlock affordance. Idempotent via ref (same pattern as
  // `home_dashboard_viewed` / `paywall_hit`). Fires only in Mode 1.
  useEffect(() => {
    if (date) return
    if (shownRef.current) return
    shownRef.current = true
    capture('countdown_unlock_cta_shown', { surface: 'home_countdown' })
  }, [date])

  // Mode 1 — no date set: render the LD-3 unlock affordance (link-only per
  // OD-2; the pre-B-018 inline date-setter form is dropped — no two surfaces
  // with divergent interaction models for the same no-date state).
  if (!date) {
    return (
      <DashboardWidget
        title="Countdown"
        testid="countdown"
        persona={persona}
        state="data"
      >
        <div className="flex flex-col gap-3">
          <p className="text-sm text-text-secondary">
            Add an interview date to unlock countdown.
          </p>
          <button
            type="button"
            data-testid="countdown-unlock-cta"
            onClick={() => {
              capture('countdown_unlock_cta_clicked', { surface: 'home_countdown' })
              navigate('/onboarding/persona?return_to=%2Fhome')
            }}
            className="self-start px-4 py-2 rounded-md bg-accent-primary text-white text-sm font-medium hover:bg-accent-primary/90 transition-colors"
          >
            Add interview date
          </button>
        </div>
      </DashboardWidget>
    )
  }

  // Mode 2 — date set: render Countdown + active-mission CTA
  const days = daysUntil(date)
  const totalDays = Math.max(days, 1)
  const progressPct = totalDays === 0 ? 100 : ((totalDays - days) / totalDays) * 100

  const state: WidgetState = 'data'
  const action = missionChecked
    ? mission && mission.status === 'active'
      ? { label: 'View mission', href: '/learn/mission' }
      : { label: 'Start a Mission sprint', href: '/learn/mission' }
    : undefined

  return (
    <DashboardWidget
      title="Countdown"
      testid="countdown"
      persona={persona}
      state={state}
      action={action}
    >
      <Countdown
        title="Interview"
        daysRemaining={days}
        totalDays={totalDays}
        progressPct={progressPct}
      />
    </DashboardWidget>
  )
}
