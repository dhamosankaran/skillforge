import { motion } from 'framer-motion'
import { Building2, Calendar, Trash2 } from 'lucide-react'
import { ScoreBadge } from '@/components/ui/ScoreBadge'
import type { TrackerApplication } from '@/types'

interface ApplicationCardProps {
  application: TrackerApplication
  onDelete: (id: string) => void
  dragHandleProps?: Record<string, unknown>
}

export function ApplicationCard({ application, onDelete, dragHandleProps }: ApplicationCardProps) {
  const { id, company, role, date_applied, ats_score } = application

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ scale: 1.02 }}
      className="bg-bg-elevated border border-contrast/[0.06] rounded-xl p-4 cursor-grab active:cursor-grabbing"
      {...dragHandleProps}
    >
      {/* Company & Delete */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/5 border border-contrast/[0.06] flex items-center justify-center">
            <Building2 size={14} className="text-text-muted" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-text-primary leading-tight">{company}</h4>
            <p className="text-xs text-text-secondary">{role}</p>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(id)
          }}
          className="p-1.5 rounded-lg text-text-muted hover:text-danger hover:bg-danger/10 transition-colors"
          aria-label={`Delete ${company} application`}
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Score + Date */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <Calendar size={11} />
          {date_applied}
        </div>
        <ScoreBadge score={ats_score} size="sm" />
      </div>
    </motion.div>
  )
}
