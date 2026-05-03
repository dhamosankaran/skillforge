import { useEffect, useRef, useState } from 'react'
import { useAuth, type Persona } from '@/context/AuthContext'
import { markHomeFirstVisit } from '@/services/api'
import { capture } from '@/utils/posthog'
import { useHomeState } from '@/hooks/useHomeState'
import { TodaysReviewWidget } from '@/components/home/widgets/TodaysReviewWidget'
import { StreakWidget } from '@/components/home/widgets/StreakWidget'
import { WeeklyProgressWidget } from '@/components/home/widgets/WeeklyProgressWidget'
import { LastScanWidget } from '@/components/home/widgets/LastScanWidget'
import { InterviewTargetWidget } from '@/components/home/widgets/InterviewTargetWidget'
import { CountdownWidget } from '@/components/home/widgets/CountdownWidget'
import { HomeScoreDeltaWidget } from '@/components/home/widgets/HomeScoreDeltaWidget'
import { TeamComingSoonWidget } from '@/components/home/widgets/TeamComingSoonWidget'
import { StateAwareWidgets } from '@/components/home/StateAwareWidgets'
import { HomeStatusHero } from '@/components/home/HomeStatusHero'
import { InterviewPrepperChecklist } from '@/components/home/widgets/InterviewPrepperChecklist'
import { StudyGapsPromptWidget } from '@/components/home/widgets/StudyGapsPromptWidget'
import { useUsage } from '@/context/UsageContext'
import { fetchActiveMission, fetchUserApplications } from '@/services/api'
import type { NextInterview } from '@/types/homeState'

const GRID = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'

interface PersonaModeProps {
  persona: Persona
  /**
   * Spec #61 §3 — composition suppression flags computed once in
   * HomeDashboard from the resolved state-slot data + user fields.
   */
  countdownSuppressedByMissionState: boolean
  interviewTargetSuppressedByMissionState: boolean
  lastScanSuppressed: boolean
}

function InterviewPrepperMode({
  persona,
  nextInterview,
  countdownSuppressedByMissionState,
  interviewTargetSuppressedByMissionState,
  lastScanSuppressed,
}: PersonaModeProps & {
  nextInterview: NextInterview | null
}) {
  return (
    <>
      <InterviewPrepperChecklist />
      <div data-testid="home-mode-interview_prepper" className={GRID}>
        <CountdownWidget
          persona={persona}
          nextInterview={nextInterview}
          suppressedByMissionState={countdownSuppressedByMissionState}
        />
        {/* Spec #63 (E-043) §8.7 — D-5 mount: same tracker_id as
            CountdownWidget; self-suppresses when history.length < 2. */}
        <HomeScoreDeltaWidget
          persona={persona}
          trackerId={nextInterview?.tracker_id ?? null}
          company={nextInterview?.company ?? null}
        />
        <InterviewTargetWidget
          persona={persona}
          nextInterview={nextInterview}
          suppressedByMissionState={interviewTargetSuppressedByMissionState}
        />
        <TodaysReviewWidget persona={persona} />
        <LastScanWidget persona={persona} suppressed={lastScanSuppressed} />
      </div>
    </>
  )
}

function CareerClimberMode({
  persona,
  lastScanSuppressed,
}: PersonaModeProps) {
  return (
    <div data-testid="home-mode-career_climber" className={GRID}>
      <StreakWidget persona={persona} />
      <TodaysReviewWidget persona={persona} />
      <WeeklyProgressWidget persona={persona} />
      <LastScanWidget persona={persona} suppressed={lastScanSuppressed} />
    </div>
  )
}

function TeamLeadMode({ persona }: { persona: Persona }) {
  return (
    <div data-testid="home-mode-team_lead" className={GRID}>
      <TodaysReviewWidget persona={persona} />
      <StreakWidget persona={persona} />
      <WeeklyProgressWidget persona={persona} />
      <TeamComingSoonWidget persona={persona} />
    </div>
  )
}

/**
 * StudyGapsPromptWidget needs the same predicate set HomeDashboard uses
 * for the LastScan suppression flag (avoid double-fetch and ensure the
 * suppression flag and the prompt's render decision agree). Hoist the
 * predicate fetches into a small hook.
 */
