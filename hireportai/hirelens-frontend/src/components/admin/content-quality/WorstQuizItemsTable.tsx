import { useNavigate } from 'react-router-dom'
import type { QuizItemQualityRow } from '@/types'

interface Props {
  items: QuizItemQualityRow[]
}

function fmtPct(value: number | null): string {
  if (value === null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export function WorstQuizItemsTable({ items }: Props) {
  const navigate = useNavigate()
  if (items.length === 0) {
    return (
      <p
        className="text-sm text-text-secondary"
        data-testid="worst-quiz-items-empty"
      >
        No quiz reviews in the current window.
      </p>
    )
  }
  return (
    <div className="overflow-x-auto" data-testid="worst-quiz-items-table">
      <table className="w-full text-sm">
        <thead className="text-left text-text-secondary border-b border-contrast/[0.08]">
          <tr>
            <th className="py-2 pr-3 font-medium">Question</th>
            <th className="py-2 px-3 font-medium text-right">Reviews</th>
            <th className="py-2 px-3 font-medium text-right">Pass rate</th>
            <th className="py-2 pl-3 font-medium text-right">Lapse rate</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr
              key={row.quiz_item_id}
              role="button"
              tabIndex={0}
              onClick={() =>
                navigate(`/admin/lessons/${row.lesson_id}/quiz-items`)
              }
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  navigate(`/admin/lessons/${row.lesson_id}/quiz-items`)
                }
              }}
              className="border-b border-contrast/[0.04] cursor-pointer hover:bg-contrast/[0.04] transition-colors"
              data-testid={`worst-quiz-items-row-${row.quiz_item_id}`}
            >
              <td className="py-2 pr-3 text-text-primary max-w-xl truncate">
                {row.question_preview}
                {row.low_volume && (
                  <span className="ml-2 text-xs text-text-secondary">
                    (low volume)
                  </span>
                )}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {row.review_count_window}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {fmtPct(row.pass_rate)}
              </td>
              <td className="py-2 pl-3 text-right text-text-primary">
                {fmtPct(row.lapse_rate)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
