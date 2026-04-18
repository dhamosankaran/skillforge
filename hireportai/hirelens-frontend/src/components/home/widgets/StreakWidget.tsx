import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { useGamification } from '@/context/GamificationContext'
import type { Persona } from '@/context/AuthContext'

interface StreakWidgetProps {
  persona: Persona
}

export function StreakWidget({ persona }: StreakWidgetProps) {
  const { stats, isLoading, error, refresh } = useGamification()

  let state: WidgetState
  if (isLoading && !stats) {
    state = 'loading'
  } else if (error && !stats) {
    state = 'error'
  } else if (!stats || stats.current_streak === 0) {
    state = 'empty'
  } else {
    state = 'data'
  }

  return (
    <DashboardWidget
      title="Streak"
      testid="streak"
      persona={persona}
      state={state}
      emptyMessage="Start your streak — review a card today."
      errorMessage="Couldn't load your streak."
      onRetry={() => void refresh()}
      action={
        state === 'data'
          ? { label: 'View profile', href: '/profile' }
          : state === 'empty'
            ? { label: 'Start now', href: '/learn/daily' }
            : undefined
      }
    >
      {stats && stats.current_streak > 0 && (
        <div className="flex flex-col">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-3xl font-bold text-text-primary">
              {stats.current_streak}
            </span>
            <span className="text-sm text-text-secondary">
              {stats.current_streak === 1 ? 'day streak' : 'day streak'}
            </span>
          </div>
          <span className="text-xs text-text-muted mt-1">
            Best: {stats.longest_streak} {stats.longest_streak === 1 ? 'day' : 'days'}
          </span>
        </div>
      )}
    </DashboardWidget>
  )
}
