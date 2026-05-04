// Spec #67 §8.2 — Profile "Career goal" section, Career-Climber-only.
// D-2: inline-form modality. D-6: explicit Clear button (DELETE; no replacement).
// D-12: passive Profile-only re-onboarding (no /home banner).
import { useEffect, useMemo, useState } from 'react'
import { Target, Loader2, Trash2 } from 'lucide-react'
import {
  clearCareerIntent,
  getCareerIntent,
  setCareerIntent,
} from '@/services/api'
import {
  CAREER_ROLES,
  CAREER_ROLE_LABELS,
  quarterLabel,
  quarterOptions,
  type CareerRole,
} from '@/utils/careerIntent'
import { capture } from '@/utils/posthog'
import type { CareerIntent } from '@/types'

type Mode = 'view' | 'edit'

export function CareerGoalSection() {
  const [intent, setIntent] = useState<CareerIntent | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [mode, setMode] = useState<Mode>('view')
  const [role, setRole] = useState('')
  const [quarter, setQuarter] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const quarters = useMemo(() => quarterOptions(new Date()), [])

  useEffect(() => {
    let cancelled = false
    getCareerIntent()
      .then((res) => {
        if (cancelled) return
        setIntent(res)
      })
      .catch(() => {
        if (cancelled) return
        setLoadError(true)
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function openEdit() {
    setRole(intent?.target_role ?? '')
    setQuarter(intent?.target_quarter ?? '')
    setSubmitError(null)
    setMode('edit')
  }

  function cancelEdit() {
    setMode('view')
    setSubmitError(null)
  }

  async function handleSave() {
    if (!role || !quarter || submitting) return
    setSubmitError(null)
    setSubmitting(true)
    const isFirst = intent === null
    try {
      const updated = await setCareerIntent(
        { target_role: role, target_quarter: quarter },
        'profile_edit',
      )
      capture(
        isFirst ? 'career_intent_captured' : 'career_intent_updated',
        {
          target_role: role,
          target_quarter: quarter,
          source: 'profile_edit',
        },
      )
      setIntent(updated)
      setMode('view')
    } catch {
      setSubmitError("Couldn't save your goal. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleClear() {
    if (clearing || intent === null) return
    if (
      typeof window !== 'undefined' &&
      !window.confirm('Clear your career goal? You can set a new one anytime.')
    ) {
      return
    }
    const prior = intent
    setClearing(true)
    try {
      await clearCareerIntent()
      capture('career_intent_updated', {
        target_role: prior.target_role,
        target_quarter: prior.target_quarter,
        source: 'profile_edit',
        cleared: true,
      })
      setIntent(null)
    } catch {
      setSubmitError("Couldn't clear your goal. Please try again.")
    } finally {
      setClearing(false)
    }
  }

  return (
    <section data-testid="career-goal-section">
      <div className="flex items-center gap-2 mb-3">
        <Target size={14} className="text-accent-primary" />
        <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
          Career goal
        </h2>
      </div>
      <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
        {loading ? (
          <p className="text-xs text-text-muted">Loading…</p>
        ) : mode === 'edit' ? (
          <div className="flex flex-col gap-3">
            <div>
              <label
                htmlFor="career-goal-role"
                className="block text-xs font-medium text-text-secondary mb-1"
              >
                Target role
              </label>
              <select
                id="career-goal-role"
                data-testid="career-goal-role-input"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-border bg-bg-base text-text-primary text-sm outline-none focus:border-border-accent"
              >
                <option value="">Pick a role…</option>
                {CAREER_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {CAREER_ROLE_LABELS[r]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="career-goal-quarter"
                className="block text-xs font-medium text-text-secondary mb-1"
              >
                Target quarter
              </label>
              <select
                id="career-goal-quarter"
                data-testid="career-goal-quarter-input"
                value={quarter}
                onChange={(e) => setQuarter(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-border bg-bg-base text-text-primary text-sm outline-none focus:border-border-accent"
              >
                <option value="">Pick a quarter…</option>
                {quarters.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            {submitError && (
              <p role="alert" className="text-xs text-danger">{submitError}</p>
            )}
            <div className="flex items-center gap-2">
              <button
                type="button"
                data-testid="career-goal-save"
                disabled={!role || !quarter || submitting}
                onClick={handleSave}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-sm font-semibold hover:bg-accent-primary/18 transition-colors disabled:opacity-40"
              >
                {submitting ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Saving…
                  </>
                ) : (
                  'Save'
                )}
              </button>
              <button
                type="button"
                data-testid="career-goal-cancel"
                onClick={cancelEdit}
                disabled={submitting}
                className="px-4 py-2 rounded-xl border border-contrast/[0.12] text-sm font-semibold text-text-secondary hover:text-text-primary hover:border-contrast/[0.25] transition-colors disabled:opacity-40"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : intent ? (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-sm text-text-primary">
                Targeting{' '}
                <span className="font-semibold">
                  {CAREER_ROLE_LABELS[intent.target_role as CareerRole] ?? intent.target_role}
                </span>{' '}
                by{' '}
                <span className="font-semibold">{quarterLabel(intent.target_quarter)}</span>
                .
              </p>
              <p className="text-[11px] text-text-muted mt-1">
                Your daily digest may include peer-aspirational copy when enough
                others share this goal.
              </p>
              {submitError && (
                <p role="alert" className="text-xs text-danger mt-1">
                  {submitError}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                data-testid="career-goal-edit"
                onClick={openEdit}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-sm font-semibold hover:bg-accent-primary/18 transition-colors"
              >
                Edit
              </button>
              <button
                type="button"
                data-testid="career-goal-clear"
                onClick={handleClear}
                disabled={clearing}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-contrast/[0.12] text-sm font-semibold text-text-secondary hover:text-danger hover:border-danger/40 transition-colors disabled:opacity-40"
              >
                {clearing ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                Clear
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-text-primary">
                Set your career goal
              </p>
              <p className="text-[11px] text-text-muted mt-1">
                Tell us your target role and quarter to get peer-aspirational copy
                in your daily digest.
              </p>
              {loadError && (
                <p className="text-[11px] text-text-muted mt-1">
                  Could not load goal.
                </p>
              )}
            </div>
            <button
              type="button"
              data-testid="career-goal-set"
              onClick={openEdit}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-sm font-semibold hover:bg-accent-primary/18 transition-colors"
            >
              Set my goal →
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
