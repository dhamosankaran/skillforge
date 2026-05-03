import { useEffect, useRef } from 'react'
import { CheckCircle2, Circle, BookOpen, RotateCcw, Calendar } from 'lucide-react'
import { capture } from '@/utils/posthog'

export type LoopFrameSurface = 'results'

export type LoopFrameStep = 1 | 2 | 3 | 4

export interface LoopFrameProps {
  surface: LoopFrameSurface
  currentStep: LoopFrameStep
  score?: number
  gapCount?: number
  interviewDate?: string | null
  plan: 'anonymous' | 'free' | 'pro'
}

interface StepDef {
  index: LoopFrameStep
  label: string
  icon: typeof BookOpen
}

const STEPS: StepDef[] = [
  { index: 1, label: 'Scanned', icon: CheckCircle2 },
  { index: 2, label: 'Studying', icon: BookOpen },
  { index: 3, label: 'Re-scan', icon: RotateCcw },
  { index: 4, label: 'Interview', icon: Calendar },
]

function daysUntil(dateIso: string | null | undefined): number | null {
  if (!dateIso) return null
  const target = new Date(dateIso)
  if (Number.isNaN(target.getTime())) return null
  const today = new Date()
  const ms = target.getTime() - today.getTime()
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)))
}

function subLineFor(
  step: LoopFrameStep,
  score: number | undefined,
  gapCount: number | undefined,
  countdown: number | null,
): string | null {
  switch (step) {
    case 1:
      return typeof score === 'number' ? `${score}%` : null
    case 2:
      return typeof gapCount === 'number' ? `${gapCount} gaps` : null
    case 3:
      return null
    case 4:
      return countdown === null ? 'Set a date' : `in ${countdown}d`
  }
}

export function LoopFrame({
  surface,
  currentStep,
  score,
  gapCount,
  interviewDate,
  plan,
}: LoopFrameProps) {
  const firedRef = useRef(false)
  const countdown = daysUntil(interviewDate)

  useEffect(() => {
    if (firedRef.current) return
    firedRef.current = true
    capture('loop_frame_rendered', {
      surface,
      current_step: currentStep,
      has_interview_date: interviewDate != null,
      plan,
    })
  }, [surface, currentStep, interviewDate, plan])

  return (
    <div
      id="loop-frame"
      data-testid="loop-frame"
      role="group"
      aria-label="Your scan in the closed loop"
      className="w-full mb-6 p-4 rounded-lg border border-border bg-bg-surface"
    >
      <div className="flex flex-col md:flex-row md:items-center md:gap-2">
        {STEPS.map((step, idx) => {
          const isCurrent = step.index === currentStep
          const isDone = step.index < currentStep
          const StepIcon = isDone ? CheckCircle2 : isCurrent ? step.icon : Circle
          const sub = subLineFor(step.index, score, gapCount, countdown)

          const stateClass = isCurrent
            ? 'border-border-accent bg-accent-primary/10 text-text-primary'
            : isDone
              ? 'border-border bg-bg-elevated text-text-secondary'
              : 'border-border bg-bg-elevated text-text-muted'

          const iconClass = isCurrent
            ? 'text-accent-primary'
            : isDone
              ? 'text-success'
              : 'text-text-muted'

          return (
            <div key={step.index} className="flex flex-col md:flex-row md:items-center md:flex-1">
              <div
                data-testid={`loop-step-${step.index}`}
                data-current={isCurrent ? 'true' : 'false'}
                className={`flex items-center gap-2 px-3 py-2 rounded-md border ${stateClass} md:flex-1`}
              >
                <StepIcon size={16} className={`shrink-0 ${iconClass}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium leading-tight">{step.label}</p>
                  {sub && (
                    <p className="text-xs text-text-muted leading-tight mt-0.5 truncate">{sub}</p>
                  )}
                </div>
              </div>

              {idx < STEPS.length - 1 && (
                <div
                  aria-hidden="true"
                  className="ml-4 my-1 h-3 w-px border-l border-border md:ml-0 md:my-0 md:h-px md:w-6 md:border-l-0 md:border-t md:border-border"
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default LoopFrame
