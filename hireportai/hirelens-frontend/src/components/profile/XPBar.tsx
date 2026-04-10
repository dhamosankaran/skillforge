/**
 * XPBar — animated progress bar showing XP toward the next level.
 *
 * Levels are tier-based: each tier (Apprentice → Journeyman → Expert →
 * Master) is anchored to one of the badge thresholds in the spec. The bar
 * fills from the previous tier threshold to the next; once Master (10k XP) is
 * reached the bar is full and the label collapses to "Max level".
 *
 * The threshold table is hard-coded here on purpose — these values come from
 * the badge spec and changing them in one place without the other would
 * desync the UI from the backend's badge evaluator.
 */
import { motion } from 'framer-motion'
import { Trophy } from 'lucide-react'

interface XPBarProps {
  totalXp: number
}

interface Tier {
  name: string
  /** XP at the bottom of this tier (where the bar starts filling). */
  floor: number
  /** XP at the top of this tier (where the bar reaches 100%). */
  ceil: number
}

// Mirrors the xp_* badges in app/services/gamification_service.BADGES.
// Anything below 100 XP is "Novice" (the implicit pre-Apprentice tier).
const TIERS: Tier[] = [
  { name: 'Novice',     floor: 0,     ceil: 100 },
  { name: 'Apprentice', floor: 100,   ceil: 500 },
  { name: 'Journeyman', floor: 500,   ceil: 2000 },
  { name: 'Expert',     floor: 2000,  ceil: 10000 },
]

const MAX_TIER_NAME = 'Master'
const MAX_XP = 10000

function resolveTier(totalXp: number): { tier: Tier | null; isMax: boolean } {
  if (totalXp >= MAX_XP) return { tier: null, isMax: true }
  for (const t of TIERS) {
    if (totalXp < t.ceil) return { tier: t, isMax: false }
  }
  return { tier: null, isMax: true }
}

export function XPBar({ totalXp }: XPBarProps) {
  const { tier, isMax } = resolveTier(totalXp)

  if (isMax || !tier) {
    return (
      <div className="w-full">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Trophy size={14} className="text-accent-primary" />
            <span className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              {MAX_TIER_NAME}
            </span>
          </div>
          <span className="text-[11px] font-mono text-accent-primary tabular-nums">
            {totalXp.toLocaleString()} XP
          </span>
        </div>
        <div className="w-full h-2 rounded-full overflow-hidden bg-bg-overlay">
          <div className="h-full w-full bg-gradient-to-r from-accent-primary to-orange-400" />
        </div>
        <p className="mt-1.5 text-[10px] text-text-muted">Max level reached</p>
      </div>
    )
  }

  const span = tier.ceil - tier.floor
  const into = totalXp - tier.floor
  const pct = Math.max(0, Math.min(100, (into / span) * 100))
  const remaining = tier.ceil - totalXp

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Trophy size={14} className="text-accent-primary" />
          <span className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
            {tier.name}
          </span>
        </div>
        <span className="text-[11px] font-mono text-text-secondary tabular-nums">
          {totalXp.toLocaleString()} / {tier.ceil.toLocaleString()} XP
        </span>
      </div>
      <div className="w-full h-2 rounded-full overflow-hidden bg-bg-overlay">
        <motion.div
          className="h-full bg-gradient-to-r from-accent-primary to-orange-400"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <p className="mt-1.5 text-[10px] text-text-muted tabular-nums">
        {remaining.toLocaleString()} XP to next level
      </p>
    </div>
  )
}
