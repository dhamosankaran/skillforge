import { useCallback, useEffect, useState } from 'react'
import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { Countdown } from '@/components/mission/Countdown'
import { useAuth, type Persona } from '@/context/AuthContext'
import { fetchActiveMission, updatePersona } from '@/services/api'
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
  const { updateUser } = useAuth()
  const [chosenDate, setChosenDate] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

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

  const handleSave = useCallback(async () => {
    if (!chosenDate || submitting) return
    setSubmitError(null)
    setSubmitting(true)
    try {
      const updated = await updatePersona({
        persona,
        interview_target_date: chosenDate,
      })
      updateUser(updated)
    } catch {
      setSubmitError("Couldn't save your date. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }, [chosenDate, persona, submitting, updateUser])

  // Mode 1 — no date set: render inline date-setter inside state="data"
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
            Set your interview date to start the countdown.
          </p>
          <input
            type="date"
            data-testid="countdown-date-input"
            value={chosenDate}
            onChange={(e) => setChosenDate(e.target.value)}
            className="w-full px-3 py-2 rounded-md border border-border bg-bg-base text-text-primary text-sm outline-none focus:border-border-accent"
          />
          <button
            type="button"
            data-testid="countdown-save"
            disabled={!chosenDate || submitting}
            onClick={handleSave}
            className="self-start px-4 py-2 rounded-md bg-accent-primary text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent-primary/90 transition-colors"
          >
            {submitting ? 'Saving…' : 'Save'}
          </button>
          {submitError && (
            <div role="alert" className="text-xs text-danger">
              {submitError}
            </div>
          )}
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
