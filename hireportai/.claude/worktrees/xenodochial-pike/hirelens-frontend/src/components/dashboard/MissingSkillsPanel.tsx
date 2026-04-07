import { motion } from 'framer-motion'
import { AlertCircle, Info, Star, ExternalLink } from 'lucide-react'
import { getImportanceBg, getImportanceColor } from '@/utils/formatters'
import { getSkillResource } from '@/utils/skillResources'
import type { SkillGap } from '@/types'
import { containerVariants, cardVariants } from '@/components/ui/AnimatedCard'

interface MissingSkillsPanelProps {
  skillGaps: SkillGap[]
}

const IMPORTANCE_ICONS = {
  critical: AlertCircle,
  recommended: Star,
  'nice-to-have': Info,
}

export function MissingSkillsPanel({ skillGaps }: MissingSkillsPanelProps) {
  if (skillGaps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="w-12 h-12 rounded-full bg-success/10 border border-success/30 flex items-center justify-center mb-3">
          <Star size={20} className="text-success" />
        </div>
        <p className="text-text-primary font-medium">No skill gaps detected!</p>
        <p className="text-sm text-text-muted mt-1">Your resume covers the key requirements.</p>
      </div>
    )
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 sm:grid-cols-2 gap-3"
    >
      {skillGaps.map((gap) => {
        const Icon = IMPORTANCE_ICONS[gap.importance]
        const color = getImportanceColor(gap.importance)
        const bg = getImportanceBg(gap.importance)

        return (
          <motion.div
            key={gap.skill}
            variants={cardVariants}
            className="flex items-start gap-3 p-3 rounded-lg border"
            style={{
              background: bg,
              borderColor: `${color}25`,
            }}
          >
            <Icon size={14} style={{ color, marginTop: 2, flexShrink: 0 }} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-primary truncate">{gap.skill}</p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{ color, background: `${color}15` }}
                >
                  {gap.importance}
                </span>
                <span className="text-xs text-text-muted">{gap.category}</span>
                {(() => {
                  const resource = getSkillResource(gap.skill)
                  return resource ? (
                    <a
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-0.5 text-xs text-accent-primary/70 hover:text-accent-primary transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink size={10} />
                      {resource.label}
                    </a>
                  ) : null
                })()}
              </div>
            </div>
          </motion.div>
        )
      })}
    </motion.div>
  )
}
