import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BookOpen, Filter, Play, X } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { CategoryCard, CategoryCardSkeleton } from '@/components/study/CategoryCard'
import { TodaysReviewWidget } from '@/components/home/widgets/TodaysReviewWidget'
import { LastScanWidget } from '@/components/home/widgets/LastScanWidget'
import { StreakWidget } from '@/components/home/widgets/StreakWidget'
import { WeeklyProgressWidget } from '@/components/home/widgets/WeeklyProgressWidget'
import { TeamComingSoonWidget } from '@/components/home/widgets/TeamComingSoonWidget'
import { RankedDeckList } from '@/components/learn/RankedDeckList'
import { useAuth, type Persona } from '@/context/AuthContext'
import { useUsage } from '@/context/UsageContext'
import { useStudyDashboard } from '@/hooks/useStudyDashboard'
import { useRankedDecks } from '@/hooks/useRankedDecks'
import { capture } from '@/utils/posthog'
import type { Category } from '@/types'

// Phase 6 slice 6.7 — persona-aware Learn page. Spec
// docs/specs/phase-6/08-persona-learn-page.md.
//
// D-5 (locked): persona modes are inline functions inside this page file
// mirroring the on-disk HomeDashboard pattern (`pages/HomeDashboard.tsx`
// lines 32/65/79). Do NOT extract to separate files; that's a later
// cross-page refactor if it ever happens.

type LearnMode = 'interview' | 'habit' | 'team'

function personaToMode(persona: Persona): LearnMode {
  switch (persona) {
    case 'interview_prepper':
      return 'interview'
    case 'career_climber':
      return 'habit'
    case 'team_lead':
      return 'team'
  }
}

// ─── Inline mode #1: LearnInterviewMode (interview_prepper) ─────────────────
// Spec §4.1 — RankedDeckList is the spine; TodaysReview inline below.

function LearnInterviewMode({
  persona,
  plan,
}: {
  persona: Persona
  plan: 'free' | 'pro' | 'enterprise'
}) {
  const ranked = useRankedDecks(true)

  return (
    <div data-testid="learn-mode-interview" className="space-y-8">
      <section>
        <h2 className="font-display text-lg font-semibold text-text-primary mb-3">
          Your study path
        </h2>
        <RankedDeckList
          data={ranked.data}
          isLoading={ranked.isLoading}
          error={ranked.error}
          persona={persona}
          plan={plan}
        />
      </section>

      <section>
        <h2 className="font-display text-base font-semibold text-text-primary mb-3">
          Today's review
        </h2>
        <TodaysReviewWidget persona={persona} />
      </section>

      {ranked.isColdStart && (
        // Cold-start branch surfaces LastScanWidget per §6 so the user
        // has secondary "what scan you did last" context (in cold-start
        // that surface honestly says "no scan yet").
        <section>
          <LastScanWidget persona={persona} suppressed={false} />
        </section>
      )}
    </div>
  )
}

// ─── Inline mode #2: LearnHabitMode (career_climber) ─────────────────────────
// Spec §4.1 — TodaysReview is the spine; ranked decks render as a
// secondary "Curriculum suggestions" section, expanded by default
// per §12 D-4. Legacy categories grid renders at the bottom for the
// free-form-explore use case.

