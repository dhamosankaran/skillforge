import { motion } from 'framer-motion'
import { ProgressBar } from '@/components/ui/ProgressBar'
import type { ATSScoreBreakdown } from '@/types'

interface ScoreBreakdownProps {
  breakdown: ATSScoreBreakdown
}

const SCORE_ITEMS = [
  { key: 'keyword_match' as const, label: 'Keyword Match', weight: '40%' },
  { key: 'skills_coverage' as const, label: 'Skills Coverage', weight: '25%' },
  { key: 'formatting_compliance' as const, label: 'Formatting Compliance', weight: '20%' },
  { key: 'bullet_strength' as const, label: 'Bullet Strength', weight: '15%' },
]

export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  return (
    <div className="space-y-5">
      {SCORE_ITEMS.map(({ key, label, weight }, i) => {
        const value = breakdown[key]
        return (
          <motion.div
            key={key}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
          >
            <div className="flex justify-between items-center mb-2">
              <div>
                <span className="text-sm font-medium text-text-primary">{label}</span>
                <span className="ml-2 text-xs text-text-muted">({weight})</span>
              </div>
              <span
                className="text-sm font-mono font-semibold"
                style={{
                  color: value >= 80 ? 'var(--success)' : value >= 60 ? 'var(--warning)' : 'var(--danger)',
                }}
              >
                {Math.round(value)}
              </span>
            </div>
            <ProgressBar value={value} height="h-2.5" />
          </motion.div>
        )
      })}
    </div>
  )
}
