import { useEffect, useRef, useState } from 'react'
import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { Countdown } from '@/components/mission/Countdown'
import { InterviewDateModal } from '@/components/home/InterviewDateModal'
import { type Persona } from '@/context/AuthContext'
import { fetchActiveMission } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { MissionDetailResponse } from '@/types'

interface CountdownWidgetProps {
  persona: Persona
  date: string | null | undefined
  /**
   * Spec #61 §3.1 — when the state-aware Mission slot renders for the
   * same active mission as this user's `interview_target_date`, the
   * static Countdown is suppressed to avoid the duplicate-render
   * symptom (audit finding #1). HomeDashboard computes this and passes
   * it down. Default false.
   */
  suppressedByMissionState?: boolean
}

function daysUntil(iso: string): number {
  const target = new Date(iso)
  const now = new Date()
  const diffMs = target.getTime() - now.getTime()
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)))
}

export function CountdownWidget({
  persona,
  date,
  suppressedByMissionState = false,
}: CountdownWidgetProps) {
  const shownRef = useRef(false)

  if (suppressedByMissionState) return null

  const [mission, setMission] = useState<MissionDetailResponse | null>(null)
  const [missionChecked, setMissionChecked] = useState(false)
  const [dateModalOpen, setDateModalOpen] = useState(false)

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

  // Mode 1 — no date set: open an inline modal with a date-only editor.
  // B-037 supersedes spec #53 LD-3 / OD-2 for this surface only — the
  // pre-fix link to /onboarding/persona sent returning users back through
  // new-user onboarding. MissionDateGate retains the link-only affordance
  // (different surface, different context). See spec #53 §Supersession.
  if (!date) {
    return (
      <>
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
                setDateModalOpen(true)
              }}
              className="self-start px-4 py-2 rounded-md bg-accent-primary text-white text-sm font-medium hover:bg-accent-primary/90 transition-colors"
            >
              Add interview date
            </button>
          </div>
        </DashboardWidget>
        <InterviewDateModal
          open={dateModalOpen}
          onClose={() => setDateModalOpen(false)}
          surface="home_countdown"
        />
      </>
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