function useStudyPromptEligibility() {
  const { usage } = useUsage()
  const [hasRecentScan, setHasRecentScan] = useState<boolean | null>(null)
  const [hasActiveMission, setHasActiveMission] = useState<boolean | null>(null)

  const planEligible = usage.plan === 'free' && !usage.isAdmin

  useEffect(() => {
    if (!planEligible) return
    let cancelled = false
    fetchUserApplications()
      .then((apps) => !cancelled && setHasRecentScan(apps.length > 0))
      .catch(() => !cancelled && setHasRecentScan(false))
    return () => {
      cancelled = true
    }
  }, [planEligible])

  useEffect(() => {
    if (!planEligible) return
    let cancelled = false
    fetchActiveMission()
      .then((m) => !cancelled && setHasActiveMission(m?.status === 'active'))
      .catch(() => !cancelled && setHasActiveMission(false))
    return () => {
      cancelled = true
    }
  }, [planEligible])

  return {
    eligible:
      planEligible && hasRecentScan === true && hasActiveMission === false,
  }
}

export default function HomeDashboard() {
  const { user, updateUser } = useAuth()
  const capturedRef = useRef(false)
  const stampedRef = useRef(false)

  // Spec #61 — single source of truth for state-slot data; passed to
  // both StateAwareWidgets (slot rendering) and persona modes (§3
  // composition suppression flags).
  const homeState = useHomeState()
  const topState = homeState.data?.states[0] ?? null

  // Spec #61 §3.1 — Mission state suppresses Countdown only when the
  // active mission's target_date matches the user's nearest upcoming
  // interview (per-mission suppression). Source flipped from
  // `user.interview_target_date` to `homeState.context.next_interview.date`
  // per spec #57 AC-7 (deprecated user-level read). InterviewTarget §5
  // suppression is broader: any Mission state in the slot.
  const nextInterview: NextInterview | null =
    homeState.data?.context.next_interview ?? null
  const missionStateActive =
    topState === 'mission_active' || topState === 'mission_overdue'
  const missionTargetMatchesUser =
    homeState.data?.context.mission_target_date != null &&
    nextInterview != null &&
    homeState.data.context.mission_target_date === nextInterview.date
  const countdownSuppressedByMissionState =
    missionStateActive && missionTargetMatchesUser
  const interviewTargetSuppressedByMissionState = missionStateActive

  // Spec #61 §4.1 — when StudyGapsPromptWidget renders, suppress
  // LastScan from the static grid; prompt rolls scan content into body.
  const studyPrompt = useStudyPromptEligibility()
  const lastScanSuppressed = studyPrompt.eligible

  useEffect(() => {
    if (!user?.persona) return
    if (capturedRef.current) return
    capturedRef.current = true
    capture('home_dashboard_viewed', { persona: user.persona })
  }, [user?.persona])

  // B-016 / B-027. Snapshot first-visit state on mount: the stamp effect
  // below persists the timestamp server-side, but we hold the greeting fork
  // frozen for the lifetime of this mount so the copy does not flip from
  // "Welcome" → "Welcome back" mid-session when updateUser applies the
  // stamped user.
  const [isFirstVisit] = useState<boolean>(
    () => user != null && user.home_first_visit_seen_at == null,
  )
  useEffect(() => {
    if (!user?.persona) return
    if (!isFirstVisit) return
    if (stampedRef.current) return
    stampedRef.current = true
    markHomeFirstVisit()
      .then((updated) => updateUser(updated))
      .catch(() => {
        // Non-blocking. If the stamp fails, the greeting will still read
        // "Welcome" on the next visit — idempotent retry. No toast.
      })
  }, [user?.persona, isFirstVisit, updateUser])

  if (!user || !user.persona) return null

  const firstName = user.name?.trim().split(/\s+/)[0] ?? ''
  const greeting = isFirstVisit
    ? firstName
      ? `Welcome, ${firstName}.`
      : 'Welcome to SkillForge.'
    : firstName
      ? `Welcome back, ${firstName}.`
      : 'Welcome back.'

  return (
    <div className="min-h-screen bg-bg-base px-4 py-8 sm:px-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary mb-8">
          {greeting}
        </h1>
        <HomeStatusHero />
        <StateAwareWidgets
          persona={user.persona}
          data={homeState.data}
          isLoading={homeState.isLoading}
          error={homeState.error}
        />
        <StudyGapsPromptWidget suppressed={!studyPrompt.eligible} />
        {user.persona === 'interview_prepper' && (
          <InterviewPrepperMode
            persona={user.persona}
            nextInterview={nextInterview}
            countdownSuppressedByMissionState={
              countdownSuppressedByMissionState
            }
            interviewTargetSuppressedByMissionState={
              interviewTargetSuppressedByMissionState
            }
            lastScanSuppressed={lastScanSuppressed}
          />
        )}
        {user.persona === 'career_climber' && (
          <CareerClimberMode
            persona={user.persona}
            countdownSuppressedByMissionState={false}
            interviewTargetSuppressedByMissionState={false}
            lastScanSuppressed={lastScanSuppressed}
          />
        )}
        {user.persona === 'team_lead' && <TeamLeadMode persona={user.persona} />}
      </div>
    </div>
  )
}
