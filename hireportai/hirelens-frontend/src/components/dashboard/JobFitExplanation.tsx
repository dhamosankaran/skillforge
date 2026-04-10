import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, XCircle, Lightbulb } from 'lucide-react'

interface JobFitExplanationProps {
  explanation: string
  topStrengths: string[]
  topGaps: string[]
}

export function JobFitExplanation({
  explanation,
  topStrengths,
  topGaps,
}: JobFitExplanationProps) {
  const [displayed, setDisplayed] = useState('')

  // Typewriter effect
  useEffect(() => {
    if (!explanation) return
    let i = 0
    setDisplayed('')
    const interval = setInterval(() => {
      if (i < explanation.length) {
        setDisplayed(explanation.slice(0, i + 1))
        i++
      } else {
        clearInterval(interval)
      }
    }, 18)
    return () => clearInterval(interval)
  }, [explanation])

  return (
    <div className="space-y-6">
      {/* Explanation text */}
      <div className="p-4 rounded-xl bg-bg-elevated border border-contrast/[0.06]">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb size={14} className="text-accent-primary" />
          <span className="text-xs font-medium text-accent-primary uppercase tracking-wider">
            Job Fit Analysis
          </span>
        </div>
        <p className="text-sm text-text-secondary leading-relaxed min-h-[60px]">
          {displayed}
          <motion.span
            animate={{ opacity: [1, 0] }}
            transition={{ repeat: Infinity, duration: 0.8 }}
            className="inline-block w-0.5 h-4 bg-accent-primary ml-0.5 align-middle"
          />
        </p>
      </div>

      {/* Strengths and gaps grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Strengths */}
        <div>
          <h4 className="text-xs font-medium text-success uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <CheckCircle size={12} />
            Top Strengths
          </h4>
          <div className="space-y-2">
            {topStrengths.length > 0 ? (
              topStrengths.map((s, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-start gap-2 p-2.5 rounded-lg bg-success/5 border border-success/15"
                >
                  <CheckCircle size={12} className="text-success flex-shrink-0 mt-0.5" />
                  <span className="text-xs text-text-primary">{s}</span>
                </motion.div>
              ))
            ) : (
              <p className="text-xs text-text-muted">No strengths identified</p>
            )}
          </div>
        </div>

        {/* Gaps */}
        <div>
          <h4 className="text-xs font-medium text-danger uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <XCircle size={12} />
            Top Gaps
          </h4>
          <div className="space-y-2">
            {topGaps.length > 0 ? (
              topGaps.map((g, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-start gap-2 p-2.5 rounded-lg bg-danger/5 border border-danger/15"
                >
                  <XCircle size={12} className="text-danger flex-shrink-0 mt-0.5" />
                  <span className="text-xs text-text-primary">{g}</span>
                </motion.div>
              ))
            ) : (
              <p className="text-xs text-text-muted">No gaps identified</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
