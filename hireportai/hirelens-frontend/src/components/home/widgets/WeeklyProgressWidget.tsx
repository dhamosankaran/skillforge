import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { ActivityHeatmap } from '@/components/progress/ActivityHeatmap'
import { useGamification } from '@/context/GamificationContext'
import type { Persona } from '@/context/AuthContext'

interface WeeklyProgressWidgetProps {
  persona: Persona
}

/**
 * Empty state gated on gamification stats as a proxy for "has reviewed any card":
 * total_xp === 0 and longest_streak === 0 means no reviews have landed yet.
 * The heatmap component fetches + renders its own loading state, so this widget
 * primarily branches loading/empty; errors from the heatmap stay inside it.
 */
export function WeeklyProgressWidget({ persona }: WeeklyProgressWidgetProps) {
  const { stats, isLoading } = useGamification()

  let state: WidgetState
  if (isLoading && !stats) {
    state = 'loading'
  } else if (stats && stats.total_xp === 0 && stats.longest_streak === 0) {
    state = 'empty'
  } else {
    state = 'data'
  }

  return (
    <DashboardWidget
      title="Weekly Progress"
      testid="weekly-progress"
      persona={persona}
      state={state}
      emptyMessage="Review your first card to see your activity heatmap."
      action={
        state === 'data'
          ? { label: 'View profile', href: '/profile' }
          : state === 'empty'
            ? { label: 'Start reviewing', href: '/learn/daily' }
            : undefined
      }
    >
      <ActivityHeatmap />
    </DashboardWidget>
  )
}
