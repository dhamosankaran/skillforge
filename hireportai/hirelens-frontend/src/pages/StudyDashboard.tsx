import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Play, RefreshCw, Lock, ArrowRight, X, AlertCircle } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { CategoryCard, CategoryCardSkeleton } from '@/components/study/CategoryCard'
import { useStudyDashboard } from '@/hooks/useStudyDashboard'
import { useUsage } from '@/context/UsageContext'
import { capture } from '@/utils/posthog'
import type { Category } from '@/types'

// ─── Upgrade modal ────────────────────────────────────────────────────────────

interface UpgradeModalProps {
  category: Category | null
  onClose: () => void
}

function CategoryUpgradeModal({ category, onClose }: UpgradeModalProps) {
  const navigate = useNavigate()

  return (
    <AnimatePresence>
      {category && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', bounce: 0.2, duration: 0.35 }}
            className="fixed inset-0 z-[101] flex items-center justify-center p-4"
          >
            <div className="relative w-full max-w-sm bg-bg-surface border border-white/[0.08] rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.5)] overflow-hidden">
              {/* Top glow line */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-px bg-gradient-to-r from-transparent via-accent-primary/50 to-transparent" />

              <button
                onClick={onClose}
                className="absolute top-3.5 right-3.5 p-1.5 rounded-lg text-text-muted hover:text-text-secondary hover:bg-white/[0.04] transition-colors"
                aria-label="Close"
              >
                <X size={15} />
              </button>

              <div className="p-7 text-center">
                {/* Icon */}
                <div className="w-12 h-12 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center mx-auto mb-4">
                  <Lock size={20} className="text-accent-primary" />
                </div>

                <h2 className="font-display text-lg font-bold text-text-primary mb-2">
                  Unlock {category.name}
                </h2>
                <p className="text-sm text-text-secondary leading-relaxed mb-6">
                  <span className="text-2xl mr-2" aria-hidden="true">{category.icon}</span>
                  <br />
                  This category is available on Pro. Upgrade to access{' '}
                  <strong className="text-text-primary">{category.name}</strong> and all other
                  premium card decks.
                </p>

                <div className="flex flex-col gap-2.5">
                  <button
                    onClick={() => { onClose(); navigate('/pricing') }}
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-accent-primary text-bg-base text-sm font-semibold hover:bg-accent-primary/90 transition-colors shadow-[0_0_20px_rgba(0,255,200,0.15)]"
                  >
                    Upgrade to Pro
                    <ArrowRight size={14} />
                  </button>
                  <button
                    onClick={onClose}
                    className="w-full py-2 text-sm text-text-muted hover:text-text-secondary transition-colors"
                  >
                    Maybe later
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function StudyDashboard() {
  const navigate = useNavigate()
  const { usage } = useUsage()
  const { categories, isLoading, error, refetch } = useStudyDashboard()
  const [lockedCategory, setLockedCategory] = useState<Category | null>(null)

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

        {/* ── Category grid ─────────────────────────────────────────────── */}
        {!error && (
          <>
            {/* Empty state (data loaded, no categories) */}
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

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {isLoading
                ? [...Array(skeletonCount)].map((_, i) => <CategoryCardSkeleton key={i} />)
                : categories.map((cat, i) => (
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

      {/* ── Upgrade modal ────────────────────────────────────────────────── */}
      <CategoryUpgradeModal
        category={lockedCategory}
        onClose={() => setLockedCategory(null)}
      />
    </PageWrapper>
  )
}
