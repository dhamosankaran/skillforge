import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp, CheckCircle } from 'lucide-react'
import { getSeverityColor, getSeverityBg } from '@/utils/formatters'
import type { FormattingIssue } from '@/types'

interface FormattingIssuesProps {
  issues: FormattingIssue[]
}

const SEVERITY_ICONS = {
  critical: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

function IssueItem({ issue }: { issue: FormattingIssue }) {
  const [expanded, setExpanded] = useState(false)
  const Icon = SEVERITY_ICONS[issue.severity as keyof typeof SEVERITY_ICONS] || Info
  const color = getSeverityColor(issue.severity)
  const bg = getSeverityBg(issue.severity)

  return (
    <div
      className="rounded-xl border overflow-hidden transition-colors"
      style={{ background: bg, borderColor: `${color}25` }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-4 text-left"
        aria-expanded={expanded}
        aria-label={`${issue.severity}: ${issue.issue}`}
      >
        <Icon size={15} style={{ color, flexShrink: 0, marginTop: 1 }} />
        <span className="flex-1 text-sm text-text-primary">{issue.issue}</span>
        {expanded ? (
          <ChevronUp size={14} className="text-text-muted flex-shrink-0" />
        ) : (
          <ChevronDown size={14} className="text-text-muted flex-shrink-0" />
        )}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pl-10">
              <p className="text-sm text-text-secondary leading-relaxed">
                <span className="font-medium text-text-primary">Fix: </span>
                {issue.fix}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function FormattingIssues({ issues }: FormattingIssuesProps) {
  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="w-12 h-12 rounded-full bg-success/10 border border-success/30 flex items-center justify-center mb-3">
          <CheckCircle size={20} className="text-success" />
        </div>
        <p className="text-text-primary font-medium">No formatting issues found!</p>
        <p className="text-sm text-text-muted mt-1">Your resume structure is ATS-friendly.</p>
      </div>
    )
  }

  const critical = issues.filter((i) => i.severity === 'critical').length
  const warnings = issues.filter((i) => i.severity === 'warning').length

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 text-xs">
        {critical > 0 && (
          <span className="px-2 py-1 rounded bg-danger/10 text-danger border border-danger/20">
            {critical} critical
          </span>
        )}
        {warnings > 0 && (
          <span className="px-2 py-1 rounded bg-warning/10 text-warning border border-warning/20">
            {warnings} warnings
          </span>
        )}
      </div>
      <div className="space-y-2">
        {issues.map((issue, i) => (
          <IssueItem key={i} issue={issue} />
        ))}
      </div>
    </div>
  )
}
