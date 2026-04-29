import { BarChart3 } from 'lucide-react'
import type { DeckMasterySection } from '@/types'

interface DeckMasteryProps {
  data: DeckMasterySection | undefined
  coldStart: boolean
}

// Spec #09 §12 D-13 — per-section cold-start copy.
const COLD_START_COPY = "No mastery data yet — review quiz items to unlock per-deck mastery."

export function DeckMastery({ data, coldStart }: DeckMasteryProps) {
  if (!data || coldStart || data.decks.length === 0) {
    return (
      <section
        data-testid="dashboard-deck-mastery"
        className="rounded-lg border border-border-subtle bg-bg-surface p-6"
      >
        <div className="flex items-center gap-3">
          <BarChart3 size={22} className="text-text-muted" aria-hidden />
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Deck mastery
          </h2>
        </div>
        <p data-testid="dashboard-deck-mastery-empty" className="mt-3 text-sm text-text-muted">
          {COLD_START_COPY}
        </p>
      </section>
    )
  }

  return (
    <section
      data-testid="dashboard-deck-mastery"
      className="rounded-lg border border-border-subtle bg-bg-surface p-6"
    >
      <div className="flex items-center gap-3">
        <BarChart3 size={22} className="text-text-accent" aria-hidden />
        <h2 className="font-display text-lg font-semibold text-text-primary">
          Deck mastery
        </h2>
      </div>
      <ul className="mt-4 space-y-3">
        {data.decks.map((deck) => (
          <li
            key={deck.deck_id}
            data-testid={`dashboard-deck-row-${deck.deck_slug}`}
            className="space-y-1"
          >
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-text-primary">{deck.deck_title}</span>
              <span className="text-text-muted">
                {deck.quiz_items_mastered}/{deck.total_quiz_items_visible} mastered
              </span>
            </div>
            <div
              className="h-2 w-full overflow-hidden rounded-full bg-bg-base"
              aria-label={`${Math.round(deck.mastery_pct * 100)}% mastery`}
            >
              <div
                className="h-full bg-text-accent"
                style={{ width: `${Math.round(deck.mastery_pct * 100)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
