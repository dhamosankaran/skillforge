import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Info } from 'lucide-react'
import clsx from 'clsx'
import { AnimatedCard } from '@/components/ui/AnimatedCard'
import { useClickOutside } from '@/hooks/useClickOutside'
import { capture } from '@/utils/posthog'

export type ResultsSectionId =
  | 'ats_score'
  | 'score_breakdown'
  | 'job_fit'
  | 'keywords'
  | 'skills_radar'
  | 'bullets'
  | 'missing_skills'
  | 'formatting'
  | 'improvements'

export interface TooltipCopy {
  what: string
  how: string
  why: string
}

interface PanelSectionProps {
  title: string
  icon: React.ElementType
  children: React.ReactNode
  className?: string
  tooltip?: TooltipCopy
  section?: ResultsSectionId
}

export function PanelSection({
  title,
  icon: Icon,
  children,
  className,
  tooltip,
  section,
}: PanelSectionProps) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const tooltipRef = useRef<HTMLDivElement | null>(null)
  const tooltipId = useId()

  const close = useCallback(() => setOpen(false), [])

  useClickOutside([triggerRef, tooltipRef], open, close)

  useEffect(() => {
    if (!open) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  const onToggle = () => {
    setOpen((prev) => {
      const next = !prev
      if (next && section) {
        capture('results_tooltip_opened', { section })
      }
      return next
    })
  }

  return (
    <AnimatedCard className={clsx('p-5', className)}>
      <div className="flex items-center gap-2 mb-4">
        <Icon size={14} className="text-accent-primary flex-shrink-0" />
        <h2 className="font-display font-semibold text-sm text-text-primary">{title}</h2>
        {tooltip && (
          <div className="relative">
            <button
              ref={triggerRef}
              type="button"
              onClick={onToggle}
              className="p-1 -m-1 text-text-muted hover:text-text-secondary transition-colors"
              aria-label={`Info: ${title}`}
              aria-expanded={open}
              aria-describedby={open ? tooltipId : undefined}
            >
              <Info size={12} />
            </button>
            {open && (
              <div
                ref={tooltipRef}
                id={tooltipId}
                role="tooltip"
                className="absolute left-1/2 -translate-x-1/2 top-6 z-50 w-64 p-2.5 rounded-lg bg-bg-overlay border border-contrast/10 shadow-lg text-xs text-text-secondary leading-relaxed space-y-1.5"
              >
                <p>
                  <span className="font-semibold text-text-primary">What this means: </span>
                  {tooltip.what}
                </p>
                <p>
                  <span className="font-semibold text-text-primary">How to act: </span>
                  {tooltip.how}
                </p>
                <p>
                  <span className="font-semibold text-text-primary">Why it matters: </span>
                  {tooltip.why}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
      {children}
    </AnimatedCard>
  )
}
