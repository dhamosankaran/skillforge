/**
 * Types for the state-aware home dashboard endpoint
 * (P5-S18c, spec #40 §5).
 */

export type HomeStateName =
  | 'mission_overdue'
  | 'streak_at_risk'
  | 'mission_active'
  | 'resume_stale'
  | 'inactive_returner'
  | 'first_session_done'

/**
 * Per-user nearest upcoming interview, sourced from
 * `tracker_applications_v2` per spec #57 §2.2 selection rule. Mirrors the
 * backend `NextInterview` Pydantic model in `app/schemas/home.py`.
 */
export interface NextInterview {
  date: string
  company: string
  tracker_id: string
}

export interface HomeStateContext {
  current_streak: number
  last_review_at: string | null
  active_mission_id: string | null
  mission_target_date: string | null
  last_scan_date: string | null
  plan: 'free' | 'pro' | 'enterprise'
  last_activity_at: string | null
  next_interview: NextInterview | null
}

export interface HomeStateResponse {
  persona: 'interview_prepper' | 'career_climber' | 'team_lead' | null
  states: HomeStateName[]
  context: HomeStateContext
}
