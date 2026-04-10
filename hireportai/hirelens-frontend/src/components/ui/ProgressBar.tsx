import { motion } from 'framer-motion'
import clsx from 'clsx'

interface ProgressBarProps {
  value: number
  max?: number
  color?: string
  className?: string
  showLabel?: boolean
  label?: string
  height?: string
}

export function ProgressBar({
  value,
  max = 100,
  color,
  className,
  showLabel = false,
  label,
  height = 'h-2',
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  const colorMap: Record<string, string> = {
    teal: 'var(--success)',
    violet: 'var(--accent-primary)',
    default: pct >= 80 ? 'var(--success)' : pct >= 60 ? 'var(--warning)' : 'var(--danger)',
  }

  const autoColor = color
    ? colorMap[color] || color
    : colorMap['default']

  return (
    <div className={clsx('w-full', className)}>
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-1">
          {label && <span className="text-sm text-text-secondary">{label}</span>}
          {showLabel && (
            <span className="text-xs font-mono" style={{ color: autoColor }}>
              {Math.round(pct)}%
            </span>
          )}
        </div>
      )}
      <div className={clsx('w-full bg-bg-overlay rounded-full overflow-hidden', height)}>
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: autoColor }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}
