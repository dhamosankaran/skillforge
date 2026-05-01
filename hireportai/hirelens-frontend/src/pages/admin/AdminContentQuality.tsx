import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { capture } from '@/utils/posthog'
import { useAdminContentQuality } from '@/hooks/useAdminContentQuality'
import { DeckRollupTable } from '@/components/admin/content-quality/DeckRollupTable'
import { WorstLessonsTable } from '@/components/admin/content-quality/WorstLessonsTable'
import { WorstQuizItemsTable } from '@/components/admin/content-quality/WorstQuizItemsTable'

const WINDOW_OPTIONS = [7, 30, 60, 90] as const

export default function AdminContentQuality() {
  const { user } = useAuth()
  const [windowDays, setWindowDays] = useState<number>(30)
  const [includeArchived, setIncludeArchived] = useState<boolean>(false)
  const { data, loading, error } = useAdminContentQuality({
    windowDays,
    includeArchived,
  })

  // Once-per-mount PostHog fire (mirrors slice 6.8 D-11 + slice 6.10 D-13).
  const firedRef = useRef(false)
  useEffect(() => {
    if (firedRef.current) return
    if (!data || !user) return
    firedRef.current = true
    capture('admin_content_quality_viewed', {
      admin_id: user.id,
      window_days: data.window_days,
      include_archived: data.include_archived,
      internal: true,
    })
  }, [data, user])

  return (
    <div className="space-y-8" data-testid="admin-content-quality">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold text-text-primary">
            Content quality
          </h2>
          <p className="text-sm text-text-secondary mt-0.5">
            Per-deck rollup and worst-first lesson + quiz-item rankings over
            the configured review window. Lessons with at least{' '}
            <strong>10 reviews</strong> get a smoothed quality score written
            back to <code>lessons.quality_score</code>.
          </p>
        </div>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-4">
          <label className="text-sm text-text-secondary inline-flex items-center gap-2">
            Window:
            <select
              value={windowDays}
              onChange={(e) => setWindowDays(Number(e.target.value))}
              data-testid="window-selector"
              className="bg-bg-surface border border-contrast/[0.08] text-text-primary rounded-md px-2 py-1 text-sm"
            >
              {WINDOW_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt} days
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-text-secondary inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              data-testid="include-archived-toggle"
              className="rounded border-contrast/[0.12] bg-bg-surface text-accent-primary"
            />
            Include archived
          </label>
        </div>
      </header>

      {loading && (
        <div
          className="flex items-center gap-2 text-text-secondary text-sm"
          data-testid="content-quality-loading"
        >
          <Loader2 size={14} className="animate-spin" /> Loading…
        </div>
      )}

      {error && !loading && (
        <p
          className="text-sm text-accent-danger"
          data-testid="content-quality-error"
        >
          {error}
        </p>
      )}

      {data && !loading && (
        <>
          {data.is_cold_start && (
            <p
              className="rounded-md bg-bg-surface/60 border border-contrast/[0.08] px-3 py-2 text-sm text-text-secondary"
              data-testid="cold-start-banner"
            >
              No reviews in window — quality scores not yet computable.
              Re-check once users have reviewed cards.
            </p>
          )}

          <section className="space-y-3">
            <h3 className="text-base font-semibold text-text-primary">
              Decks
            </h3>
            <DeckRollupTable decks={data.decks} />
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-semibold text-text-primary">
              Worst lessons
            </h3>
            <WorstLessonsTable lessons={data.worst_lessons} />
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-semibold text-text-primary">
              Worst quiz items
            </h3>
            <WorstQuizItemsTable items={data.worst_quiz_items} />
          </section>

          <footer className="text-xs text-text-secondary">
            Writebacks applied this load: {data.writebacks_applied}. Generated
            at {new Date(data.generated_at).toLocaleString()}.
          </footer>
        </>
      )}
    </div>
  )
}
