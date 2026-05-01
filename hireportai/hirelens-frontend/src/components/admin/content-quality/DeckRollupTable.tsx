import { useNavigate } from 'react-router-dom'
import type { DeckQualityRow } from '@/types'

interface Props {
  decks: DeckQualityRow[]
}

function fmtPct(value: number | null): string {
  if (value === null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

function fmtScore(value: number | null): string {
  if (value === null) return '—'
  return value.toFixed(2)
}

export function DeckRollupTable({ decks }: Props) {
  const navigate = useNavigate()
  if (decks.length === 0) {
    return (
      <p
        className="text-sm text-text-secondary"
        data-testid="deck-rollup-empty"
      >
        No decks visible in the current window.
      </p>
    )
  }
  return (
    <div className="overflow-x-auto" data-testid="deck-rollup-table">
      <table className="w-full text-sm">
        <thead className="text-left text-text-secondary border-b border-contrast/[0.08]">
          <tr>
            <th className="py-2 pr-3 font-medium">Deck</th>
            <th className="py-2 px-3 font-medium">Tier</th>
            <th className="py-2 px-3 font-medium">Persona</th>
            <th className="py-2 px-3 font-medium text-right">Lessons</th>
            <th className="py-2 px-3 font-medium text-right">Reviews</th>
            <th className="py-2 px-3 font-medium text-right">Pass rate</th>
            <th className="py-2 pl-3 font-medium text-right">Quality</th>
          </tr>
        </thead>
        <tbody>
          {decks.map((row) => (
            <tr
              key={row.deck_id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/admin/decks/${row.deck_id}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  navigate(`/admin/decks/${row.deck_id}`)
                }
              }}
              className="border-b border-contrast/[0.04] cursor-pointer hover:bg-contrast/[0.04] transition-colors"
              data-testid={`deck-rollup-row-${row.deck_slug}`}
            >
              <td className="py-2 pr-3 text-text-primary">
                {row.deck_title}
                {row.archived && (
                  <span className="ml-2 text-xs text-text-secondary">
                    (archived)
                  </span>
                )}
              </td>
              <td className="py-2 px-3 text-text-secondary capitalize">
                {row.tier}
              </td>
              <td className="py-2 px-3 text-text-secondary">
                {row.persona_visibility}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {row.lesson_count}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {row.review_count_window}
              </td>
              <td className="py-2 px-3 text-right text-text-primary">
                {fmtPct(row.weighted_pass_rate)}
              </td>
              <td className="py-2 pl-3 text-right text-text-primary">
                {fmtScore(row.avg_quality_score)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
