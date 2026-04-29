import { useEffect, useRef } from 'react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { useAuth } from '@/context/AuthContext'
import { useFsrsDashboard } from '@/hooks/useFsrsDashboard'
import { capture } from '@/utils/posthog'
import { DueToday } from '@/components/dashboard/DueToday'
import { Streak } from '@/components/dashboard/Streak'
import { RetentionCurve } from '@/components/dashboard/RetentionCurve'
import { DeckMastery } from '@/components/dashboard/DeckMastery'
import { ReviewHistory } from '@/components/dashboard/ReviewHistory'

// Phase 6 slice 6.8 — User-self FSRS dashboard at /learn/dashboard.
// Spec docs/specs/phase-6/09-fsrs-dashboard.md.
//
// D-1 mount path /learn/dashboard. D-2 universal composition (no
// per-persona render modes; cards-due → streak → retention →
// deck-mastery → review-history per §8.1). D-11 single
// dashboard_viewed event once-per-mount via useRef. D-13 per-section
// cold-start variants (each section component owns its empty copy).

export default function Dashboard() {
  const { user } = useAuth()
  const { data, isLoading, error, isColdStart } = useFsrsDashboard()
  const viewedRef = useRef(false)

  // §9 D-11 — `dashboard_viewed` once per mount via useRef.
  // Fires AFTER the fetch resolves so the payload includes is_cold_start.
  useEffect(() => {
    if (viewedRef.current) return
    if (!data) return
    viewedRef.current = true
    capture('dashboard_viewed', {
      persona: data.persona,
      plan: data.plan,
      is_cold_start: data.is_cold_start,
      retention_window_days: data.retention_window_days,
    })
  }, [data])

  return (
    <PageWrapper className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <h1
          data-testid="dashboard-page"
          className="font-display text-2xl font-bold text-text-primary"
        >
          Your dashboard
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          A read-only view of your FSRS progress
          {user?.name ? `, ${user.name.split(' ')[0]}.` : '.'}
        </p>
      </header>

      {isLoading && !data && (
        <div data-testid="dashboard-loading" className="text-sm text-text-muted">
          Loading your progress…
        </div>
      )}

      {error && (
        <div
          data-testid="dashboard-error"
          className="rounded-lg border border-border-subtle bg-bg-surface p-4 text-sm text-text-muted"
        >
          We couldn't load your dashboard. Please try again later.
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <DueToday data={data.cards_due} coldStart={isColdStart} />
          <Streak data={data.streak} coldStart={isColdStart} />
          <RetentionCurve data={data.retention} coldStart={isColdStart} />
          <DeckMastery data={data.deck_mastery} coldStart={isColdStart} />
          <ReviewHistory data={data.review_history} coldStart={isColdStart} />
        </div>
      )}
    </PageWrapper>
  )
}
