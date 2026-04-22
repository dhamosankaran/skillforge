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

/**
 * Pick the empty-state copy from the actual gap (B-017).
 *
 * The pre-B-017 copy was a single string that told the user to "set the
 * company in the Countdown widget" — but Countdown only captures date, and
 * `interview_target_company` is only capturable from PersonaPicker. The
 * three branches below match the two partial-set cases to the surface that
 * can actually satisfy them (or, for the company gap, state the fact
 * plainly — there is no self-service company editor until E-017 lands).
 */
function emptyCopy(
  company: string | null | undefined,
  date: string | null | undefined,
): string {
  if (!company && !date) return 'No interview target set yet.'
  if (!company) return 'No interview company set yet.'
  return 'Set your interview date in the Countdown widget below.'
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
      emptyMessage={emptyCopy(company, date)}
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
