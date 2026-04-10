import clsx from 'clsx'
import { getGradeColor, getScoreColor } from '@/utils/formatters'

interface ScoreBadgeProps {
  score?: number
  grade?: string
  size?: 'sm' | 'md' | 'lg'
}

export function ScoreBadge({ score, grade, size = 'md' }: ScoreBadgeProps) {
  const hexColor = grade ? getGradeColor(grade) : score !== undefined ? getScoreColor(score) : null
  const label = grade || (score !== undefined ? `${score}` : '–')

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 rounded',
    md: 'text-sm px-3 py-1 rounded-md',
    lg: 'text-base px-4 py-1.5 rounded-lg font-semibold',
  }

  // When we have a hex color (from grade/score), use hex+alpha for bg/border.
  // For the fallback (no grade, no score), use CSS variables directly.
  const style = hexColor
    ? {
        color: hexColor,
        backgroundColor: `${hexColor}18`,
        border: `1px solid ${hexColor}30`,
      }
    : {
        color: 'var(--text-muted)',
        backgroundColor: 'rgba(var(--color-contrast), 0.06)',
        border: '1px solid rgba(var(--color-contrast), 0.12)',
      }

  return (
    <span
      className={clsx('inline-flex items-center font-mono font-medium', sizeClasses[size])}
      style={style}
    >
      {label}
    </span>
  )
}
