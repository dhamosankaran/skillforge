import { useEffect, useRef } from 'react'
import { useAuth, type Persona } from '@/context/AuthContext'
import { capture } from '@/utils/posthog'
import { TodaysReviewWidget } from '@/components/home/widgets/TodaysReviewWidget'
import { StreakWidget } from '@/components/home/widgets/StreakWidget'
import { WeeklyProgressWidget } from '@/components/home/widgets/WeeklyProgressWidget'
import { LastScanWidget } from '@/components/home/widgets/LastScanWidget'
import { InterviewTargetWidget } from '@/components/home/widgets/InterviewTargetWidget'
import { CountdownWidget } from '@/components/home/widgets/CountdownWidget'
import { TeamComingSoonWidget } from '@/components/home/widgets/TeamComingSoonWidget'

const GRID = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'

function InterviewPrepperMode({
  persona,
  company,
  date,
}: {
  persona: Persona
  company: string | null | undefined
  date: string | null | undefined
}) {
  return (
    <div data-testid="home-mode-interview_prepper" className={GRID}>
      <CountdownWidget persona={persona} date={date} />
      <InterviewTargetWidget persona={persona} company={company} date={date} />
      <TodaysReviewWidget persona={persona} />
      <LastScanWidget persona={persona} />
    </div>
  )
}

function CareerClimberMode({ persona }: { persona: Persona }) {
  return (
    <div data-testid="home-mode-career_climber" className={GRID}>
      <StreakWidget persona={persona} />
      <TodaysReviewWidget persona={persona} />
      <WeeklyProgressWidget persona={persona} />
      <LastScanWidget persona={persona} />
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

export default function HomeDashboard() {
  const { user } = useAuth()
  const capturedRef = useRef(false)

  useEffect(() => {
    if (!user?.persona) return
    if (capturedRef.current) return
    capturedRef.current = true
    capture('home_dashboard_viewed', { persona: user.persona })
  }, [user?.persona])

  if (!user || !user.persona) return null

  const firstName = user.name?.trim().split(/\s+/)[0] ?? ''
  const greeting = firstName ? `Welcome back, ${firstName}.` : 'Welcome back.'

  return (
    <div className="min-h-screen bg-bg-base px-4 py-8 sm:px-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary mb-8">
          {greeting}
        </h1>
        {user.persona === 'interview_prepper' && (
          <InterviewPrepperMode
            persona={user.persona}
            company={user.interview_target_company}
            date={user.interview_target_date}
          />
        )}
        {user.persona === 'career_climber' && (
          <CareerClimberMode persona={user.persona} />
        )}
        {user.persona === 'team_lead' && <TeamLeadMode persona={user.persona} />}
      </div>
    </div>
  )
}
