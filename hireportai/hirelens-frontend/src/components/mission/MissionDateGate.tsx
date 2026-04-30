/**
 * MissionDateGate — no-date interview_prepper affordance on `/learn/mission`.
 *
 * Spec #53 §7.3 (CTA target amended by spec #57 AC-6). Rendered by
 * `MissionMode.tsx` when:
 *   - user.persona === 'interview_prepper'
 *   - homeState.context.next_interview === null
 *   - phase === 'setup' (no active mission — existing predicate)
 *
 * Replaces `MissionSetup` in that specific branch. All other phases
 * (loading, setup for date-present or non-interview_prepper, active,
 * studying, dayDone, completed, error) are unchanged.
 */
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { capture } from '@/utils/posthog'

export function MissionDateGate() {
  const navigate = useNavigate()
  const shownRef = useRef(false)

  useEffect(() => {
    if (shownRef.current) return
    shownRef.current = true
    capture('countdown_unlock_cta_shown', { surface: 'mission_mode' })
  }, [])

  function handleAddDate() {
    // Spec #53 §7.3 preserved-event (still fires from MissionDateGate).
    capture('countdown_unlock_cta_clicked', { surface: 'mission_mode' })
    // Spec #57 §7.1 — new event with `source: 'mission_gate'`.
    capture('countdown_widget_add_date_cta_clicked', { source: 'mission_gate' })
    // Spec #57 AC-6 — CTA now routes to the tracker new-row flow rather
    // than PersonaPicker. The tracker is the canonical date-capture
    // surface post-spec-57.
    navigate('/prep/tracker?new=1')
  }

  function handleBrowse() {
    navigate('/learn')
  }

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div
        data-testid="mission-date-gate"
        className="max-w-md mx-auto px-4 py-24 sm:px-6 flex flex-col items-center gap-5 text-center"
      >
        <h2 className="font-display text-xl font-semibold text-text-primary">
          Set a date to start a sprint
        </h2>
        <p className="text-sm text-text-secondary leading-relaxed">
          Mission Mode runs a time-bound study sprint up to an interview date.
          Add yours to start one — or keep prepping broadly from the
          category library.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <button
            type="button"
            data-testid="mission-date-gate-add-date"
            onClick={handleAddDate}
            className="px-5 py-2.5 rounded-md bg-accent-primary text-white text-sm font-medium hover:bg-accent-primary/90 transition-colors"
          >
            Add interview date
          </button>
          <button
            type="button"
            data-testid="mission-date-gate-browse"
            onClick={handleBrowse}
            className="px-5 py-2.5 rounded-md border border-border text-text-secondary text-sm font-medium hover:border-border-accent hover:text-text-primary transition-colors"
          >
            Browse categories instead
          </button>
        </div>
      </div>
    </PageWrapper>
  )
}
