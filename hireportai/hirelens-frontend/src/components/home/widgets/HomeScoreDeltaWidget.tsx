import { Link } from 'react-router-dom'
import { DashboardWidget } from '@/components/home/DashboardWidget'
import { useScoreHistory } from '@/hooks/useScoreHistory'
import type { Persona } from '@/context/AuthContext'

interface HomeScoreDeltaWidgetProps {
  persona: Persona
  /**
   * Spec #63 §8.2 — `next_interview.tracker_id` from
   * `homeState.context.next_interview`. Null when no upcoming interview
   * is set; widget self-suppresses (no render).
   */
  trackerId: string | null
  /**
   * Spec #63 §8.2 — display label routed in from CountdownWidget's
   * source so the home variant says "Stripe" rather than re-deriving.
   */
  company?: string | null
}

/**
 * Spec #63 (E-043) §8.2 — `interview_prepper`-only home variant. Mounts
 * directly below `<CountdownWidget>` for the same `tracker_id` (D-5
 * suppression rule — both widgets surface the same tracker row).
 *
 * Render gate: `trackerId != null && history.length >= 2`. Cold-start
 * (single history row) hides the widget entirely (no empty state on the
 * home dashboard — minimalism per spec #61).
 */
export function HomeScoreDeltaWidget({
  persona,
  trackerId,
  company,
}: HomeScoreDeltaWidgetProps) {
  const { data, isLoading } = useScoreHistory(trackerId ?? null)

  if (trackerId == null) return null
  if (isLoading) return null

  const history = data?.history ?? []
  const delta = data?.delta ?? null
  if (history.length < 2 || !delta) return null

  const latest = history[history.length - 1]
  const previous = history[history.length - 2]
  const tone =
    delta.overall_delta > 0
      ? 'text-success'
      : delta.overall_delta < 0
        ? 'text-danger'
        : 'text-text-muted'
  const sign = delta.overall_delta > 0 ? '+' : ''
  const label = company ? company : 'this application'

  return (
    <DashboardWidget
      title="Score improvement"
      testid="home-score-delta"
      persona={persona}
      state="data"
      action={{
        label: 'View detail',
        href: `/prep/tracker?focus=${encodeURIComponent(trackerId)}`,
      }}
    >
      <div className="flex flex-col gap-2">
        <p className="text-sm text-text-secondary">
          You've moved on {label}.
        </p>
        <div className="flex items-baseline gap-3">
          <span className="text-sm text-text-secondary">
            {previous.overall_score}
          </span>
          <span className="text-text-muted text-xs">→</span>
          <span className="text-2xl font-display font-bold text-text-primary">
            {latest.overall_score}
          </span>
          <span className={`text-sm font-medium ${tone}`}>
            {sign}
            {delta.overall_delta} pts
          </span>
        </div>
        <Link
          to={`/prep/tracker?focus=${encodeURIComponent(trackerId)}`}
          className="sr-only"
        >
          View score history
        </Link>
      </div>
    </DashboardWidget>
  )
}