function LearnHabitMode({
  persona,
  plan,
  filteredCategoryId,
  onClearCategoryFilter,
}: {
  persona: Persona
  plan: 'free' | 'pro' | 'enterprise'
  filteredCategoryId: string | null
  onClearCategoryFilter: () => void
}) {
  const navigate = useNavigate()
  // §4.2 cross-cutting rule: career_climber doesn't fetch the ranker
  // (TodaysReview is the spine). The ranked-deck section appears as a
  // secondary "Curriculum suggestions" surface — see §4.1 row.
  // D-4: section is expanded by default (rendered, not collapsed-with-toggle).
  const ranked = useRankedDecks(true)
  const { categories, isLoading: categoriesLoading } = useStudyDashboard()

  const visibleCategories = useMemo(() => {
    if (!filteredCategoryId) return categories
    return categories.filter((c) => c.id === filteredCategoryId)
  }, [categories, filteredCategoryId])
  const filteredCategoryName = visibleCategories[0]?.name

  function handleCategoryClick(category: Category) {
    if (category.locked) {
      capture('locked_tile_clicked', {
        category_id: category.id,
        category_name: category.name,
      })
      return
    }
    capture('category_tile_clicked', {
      category_id: category.id,
      category_name: category.name,
      studied_count: category.studied_count,
      card_count: category.card_count,
    })
    navigate(`/learn/category/${category.id}`)
  }

  return (
    <div data-testid="learn-mode-habit" className="space-y-8">
      <section>
        <h2 className="font-display text-lg font-semibold text-text-primary mb-3">
          Today's practice
        </h2>
        <TodaysReviewWidget persona={persona} />
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StreakWidget persona={persona} />
        <WeeklyProgressWidget persona={persona} />
      </section>

      <section>
        <LastScanWidget persona={persona} suppressed={false} />
      </section>

      {/* §12 D-4 — Curriculum suggestions, expanded by default. */}
      <section data-testid="learn-mode-habit-curriculum-suggestions">
        <h2 className="font-display text-base font-semibold text-text-primary mb-3">
          Curriculum suggestions
        </h2>
        <RankedDeckList
          data={ranked.data}
          isLoading={ranked.isLoading}
          error={ranked.error}
          persona={persona}
          plan={plan}
        />
      </section>

      {/* Legacy ?category browse grid — §4.1 keeps this in HabitMode only. */}
      <section data-testid="learn-mode-habit-browse-categories">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-base font-semibold text-text-primary">
            Browse categories
          </h2>
          {filteredCategoryId && (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-xs">
                <Filter size={11} className="text-accent-primary" />
                <span className="text-text-primary font-medium">
                  Filtered: {filteredCategoryName ?? 'category'}
                </span>
              </span>
              <button
                type="button"
                data-testid="learn-habit-clear-category-filter"
                onClick={onClearCategoryFilter}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-contrast/[0.08] text-xs text-text-muted hover:text-text-secondary hover:border-contrast/[0.15] transition-colors"
              >
                Show all
              </button>
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {categoriesLoading
            ? [0, 1, 2].map((i) => <CategoryCardSkeleton key={i} />)
            : visibleCategories.map((cat, i) => (
                <CategoryCard
                  key={cat.id}
                  category={cat}
                  index={i}
                  onClick={() => handleCategoryClick(cat)}
                />
              ))}
        </div>
      </section>
    </div>
  )
}

// ─── Inline mode #3: LearnTeamMode (team_lead — v1 stub) ────────────────────
// Spec §4.1 — TeamComingSoonWidget at top sets B2B-coming expectation;
// inherits ranker behavior below.

function LearnTeamMode({
  persona,
  plan,
}: {
  persona: Persona
  plan: 'free' | 'pro' | 'enterprise'
}) {
  const ranked = useRankedDecks(true)

  return (
    <div data-testid="learn-mode-team" className="space-y-8">
      <TeamComingSoonWidget persona={persona} />

      <section>
        <h2 className="font-display text-lg font-semibold text-text-primary mb-3">
          Browse decks
        </h2>
        <RankedDeckList
          data={ranked.data}
          isLoading={ranked.isLoading}
          error={ranked.error}
          persona={persona}
          plan={plan}
        />
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StreakWidget persona={persona} />
        <WeeklyProgressWidget persona={persona} />
      </section>

      <section>
        <TodaysReviewWidget persona={persona} />
      </section>
    </div>
  )
}

// ─── Page shell ──────────────────────────────────────────────────────────────

export default function Learn() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { usage } = useUsage()
  const [searchParams, setSearchParams] = useSearchParams()

  // Spec §7.2 — query param ownership at parent level (mirrors
  // HomeDashboard's cross-cutting hook + suppression-flag pattern).
  const sourceParam = searchParams.get('source')
  const isLastScanSource = sourceParam === 'last_scan'
  const [sourceHintDismissed, setSourceHintDismissed] = useState(false)
  const showSourceHint = isLastScanSource && !sourceHintDismissed
  const sourceHintFiredRef = useRef(false)

  // ?category routes only to HabitMode per §4.2 + §7.2; other modes
  // silently ignore (no error, no banner).
  const filteredCategoryId = searchParams.get('category')

  // §9 + D-6 — once-per-mount idempotent firing for both events. Two
  // separate refs so each event has its own guard.
  const pageViewedRef = useRef(false)
  const modeRenderedRef = useRef(false)

  // The ranker is also called inside the persona-mode functions for
  // their own rendering. To populate `learn_page_viewed`'s
  // `has_ranked_decks` + `cold_start` properties WITHOUT double-fetching,
  // call the hook here too — React de-dupes in-flight requests for
  // identical params via the hook's internal state (each persona-mode
  // mount has its own independent state because they're separate
  // components, but axios and the BE are cheap; per spec #07 §12 D-12
  // there's no caching layer and the request is small). Pragmatic v1
  // — if telemetry shows the double-fetch matters we can lift the hook
  // into a context or a parent-pass-down prop.
  const persona = user?.persona ?? null
  const plan = (usage?.plan ?? 'free') as 'free' | 'pro' | 'enterprise'
  const fetchRankerForTelemetry =
    persona === 'interview_prepper' || persona === 'team_lead'
  const telemetryRanked = useRankedDecks(fetchRankerForTelemetry)

  const mode: LearnMode | null = persona ? personaToMode(persona) : null

  // §9 — `study_dashboard_source_hint_shown` preserved verbatim per D-8 +
  // spec #62 §7.4. Same firing logic as the prior StudyDashboard.tsx
  // emission: once per mount via useRef when `?source=last_scan`.
  useEffect(() => {
    if (!isLastScanSource) return
    if (sourceHintFiredRef.current) return
    sourceHintFiredRef.current = true
    capture('study_dashboard_source_hint_shown', {
      source: 'last_scan',
      persona: persona ?? null,
      copy_variant: '6A',
    })
  }, [isLastScanSource, persona])

  // §9 D-6 — `learn_mode_rendered` once per mount via useRef.
  useEffect(() => {
    if (!mode) return
    if (modeRenderedRef.current) return
    modeRenderedRef.current = true
    capture('learn_mode_rendered', { mode, persona })
  }, [mode, persona])

  // §9 — `learn_page_viewed` once per mount, after the ranker call
  // resolves so `has_ranked_decks` + `cold_start` are populated. For
  // career_climber the ranker is not called here (telemetryRanked stays
  // idle) — fire immediately with `has_ranked_decks=false` +
  // `cold_start=false` per the §9 spec table.
  useEffect(() => {
    if (!mode) return
    if (pageViewedRef.current) return
    if (fetchRankerForTelemetry && telemetryRanked.isLoading) return
    pageViewedRef.current = true
    capture('learn_page_viewed', {
      persona,
      plan,
      mode,
      has_ranked_decks: (telemetryRanked.data?.decks.length ?? 0) > 0,
      cold_start: telemetryRanked.isColdStart,
    })
  }, [
    mode,
    persona,
    plan,
    fetchRankerForTelemetry,
    telemetryRanked.isLoading,
    telemetryRanked.data,
    telemetryRanked.isColdStart,
  ])

  if (!user || !user.persona || !mode) return null

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div data-testid="page-learn" className="max-w-6xl mx-auto px-4 py-10 sm:px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8"
        >
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <div className="w-8 h-8 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
                <BookOpen size={16} className="text-accent-primary" />
              </div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary">
                Learn <span className="text-accent-primary">Dashboard</span>
              </h1>
            </div>
            <p className="text-sm text-text-secondary">
              {mode === 'interview' &&
                'Ranked study path based on your most recent scan.'}
              {mode === 'habit' &&
                'Daily review keeps your skills sharp.'}
              {mode === 'team' &&
                "Browse decks now — assigned-deck workflows are coming."}
            </p>
          </div>

          <GlowButton onClick={() => navigate('/learn/daily')} size="sm">
            <Play size={13} />
            Start Daily Review
          </GlowButton>
        </motion.div>

        {/* Spec #62 ?source=last_scan banner (D-8 preserved verbatim) */}
        {showSourceHint && (
          <motion.div
            data-testid="study-dashboard-source-hint"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 flex items-center gap-3 rounded-xl border border-contrast/[0.08] bg-contrast/[0.02] px-4 py-2.5"
          >
            <BookOpen size={16} className="text-accent-primary shrink-0" />
            <p className="flex-1 text-sm text-text-secondary">
              Studying gaps from your last scan.
            </p>
            <button
              type="button"
              data-testid="study-dashboard-source-hint-dismiss"
              aria-label="Dismiss"
              onClick={() => setSourceHintDismissed(true)}
              className="rounded-md p-1 text-text-muted hover:text-text-primary hover:bg-contrast/[0.06] transition-colors"
            >
              <X size={14} />
            </button>
          </motion.div>
        )}

        {/* Persona-mode branch */}
        {user.persona === 'interview_prepper' && (
          <LearnInterviewMode persona={user.persona} plan={plan} />
        )}
        {user.persona === 'career_climber' && (
          <LearnHabitMode
            persona={user.persona}
            plan={plan}
            filteredCategoryId={filteredCategoryId}
            onClearCategoryFilter={() => setSearchParams({})}
          />
        )}
        {user.persona === 'team_lead' && (
          <LearnTeamMode persona={user.persona} plan={plan} />
        )}
      </div>
    </PageWrapper>
  )
}
