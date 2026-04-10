/**
 * StreakBadge — compact streak indicator (flame icon + count).
 *
 * Rendered in the navbar so the user always sees their streak. Clicking it
 * navigates to /profile for the full stats view. The flame glows brighter as
 * the streak grows; a 0-day streak renders muted.
 *
 * Reads from GamificationContext so it stays in sync with Profile after every
 * review without each surface re-fetching independently.
 */
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Flame } from 'lucide-react'
import clsx from 'clsx'
import { useGamification } from '@/context/GamificationContext'

export function StreakBadge() {
  const { stats } = useGamification()

  // While stats are still loading (or the user is signed out) render nothing
  // to keep the navbar clean — there's no useful skeleton at this size.
  if (!stats) return null

  const streak = stats.current_streak
  const isActive = streak > 0

  return (
    <Link
      to="/profile"
      aria-label={`Current streak: ${streak} day${streak === 1 ? '' : 's'}`}
      className={clsx(
        'flex items-center gap-1.5 px-2.5 py-1 border rounded-lg text-[11px] font-semibold transition-all duration-200 glow-hover tabular-nums',
        isActive
          ? 'border-orange-500/40 text-orange-300 hover:border-orange-500/60'
          : 'border-white/[0.08] text-text-muted hover:text-text-secondary',
      )}
    >
      <motion.span
        animate={isActive ? { scale: [1, 1.12, 1] } : undefined}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        className="flex items-center"
      >
        <Flame
          size={12}
          strokeWidth={2.4}
          className={isActive ? 'text-orange-400' : 'text-text-muted'}
          fill={isActive ? 'currentColor' : 'none'}
        />
      </motion.span>
      <span>{streak}</span>
    </Link>
  )
}
