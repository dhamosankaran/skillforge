import { Link } from 'react-router-dom'
import { Clock } from 'lucide-react'
import type { CardsDueSection } from '@/types'

interface DueTodayProps {
  data: CardsDueSection | undefined
  coldStart: boolean
}

// Spec #09 §12 D-13 — per-section cold-start copy.
const COLD_START_COPY = "Nothing due — start a session to see your queue here."

export function DueToday({ data, coldStart }: DueTodayProps) {
  if (!data || coldStart) {
    return (
      <section
        data-testid="dashboard-cards-due"
        className="rounded-lg border border-border-subtle bg-bg-surface p-6"
      >
        <div className="flex items-center gap-3">
          <Clock size={22} className="text-text-muted" aria-hidden />
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Due today
          </h2>
        </div>
        <p data-testid="dashboard-cards-due-empty" className="mt-3 text-sm text-text-muted">
          {COLD_START_COPY}
        </p>
        <Link
          to="/learn/daily"
          className="mt-4 inline-block text-sm font-medium text-text-accent hover:underline"
        >
          Start daily review →
        </Link>
      </section>
    )
  }

  return (
    <section
      data-testid="dashboard-cards-due"
      className="rounded-lg border border-border-subtle bg-bg-surface p-6"
    >
      <div className="flex items-center gap-3">
        <Clock size={22} className="text-text-accent" aria-hidden />
        <h2 className="font-display text-lg font-semibold text-text-primary">
          Due today
        </h2>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Today" value={data.due_today} testid="dashboard-cards-due-today" />
        <Stat label="Next 7 days" value={data.due_next_7_days} testid="dashboard-cards-due-7d" />
        <Stat label="In progress" value={data.total_quiz_items_in_progress} testid="dashboard-cards-in-progress" />
        <Stat
          label="Mastered (review)"
          value={data.due_breakdown_by_state.review}
          testid="dashboard-cards-state-review"
        />
      </div>
      {data.due_today > 0 && (
        <Link
          to="/learn/daily"
          className="mt-4 inline-block text-sm font-medium text-text-accent hover:underline"
        >
          Start daily review →
        </Link>
      )}
    </section>
  )
}

function Stat({ label, value, testid }: { label: string; value: number; testid: string }) {
  return (
    <div data-testid={testid}>
      <div className="text-2xl font-semibold text-text-primary">{value}</div>
      <div className="text-xs uppercase tracking-wide text-text-muted">{label}</div>
    </div>
  )
}
