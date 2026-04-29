import { Link } from 'react-router-dom'
import { History } from 'lucide-react'
import type { RecentReview, ReviewHistorySection } from '@/types'

interface ReviewHistoryProps {
  data: ReviewHistorySection | undefined
  coldStart: boolean
}

// Spec #09 §12 D-13 — per-section cold-start copy.
const COLD_START_COPY = "Your recent reviews will show up here."

const RATING_LABEL: Record<number, string> = {
  1: 'Again',
  2: 'Hard',
  3: 'Good',
  4: 'Easy',
}

export function ReviewHistory({ data, coldStart }: ReviewHistoryProps) {
  if (!data || coldStart || data.recent_reviews.length === 0) {
    return (
      <section
        data-testid="dashboard-review-history"
        className="rounded-lg border border-border-subtle bg-bg-surface p-6"
      >
        <div className="flex items-center gap-3">
          <History size={22} className="text-text-muted" aria-hidden />
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Recent reviews
          </h2>
        </div>
        <p data-testid="dashboard-review-history-empty" className="mt-3 text-sm text-text-muted">
          {COLD_START_COPY}
        </p>
      </section>
    )
  }

  return (
    <section
      data-testid="dashboard-review-history"
      className="rounded-lg border border-border-subtle bg-bg-surface p-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History size={22} className="text-text-accent" aria-hidden />
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Recent reviews
          </h2>
        </div>
        <span className="text-xs text-text-muted">
          {data.total_in_window} in last {data.window_days}d
        </span>
      </div>
      <ul className="mt-4 divide-y divide-border-subtle">
        {data.recent_reviews.map((row) => (
          <ReviewRow key={`${row.quiz_item_id}-${row.reviewed_at}`} row={row} />
        ))}
      </ul>
    </section>
  )
}

function ReviewRow({ row }: { row: RecentReview }) {
  return (
    <li data-testid={`dashboard-review-row-${row.quiz_item_id}`} className="py-3">
      <Link
        to={`/learn/lesson/${row.lesson_id}`}
        className="block hover:bg-bg-base"
      >
        <div className="flex items-center justify-between gap-3 text-sm">
          <span className="truncate font-medium text-text-primary">
            {row.lesson_title}
          </span>
          <span className="shrink-0 text-xs text-text-muted">
            {RATING_LABEL[row.rating] ?? `Rating ${row.rating}`}
          </span>
        </div>
        <div className="mt-1 flex items-center justify-between text-xs text-text-muted">
          <span>{row.deck_slug}</span>
          <span>{new Date(row.reviewed_at).toLocaleString()}</span>
        </div>
      </Link>
    </li>
  )
}
