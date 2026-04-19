/**
 * Interview-Prepper onboarding checklist (Spec #41).
 *
 * Renders a 5-step guided sequence (scan → review gaps → pick category
 * → set mission → first review) on `/home` for `interview_prepper`
 * users. Visibility and skip state are owned entirely by this
 * component:
 *   - null when persona is not interview_prepper
 *   - null when localStorage.interview_prepper_checklist_skipped === 'true'
 *   - null when all 5 complete AND 7 days have elapsed since completion
 *   - shows celebration copy when freshly complete
 *
 * HomeDashboard renders this above the persona grid; no branching on
 * persona lives there.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Circle, ChevronRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useOnboardingChecklist } from '@/hooks/useOnboardingChecklist'
import { capture } from '@/utils/posthog'
import type { ChecklistStep } from '@/services/api'

const SKIP_STORAGE_KEY = 'interview_prepper_checklist_skipped'
const AUTO_HIDE_DAYS = 7

function isSkipped(): boolean {
  try {
    return localStorage.getItem(SKIP_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function isPastAutoHideWindow(completedAt: string | null): boolean {
  if (!completedAt) return false
  const completed = new Date(completedAt).getTime()
  if (Number.isNaN(completed)) return false
  const elapsedMs = Date.now() - completed
  return elapsedMs > AUTO_HIDE_DAYS * 24 * 60 * 60 * 1000
}

export function InterviewPrepperChecklist() {
  const { user } = useAuth()
  const { data } = useOnboardingChecklist()
  const navigate = useNavigate()
  const [skipped, setSkipped] = useState<boolean>(() => isSkipped())
  const shownRef = useRef<boolean>(false)
  const completedFiredRef = useRef<boolean>(false)

  const completeCount = data?.steps.filter((s) => s.complete).length ?? 0
  const allComplete = data?.all_complete ?? false
  const pastWindow = isPastAutoHideWindow(data?.completed_at ?? null)
  const shouldRender =
    user?.persona === 'interview_prepper' &&
    !skipped &&
    data !== null &&
    !(allComplete && pastWindow)

  // Fire `checklist_shown` once per mount with data.
  useEffect(() => {
    if (!shouldRender) return
    if (shownRef.current) return
    shownRef.current = true
    capture('checklist_shown', {
      complete_count: completeCount,
      all_complete: allComplete,
    })
  }, [shouldRender, completeCount, allComplete])

  // Fire `checklist_completed` when all_complete flips to true.
  useEffect(() => {
    if (!allComplete || !data) return
    if (completedFiredRef.current) return
    completedFiredRef.current = true
    capture('checklist_completed', { completed_at: data.completed_at })
  }, [allComplete, data])

  if (!shouldRender || !data) return null

  function handleStepClick(step: ChecklistStep) {
    capture('checklist_step_clicked', { step_id: step.id })
    navigate(step.link_target)
  }

  function handleSkip() {
    capture('checklist_skipped', { complete_count: completeCount })
    try {
      localStorage.setItem(SKIP_STORAGE_KEY, 'true')
    } catch {
      /* ignore storage errors */
    }
    setSkipped(true)
  }

  const title = allComplete ? "🎉 You're all set." : 'Get started'
  const subtitle = allComplete
    ? 'Every step done. This card will fade out soon.'
    : `${completeCount} of ${data.steps.length} done`

  const progressPct = Math.round((completeCount / data.steps.length) * 100)

  return (
    <section
      data-testid="interview-prepper-checklist"
      className="mb-6 rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5"
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="font-display text-lg font-semibold text-text-primary">
            {title}
          </h2>
          <p className="text-[11px] text-text-muted mt-1">{subtitle}</p>
        </div>
        <button
          onClick={handleSkip}
          className="text-[11px] text-text-muted hover:text-text-secondary transition-colors"
        >
          {allComplete ? 'Dismiss' : 'Skip checklist'}
        </button>
      </div>

      <div
        data-testid="checklist-progress-bar"
        className="h-1.5 w-full rounded-full bg-contrast/[0.06] mb-4 overflow-hidden"
      >
        <div
          className="h-full bg-accent-primary/60 transition-all duration-300"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <ul className="space-y-2">
        {data.steps.map((step) => (
          <li key={step.id}>
            <button
              onClick={() => handleStepClick(step)}
              data-testid={`checklist-step-${step.id}`}
              className="w-full flex items-center gap-3 p-3 rounded-xl border border-contrast/[0.06] bg-bg-base/40 hover:border-accent-primary/25 hover:bg-bg-base/80 transition-colors text-left"
            >
              {step.complete ? (
                <CheckCircle2
                  size={18}
                  className="text-accent-primary shrink-0"
                  aria-label="complete"
                />
              ) : (
                <Circle
                  size={18}
                  className="text-text-muted shrink-0"
                  aria-label="incomplete"
                />
              )}
              <div className="flex-1 min-w-0">
                <p
                  className={
                    'text-sm font-semibold text-text-primary ' +
                    (step.complete ? 'line-through opacity-60' : '')
                  }
                >
                  {step.title}
                </p>
                <p className="text-[11px] text-text-muted mt-0.5">
                  {step.description}
                </p>
              </div>
              <ChevronRight size={14} className="text-text-muted shrink-0" />
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
