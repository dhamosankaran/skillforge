import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertCircle, ArrowLeft, ArrowRight, RefreshCw } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { fetchCardsByCategory, type CategoryCardsResponse } from '@/services/api'
import { capture } from '@/utils/posthog'

/**
 * Category detail page — minimal card list for a single category.
 *
 * Closes the dead `/study/category/:id` route that `StudyDashboard`
 * navigates to on tile click. Fetches the category + its cards via
 * `GET /api/v1/cards/category/{id}` and links each row into the
 * existing `CardViewer` at `/study/card/:id`.
 */
export default function CategoryDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<CategoryCardsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchCardsByCategory(id)
      .then((resp) => {
        if (cancelled) return
        setData(resp)
        capture('category_detail_viewed', {
          category_id: resp.category.id,
          category_name: resp.category.name,
          card_count: resp.total,
        })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err : new Error('Failed to load category'))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-4xl mx-auto px-4 py-10 sm:px-6">
        {/* Breadcrumb */}
        <Link
          to="/study"
          className="inline-flex items-center gap-1.5 text-[11px] tracking-wide uppercase text-text-muted hover:text-text-secondary transition-colors mb-6"
        >
          <ArrowLeft size={12} />
          Study Dashboard
        </Link>

        {/* Header */}
        {isLoading ? (
          <div className="h-12 w-60 rounded-xl bg-bg-surface/60 animate-pulse mb-8" />
        ) : data ? (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 flex items-center gap-4"
          >
            <div className="w-12 h-12 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center text-2xl">
              {data.category.icon}
            </div>
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary">
                {data.category.name}
              </h1>
              <p className="text-xs text-text-muted font-mono mt-0.5">
                {data.total} card{data.total === 1 ? '' : 's'}
              </p>
            </div>
          </motion.div>
        ) : null}

        {/* Error */}
        {error && !isLoading && (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
              <AlertCircle size={20} className="text-red-400" />
            </div>
            <p className="text-sm font-medium text-text-primary">
              Couldn't load this category
            </p>
            <p className="text-xs text-text-muted">{error.message}</p>
            <GlowButton
              variant="ghost"
              size="sm"
              onClick={() => navigate(0)}
            >
              <RefreshCw size={13} />
              Retry
            </GlowButton>
          </div>
        )}

        {/* Card list */}
        {data && !error && (
          <>
            {data.cards.length === 0 ? (
              <div className="rounded-xl border border-contrast/[0.06] bg-bg-surface/50 p-8 text-center">
                <p className="text-sm text-text-secondary">
                  No cards in this category yet.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {data.cards.map((card, i) => (
                  <motion.button
                    key={card.id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.03 * i }}
                    onClick={() => navigate(`/study/card/${card.id}`)}
                    className="group w-full flex items-center gap-4 rounded-xl border border-contrast/[0.06] bg-bg-surface/50 p-4 sm:p-5 text-left hover:border-contrast/[0.14] hover:bg-bg-surface/70 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {card.question}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span
                          className={
                            'text-[10px] uppercase tracking-wider font-mono px-1.5 py-0.5 rounded ' +
                            (card.difficulty === 'easy'
                              ? 'text-accent-secondary bg-accent-secondary/10'
                              : card.difficulty === 'hard'
                                ? 'text-red-400 bg-red-400/10'
                                : 'text-accent-primary bg-accent-primary/10')
                          }
                        >
                          {card.difficulty}
                        </span>
                        {card.tags.slice(0, 3).map((t) => (
                          <span
                            key={t}
                            className="text-[10px] text-text-muted font-mono"
                          >
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                    <ArrowRight
                      size={14}
                      className="text-text-muted group-hover:text-text-secondary transition-colors shrink-0"
                    />
                  </motion.button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </PageWrapper>
  )
}
