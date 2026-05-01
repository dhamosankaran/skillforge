import { useScoreHistory } from '@/hooks/useScoreHistory'
import type { ScoreDelta } from '@/types'

interface ScoreDeltaWidgetProps {
  trackerApplicationId: string
}

/**
 * Spec #63 (E-043) §8.1 — score delta visualization for the tracker
 * focused-row inline-expand block (D-4 mount). Three states by history
 * length:
 *   - 0 rows: empty CTA ("Re-scan to see how you've improved").
 *   - 1 row: first-scan baseline copy.
 *   - 2+ rows: per-axis delta rendered from BE-pre-computed values
 *     (D-6 — FE never re-does the math).
 *
 * Re-scan trigger UX is intentionally not in this widget — the spec
 * describes the data display surface; the trigger is wired by the
 * parent (Tracker.tsx) when resume_text is available.
 */
export function ScoreDeltaWidget({
  trackerApplicationId,
}: ScoreDeltaWidgetProps) {
  const { data, isLoading, error } = useScoreHistory(trackerApplicationId)

  if (isLoading) {
    return (
      <div
        data-testid="score-delta-widget-loading"
        className="text-sm text-text-muted"
      >
        Loading score history…
      </div>
    )
  }

  if (error) {
    return (
      <div
        data-testid="score-delta-widget-error"
        className="text-sm text-text-muted"
      >
        Couldn't load score history.
      </div>
    )
  }

  const history = data?.history ?? []
  const delta = data?.delta ?? null

  if (history.length === 0) {
    return (
      <div
        data-testid="score-delta-widget-empty"
        className="rounded-lg border border-contrast/[0.06] bg-bg-elevated p-4"
      >
        <p className="text-sm text-text-secondary">
          Re-scan this application to see how your resume has improved.
        </p>
      </div>
    )
  }

  if (history.length === 1 || !delta) {
    const row = history[0]
    return (
      <div
        data-testid="score-delta-widget-baseline"
        className="rounded-lg border border-contrast/[0.06] bg-bg-elevated p-4"
      >
        <p className="text-[11px] uppercase tracking-widest text-text-muted font-semibold mb-1">
          First scan baseline
        </p>
        <p className="text-2xl font-display font-bold text-text-primary">
          {row.overall_score}
        </p>
        <p className="text-xs text-text-muted mt-1">
          Re-scan after improving your resume to see the delta.
        </p>
      </div>
    )
  }

  const latest = history[history.length - 1]
  const previous = history[history.length - 2]

  return (
    <div
      data-testid="score-delta-widget"
      className="rounded-lg border border-contrast/[0.06] bg-bg-elevated p-4"
    >
      <div className="flex items-baseline gap-3 mb-4">
        <span className="text-[11px] uppercase tracking-widest text-text-muted font-semibold">
          ATS score
        </span>
        <span className="text-sm text-text-secondary">
          {previous.overall_score}
        </span>
        <span className="text-text-muted text-xs">→</span>
        <span className="text-2xl font-display font-bold text-text-primary">
          {latest.overall_score}
        </span>
        <DeltaBadge value={delta.overall_delta} unit="points" />
      </div>
      <ul className="space-y-1.5 text-sm">
        <DeltaRow label="Keyword match" value={delta.keyword_match_delta} />
        <DeltaRow label="Skills coverage" value={delta.skills_coverage_delta} />
        <DeltaRow
          label="Formatting"
          value={delta.formatting_compliance_delta}
        />
        <DeltaRow label="Bullets" value={delta.bullet_strength_delta} />
      </ul>
      {delta.days_between > 0 && (
        <p className="mt-3 text-xs text-text-muted">
          Compared over {delta.days_between} day
          {delta.days_between === 1 ? '' : 's'}.
        </p>
      )}
    </div>
  )
}

function DeltaBadge({ value, unit }: { value: number; unit: string }) {
  const tone =
    value > 0
      ? 'text-success'
      : value < 0
        ? 'text-danger'
        : 'text-text-muted'
  const sign = value > 0 ? '+' : ''
  return (
    <span
      data-testid="score-delta-overall-badge"
      className={`text-sm font-medium ${tone}`}
    >
      {sign}
      {value} {unit}
    </span>
  )
}

interface DeltaRowProps {
  label: string
  value: number
}

function DeltaRow({ label, value }: DeltaRowProps) {
  const rounded = Math.round(value * 100) / 100
  const tone =
    rounded > 0
      ? 'text-success'
      : rounded < 0
        ? 'text-danger'
        : 'text-text-muted'
  const sign = rounded > 0 ? '+' : ''
  return (
    <li className="flex items-center justify-between">
      <span className="text-text-secondary">{label}</span>
      <span className={`font-medium ${tone}`}>
        {sign}
        {rounded.toFixed(2)}
      </span>
    </li>
  )
}
