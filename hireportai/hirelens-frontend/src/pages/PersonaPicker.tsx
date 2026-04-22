import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Target, Flame, Users } from 'lucide-react'
import { useAuth, type Persona } from '@/context/AuthContext'
import { updatePersona } from '@/services/api'
import { capture } from '@/utils/posthog'
import { FIRST_ACTION_SEEN_KEY } from '@/pages/FirstAction'

// Spec #53 OD-3: inline whitelist for the `?return_to=` URL param. Any path
// not in this set falls back to the existing `first_action_seen` → /home vs
// /first-action routing. The whitelist prevents open-redirect from arbitrary
// attacker-controlled values while letting the unlock CTAs (CountdownWidget,
// MissionDateGate) return the user to their origin after saving a date.
const RETURN_TO_WHITELIST: ReadonlySet<string> = new Set([
  '/home',
  '/learn',
  '/learn/mission',
  '/prep/analyze',
  '/prep/results',
  '/prep/rewrite',
  '/prep/interview',
  '/prep/tracker',
  '/profile',
])

interface PersonaCard {
  id: Persona
  icon: typeof Target
  label: string
  description: string
}

const PERSONAS: PersonaCard[] = [
  {
    id: 'interview_prepper',
    icon: Target,
    label: 'Interview-Prepper',
    description: 'I have a Google interview in 14 days',
  },
  {
    id: 'career_climber',
    icon: Flame,
    label: 'Career-Climber',
    description: 'I want to stay sharp and get promoted',
  },
  {
    id: 'team_lead',
    icon: Users,
    label: 'Team Lead',
    description: 'My team needs to learn agentic AI patterns',
  },
]

