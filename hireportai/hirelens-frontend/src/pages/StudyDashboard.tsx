import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BookOpen, Play, RefreshCw, AlertCircle, Filter, Target, Flame, Users, Crosshair } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { CategoryCard, CategoryCardSkeleton } from '@/components/study/CategoryCard'
import { PaywallModal } from '@/components/PaywallModal'
import { useStudyDashboard } from '@/hooks/useStudyDashboard'
import { useAuth } from '@/context/AuthContext'
import { useUsage } from '@/context/UsageContext'
import { useGamification } from '@/context/GamificationContext'
import { capture } from '@/utils/posthog'
import type { Category } from '@/types'

// ─── Page ─────────────────────────────────────────────────────────────────────

const PERSONA_CONFIG = {
  interview_prepper: {
    icon: Target,
    emoji: '🎯',
    label: 'Interview prep',
    cssVar: 'var(--sf-accent-primary)',
    link: '/learn/mission',
    linkLabel: 'Go to Mission →',
  },
  career_climber: {
    icon: Flame,
    emoji: '🔥',
    label: 'Daily practice',
    cssVar: 'var(--sf-accent-secondary)',
    link: '/learn/daily',
    linkLabel: 'Start Daily 5 →',
  },
  team_lead: {
    icon: Users,
    emoji: '👥',
    label: 'Team exploration',
    cssVar: 'var(--sf-accent-warm, #f59e0b)',
    link: '/learn',
    linkLabel: 'Browse All →',
  },
} as const

function daysUntil(dateStr: string): number | null {
  try {
    const target = new Date(dateStr)
    const now = new Date()
    const diff = target.getTime() - now.getTime()
    return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)))
  } catch {
    return null
  }
}

export default function StudyDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { usage } = useUsage()
  const { stats: gamificationStats } = useGamification()
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
      navigate(`/learn/category/${category.id}`)
    }
  }

  const skeletonCount = 6

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div data-testid="page-study-dashboard" className="max-w-6xl mx-auto px-4 py-10 sm:px-6">

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

          <GlowButton onClick={() => navigate('/learn/daily')} size="sm" data-tour="daily-review">
            <Play size={13} />
            Start Daily Review
          </GlowButton>
        </motion.div>

        {/* ── Your Goal card ──────────────────────────────────────────── */}
        {user?.persona ? (() => {
          const cfg = PERSONA_CONFIG[user.persona]
          const Icon = cfg.icon
          const c = cfg.cssVar
          const days = user.persona === 'interview_prepper' && user.interview_target_date
            ? daysUntil(user.interview_target_date)
            : null
          const streak = gamificationStats?.current_streak ?? 0
          return (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 rounded-2xl"
              style={{ border: `1px solid color-mix(in srgb, ${c} 20%, transparent)`, background: `color-mix(in srgb, ${c} 5%, transparent)` }}
            >
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ background: `color-mix(in srgb, ${c} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${c} 20%, transparent)` }}
                  >
                    <Icon size={18} style={{ color: c }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-text-primary">
                        {cfg.emoji} {cfg.label}
                      </span>
                      {user.persona === 'interview_prepper' && user.interview_target_company && (
                        <span className="text-xs text-text-muted">
                          at {user.interview_target_company}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      {days !== null && (
                        <span className="text-xs font-medium" style={{ color: c }}>
                          {days === 0 ? 'Today!' : `${days} day${days === 1 ? '' : 's'} left`}
                        </span>
                      )}
                      {user.persona === 'career_climber' && (
                        <span className="text-xs font-medium" style={{ color: c }}>
                          {streak} day streak
                        </span>
                      )}
                      {user.persona === 'team_lead' && !isLoading && (
                        <span className="text-xs text-text-muted">
                          {categories.length} categories browsed
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => navigate(cfg.link)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                    style={{ background: `color-mix(in srgb, ${c} 12%, transparent)`, color: c }}
                  >
                    {cfg.linkLabel}
                  </button>
                </div>
              </div>
            </motion.div>
          )
        })() : (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-2xl border border-contrast/[0.08] bg-contrast/[0.02]"
          >
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-contrast/[0.06] border border-contrast/[0.1]">
                  <Crosshair size={18} className="text-text-muted" />
                </div>
                <div>
                  <span className="text-sm font-semibold text-text-primary">Your Goal</span>
                  <p className="text-xs text-text-muted mt-0.5">Tell us what you're working towards</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}

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
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-contrast/[0.08] text-xs text-text-muted hover:text-text-secondary hover:border-contrast/[0.15] transition-colors"
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
                className="flex flex-col items-center gap-4 py-20 text-center"
              >
                <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
                  <BookOpen size={24} className="text-accent-primary" />
                </div>
                <div>
                  <p className="text-base font-semibold text-text-primary mb-1">No categories yet</p>
                  <p className="text-sm text-text-muted max-w-xs mx-auto">
                    Scan your resume first — we'll build study categories from your skill gaps.
                  </p>
                </div>
                <GlowButton size="sm" onClick={() => navigate('/prep/analyze')}>
                  Scan Resume
                </GlowButton>
              </motion.div>
            )}

            {/* Filtered to a category that isn't in the visible set (likely locked) */}
            {filterMatchedNothing && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-4 py-16 text-center"
              >
                <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
                  <Filter size={24} className="text-accent-primary" />
                </div>
                <div>
                  <p className="text-base font-semibold text-text-primary mb-1">Category not available</p>
                  <p className="text-sm text-text-muted max-w-xs mx-auto">
                    That category isn't included in your current plan. Explore other categories or upgrade.
                  </p>
                </div>
                <GlowButton variant="ghost" size="sm" onClick={() => setSearchParams({})}>
                  Show all categories
                </GlowButton>
              </motion.div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-tour="category-grid">
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
