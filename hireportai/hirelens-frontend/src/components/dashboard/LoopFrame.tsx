import { useEffect, useRef } from 'react'
import {
  CheckCircle2,
  Circle,
  BookOpen,
  RotateCcw,
  Calendar,
  AlertTriangle,
  Lock,
} from 'lucide-react'
import { capture } from '@/utils/posthog'

export type LoopFrameSurface = 'results' | 'appshell'

export type LoopFrameStep = 1 | 2 | 3 | 4

export type LoopFrameStepState = 'future' | 'current' | 'done' | 'locked' | 'alert'

export interface LoopFrameProps {
  surface: LoopFrameSurface
  currentStep: LoopFrameStep
  score?: number
  gapCount?: number
  interviewDate?: string | null
  plan: 'anonymous' | 'free' | 'pro'
  /**
   * Spec #66 §4.1 / D-11. When provided, OVERRIDES the linear
   * `currentStep`-based per-step state derivation. When omitted, the
   * pre-spec-#66 linear behavior is preserved (Results.tsx call site
   * unaffected). Per-step values: 'future' / 'current' / 'done' /
   * 'locked' / 'alert'.
   */
  stepStates?: Partial<Record<LoopFrameStep, LoopFrameStepState>>
  /**
   * Spec #66 §4.1. When provided, the rendered step becomes a
   * `<button>` instead of a `<div>`; only steps whose state is
   * `'current'` are clickable (gate is internal).
   */
  onStepClick?: (step: LoopFrameStep) => void
  /**
   * Spec #66 §4.1 / D-11. Tighter padding + hidden sublines for the
   * AppShell strip's vertical budget. Default false. Layout-driven —
   * separate from `surface`, which is a pure analytics marker.
   */
  compact?: boolean
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

function deriveStateFromCurrentStep(
  index: LoopFrameStep,
  currentStep: LoopFrameStep,
): LoopFrameStepState {
  if (index < currentStep) return 'done'
  if (index === currentStep) return 'current'
  return 'future'
}

function iconForState(
  state: LoopFrameStepState,
  fallbackIcon: typeof BookOpen,
): typeof BookOpen {
  switch (state) {
    case 'done':
      return CheckCircle2
    case 'current':
      return fallbackIcon
    case 'alert':
      return AlertTriangle
    case 'locked':
      return Lock
    case 'future':
    default:
      return Circle
  }
}

function classForState(state: LoopFrameStepState): {
  container: string
  icon: string
} {
  switch (state) {
    case 'current':
      return {
        container:
          'border-border-accent bg-accent-primary/10 text-text-primary',
        icon: 'text-accent-primary',
      }
    case 'done':
      return {
        container: 'border-border bg-bg-elevated text-text-secondary',
        icon: 'text-success',
      }
    case 'alert':
      return {
        container: 'border-danger bg-danger/10 text-text-primary',
        icon: 'text-danger',
      }
    case 'locked':
      return {
        container: 'border-border bg-bg-elevated text-text-muted',
        icon: 'text-text-muted',
      }
    case 'future':
    default:
      return {
        container: 'border-border bg-bg-elevated text-text-muted',
        icon: 'text-text-muted',
      }
  }
}

export function LoopFrame({
  surface,
  currentStep,
  score,
  gapCount,
  interviewDate,
  plan,
  stepStates,
  onStepClick,
  compact = false,
}: LoopFrameProps) {
  const firedRef = useRef(false)
  const countdown = daysUntil(interviewDate)

  useEffect(() => {
    // §9.2 / D-4: AppShell mount fires its own `loop_strip_rendered`;
    // suppress LoopFrame's analytics fire there to avoid double-counting.
    if (surface === 'appshell') return
    if (firedRef.current) return
    firedRef.current = true
    capture('loop_frame_rendered', {
      surface,
      current_step: currentStep,
      has_interview_date: interviewDate != null,
      plan,
    })
  }, [surface, currentStep, interviewDate, plan])

  const containerCls = compact
    ? 'w-full p-2 rounded-md border border-border bg-bg-surface'
    : 'w-full mb-6 p-4 rounded-lg border border-border bg-bg-surface'

  return (
    <div
      id="loop-frame"
      data-testid="loop-frame"
      role="group"
      aria-label="Your scan in the closed loop"
      className={containerCls}
    >
      <div className="flex flex-col md:flex-row md:items-center md:gap-2">
        {STEPS.map((step, idx) => {
          const state =
            stepStates?.[step.index] ??
            deriveStateFromCurrentStep(step.index, currentStep)
          const StepIcon = iconForState(state, step.icon)
          const sub = compact
            ? null
            : subLineFor(step.index, score, gapCount, countdown)
          const { container: stateClass, icon: iconClass } = classForState(state)
          const clickable = onStepClick != null && state === 'current'
          const stepInner = (
            <>
              <StepIcon size={16} className={`shrink-0 ${iconClass}`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium leading-tight">{step.label}</p>
                {sub && (
                  <p className="text-xs text-text-muted leading-tight mt-0.5 truncate">
                    {sub}
                  </p>
                )}
              </div>
            </>
          )

          return (
            <div
              key={step.index}
              className="flex flex-col md:flex-row md:items-center md:flex-1"
            >
              {clickable ? (
                <button
                  type="button"
                  data-testid={`loop-step-${step.index}`}
                  data-current={state === 'current' ? 'true' : 'false'}
                  data-state={state}
                  onClick={() => onStepClick?.(step.index)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md border ${stateClass} md:flex-1 cursor-pointer hover:bg-accent-primary/15 transition-colors`}
                >
                  {stepInner}
                </button>
              ) : (
                <div
                  data-testid={`loop-step-${step.index}`}
                  data-current={state === 'current' ? 'true' : 'false'}
                  data-state={state}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md border ${stateClass} md:flex-1`}
                >
                  {stepInner}
                </div>
              )}

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
