/**
 * Spec #66 — Live loop-progress strip in AppShell for the
 * Interview-Prepper persona. Persistent across `/home`, `/learn/*`,
 * `/prep/*` (anywhere AppShell renders chrome).
 *
 * Render gate: persona === 'interview_prepper' && next_interview != null.
 * Chromeless-path suppression is the AppShell parent's responsibility
 * (this component is mounted only when chrome renders).
 */
import { useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useHomeState } from '@/hooks/useHomeState'
import { useScoreHistory } from '@/hooks/useScoreHistory'
import { useLoopProgress } from '@/hooks/useLoopProgress'
import {
  LoopFrame,
  type LoopFrameStep,
  type LoopFrameStepState,
} from '@/components/dashboard/LoopFrame'
import { capture } from '@/utils/posthog'

const MIN_DAYS_SINCE_SCAN = 3
const MIN_PERCENT_REVIEWED = 50
const INTERVIEW_ALERT_WINDOW_DAYS = 7

type StepStateMap = Partial<Record<LoopFrameStep, LoopFrameStepState>>

function daysUntilUtc(dateIso: string): number {
  const target = new Date(`${dateIso}T00:00:00Z`)
  const now = new Date()
  const todayMid = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  )
  return Math.ceil((target.getTime() - todayMid) / (1000 * 60 * 60 * 24))
}

function deriveCurrentStep(states: StepStateMap): LoopFrameStep {
  // Per §8.4 / D-10: lowest 'current' index → 'alert' (4) → 4.
  for (const idx of [1, 2, 3, 4] as LoopFrameStep[]) {
    if (states[idx] === 'current') return idx
  }
  if (states[4] === 'alert') return 4
  return 4
}

export function LoopProgressStrip() {
  const { user } = useAuth()
  const homeState = useHomeState()
  const navigate = useNavigate()

  const persona = user?.persona ?? null
  const nextInterview = homeState.data?.context.next_interview ?? null
  const trackerId = nextInterview?.tracker_id ?? null

  const scoreHistory = useScoreHistory(trackerId)
  const loopProgress = useLoopProgress(trackerId)

  const stepStates = useMemo<StepStateMap>(() => {
    const states: StepStateMap = {}

    // Step 1 — Scanned
    const history = scoreHistory.data?.history ?? []
    const latestScore = history.length > 0 ? history[history.length - 1] : null
    states[1] = latestScore ? 'done' : 'future'

    // Step 2 — Studying
    if (states[1] !== 'done' || !loopProgress.data) {
      states[2] = 'future'
    } else if (loopProgress.data.total_gap_cards === 0) {
      states[2] = 'future'
    } else if (loopProgress.data.percent_reviewed < MIN_PERCENT_REVIEWED) {
      states[2] = 'current'
    } else {
      states[2] = 'done'
    }

    // Step 3 — Re-scan (per D-1: history.length ≥ 2 AND step-2 done = done)
    const days = loopProgress.data?.days_since_last_scan ?? null
    if (states[2] === 'done' && history.length >= 2) {
      states[3] = 'done'
    } else if (
      states[2] === 'done' &&
      days !== null &&
      days >= MIN_DAYS_SINCE_SCAN
    ) {
      states[3] = 'current'
    } else {
      states[3] = 'locked'
    }

    // Step 4 — Interview
    if (nextInterview) {
      const dUntil = daysUntilUtc(nextInterview.date)
      if (dUntil < 0) {
        states[4] = 'alert'
      } else if (dUntil <= INTERVIEW_ALERT_WINDOW_DAYS) {
        states[4] = 'current'
      } else {
        states[4] = 'future'
      }
    } else {
      states[4] = 'future'
    }

    return states
  }, [scoreHistory.data, loopProgress.data, nextInterview])

  const currentStep = useMemo(
    () => deriveCurrentStep(stepStates),
    [stepStates],
  )

  // Analytics — once-per-mount keyed on tracker_id (D-7).
  const renderedRef = useRef<string | null>(null)
  const unlockedRef = useRef<boolean>(false)
  const completedRef = useRef<Set<LoopFrameStep>>(new Set())
  const plan = homeState.data?.context.plan ?? 'free'

  useEffect(() => {
    if (!trackerId) return
    if (renderedRef.current === trackerId) return
    // Wait for at least step 4 to resolve into a non-future state OR
    // for step 1 to resolve so the strip has something to render.
    const hasStep4 = stepStates[4] != null
    if (!hasStep4) return
    renderedRef.current = trackerId
    unlockedRef.current = stepStates[3] === 'current'
    capture('loop_strip_rendered', {
      persona,
      plan,
      current_step: currentStep,
      has_overdue: stepStates[4] === 'alert',
      days_until_interview: nextInterview
        ? daysUntilUtc(nextInterview.date)
        : null,
      tracker_id: trackerId,
    })
  }, [trackerId, stepStates, persona, plan, currentStep, nextInterview])

  useEffect(() => {
    if (renderedRef.current == null) return
    // Only fire after the initial render-event has been captured.
    if (!unlockedRef.current && stepStates[3] === 'current') {
      unlockedRef.current = true
      capture('loop_strip_rescan_unlocked', {
        plan,
        days_since_last_scan: loopProgress.data?.days_since_last_scan ?? null,
        percent_reviewed: loopProgress.data?.percent_reviewed ?? 0,
      })
    }
  }, [stepStates, plan, loopProgress.data])

  useEffect(() => {
    if (renderedRef.current == null) return
    for (const idx of [1, 2, 3] as LoopFrameStep[]) {
      if (stepStates[idx] === 'done' && !completedRef.current.has(idx)) {
        completedRef.current.add(idx)
        capture('loop_strip_step_completed', {
          step: idx,
          plan,
          days_in_step: null,
        })
      }
    }
  }, [stepStates, plan])

  // Render gate.
  if (persona !== 'interview_prepper') return null
  if (!nextInterview) return null

  const handleStepClick = (step: LoopFrameStep) => {
    if (step !== 3) return
    if (stepStates[3] !== 'current') return
    capture('loop_strip_step_clicked', {
      step: 3,
      current_step: currentStep,
      plan,
    })
    navigate(
      `/prep/tracker?focus=${encodeURIComponent(
        nextInterview.tracker_id,
      )}&action=rescan`,
    )
  }

  return (
    <div
      data-testid="loop-progress-strip"
      role="region"
      aria-label="Interview preparation progress"
      className="border-b border-border bg-bg-base px-4 py-2 sm:px-8"
    >
      <div className="max-w-6xl mx-auto">
        <LoopFrame
          surface="appshell"
          currentStep={currentStep}
          score={
            scoreHistory.data?.history?.length
              ? scoreHistory.data.history[
                  scoreHistory.data.history.length - 1
                ].overall_score
              : undefined
          }
          interviewDate={nextInterview.date}
          plan={plan === 'enterprise' ? 'pro' : plan}
          stepStates={stepStates}
          onStepClick={handleStepClick}
          compact
        />
      </div>
    </div>
  )
}

export default LoopProgressStrip
