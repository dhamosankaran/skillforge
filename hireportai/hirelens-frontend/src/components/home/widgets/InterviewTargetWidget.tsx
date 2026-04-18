import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import type { Persona } from '@/context/AuthContext'

interface InterviewTargetWidgetProps {
  persona: Persona
  company: string | null | undefined
  date: string | null | undefined
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function InterviewTargetWidget({
  persona,
  company,
  date,
}: InterviewTargetWidgetProps) {
  const hasBoth = Boolean(company && date)
  const state: WidgetState = hasBoth ? 'data' : 'empty'

  return (
    <DashboardWidget
      title="Interview Target"
      testid="interview-target"
      persona={persona}
      state={state}
      emptyMessage="Set your interview company in the Countdown widget below."
    >
      {hasBoth && (
        <div className="flex flex-col gap-1">
          <div className="font-display text-base font-semibold text-text-primary">
            {company}
          </div>
          <div className="text-sm text-text-secondary">{formatDate(date!)}</div>
        </div>
      )}
    </DashboardWidget>
  )
}
