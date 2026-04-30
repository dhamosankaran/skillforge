import { useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '@/context/AuthContext'
import { useHomeState } from '@/hooks/useHomeState'
import { capture } from '@/utils/posthog'
import type { NextInterview } from '@/types/homeState'

export const FIRST_ACTION_SEEN_KEY = 'first_action_seen'

type CtaChoice = {
  label: string
  route: string
}

function daysUntil(targetIso: string): number {
  const target = new Date(`${targetIso}T00:00:00`)
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const diffMs = target.getTime() - now.getTime()
  return Math.max(0, Math.ceil(diffMs / 86_400_000))
}

export function computeCta(
  persona: 'interview_prepper' | 'career_climber' | 'team_lead',
  nextInterview: NextInterview | null,
): CtaChoice {
  if (persona === 'career_climber') {
    return { label: 'Start your first Daily Review', route: '/learn/daily' }
  }
  if (persona === 'team_lead') {
    return { label: 'Browse the card library', route: '/learn' }
  }
  // interview_prepper — spec #57 AC-7: re-source from next_interview.
  // Null preserves the existing browse-categories branch verbatim
  // (FirstAction.tsx pre-spec behaviour).
  if (!nextInterview) {
    return { label: 'Browse interview prep categories', route: '/learn' }
  }
  const n = daysUntil(nextInterview.date)
  const company = nextInterview.company.trim()
  return {
    label: company
      ? `Start your ${n}-day Mission to ${company}`
      : `Start your ${n}-day Mission`,
    route: '/learn/mission',
  }
}

function firstName(fullName: string | null | undefined): string | null {
  if (!fullName) return null
  const first = fullName.trim().split(/\s+/)[0]
  return first || null
}

export default function FirstAction() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const homeState = useHomeState()
  const hasCapturedRef = useRef(false)

  const persona = user?.persona ?? null
  const flagSet =
    typeof window !== 'undefined' &&
    window.localStorage.getItem(FIRST_ACTION_SEEN_KEY) === 'true'

  useEffect(() => {
    if (flagSet) {
      navigate('/home', { replace: true })
    }
  }, [flagSet, navigate])

  useEffect(() => {
    if (flagSet || !persona) return
    if (hasCapturedRef.current) return
    hasCapturedRef.current = true
    capture('first_action_viewed', { persona })
  }, [flagSet, persona])

  const nextInterview = homeState.data?.context.next_interview ?? null

  const cta = useMemo(() => {
    if (!persona) return null
    return computeCta(persona, nextInterview)
  }, [persona, nextInterview])

  // PersonaGate handles persona === null by redirecting to /onboarding/persona.
  // flagSet short-circuits to /home via the effect above. In both cases render
  // nothing until the redirect lands.
  if (flagSet || !persona || !cta) return null

  const name = firstName(user?.name)

  function handlePrimary() {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(FIRST_ACTION_SEEN_KEY, 'true')
    }
    capture('first_action_primary_clicked', {
      persona,
      cta_route: cta!.route,
    })
    navigate(cta!.route, { replace: true })
  }

  function handleSecondary() {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(FIRST_ACTION_SEEN_KEY, 'true')
    }
    capture('first_action_secondary_clicked', { persona })
    navigate('/home', { replace: true })
  }

  const subtitle =
    persona === 'interview_prepper'
      ? "You're prepping for an interview. Here's the fastest way to start."
      : persona === 'career_climber'
        ? "You're leveling up. Here's the fastest way to start."
        : "You're exploring for your team. Here's the fastest way to start."

  return (
    <div
      data-testid="first-action"
      className="min-h-screen bg-bg-base flex items-center justify-center px-4 py-10"
    >
      <div className="w-full max-w-xl text-center">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary mb-2">
            {name ? `Welcome, ${name}.` : 'Welcome to SkillForge.'}
          </h1>
          <p className="text-sm text-text-secondary">{subtitle}</p>
        </motion.div>

        <motion.button
          type="button"
          data-testid="first-action-primary"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={handlePrimary}
          className="w-full py-4 rounded-lg font-semibold text-base bg-accent-primary text-white hover:bg-accent-primary/90 transition-colors"
        >
          {cta.label}
        </motion.button>

        <button
          type="button"
          data-testid="first-action-secondary"
          onClick={handleSecondary}
          className="mt-4 text-sm text-text-muted hover:text-text-secondary transition-colors underline-offset-2 hover:underline"
        >
          Take me to the dashboard instead
        </button>
      </div>
    </div>
  )
}
