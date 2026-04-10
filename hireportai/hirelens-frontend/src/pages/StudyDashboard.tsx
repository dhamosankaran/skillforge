import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BookOpen, Play, RefreshCw, AlertCircle, Filter } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { CategoryCard, CategoryCardSkeleton } from '@/components/study/CategoryCard'
import { PaywallModal } from '@/components/PaywallModal'
import { useStudyDashboard } from '@/hooks/useStudyDashboard'
import { useUsage } from '@/context/UsageContext'
import { capture } from '@/utils/posthog'
import type { Category } from '@/types'

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function StudyDashboard() {
  const navigate = useNavigate()
  const { usage } = useUsage()
  const { categories, isLoading, error, refetch } = useStudyDashboard()
  const [lockedCategory, setLockedCategory] = useState<Category | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  // Spec #09: when arriving from the onboarding bridge, the URL carries
  // `?category=<id>`. Filter the grid down to that single category so the
  // user lands directly on what they just clicked. A "Show all" pill clears
  // the filter without dropping navigation history.
  const filteredCategoryId = searchParams.get('category')
  const visibleCategories = useMemo(() => {
    if (!filteredCategoryId) return categories
    return categories.filter((c) => c.id === filteredCategoryId)
  }, [categories, filteredCategoryId])
  const filteredCategoryName = visibleCategories[0]?.name
  const filterMatchedNothing =
    !!filteredCategoryId && !isLoading && visibleCategories.length === 0

  // AC-9: fire study_dashboard_viewed once data has loaded
  useEffect(() => {
    if (isLoading) return
    const lockedCount = categories.filter((c) => c.locked).length
    capture('study_dashboard_viewed', {
      category_count: categories.length,
      locked_count: lockedCount,
      plan: usage.plan,
    })
  }, [isLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleTileClick(category: Category) {
    if (category.locked) {
      capture('locked_tile_clicked', {
        category_id: category.id,
        category_name: category.name,
      })
      setLockedCategory(category)
    } else {
      capture('category_tile_clicked', {
        category_id: category.id,
        category_name: category.name,
        studied_count: category.studied_count,
        card_count: category.card_count,
      })
      navigate(`/study/category/${category.id}`)
    }
  }

  const skeletonCount = 6

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-6xl mx-auto px-4 py-10 sm:px-6">

        {/* ── Header ───────────────────────────────────────────────────── */}
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
                Study <span className="text-accent-primary">Dashboard</span>
              </h1>
            </div>
            <p className="text-sm text-text-secondary">
              Choose a category to study or jump into your daily review.
            </p>
          </div>

          <GlowButton onClick={() => navigate('/study/daily')} size="sm">
            <Play size={13} />
            Start Daily Review
          </GlowButton>
        </motion.div>

        {/* ── Error state ──────────────────────────────────────────────── */}
        {error && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center gap-4 py-16 text-center"
          >
            <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
              <AlertCircle size={20} className="text-red-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary mb-1">Failed to load categories</p>
              <p className="text-xs text-text-muted">{error.message}</p>
            </div>
            <GlowButton variant="ghost" size="sm" onClick={refetch}>
              <RefreshCw size={13} />
              Retry
            </GlowButton>
          </motion.div>
        )}

        {/* ── Onboarding filter pill ────────────────────────────────────── */}
        {filteredCategoryId && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-5 flex items-center gap-2 flex-wrap"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-xs">
              <Filter size={11} className="text-accent-primary" />
              <span className="text-text-primary font-medium">
                Filtered: {filteredCategoryName ?? 'category'}
              </span>
            </div>
            <button
              onClick={() => setSearchParams({})}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-white/[0.08] text-xs text-text-muted hover:text-text-secondary hover:border-white/[0.15] transition-colors"
            >
              Show all categories
            </button>
          </motion.div>
        )}

        {/* ── Category grid ─────────────────────────────────────────────── */}
        {!error && (
          <>
            {/* Empty state (data loaded, no categories at all) */}
            {!isLoading && categories.length === 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-3 py-20 text-center"
              >
                <BookOpen size={36} className="text-text-muted opacity-40" />
                <p className="text-sm text-text-muted">No categories found.</p>
              </motion.div>
            )}

            {/* Filtered to a category that isn't in the visible set (likely locked) */}
            {filterMatchedNothing && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-3 py-16 text-center"
              >
                <BookOpen size={36} className="text-text-muted opacity-40" />
                <p className="text-sm text-text-muted">
                  That category isn't available on your current plan.
                </p>
                <GlowButton variant="ghost" size="sm" onClick={() => setSearchParams({})}>
                  Show all categories
                </GlowButton>
              </motion.div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {isLoading
                ? [...Array(skeletonCount)].map((_, i) => <CategoryCardSkeleton key={i} />)
                : visibleCategories.map((cat, i) => (
                    <CategoryCard
                      key={cat.id}
                      category={cat}
                      index={i}
                      onClick={() => handleTileClick(cat)}
                    />
                  ))}
            </div>
          </>
        )}
      </div>

      {/* ── Paywall modal ───────────────────────────────────────────────── */}
      <PaywallModal
        open={lockedCategory !== null}
        onClose={() => setLockedCategory(null)}
        trigger="locked_category"
        context={{ categoryName: lockedCategory?.name }}
      />
    </PageWrapper>
  )
}
