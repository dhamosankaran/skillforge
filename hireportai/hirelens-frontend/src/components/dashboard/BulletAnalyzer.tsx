import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { getBulletScoreColor } from '@/utils/formatters'
import type { BulletAnalysis } from '@/types'

interface BulletAnalyzerProps {
  bullets: BulletAnalysis[]
}

function BulletCard({ bullet }: { bullet: BulletAnalysis }) {
  const [expanded, setExpanded] = useState(false)
  const color = getBulletScoreColor(bullet.score)

  return (
    <div className="bg-bg-elevated border border-contrast/[0.06] rounded-xl overflow-hidden">
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span
            className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-mono font-bold mt-0.5"
            style={{ background: `${color}18`, color }}
          >
            {bullet.score}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-text-secondary leading-relaxed line-clamp-2">
              {bullet.original}
            </p>
            <div className="mt-2">
              <ProgressBar value={bullet.score * 10} height="h-1.5" />
            </div>
            {bullet.issues.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {bullet.issues.map((issue) => (
                  <span
                    key={issue}
                    className="text-xs px-2 py-0.5 rounded bg-danger/10 text-danger/80 border border-danger/20"
                  >
                    {issue}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {bullet.score < 8 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-3 flex items-center gap-1.5 text-xs text-accent-primary hover:text-accent-primary/80 transition-colors"
            aria-label={expanded ? 'Hide rewritten bullet' : 'Show rewritten bullet'}
          >
            <Sparkles size={12} />
            {expanded ? 'Hide suggestion' : 'Show AI suggestion'}
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        )}
      </div>

      <AnimatePresence>
        {expanded && bullet.rewritten && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-0">
              <div className="p-3 rounded-lg bg-accent-primary/5 border border-accent-primary/20">
                <p className="text-xs text-accent-primary font-medium mb-1 flex items-center gap-1">
                  <Sparkles size={10} />
                  Suggested rewrite
                </p>
                <p className="text-sm text-text-primary leading-relaxed">{bullet.rewritten}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function BulletAnalyzer({ bullets }: BulletAnalyzerProps) {
  if (bullets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <p className="text-text-muted text-sm">No bullet points found in your resume.</p>
        <p className="text-xs text-text-muted mt-1">Add bullet-point descriptions to your experience sections.</p>
      </div>
    )
  }

  const avgScore = Math.round(bullets.reduce((sum, b) => sum + b.score, 0) / bullets.length)

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-text-secondary">{bullets.length} bullets analyzed</p>
        <span
          className="text-sm font-mono font-semibold px-2 py-1 rounded"
          style={{
            color: getBulletScoreColor(avgScore),
            background: `${getBulletScoreColor(avgScore)}18`,
          }}
        >
          Avg: {avgScore}/10
        </span>
      </div>
      <div className="space-y-3">
        {bullets.map((bullet, i) => (
          <BulletCard key={i} bullet={bullet} />
        ))}
      </div>
    </div>
  )
}
