import clsx from 'clsx'
import { getGradeColor, getScoreColor } from '@/utils/formatters'

interface ScoreBadgeProps {
  score?: number
  grade?: string
  size?: 'sm' | 'md' | 'lg'
}

export function ScoreBadge({ score, grade, size = 'md' }: ScoreBadgeProps) {
  const color = grade ? getGradeColor(grade) : score !== undefined ? getScoreColor(score) : '#8b949e'
  const label = grade || (score !== undefined ? `${score}` : '–')

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 rounded',
    md: 'text-sm px-3 py-1 rounded-md',
    lg: 'text-base px-4 py-1.5 rounded-lg font-semibold',
  }

  return (
    <span
      className={clsx('inline-flex items-center font-mono font-medium', sizeClasses[size])}
      style={{
        color,
        backgroundColor: `${color}18`,
        border: `1px solid ${color}30`,
      }}
    >
      {label}
    </span>
  )
}
