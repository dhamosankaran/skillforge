import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BookOpen, Sparkles, Target } from 'lucide-react'
import { GlowButton } from '@/components/ui/GlowButton'
import { capture } from '@/utils/posthog'
import type { Persona } from '@/context/AuthContext'
import type { RankedDeck, RankedDecksResponse } from '@/types'

interface RankedDeckListProps {
  data: RankedDecksResponse | null
  isLoading: boolean
  error: Error | null
  persona: Persona
  plan: 'free' | 'pro' | 'enterprise'
  // First-lesson resolver — see Learn.tsx wiring; deck-card click navigates to
  // /learn/lesson/<first-lesson-id>. When the resolver returns null (no
  // lessons loaded yet), the card falls back to /learn (non-blocking).
  resolveFirstLessonId?: (deck: RankedDeck) => string | null
}

// Spec #08 §6 D-7 — verbose-most-specific copy variant.
const COLD_START_HEADLINE = 'Take a scan to personalize your learning path.'
const COLD_START_BODY =
  "We'll rank the lessons that close your skill gaps."

// Spec #08 §12 D-2 — actionable empty-state copy.
const EMPTY_STATE_COPY =
  'No decks match your profile yet — scan your resume to get personalized recommendations.'

export function RankedDeckList({
  data,
  isLoading,
  error,
  persona,
  plan,
  resolveFirstLessonId,
}: RankedDeckListProps) {
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div
        data-testid="ranked-deck-list-loading"
        className="grid grid-cols-1 md:grid-cols-2 gap-4"
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-40 rounded-2xl border border-contrast/[0.08] bg-contrast/[0.02] animate-pulse"
          />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div
        data-testid="ranked-deck-list-error"
        className="rounded-2xl border border-danger/20 bg-danger/5 p-6 text-sm text-text-secondary"
      >
        Couldn't load ranked decks. Try refreshing.
      </div>
    )
  }

  const isColdStart = data?.cold_start === true
  const decks = data?.decks ?? []

  function handleDeckClick(deck: RankedDeck) {
    capture('learn_deck_clicked', {
      deck_slug: deck.deck.slug,
      deck_position: deck.rank,
      persona,
      plan,
      score: deck.score,
      matched_gap_count: deck.matched_gaps.length,
      is_cold_start: isColdStart,
    })
    const lessonId = resolveFirstLessonId?.(deck) ?? null
    if (lessonId) {
      navigate(`/learn/lesson/${lessonId}`)
    } else {
      // Defensive fallback — first-lesson resolver hasn't loaded yet.
      // /learn re-renders the same page; user can re-click after lessons load.
      navigate('/learn')
    }
  }

  return (
    <div data-testid="ranked-deck-list" className="space-y-4">
      {isColdStart && (
        <motion.div
          data-testid="ranked-deck-list-cold-start"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-accent-primary/20 bg-accent-primary/5 p-5"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center shrink-0">
              <Sparkles size={18} className="text-accent-primary" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-text-primary mb-1">
                {COLD_START_HEADLINE}
              </p>
              <p className="text-sm text-text-secondary mb-4">
                {COLD_START_BODY}
              </p>
              <GlowButton
                size="sm"
                onClick={() => navigate('/prep/analyze')}
                data-testid="ranked-deck-list-cold-start-cta"
              >
                Scan resume
              </GlowButton>
            </div>
          </div>
        </motion.div>
      )}

      {!isColdStart && decks.length === 0 && (
        <div
          data-testid="ranked-deck-list-empty"
          className="rounded-2xl border border-contrast/[0.08] bg-contrast/[0.02] p-6 text-center text-sm text-text-secondary"
        >
          {EMPTY_STATE_COPY}
        </div>
      )}

      {decks.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {decks.map((rd) => (
            <button
              key={rd.deck.id}
              type="button"
              data-testid={`ranked-deck-card-${rd.deck.slug}`}
              data-rank={rd.rank}
              onClick={() => handleDeckClick(rd)}
              className="text-left rounded-2xl border border-contrast/[0.08] bg-bg-surface p-5 transition-colors hover:border-accent-primary/30 hover:bg-accent-primary/[0.03]"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center shrink-0">
                  <BookOpen size={18} className="text-accent-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-text-primary mb-1 truncate">
                    {rd.deck.title}
                  </h3>
                  <p className="text-xs text-text-muted line-clamp-2 mb-3">
                    {rd.deck.description}
                  </p>
                  {rd.matched_gaps.length > 0 && (
                    <div
                      data-testid={`ranked-deck-card-${rd.deck.slug}-gaps`}
                      className="flex flex-wrap gap-1.5"
                    >
                      {rd.matched_gaps.slice(0, 4).map((gap) => (
                        <span
                          key={gap}
                          className="inline-flex items-center gap-1 rounded-full border border-accent-primary/20 bg-accent-primary/10 px-2 py-0.5 text-[11px] font-medium text-accent-primary"
                        >
                          <Target size={9} />
                          {gap}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
