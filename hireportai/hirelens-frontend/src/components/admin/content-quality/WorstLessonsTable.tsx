import { useNavigate } from 'react-router-dom'
import type { LessonQualityRow } from '@/types'

interface Props {
  lessons: LessonQualityRow[]
}

function fmtPct(value: number | null): string {
  if (value === null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

function fmtScore(value: number | null): string {
  if (value === null) return '—'
  return value.toFixed(2)
}

export function WorstLessonsTable({ lessons }: Props) {
  const navigate = useNavigate()
  if (lessons.length === 0) {
    return (
      <p
        className="text-sm text-text-secondary"
        data-testid="worst-lessons-empty"
      >
        No lesson reviews in the current window.
      </p>
    )
  }
  return (
    <div className="overflow-x-auto" data-testid="worst-lessons-table">
      <table className="w-full text-sm">
        <thead className="text-left text-text-secondary border-b border-contrast/[0.08]">
          <tr>
            <th className="py-2 pr-3 font-medium">Lesson</th>
            <th className="py-2 px-3 font-medium">Deck</th>
            <th className="py-2 px-3 font-medium text-right">Reviews</th>
            <th className="py-2 px-3 font-medium text-right">Views</th>
            <th className="py-2 px-3 font-medium text-right">Pass rate</th>
            <th className="py-2 px-3 font-medium text-right">Smoothed</th>
            <th className="py-2 pl-3 font-medium text-right">Persisted</th>
          </tr>
        </thead>
        <tbody>
          {lessons.map((row) => (
            <tr
              key={row.lesson_id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/admin/lessons/${row.lesson_id}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  navigate(`/admin/lessons/${row.lesson_id}`)
                }
              }}
              className="border-b border-contrast/[0.04] cursor-pointer hover:bg-contrast/[0.04] transition-colors"
              data-testid={`worst-lessons-row-${row.lesson_slug}`}
            >
              <td className="py-2 pr-3 text-text-primary">
                {row.lesson_title}
                {row.low_volume && (
                  <span
                    className="ml-2 text-xs text-text-secondary"
                    data-testid={`low-volume-${row.lesson_slug}`}
                  >
                    (low volume)
                  </span>
                )}
                {row.archived && (
                  <span className="ml-2 text-xs text-text-secondary">
                    (archived)
                  </span>
                )}
              </td>
              <td className="py-2 px-3 text-text-secondary">
                {row.deck_slug}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {row.review_count_window}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {row.view_count_window}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {fmtPct(row.pass_rate)}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {fmtScore(row.smoothed_quality_score)}
              </td>
              <td className="py-2 pl-3 text-right text-text-primary">
                {fmtScore(row.persisted_quality_score)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