export default function PersonaPicker() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, updateUser } = useAuth()
  // Spec #53 §7.4: when the unlock CTAs send the user here to add a date
  // post-onboarding, pre-select interview_prepper so the expansion block
  // opens automatically. Users arriving via the normal null-persona gate
  // land with `selected === null` and pick fresh.
  const returnToRaw = searchParams.get('return_to')
  const returnTo =
    returnToRaw && RETURN_TO_WHITELIST.has(returnToRaw) ? returnToRaw : null
  const [selected, setSelected] = useState<Persona | null>(
    returnTo && user?.persona === 'interview_prepper' ? 'interview_prepper' : null,
  )
  const [targetDate, setTargetDate] = useState('')
  const [targetCompany, setTargetCompany] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    capture('persona_picker_shown', { is_new_user: user?.persona == null })
  }, [user?.persona])

  async function handleContinue() {
    if (!selected || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      const trimmedCompany = targetCompany.trim()
      const body = {
        persona: selected,
        ...(selected === 'interview_prepper' && targetDate
          ? { interview_target_date: targetDate }
          : {}),
        ...(selected === 'interview_prepper' && trimmedCompany
          ? { interview_target_company: trimmedCompany }
          : {}),
      }
      const updated = await updatePersona(body)
      capture('persona_selected', {
        persona: selected,
        has_target_date: selected === 'interview_prepper' && !!targetDate,
        has_target_company: selected === 'interview_prepper' && !!trimmedCompany,
      })
      // Spec #53 §7.1: if the user picked interview_prepper but left the date
      // blank, record the signal so telemetry can quantify the "broadly
      // prepping, no specific interview" cohort. Fires alongside (not
      // instead of) persona_selected; never gates or delays the navigate.
      if (selected === 'interview_prepper' && !targetDate) {
        capture('interview_target_date_skipped', { source: 'onboarding' })
      }
      // Spec #53 §7.4: the return_to param takes precedence over the
      // default onboarding route. Both unlock CTAs (Countdown + MissionMode)
      // append `?return_to=<whitelisted-path>` so the user lands back where
      // they started after saving a date.
      if (targetDate && selected === 'interview_prepper') {
        capture('interview_target_date_added', {
          source: returnTo ? 'persona_edit' : 'onboarding',
        })
      }
      updateUser(updated)
      if (returnTo) {
        navigate(returnTo, { replace: true })
        return
      }
      const seen =
        typeof window !== 'undefined' &&
        window.localStorage.getItem(FIRST_ACTION_SEEN_KEY) === 'true'
      navigate(seen ? '/home' : '/first-action', { replace: true })
    } catch {
      setError("Couldn't save your selection. Please try again.")
      setSubmitting(false)
    }
  }

  return (
    <div
      data-testid="persona-picker"
      className="min-h-screen bg-bg-base flex items-center justify-center px-4 py-10"
    >
      <div className="w-full max-w-xl">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary mb-2">
            What brings you to <span className="text-accent-primary">SkillForge</span>?
          </h1>
          <p className="text-sm text-text-secondary">
            Pick the goal that fits you best — we'll tailor your experience.
          </p>
        </motion.div>

        <div className="flex flex-col gap-3">
          {PERSONAS.map((p) => {
            const Icon = p.icon
            const isSelected = selected === p.id
            return (
              <motion.button
                key={p.id}
                type="button"
                data-testid={`persona-card-${p.id}`}
                data-selected={isSelected ? 'true' : 'false'}
                onClick={() => setSelected(p.id)}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={[
                  'w-full text-left flex items-start gap-4 p-4 rounded-xl border-2 transition-colors',
                  isSelected
                    ? 'border-border-accent bg-accent-primary/5'
                    : 'border-border hover:border-border-accent/60 bg-bg-surface',
                ].join(' ')}
              >
                <div
                  className={[
                    'w-11 h-11 rounded-lg flex items-center justify-center shrink-0',
                    isSelected
                      ? 'bg-accent-primary/15 text-accent-primary'
                      : 'bg-bg-elevated text-text-secondary',
                  ].join(' ')}
                >
                  <Icon size={20} />
                </div>
                <div className="flex-1">
                  <div
                    className={[
                      'font-display font-semibold text-base',
                      isSelected ? 'text-accent-primary' : 'text-text-primary',
                    ].join(' ')}
                  >
                    {p.label}
                  </div>
                  <div className="text-sm text-text-secondary mt-0.5">
                    {p.description}
                  </div>
                </div>
              </motion.button>
            )
          })}
        </div>

        <AnimatePresence initial={false}>
          {selected === 'interview_prepper' && (
            <motion.div
              key="interview-extras"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="mt-4 p-4 rounded-xl border border-border bg-bg-surface flex flex-col gap-3">
                <div>
                  <label
                    htmlFor="interview-target-date"
                    className="block text-xs font-medium text-text-secondary mb-1"
                  >
                    Interview date
                  </label>
                  <input
                    id="interview-target-date"
                    type="date"
                    data-testid="interview-target-date-input"
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-md border border-border bg-bg-base text-text-primary text-sm outline-none focus:border-border-accent"
                  />
                  <div className="mt-1 text-xs text-text-muted">
                    Optional — leave blank if you're prepping broadly.
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="interview-target-company"
                    className="block text-xs font-medium text-text-secondary mb-1"
                  >
                    Target company
                  </label>
                  <input
                    id="interview-target-company"
                    type="text"
                    data-testid="interview-target-company-input"
                    value={targetCompany}
                    onChange={(e) => setTargetCompany(e.target.value.slice(0, 100))}
                    maxLength={100}
                    placeholder="e.g. Google"
                    className="w-full px-3 py-2 rounded-md border border-border bg-bg-base text-text-primary text-sm outline-none focus:border-border-accent"
                  />
                  <div className="mt-1 flex items-center justify-between text-xs text-text-muted">
                    <span>Optional — e.g. Google in 14 days.</span>
                    <span>{targetCompany.length}/100</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <div
            role="alert"
            className="mt-4 px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger"
          >
            {error}
          </div>
        )}

        <button
          type="button"
          data-testid="persona-continue"
          disabled={!selected || submitting}
          onClick={handleContinue}
          className="mt-6 w-full py-3 rounded-lg font-semibold text-sm bg-accent-primary text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent-primary/90 transition-colors"
        >
          {submitting ? 'Saving…' : 'Continue'}
        </button>
      </div>
    </div>
  )
}
