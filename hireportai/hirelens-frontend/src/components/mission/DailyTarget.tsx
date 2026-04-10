/**
 * DailyTarget — "8 cards today" with animated progress bar.
 *
 * Shows the day's card target vs completed count, a progress bar,
 * and a "Start studying" / "All done!" button.
 */
import { motion } from 'framer-motion'
import { BookOpen, CheckCircle } from 'lucide-react'
import { GlowButton } from '@/components/ui/GlowButton'

interface DailyTargetProps {
  cardsTarget: number
  cardsCompleted: number
  onStudy: () => void
  dayComplete: boolean
}

export function DailyTarget({ cardsTarget, cardsCompleted, onStudy, dayComplete }: DailyTargetProps) {
  const pct = cardsTarget > 0 ? Math.min(100, Math.round((cardsCompleted / cardsTarget) * 100)) : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="rounded-2xl border border-white/[0.07] bg-bg-surface/60 p-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
            <BookOpen size={14} className="text-accent-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary">Today's Target</p>
            <p className="text-[11px] text-text-muted">
              {cardsCompleted} of {cardsTarget} card{cardsTarget !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <span className="text-xl font-display font-bold text-text-primary tabular-nums">
          {cardsTarget - cardsCompleted > 0 ? cardsTarget - cardsCompleted : 0}
          <span className="text-xs font-body font-normal text-text-muted ml-1">left</span>
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden mb-4">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-accent-primary to-accent-secondary"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>

      {/* Action */}
      {dayComplete ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex items-center justify-center gap-2 py-2 text-sm text-accent-primary font-medium"
        >
          <CheckCircle size={16} />
          Day complete!
        </motion.div>
      ) : (
        <GlowButton onClick={onStudy} size="md" className="w-full">
          <BookOpen size={14} />
          Study {cardsTarget - cardsCompleted} card{cardsTarget - cardsCompleted !== 1 ? 's' : ''}
        </GlowButton>
      )}
    </motion.div>
  )
}
