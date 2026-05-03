import { useEffect, useRef, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useHomeState } from '@/hooks/useHomeState'
import { fetchDailyQueue, fetchUserApplications } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { TrackerApplication } from '@/types'

type IpClause = 'company' | 'days' | 'due' | 'due_zero' | 'score'
type CcClause = 'streak' | 'streak_zero' | 'due' | 'due_zero'

function daysFromIso(iso: string): number {
  const target = new Date(iso)
  const now = new Date()
  const targetMid = Date.UTC(
    target.getUTCFullYear(),
    target.getUTCMonth(),
    target.getUTCDate(),
  )
  const todayMid = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  )
  return Math.ceil((targetMid - todayMid) / 86_400_000)
}

export function HomeStatusHero() {
  const { user } = useAuth()
  const homeState = useHomeState()

  const [dueCount, setDueCount] = useState<number | null>(null)
  const [latestApp, setLatestApp] = useState<TrackerApplication | null>(null)

  const persona = user?.persona ?? null
  const renderable = persona === 'interview_prepper' || persona === 'career_climber'

  useEffect(() => {
    if (!renderable) return
    let cancelled = false
    fetchDailyQueue()
      .then((res) => !cancelled && setDueCount(res.total_due))
      .catch(() => !cancelled && setDueCount(null))
    return () => {
      cancelled = true
    }
  }, [renderable])

  useEffect(() => {
    if (persona !== 'interview_prepper') return
    let cancelled = false
    fetchUserApplications()
      .then((apps) => {
        if (cancelled) return
        if (apps.length === 0) {
          setLatestApp(null)
          return
        }
        const sorted = [...apps].sort((a, b) =>
          (b.created_at ?? '').localeCompare(a.created_at ?? ''),
        )
        setLatestApp(sorted[0])
      })
      .catch(() => !cancelled && setLatestApp(null))
    return () => {
      cancelled = true
    }
  }, [persona])

  const capturedRef = useRef(false)

  let text: string | null = null
  const clauses: (IpClause | CcClause)[] = []

  if (persona === 'interview_prepper') {
    const next = homeState.data?.context.next_interview ?? null
    const days = next ? daysFromIso(next.date) : null
    const parts: string[] = []
    if (next && days != null && days >= 0) {
      if (next.company) {
        parts.push(`${next.company} interview in ${days}d.`)
        clauses.push('company', 'days')
      } else {
        parts.push(`Interview in ${days}d.`)
        clauses.push('days')
      }
    }
    if (dueCount != null) {
      if (dueCount > 0) {
        parts.push(`${dueCount} cards due today.`)
        clauses.push('due')
      } else {
        parts.push('No cards due today.')
        clauses.push('due_zero')
      }
    }
    if (latestApp && latestApp.ats_score != null) {
      parts.push(`Last scan was ${latestApp.ats_score}%.`)
      clauses.push('score')
    }
    text = parts.length > 0 ? parts.join(' ') : null
  } else if (persona === 'career_climber') {
    const streak = homeState.data?.context.current_streak ?? null
    const parts: string[] = []
    if (streak != null) {
      if (streak > 0) {
        parts.push(`${streak}-day streak.`)
        clauses.push('streak')
      } else {
        parts.push('Start your streak today.')
        clauses.push('streak_zero')
      }
    }
    if (dueCount != null) {
      if (dueCount > 0) {
        parts.push(`${dueCount} cards due today.`)
        clauses.push('due')
      } else {
        parts.push('No cards due today.')
        clauses.push('due_zero')
      }
    }
    text = parts.length > 0 ? parts.join(' ') : null
  }

  useEffect(() => {
    if (capturedRef.current) return
    if (text == null) return
    if (persona !== 'interview_prepper' && persona !== 'career_climber') return
    capturedRef.current = true
    capture('home_status_hero_rendered', {
      persona,
      plan: homeState.data?.context.plan ?? 'free',
      clauses_shown: clauses,
    })
  }, [text, persona, clauses, homeState.data?.context.plan])

  if (!renderable) return null
  if (text == null) return null

  return (
    <p
      data-testid="home-status-hero"
      className="text-lg text-text-secondary mb-6"
    >
      {text}
    </p>
  )
}
