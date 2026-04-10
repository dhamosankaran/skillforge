import { motion } from 'framer-motion'
import { Lock } from 'lucide-react'
import clsx from 'clsx'
import type { Category } from '@/types'

interface CategoryCardProps {
  category: Category
  index: number            // stagger entrance animation
  onClick: () => void
}

/** Animated progress bar — width animates from 0 on mount. */
function ProgressBar({ studied, total, locked }: { studied: number; total: number; locked: boolean }) {
  const pct = total > 0 ? Math.min(100, (studied / total) * 100) : 0

  return (
    <div className="mt-3">
      <div className="h-1.5 rounded-full bg-contrast/[0.06] overflow-hidden">
        {!locked && (
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-accent-primary to-accent-secondary"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.7, delay: 0.1, ease: 'easeOut' }}
          />
        )}
      </div>
      <p className="mt-1.5 text-[11px] text-text-muted">
        {locked ? 'Pro only' : `${studied} / ${total} studied`}
      </p>
    </div>
  )
}

export function CategoryCard({ category, index, onClick }: CategoryCardProps) {
  const { name, icon, card_count, studied_count, locked } = category

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={
        locked
          ? { borderColor: 'var(--border)' }
          : {
              y: -3,
              scale: 1.02,
              borderColor: 'var(--border)',
              boxShadow: '0 12px 36px rgba(0,0,0,0.35), 0 0 20px rgba(var(--color-accent-primary), 0.08)',
              transition: { duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] },
            }
      }
      whileTap={{ scale: 0.98, transition: { duration: 0.1 } }}
      onClick={onClick}
      className={clsx(
        'relative cursor-pointer rounded-2xl border border-contrast/[0.06] bg-bg-surface/60 p-5 min-h-[160px] flex flex-col transition-colors duration-200',
        locked && 'opacity-60'
      )}
    >
      {/* Lock badge */}
      {locked && (
        <div className="absolute top-3 right-3 w-6 h-6 rounded-lg bg-contrast/[0.06] border border-contrast/[0.08] flex items-center justify-center">
          <Lock size={11} className="text-text-muted" />
        </div>
      )}

      {/* Icon + name */}
      <div className="flex items-center gap-3">
        <span className={clsx('text-2xl leading-none', locked && 'grayscale')} aria-hidden="true">
          {icon}
        </span>
        <h3 className="font-display font-semibold text-sm text-text-primary leading-snug">
          {name}
        </h3>
      </div>

      {/* Card count */}
      <p className="mt-2 text-[12px] text-text-muted">
        {card_count} {card_count === 1 ? 'card' : 'cards'}
      </p>

      {/* Progress bar */}
      <div className="mt-auto">
        <ProgressBar studied={studied_count} total={card_count} locked={locked} />
      </div>
    </motion.div>
  )
}

/** Pulsing skeleton tile that matches CategoryCard dimensions. */
export function CategoryCardSkeleton() {
  return (
    <div className="rounded-2xl border border-contrast/[0.04] bg-bg-surface/40 p-5 min-h-[160px] flex flex-col animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 rounded-xl bg-bg-elevated" />
        <div className="h-3.5 w-28 rounded-full bg-bg-elevated" />
      </div>
      <div className="h-3 w-16 rounded-full bg-bg-elevated" />
      <div className="mt-auto pt-4 space-y-1.5">
        <div className="h-1.5 rounded-full bg-bg-elevated" />
        <div className="h-2.5 w-20 rounded-full bg-bg-elevated" />
      </div>
    </div>
  )
}
